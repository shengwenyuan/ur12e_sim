"""Static USD acceptance; no Kit timeline or device connections are used."""

import math
import pathlib
import sys
import tempfile
import unittest

# OpenUSD is supplied by the Ubuntu Isaac runtime.
# pylint: disable=import-error
from pxr import (
    Gf,
    Usd,
    UsdGeom,
    UsdPhysics,
    UsdUtils,
)

# pylint: enable=import-error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# The separate scene tools deliberately do not import collector/control code.
import kinematics  # pylint: disable=wrong-import-position,import-error


class SceneTest(unittest.TestCase):
    """Verify durable geometry, collision authoring and joint consistency."""

    @classmethod
    def setUpClass(cls):
        cls.scene = ROOT / "scenes/tabletop_home/scene.usda"
        cls.stage = Usd.Stage.Open(str(cls.scene))

    def test_relocatable_dependencies(self):
        """Resolve every asset without absolute reference paths."""
        layers, _, unresolved = UsdUtils.ComputeAllDependencies(str(self.scene))
        self.assertFalse(unresolved)
        for layer in layers:
            for asset in layer.GetExternalReferences():
                self.assertFalse(pathlib.Path(asset).is_absolute(), asset)

    def test_dimensions_and_home(self):
        """Preserve meter scale and the specified downward HOME posture."""
        self.assertEqual(UsdGeom.GetStageMetersPerUnit(self.stage), 1)
        self.assertEqual(UsdGeom.GetStageUpAxis(self.stage), "Z")
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default"])
        bounds = cache.ComputeWorldBound(
            self.stage.GetPrimAtPath("/World/Table/Top")
        ).ComputeAlignedRange()
        for actual, expected in zip(bounds.GetSize(), (2.2, 1.2, 0.05)):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertAlmostEqual(bounds.GetMax()[2], 1.2, places=6)
        tcp = UsdGeom.XformCache().GetLocalToWorldTransform(
            self.stage.GetPrimAtPath("/World/NominalTCP")
        )
        self.assertLess(
            (
                tcp.TransformDir(Gf.Vec3d(0, 0, 1)) - Gf.Vec3d(0, 0, -1)
            ).GetLength(),
            1e-8,
        )
        self.assertAlmostEqual(tcp.ExtractTranslation()[1], 0.6, places=6)
        self.assertLess(abs(tcp.ExtractTranslation()[0] - 4.4 / 3), 0.03)

    def test_collision_coverage(self):
        """Require enabled colliders across all model and workcell parts."""
        counts = {"UR12e": 0, "HandE": 0, "Table": 0, "Floor": 0}
        for prim in self.stage.Traverse():
            if not prim.HasAPI(UsdPhysics.CollisionAPI):
                continue
            self.assertTrue(
                UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get()
            )
            if prim.IsA(UsdGeom.Mesh):
                self.assertEqual(
                    UsdPhysics.MeshCollisionAPI(prim)
                    .GetApproximationAttr()
                    .Get(),
                    "convexDecomposition",
                )
            counts[str(prim.GetPath()).split("/")[2]] += 1
        self.assertEqual(
            counts, {"UR12e": 7, "HandE": 6, "Table": 5, "Floor": 1}
        )

    def test_revolute_joint_anchors(self):
        """Keep both joint anchors coincident in the posed world frame."""
        cache = UsdGeom.XformCache()
        joints = [
            p for p in self.stage.Traverse() if p.IsA(UsdPhysics.RevoluteJoint)
        ]
        self.assertEqual(len(joints), 6)
        for prim in joints:
            joint = UsdPhysics.Joint(prim)
            anchors = []
            for targets, position in (
                (joint.GetBody0Rel(), joint.GetLocalPos0Attr()),
                (joint.GetBody1Rel(), joint.GetLocalPos1Attr()),
            ):
                body = self.stage.GetPrimAtPath(targets.GetTargets()[0])
                anchors.append(
                    cache.GetLocalToWorldTransform(body).Transform(
                        Gf.Vec3d(position.Get())
                    )
                )
            self.assertLess(
                (anchors[0] - anchors[1]).GetLength(), 1e-5, str(prim.GetPath())
            )

    def test_joint_transform_order(self):
        """Check a known composed rotation and translation independently."""
        xml = """<robot name="fixture">
          <link name="base"/><link name="arm"/><link name="tip"/>
          <joint name="turn" type="revolute"><parent link="base"/>
            <child link="arm"/><origin xyz="1 2 3" rpy="0 0 1.5707963267948966"/>
            <axis xyz="0 0 1"/></joint>
          <joint name="reach" type="fixed"><parent link="arm"/>
            <child link="tip"/><origin xyz="1 0 0"/></joint>
        </robot>"""
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "fixture.urdf"
            path.write_text(xml, encoding="utf-8")
            result = kinematics.forward(path, {"turn": math.pi / 2})
        self.assertLess(
            (
                result["tip"].ExtractTranslation() - Gf.Vec3d(0, 2, 3)
            ).GetLength(),
            1e-10,
        )


if __name__ == "__main__":
    unittest.main()
