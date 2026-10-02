"""Add a static glazed wall at the far end of the Table2 board run."""

# OpenUSD comes from the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

import workcell_furniture

GROUP = workcell_furniture.GROUP + "/Room"
GLASS_MDL = "OmniGlass.mdl"
HEIGHT, THICKNESS = 3.0, 0.08
FAR_WALL_LENGTH = 0.3
END_WIDTH, END_DEPTH = 0.3556, 0.1524
GLASS_WIDTHS, GLASS_HEIGHT, GLASS_BOTTOM = (2.3749, 1.2192), 2.4, 0.4064
BORDER, GLASS_THICKNESS = 0.0381, 0.02
FRAME_BOTTOM = GLASS_BOTTOM - BORDER
FRAME_TOP = GLASS_BOTTOM + GLASS_HEIGHT + BORDER
OPENINGS_LENGTH = sum(GLASS_WIDTHS) + 4 * BORDER
LENGTH = OPENINGS_LENGTH + FAR_WALL_LENGTH


def glass_material(stage) -> UsdShade.Material:
    """Create thin-walled clear glass using the installed Isaac MDL."""
    path = GROUP + "/Glass"
    material = UsdShade.Material.Define(stage, path)
    mdl = UsdShade.Shader.Define(stage, path + "/OmniGlass")
    mdl.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    mdl.SetSourceAsset(GLASS_MDL, "mdl")
    mdl.SetSourceAssetSubIdentifier("OmniGlass", "mdl")
    mdl.CreateInput("thin_walled", Sdf.ValueTypeNames.Bool).Set(True)
    mdl.CreateInput("glass_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1))
    mdl.CreateInput("glass_ior", Sdf.ValueTypeNames.Float).Set(1.491)
    mdl.CreateInput("frosting_roughness", Sdf.ValueTypeNames.Float).Set(0)
    material.CreateSurfaceOutput("mdl").ConnectToSource(mdl.ConnectableAPI(), "out")
    preview = UsdShade.Shader.Define(stage, path + "/Preview")
    preview.CreateIdAttr("UsdPreviewSurface")
    preview.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.9))
    preview.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.15)
    preview.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0)
    material.CreateSurfaceOutput().ConnectToSource(preview.ConnectableAPI(), "surface")
    return material


def window(stage, name: str, interval: tuple, paint) -> None:
    """Frame a clear pane, with no opaque wall behind its opening."""
    start, width = interval
    glass = UsdShade.Material(stage.GetPrimAtPath(GROUP + "/Glass"))
    outer_width = width + 2 * BORDER
    frame_height = FRAME_TOP - FRAME_BOTTOM
    parts = (
        (
            "NearBorder",
            start + BORDER / 2,
            (FRAME_BOTTOM + FRAME_TOP) / 2,
            BORDER,
            frame_height,
        ),
        (
            "FarBorder",
            start + outer_width - BORDER / 2,
            (FRAME_BOTTOM + FRAME_TOP) / 2,
            BORDER,
            frame_height,
        ),
        (
            "BottomBorder",
            start + outer_width / 2,
            FRAME_BOTTOM + BORDER / 2,
            width,
            BORDER,
        ),
        ("TopBorder", start + outer_width / 2, FRAME_TOP - BORDER / 2, width, BORDER),
    )
    for part, y, z, length, height in parts:
        workcell_furniture.static_box(
            stage,
            GROUP + "/" + name + "/" + part,
            (THICKNESS / 2, y, z),
            (THICKNESS, length, height),
            paint,
        )
    workcell_furniture.static_box(
        stage,
        GROUP + "/" + name + "/Pane",
        (THICKNESS / 2, start + outer_width / 2, GLASS_BOTTOM + GLASS_HEIGHT / 2),
        (GLASS_THICKNESS, width, GLASS_HEIGHT),
        glass,
    )


def build(stage, table2: dict) -> dict:
    """Attach the end block and glazed wall using Table2's measured frame."""
    b, u, v = workcell_furniture.frame(table2["corners_m"])
    anchor = (
        b - u * (4 + END_WIDTH) + v * (END_DEPTH - workcell_furniture.BOARD_THICKNESS)
    )
    room = UsdGeom.Xform.Define(stage, GROUP)
    room.AddTranslateOp().Set(anchor)
    room.AddRotateZOp().Set(table2["yaw_deg"])
    paint = UsdShade.Material(stage.GetPrimAtPath(workcell_furniture.GROUP + "/Paint"))
    glass_material(stage)
    solids = (
        (
            "EndWall",
            (END_WIDTH / 2, -END_DEPTH / 2, HEIGHT / 2),
            (END_WIDTH, END_DEPTH, HEIGHT),
        ),
        (
            "SillWall",
            (THICKNESS / 2, OPENINGS_LENGTH / 2, FRAME_BOTTOM / 2),
            (THICKNESS, OPENINGS_LENGTH, FRAME_BOTTOM),
        ),
        (
            "HeaderWall",
            (THICKNESS / 2, OPENINGS_LENGTH / 2, (FRAME_TOP + HEIGHT) / 2),
            (THICKNESS, OPENINGS_LENGTH, HEIGHT - FRAME_TOP),
        ),
        (
            "FarWall",
            (THICKNESS / 2, (OPENINGS_LENGTH + LENGTH) / 2, HEIGHT / 2),
            (THICKNESS, FAR_WALL_LENGTH, HEIGHT),
        ),
    )
    for name, center, dimensions in solids:
        workcell_furniture.static_box(
            stage, GROUP + "/" + name, center, dimensions, paint
        )
    start = 0.0
    for index, width in enumerate(GLASS_WIDTHS, start=1):
        window(stage, "Window" + str(index), (start, width), paint)
        start += width + 2 * BORDER
    return {
        "prim_path": GROUP,
        "anchor_m": list(anchor),
        "yaw_deg": table2["yaw_deg"],
        "extension_direction": "Table2 B-to-C (+v); table side",
        "wall_length_m": LENGTH,
        "wall_height_m": HEIGHT,
        "wall_thickness_m": THICKNESS,
        "end_wall_footprint_m": [END_WIDTH, END_DEPTH],
        "glass_clear_widths_m": list(GLASS_WIDTHS),
        "glass_bottom_m": GLASS_BOTTOM,
        "glass_height_m": GLASS_HEIGHT,
        "glass_thickness_m": GLASS_THICKNESS,
        "frame_border_m": BORDER,
        "between_frames_gap_m": 0,
        "far_solid_wall_length_m": FAR_WALL_LENGTH,
        "runtime_dependency": GLASS_MDL,
    }


