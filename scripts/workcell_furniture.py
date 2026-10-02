"""Compose static Table2 furniture in its measured tabletop frame."""

import pathlib

# OpenUSD comes from the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

import compose_scene

BOARD_WIDTH, BOARD_HEIGHT, BOARD_THICKNESS = 2.0, 2.5, 0.018
WALL_HEIGHT, WALL_THICKNESS, SHORT_WALL_LENGTH = 3.0, 0.14605, 0.682
GROUP = "/World/Furniture"
BUILTIN_MDL = "OmniPBR.mdl"


def frame(corners: dict) -> tuple:
    """Return B and unit vectors A-to-B / B-to-C in the world XY plane."""
    a, b, c = (Gf.Vec3d(*corners[key]) for key in ("A", "B", "C"))
    b[2] = a[2] = c[2] = 0
    return b, (b - a).GetNormalized(), (c - b).GetNormalized()


def wall_material(stage):
    """Bind white matte paint using Isaac's built-in MDL and USD fallback."""
    path = GROUP + "/Paint"
    material = UsdShade.Material.Define(stage, path)
    mdl = UsdShade.Shader.Define(stage, path + "/OmniPBR")
    mdl.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
    mdl.SetSourceAsset(BUILTIN_MDL, "mdl")
    mdl.SetSourceAssetSubIdentifier("OmniPBR", "mdl")
    mdl.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0.85)
    )
    mdl.CreateInput("reflection_roughness_constant", Sdf.ValueTypeNames.Float).Set(0.9)
    mdl.CreateInput("metallic_constant", Sdf.ValueTypeNames.Float).Set(0)
    material.CreateSurfaceOutput("mdl").ConnectToSource(mdl.ConnectableAPI(), "out")
    preview = UsdShade.Shader.Define(stage, path + "/Preview")
    preview.CreateIdAttr("UsdPreviewSurface")
    preview.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.85))
    preview.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
    material.CreateSurfaceOutput().ConnectToSource(preview.ConnectableAPI(), "surface")
    return material


def walls(stage, anchor, u, v, yaw: float) -> None:
    """Create the two static oriented boxes with shared matte paint."""
    material = wall_material(stage)
    placements = (
        (
            "LongWall",
            anchor - u * BOARD_WIDTH - v * (BOARD_THICKNESS + WALL_THICKNESS / 2),
            (2 * BOARD_WIDTH, WALL_THICKNESS, WALL_HEIGHT),
        ),
        (
            "ShortWall",
            anchor + u * (WALL_THICKNESS / 2) + v * (SHORT_WALL_LENGTH / 2),
            (WALL_THICKNESS, SHORT_WALL_LENGTH, WALL_HEIGHT),
        ),
    )
    for name, center, dimensions in placements:
        center[2] = WALL_HEIGHT / 2
        shape = UsdGeom.Cube.Define(stage, GROUP + "/" + name)
        shape.CreateSizeAttr(1)
        shape.AddTranslateOp().Set(center)
        shape.AddRotateZOp().Set(yaw)
        shape.AddScaleOp().Set(Gf.Vec3f(*dimensions))
        UsdPhysics.CollisionAPI.Apply(shape.GetPrim()).CreateCollisionEnabledAttr(True)
        UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(material)


