"""Standalone PBR and Thin Walled glass authoring with USD fallbacks."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdShade

# pylint: enable=import-error

PBR_MDL = "OmniPBR.mdl"
GLASS_MDL = "OmniGlass.mdl"


def surface_material(
    stage: Usd.Stage, path: str, color: tuple, roughness: float, metallic: float
) -> UsdShade.Material:
    """Author a shared PBR material with a portable USD fallback."""
    material = UsdShade.Material.Define(stage, path)
    mdl = UsdShade.Shader.Define(stage, path + "/OmniPBR")
    mdl.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    mdl.SetSourceAsset(PBR_MDL, "mdl")
    mdl.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    mdl.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*color)
    )
    mdl.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(
        roughness
    )
    mdl.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(metallic)
    material.CreateSurfaceOutput("mdl").ConnectToSource(mdl.ConnectableAPI(), "out")
    preview = UsdShade.Shader.Define(stage, path + "/Preview")
    preview.CreateIdAttr("UsdPreviewSurface")
    preview.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*color)
    )
    preview.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    if metallic:
        preview.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    material.CreateSurfaceOutput().ConnectToSource(preview.ConnectableAPI(), "surface")
    return material


def paint_material(stage: Usd.Stage, path: str) -> UsdShade.Material:
    """Share the accepted matte white paint specification."""
    return surface_material(stage, path, (0.85, 0.85, 0.85), 0.9, 0)


def glass_material(stage: Usd.Stage, path: str) -> UsdShade.Material:
    """Create thin-walled clear glass using the installed Isaac MDL."""
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
