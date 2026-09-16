"""Physical scene overlay and Isaac 6.0.1 articulation adapter.

Only prepare() is used by static tests. Kit and solver imports stay in Driver.
"""

import math
import time

# OpenUSD/Kit are supplied only by the independent Ubuntu Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

from ur12e_collection.contracts import JOINT_NAMES
from ur12e_collection.followers import physics

FINGER_NAMES = tuple(
    f"robotiq_hande_{s}_finger_joint" for s in ("left", "right")
)
NAMES = (*JOINT_NAMES, *FINGER_NAMES)


def fixed(stage, path, body0, body1):
    """Bind at the current relative transform; an absent body0 means world."""
    joint = UsdPhysics.FixedJoint.Define(stage, path)
    cache = UsdGeom.XformCache()
    world = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(body1))
    relative = world
    if body0:
        joint.CreateBody0Rel().SetTargets([body0])
        relative = (
            world
            * cache.GetLocalToWorldTransform(
                stage.GetPrimAtPath(body0)
            ).GetInverse()
        )
    joint.CreateBody1Rel().SetTargets([body1])
    joint.CreateLocalPos0Attr(Gf.Vec3f(relative.ExtractTranslation()))
    joint.CreateLocalRot0Attr(Gf.Quatf(relative.ExtractRotationQuat()))
    joint.CreateLocalPos1Attr(Gf.Vec3f(0))
    joint.CreateLocalRot1Attr(Gf.Quatf(1))
    return joint


def finger_inertia(body):
    """Estimate inertia from a uniform collision-bounds box."""
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        ["default", "render", "proxy", "guide"],
        False,
        True,
    )
    bounds = Gf.Range3d()
    for prim in Usd.PrimRange(body):
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            bounds.UnionWith(
                cache.ComputeRelativeBound(prim, body).ComputeAlignedRange()
            )
    size = bounds.GetSize()
    if bounds.IsEmpty() or min(size) <= 0:
        raise ValueError(f"missing finger collision bounds: {body.GetPath()}")
    mass = UsdPhysics.MassAPI(body)
    m = mass.GetMassAttr().Get()
    x, y, z = size
    inertia = Gf.Vec3f(
        m * (y * y + z * z) / 12,
        m * (x * x + z * z) / 12,
        m * (x * x + y * y) / 12,
    )
    mass.CreateDiagonalInertiaAttr(inertia)
    mass.CreateCenterOfMassAttr(Gf.Vec3f(bounds.GetMidpoint()))
    mass.CreatePrincipalAxesAttr(Gf.Quatf(1))
    body.CreateAttribute(
        "physicsModel:inertiaSource", Sdf.ValueTypeNames.String
    ).Set("uniform collision-bounds box; provisional, not measured")
    return {
        "body": str(body.GetPath()),
        "size_m": list(size),
        "inertia_kg_m2": list(inertia),
    }


def prepare(stage, _root, config):
    """Compose a physical session overlay without starting or importing Kit."""
    settings = config["physics"]
    if (
        UsdGeom.GetStageMetersPerUnit(stage) != 1
        or UsdGeom.GetStageUpAxis(stage) != "Z"
    ):
        raise ValueError("physical scene requires meters and Z up")
    stage.SetEditTarget(stage.GetSessionLayer())
    joints = {
        p.GetName(): p
        for p in stage.Traverse()
        if p.IsA(UsdPhysics.Joint)
        and str(p.GetPath()).startswith(("/World/UR12e/", "/World/HandE/"))
    }
    if not set(NAMES).issubset(joints):
        raise ValueError(
            "scene must expose the configured six arm and two finger joints"
        )
    arm_base = topology(stage, joints)
    inertias = configure_drives(stage, joints, config)
    configure_contacts(stage, settings)
    scenes = [p for p in stage.Traverse() if p.IsA(UsdPhysics.Scene)]
    if len(scenes) > 1:
        raise ValueError("physical follower requires exactly one physics scene")
    scene = (
        UsdPhysics.Scene(scenes[0])
        if scenes
        else UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    )
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(9.81)
    stage.GetSessionLayer().customLayerData = {
        "physical_model": "provisional force drives; box finger inertia",
        "dynamics_accepted": False,
    }
    return {
        "articulation": str(arm_base),
        "scene": str(scene.GetPath()),
        "finger_inertias": inertias,
    }


