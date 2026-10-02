"""Place Table2 assets and describe its adjoining painted L wall."""

import pathlib

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdPhysics

# pylint: enable=import-error

import scene_geometry
import wall_materials
from wall_components import WallAssembly, WallPanel

import compose_scene
import cut_wood_board
from wall_layout import FURNITURE, FURNITURE_PATH, PAINT_PATH


def walls(stage: Usd.Stage, anchor, u, v, yaw: float) -> None:
    """Create the two static oriented boxes with shared matte paint."""
    wall_materials.paint_material(stage, PAINT_PATH)
    placements = (
        (
            "LongWall",
            anchor
            - u * (FURNITURE.board_run_length / 2)
            - v * (FURNITURE.board_thickness + FURNITURE.wall_thickness / 2),
            (
                FURNITURE.board_run_length,
                FURNITURE.wall_thickness,
                FURNITURE.wall_height,
            ),
        ),
        (
            "ShortWall",
            anchor
            + u * (FURNITURE.wall_thickness / 2)
            + v * (FURNITURE.short_wall_length / 2),
            (
                FURNITURE.wall_thickness,
                FURNITURE.short_wall_length,
                FURNITURE.wall_height,
            ),
        ),
    )
    panels = []
    for name, center, dimensions in placements:
        center[2] = FURNITURE.wall_height / 2
        panels.append((name, WallPanel(tuple(center), dimensions, PAINT_PATH, yaw)))
    WallAssembly(panels=tuple(panels)).build(stage, FURNITURE_PATH)


def place_boards(stage: Usd.Stage, source: pathlib.Path, table2: dict) -> dict:
    """Keep the BC endpoint and seam fixed while cutting only the far board."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    boards = (source, cut_wood_board.build(source, FURNITURE.board_widths[1]))
    positions, distance = {}, 0.0
    for index, (asset, width) in enumerate(
        zip(boards, FURNITURE.board_widths, strict=True)
    ):
        name = "Board" + str(index + 1)
        center = b - u * (distance + width / 2) - v * (FURNITURE.board_thickness / 2)
        center[2] = FURNITURE.board_height / 2
        prim = compose_scene.place(
            stage,
            FURNITURE_PATH + "/" + name,
            asset,
            tuple(center),
            table2["yaw_deg"] + 180,
        )
        UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
        positions[name] = list(center)
        distance += width
    return positions


def build(stage: Usd.Stage, root: pathlib.Path, table2: dict) -> dict:
    """Place two boards, one chair and two walls without stepping physics."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    yaw = table2["yaw_deg"]
    directory = root / "assets/furniture"
    positions = place_boards(
        stage, directory / "wood_board/isaac/wood_board.usdc", table2
    )
    chair = directory / "red_cushion_caster_chair/isaac/chair_fixed.usda"
    # The source chair faces -Y; this rotation maps its front to C-to-D.
    center = Gf.Vec3d(*table2["corners_m"]["C"]) - u * 0.1 + v * (0.545 / 2 + 0.05)
    center[2] = 0
    compose_scene.place(
        stage, FURNITURE_PATH + "/Chair", chair, tuple(center), yaw - 90
    )
    positions["Chair"] = list(center)
    walls(stage, b, u, v, yaw)
    return {
        "prim_path": FURNITURE_PATH,
        "positions_m": positions,
        "board_yaw_deg": yaw + 180,
        "chair_yaw_deg": yaw - 90,
        "wall_height_m": FURNITURE.wall_height,
        "wall_thickness_m": FURNITURE.wall_thickness,
        "board_widths_m": list(FURNITURE.board_widths),
        "long_wall_length_m": FURNITURE.board_run_length,
        "short_wall_length_m": FURNITURE.short_wall_length,
        "material": "white OmniPBR; roughness 0.9; metallic 0",
        "runtime_dependency": wall_materials.PBR_MDL,
        "corner_joint": "Board1's 18 mm end bridges the wall faces at B",
    }
