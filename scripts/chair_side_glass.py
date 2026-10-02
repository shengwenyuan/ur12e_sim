"""Describe a joined glass run in the Table2 attachment frame."""

import math

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd

# pylint: enable=import-error

import scene_geometry
import wall_materials
from wall_components import WallAssembly, WallPanel

from wall_layout import FURNITURE, PARTITION, PARTITION_PATH, GLASS_PATH


def unit_poses() -> list[dict]:
    """Walk joined centerlines, turning 18 degrees at each added panel."""
    start = Gf.Vec3d(0)
    result = []
    headings = [0] * PARTITION.straight_count + [
        PARTITION.turn_deg * i for i in range(1, PARTITION.bend_count + 1)
    ]
    for heading in headings:
        angle = math.radians(heading)
        end = start + Gf.Vec3d(math.cos(angle), math.sin(angle), 0) * PARTITION.pitch
        result.append(
            {"start_m": list(start), "end_m": list(end), "heading_deg": heading}
        )
        start = end
    return result


def glass_unit(pose: dict) -> WallAssembly:
    """Place a clear pane and two adhesive strips over a centered metal base."""
    panels = [
        (
            "Skirting",
            WallPanel(
                (PARTITION.pitch / 2, 0, PARTITION.skirt_height / 2),
                (PARTITION.pitch, PARTITION.skirt_thickness, PARTITION.skirt_height),
                PARTITION_PATH + "/Metal",
            ),
        )
    ]
    parts = (
        (
            "NearEdge",
            PARTITION.edge_width / 2,
            PARTITION.edge_width,
            PARTITION_PATH + "/Adhesive",
        ),
        ("Pane", PARTITION.pitch / 2, PARTITION.clear_width, GLASS_PATH),
        (
            "FarEdge",
            PARTITION.pitch - PARTITION.edge_width / 2,
            PARTITION.edge_width,
            PARTITION_PATH + "/Adhesive",
        ),
    )
    panels.extend(
        (
            name,
            WallPanel(
                (x, 0, (PARTITION.skirt_height + PARTITION.height) / 2),
                (
                    width,
                    PARTITION.glass_thickness,
                    PARTITION.height - PARTITION.skirt_height,
                ),
                material,
            ),
        )
        for name, x, width, material in parts
    )
    return WallAssembly(
        panels=tuple(panels),
        translation=tuple(pose["start_m"]),
        yaw_deg=pose["heading_deg"],
    )


def build(stage: Usd.Stage, table2: dict) -> dict:
    """Start at the short wall outer face midpoint, keeping the chair fixed."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    center_v = FURNITURE.short_wall_length / 2
    anchor = b + u * FURNITURE.wall_thickness + v * center_v
    WallAssembly(translation=tuple(anchor), yaw_deg=table2["yaw_deg"]).build(
        stage, PARTITION_PATH
    )
    wall_materials.surface_material(
        stage, PARTITION_PATH + "/Metal", (0.8, 0.82, 0.85), 0.25, 1
    )
    wall_materials.surface_material(
        stage, PARTITION_PATH + "/Adhesive", (0.35, 0.35, 0.35), 0.95, 0
    )
    wall_materials.glass_material(stage, GLASS_PATH)
    units = tuple(
        ("Unit" + str(index + 1), glass_unit(pose))
        for index, pose in enumerate(unit_poses())
    )
    WallAssembly(children=units).build(stage, PARTITION_PATH)
    return {
        "prim_path": PARTITION_PATH,
        "anchor_m": list(anchor),
        "yaw_deg": table2["yaw_deg"],
        "direction": "Start parallel to AB (+u), then turn toward the table side (+v)",
        "centerline_v_m": center_v,
        "unit_count": PARTITION.count,
        "straight_unit_count": PARTITION.straight_count,
        "bend_unit_count": PARTITION.bend_count,
        "turn_increment_deg": PARTITION.turn_deg,
        "total_turn_deg": PARTITION.bend_count * PARTITION.turn_deg,
        "unit_poses_local": unit_poses(),
        "glass_clear_width_m": PARTITION.clear_width,
        "edge_strip_width_m": PARTITION.edge_width,
        "unit_pitch_m": PARTITION.pitch,
        "length_m": PARTITION.length,
        "straight_length_m": PARTITION.straight_count * PARTITION.pitch,
        "overall_height_m": PARTITION.height,
        "glass_height_m": PARTITION.height - PARTITION.skirt_height,
        "glass_thickness_m": PARTITION.glass_thickness,
        "skirting_height_m": PARTITION.skirt_height,
        "skirting_thickness_m": PARTITION.skirt_thickness,
        "chair_moved": False,
    }
