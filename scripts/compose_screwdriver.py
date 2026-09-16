"""Compose a screwdriver workcell as a layer over the existing HOME scene."""

import json
import pathlib

# OpenUSD is supplied by the Ubuntu Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdUtils

# pylint: enable=import-error


def build(root: pathlib.Path) -> dict:
    """Place the source-sized tool on the table without running dynamics."""
    directory = root / "scenes/tabletop_screwdriver"
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / "scene.usda"
    stage = Usd.Stage.CreateNew(str(output))
    stage.GetRootLayer().subLayerPaths = ["../tabletop_home/scene.usda"]
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    stage.SetMetadataByDictKey(
        "customLayerData", "cameraSettings:boundCamera", "/World/Camera"
    )
    stage.SetMetadataByDictKey(
        "customLayerData",
        "purpose",
        "HOME workcell with a nominal Husky screwdriver",
    )
    prop = UsdGeom.Xform.Define(stage, "/World/Props/HuskyScrewdriver")
    prop.GetPrim().GetReferences().AddReference(
        "../../assets/props/husky_screwdriver/husky_screwdriver.usdc"
    )
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), ["default", "render", "proxy"]
    )
    source_bounds = cache.ComputeWorldBound(
        prop.GetPrim()
    ).ComputeAlignedRange()
    table_bounds = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/Table/Top")
    ).ComputeAlignedRange()
    position = Gf.Vec3d(
        1.42, 0.70, table_bounds.GetMax()[2] - source_bounds.GetMin()[2] + 0.001
    )
    prop.AddTranslateOp().Set(position)
    prop.AddRotateZOp().Set(25)
    stage.GetRootLayer().Save()
    report = validate(output)
    report.update(
        position_m=list(position),
        yaw_deg=25,
        support_clearance_m=0.001,
        source_dimensions_m=list(source_bounds.GetSize()),
        dimension_status="Source estimate, approximately 100 mm; not measured",
        physics_contact_test="NOT RUN",
    )
    (directory / "placement.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def validate(path: pathlib.Path) -> dict:
    """Check relocated dependencies, enabled colliders and table support."""
    stage = Usd.Stage.Open(str(path))
    layers, _, unresolved = UsdUtils.ComputeAllDependencies(str(path))
    if unresolved:
        raise ValueError(f"Unresolved USD assets: {unresolved}")
    for layer in layers:
        if any(
            pathlib.Path(asset).is_absolute()
            for asset in layer.GetExternalReferences()
        ):
            raise ValueError(f"Absolute USD reference in {layer.identifier}")
    prop = stage.GetPrimAtPath("/World/Props/HuskyScrewdriver")
    assert UsdPhysics.RigidBodyAPI(prop).GetRigidBodyEnabledAttr().Get()
    colliders = [
        p for p in Usd.PrimRange(prop) if p.HasAPI(UsdPhysics.CollisionAPI)
    ]
    assert colliders and all(
        UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()
        for p in colliders
    )
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), ["default", "render", "proxy"]
    )
    bounds = cache.ComputeWorldBound(prop).ComputeAlignedRange()
    table = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/Table/Top")
    ).ComputeAlignedRange()
    for axis in (0, 1):
        assert (
            table.GetMin()[axis]
            < bounds.GetMin()[axis]
            < bounds.GetMax()[axis]
            < table.GetMax()[axis]
        )
    assert abs(bounds.GetMin()[2] - table.GetMax()[2] - 0.001) < 1e-6
    assert (
        stage.GetMetadataByDictKey(
            "customLayerData", "cameraSettings:boundCamera"
        )
        == "/World/Camera"
    )
    assert stage.GetPrimAtPath("/World/UR12e") and stage.GetPrimAtPath(
        "/World/HandE"
    )
    return {
        "scene": "tabletop_screwdriver",
        "asset_colliders": len(colliders),
        "validation": "PASS",
    }


if __name__ == "__main__":
    print(
        json.dumps(build(pathlib.Path(__file__).resolve().parents[1]), indent=2)
    )
