"""Physical authoring checks only: no Kit startup, stepping or device access."""

import importlib.util
import json
import math
import pathlib
import unittest

from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

from ur12e_collection.control import model
from ur12e_collection.followers.physics import Settings

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "physical_scene", ROOT / "runtime/physical.py"
)
physical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(physical)


class PhysicalTest(unittest.TestCase):
    """Check the composed topology and SI contracts, not solver behavior."""

    def setUp(self):
        self.stage = Usd.Stage.Open(
            str(ROOT / "scenes/tabletop_home/scene.usda")
        )
        self.saved = {
            l.identifier: l.ExportToString()
            for l in self.stage.GetUsedLayers()
            if l != self.stage.GetSessionLayer()
        }
        self.settings = Settings(
            240,
            (6000,) * 6,
            (600,) * 6,
            (330,) * 6,
            10000,
            100,
            130,
            0.6,
            0.5,
            0,
            0.0002,
            0.001,
        )
        self.config = {
            "physics": self.settings,
            "limits": model.Limits(
                lower=(-5.5,) * 6,
                upper=(5.5,) * 6,
                ready=(
                    0,
                    -math.pi / 2,
                    -math.pi / 2,
                    -math.pi / 2,
                    math.pi / 2,
                    0,
                ),
            ),
        }
        self.layout = physical.prepare(self.stage, ROOT, self.config)

    def test_single_connected_fixed_base_articulation(self):
        roots = [
            p.GetPath()
            for p in self.stage.Traverse()
            if p.HasAPI(UsdPhysics.ArticulationRootAPI)
        ]
        self.assertEqual(
            roots,
            [self.stage.GetPrimAtPath(self.layout["articulation"]).GetPath()],
        )
        bodies = {
            p.GetPath()
            for p in self.stage.Traverse()
            if p.HasAPI(UsdPhysics.RigidBodyAPI)
        }
        edges, world = [], []
        for prim in self.stage.Traverse():
            if not prim.IsA(UsdPhysics.Joint):
                continue
            joint = UsdPhysics.Joint(prim)
            a, b = (
                joint.GetBody0Rel().GetTargets(),
                joint.GetBody1Rel().GetTargets(),
            )
            self.assertEqual(len(b), 1)
            self.assertIn(b[0], bodies)
            if a:
                self.assertEqual(len(a), 1)
                self.assertIn(a[0], bodies)
                edges.append((a[0], b[0]))
            else:
                world.append(b[0])
        self.assertEqual(world, roots)
        visited = set(world)
        while True:
            before = len(visited)
            for a, b in edges:
                if a in visited:
                    visited.add(b)
            if len(visited) == before:
                break
        self.assertEqual(visited, bodies)
        self.assertEqual(len(edges), len(bodies) - 1)

    def test_usd_physics_parser_accepts_one_complete_articulation(self):
        parsed = UsdPhysics.UsdPhysicsLoadStageFromPrimRange(
            self.stage, [Sdf.Path("/World")]
        )
        for _, descriptors in parsed.values():
            self.assertTrue(all(item.isValid for item in descriptors))
        roots, descriptors = parsed[UsdPhysics.ObjectType.Articulation]
        self.assertEqual(len(roots), 1)
        bodies = {p for p in descriptors[0].articulatedBodies if p}
        self.assertEqual(len(bodies), 11)
        self.assertEqual(len(parsed[UsdPhysics.ObjectType.RevoluteJoint][0]), 6)
        self.assertEqual(
            len(parsed[UsdPhysics.ObjectType.PrismaticJoint][0]), 2
        )
        for path in bodies:
            mass = UsdPhysics.MassAPI(self.stage.GetPrimAtPath(path))
            self.assertGreater(mass.GetMassAttr().Get(), 0)
            inertia = mass.GetDiagonalInertiaAttr().Get()
            self.assertTrue(all(math.isfinite(v) and v > 0 for v in inertia))
            self.assertLessEqual(max(inertia), sum(inertia) / 2 + 1e-8)

    def test_fixed_anchors_preserve_mount_and_base_pose(self):
        cache = UsdGeom.XformCache()
        for path in (
            "/World/PhysicalJoints/Base",
            "/World/PhysicalJoints/Tool",
        ):
            joint = UsdPhysics.Joint(self.stage.GetPrimAtPath(path))
            matrices = []
            for relation, pos, rot in (
                (
                    joint.GetBody0Rel(),
                    joint.GetLocalPos0Attr(),
                    joint.GetLocalRot0Attr(),
                ),
                (
                    joint.GetBody1Rel(),
                    joint.GetLocalPos1Attr(),
                    joint.GetLocalRot1Attr(),
                ),
            ):
                local = Gf.Matrix4d().SetRotate(Gf.Quatd(rot.Get()))
                local.SetTranslateOnly(Gf.Vec3d(pos.Get()))
                targets = relation.GetTargets()
                matrices.append(
                    local
                    * cache.GetLocalToWorldTransform(
                        self.stage.GetPrimAtPath(targets[0])
                    )
                    if targets
                    else local
                )
            for row in range(4):
                for col in range(4):
                    self.assertAlmostEqual(
                        matrices[0][row][col], matrices[1][row][col], places=5
                    )

    def test_drives_convert_si_gains_and_targets(self):
        joints = {
            p.GetName(): p
            for p in self.stage.Traverse()
            if p.IsA(UsdPhysics.Joint)
        }
        for i, name in enumerate(physical.NAMES):
            angular = i < 6
            drive = UsdPhysics.DriveAPI(
                joints[name], "angular" if angular else "linear"
            )
            self.assertEqual(drive.GetTypeAttr().Get(), "force")
            expected = 6000 * math.pi / 180 if angular else 10000
            self.assertAlmostEqual(
                drive.GetStiffnessAttr().Get(), expected, places=4
            )
            expected = (
                math.degrees(self.config["limits"].ready[i])
                if angular
                else 0.025
            )
            self.assertAlmostEqual(
                drive.GetTargetPositionAttr().Get(), expected, places=6
            )
            self.assertGreater(drive.GetMaxForceAttr().Get(), 0)
            self.assertFalse(
                any("Mimic" in api for api in joints[name].GetAppliedSchemas())
            )

    def test_finger_inertia_is_explicit_geometric_estimate(self):
        self.assertEqual(len(self.layout["finger_inertias"]), 2)
        for result in self.layout["finger_inertias"]:
            self.assertGreater(min(result["size_m"]), 0)
            self.assertGreater(min(result["inertia_kg_m2"]), 1e-9)
            x, y, z = result["inertia_kg_m2"]
            self.assertLessEqual(max(x, y, z), (x + y + z) / 2 + 1e-10)
            prim = self.stage.GetPrimAtPath(result["body"])
            self.assertIn(
                "provisional",
                prim.GetAttribute("physicsModel:inertiaSource").Get(),
            )

    def test_collision_material_and_filters_preserve_table_contacts(self):
        scene = UsdPhysics.Scene(self.stage.GetPrimAtPath(self.layout["scene"]))
        self.assertAlmostEqual(
            scene.GetGravityMagnitudeAttr().Get(), 9.81, places=5
        )
        collider_count = 0
        for p in self.stage.Traverse():
            if p.HasAPI(UsdPhysics.FilteredPairsAPI):
                for target in (
                    UsdPhysics.FilteredPairsAPI(p)
                    .GetFilteredPairsRel()
                    .GetTargets()
                ):
                    self.assertFalse(
                        str(target).startswith(("/World/Table", "/World/Floor"))
                    )
            if p.HasAPI(UsdPhysics.CollisionAPI):
                collider_count += 1
                self.assertTrue(
                    UsdPhysics.CollisionAPI(p).GetCollisionEnabledAttr().Get()
                )
                material, _ = UsdShade.MaterialBindingAPI(
                    p
                ).ComputeBoundMaterial(materialPurpose="physics")
                self.assertTrue(material)
        self.assertGreaterEqual(collider_count, 19)

    def test_source_layers_unchanged_and_overlay_repeatable(self):
        overlay = self.stage.GetSessionLayer().ExportToString()
        again = physical.prepare(self.stage, ROOT, self.config)
        self.assertEqual(again, self.layout)
        self.assertEqual(overlay, self.stage.GetSessionLayer().ExportToString())
        for layer in self.stage.GetUsedLayers():
            if layer.identifier in self.saved:
                self.assertEqual(
                    layer.ExportToString(), self.saved[layer.identifier]
                )
        json.dumps(self.layout)


if __name__ == "__main__":
    unittest.main()
