"""Configured scene pose application for the native kinematic follower."""

import collections
import pathlib
import sys

from pxr import Gf, UsdGeom  # pylint: disable=import-error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import compose_scene  # pylint: disable=wrong-import-position,import-error
import kinematics  # pylint: disable=wrong-import-position,import-error

# pylint: disable-next=wrong-import-position
from ur12e_collection.contracts import JOINT_NAMES


class Pose:
    """Apply simulated joints without physics or saved-stage changes."""

    def __init__(self, stage, root):
        self.stage = stage
        self.arm_model = kinematics.Model(
            root / "assets/robots/ur12e/ur12e.urdf"
        )
        self.tool_model = kinematics.Model(
            root / "assets/grippers/hande/hande.urdf"
        )
        self.tool_poses = self.tool_model.forward(
            {
                f"robotiq_hande_{side}_finger_joint": 0.025
                for side in ("left", "right")
            }
        )
        arm = stage.GetPrimAtPath("/World/UR12e")
        tool = stage.GetPrimAtPath("/World/HandE")
        if not arm or not tool:
            raise ValueError("Scene must contain /World/UR12e and /World/HandE")
        self.mount = UsdGeom.XformCache().GetLocalToWorldTransform(arm)
        self.arm = compose_scene.PoseWriter(arm, self.arm_model.forward({}))
        self.tool = compose_scene.PoseWriter(tool, self.tool_poses)
        stage.SetEditTarget(stage.GetSessionLayer())
        self.trail = collections.deque(maxlen=300)
        self.epoch = None
        self.curve = UsdGeom.BasisCurves.Define(stage, "/World/LiveTCPTrail")
        self.curve.CreateTypeAttr("linear")
        self.curve.CreateWrapAttr("nonperiodic")
        self.curve.CreateWidthsAttr([0.004])
        self.curve.SetWidthsInterpolation("constant")
        self.curve.CreateDisplayColorAttr([Gf.Vec3f(0.1, 0.8, 0.9)])
        self.curve.CreateVisibilityAttr("invisible")

    def apply(self, q, epoch, gripper_position=0):
        """Keep the saved mounting fixed and carry Hand-E with tool0."""
        if epoch != self.epoch:
            self.trail.clear()
            self.epoch = epoch
        poses = self.arm_model.forward(dict(zip(JOINT_NAMES, q)))
        self.arm.apply(poses, self.mount)
        tool_mount = poses["tool0"] * self.mount
        self.tool_poses = self.tool_model.forward(
            {
                f"robotiq_hande_{side}_finger_joint": 0.025
                * (1 - gripper_position / 255)
                for side in ("left", "right")
            }
        )
        self.tool.apply(self.tool_poses, tool_mount)
        tcp = self.tool_poses["robotiq_hande_end"] * tool_mount
        self.trail.append(Gf.Vec3f(tcp.ExtractTranslation()))
        self.curve.GetPointsAttr().Set(list(self.trail))
        self.curve.GetCurveVertexCountsAttr().Set([len(self.trail)])
        self.curve.GetVisibilityAttr().Set(
            "inherited" if len(self.trail) >= 2 else "invisible"
        )
        return list(tcp.ExtractTranslation())
