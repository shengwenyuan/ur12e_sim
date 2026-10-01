"""Build the portable Versteel workcell and its physical red PLA cube."""

import argparse
import hashlib
import json
import math
import pathlib

# OpenUSD is provided by the independent Isaac/USD environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, UsdUtils

# pylint: enable=import-error

import compose_scene

SCENE = "versteel_box_pick_place"
LENGTH, WIDTH, HEIGHT = 1.8288, 0.762, 0.85
NATIVE_HEIGHT = 0.8128
EDGE, DENSITY = 0.03, 1240.0
BACK_GAP, BASE_GAP = 0.235, 0.9
BASE_FROM_CORNER = LENGTH - BACK_GAP - 0.047 / 2 - BASE_GAP
RIGHT_EDGE = LENGTH - BASE_FROM_CORNER


def cube_asset(root: pathlib.Path) -> pathlib.Path:
    """Author a solid nominal PLA cube with a real rigid body and collider."""
    directory = root / "assets/props/red_cube"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "red_cube.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, "Z")
    body = UsdGeom.Xform.Define(stage, "/RedCube").GetPrim()
    stage.SetDefaultPrim(body)
    UsdPhysics.RigidBodyAPI.Apply(body).CreateRigidBodyEnabledAttr(True)
    mass = DENSITY * EDGE**3
    api = UsdPhysics.MassAPI.Apply(body)
    api.CreateMassAttr(mass)
    api.CreateCenterOfMassAttr(Gf.Vec3f(0))
    api.CreateDiagonalInertiaAttr(Gf.Vec3f(mass * EDGE**2 / 6))
    shape = UsdGeom.Cube.Define(stage, "/RedCube/Shape")
    shape.CreateSizeAttr(EDGE)
    shape.CreateDisplayColorAttr([Gf.Vec3f(0.75, 0.008, 0.008)])
    UsdPhysics.CollisionAPI.Apply(shape.GetPrim()).CreateCollisionEnabledAttr(
        True
    )
    material = UsdShade.Material.Define(stage, "/RedCube/Material")
    shader = UsdShade.Shader.Define(stage, "/RedCube/Material/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    from pxr import Sdf  # pylint: disable=import-outside-toplevel,import-error

    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0.75, 0.008, 0.008)
    )
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.6)
    material.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )
    UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(material)
    physics = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics.CreateStaticFrictionAttr(0.5)
    physics.CreateDynamicFrictionAttr(0.4)
    physics.CreateRestitutionAttr(0)
    UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(
        material, materialPurpose="physics"
    )
    stage.GetRootLayer().Save()
    (directory / "asset.json").write_text(
        json.dumps(
            {
                "name": "red_cube",
                "edge_m": EDGE,
                "mass_kg": mass,
                "density_kg_m3": DENSITY,
                "material": "solid PLA, assumed 100% infill",
                "mass_status": "estimated, not weighed",
                "source": (
                    "https://prusament.com/wp-content/uploads/2022/10/"
                    "PLA_Prusament_TDS_2021_10_EN.pdf"
                ),
                "inertia_kg_m2": [mass * EDGE**2 / 6] * 3,
                "friction_status": "provisional",
                "origin": "cube center",
            },
            indent=2,
        )
        + "\n"
    )
    return path


def place(
    stage,
    name: str,
    asset: pathlib.Path,
    position: tuple,
    yaw: float = 0,
):
    """Place one referenced component without scaling its original geometry."""
    prim = compose_scene.reference(
        stage, name, asset, pathlib.Path(stage.GetRootLayer().realPath)
    )
    matrix = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), yaw))
    matrix.SetTranslateOnly(Gf.Vec3d(*position))
    UsdGeom.Xformable(prim).MakeMatrixXform().Set(matrix)
    return prim


