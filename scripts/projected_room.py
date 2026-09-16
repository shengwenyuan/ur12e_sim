"""Project an LDR panorama onto finite, approximate room surfaces."""

import json
import math
import pathlib

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade


def load(path: pathlib.Path) -> dict:
    """Reject invalid room/capture geometry before authoring any USD."""
    settings = json.loads(path.read_text())
    origin = settings["capture_position_m"]
    bounds = settings["bounds_m"]
    if len(origin) != 3 or settings["mesh_spacing_m"] <= 0:
        raise ValueError("Capture requires XYZ and positive mesh spacing")
    for axis, coordinate in zip("xyz", origin):
        lower, upper = bounds[axis]
        if not all(math.isfinite(v) for v in (lower, upper, coordinate)):
            raise ValueError("Room coordinates must be finite")
        if not lower < coordinate < upper:
            raise ValueError(
                f"Capture point must lie inside the {axis} bounds"
            )
    if not bounds["z"][0] < settings["table_height_m"] < bounds["z"][1]:
        raise ValueError("Tabletop must lie between floor and ceiling")
    return settings


def texture_uv(point: tuple, settings: dict) -> tuple[float, float]:
    """Map a fixed world point to USD ST; +X is center and +Y is image-left."""
    x, y, z = (p - c for p, c in zip(point, settings["capture_position_m"]))
    yaw = math.radians(settings["projection_yaw_deg"])
    forward = math.cos(yaw) * x + math.sin(yaw) * y
    left = -math.sin(yaw) * x + math.cos(yaw) * y
    radius = math.sqrt(x * x + y * y + z * z)
    if radius == 0:
        raise ValueError("A surface cannot pass through the capture origin")
    return (
        0.5 - math.atan2(left, forward) / (2 * math.pi),
        0.5 + math.asin(max(-1.0, min(1.0, z / radius))) / math.pi,
    )


def surfaces(settings: dict) -> list[tuple]:
    """Return rectangles with their front faces pointing into the room."""
    (x0, x1), (y0, y1), (z0, z1) = (
        settings["bounds_m"][axis] for axis in "xyz"
    )
    return [
        ("WoodWall", (x1, y1, z0), (0, y0 - y1, 0), (0, 0, z1 - z0)),
        ("Blinds", (x1, y0, z0), (x0 - x1, 0, 0), (0, 0, z1 - z0)),
        ("LeftBoundary", (x0, y1, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0)),
        ("RearBoundary", (x0, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0)),
        ("Floor", (x0, y0, z0), (x1 - x0, 0, 0), (0, y1 - y0, 0)),
        ("Ceiling", (x0, y1, z1), (x1 - x0, 0, 0), (0, y0 - y1, 0)),
    ]


def photographic_material(stage, texture: str):
    """Use sRGB pixels without diffuse or specular relighting."""
    material = UsdShade.Material.Define(stage, "/LabBackground/Material")
    reader = UsdShade.Shader.Define(
        stage, "/LabBackground/Material/Coordinates"
    )
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    image = UsdShade.Shader.Define(stage, "/LabBackground/Material/Image")
    image.CreateIdAttr("UsdUVTexture")
    image.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture)
    image.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    image.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
    image.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("clamp")
    image.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.ConnectableAPI(), "result"
    )
    image.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    shader = UsdShade.Shader.Define(stage, "/LabBackground/Material/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0)
    )
    shader.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(1)
    shader.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0)
    )
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1)
    shader.CreateInput(
        "emissiveColor", Sdf.ValueTypeNames.Color3f
    ).ConnectToSource(image.ConnectableAPI(), "rgb")
    material.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )
    return material


def author_surface(stage, surface: tuple, settings: dict, material) -> int:
    """Tessellate projection and unwrap ST across the longitude seam."""
    # pylint: disable=too-many-locals
    name, origin, along, across = surface
    spacing = settings["mesh_spacing_m"]
    columns = math.ceil(math.sqrt(sum(v * v for v in along)) / spacing)
    rows = math.ceil(math.sqrt(sum(v * v for v in across)) / spacing)
    points = [
        tuple(
            origin[k] + along[k] * column / columns + across[k] * row / rows
            for k in range(3)
        )
        for row in range(rows + 1)
        for column in range(columns + 1)
    ]
    coordinates = [texture_uv(point, settings) for point in points]
    indices, uv = [], []
    for row in range(rows):
        for column in range(columns):
            a = row * (columns + 1) + column
            for face in (
                (a, a + 1, a + columns + 2),
                (a, a + columns + 2, a + columns + 1),
            ):
                st = [coordinates[index] for index in face]
                if max(u for u, _ in st) - min(u for u, _ in st) > 0.5:
                    st = [(u + 1 if u < 0.5 else u, v) for u, v in st]
                indices.extend(face)
                uv.extend(Gf.Vec2f(*pair) for pair in st)
    mesh = UsdGeom.Mesh.Define(stage, "/LabBackground/" + name)
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr([3] * (len(indices) // 3))
    mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateSubdivisionSchemeAttr("none")
    mesh.CreateDoubleSidedAttr(True)
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying
    ).Set(uv)
    mesh.GetPrim().CreateAttribute(
        "primvars:doNotCastShadows", Sdf.ValueTypeNames.Bool
    ).Set(True)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return len(indices) // 3


def build(path: pathlib.Path, settings: dict) -> dict:
    """Save fixed photographic geometry without collision or tracking."""
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, "/LabBackground").GetPrim()
    stage.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, "Z")
    root.SetCustomDataByKey("depthSemantics", settings["depth_semantics"])
    root.SetCustomDataByKey(
        "measurementStatus", settings["measurement_status"]
    )
    material = photographic_material(stage, settings["texture"])
    triangles = sum(
        author_surface(stage, plane, settings, material)
        for plane in surfaces(settings)
    )
    stage.GetRootLayer().Save()
    return {
        **settings,
        "representation": "fixed finite room with baked panorama ST",
        "entrypoint": path.name,
        "triangles": triangles,
        "collision": False,
        "hardware_control": False,
        "render_validation": "NOT RUN",
    }
