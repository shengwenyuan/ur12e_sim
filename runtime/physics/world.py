"""Single-owner physical world with explicit steps and measured feedback."""

import json
import pathlib
import xml.etree.ElementTree as ET
import numpy as np

# OpenUSD and Kit extensions are supplied by the Ubuntu Isaac runtime.
# pylint: disable=import-error
import omni.usd
from pxr import Sdf, UsdPhysics, PhysxSchema
from isaacsim.core.simulation_manager import SimulationManager as Sim
from isaacsim.core.experimental.prims import Articulation
from . import rig


class World:
    """No hardware SDK or kinematic pose writer participates in execution."""

    def __init__(self, root: pathlib.Path, scene: pathlib.Path, *, epoch=0):
        self.source = root, scene
        self.epoch = epoch
        self._open()

    def _open(self):
        root, scene = self.source
        context = omni.usd.get_context()
        context.open_stage(str(scene))
        self.stage = context.get_stage()
        self.stage.SetEditTarget(self.stage.GetSessionLayer())
        layout = json.loads(
            (root / "scenes/tabletop_home/layout.json").read_text()
        )
        names = layout["robot"]["joint_names"]
        self.home = np.r_[np.deg2rad(layout["robot"]["home_deg"]), 0.0]
        joints = ET.parse(root / "assets/robots/ur12e/ur12e.urdf").findall(
            "joint"
        )
        limits = {
            j.attrib["name"]: j.find("limit").attrib
            for j in joints
            if j.find("limit") is not None
        }
        self.limits = np.array(
            [
                [float(limits[n][key]) for n in names]
                for key in ("lower", "upper")
            ]
        )
        bodies = rig.prepare(self.stage)
        _mount(self.stage, bodies)
        root_prim = self.stage.GetPrimAtPath("/World/UR12e")
        UsdPhysics.ArticulationRootAPI.Apply(root_prim)
        PhysxSchema.PhysxArticulationAPI.Apply(
            root_prim
        ).CreateEnabledSelfCollisionsAttr(False)
        for prim in self.stage.Traverse():
            if prim.IsA(UsdPhysics.RevoluteJoint):
                q = layout["robot"]["home_deg"][names.index(prim.GetName())]
                rig.drive(
                    prim,
                    "angular",
                    np.deg2rad(100000),
                    np.deg2rad(10000),
                    float(limits[prim.GetName()]["effort"]),
                ).CreateTargetPositionAttr(q)
                prim.CreateAttribute(
                    "state:angular:physics:position", Sdf.ValueTypeNames.Float
                ).Set(q)
        rig.physics_scene(self.stage)
        Sim.set_physics_dt(1 / 240)
        Sim.set_device("cpu")
        Sim.initialize_physics()
        self.robot = Articulation("/World/UR12e")
        self.indices = [self.robot.dof_names.index(n) for n in names]
        self.fingers = [
            self.robot.dof_names.index(f"robotiq_hande_{s}_finger_joint")
            for s in ("left", "right")
        ]
        self.steps = 0
        self.command(self.home)

    def validate(self, action: np.ndarray) -> None:
        """Check action units and source-asset joint limits before execution."""
        action = np.asarray(action, dtype=float)
        if (
            action.shape != (7,)
            or not np.isfinite(action).all()
            or not 0 <= action[6] <= 255
            or np.any(action[:6] < self.limits[0])
            or np.any(action[:6] > self.limits[1])
        ):
            raise ValueError(
                "Expected finite absolute joint radians and 0..255 closure"
            )

    def command(self, action: np.ndarray) -> None:
        """Set physical drive targets; never assign the current joint pose."""
        self.validate(action)
        self.robot.set_dof_position_targets(
            action[:6], dof_indices=self.indices
        )
        self.robot.set_dof_position_targets(
            float(0.025 * (1 - action[6] / 255)), dof_indices=self.fingers
        )

    def step(self, count: int = 1) -> None:
        """Advance simulation only through fixed substeps."""
        if not isinstance(count, int) or count <= 0:
            raise ValueError("Step count must be a positive integer")
        Sim.step(steps=count)
        self.steps += count

    @property
    def time(self) -> float:
        """Logical episode time excludes initialization and inference wait."""
        return self.steps / 240

    def state(self) -> np.ndarray:
        """Return measured simulated joints and mean finger-based closure."""
        q = self.robot.get_dof_positions().numpy()[0]
        return np.r_[
            q[self.indices],
            np.clip(255 * (1 - np.mean(q[self.fingers]) / 0.025), 0, 255),
        ]

    @property
    def clock(self) -> float:
        """Actual solver clock detects steps outside this world's owner."""
        return Sim.get_simulation_time()

    def reset(self) -> None:
        """Reopen the saved scene, rebuilding contacts and discarding state."""
        self.epoch += 1
        self._open()


def _mount(stage, bodies):
    """Replace world anchors with the actual physical tool mount."""
    # Replace imported world anchors with correctly mounted physical joints.
    for prim in stage.Traverse():
        if not prim.IsA(UsdPhysics.FixedJoint):
            continue
        joint = UsdPhysics.Joint(prim)
        targets = joint.GetBody0Rel().GetTargets()
        parent = stage.GetPrimAtPath(targets[0]) if targets else None
        child_targets = joint.GetBody1Rel().GetTargets()
        if not child_targets:
            continue
        child = stage.GetPrimAtPath(child_targets[0])
        if prim.GetName() == "robotiq_hande_coupler_joint":
            rig.fixed_frame(joint, child, bodies["wrist_3_link"])
        elif not parent or not parent.HasAPI(UsdPhysics.RigidBodyAPI):
            rig.fixed_frame(joint, child)