def build(stage, root: pathlib.Path, table2: dict) -> dict:
    """Place two boards, one chair and two walls without stepping physics."""
    b, u, v = frame(table2["corners_m"])
    yaw = table2["yaw_deg"]
    directory = root / "assets/furniture"
    board = directory / "wood_board/isaac/wood_board.usdc"
    chair = directory / "red_cushion_caster_chair/isaac/chair_fixed.usda"
    positions = {}
    for index in range(2):
        name = "Board" + str(index + 1)
        center = b - u * (BOARD_WIDTH * (index + 0.5)) - v * (BOARD_THICKNESS / 2)
        center[2] = BOARD_HEIGHT / 2
        prim = compose_scene.place(
            stage, GROUP + "/" + name, board, tuple(center), yaw + 180
        )
        UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
        positions[name] = list(center)
    # The source chair faces -Y; this rotation maps its front to C-to-D.
    center = Gf.Vec3d(*table2["corners_m"]["C"]) - u * 0.1 + v * (0.545 / 2 + 0.05)
    center[2] = 0
    compose_scene.place(stage, GROUP + "/Chair", chair, tuple(center), yaw - 90)
    positions["Chair"] = list(center)
    walls(stage, b, u, v, yaw)
    return {
        "prim_path": GROUP,
        "positions_m": positions,
        "board_yaw_deg": yaw + 180,
        "chair_yaw_deg": yaw - 90,
        "wall_height_m": WALL_HEIGHT,
        "wall_thickness_m": WALL_THICKNESS,
        "long_wall_length_m": 2 * BOARD_WIDTH,
        "short_wall_length_m": SHORT_WALL_LENGTH,
        "material": "white OmniPBR; roughness 0.9; metallic 0",
        "runtime_dependency": BUILTIN_MDL,
        "corner_joint": "Board1's 18 mm end bridges the wall faces at B",
    }


# Keep related geometric measurements visible in one acceptance pass.
# pylint: disable-next=too-many-locals
def validate(stage, table2: dict) -> dict:
    """Measure seams, direction, support, collisions and chair clearance."""
    b, u, v = frame(table2["corners_m"])
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    transforms = UsdGeom.XformCache()
    bodies, measured = [], {}
    for name in ("Board1", "Board2", "Chair"):
        prim = stage.GetPrimAtPath(GROUP + "/" + name)
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
            assert abs(bounds.GetSize()[0] - BOARD_WIDTH) < 1e-5
            assert abs(bounds.GetSize()[2] - BOARD_HEIGHT) < 1e-5
            assert Gf.Dot(matrix.TransformDir(Gf.Vec3d(0, -1, 0)), v) > 0.99999
            bodies.append((center, bounds))
        else:
            front = matrix.TransformDir(Gf.Vec3d(0, -1, 0))
            assert Gf.Dot(front, -u) > 0.99999
            rear = center + matrix.TransformDir(Gf.Vec3d(0, bounds.GetMax()[1], 0))
            assert Gf.Dot(rear - b, u) > WALL_THICKNESS
            c = Gf.Vec3d(*table2["corners_m"]["C"])
            clearance = Gf.Dot(center - c, v) + bounds.GetMin()[0]
            assert clearance > 0.04
            measured["chair_table_clearance_m"] = clearance
            # Even the chair's innermost edge is beyond the wall's C-side end.
            assert Gf.Dot(center - b, v) + bounds.GetMin()[0] > SHORT_WALL_LENGTH
        measured[name] = {"center_m": list(center), "colliders": len(shapes)}
    end = bodies[0][0] + u * BOARD_WIDTH / 2
    assert abs(Gf.Dot(end - b, u)) < 1e-6
    assert abs(Gf.Dot(end - b, v) + BOARD_THICKNESS / 2) < 1e-6
    assert abs((bodies[0][0] - bodies[1][0]).GetLength() - BOARD_WIDTH) < 1e-6
    for name, dimensions in (
        ("LongWall", (4, WALL_THICKNESS, WALL_HEIGHT)),
        ("ShortWall", (WALL_THICKNESS, SHORT_WALL_LENGTH, WALL_HEIGHT)),
    ):
        prim = stage.GetPrimAtPath(GROUP + "/" + name)
        scale = prim.GetAttribute("xformOp:scale").Get()
        assert all(abs(a - e) < 1e-6 for a, e in zip(scale, dimensions, strict=True))
        assert UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
        assert (
            abs(cache.ComputeWorldBound(prim).ComputeAlignedRange().GetMin()[2]) < 1e-6
        )
        assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        assert str(material.GetPath()) == GROUP + "/Paint"
    shader = UsdShade.Shader(stage.GetPrimAtPath(GROUP + "/Paint/OmniPBR"))
    assert shader.GetSourceAsset("mdl").path == BUILTIN_MDL
    assert shader.GetSourceAssetSubIdentifier("mdl") == "OmniPBR"
    assert abs(shader.GetInput("reflection_roughness_constant").Get() - 0.9) < 1e-6
    measured["status"] = "PASS"
    return measured
