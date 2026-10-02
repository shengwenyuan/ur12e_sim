"""Place the exterior wall relative to the configured turning glass pane."""

import math

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom

# pylint: enable=import-error

import wall_materials
from wall_components import WallPanel

from wall_layout import PARTITION, RED_WALL, RED_WALL_PATH, RED_WALL_REFERENCE


def build(stage: Usd.Stage) -> dict:
    """Align the wall's viewer-left end with the glass's viewer-right edge."""
    unit = UsdGeom.XformCache().GetLocalToWorldTransform(
        stage.GetPrimAtPath(RED_WALL_REFERENCE)
    )
    tangent = unit.TransformDir(Gf.Vec3d(1, 0, 0)).GetNormalized()
    outward = Gf.Vec3d(tangent[1], -tangent[0], 0)
    right_edge = unit.Transform(Gf.Vec3d(PARTITION.edge_width, 0, 0))
    offset = RED_WALL.gap + (PARTITION.glass_thickness + RED_WALL.thickness) / 2
    left_end = right_edge + outward * offset
    center = left_end - tangent * (RED_WALL.length / 2)
    center[2] = RED_WALL.height / 2
    wall_materials.surface_material(
        stage, RED_WALL_PATH + "Material", (0.7, 0.015, 0.015), 0.9, 0
    )
    yaw = math.degrees(math.atan2(tangent[1], tangent[0]))
    WallPanel(
        tuple(center),
        (RED_WALL.length, RED_WALL.thickness, RED_WALL.height),
        RED_WALL_PATH + "Material",
        yaw,
    ).build(stage, RED_WALL_PATH)
    return {
        "prim_path": RED_WALL_PATH,
        "reference_unit": RED_WALL_REFERENCE,
        "center_m": list(center),
        "yaw_deg": yaw,
        "dimensions_xyz_m": [RED_WALL.length, RED_WALL.thickness, RED_WALL.height],
        "surface_clearance_m": RED_WALL.gap,
        "center_plane_offset_m": offset,
        "outward_normal_world": list(outward),
        "left_end_ground_m": list(left_end),
        "right_end_ground_m": list(left_end - tangent * RED_WALL.length),
        "alignment": (
            "Inside looking out: wall left end aligns with glass right clear edge "
            "along outward normal"
        ),
    }
