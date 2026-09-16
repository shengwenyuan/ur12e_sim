"""Protocol faults and scheduling invariants without Kit or robot access."""

import pathlib
import sys
import threading
import unittest
from functools import partial
from unittest import mock

import numpy as np
from websockets.sync.server import serve

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / ".deps/inference")]
# Test runner resolves standalone imports without installing the scene project.
# pylint: disable=wrong-import-position,import-error
from physics.client import Client, Session, Timing
from physics import wire
from fake_server import handler

# pylint: enable=wrong-import-position,import-error


def observation():
    """One coherent fixture observation with production role names and shape."""
    return {
        "state": np.zeros(7),
        "images": {
            name: np.zeros((480, 640, 3), dtype=np.uint8)
            for name in ("wrist", "third_left", "third_right")
        },
    }


class InferenceTest(unittest.TestCase):
    """Exercise real WebSocket bytes and clock/action failure boundaries."""

    def connect(self, *, delay=0, fault=None, timeout=1):
        """Start only an ephemeral localhost fixture and register cleanup."""
        server = serve(
            partial(handler, delay=delay, fault=fault),
            "127.0.0.1",
            0,
            compression=None,
            max_size=wire.MAX_BYTES,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        client = Client(
            f"ws://127.0.0.1:{server.socket.getsockname()[1]}", timeout=timeout
        )
        self.addCleanup(client.close)
        return client

    def test_successful_delayed_wire_exchange(self):
        client = self.connect(delay=0.03)
        result = client.infer(observation(), 7, 120, "fixture")
        self.assertEqual(result.shape, (8, 7))
        self.assertAlmostEqual(result[-1, 0], 0.016)
        self.assertGreaterEqual(client.wait_seconds, 0.03)

    def test_stale_epoch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "epoch"):
            self.connect(fault="stale").infer(observation(), 7, 120, "x")

    def test_nan_at_chunk_end_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Malformed"):
            self.connect(fault="nan").infer(observation(), 7, 120, "x")

    def test_network_timeout(self):
        with self.assertRaises(TimeoutError):
            self.connect(delay=0.2, timeout=0.05).infer(
                observation(), 7, 120, "x"
            )

    def test_wire_rgb_and_state_round_trip(self):
        obs = observation()
        obs["images"]["wrist"][2, 3] = (1, 127, 255)
        decoded = wire.unpack(wire.pack(obs))
        np.testing.assert_array_equal(
            decoded["images"]["wrist"], obs["images"]["wrist"]
        )

    def test_wire_rejects_object_arrays(self):
        with self.assertRaises(ValueError):
            wire.pack(np.array([object()], dtype=object))

    def test_rate_must_be_positive_and_integral_substeps(self):
        for rate in (0, -1, float("nan"), float("inf"), 31):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                Timing(rate)
        self.assertEqual(Timing(30).substeps, 8)
        self.assertEqual(Timing(120).substeps, 2)

    def session(self):
        """Create a deterministic test world for scheduler ownership checks."""
        world = mock.Mock(steps=0, epoch=0, clock=0, time=0)
        world.state.return_value = np.zeros(7)
        cameras = mock.Mock()
        cameras.capture.return_value = observation()
        client = mock.Mock()
        client.infer.return_value = np.zeros((8, 7))
        return Session(world, cameras, client, Timing(30))

    def test_prefix_execution_steps_at_model_rate(self):
        session = self.session()
        session.cycle("x", 3)
        self.assertEqual(session.world.step.call_args_list, [mock.call(8)] * 3)
        self.assertEqual(session.world.validate.call_count, 8)

    def test_invalid_later_target_prevents_all_motion(self):
        session = self.session()
        session.world.validate.side_effect = [None, ValueError("joint limit")]
        with self.assertRaisesRegex(ValueError, "joint limit"):
            session.cycle("x")
        session.world.command.assert_not_called()
        session.world.step.assert_not_called()

    def test_reset_while_waiting_discards_response(self):
        session = self.session()

        def reset_during_inference(*_args):
            session.world.epoch += 1
            return np.zeros((8, 7))

        session.client.infer.side_effect = reset_during_inference
        with self.assertRaisesRegex(RuntimeError, "reset"):
            session.cycle("x")
        session.world.command.assert_not_called()

    def test_unowned_physics_step_is_detected(self):
        session = self.session()

        def step_during_inference(*_args):
            session.world.clock += 1 / 240
            return np.zeros((8, 7))

        session.client.infer.side_effect = step_during_inference
        with self.assertRaisesRegex(RuntimeError, "changed"):
            session.cycle("x")
        session.world.command.assert_not_called()

    def test_render_cannot_step_physics(self):
        session = self.session()
        session.next_render = 0

        def render():
            session.world.clock += 1 / 240

        session.render = render
        with self.assertRaisesRegex(RuntimeError, "Viewport"):
            session.cycle("x")
        self.assertEqual(session.world.step.call_count, 1)

    def test_invalid_prefix_never_executes(self):
        for count in (0, 9, 1.5, True):
            session = self.session()
            with self.subTest(count=count), self.assertRaises(ValueError):
                session.cycle("x", count)
            session.world.step.assert_not_called()


if __name__ == "__main__":
    unittest.main()
