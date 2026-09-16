"""Check finite background geometry and the base-centered workcell contract."""

import copy
import json
import math
import pathlib
import sys
import tempfile
import unittest

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, UsdUtils

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# pylint: disable=wrong-import-position
import compose_box_scene
import kinematics
import projected_room


class ProjectedRoomTest(unittest.TestCase):
    """Check world geometry and camera behavior independently of rendering."""

    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / "scenes/versteel_box_pick_place"
        cls.settings = projected_room.load(cls.directory / "room.json")
        cls.stage = Usd.Stage.Open(str(cls.directory / "scene.usda"))
        cls.layout = json.loads((cls.directory / "layout.json").read_text())

    def test_cardinal_projection(self):
        """Keep wood forward, entrance left, blinds right, and ceiling up."""
        origin = self.settings["capture_position_m"]
        for direction, expected in (
            ((1, 0, 0), (0.5, 0.5)),
            ((0, 1, 0), (0.25, 0.5)),
            ((0, -1, 0), (0.75, 0.5)),
            ((0, 0, 1), (0.5, 1)),
            ((0, 0, -1), (0.5, 0)),
        ):
            point = tuple(a + b for a, b in zip(origin, direction))
            self.assertEqual(
                projected_room.texture_uv(point, self.settings), expected
            )

    def test_camera_translation_has_distance_dependent_parallax(self):
        """A 10 cm camera translation shifts the nearby blind texture more."""
        before = copy.deepcopy(self.settings)
        near0 = projected_room.texture_uv((0.3, -0.5, 1.2), self.settings)[0]
        near1 = projected_room.texture_uv((0.4, -0.5, 1.2), self.settings)[0]
        far0 = projected_room.texture_uv((2.0, 0, 1.2), self.settings)[0]
        far1 = projected_room.texture_uv((2.0, 0.1, 1.2), self.settings)[0]
        self.assertAlmostEqual(
            abs(near1 - near0) * 2 * math.pi, math.atan(0.1 / 0.5)
        )
        self.assertAlmostEqual(
            abs(far1 - far0) * 2 * math.pi, math.atan(0.1 / 1.7)
        )
        self.assertGreater(abs(near1 - near0), 3 * abs(far1 - far0))
        self.assertEqual(self.settings, before)

    def test_base_table_and_retained_prop_layout(self):
        """Keep grounded feet, 0.85 m support, and relative XY placement."""
        report = compose_box_scene.validate(self.directory / "scene.usda")
        self.assertEqual(report["static_validation"], "PASS")
        self.assertEqual(self.layout["robot"]["base_position_m"], [0, 0, 0.85])
        self.assertEqual(
            self.layout["robot"]["home_deg"], [0, -90, -90, -90, 90, 0]
        )
        self.assertEqual(self.layout["robot"]["base_yaw_rad"], -math.pi)
        self.assertAlmostEqual(
            self.layout["props"]["cube_position_m"][0], 0.6097
        )
        self.assertAlmostEqual(
            self.layout["props"]["cube_position_m"][1], 0.019
        )
        cache = UsdGeom.BBoxCache(
            Usd.TimeCode.Default(), ["default", "render"]
        )
        bounds = cache.ComputeWorldBound(
            self.stage.GetPrimAtPath("/World/Table")
        ).ComputeAlignedRange()
        self.assertLess(abs(bounds.GetMin()[2]), 0.001)
        self.assertAlmostEqual(bounds.GetMax()[2], 0.85, places=5)
        floor = self.stage.GetPrimAtPath("/World/Floor")
        self.assertTrue(
            UsdPhysics.CollisionAPI(floor).GetCollisionEnabledAttr().Get()
        )

    def test_robot_geometry_is_not_scaled_or_reposed(self):
        """Preserve link HOME FK when changing the mounting translation."""
        robot = self.layout["robot"]
        urdf = ROOT / "assets/robots/ur12e/ur12e.urdf"
        joints = dict(
            zip(robot["joint_names"], map(math.radians, robot["home_deg"]))
        )
        expected = kinematics.forward(urdf, joints)
        cache = UsdGeom.XformCache()
        mount = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), -180))
        mount.SetTranslateOnly(Gf.Vec3d(0, 0, 0.85))
        checked = 0
        for prim in Usd.PrimRange(self.stage.GetPrimAtPath("/World/UR12e")):
            if not prim.IsA(UsdGeom.Xform) or prim.GetName() not in expected:
                continue
            transform = expected[prim.GetName()]
            actual = cache.GetLocalToWorldTransform(prim)
            self.assertLess(
                max(
                    abs(actual[i][j] - (transform * mount)[i][j])
                    for i in range(4)
                    for j in range(4)
                ),
                1e-7,
            )
            checked += 1
        self.assertGreaterEqual(checked, 7)

    def test_finite_meshes_material_and_dependencies(self):
        """A relocatable, non-colliding room owns the visible photograph."""
        _, _, unresolved = UsdUtils.ComputeAllDependencies(
            str(self.directory / "scene.usda")
        )
        self.assertFalse(unresolved)
        dome = UsdLux.DomeLight(self.stage.GetPrimAtPath("/World/Environment"))
        self.assertFalse(dome.GetTextureFileAttr().Get())
        meshes = [
            p
            for p in Usd.PrimRange(
                self.stage.GetPrimAtPath("/World/LabBackground")
            )
            if p.IsA(UsdGeom.Mesh)
        ]
        self.assertEqual(len(meshes), 6)
        for prim in meshes:
            self.assertFalse(prim.HasAPI(UsdPhysics.CollisionAPI))
            self.assertTrue(
                prim.GetAttribute("primvars:doNotCastShadows").Get()
            )
            mesh = UsdGeom.Mesh(prim)
            self.assertEqual(
                len(UsdGeom.PrimvarsAPI(prim).GetPrimvar("st").Get()),
                len(mesh.GetFaceVertexIndicesAttr().Get()),
            )
        shader = UsdShade.Shader(
            self.stage.GetPrimAtPath("/World/LabBackground/Material/Image")
        )
        self.assertEqual(shader.GetInput("sourceColorSpace").Get(), "sRGB")
        capture = UsdGeom.XformCache().GetLocalToWorldTransform(
            self.stage.GetPrimAtPath("/World/CaptureCamera")
        )
        self.assertLess(
            (capture.ExtractTranslation() - Gf.Vec3d(0.3, 0, 1.2)).GetLength(),
            1e-8,
        )
        self.assertLess(
            (
                capture.TransformDir(Gf.Vec3d(0, 0, -1)) - Gf.Vec3d(1, 0, 0)
            ).GetLength(),
            1e-8,
        )

    def test_room_front_faces_point_toward_capture(self):
        """RTX emission must be visible from inside every room surface."""
        origin = Gf.Vec3d(*self.settings["capture_position_m"])
        for prim in Usd.PrimRange(
            self.stage.GetPrimAtPath("/World/LabBackground")
        ):
            if not prim.IsA(UsdGeom.Mesh):
                continue
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get()
            first_face = mesh.GetFaceVertexIndicesAttr().Get()[:3]
            a, b, c = (Gf.Vec3d(points[index]) for index in first_face)
            normal = Gf.Cross(b - a, c - a)
            self.assertGreater(
                Gf.Dot(normal, origin - a), 0, str(prim.GetPath())
            )

    def test_invalid_capture_is_rejected(self):
        """A camera outside the room cannot define this projection model."""
        invalid = copy.deepcopy(self.settings)
        invalid["capture_position_m"][1] = -0.5
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "room.json"
            path.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError):
                projected_room.load(path)


if __name__ == "__main__":
    unittest.main()
