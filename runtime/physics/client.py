"""Synchronous model-neutral inference on a stepped physics world."""

from dataclasses import dataclass
import math
import time
import uuid

import numpy as np
from websockets.sync.client import connect

from . import wire

ENVELOPE = ("protocol", "request_id", "epoch", "anchor", "contract_id", "model")


@dataclass(frozen=True)
class Timing:
    """Explicit action period; viewport rate is independent of observations."""

    action_hz: float
    render_hz: float = 10

    def __post_init__(self):
        if (
            not math.isfinite(self.action_hz)
            or self.action_hz <= 0
            or not (240 / self.action_hz).is_integer()
        ):
            raise ValueError("Action Hz must divide the 240 Hz physics rate")
        if not 0 < self.render_hz <= 10:
            raise ValueError("Render Hz must be in (0, 10]")

    @property
    def substeps(self) -> int:
        """Number of 240 Hz physical steps per model action."""
        return round(240 / self.action_hz)


class Client:
    """Use the inference protocol without importing a model or robot SDK."""

    def __init__(self, url: str, timeout: float = 60):
        self.timeout = timeout
        self.socket = connect(
            url, open_timeout=timeout, max_size=wire.MAX_BYTES, compression=None
        )
        try:
            self.capabilities = wire.unpack(self.socket.recv(timeout=timeout))
            caps = self.capabilities
            horizon = caps.get("horizon")
            if (
                not isinstance(horizon, int)
                or isinstance(horizon, bool)
                or not 0 < horizon <= 1000
                or not all(
                    isinstance(caps.get(k), str) and caps[k]
                    for k in ("contract_id", "model")
                )
            ):
                raise ValueError("Invalid server capabilities")
        except (ValueError, TypeError, AttributeError, TimeoutError):
            self.close()
            raise
        self.wait_seconds = 0.0
        self.request_count = 0

    def infer(
        self, observation: dict, epoch: int, anchor: int, prompt: str
    ) -> np.ndarray:
        """Send a no-prefix request; reject stale or malformed action chunks."""
        caps = self.capabilities
        request = {
            "protocol": 1,
            "request_id": uuid.uuid4().hex,
            "epoch": epoch,
            "anchor": anchor,
            "contract_id": caps["contract_id"],
            "model": caps["model"],
            "observation": {**observation, "prompt": prompt},
            "prefix": np.empty((0, 7), dtype=np.float32),
            "delay": 0,
        }
        start = time.monotonic()
        try:
            self.socket.send(wire.pack(request))
            response = wire.unpack(self.socket.recv(timeout=self.timeout))
        finally:
            self.wait_seconds += time.monotonic() - start
        for key in ENVELOPE:
            if response.get(key) != request[key]:
                raise ValueError(f"Response identity mismatch: {key}")
        actions = np.asarray(response["actions"], dtype=float)
        if (
            actions.shape != (caps["horizon"], 7)
            or not np.isfinite(actions).all()
            or np.any((actions[:, 6] < 0) | (actions[:, 6] > 255))
        ):
            raise ValueError("Malformed action chunk")
        self.request_count += 1
        return actions

    def close(self) -> None:
        """Disconnect without advancing, resetting or opening the gripper."""
        self.socket.close()


# The constructor names its four owned dependencies and optional viewport.
# pylint: disable=too-many-arguments
class Session:
    """Observe, infer while frozen, then physically execute a checked chunk."""

    def __init__(
        self,
        world,
        cameras,
        client: Client,
        timing: Timing,
        *,
        render=None,
    ):
        self.world = world
        self.cameras = cameras
        self.client = client
        self.timing = timing
        self.render = render
        self.next_render = world.time + 1 / timing.render_hz
        self.trace = []

    def cycle(self, prompt: str, execute_steps: int | None = None) -> dict:
        """Validate the complete chunk before applying any of its actions."""
        observation = self.cameras.capture()
        epoch, step, stamp = (
            self.world.epoch,
            self.world.steps,
            self.world.clock,
        )
        before = self.world.state().copy()
        actions = self.client.infer(observation, epoch, step, prompt)
        if (
            self.world.epoch != epoch
            or self.world.steps != step
            or self.world.clock != stamp
            or not np.array_equal(before, self.world.state())
        ):
            raise RuntimeError("Inference wait changed or reset the world")
        for action in actions:
            self.world.validate(action)
        count = len(actions) if execute_steps is None else execute_steps
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 < count <= len(actions)
        ):
            raise ValueError("Invalid executed chunk prefix length")
        for action in actions[:count]:
            self.world.command(action)
            self.world.step(self.timing.substeps)
            self.trace.append(
                {
                    "epoch": epoch,
                    "sim_time": self.world.time,
                    "target": action.tolist(),
                    "actual": self.world.state().tolist(),
                }
            )
            if self.render and self.world.time >= self.next_render:
                stamp = self.world.clock
                self.render()
                if self.world.clock != stamp:
                    raise RuntimeError("Viewport advanced physics")
                self.next_render = self.world.time + 1 / self.timing.render_hz
        return observation

    def reset(self) -> None:
        """Reload saved initialization and revoke the previous episode epoch."""
        self.cameras.close()
        self.world.reset()
        self.world.step(480)
        self.cameras.rebuild()
        self.next_render = self.world.time + 1 / self.timing.render_hz