def bounds_in_room(stage, path: str) -> Gf.Range3d:
    """Measure exact box corners; aggregate BBoxes overestimate rotated groups."""
    transforms = UsdGeom.XformCache()
    inverse = transforms.GetLocalToWorldTransform(
        stage.GetPrimAtPath(GROUP)
    ).GetInverse()
    bounds = Gf.Range3d()
    for prim in Usd.PrimRange(stage.GetPrimAtPath(path)):
        if not prim.IsA(UsdGeom.Cube):
            continue
        half = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2
        matrix = transforms.GetLocalToWorldTransform(prim) * inverse
        for x in (-half, half):
            for y in (-half, half):
                for z in (-half, half):
                    bounds.UnionWith(matrix.Transform(Gf.Vec3d(x, y, z)))
    return bounds


# Keep related composed measurements visible in a single acceptance pass.
# pylint: disable-next=too-many-locals
def validate(stage, table2: dict) -> dict:
    """Measure contiguous openings and reject wall geometry behind the glass."""
    room = stage.GetPrimAtPath(GROUP)
    assert room
    b, u, v = workcell_furniture.frame(table2["corners_m"])
    matrix = UsdGeom.XformCache().GetLocalToWorldTransform(room)
    assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, 1, 0)), v) > 0.99999
    assert abs(Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, 1, 0)), u)) < 1e-6
    start = matrix.ExtractTranslation()
    assert abs(Gf.Dot(start - b, u) + 4 + END_WIDTH) < 1e-6
    assert (
        abs(Gf.Dot(start - b, v) - (END_DEPTH - workcell_furniture.BOARD_THICKNESS))
        < 1e-6
    )
    boxes = [p for p in Usd.PrimRange(room) if p.IsA(UsdGeom.Cube)]
    assert len(boxes) == 14
    assert all(
        UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get() for p in boxes
    )
    assert all(not p.HasAPI(UsdPhysics.RigidBodyAPI) for p in boxes)
    end = bounds_in_room(stage, GROUP + "/EndWall")
    assert abs(end.GetMax()[1]) < 1e-6
    assert abs(end.GetMin()[0]) < 1e-6
    intervals = []
    for index, width in enumerate(GLASS_WIDTHS, start=1):
        path = GROUP + "/Window" + str(index)
        pane = bounds_in_room(stage, path + "/Pane")
        low, high = pane.GetMin(), pane.GetMax()
        assert abs(low[2] - GLASS_BOTTOM) < 1e-6
        assert abs(high[2] - (GLASS_BOTTOM + GLASS_HEIGHT)) < 1e-6
        assert abs(low[0] - 0.03) < 1e-6 and abs(high[0] - 0.05) < 1e-6
        assert abs(high[1] - low[1] - width) < 1e-6
        frame = bounds_in_room(stage, path)
        assert abs(frame.GetMin()[2] - FRAME_BOTTOM) < 1e-6
        assert abs(frame.GetMax()[2] - FRAME_TOP) < 1e-6
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
        assert str(material.GetPath()) == GROUP + "/Glass"
    assert abs(intervals[0][0]) < 1e-6
    assert abs(intervals[0][1] - intervals[1][0]) < 1e-6
    far = bounds_in_room(stage, GROUP + "/FarWall")
    assert abs(far.GetMin()[1] - intervals[1][1]) < 1e-6
    assert abs(far.GetMax()[1] - LENGTH) < 1e-6
    shader = UsdShade.Shader(stage.GetPrimAtPath(GROUP + "/Glass/OmniGlass"))
    assert shader.GetSourceAsset("mdl").path == GLASS_MDL
    assert shader.GetInput("thin_walled").Get() is True
    return {
        "status": "PASS",
        "static_colliders": len(boxes),
        "frames_touch": True,
        "glass_clear_of_opaque_boxes": True,
        "far_solid_length_m": far.GetSize()[1],
        "anchor_m": list(start),
    }
