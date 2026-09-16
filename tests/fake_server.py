"""Local protocol fixture: delayed, small joint ramps; no model or hardware."""

import argparse
import pathlib
import sys
import time
from functools import partial

import numpy as np
from websockets.sync.server import serve

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / ".deps/inference")]
# Standalone fixture resolves the project runtime before importing it.
# pylint: disable=wrong-import-position,import-error
from physics import wire
from physics.client import ENVELOPE

# pylint: enable=wrong-import-position,import-error


def handler(socket, *, delay=0.5, fault=None):
    """Return a synthetic chunk, optionally violating its response contract."""
    socket.send(
        wire.pack(
            {
                "model": "fake-contact",
                "horizon": 8,
                "rtc": False,
                "max_delay": 0,
                "contract_id": "fake-contact-v1",
            }
        )
    )
    for raw in socket:
        request = wire.unpack(raw)
        images = request["observation"]["images"]
        assert set(images) == {"wrist", "third_left", "third_right"}
        assert all(im.shape == (480, 640, 3) for im in images.values())
        assert request["delay"] == 0 and request["prefix"].shape == (0, 7)
        actions = np.tile(request["observation"]["state"], (8, 1))
        actions[:, 0] += np.linspace(0.002, 0.016, 8)
        response = {k: request[k] for k in ENVELOPE}
        if fault == "nan":
            actions[-1, 0] = np.nan
        elif fault == "stale":
            response["epoch"] -= 1
        time.sleep(delay)
        socket.send(wire.pack({**response, "actions": actions}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--fault", choices=["nan", "stale"])
    args = parser.parse_args()
    with serve(
        partial(handler, delay=args.delay, fault=args.fault),
        "127.0.0.1",
        args.port,
        max_size=wire.MAX_BYTES,
        compression=None,
    ) as server:
        print("FAKE_SERVER_READY", flush=True)
        server.serve_forever()