# The workcell builder keeps its component placements together.
# pylint: disable-next=too-many-locals
def build(root: pathlib.Path, collection_root: pathlib.Path) -> dict:
    """Validate collection HOME and apply the saved tabletop placement."""
    layout = json.loads((root / "scenes/tabletop_home/layout.json").read_text())
    compose_scene.check_home(collection_root, layout["robot"]["home_deg"])
    source = collection_root / "src/ur12e_collection/simulation/profile.py"
    layout["robot"]["home_source_sha256"] = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    height = HEIGHT
    output = root / "scenes" / SCENE / "scene.usda"
    output.parent.mkdir(parents=True, exist_ok=True)
    cube = cube_asset(root)
    stage = Usd.Stage.CreateNew(str(output))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, "Z")
    stage.SetMetadataByDictKey(
        "customLayerData", "cameraSettings:boundCamera", "/World/Camera"
    )
    table = root / "assets/furniture/versteel_table_3072/isaac/table_fixed.usda"
    fixture = place(
        stage, "/World/Table", table, (LENGTH / 2 - BASE_FROM_CORNER, 0, 0)
    )
    transform = UsdGeom.Xformable(fixture)
    matrix = transform.GetLocalTransformation()
    transform.MakeMatrixXform().Set(
        Gf.Matrix4d().SetScale(Gf.Vec3d(1, 1, height / NATIVE_HEIGHT)) * matrix
    )
    box_x = BASE_GAP
    layout["scene_id"] = SCENE
    layout["description"] = (
        "Static Versteel HOME with open carton and physical red cube"
    )
    layout["table"] = {
        "length_m": LENGTH,
        "width_m": WIDTH,
        "top_surface_height_m": height,
        "native_top_surface_height_m": NATIVE_HEIGHT,
        "scene_vertical_scale": height / NATIVE_HEIGHT,
    }
    layout["world"] = {
        "origin": "Floor directly below the robot mounting base",
        "x_axis": "Table length; positive from base toward carton",
        "y_axis": "Left while looking along +X",
        "z_axis": "up",
    }
    layout["robot"]["base_position_m"] = [0, 0, height]
    layout["robot"]["base_yaw_rad"] = -math.pi
    layout["robot"][
        "yaw_policy"
    ] = "Fixed -180 degrees; retain natural TCP offset"
    layout["robot"]["base_yaw_rad"], tcp = compose_scene.place_robot(
        stage, root, layout, output
    )
    layout["tcp_layout_goal"] = {
        "position_m": list(tcp.ExtractTranslation()),
        "source": "nominal HOME FK",
    }
    box = root / "assets/props/open_dynamixel_box/isaac/open_cube_carton.usdc"
    place(
        stage,
        "/World/Props/OpenDynamixelBox",
        box,
        (box_x, 0, height + 0.001),
        -90,
    )
    position = (
        1.280 - BASE_FROM_CORNER,
        0.400 - WIDTH / 2,
        height + EDGE / 2 + 0.001,
    )
    cube_yaw = 173.62582178591697  # Retained from the original seed-3072 pose.
    place(stage, "/World/Props/RedCube", cube, position, cube_yaw)
    layout["props"] = {
        "box_body_center_m": [box_x, 0, height + 0.001],
        "box_yaw_deg": -90,
        "back_plane_x_m": RIGHT_EDGE - BACK_GAP,
        "back_to_short_edge_m": BACK_GAP,
        "base_to_box_center_xy_m": BASE_GAP,
        "cube_position_m": list(position),
        "cube_yaw_deg": cube_yaw,
        "original_yaw_seed": 3072,
        "position_policy": "user-refined XY; original seeded yaw retained",
        "support_clearance_m": 0.001,
    }
    environment(stage)
    layout["background"] = {"mode": "none", "lighting": "neutral"}
    stage.GetRootLayer().Save()
    (output.parent / "layout.json").write_text(
        json.dumps(layout, indent=2) + "\n"
    )
    report = validate(output)
    (output.parent / "scene-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    return report


def environment(stage) -> None:
    """Add a visible support floor, neutral lights and the saved observer."""
    floor = UsdGeom.Cube.Define(stage, "/World/Floor")
    floor.CreateSizeAttr(1)
    floor.AddTranslateOp().Set(Gf.Vec3d(0, 0, -0.01))
    floor.AddScaleOp().Set(Gf.Vec3f(12, 12, 0.02))
    UsdPhysics.CollisionAPI.Apply(floor.GetPrim())
    dome = UsdLux.DomeLight.Define(stage, "/World/Environment")
    dome.CreateIntensityAttr(800)
    dome.CreateColorAttr(Gf.Vec3f(0.5))
    sun = UsdLux.DistantLight.Define(stage, "/World/Key")
    sun.CreateIntensityAttr(1800)
    sun.AddRotateXYZOp().Set(Gf.Vec3f(-35, -25, 20))
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(9.81)
    height_delta = HEIGHT - NATIVE_HEIGHT
    camera = UsdGeom.Camera.Define(stage, "/World/Camera")
    camera.CreateFocalLengthAttr(27)
    camera.AddTransformOp().Set(
        Gf.Matrix4d()
        .SetLookAt(
            Gf.Vec3d(
                1.04 - BASE_FROM_CORNER, WIDTH / 2 + 3.2, 2.2 + height_delta
            ),
            Gf.Vec3d(1.04 - BASE_FROM_CORNER, 0, 1.25 + height_delta),
            Gf.Vec3d(0, 0, 1),
        )
        .GetInverse()
    )


def validate(path: pathlib.Path) -> dict:
    """Check physical layout, stable initialization and portable references."""
    stage = Usd.Stage.Open(str(path))
    layers, _, unresolved = UsdUtils.ComputeAllDependencies(str(path))
    assert not unresolved, unresolved
    assert not any(
        pathlib.Path(ref).is_absolute()
        for layer in layers
        for ref in layer.GetExternalReferences()
    )
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), ["default", "render", "proxy"]
    )
    table = stage.GetPrimAtPath("/World/Table")
    assert not UsdPhysics.RigidBodyAPI(table).GetRigidBodyEnabledAttr().Get()
    top = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/Table/Visuals/Tabletop")
    ).ComputeAlignedRange()
    layout = json.loads((path.parent / "layout.json").read_text())
    assert abs(top.GetMax()[2] - layout["table"]["top_surface_height_m"]) < 1e-5
    box = stage.GetPrimAtPath("/World/Props/OpenDynamixelBox")
    transforms = UsdGeom.XformCache()
    matrix = transforms.GetLocalToWorldTransform(box)
    back = matrix.Transform(Gf.Vec3d(0, 0.047 / 2, 0))
    assert abs(RIGHT_EDGE - back[0] - BACK_GAP) < 1e-6
    assert matrix.TransformDir(Gf.Vec3d(0, 1, 0))[0] > 0.999
    center = matrix.ExtractTranslation()
    assert abs(center[1]) < 1e-8
    base = layout["robot"]["base_position_m"]
    assert abs(math.dist(base[:2], list(center)[:2]) - BASE_GAP) < 1e-8
    counts = supported_components(stage, cache)
    return {
        "static_validation": "PASS",
        "colliders": counts,
        "back_gap_m": RIGHT_EDGE - back[0],
        "base_box_distance_m": BASE_GAP,
        "red_cube_mass_kg": DENSITY * EDGE**3,
        "render_validation": "NOT RUN",
        "settle_validation": "NOT RUN",
    }


