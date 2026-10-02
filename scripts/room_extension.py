"""Describe the far-end painted wall and its two framed openings."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Usd

# pylint: enable=import-error

import scene_geometry
import wall_materials
from wall_components import WallAssembly, WallPanel

from wall_layout import FURNITURE, ROOM, ROOM_PATH, PAINT_PATH, GLASS_PATH


def window(interval: tuple) -> WallAssembly:
    """Frame a clear pane, with no opaque wall behind its opening."""
    start, width = interval
    outer_width = width + 2 * ROOM.border
    frame_height = ROOM.frame_top - ROOM.frame_bottom
    parts = (
        (
            "NearBorder",
            start + ROOM.border / 2,
            (ROOM.frame_bottom + ROOM.frame_top) / 2,
            ROOM.border,
            frame_height,
        ),
        (
            "FarBorder",
            start + outer_width - ROOM.border / 2,
            (ROOM.frame_bottom + ROOM.frame_top) / 2,
            ROOM.border,
            frame_height,
        ),
        (
            "BottomBorder",
            start + outer_width / 2,
            ROOM.frame_bottom + ROOM.border / 2,
            width,
            ROOM.border,
        ),
        (
            "TopBorder",
            start + outer_width / 2,
            ROOM.frame_top - ROOM.border / 2,
            width,
            ROOM.border,
        ),
    )
    panels = [
        (
            name,
            WallPanel(
                (ROOM.thickness / 2, y, z), (ROOM.thickness, length, height), PAINT_PATH
            ),
        )
        for name, y, z, length, height in parts
    ]
    panels.append(
        (
            "Pane",
            WallPanel(
                (
                    ROOM.thickness / 2,
                    start + outer_width / 2,
                    ROOM.glass_bottom + ROOM.glass_height / 2,
                ),
                (ROOM.glass_thickness, width, ROOM.glass_height),
                GLASS_PATH,
            ),
        )
    )
    return WallAssembly(panels=tuple(panels))


def build(stage: Usd.Stage, table2: dict) -> dict:
    """Attach the end block and glazed wall using Table2's measured frame."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    anchor = (
        b
        - u * (FURNITURE.board_run_length + ROOM.end_width)
        + v * (ROOM.end_depth - FURNITURE.board_thickness)
    )
    WallAssembly(translation=tuple(anchor), yaw_deg=table2["yaw_deg"]).build(
        stage, ROOM_PATH
    )
    wall_materials.paint_material(stage, PAINT_PATH)
    wall_materials.glass_material(stage, GLASS_PATH)
    solids = (
        (
            "EndWall",
            (ROOM.end_width / 2, -ROOM.end_depth / 2, ROOM.height / 2),
            (ROOM.end_width, ROOM.end_depth, ROOM.height),
        ),
        (
            "SillWall",
            (ROOM.thickness / 2, ROOM.openings_length / 2, ROOM.frame_bottom / 2),
            (ROOM.thickness, ROOM.openings_length, ROOM.frame_bottom),
        ),
        (
            "HeaderWall",
            (
                ROOM.thickness / 2,
                ROOM.openings_length / 2,
                (ROOM.frame_top + ROOM.height) / 2,
            ),
            (ROOM.thickness, ROOM.openings_length, ROOM.height - ROOM.frame_top),
        ),
        (
            "FarWall",
            (
                ROOM.thickness / 2,
                (ROOM.openings_length + ROOM.length) / 2,
                ROOM.height / 2,
            ),
            (ROOM.thickness, ROOM.far_wall_length, ROOM.height),
        ),
    )
    panels = tuple(
        (name, WallPanel(center, dimensions, PAINT_PATH))
        for name, center, dimensions in solids
    )
    windows, start = [], 0.0
    for index, width in enumerate(ROOM.glass_widths, start=1):
        windows.append(("Window" + str(index), window((start, width))))
        start += width + 2 * ROOM.border
    WallAssembly(panels=panels, children=tuple(windows)).build(stage, ROOM_PATH)
    return {
        "prim_path": ROOM_PATH,
        "anchor_m": list(anchor),
        "yaw_deg": table2["yaw_deg"],
        "extension_direction": "Table2 B-to-C (+v); table side",
        "wall_length_m": ROOM.length,
        "wall_height_m": ROOM.height,
        "wall_thickness_m": ROOM.thickness,
        "end_wall_footprint_m": [ROOM.end_width, ROOM.end_depth],
        "glass_clear_widths_m": list(ROOM.glass_widths),
        "glass_bottom_m": ROOM.glass_bottom,
        "glass_height_m": ROOM.glass_height,
        "glass_thickness_m": ROOM.glass_thickness,
        "frame_border_m": ROOM.border,
        "between_frames_gap_m": 0,
        "far_solid_wall_length_m": ROOM.far_wall_length,
        "runtime_dependency": wall_materials.GLASS_MDL,
    }
