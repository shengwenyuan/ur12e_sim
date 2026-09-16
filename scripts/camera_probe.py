"""Validate frozen-world three-view rendering with temporary camera poses."""

import json

import _physics_app

# Kit-only imports stay local; each diagnostic owns one bounded fixture.
# pylint: disable=too-many-locals


def probe(_app, root, args):
    """Run the diagnostic after Kit has initialized its extension imports."""
    # Kit imports must follow SimulationApp startup.
    # pylint: disable=import-outside-toplevel,import-error
    import numpy as np
    from PIL import Image
    from physics.world import World
    from physics.cameras import Cameras
    from physics.client import Session, Timing
    from unittest import mock

    world = World(root, root / "scenes/tabletop_home/scene.usda")
    world.step(240)
    config = json.loads((root / "tests/fixtures/cameras.json").read_text())
    cameras = Cameras(world, config)
    before = cameras.capture()
    for role, image in before["images"].items():
        Image.fromarray(image).save(args.output / (role + ".png"))
    world.command(world.home + np.array([0.15, 0, 0, 0, 0, 0, 0]))
    world.step(240)
    after = cameras.capture()
    differences = {
        r: float(
            np.mean(abs(after["images"][r].astype(float) - before["images"][r]))
        )
        for r in before["images"]
    }
    report = {
        "passed": all(v > 0 for v in differences.values()),
        "changes": differences,
        "first_sim_time": before["sim_time"],
        "second_sim_time": after["sim_time"],
        "shapes": {r: list(x.shape) for r, x in after["images"].items()},
        "calibration_status": "fixture_only",
    }
    # This diagnostic uses a hold-only fake policy with actual world stepping.
    client = mock.Mock()
    client.infer.side_effect = lambda obs, *_: np.tile(obs["state"], (8, 1))
    session = Session(world, cameras, client, Timing(30), render=_app.update)
    session.cycle("hold fixture")
    session.reset()
    session.cycle("hold fixture after reset")
    reset = cameras.capture()
    report["session_actions"] = len(session.trace)
    report["session_epochs"] = sorted({row["epoch"] for row in session.trace})
    report["reset_epoch"] = reset["epoch"]
    report["reset_images_valid"] = all(
        im.shape == (480, 640, 3) for im in reset["images"].values()
    )
    report["passed"] &= (
        report["reset_epoch"] == 1 and report["reset_images_valid"]
    )
    cameras.close()
    return report


if __name__ == "__main__":
    raise SystemExit(_physics_app.diagnostic(probe))
