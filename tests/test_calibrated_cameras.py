"""Validate optical frames, source selection and retained workcell fields."""

import json
import pathlib
import sys
import unittest

import numpy as np
from pxr import Gf, Usd, UsdGeom  # pylint: disable=import-error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# pylint: disable=wrong-import-position
import calibrated_cameras
import import_camera_calibration


class CalibratedCameraTest(unittest.TestCase):
    """Test three optical cameras without Kit, devices or controller clients."""

    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / calibrated_cameras.CONFIG).read_text())
        cls.scene = ROOT / "scenes/versteel_box_pick_place/scene.usda"

    def test_sources_and_complete_lens_parameters(self):
        """Keep serial-specific K/D and numerical conversion provenance."""
        stage = Usd.Stage.Open(str(self.scene))
        self.assertEqual(self.config["resolution"], [640, 480])
        serials = {
            "camera_1": "260522273667",
            "camera_2": "327122073926",
            "camera_3": "327122075735",
        }
        for name, spec in self.config["cameras"].items():
            self.assertEqual(spec["serial"], serials[name])
            parent = calibrated_cameras.reference_link(
                stage, spec["reference_link"]
            )
            prim = stage.GetPrimAtPath(str(parent.GetPath()) + "/" + name)
            self.assertIn(
                calibrated_cameras.SCHEMA,
                prim.GetMetadata("apiSchemas").GetAddedOrExplicitItems(),
            )
            self.assertEqual(
                list(
                    prim.GetAttribute(
                        calibrated_cameras.PREFIX + "imageSize"
                    ).Get()
                ),
                [640, 480],
            )
            for key, expected in spec["intrinsics"].items():
                self.assertAlmostEqual(
                    prim.GetAttribute(calibrated_cameras.PREFIX + key).Get(),
                    expected,
                    delta=5e-5,
                )
            for key, expected in zip(
                ("k1", "k2", "p1", "p2", "k3"), spec["renderer_distortion"]
            ):
                self.assertAlmostEqual(
                    prim.GetAttribute(calibrated_cameras.PREFIX + key).Get(),
                    expected,
                    delta=1e-7,
                )
            if name != "camera_1":
                self.assertEqual(
                    spec["blend"]["camera_matrix_from"]["resolution"],
                    [640, 480],
                )
                self.assertEqual(
                    spec["blend"]["distortion_from"]["resolution"], [1280, 720]
                )
                self.assertEqual(
                    spec["intrinsics"],
                    spec["pure_480p_alternative"]["intrinsics"],
                )
                self.assertNotEqual(
                    spec["source_distortion"],
                    spec["pure_480p_alternative"]["distortion"],
                )
        factory = self.config["cameras"]["camera_1"]
        self.assertEqual(
            factory["source_distortion_model"],
            "distortion.inverse_brown_conrady",
        )
        self.assertLess(factory["conversion"]["max_error_px"], 0.1)

    def test_world_axes_and_wrist_attachment(self):
        """Verify controller base and optical axis conversion."""
        stage = Usd.Stage.Open(str(self.scene))
        stage.SetEditTarget(stage.GetSessionLayer())
        cache = UsdGeom.XformCache()
        base = calibrated_cameras.reference_link(stage, "base")
        base_world = cache.GetLocalToWorldTransform(base)
        self.assertLess(
            (
                base_world.ExtractTranslation() - Gf.Vec3d(0, 0, 0.85)
            ).GetLength(),
            1e-8,
        )
        for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            self.assertLess(
                (
                    base_world.TransformDir(Gf.Vec3d(*axis)) - Gf.Vec3d(*axis)
                ).GetLength(),
                1e-8,
            )
        paths = calibrated_cameras.build(stage, self.config)
        for name, path in paths.items():
            spec = self.config["cameras"][name]
            parent = calibrated_cameras.reference_link(
                stage, spec["reference_link"]
            )
            optical_world = calibrated_cameras.optical_matrix(
                spec
            ) * cache.GetLocalToWorldTransform(parent)
            actual = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(path))
            # USD +Y/-Z match optical -Y/+Z without reflection or yaw changes.
            for usd_axis, optical_axis in (
                ((1, 0, 0), (1, 0, 0)),
                ((0, 1, 0), (0, -1, 0)),
                ((0, 0, -1), (0, 0, 1)),
            ):
                self.assertLess(
                    (
                        actual.TransformDir(Gf.Vec3d(*usd_axis))
                        - optical_world.TransformDir(Gf.Vec3d(*optical_axis))
                    ).GetLength(),
                    1e-8,
                )

    def test_wrist_follows_without_moving_fixed_cameras(self):
        """A tool rotation moves only the wrist view."""
        stage = Usd.Stage.Open(str(self.scene))
        stage.SetEditTarget(stage.GetSessionLayer())
        paths = calibrated_cameras.build(stage, self.config)
        cache = UsdGeom.XformCache()
        before = {
            name: cache.GetLocalToWorldTransform(stage.GetPrimAtPath(path))
            for name, path in paths.items()
        }
        tool = calibrated_cameras.reference_link(stage, "tool0")
        transform = UsdGeom.Xformable(tool)
        change = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), 23))
        transform.MakeMatrixXform().Set(
            change * transform.GetLocalTransformation()
        )
        cache.Clear()
        for name, path in paths.items():
            after = cache.GetLocalToWorldTransform(stage.GetPrimAtPath(path))
            if name == "camera_1":
                self.assertGreater(
                    (
                        after.ExtractTranslation()
                        - before[name].ExtractTranslation()
                    ).GetLength(),
                    0.01,
                )
            else:
                self.assertEqual(after, before[name])

    def test_sdk_projection_approximation(self):
        """Verify expanded ray domain and avoid a sign-flipped factory model."""
        spec = self.config["cameras"]["camera_1"]
        intrinsic = spec["intrinsics"]
        x, y = np.meshgrid(np.linspace(0, 639, 129), np.linspace(0, 479, 97))
        focal = np.array([intrinsic["fx"], intrinsic["fy"]])
        points = (
            (
                np.column_stack((x.ravel(), y.ravel()))
                - [intrinsic["cx"], intrinsic["cy"]]
            )
            / focal
            * 1.05
        )
        exact = import_camera_calibration.factory_projection(
            points, spec["source_distortion"]
        )
        rendered = import_camera_calibration.distort(
            points, spec["renderer_distortion"]
        )
        self.assertLess(
            np.linalg.norm((rendered - exact) * focal, axis=1).max(), 0.1
        )
        flipped = import_camera_calibration.distort(
            points, -np.array(spec["source_distortion"])
        )
        self.assertGreater(
            np.linalg.norm((flipped - exact) * focal, axis=1).max(), 5
        )

    def test_configuration_is_idempotent_and_retains_scene(self):
        """Rebuilding preserves saved layers and avoids duplicate transforms."""
        stage = Usd.Stage.Open(str(self.scene))
        original = stage.GetRootLayer().ExportToString()
        stage.SetEditTarget(stage.GetSessionLayer())
        calibrated_cameras.build(stage, self.config)
        first = stage.GetSessionLayer().ExportToString()
        calibrated_cameras.build(stage, self.config)
        self.assertEqual(first, stage.GetSessionLayer().ExportToString())
        self.assertEqual(original, stage.GetRootLayer().ExportToString())


if __name__ == "__main__":
    unittest.main()
