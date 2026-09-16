"""URDF forward kinematics for saved poses, with radians and meters at input."""

import math
import pathlib
import xml.etree.ElementTree as ET

from pxr import Gf  # pylint: disable=import-error


def rotation(axis: tuple, radians: float):
    """Return a USD row-vector rotation matrix."""
    return Gf.Matrix4d().SetRotate(
        Gf.Rotation(Gf.Vec3d(*axis), math.degrees(radians))
    )


def origin_matrix(origin):
    """Convert URDF extrinsic XYZ Euler angles without changing axis order."""
    if origin is None:
        return Gf.Matrix4d(1)
    xyz = [float(value) for value in origin.get("xyz", "0 0 0").split()]
    rpy = [float(value) for value in origin.get("rpy", "0 0 0").split()]
    result = Gf.Matrix4d(1)
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rpy):
        result *= rotation(axis, angle)
    return result * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*xyz))


def joint_matrix(joint, positions: dict):
    """Apply joint motion in the local axis frame after the fixed origin."""
    name, kind = joint.get("name"), joint.get("type")
    value = positions.get(name, 0.0)
    axis_node = joint.find("axis")
    axis = (
        tuple(float(v) for v in axis_node.get("xyz").split())
        if axis_node is not None
        else (1, 0, 0)
    )
    motion = Gf.Matrix4d(1)
    if kind in ("revolute", "continuous"):
        motion = rotation(axis, value)
    elif kind == "prismatic":
        motion.SetTranslate(Gf.Vec3d(*axis) * value)
    elif kind != "fixed":
        raise ValueError(f"Unsupported joint type: {kind}")
    return motion * origin_matrix(joint.find("origin"))


class Model:
    """Parse and order URDF topology once for repeated pose evaluation."""

    def __init__(self, urdf: pathlib.Path):
        robot = ET.parse(urdf).getroot()
        joints = robot.findall("joint")
        children = {joint.find("child").get("link") for joint in joints}
        roots = {link.get("name") for link in robot.findall("link")} - children
        if len(roots) != 1:
            raise ValueError("Expected exactly one URDF root")
        self.root = roots.pop()
        self.joints = []
        known = {self.root}
        pending = list(joints)
        while pending:
            ready = [
                j for j in pending if j.find("parent").get("link") in known
            ]
            if not ready:
                raise ValueError("Disconnected or cyclic URDF joints")
            for joint in ready:
                self.joints.append(joint)
                known.add(joint.find("child").get("link"))
                pending.remove(joint)

    def forward(self, positions: dict) -> dict:
        """Return link transforms relative to the URDF root, in tree order."""
        poses = {self.root: Gf.Matrix4d(1)}
        for joint in self.joints:
            parent = poses[joint.find("parent").get("link")]
            poses[joint.find("child").get("link")] = (
                joint_matrix(joint, positions) * parent
            )
        return poses


def forward(urdf: pathlib.Path, positions: dict) -> dict:
    """Convenience entry for one-off saved-pose composition."""
    return Model(urdf).forward(positions)
