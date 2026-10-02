"""Attach a straight glass run and a five-facet bend to the chair-side wall."""

import math

# OpenUSD comes from the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

import room_extension
import workcell_furniture

GROUP = workcell_furniture.GROUP + "/ChairSideGlass"
STRAIGHT_COUNT, BEND_COUNT, TURN_DEG = 3, 5, 18
COUNT = STRAIGHT_COUNT + BEND_COUNT
CLEAR_WIDTH, EDGE_WIDTH = 0.8128, 0.005
HEIGHT, GLASS_THICKNESS = 3.0, 0.02
SKIRT_HEIGHT, SKIRT_THICKNESS = 0.10, 0.03
PITCH = CLEAR_WIDTH + 2 * EDGE_WIDTH
LENGTH = COUNT * PITCH


def unit_poses() -> list[dict]:
    """Walk joined centerlines, turning 18 degrees at each added panel."""
    start = Gf.Vec3d(0)
    result = []
    headings = [0] * STRAIGHT_COUNT + [TURN_DEG * i for i in range(1, BEND_COUNT + 1)]
    for heading in headings:
        angle = math.radians(heading)
        end = start + Gf.Vec3d(math.cos(angle), math.sin(angle), 0) * PITCH
        result.append(
            {"start_m": list(start), "end_m": list(end), "heading_deg": heading}
        )
        start = end
    return result


def place_unit(stage, path: str, pose: dict, materials: tuple) -> None:
    """Place a clear pane and two adhesive strips over a centered metal base."""
    metal, adhesive, glass = materials
    unit = UsdGeom.Xform.Define(stage, path)
    unit.AddTranslateOp().Set(Gf.Vec3d(*pose["start_m"]))
    unit.AddRotateZOp().Set(pose["heading_deg"])
    workcell_furniture.static_box(
        stage,
        path + "/Skirting",
        (PITCH / 2, 0, SKIRT_HEIGHT / 2),
        (PITCH, SKIRT_THICKNESS, SKIRT_HEIGHT),
        metal,
    )
    parts = (
        ("NearEdge", EDGE_WIDTH / 2, EDGE_WIDTH, adhesive),
        ("Pane", PITCH / 2, CLEAR_WIDTH, glass),
        ("FarEdge", PITCH - EDGE_WIDTH / 2, EDGE_WIDTH, adhesive),
    )
    for name, x, width, material in parts:
        workcell_furniture.static_box(
            stage,
            path + "/" + name,
            (x, 0, (SKIRT_HEIGHT + HEIGHT) / 2),
            (width, GLASS_THICKNESS, HEIGHT - SKIRT_HEIGHT),
            material,
        )


def build(stage, table2: dict) -> dict:
    """Start at the short wall outer face midpoint, keeping the chair fixed."""
    b, u, v = workcell_furniture.frame(table2["corners_m"])
    center_v = workcell_furniture.SHORT_WALL_LENGTH / 2
    anchor = b + u * workcell_furniture.WALL_THICKNESS + v * center_v
    group = UsdGeom.Xform.Define(stage, GROUP)
    group.AddTranslateOp().Set(anchor)
    group.AddRotateZOp().Set(table2["yaw_deg"])
    metal = workcell_furniture.surface_material(
        stage, GROUP + "/Metal", (0.8, 0.82, 0.85), 0.25, 1
    )
    adhesive = workcell_furniture.surface_material(
        stage, GROUP + "/Adhesive", (0.35, 0.35, 0.35), 0.95, 0
    )
    glass = UsdShade.Material(stage.GetPrimAtPath(room_extension.GROUP + "/Glass"))
    for index, pose in enumerate(unit_poses()):
        place_unit(
            stage,
            GROUP + "/Unit" + str(index + 1),
            pose,
            (metal, adhesive, glass),
        )
    return {
        "prim_path": GROUP,
        "anchor_m": list(anchor),
        "yaw_deg": table2["yaw_deg"],
        "direction": "Start parallel to AB (+u), then turn toward the table side (+v)",
        "centerline_v_m": center_v,
        "unit_count": COUNT,
        "straight_unit_count": STRAIGHT_COUNT,
        "bend_unit_count": BEND_COUNT,
        "turn_increment_deg": TURN_DEG,
        "total_turn_deg": BEND_COUNT * TURN_DEG,
        "unit_poses_local": unit_poses(),
        "glass_clear_width_m": CLEAR_WIDTH,
        "edge_strip_width_m": EDGE_WIDTH,
        "unit_pitch_m": PITCH,
        "length_m": LENGTH,
        "straight_length_m": STRAIGHT_COUNT * PITCH,
        "overall_height_m": HEIGHT,
        "glass_height_m": HEIGHT - SKIRT_HEIGHT,
        "glass_thickness_m": GLASS_THICKNESS,
        "skirting_height_m": SKIRT_HEIGHT,
        "skirting_thickness_m": SKIRT_THICKNESS,
        "chair_moved": False,
    }


def local_bounds(stage, path: str, frame_path: str = GROUP) -> Gf.Range3d:
    """Measure geometry in the partition frame, including the unchanged chair."""
    root = stage.GetPrimAtPath(frame_path)
    prim = stage.GetPrimAtPath(path)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    bounds = Gf.Range3d()
    # Aggregating a rotated group first inflates its bounds; union actual leaf
    # shapes in the measurement frame instead.
    for shape in Usd.PrimRange(prim):
        if shape.IsA(UsdGeom.Boundable):
            bounds.UnionWith(
                cache.ComputeRelativeBound(shape, root).ComputeAlignedRange()
            )
    return bounds