def supported_components(stage, cache) -> dict:
    """Verify rigid props rest over the tabletop and keep enabled colliders."""
    table, box, cube = (
        stage.GetPrimAtPath(path)
        for path in (
            "/World/Table",
            "/World/Props/OpenDynamixelBox",
            "/World/Props/RedCube",
        )
    )
    top = cache.ComputeWorldBound(
        stage.GetPrimAtPath("/World/Table/Visuals/Tabletop")
    ).ComputeAlignedRange()
    counts = {}
    for prim in (table, box, cube):
        bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if prim != table:
            assert abs(bounds.GetMin()[2] - top.GetMax()[2] - 0.001) < 1e-5
            for axis in (0, 1):
                assert top.GetMin()[axis] < bounds.GetMin()[axis]
                assert bounds.GetMax()[axis] < top.GetMax()[axis]
            assert UsdPhysics.RigidBodyAPI(prim).GetRigidBodyEnabledAttr().Get()
        counts[prim.GetName()] = sum(
            p.HasAPI(UsdPhysics.CollisionAPI) for p in Usd.PrimRange(prim)
        )
        assert counts[prim.GetName()] > 0
    assert (
        abs(UsdPhysics.MassAPI(cube).GetMassAttr().Get() - DENSITY * EDGE**3)
        < 1e-8
    )
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(
                pathlib.Path(__file__).resolve().parents[1],
                args.collection_root,
            ),
            indent=2,
        )
    )
