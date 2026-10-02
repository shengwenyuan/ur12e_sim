"""Verify a closed physical cut and unchanged photo texture scale."""

import collections
import pathlib
import unittest

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CutBoardTest(unittest.TestCase):
    """Check the resulting asset independently of the clipping algorithm."""

    @classmethod
    def setUpClass(cls):
        path = ROOT / "assets/furniture/wood_board/isaac/wood_board_1.4m.usda"
        cls.stage = Usd.Stage.Open(str(path))
        cls.mesh = UsdGeom.Mesh(cls.stage.GetPrimAtPath("/WoodBoard/Visuals/Board"))
        cls.points = cls.mesh.GetPointsAttr().Get()
        cls.indices = list(cls.mesh.GetFaceVertexIndicesAttr().Get())

    def test_closed_solid_and_matching_collider(self):
        """Reject open cut edges, T-junctions, reversed caps or stretched geometry."""
        edges = collections.Counter()
        volume = 0.0
        for start in range(0, len(self.indices), 3):
            face = self.indices[start : start + 3]
            a, b, c = (Gf.Vec3d(self.points[index]) for index in face)
            self.assertGreater(Gf.Cross(b - a, c - a).GetLength(), 1e-12)
            volume += Gf.Dot(a, Gf.Cross(b, c)) / 6
            for index in range(3):
                edges[tuple(sorted((face[index], face[(index + 1) % 3])))] += 1
        self.assertEqual(set(edges.values()), {2})
        self.assertAlmostEqual(volume, 1.4 * 0.018 * 2.5, delta=1e-5)
        self.assertEqual(
            UsdGeom.Xformable(self.stage.GetDefaultPrim()).GetLocalTransformation(),
            Gf.Matrix4d(1),
        )
        collider = self.stage.GetPrimAtPath("/WoodBoard/Collision/Box")
        dimensions = collider.GetAttribute("xformOp:scale").Get()
        for axis, expected in enumerate((1.4, 0.018, 2.5)):
            low = min(point[axis] for point in self.points)
            high = max(point[axis] for point in self.points)
            self.assertAlmostEqual(high - low, expected, places=6)
            self.assertAlmostEqual(dimensions[axis], expected, places=6)
            self.assertAlmostEqual(low + high, 0, places=6)

    def test_photo_uvs_are_cropped_without_rescaling(self):
        """The retained photo occupies its original 70%, including cut intersections."""
        uv = UsdGeom.PrimvarsAPI(self.mesh).GetPrimvar("st").Get()
        subset = UsdGeom.Subset(
            self.stage.GetPrimAtPath("/WoodBoard/Visuals/Board/Photo_Front")
        )
        retained_u = []
        for face in subset.GetIndicesAttr().Get():
            for corner in range(face * 3, face * 3 + 3):
                point = self.points[self.indices[corner]]
                self.assertAlmostEqual(uv[corner][0], (point[0] + 0.7) / 2, places=6)
                self.assertAlmostEqual(uv[corner][1], (point[2] + 1.25) / 2.5, places=6)
                retained_u.append(uv[corner][0])
        self.assertAlmostEqual(max(retained_u), 0.7, places=6)


if __name__ == "__main__":
    unittest.main()
