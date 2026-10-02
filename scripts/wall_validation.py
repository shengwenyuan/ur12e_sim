"""Independent acceptance checks for composed wall geometry and materials."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

import scene_geometry
import wall_materials
from wall_layout import (
    FURNITURE,
    FURNITURE_PATH,
    ROOM,
    ROOM_PATH,
    PARTITION,
    PARTITION_PATH,
    RED_WALL,
    RED_WALL_PATH,
    RED_WALL_REFERENCE,
    GLASS_PATH,
)


def bounds_in_partition(stage, path: str, frame_path: str = PARTITION_PATH):
    """Measure a leaf union in the partition or a specific unit frame."""
    return scene_geometry.bounds_in_frame(stage, path, frame_path)


def bounds_in_room(stage, path: str):
    """Measure each leaf directly in the room frame."""
    return scene_geometry.bounds_in_frame(stage, path, ROOM_PATH)


# pylint: disable-next=too-many-locals
def validate_furniture(stage, table2: dict) -> dict:
    """Measure seams, direction, support, collisions and chair clearance."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    transforms = UsdGeom.XformCache()
    bodies, measured = [], {}
    for name in ("Board1", "Board2", "Chair"):
        prim = stage.GetPrimAtPath(FURNITURE_PATH + "/" + name)
        assert not UsdPhysics.RigidBodyAPI(prim).GetRigidBodyEnabledAttr().Get()
        bounds = cache.ComputeRelativeBound(prim, prim).ComputeAlignedRange()
        matrix = transforms.GetLocalToWorldTransform(prim)
        center = matrix.ExtractTranslation()
        assert abs(center[2] + bounds.GetMin()[2]) < 0.001
        shapes = [p for p in Usd.PrimRange(prim) if p.HasAPI(UsdPhysics.CollisionAPI)]
        assert shapes and all(
            UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get() for p in shapes
        )
        if name.startswith("Board"):
            width = FURNITURE.board_widths[int(name[-1]) - 1]
            assert abs(bounds.GetSize()[0] - width) < 1e-5
            assert abs(bounds.GetSize()[2] - FURNITURE.board_height) < 1e-5
            assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, -1, 0)), v) > 0.99999
            bodies.append((center, bounds))
        else:
            front = matrix.TransformDir(Gf.Vec3d(0, -1, 0))
            assert Gf.Dot(front, -u) > 0.99999
            rear = center + matrix.TransformDir(Gf.Vec3d(0, bounds.GetMax()[1], 0))
            assert Gf.Dot(rear - b, u) > FURNITURE.wall_thickness
            c = Gf.Vec3d(*table2["corners_m"]["C"])
            clearance = Gf.Dot(center - c, v) + bounds.GetMin()[0]
            assert clearance > 0.04
            measured["chair_table_clearance_m"] = clearance
            # Even the chair's innermost edge is beyond the wall's C-side end.
            assert (
                Gf.Dot(center - b, v) + bounds.GetMin()[0] > FURNITURE.short_wall_length
            )
        measured[name] = {"center_m": list(center), "colliders": len(shapes)}
    end = bodies[0][0] + u * FURNITURE.board_widths[0] / 2
    assert abs(Gf.Dot(end - b, u)) < 1e-6
    assert abs(Gf.Dot(end - b, v) + FURNITURE.board_thickness / 2) < 1e-6
    assert (
        abs((bodies[0][0] - bodies[1][0]).GetLength() - FURNITURE.board_run_length / 2)
        < 1e-6
    )
    for name, dimensions in (
        (
            "LongWall",
            (
                FURNITURE.board_run_length,
                FURNITURE.wall_thickness,
                FURNITURE.wall_height,
            ),
        ),
        (
            "ShortWall",
            (
                FURNITURE.wall_thickness,
                FURNITURE.short_wall_length,
                FURNITURE.wall_height,
            ),
        ),
    ):
        prim = stage.GetPrimAtPath(FURNITURE_PATH + "/" + name)
        scale = prim.GetAttribute("xformOp:scale").Get()
        assert all(abs(a - e) < 1e-6 for a, e in zip(scale, dimensions, strict=True))
        assert UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
        assert (
            abs(cache.ComputeWorldBound(prim).ComputeAlignedRange().GetMin()[2]) < 1e-6
        )
        assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        assert str(material.GetPath()) == FURNITURE_PATH + "/Paint"
    shader = UsdShade.Shader(stage.GetPrimAtPath(FURNITURE_PATH + "/Paint/OmniPBR"))
    assert shader.GetSourceAsset("mdl").path == wall_materials.PBR_MDL
    assert shader.GetSourceAssetSubIdentifier("mdl") == "OmniPBR"
    assert abs(shader.GetInput("reflection_roughness_constant").Get() - 0.9) < 1e-6
    measured["status"] = "PASS"
    return measured


