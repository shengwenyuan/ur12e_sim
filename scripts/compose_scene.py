"""Compose the nominal HOME workcell with enabled collision geometry."""

import argparse
import ast
import json
import math
import os
import pathlib

# OpenUSD is supplied by the existing Ubuntu Isaac environment.
# pylint: disable=import-error
from pxr import (
    Gf,
    Sdf,
    Usd,
    UsdGeom,
    UsdPhysics,
)

# pylint: enable=import-error

import kinematics
import table_scene


def check_home(collection_root: pathlib.Path, home: list) -> None:
    """Check collection HOME without importing any device or control code."""
    profile = collection_root / "src/ur12e_collection/simulation/profile.py"
    tree = ast.parse(profile.read_text(encoding="utf-8"))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "HOME"
            for target in node.targets
        )
    )
    # Evaluate only HOME from this trusted repository, without device imports.
    # pylint: disable-next=eval-used
    value = eval(
        compile(ast.Expression(assignment.value), str(profile), "eval"),
        {"__builtins__": {}, "math": math},
    )
    if any(
        abs(a - math.radians(b)) > 1e-12
        for a, b in zip(value, home, strict=True)
    ):
        raise ValueError("Layout HOME differs from collection HOME")


def reference(stage, path: str, asset: pathlib.Path, output: pathlib.Path):
    """Add a relocatable asset reference."""
    prim = UsdGeom.Xform.Define(stage, path).GetPrim()
    prim.GetReferences().AddReference(os.path.relpath(asset, output.parent))
    return prim


class PoseWriter:
    """Cache imported link prims; retain mesh offsets and reset-stack rules."""

    def __init__(self, prim, names):
        self.prim = prim
        self.links = [
            link
            for link in Usd.PrimRange(prim)
            if link != prim
            and link.GetName() in names
            and link.IsA(UsdGeom.Xform)
        ]

    def apply(self, poses: dict, mounting) -> None:
        """Author parent-first local transforms into the current edit layer."""
        UsdGeom.Xformable(self.prim).MakeMatrixXform().Set(mounting)
        for link in self.links:
            world = poses[link.GetName()] * mounting
            transform = UsdGeom.Xformable(link)
            cache = UsdGeom.XformCache()
            parent_world = cache.GetLocalToWorldTransform(link.GetParent())
            local = (
                world
                if transform.GetResetXformStack()
                else world * parent_world.GetInverse()
            )
            transform.MakeMatrixXform().Set(local)
        if self.prim.HasAttribute("extentsHint"):
            self.prim.GetAttribute("extentsHint").Block()


def apply_pose(prim, poses: dict, mounting) -> None:
    """Apply a one-off pose using the same path as the live mirror."""
    PoseWriter(prim, poses).apply(poses, mounting)


def collisions(stage) -> list:
    """Make collider overrides editable and select convex decomposition."""
    for prim in list(Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())):
        if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.IsInstanceProxy():
            ancestor = prim.GetParent()
            while ancestor.IsInstanceProxy():
                ancestor = ancestor.GetParent()
            ancestor.SetInstanceable(False)
    paths = []
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(True)
            if prim.IsA(UsdGeom.Mesh):
                UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(
                    "convexDecomposition"
                )
            paths.append(str(prim.GetPath()))
    return paths


