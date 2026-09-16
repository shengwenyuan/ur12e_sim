"""Author the user-aligned table layout without robot or physics interfaces."""

import argparse
import json
import pathlib

# OpenUSD is provided by the existing Ubuntu Isaac environment.
from pxr import Gf, Usd, UsdGeom, UsdLux  # pylint: disable=import-error


def cube(stage, path, position, scale, color):
    """Place a meter-scale box by its center and full dimensions."""
    shape = UsdGeom.Cube.Define(stage, path)
    shape.CreateSizeAttr(1)
    shape.AddTranslateOp().Set(Gf.Vec3d(*position))
    shape.AddScaleOp().Set(Gf.Vec3f(*scale))
    shape.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    return shape


def marker(stage, path, xy, top, color):
    """Mark a layout position on the surface, not a measured TCP height."""
    shape = UsdGeom.Cylinder.Define(stage, path)
    shape.CreateRadiusAttr(0.055)
    shape.CreateHeightAttr(0.012)
    shape.CreateAxisAttr("Z")
    shape.AddTranslateOp().Set(Gf.Vec3d(*xy, top + 0.006))
    shape.CreateDisplayColorAttr([Gf.Vec3f(*color)])


def table_geometry(stage, length, width, top):
    """Keep the illustrative legs and thickness below the given top height."""
    thickness = 0.05
    tabletop = cube(
        stage,
        "/World/Table/Top",
        (length / 2, width / 2, top - thickness / 2),
        (length, width, thickness),
        (0.38, 0.28, 0.18),
    )
    leg_height = top - thickness
    for index, (x, y) in enumerate(
        ((x, y) for x in (0.09, length - 0.09) for y in (0.09, width - 0.09))
    ):
        cube(
            stage,
            f"/World/Table/Leg{index}",
            (x, y, leg_height / 2),
            (0.07, 0.07, leg_height),
            (0.12, 0.14, 0.17),
        )
    return tabletop


def build(layout_path, destination):
    """Save a self-contained table-only USD and verify its top surface."""
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    table = layout["table"]
    length, width, top = (
        table[key] for key in ("length_m", "width_m", "top_surface_height_m")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(destination))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().customLayerData = {
        "purpose": "Table layout render check; robot meshes are not loaded",
        "robot_control": False,
        "physics_integration": False,
    }
    tabletop = table_geometry(stage, length, width, top)
    cube(
        stage,
        "/World/Floor",
        (length / 2, width / 2, -0.01),
        (8, 6, 0.02),
        (0.12, 0.14, 0.17),
    )
    marker(
        stage,
        "/World/BasePosition",
        layout["robot"]["base_position_m"][:2],
        top,
        (0.1, 0.7, 0.3),
    )
    marker(
        stage,
        "/World/TcpXYGuide",
        layout["tcp_layout_goal"]["xy_m"],
        top,
        (1.0, 0.45, 0.08),
    )
    dome = UsdLux.DomeLight.Define(stage, "/World/Lighting/Sky")
    dome.CreateIntensityAttr(600)
    sun = UsdLux.DistantLight.Define(stage, "/World/Lighting/Sun")
    sun.CreateIntensityAttr(2500)
    UsdGeom.Xformable(sun).AddRotateXYZOp().Set(Gf.Vec3f(315, 0, 35))
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100))
    camera.CreateFocalLengthAttr(28)
    view = Gf.Matrix4d().SetLookAt(
        Gf.Vec3d(3.6, -3.2, 3.0),
        Gf.Vec3d(length / 2, width / 2, top * 0.7),
        Gf.Vec3d(0, 0, 1),
    )
    camera.AddTransformOp().Set(view.GetInverse())
    stage.GetRootLayer().Save()
    bounds = (
        UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default"])
        .ComputeWorldBound(tabletop.GetPrim())
        .ComputeAlignedRange()
    )
    assert abs(bounds.GetMax()[2] - top) < 1e-6
    reloaded = Usd.Stage.Open(str(destination))
    assert reloaded.GetPrimAtPath("/World/Camera")
    return {
        "stage": str(destination),
        "table_top_z_m": bounds.GetMax()[2],
        "robot_meshes_loaded": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(build(args.layout, args.output)))
