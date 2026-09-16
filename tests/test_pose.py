"""M14 USD pose checks with no physics or robot connection."""

import math
import pathlib
import shutil
import sys
import tempfile
import unittest

# pylint: disable-next=import-error
from pxr import (
    Gf,
    Usd,
    UsdGeom,
    UsdPhysics,
    UsdUtils,
)  # pylint: disable=import-error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / "scripts")]
import pose  # pylint: disable=wrong-import-position,import-error

# pylint: disable-next=wrong-import-position
from ur12e_collection.contracts import (
    JOINT_NAMES,
)  # pylint: disable=wrong-import-position

HOME = (0, -math.pi / 2, -math.pi / 2, -math.pi / 2, math.pi / 2, 0)


class PoseTest(unittest.TestCase):
    """Compare live authoring with saved HOME and independent joint anchors."""

    def setUp(self):
        self.stage = Usd.Stage.Open(
            str(ROOT / "scenes/tabletop_home/scene.usda")
        )
        self.saved = [
            (layer, layer.ExportToString())
            for layer in self.stage.GetUsedLayers()
            if layer != self.stage.GetSessionLayer()
        ]
        cache = UsdGeom.XformCache()
        self.home = {
            str(prim.GetPath()): cache.GetLocalToWorldTransform(prim)
            for prim in self.stage.Traverse()
            if prim.IsA(UsdGeom.Xform)
        }
        self.model = pose.Pose(self.stage, ROOT)

    def assert_matrix(self, actual, expected):
        """Assert matrix."""
        self.assertLess(
            max(
                abs(actual[i][j] - expected[i][j])
                for i in range(4)
                for j in range(4)
            ),
            1e-8,
        )

    def anchors(self):
        """Anchors."""
        cache = UsdGeom.XformCache()
        for prim in self.stage.Traverse():
            if not prim.IsA(UsdPhysics.RevoluteJoint):
                continue
            joint = UsdPhysics.Joint(prim)
            anchors = []
            for body, pos in (
                (joint.GetBody0Rel(), joint.GetLocalPos0Attr()),
                (joint.GetBody1Rel(), joint.GetLocalPos1Attr()),
            ):
                transform = cache.GetLocalToWorldTransform(
                    self.stage.GetPrimAtPath(body.GetTargets()[0])
                )
                anchors.append(transform.Transform(Gf.Vec3d(pos.Get())))
            self.assertLess((anchors[0] - anchors[1]).GetLength(), 1e-5)

    def test_home_axes_mixed_pose_tool_attachment_and_saved_layers(self):
        """Test home axes mixed pose tool attachment and saved layers."""
        self.model.apply(HOME, "epoch")
        cache = UsdGeom.XformCache()
        for path, expected in self.home.items():
            self.assert_matrix(
                cache.GetLocalToWorldTransform(self.stage.GetPrimAtPath(path)),
                expected,
            )
        poses = []
        for axis in range(6):
            for delta in (-0.3, 0.3):
                q = list(HOME)
                q[axis] += delta
                poses.append(tuple(q))
        poses.append((0.3, -1.2, -1.8, -0.9, 1.1, -0.2))
        for q in poses:
            with self.subTest(q=q):
                self.model.apply(q, "epoch")
                self.anchors()
                arm = self.model.arm_model.forward(dict(zip(JOINT_NAMES, q)))
                actual = UsdGeom.XformCache().GetLocalToWorldTransform(
                    self.stage.GetPrimAtPath("/World/HandE")
                )
                self.assert_matrix(actual, arm["tool0"] * self.model.mount)
                self.assert_matrix(
                    UsdGeom.XformCache().GetLocalToWorldTransform(
                        self.stage.GetPrimAtPath("/World/UR12e")
                    ),
                    self.home["/World/UR12e"],
                )
        for layer, contents in self.saved:
            self.assertEqual(layer.ExportToString(), contents)

    def test_gripper_open_half_closed_preserves_arm_and_saved_layers(self):
        """Measure authored finger displacement across the complete travel."""
        fingers = {
            side: next(
                link
                for link in self.model.tool.links
                if link.GetName() == f"robotiq_hande_{side}_finger"
            )
            for side in ("left", "right")
        }
        distances = []
        for position in (0, 127.5, 255):
            self.model.apply(HOME, "gripper", position)
            cache = UsdGeom.XformCache()
            points = [
                cache.GetLocalToWorldTransform(link).ExtractTranslation()
                for link in fingers.values()
            ]
            distances.append((points[0] - points[1]).GetLength())
            for path, expected in self.home.items():
                if path.startswith("/World/UR12e"):
                    self.assert_matrix(
                        cache.GetLocalToWorldTransform(
                            self.stage.GetPrimAtPath(path)
                        ),
                        expected,
                    )
        self.assertAlmostEqual(distances[0] - distances[1], 0.025, places=7)
        self.assertAlmostEqual(distances[1] - distances[2], 0.025, places=7)
        for layer, contents in self.saved:
            self.assertEqual(layer.ExportToString(), contents)

    def test_trail_is_bounded_and_resets_with_source_epoch(self):
        """Test trail is bounded and resets with source epoch."""
        for _ in range(305):
            self.model.apply(HOME, "epoch")
        self.assertEqual(len(self.model.trail), 300)
        self.model.apply(HOME, "new")
        self.assertEqual(len(self.model.trail), 1)
        self.assertEqual(
            self.model.curve.GetVisibilityAttr().Get(), "invisible"
        )

    def test_relocated_scene_roots_resolve_all_assets(self):
        """Load two relocated scene roots and resolve every relative asset."""
        for name in ("first", "second/nested"):
            with tempfile.TemporaryDirectory() as temporary:
                root = pathlib.Path(temporary) / name
                shutil.copytree(ROOT / "assets", root / "assets")
                shutil.copytree(ROOT / "scenes", root / "scenes")
                entrypoint = root / "scenes/tabletop_home/scene.usda"
                _, _, unresolved = UsdUtils.ComputeAllDependencies(
                    str(entrypoint)
                )
                self.assertFalse(unresolved)
                stage = Usd.Stage.Open(str(entrypoint))
                model = pose.Pose(stage, root)
                model.apply(HOME, "copy")
                self.assert_matrix(
                    UsdGeom.XformCache().GetLocalToWorldTransform(
                        stage.GetPrimAtPath("/World/UR12e")
                    ),
                    self.home["/World/UR12e"],
                )


if __name__ == "__main__":
    unittest.main()
