"""Render the three saved calibrated RGB views without playing physics."""

import hashlib
import importlib.metadata
import json

import _physics_app


def without_render_bookkeeping(content: str) -> str:
    """Compare saved scene fields separately from Kit's transient products."""
    # The schema library becomes available after Kit startup.
    from pxr import Sdf  # pylint: disable=import-outside-toplevel,import-error

    layer = Sdf.Layer.CreateAnonymous()
    layer.ImportFromString(content)
    if "Render" in layer.rootPrims:
        del layer.rootPrims["Render"]
    return layer.ExportToString()


# The bounded review records all three render products and their poses.
# pylint: disable=too-many-locals


def preview(_app, root, args):
    """Capture 480p RGB from static HOME with native lens distortion."""
    # Kit imports must follow SimulationApp startup.
    # pylint: disable=import-outside-toplevel,import-error
    import numpy as np
    from PIL import Image
    import omni.usd
    import omni.timeline
    import omni.replicator.core as rep
    from pxr import UsdGeom
    import calibrated_cameras

    scene = root / "scenes/versteel_box_pick_place/scene.usda"
    checksum = hashlib.sha256(scene.read_bytes()).hexdigest()
    context = omni.usd.get_context()
    if not context.open_stage(str(scene)):
        raise RuntimeError("Could not open the workcell")
    stage = context.get_stage()
    original = stage.GetRootLayer().ExportToString()

    stage.SetEditTarget(stage.GetSessionLayer())
    config = json.loads((root / calibrated_cameras.CONFIG).read_text())
    timeline = omni.timeline.get_timeline_interface()
    if timeline.is_playing() or timeline.get_current_time() != 0:
        raise RuntimeError("Preview requires a stopped, zero-time timeline")
    rep.orchestrator.set_capture_on_play(False)
    captures = {}
    cache = UsdGeom.XformCache()
    for name, spec in config["cameras"].items():
        parent = calibrated_cameras.reference_link(
            stage, spec["reference_link"]
        )
        path = str(parent.GetPath()) + "/" + name
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.HasAPI(calibrated_cameras.SCHEMA):
            raise RuntimeError(
                f"Native OpenCV camera schema unavailable: {path}"
            )
        product = rep.create.render_product(path, tuple(config["resolution"]))
        annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        annotator.attach(product)
        captures[name] = (
            annotator,
            product,
            cache.GetLocalToWorldTransform(prim),
        )
    try:
        rep.orchestrator.step(
            rt_subframes=16, delta_time=0.0, pause_timeline=False
        )
        views = {}
        for name, (annotator, _, matrix) in captures.items():
            image = np.array(annotator.get_data()[..., :3], copy=True)
            if (
                image.shape != (480, 640, 3)
                or image.dtype != np.uint8
                or np.ptp(image) == 0
            ):
                raise RuntimeError(f"Invalid RGB image: {name}: {image.shape}")
            Image.fromarray(image).save(args.output / (name + ".png"))
            views[name] = {
                "image": name + ".png",
                "serial": config["cameras"][name]["serial"],
                "shape": list(image.shape),
                "usd_to_world_row_matrix": [list(row) for row in matrix],
            }
    finally:
        for annotator, product, _ in captures.values():
            annotator.detach(product)
            product.destroy()
    # Kit adds /Render products relationships to the root even when products
    # are session-only. Verify all scene fields, then restore that bookkeeping.
    current = stage.GetRootLayer().ExportToString()
    if without_render_bookkeeping(current) != without_render_bookkeeping(
        original
    ):
        raise RuntimeError("Rendering changed non-render scene fields")
    stage.GetRootLayer().ImportFromString(original)
    if timeline.is_playing() or timeline.get_current_time() != 0:
        raise RuntimeError("Rendering advanced the timeline")
    if (
        stage.GetRootLayer().ExportToString() != original
        or hashlib.sha256(scene.read_bytes()).hexdigest() != checksum
    ):
        raise RuntimeError("Preview modified the saved workcell")
    return {
        "passed": True,
        "runtime": importlib.metadata.version("isaacsim"),
        "scene_sha256": checksum,
        "config_sha256": hashlib.sha256(
            (root / calibrated_cameras.CONFIG).read_bytes()
        ).hexdigest(),
        "calibration_status": config["status"],
        "physics_steps": 0,
        "timeline_time_s": timeline.get_current_time(),
        "hardware_control": False,
        "views": views,
        "user_visual_acceptance": "PENDING",
    }


if __name__ == "__main__":
    raise SystemExit(_physics_app.diagnostic(preview))