# pylint: disable-next=too-many-locals
def validate_room(stage, table2: dict) -> dict:
    """Measure contiguous openings and reject wall geometry behind the glass."""
    room = stage.GetPrimAtPath(ROOM_PATH)
    assert room
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(room)
    assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, 1, 0)), v) > 0.99999
    assert abs(Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, 1, 0)), u)) < 1e-6
    start = matrix.ExtractTranslation()
    assert (
        abs(Gf.Dot(start - b, u) + FURNITURE.board_run_length + ROOM.end_width) < 1e-6
    )
    assert (
        abs(Gf.Dot(start - b, v) - (ROOM.end_depth - FURNITURE.board_thickness)) < 1e-6
    )
    boxes = [p for p in Usd.PrimRange(room) if p.IsA(UsdGeom.Cube)]
    assert len(boxes) == 14
    assert all(
        UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get() for p in boxes
    )
    assert all(not p.HasAPI(UsdPhysics.RigidBodyAPI) for p in boxes)
    end = bounds_in_room(stage, ROOM_PATH + "/EndWall")
    assert abs(end.GetMax()[1]) < 1e-6
    assert abs(end.GetMin()[0]) < 1e-6
    intervals = []
    for index, width in enumerate(ROOM.glass_widths, start=1):
        path = ROOM_PATH + "/Window" + str(index)
        pane = bounds_in_room(stage, path + "/Pane")
        low, high = pane.GetMin(), pane.GetMax()
        assert abs(low[2] - ROOM.glass_bottom) < 1e-6
        assert abs(high[2] - (ROOM.glass_bottom + ROOM.glass_height)) < 1e-6
        assert abs(low[0] - 0.03) < 1e-6 and abs(high[0] - 0.05) < 1e-6
        assert abs(high[1] - low[1] - width) < 1e-6
        frame = bounds_in_room(stage, path)
        assert abs(frame.GetMin()[2] - ROOM.frame_bottom) < 1e-6
        assert abs(frame.GetMax()[2] - ROOM.frame_top) < 1e-6
        intervals.append((frame.GetMin()[1], frame.GetMax()[1]))
        for prim in boxes:
            if str(prim.GetPath()) == path + "/Pane":
                continue
            other = bounds_in_room(stage, str(prim.GetPath()))
            overlap = (
                min(high[i], other.GetMax()[i]) - max(low[i], other.GetMin()[i])
                for i in range(3)
            )
            assert not all(distance > 1e-6 for distance in overlap), prim.GetPath()
        material, _ = UsdShade.MaterialBindingAPI(
            stage.GetPrimAtPath(path + "/Pane")
        ).ComputeBoundMaterial()
        assert str(material.GetPath()) == GLASS_PATH
    assert abs(intervals[0][0]) < 1e-6
    assert abs(intervals[0][1] - intervals[1][0]) < 1e-6
    far = bounds_in_room(stage, ROOM_PATH + "/FarWall")
    assert abs(far.GetMin()[1] - intervals[1][1]) < 1e-6
    assert abs(far.GetMax()[1] - ROOM.length) < 1e-6
    shader = UsdShade.Shader(stage.GetPrimAtPath(GLASS_PATH + "/OmniGlass"))
    assert shader.GetSourceAsset("mdl").path == wall_materials.GLASS_MDL
    assert shader.GetInput("thin_walled").Get() is True
    return {
        "status": "PASS",
        "static_colliders": len(boxes),
        "frames_touch": True,
        "glass_clear_of_opaque_boxes": True,
        "far_solid_length_m": far.GetSize()[1],
        "anchor_m": list(start),
    }


def validate_unit(stage, path: str) -> None:
    """Measure pane, glue and skirting dimensions in the unit's own frame."""
    bounds = bounds_in_partition(stage, path, path)
    assert abs(bounds.GetMin()[0]) < 1e-6
    assert abs(bounds.GetMax()[0] - PARTITION.pitch) < 1e-6
    assert (
        abs(bounds.GetMin()[2]) < 1e-6
        and abs(bounds.GetMax()[2] - PARTITION.height) < 1e-6
    )
    intervals = []
    for name, width, thickness, height, bottom, material in (
        (
            "NearEdge",
            PARTITION.edge_width,
            PARTITION.glass_thickness,
            PARTITION.height - PARTITION.skirt_height,
            PARTITION.skirt_height,
            PARTITION_PATH + "/Adhesive",
        ),
        (
            "Pane",
            PARTITION.clear_width,
            PARTITION.glass_thickness,
            PARTITION.height - PARTITION.skirt_height,
            PARTITION.skirt_height,
            GLASS_PATH,
        ),
        (
            "FarEdge",
            PARTITION.edge_width,
            PARTITION.glass_thickness,
            PARTITION.height - PARTITION.skirt_height,
            PARTITION.skirt_height,
            PARTITION_PATH + "/Adhesive",
        ),
        (
            "Skirting",
            PARTITION.pitch,
            PARTITION.skirt_thickness,
            PARTITION.skirt_height,
            0,
            PARTITION_PATH + "/Metal",
        ),
    ):
        prim = stage.GetPrimAtPath(path + "/" + name)
        shape = bounds_in_partition(stage, str(prim.GetPath()), path)
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