def validate_unit(stage, path: str) -> None:
    """Measure pane, glue and skirting dimensions in the unit's own frame."""
    bounds = local_bounds(stage, path, path)
    assert abs(bounds.GetMin()[0]) < 1e-6
    assert abs(bounds.GetMax()[0] - PITCH) < 1e-6
    assert abs(bounds.GetMin()[2]) < 1e-6 and abs(bounds.GetMax()[2] - HEIGHT) < 1e-6
    intervals = []
    for name, width, thickness, height, bottom, material in (
        (
            "NearEdge",
            EDGE_WIDTH,
            GLASS_THICKNESS,
            HEIGHT - SKIRT_HEIGHT,
            SKIRT_HEIGHT,
            GROUP + "/Adhesive",
        ),
        (
            "Pane",
            CLEAR_WIDTH,
            GLASS_THICKNESS,
            HEIGHT - SKIRT_HEIGHT,
            SKIRT_HEIGHT,
            room_extension.GROUP + "/Glass",
        ),
        (
            "FarEdge",
            EDGE_WIDTH,
            GLASS_THICKNESS,
            HEIGHT - SKIRT_HEIGHT,
            SKIRT_HEIGHT,
            GROUP + "/Adhesive",
        ),
        ("Skirting", PITCH, SKIRT_THICKNESS, SKIRT_HEIGHT, 0, GROUP + "/Metal"),
    ):
        prim = stage.GetPrimAtPath(path + "/" + name)
        shape = local_bounds(stage, str(prim.GetPath()), path)
        for actual, expected in zip(
            shape.GetSize(), (width, thickness, height), strict=True
        ):
            assert abs(actual - expected) < 1e-6
        assert abs(shape.GetMin()[1] + shape.GetMax()[1]) < 1e-6
        assert abs(shape.GetMin()[2] - bottom) < 1e-6
        bound, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        assert str(bound.GetPath()) == material
        if name != "Skirting":
            intervals.append((shape.GetMin()[0], shape.GetMax()[0]))
    assert all(
        abs(left[1] - right[0]) < 1e-6 for left, right in zip(intervals, intervals[1:])
    )


# Keep wall attachment and every joint visible in one acceptance pass.
# pylint: disable-next=too-many-locals
def validate(stage, table2: dict) -> dict:
    """Check centered attachment, five 18-degree turns and chair separation."""
    b, u, v = workcell_furniture.frame(table2["corners_m"])
    root = stage.GetPrimAtPath(GROUP)
    cache = UsdGeom.XformCache()
    matrix = cache.GetLocalToWorldTransform(root)
    anchor = (
        b
        + u * workcell_furniture.WALL_THICKNESS
        + v * (workcell_furniture.SHORT_WALL_LENGTH / 2)
    )
    assert (matrix.ExtractTranslation() - anchor).GetLength() < 1e-6
    assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(1, 0, 0)), u) > 0.99999
    wall = local_bounds(stage, workcell_furniture.GROUP + "/ShortWall")
    assert abs(wall.GetMax()[0]) < 1e-6
    assert abs(wall.GetMin()[1] + wall.GetMax()[1]) < 1e-6
    boxes = [prim for prim in Usd.PrimRange(root) if prim.IsA(UsdGeom.Cube)]
    assert len(boxes) == 4 * COUNT
    assert all(
        UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() for prim in boxes
    )
    assert all(not prim.HasAPI(UsdPhysics.RigidBodyAPI) for prim in boxes)
    previous = matrix.ExtractTranslation()
    chair = local_bounds(stage, workcell_furniture.GROUP + "/Chair")
    clearance = float("inf")
    for index in range(COUNT):
        path = GROUP + "/Unit" + str(index + 1)
        prim = stage.GetPrimAtPath(path)
        unit = cache.GetLocalToWorldTransform(prim)
        assert (unit.ExtractTranslation() - previous).GetLength() < 1e-6
        heading = max(0, index - STRAIGHT_COUNT + 1) * TURN_DEG
        assert abs(prim.GetAttribute("xformOp:rotateZ").Get() - heading) < 1e-6
        previous = unit.Transform(Gf.Vec3d(PITCH, 0, 0))
        validate_unit(stage, path)
        bounds = local_bounds(stage, path)
        gap = max(
            max(
                bounds.GetMin()[axis] - chair.GetMax()[axis],
                chair.GetMin()[axis] - bounds.GetMax()[axis],
            )
            for axis in range(3)
        )
        assert gap > 0, path
        clearance = min(clearance, gap)
    assert Gf.Dot(unit.TransformDir(Gf.Vec3d(1, 0, 0)), v) > 0.99999
    for name, roughness, metallic in (("Metal", 0.25, 1), ("Adhesive", 0.95, 0)):
        shader = UsdShade.Shader(stage.GetPrimAtPath(GROUP + "/" + name + "/OmniPBR"))
        assert (
            abs(shader.GetInput("reflection_roughness_constant").Get() - roughness)
            < 1e-6
        )
        assert shader.GetInput("metallic_constant").Get() == metallic
    assert (
        stage.GetPrimAtPath(room_extension.GROUP + "/Glass/OmniGlass")
        .GetAttribute("inputs:thin_walled")
        .Get()
    )
    return {
        "status": "PASS",
        "static_colliders": len(boxes),
        "length_m": LENGTH,
        "unit_count": COUNT,
        "turn_deg": BEND_COUNT * TURN_DEG,
        "chair_clearance_m": clearance,
        "chair_moved": False,
        "endpoint_world_m": list(previous),
    }