def place_robot(stage, root: pathlib.Path, layout: dict, output: pathlib.Path):
    """Mount the separate nominal tool asset on the arm tool0 frame."""
    arm_dir = root / "assets/robots/ur12e"
    tool_dir = root / "assets/grippers/hande"
    arm_poses = kinematics.forward(
        arm_dir / "ur12e.urdf",
        dict(
            zip(
                layout["robot"]["joint_names"],
                map(math.radians, layout["robot"]["home_deg"]),
                strict=True,
            )
        ),
    )
    tool_poses = kinematics.forward(
        tool_dir / "hande.urdf",
        {
            f"robotiq_hande_{side}_finger_joint": 0.025
            for side in ("left", "right")
        },
    )
    # Installation orientation is independent of the TCP's natural offset.
    yaw = layout["robot"].get("base_yaw_rad")
    if yaw is None:
        yaw = -math.pi
    mounting = kinematics.rotation((0, 0, 1), yaw) * Gf.Matrix4d().SetTranslate(
        Gf.Vec3d(*layout["robot"]["base_position_m"])
    )
    arm = reference(
        stage, "/World/UR12e", arm_dir / "usd/ur12e/ur12e.usda", output
    )
    tool = reference(
        stage, "/World/HandE", tool_dir / "usd/hande/hande.usda", output
    )
    apply_pose(arm, arm_poses, mounting)
    tool_mount = arm_poses["tool0"] * mounting
    apply_pose(tool, tool_poses, tool_mount)
    for prim in (arm, tool):
        prim.CreateAttribute(
            "preview:stateSource", Sdf.ValueTypeNames.String
        ).Set("configured_home_static")
    tool.CreateAttribute(
        "preview:jawOpeningMeters", Sdf.ValueTypeNames.Double
    ).Set(0.05)
    return yaw, tool_poses["robotiq_hande_end"] * tool_mount


def compose(root: pathlib.Path, collection_root: pathlib.Path) -> dict:
    """Save HOME geometry and collision authoring without stepping physics."""
    directory = root / "scenes/tabletop_home"
    layout_path = directory / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    check_home(collection_root, layout["robot"]["home_deg"])
    output = directory / "scene.usda"
    table_scene.build(layout_path, output)
    stage = Usd.Stage.Open(str(output))
    yaw, tcp_matrix = place_robot(stage, root, layout, output)
    for prim in stage.Traverse():
        if (
            str(prim.GetPath()).startswith("/World/Table/")
            or str(prim.GetPath()) == "/World/Floor"
        ):
            if prim.IsA(UsdGeom.Cube):
                UsdPhysics.CollisionAPI.Apply(prim)
    collider_paths = collisions(stage)
    camera = UsdGeom.Camera(stage.GetPrimAtPath("/World/Camera"))
    camera.CreateFocalLengthAttr(22)
    view = Gf.Matrix4d().SetLookAt(
        Gf.Vec3d(-1.6, 5.2, 3.0),
        Gf.Vec3d(1.1, 0.6, 1.25),
        Gf.Vec3d(0, 0, 1),
    )
    UsdGeom.Xformable(camera).MakeMatrixXform().Set(view.GetInverse())
    # A static reference point records the nominal fingertip TCP independently
    # of the user's approximate XY layout marker and any real tool calibration.
    UsdGeom.Xform.Define(stage, "/World/NominalTCP").AddTransformOp().Set(
        tcp_matrix
    )
    stage.GetRootLayer().customLayerData = {
        "purpose": "Nominal UR12e/Hand-E HOME with collision geometry",
        "robot_meshes_loaded": True,
        "robot_control": False,
        "physics_integration": False,
        "tool_mount_verified": False,
        "base_yaw_rad": yaw,
        "cameraSettings": {"boundCamera": "/World/Camera"},
    }
    stage.GetRootLayer().Save()
    report = {
        "scene": "scene.usda",
        "home_deg": layout["robot"]["home_deg"],
        "base_yaw_rad": yaw,
        "nominal_tcp_m": list(tcp_matrix.ExtractTranslation()),
        "tool_z_direction": list(tcp_matrix.TransformDir(Gf.Vec3d(0, 0, 1))),
        "collider_count": len(collider_paths),
        "colliders": collider_paths,
        "gripper_state": "static_open_unobserved",
        "physics_contact_test": "NOT RUN",
    }
    (directory / "scene-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--collection-root",
        type=pathlib.Path,
        required=True,
        help="Collection checkout whose HOME must match the scene layout",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            compose(
                pathlib.Path(__file__).resolve().parents[1],
                args.collection_root,
            ),
            indent=2,
        )
    )