# pylint: disable-next=too-many-locals
def validate_partition(stage, table2: dict) -> dict:
    """Check centered attachment, five 18-degree turns and chair separation."""
    b, u, v = scene_geometry.table_frame(table2["corners_m"])
    root = stage.GetPrimAtPath(PARTITION_PATH)
    cache = UsdGeom.XformCache()
    matrix = cache.GetLocalToWorldTransform(root)
    anchor = b + u * FURNITURE.wall_thickness + v * (FURNITURE.short_wall_length / 2)
    assert (matrix.ExtractTranslation() - anchor).GetLength() < 1e-6
    assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(1, 0, 0)), u) > 0.99999
    wall = bounds_in_partition(stage, FURNITURE_PATH + "/ShortWall")
    assert abs(wall.GetMax()[0]) < 1e-6
    assert abs(wall.GetMin()[1] + wall.GetMax()[1]) < 1e-6
    boxes = [prim for prim in Usd.PrimRange(root) if prim.IsA(UsdGeom.Cube)]
    assert len(boxes) == 4 * PARTITION.count
    assert all(
        UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() for prim in boxes
    )
    assert all(not prim.HasAPI(UsdPhysics.RigidBodyAPI) for prim in boxes)
    previous = matrix.ExtractTranslation()
    chair = bounds_in_partition(stage, FURNITURE_PATH + "/Chair")
    clearance = float("inf")
    for index in range(PARTITION.count):
        path = PARTITION_PATH + "/Unit" + str(index + 1)
        prim = stage.GetPrimAtPath(path)
        unit = cache.GetLocalToWorldTransform(prim)
        assert (unit.ExtractTranslation() - previous).GetLength() < 1e-6
        heading = max(0, index - PARTITION.straight_count + 1) * PARTITION.turn_deg
        assert abs(prim.GetAttribute("xformOp:rotateZ").Get() - heading) < 1e-6
        previous = unit.Transform(Gf.Vec3d(PARTITION.pitch, 0, 0))
        validate_unit(stage, path)
        bounds = bounds_in_partition(stage, path)
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
        shader = UsdShade.Shader(
            stage.GetPrimAtPath(PARTITION_PATH + "/" + name + "/OmniPBR")
        )
        assert (
            abs(shader.GetInput("reflection_roughness_constant").Get() - roughness)
            < 1e-6
        )
        assert shader.GetInput("metallic_constant").Get() == metallic
    assert (
        stage.GetPrimAtPath(GLASS_PATH + "/OmniGlass")
        .GetAttribute("inputs:thin_walled")
        .Get()
    )
    return {
        "status": "PASS",
        "static_colliders": len(boxes),
        "length_m": PARTITION.length,
        "unit_count": PARTITION.count,
        "turn_deg": PARTITION.bend_count * PARTITION.turn_deg,
        "chair_clearance_m": clearance,
        "chair_moved": False,
        "endpoint_world_m": list(previous),
    }


def validate_red_wall(stage) -> dict:
    """Measure clearance and edge alignment independently in the glass frame."""
    wall = bounds_in_partition(stage, RED_WALL_PATH, RED_WALL_REFERENCE)
    glass = bounds_in_partition(stage, RED_WALL_REFERENCE + "/Pane", RED_WALL_REFERENCE)
    prim = stage.GetPrimAtPath(RED_WALL_PATH)
    for actual, expected in zip(
        wall.GetSize(),
        (RED_WALL.length, RED_WALL.thickness, RED_WALL.height),
        strict=True,
    ):
        assert abs(actual - expected) < 1e-6
    assert abs(wall.GetMin()[2]) < 1e-6
    gap = glass.GetMin()[1] - wall.GetMax()[1]
    assert abs(gap - RED_WALL.gap) < 1e-6
    assert abs(wall.GetMax()[0] - glass.GetMin()[0]) < 1e-6
    assert UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
    assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
    material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    assert str(material.GetPath()) == RED_WALL_PATH + "Material"
    shader = UsdShade.Shader(
        stage.GetPrimAtPath(RED_WALL_PATH + "Material" + "/OmniPBR")
    )
    assert shader.GetInput("diffuse_color_constant").Get()[0] > 0.6
    assert abs(shader.GetInput("reflection_roughness_constant").Get() - 0.9) < 1e-6
    assert shader.GetInput("metallic_constant").Get() == 0
    return {
        "status": "PASS",
        "surface_clearance_m": gap,
        "viewer_endpoint_alignment": "PASS",
        "static_colliders": 1,
    }