def topology(stage, joints):
    """Combine arm and tool into one world-fixed articulation tree."""
    arm_base = (
        UsdPhysics.Joint(joints[JOINT_NAMES[0]]).GetBody0Rel().GetTargets()[0]
    )
    flange = (
        UsdPhysics.Joint(joints[JOINT_NAMES[-1]]).GetBody1Rel().GetTargets()[0]
    )
    coupler_joint = UsdPhysics.Joint(
        stage.GetPrimAtPath("/World/HandE/Physics/robotiq_hande_coupler_joint")
    )
    coupler = coupler_joint.GetBody1Rel().GetTargets()[0]
    for prim in list(stage.Traverse()):
        if not str(prim.GetPath()).startswith(
            ("/World/UR12e/", "/World/HandE/")
        ):
            continue
        if (
            prim.HasAPI(UsdPhysics.ArticulationRootAPI)
            and prim.GetPath() != arm_base
        ):
            prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
        if prim.IsA(UsdPhysics.FixedJoint):
            joint = UsdPhysics.Joint(prim)
            if joint.GetBody1Rel().GetTargets() in ([arm_base], [coupler]):
                prim.SetActive(False)
    base_joint = fixed(stage, "/World/PhysicalJoints/Base", None, arm_base)
    fixed(stage, "/World/PhysicalJoints/Tool", flange, coupler)
    UsdPhysics.ArticulationRootAPI.Apply(stage.GetPrimAtPath(arm_base))
    base_joint.CreateExcludeFromArticulationAttr(False)
    return arm_base


def configure_drives(stage, joints, config):
    """Author force drives with explicit SI-to-USD angular conversion."""
    settings = config["physics"]
    inertias = []
    for i, name in enumerate(NAMES):
        prim = joints[name]
        angular = i < 6
        if not prim.IsA(
            UsdPhysics.RevoluteJoint if angular else UsdPhysics.PrismaticJoint
        ):
            raise ValueError(f"unexpected joint type: {name}")
        # Independent fingers must not have a competing mimic constraint.
        for schema in prim.GetAppliedSchemas():
            if "Mimic" in schema:
                prim.RemoveAppliedSchema(schema)
        drive = UsdPhysics.DriveAPI.Apply(
            prim, "angular" if angular else "linear"
        )
        drive.CreateTypeAttr("force")
        scale = math.pi / 180 if angular else 1
        drive.CreateStiffnessAttr(
            (
                settings.arm_stiffness[i]
                if angular
                else settings.finger_stiffness
            )
            * scale
        )
        drive.CreateDampingAttr(
            (settings.arm_damping[i] if angular else settings.finger_damping)
            * scale
        )
        drive.CreateMaxForceAttr(
            settings.arm_effort[i] if angular else settings.finger_effort
        )
        drive.CreateTargetVelocityAttr(0)
        drive.CreateTargetPositionAttr(
            math.degrees(config["limits"].ready[i]) if angular else 0.025
        )
        if angular:
            joint = UsdPhysics.RevoluteJoint(prim)
            joint.CreateLowerLimitAttr(math.degrees(config["limits"].lower[i]))
            joint.CreateUpperLimitAttr(math.degrees(config["limits"].upper[i]))
        else:
            body = stage.GetPrimAtPath(
                UsdPhysics.Joint(prim).GetBody1Rel().GetTargets()[0]
            )
            inertias.append(finger_inertia(body))
    return inertias


def configure_contacts(stage, settings):
    """Apply workcell materials and adjacent-body collision exclusions."""
    # Filter only mechanically adjacent bodies.
    for prim in stage.Traverse():
        if not prim.IsA(UsdPhysics.Joint):
            continue
        joint = UsdPhysics.Joint(prim)
        a, b = (
            joint.GetBody0Rel().GetTargets(),
            joint.GetBody1Rel().GetTargets(),
        )
        if (
            a
            and b
            and (
                str(a[0]).startswith("/World/UR12e/")
                or str(a[0]).startswith("/World/HandE/")
            )
        ):
            UsdPhysics.FilteredPairsAPI.Apply(
                stage.GetPrimAtPath(a[0])
            ).CreateFilteredPairsRel().AddTarget(b[0])
    material = UsdShade.Material.Define(stage, "/World/PhysicalMaterial")
    api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    api.CreateStaticFrictionAttr(settings.static_friction)
    api.CreateDynamicFrictionAttr(settings.dynamic_friction)
    api.CreateRestitutionAttr(settings.restitution)
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.CollisionAPI) and str(
            prim.GetPath()
        ).startswith(
            ("/World/UR12e/", "/World/HandE/", "/World/Table/", "/World/Floor")
        ):
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(
                material, materialPurpose="physics"
            )


