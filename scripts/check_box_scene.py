"""Render the saved box workcell and check a no-action physical settle."""

import json
import _physics_app


def probe(app, root, args):
    """Capture the authored view and check static/dynamic asset semantics."""
    # Kit imports must follow application startup.
    # pylint: disable=import-outside-toplevel,import-error,too-many-locals
    import numpy as np
    import omni.replicator.core as rep
    from PIL import Image
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade
    from isaacsim.core.experimental.prims import RigidPrim
    from physics.world import World

    scene = root / "scenes/versteel_box_pick_place/scene.usda"
    layout = json.loads(scene.with_name("layout.json").read_text())
    tabletop_height = layout["table"]["top_surface_height_m"]
    world = World(root, scene)
    table = world.stage.GetPrimAtPath("/World/Table")
    assert not UsdPhysics.RigidBodyAPI(table).GetRigidBodyEnabledAttr().Get()
    props = RigidPrim(
        ["/World/Props/OpenDynamixelBox", "/World/Props/RedCube"]
    )
    initial = props.get_world_poses()[0].numpy().copy()
    rep.orchestrator.set_capture_on_play(False)
    product = rep.create.render_product("/World/Camera", (1600, 1000))
    annotator = rep.AnnotatorRegistry.get_annotator("rgb")
    annotator.attach(product)
    rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=False)
    Image.fromarray(annotator.get_data()[..., :3]).save(
        args.output / "preview.png"
    )
    world.step(480)
    final = props.get_world_poses()[0].numpy().copy()
    rep.orchestrator.step(rt_subframes=4, delta_time=0.0, pause_timeline=False)
    Image.fromarray(annotator.get_data()[..., :3]).save(
        args.output / "settled.png"
    )
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(), ["default", "render", "proxy"]
    )
    clearance = {}
    for name in ("OpenDynamixelBox", "RedCube"):
        prim = world.stage.GetPrimAtPath("/World/Props/" + name)
        bounds = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        clearance[name] = float(bounds.GetMin()[2] - tabletop_height)
    paper = next(
        p
        for p in Usd.PrimRange(
            world.stage.GetPrimAtPath("/World/Props/OpenDynamixelBox")
        )
        if p.HasAPI(UsdPhysics.CollisionAPI)
    )
    material, _ = UsdShade.MaterialBindingAPI(paper).ComputeBoundMaterial(
        materialPurpose="physics"
    )
    friction = UsdPhysics.MaterialAPI(material).GetDynamicFrictionAttr().Get()
    report = {
        "passed": (
            all(abs(z) < 0.002 for z in clearance.values())
            and float(np.max(abs(final[:, :2] - initial[:, :2]))) < 0.002
            and abs(friction - 0.4) < 1e-6
        ),
        "simulation_seconds": world.time,
        "initial_positions": initial.tolist(),
        "final_positions": final.tolist(),
        "support_clearance_m": clearance,
        "paper_dynamic_friction": friction,
        "table_remains_static": True,
        "hardware_control": False,
    }
    (args.output / "positions.json").write_text(json.dumps(report, indent=2))
    annotator.detach(product)
    product.destroy()
    app.update()
    return report


if __name__ == "__main__":
    raise SystemExit(_physics_app.diagnostic(probe))
