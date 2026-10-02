"""Rebuild accepted furniture and verify transformed wall composition."""

import json
import pathlib
import shutil
import sys
import tempfile
import unittest

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils

# pylint: enable=import-error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# This suite exercises standalone authoring without Kit or collector imports.
# pylint: disable=wrong-import-position
import chair_side_glass
import red_wall
import room_extension
import scene_geometry
import wall_materials
import workcell_furniture
import wall_fixtures
from wall_components import WallAssembly, WallPanel

# pylint: enable=wrong-import-position


def authored_fields(layer: Sdf.Layer) -> dict:
    """Include metadata, references, connections and every authored value."""
    result = {}

    def capture(path):
        spec = layer.GetObjectAtPath(path)
        if spec is None:
            return
        for key in spec.ListInfoKeys():
            result[(str(path), key)] = spec.GetInfo(key)

    layer.Traverse(Sdf.Path.absoluteRootPath, capture)
    return result


def copy_scene_dependencies(scene: pathlib.Path, target: pathlib.Path) -> None:
    """Relocate only actual USD/texture dependencies, excluding native MDL."""
    layers, assets, missing = UsdUtils.ComputeAllDependencies(str(scene))
    if set(missing) - {wall_materials.PBR_MDL, wall_materials.GLASS_MDL}:
        raise ValueError(f"Missing scene dependencies: {missing}")
    files = {pathlib.Path(layer.realPath) for layer in layers}
    files.update(pathlib.Path(asset) for asset in assets)
    for source in files:
        destination = target / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


class WallCompositionTest(unittest.TestCase):
    """Verify reuse, local transforms, failure handling and exact equivalence."""

    def test_rebuilt_furniture_matches_every_accepted_field(self):
        """Recreate all wall/furniture modules without retaining old geometry."""
        source = ROOT / "scenes/versteel_box_pick_place/scene.usda"
        layout = json.loads(source.with_name("layout.json").read_text())
        expected = authored_fields(Sdf.Layer.FindOrOpen(str(source)))
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory)
            copy_scene_dependencies(source, target)
            output = target / source.relative_to(ROOT)
            stage = Usd.Stage.Open(str(output))
            stage.RemovePrim("/World/Furniture")
            for key, result in (
                (
                    "furniture",
                    workcell_furniture.build(stage, target, layout["table2"]),
                ),
                ("room_extension", room_extension.build(stage, layout["table2"])),
                ("chair_side_glass", chair_side_glass.build(stage, layout["table2"])),
                ("red_wall", red_wall.build(stage)),
                ("fire_extinguisher", wall_fixtures.build(stage, target)),
            ):
                self.assertEqual(result, layout[key], key)
            self.assertEqual(authored_fields(stage.GetRootLayer()), expected)

    def test_nested_local_frames_and_bound_material(self):
        """Check an offset panel under two rotated, translated assemblies."""
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        wall_materials.surface_material(stage, "/World/Paint", (1, 0, 0), 0.9, 0)
        panel = WallPanel((1, 0, 1), (2, 0.10, 2), "/World/Paint")
        child = WallAssembly(
            panels=(("Panel", panel),), translation=(2, 0, 0), yaw_deg=90
        )
        WallAssembly(
            children=(("Child", child),), translation=(3, 4, 0), yaw_deg=90
        ).build(stage, "/World/Assembly")
        prim = stage.GetPrimAtPath("/World/Assembly/Child/Panel")
        matrix = UsdGeom.XformCache().GetLocalToWorldTransform(prim)
        self.assertLess(
            (matrix.ExtractTranslation() - Gf.Vec3d(2, 6, 1)).GetLength(), 1e-8
        )
        bounds = scene_geometry.bounds_in_frame(
            stage, str(prim.GetPath()), "/World/Assembly/Child"
        )
        self.assertLess((bounds.GetSize() - Gf.Vec3d(2, 0.10, 2)).GetLength(), 1e-7)
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        self.assertEqual(str(material.GetPath()), "/World/Paint")
        self.assertTrue(UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get())
        self.assertFalse(prim.HasAPI(UsdPhysics.RigidBodyAPI))

    def test_invalid_panel_does_not_author_geometry(self):
        """Reject absent materials and nonpositive metric dimensions."""
        stage = Usd.Stage.CreateInMemory()
        with self.assertRaisesRegex(ValueError, "Missing wall material"):
            WallPanel((0, 0, 0), (1, 1, 1), "/Paint").build(stage, "/Missing")
        wall_materials.surface_material(stage, "/Paint", (1, 0, 0), 0.9, 0)
        with self.assertRaisesRegex(ValueError, "positive meters"):
            WallPanel((0, 0, 0), (1, 0, 1), "/Paint").build(stage, "/Invalid")
        self.assertFalse(stage.GetPrimAtPath("/Missing"))
        self.assertFalse(stage.GetPrimAtPath("/Invalid"))

    def test_partition_can_build_without_room_builder(self):
        """The glass partition owns material setup without importing a wall."""
        stage = Usd.Stage.CreateInMemory()
        layout = json.loads(
            (ROOT / "scenes/versteel_box_pick_place/layout.json").read_text()
        )
        chair_side_glass.build(stage, layout["table2"])
        pane = stage.GetPrimAtPath("/World/Furniture/ChairSideGlass/Unit1/Pane")
        material, _ = UsdShade.MaterialBindingAPI(pane).ComputeBoundMaterial()
        self.assertTrue(material)
        self.assertTrue(
            stage.GetPrimAtPath(str(material.GetPath()) + "/OmniGlass")
            .GetAttribute("inputs:thin_walled")
            .Get()
        )


if __name__ == "__main__":
    unittest.main()
