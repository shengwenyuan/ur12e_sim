"""Check retained workcell geometry and the background-free scene contract."""

import json
import math
import pathlib
import sys
import unittest

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdUtils

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# pylint: disable=wrong-import-position
import compose_box_scene
import kinematics


class BoxSceneTest(unittest.TestCase):
    """Verify the clean scene without connecting to hardware or Kit."""

    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / "scenes/versteel_box_pick_place"
        cls.stage = Usd.Stage.Open(str(cls.directory / "scene.usda"))
        cls.layout = json.loads((cls.directory / "layout.json").read_text())

    def test_base_table_and_retained_prop_layout(self):
        """Keep grounded feet, 0.85 m support, and relative XY placement."""
        report = compose_box_scene.validate(self.directory / "scene.usda")
        self.assertEqual(report["static_validation"], "PASS")
        self.assertEqual(self.layout["robot"]["base_position_m"], [0, 0, 0.85])
        self.assertEqual(self.layout["robot"]["home_deg"], [0, -90, -90, -90, 90, 0])
        self.assertEqual(self.layout["robot"]["base_yaw_rad"], -math.pi)
        self.assertAlmostEqual(self.layout["props"]["cube_position_m"][0], 0.6097)
        self.assertAlmostEqual(self.layout["props"]["cube_position_m"][1], 0.019)
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
        bounds = cache.ComputeWorldBound(
            self.stage.GetPrimAtPath("/World/Table")
        ).ComputeAlignedRange()
        self.assertLess(abs(bounds.GetMin()[2]), 0.001)
        self.assertAlmostEqual(bounds.GetMax()[2], 0.85, places=5)
        floor = self.stage.GetPrimAtPath("/World/Floor")
        self.assertTrue(UsdPhysics.CollisionAPI(floor).GetCollisionEnabledAttr().Get())

    def test_robot_geometry_is_not_scaled_or_reposed(self):
        """Preserve link HOME FK when changing the mounting translation."""
        robot = self.layout["robot"]
        urdf = ROOT / "assets/robots/ur12e/ur12e.urdf"
        joints = dict(zip(robot["joint_names"], map(math.radians, robot["home_deg"])))
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

    def test_clean_environment_and_portable_dependencies(self):
        """No room/photo dependencies can enter the active workcell."""
        self.assertFalse(self.stage.GetPrimAtPath("/World/LabBackground"))
        self.assertFalse(self.stage.GetPrimAtPath("/World/CaptureCamera"))
        dome = UsdLux.DomeLight(self.stage.GetPrimAtPath("/World/Environment"))
        self.assertFalse(dome.GetTextureFileAttr().Get())
        floor = UsdGeom.Imageable(self.stage.GetPrimAtPath("/World/Floor"))
        self.assertEqual(floor.ComputeVisibility(), "inherited")
        expected = {
            "Table",
            "Table2",
            "UR12e",
            "HandE",
            "Props",
            "Floor",
            "Environment",
            "Key",
            "PhysicsScene",
            "Camera",
        }
        self.assertEqual(
            {p.GetName() for p in self.stage.GetPrimAtPath("/World").GetChildren()},
            expected,
        )
        layers, assets, unresolved = UsdUtils.ComputeAllDependencies(
            str(self.directory / "scene.usda")
        )
        self.assertFalse(unresolved)
        dependencies = [layer.realPath for layer in layers] + assets
        self.assertFalse(
            any("background" in str(path).lower() for path in dependencies)
        )
        self.assertEqual(self.layout["background"]["mode"], "none")


if __name__ == "__main__":
    unittest.main()
