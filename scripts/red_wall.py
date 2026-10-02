"""Place a matte red exterior wall using the third turning pane as reference."""

import math

# OpenUSD comes from the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

import chair_side_glass
import workcell_furniture

PATH = workcell_furniture.GROUP + "/RedWall"
MATERIAL = PATH + "Material"
REFERENCE = chair_side_glass.GROUP + "/Unit" + str(chair_side_glass.STRAIGHT_COUNT + 3)
LENGTH, HEIGHT, THICKNESS, GAP = 3.0, 3.0, 0.10, 3.0


def build(stage) -> dict:
    """Align the wall's viewer-left end with the glass's viewer-right edge."""
    unit = UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(REFERENCE))
    tangent = unit.TransformDir(Gf.Vec3d(1, 0, 0)).GetNormalized()
    outward = Gf.Vec3d(tangent[1], -tangent[0], 0)
    right_edge = unit.Transform(Gf.Vec3d(chair_side_glass.EDGE_WIDTH, 0, 0))
    offset = GAP + (chair_side_glass.GLASS_THICKNESS + THICKNESS) / 2
    left_end = right_edge + outward * offset
    center = left_end - tangent * (LENGTH / 2)
    center[2] = HEIGHT / 2
    material = workcell_furniture.surface_material(
        stage, MATERIAL, (0.7, 0.015, 0.015), 0.9, 0
    )
    prim = workcell_furniture.static_box(
        stage, PATH, tuple(center), (LENGTH, THICKNESS, HEIGHT), material
    )
    yaw = math.degrees(math.atan2(tangent[1], tangent[0]))
    prim.GetAttribute("xformOp:rotateZ").Set(yaw)
    return {
        "prim_path": PATH,
        "reference_unit": REFERENCE,
        "center_m": list(center),
        "yaw_deg": yaw,
        "dimensions_xyz_m": [LENGTH, THICKNESS, HEIGHT],
        "surface_clearance_m": GAP,
        "center_plane_offset_m": offset,
        "outward_normal_world": list(outward),
        "left_end_ground_m": list(left_end),
        "right_end_ground_m": list(left_end - tangent * LENGTH),
        "alignment": (
            "Inside looking out: wall left end aligns with glass right clear edge "
            "along outward normal"
        ),
    }


def validate(stage) -> dict:
    """Measure clearance and edge alignment independently in the glass frame."""
    wall = chair_side_glass.local_bounds(stage, PATH, REFERENCE)
    glass = chair_side_glass.local_bounds(stage, REFERENCE + "/Pane", REFERENCE)
    prim = stage.GetPrimAtPath(PATH)
    for actual, expected in zip(
        wall.GetSize(), (LENGTH, THICKNESS, HEIGHT), strict=True
    ):
        assert abs(actual - expected) < 1e-6
    assert abs(wall.GetMin()[2]) < 1e-6
    gap = glass.GetMin()[1] - wall.GetMax()[1]
    assert abs(gap - GAP) < 1e-6
    assert abs(wall.GetMax()[0] - glass.GetMin()[0]) < 1e-6
    assert UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
    assert not prim.HasAPI(UsdPhysics.RigidBodyAPI)
    material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    assert str(material.GetPath()) == MATERIAL
    shader = UsdShade.Shader(stage.GetPrimAtPath(MATERIAL + "/OmniPBR"))
    assert shader.GetInput("diffuse_color_constant").Get()[0] > 0.6
    assert abs(shader.GetInput("reflection_roughness_constant").Get() - 0.9) < 1e-6
    assert shader.GetInput("metallic_constant").Get() == 0
    return {
        "status": "PASS",
        "surface_clearance_m": gap,
        "viewer_endpoint_alignment": "PASS",
        "static_colliders": 1,
    }
