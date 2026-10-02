"""Place native USD fixtures using measured wall and asset bounds."""

import math
import pathlib

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics

# pylint: enable=import-error

import compose_scene
import scene_geometry
from wall_layout import EXTINGUISHER, EXTINGUISHER_PATH, ROOM_PATH


def build(stage: Usd.Stage, root: pathlib.Path) -> dict:
    """Mount the extinguisher on the exposed AB-facing corner-column face."""
    asset = root / EXTINGUISHER.asset
    source = Usd.Stage.Open(str(asset))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    native = cache.ComputeWorldBound(source.GetDefaultPrim()).ComputeAlignedRange()
    wall = scene_geometry.bounds_in_frame(stage, EXTINGUISHER.wall_path, ROOM_PATH)
    glass = scene_geometry.bounds_in_frame(
        stage, EXTINGUISHER.adjacent_glazing_path, ROOM_PATH
    )
    exposed_start = max(wall.GetMin()[0], glass.GetMax()[0])
    if native.GetSize()[0] > wall.GetMax()[0] - exposed_start:
        raise ValueError("Extinguisher is wider than the exposed corner column")
    # A 180-degree local turn maps the source's front (-Y) into the room (+Y).
    local = Gf.Vec3d(
        (exposed_start + wall.GetMax()[0] + native.GetMin()[0] + native.GetMax()[0])
        / 2,
        wall.GetMax()[1] + native.GetMax()[1] + EXTINGUISHER.wall_gap,
        EXTINGUISHER.bottom_height - native.GetMin()[2],
    )
    room = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(ROOM_PATH))
    position = room.Transform(local)
    direction = room.TransformDir(Gf.Vec3d(1, 0, 0))
    yaw = math.degrees(math.atan2(direction[1], direction[0])) + 180
    prim = compose_scene.place(stage, EXTINGUISHER_PATH, asset, tuple(position), yaw)
    UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
    return {
        "prim_path": EXTINGUISHER_PATH,
        "asset": "../../" + EXTINGUISHER.asset,
        "wall_path": EXTINGUISHER.wall_path,
        "mount_position_room_m": list(local),
        "position_world_m": list(position),
        "yaw_deg": yaw,
        "bottom_height_m": EXTINGUISHER.bottom_height,
        "wall_gap_m": EXTINGUISHER.wall_gap,
        "native_dimensions_m": list(native.GetSize()),
        "front_direction": "Room +Y; Table2 B-to-C (+v)",
        "body_mode": "static wall fixture; source rigid body disabled",
    }
