"""Display a saved scene until the user closes the Isaac window."""

import argparse
import json
import pathlib
import time


def main():
    """No robot connection or physics timeline is created."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    # Isaac exists only on Ubuntu; initialize Kit before its dependent imports.
    # pylint: disable-next=import-outside-toplevel,import-error
    from isaacsim import SimulationApp

    app = SimulationApp(
        {
            "headless": False,
            "width": 1280,
            "height": 720,
            "window_width": 1440,
            "window_height": 900,
            "open_usd": str(args.scene.resolve()),
            "multi_gpu": False,
        }
    )
    # Kit-dependent imports must follow application startup.
    # pylint: disable=import-outside-toplevel,import-error
    import carb.settings
    import omni.kit.viewport.utility
    import omni.usd

    settings = carb.settings.get_settings()
    settings.set("/app/window/title", "UR12e Scene - Static Preview")
    viewport = omni.kit.viewport.utility.get_active_viewport()
    viewport.camera_path = "/World/Camera"
    report = {
        "state": "starting",
        "robot_meshes_loaded": bool(
            omni.usd.get_context().get_stage().GetPrimAtPath("/World/UR12e")
        ),
        "robot_control": False,
        "physics_integration": False,
    }
    frames = 0
    try:
        while app.is_running():
            app.update()
            frames += 1
            if frames == 120:
                stage = omni.usd.get_context().get_stage()
                assert stage.GetPrimAtPath("/World/Table/Top")
                report.update(
                    state="viewport_ready",
                    update_frames=frames,
                    camera=str(viewport.camera_path),
                )
                args.report.write_text(
                    json.dumps(report, indent=2), encoding="utf-8"
                )
                print(
                    "VIEWPORT_READY: static scene; close window to exit.",
                    flush=True,
                )
            time.sleep(1 / 60)
    finally:
        app.close()
        report.update(state="closed", update_frames=frames)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
