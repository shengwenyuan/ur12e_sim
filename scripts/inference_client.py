"""Run an isolated contact-physics inference client; no hardware backends."""

import argparse
import json
import pathlib
import time

import _physics_app


def infer(app, root, args):
    """Run a bounded synchronous episode and preserve target/actual traces."""
    # Kit extensions must be imported after SimulationApp startup.
    # pylint: disable=import-outside-toplevel,import-error
    from physics.world import World
    from physics.cameras import Cameras
    from physics.client import Client, Session, Timing

    # pylint: enable=import-outside-toplevel,import-error

    config = json.loads(args.cameras.read_text())
    world = World(root, args.scene.resolve())
    world.step(480)
    cameras = Cameras(world, config)
    client = Client(args.server, timeout=args.timeout)
    session = Session(
        world,
        cameras,
        client,
        Timing(args.action_hz),
        render=app.update if args.gui else None,
    )
    start = time.monotonic()
    try:
        for index in range(args.chunks):
            session.cycle(args.prompt, args.execute_steps)
            print(
                "CHUNK",
                index + 1,
                "SIM_TIME",
                world.time,
                "WAIT_SECONDS",
                client.wait_seconds,
                flush=True,
            )
        return {
            "passed": True,
            "chunks": client.request_count,
            "inference_wall_seconds": client.wait_seconds,
            "elapsed_wall_seconds": time.monotonic() - start,
            "executed_sim_seconds": len(session.trace) / args.action_hz,
            "physics_hz": 240,
            "action_hz": args.action_hz,
            "calibration_status": config["calibration_status"],
            "server": client.capabilities,
        }
    finally:
        (args.output / "trace.json").write_text(
            json.dumps(session.trace, indent=2)
        )
        client.close()
        cameras.close()


def main():
    """Require action timing explicitly; fixture cameras require opt-in."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--scene", type=pathlib.Path, required=True)
    parser.add_argument("--cameras", type=pathlib.Path, required=True)
    parser.add_argument("--action-hz", type=float, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--chunks", type=int, default=3)
    parser.add_argument("--execute-steps", type=int)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--allow-fixture-cameras", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.chunks <= 0 or args.timeout <= 0:
        parser.error("Chunks and timeout must be positive")
    config = json.loads(args.cameras.read_text())
    if config["calibration_status"] != "fixture_only":
        parser.error("Calibrated camera support awaits the supplied parameters")
    if not args.allow_fixture_cameras:
        parser.error("Temporary cameras require --allow-fixture-cameras")
    return _physics_app.run(args, infer)


if __name__ == "__main__":
    raise SystemExit(main())
