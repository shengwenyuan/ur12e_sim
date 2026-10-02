"""Bind a small world-meter procedural floor shader without changing geometry."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdShade

# pylint: enable=import-error

MATERIAL_PATH = "/World/FloorMaterial"
MDL_ASSET = "../../assets/materials/terrazzo.mdl"
BASE_COLOR = (0.14, 0.15, 0.14)


def build(stage: Usd.Stage) -> None:
    """Apply metric color grains and a plain fallback to the existing floor."""
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
    UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath("/World/Floor")).Bind(
        material
    )
