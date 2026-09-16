"""Coherent three-view observations from one explicitly frozen physics state."""

import numpy as np

# OpenUSD and Kit extensions are supplied by the Ubuntu Isaac runtime.
# pylint: disable=import-error
import omni.replicator.core as rep
from pxr import Gf, UsdGeom
from isaacsim.core.simulation_manager import SimulationManager as Sim


class Cameras:
    """Fixture views are uncalibrated and must not be labeled as lab cameras."""

    def __init__(self, world, config: dict):
        self.world = world
        self.config = config
        if set(config["cameras"]) != {"wrist", "third_left", "third_right"}:
            raise ValueError("Exactly three named camera roles are required")
        if config["calibration_status"] != "fixture_only":
            raise ValueError(
                "Calibrated camera adapter awaits supplied intrinsics"
            )
        self.rebuild()

    def rebuild(self) -> None:
        """Create render products for the current stage after startup/reset."""
        world, config = self.world, self.config
        self.annotators = {}
        rep.orchestrator.set_capture_on_play(False)
        for role, spec in config["cameras"].items():
            parent = world.stage.GetPrimAtPath("/World")
            if spec.get("mount_link"):
                parent = next(
                    p
                    for p in world.stage.Traverse()
                    if p.GetName() == spec["mount_link"]
                )
            camera = UsdGeom.Camera.Define(
                world.stage, str(parent.GetPath()) + "/PolicyCamera_" + role
            )
            local = (
                Gf.Matrix4d()
                .SetLookAt(
                    Gf.Vec3d(*spec["eye_m"]),
                    Gf.Vec3d(*spec["look_at_m"]),
                    Gf.Vec3d(0, 0, 1),
                )
                .GetInverse()
            )
            if parent.GetPath() != "/World":
                local *= (
                    UsdGeom.XformCache()
                    .GetLocalToWorldTransform(parent)
                    .GetInverse()
                )
            camera.AddTransformOp().Set(local)
            width, height = config["resolution"]
            camera.CreateHorizontalApertureAttr(20.955)
            camera.CreateVerticalApertureAttr(20.955 * height / width)
            camera.CreateFocalLengthAttr(spec["fx_px"] * 20.955 / width)
            camera.CreateClippingRangeAttr(Gf.Vec2f(0.01, 100))
            product = rep.create.render_product(
                str(camera.GetPath()), (width, height)
            )
            annotator = rep.AnnotatorRegistry.get_annotator("rgb")
            annotator.attach(product)
            self.annotators[role] = (annotator, product)

    def capture(self) -> dict:
        """Render all views without advancing the physical world."""
        before = self.world.state().copy()
        time_before = Sim.get_simulation_time()
        rep.orchestrator.step(
            rt_subframes=2, delta_time=0.0, pause_timeline=False
        )
        images = {
            role: np.array(pair[0].get_data()[..., :3], copy=True)
            for role, pair in self.annotators.items()
        }
        if Sim.get_simulation_time() != time_before or not np.array_equal(
            before, self.world.state()
        ):
            raise RuntimeError("Rendering advanced physics unexpectedly")
        for role, image in images.items():
            if (
                image.shape
                != (
                    self.config["resolution"][1],
                    self.config["resolution"][0],
                    3,
                )
                or image.dtype != np.uint8
            ):
                raise RuntimeError(
                    f"Invalid rendered RGB: {role}: {image.shape}"
                )
        return {
            "state": before,
            "images": images,
            "sim_time": self.world.time,
            "epoch": self.world.epoch,
            "calibration_status": self.config["calibration_status"],
        }

    def close(self) -> None:
        """Release render products before reopening the physical scene."""
        for annotator, product in self.annotators.values():
            annotator.detach(product)
            product.destroy()
        self.annotators.clear()
