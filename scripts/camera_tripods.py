"""Place coarse visual tripod assemblies beside the calibrated D435 cameras."""

import math
import pathlib

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics

# pylint: enable=import-error

import calibrated_cameras
import compose_scene

ASSET = "assets/props/tripod_d435/isaac/tripod_d435.usdc"
ROOT_PATH = "/World/CameraTripods"


def native_geometry(asset: pathlib.Path) -> tuple[Gf.Vec3d, float]:
    """Read the native RGB offset and lowest assembly geometry in meters."""
    source = Usd.Stage.Open(str(asset))
    rgb = source.GetDefaultPrim().GetPath().AppendPath("Sensors/RGB")
    offset = (
        UsdGeom.XformCache()
        .GetLocalToWorldTransform(source.GetPrimAtPath(rgb))
        .ExtractTranslation()
    )
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    bottom = (
        cache.ComputeWorldBound(source.GetDefaultPrim())
        .ComputeAlignedRange()
        .GetMin()[2]
    )
    return offset, bottom


def place(
    stage: Usd.Stage,
    asset: pathlib.Path,
    camera: Usd.Prim,
    serial: str,
    native: tuple[Gf.Vec3d, float],
) -> dict:
    """Ground one assembly, preserving only optical XY and horizontal heading."""
    offset, bottom = native
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(camera)
    target = matrix.ExtractTranslation()
    forward = matrix.TransformDir(Gf.Vec3d(0, 0, -1))
    yaw = math.degrees(math.atan2(forward[1], forward[0]))
    rotated = Gf.Rotation(Gf.Vec3d(0, 0, 1), yaw).TransformDir(offset)
    position = Gf.Vec3d(target[0] - rotated[0], target[1] - rotated[1], -bottom)
    prim = compose_scene.place(
        stage, ROOT_PATH + "/" + camera.GetName(), asset, tuple(position), yaw
    )
    UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
    stage.GetPrimAtPath(prim.GetPath().AppendChild("Sensors")).SetActive(False)
    visual_rgb = position + rotated
    return {
        "prim_path": str(prim.GetPath()),
        "serial": serial,
        "position_world_m": list(position),
        "yaw_deg": yaw,
        "calibrated_rgb_world_m": list(target),
        "visual_rgb_world_m": list(visual_rgb),
        "optical_separation_m": (visual_rgb - target).GetLength(),
    }


def build(stage: Usd.Stage, root: pathlib.Path, config: dict) -> dict:
    """Reference one native asset twice; leave calibrated sensor prims intact."""
    asset = root / ASSET
    native = native_geometry(asset)
    placements = {}
    UsdGeom.Xform.Define(stage, ROOT_PATH)
    for name in ("camera_2", "camera_3"):
        spec = config["cameras"][name]
        parent = calibrated_cameras.reference_link(stage, spec["reference_link"])
        camera = stage.GetPrimAtPath(parent.GetPath().AppendChild(name))
        placements[name] = place(stage, asset, camera, spec["serial"], native)
    return {
        "asset": "../../" + ASSET,
        "placement": "native scale; grounded feet; calibrated RGB XY and horizontal heading",
        "body_mode": "static; source rigid body disabled; colliders retained",
        "nominal_sensors": "inactive; original calibrated cameras unchanged",
        "instances": placements,
    }