class Driver:
    """Isaac 6.0.1 compatibility API; initialization is the only teleport."""

    def __init__(self, stage, root, config):
        # Static preparation intentionally has no dependency on a running Kit.
        # Lazy imports require a running Kit and are absent on Mac.
        # pylint: disable=import-outside-toplevel,import-error
        from isaacsim.core.api import SimulationContext
        from isaacsim.core.prims import SingleArticulation
        from isaacsim.core.utils.types import ArticulationAction
        import numpy as np
        from pxr import PhysxSchema

        # pylint: enable=import-outside-toplevel,import-error

        self.np, self.action = np, ArticulationAction
        self.layout = prepare(stage, root, config)
        scene = stage.GetPrimAtPath(self.layout["scene"])
        api = PhysxSchema.PhysxSceneAPI.Apply(scene)
        api.CreateTimeStepsPerSecondAttr(config["physics"].step_hz)
        api.CreateSolverTypeAttr(config["physics"].solver_type)
        api.CreateEnableGPUDynamicsAttr(False)
        root_prim = stage.GetPrimAtPath(self.layout["articulation"])
        articulation = PhysxSchema.PhysxArticulationAPI.Apply(root_prim)
        articulation.CreateEnabledSelfCollisionsAttr(True)
        articulation.CreateSolverPositionIterationCountAttr(16)
        articulation.CreateSolverVelocityIterationCountAttr(4)
        self.sim = SimulationContext(
            physics_dt=1 / config["physics"].step_hz,
            rendering_dt=0,
            stage_units_in_meters=1,
            physics_prim_path=self.layout["scene"],
            set_defaults=False,
            backend="numpy",
            device="cpu",
        )
        self.sim.reset()
        try:
            self.robot = SingleArticulation(
                self.layout["articulation"], reset_xform_properties=False
            )
            self.robot.initialize()
            names = self.robot.dof_names
            if set(names) != set(NAMES) or len(names) != len(NAMES):
                raise ValueError(f"physical articulation DOFs differ: {names}")
            self.indices = np.array([names.index(name) for name in NAMES])
            home = np.array((*config["limits"].ready, 0.025, 0.025))
            self.robot.set_joint_positions(home, joint_indices=self.indices)
            self.robot.set_joint_velocities(
                np.zeros(8), joint_indices=self.indices
            )
            self.robot.apply_action(
                self.action(joint_positions=home, joint_indices=self.indices)
            )
            self.origin = self.sim.current_time
            self.last_time = self.origin
            self.sequence = 0
            self.sample = self._read()
        except BaseException:
            self.close()
            raise

    def _read(self):
        q = self.robot.get_joint_positions(joint_indices=self.indices)
        qd = self.robot.get_joint_velocities(joint_indices=self.indices)
        return physics.Sample(
            tuple(map(float, q[:6])),
            tuple(map(float, qd[:6])),
            tuple(map(float, q[6:])),
            tuple(map(float, qd[6:])),
            self.sim.current_time - self.origin,
            self.sequence,
            time.monotonic_ns(),
        )

    def read(self):
        """Return the last solver acquisition without refreshing its clock."""
        return self.sample

    def is_playing(self):
        """Expose actual timeline status."""
        return self.sim.is_playing()

    def step(self, q, fingers):
        """Apply drive targets, step once and read solved DOFs in SI units."""
        if not self.sim.is_playing() or self.sim.current_time != self.last_time:
            raise ValueError(
                "simulation paused, reset or advanced outside its owner"
            )
        self.robot.apply_action(
            self.action(
                joint_positions=self.np.array((*q, *fingers)),
                joint_velocities=self.np.zeros(8),
                joint_indices=self.indices,
            )
        )
        self.sim.step(render=False)
        self.sequence += 1
        self.last_time = self.sim.current_time
        self.sample = self._read()
        return self.sample

    def render(self):
        """Render without an additional physics step."""
        self.sim.render()

    def close(self):
        """Stop this local simulation only."""
        self.sim.stop()
