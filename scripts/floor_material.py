"""Apply the procedural floor finish only within the room perimeter."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

# pylint: enable=import-error

from wall_layout import FURNITURE

MATERIAL_PATH = "/World/FloorMaterial"
MDL_ASSET = "../../assets/materials/terrazzo.mdl"
BASE_COLOR = (0.14, 0.15, 0.14)


def room_outline(stage: Usd.Stage, layout: dict) -> list[Gf.Vec3f]:
    """Follow existing wall endpoints, closing the open side with one segment."""
    room = layout["room_extension"]
    glass = layout["chair_side_glass"]
    cache = UsdGeom.XformCache()
    room_frame = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(room["prim_path"]))
    glass_frame = cache.GetLocalToWorldTransform(
        stage.GetPrimAtPath(glass["prim_path"])
    )
    back = room_frame.Transform(
        Gf.Vec3d(room["wall_thickness_m"] / 2, -room["end_wall_footprint_m"][1], 0)
    )
    start = Gf.Vec3d(*glass["anchor_m"])
    # The short painted return connects the glass start to the back wall.
    direction = glass_frame.TransformDir(Gf.Vec3d(0, 1, 0))
    corner = start - direction * (glass["centerline_v_m"] + FURNITURE.board_thickness)
    points = [back, corner, start]
    points.extend(
        glass_frame.Transform(Gf.Vec3d(*pose["end_m"]))
        for pose in glass["unit_poses_local"]
    )
    points.append(
        room_frame.Transform(
            Gf.Vec3d(room["wall_thickness_m"] / 2, room["wall_length_m"], 0)
        )
    )
    return [Gf.Vec3f(point[0], point[1], 0.0002) for point in points]


def build(stage: Usd.Stage, layout: dict) -> dict:
    """Bind a single interior polygon, retaining the plain support collider."""
    material = UsdShade.Material.Define(stage, MATERIAL_PATH)
    shader = UsdShade.Shader.Define(stage, MATERIAL_PATH + "/Terrazzo")
    shader.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    shader.SetSourceAsset(MDL_ASSET, "mdl")
    shader.SetSourceAssetSubIdentifier("terrazzo", "mdl")
    for name, value in (
        ("cell_size_m", 0.004),
        ("coverage", 0.20),
        ("roughness", 0.75),
    ):
        shader.CreateInput(name, Sdf.ValueTypeNames.Float).Set(value)
    shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*BASE_COLOR)
    )
    material.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
    preview = UsdShade.Shader.Define(stage, MATERIAL_PATH + "/Preview")
    preview.CreateIdAttr("UsdPreviewSurface")
    preview.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*BASE_COLOR)
    )
    preview.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.75)
    material.CreateSurfaceOutput().ConnectToSource(preview.ConnectableAPI(), "surface")
    floor = stage.GetPrimAtPath("/World/Floor")
    floor.RemoveProperty("material:binding")
    floor.RemoveAPI(UsdShade.MaterialBindingAPI)
    points = room_outline(stage, layout)
    finish = UsdGeom.Mesh.Define(stage, "/World/RoomFloor")
    finish.CreatePointsAttr(points)
    finish.CreateFaceVertexCountsAttr([len(points)])
    finish.CreateFaceVertexIndicesAttr(list(range(len(points))))
    finish.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    finish.CreateDoubleSidedAttr(True)
    UsdShade.MaterialBindingAPI.Apply(finish.GetPrim()).Bind(material)
    return {
        "prim_path": "/World/RoomFloor",
        "material_scope": "room interior only",
        "boundary_xy_m": [[float(point[0]), float(point[1])] for point in points],
        "height_m": 0.0002,
        "opening_closure": "straight segment between wall endpoints; no added wall",
        "collision": "existing /World/Floor only; finish is visual",
    }
