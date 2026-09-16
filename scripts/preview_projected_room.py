"""Create CPU background projection checks, separate from Isaac rendering."""

import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]


def room_hits(settings: dict, eye: tuple, yaw: float) -> np.ndarray:
    """Intersect a 90-degree camera view with finite room planes."""
    width, height = 800, 500
    x, y = np.meshgrid(
        (np.arange(width) + 0.5 - width / 2) / (width / 2),
        (np.arange(height) + 0.5 - height / 2) / (width / 2),
    )
    angle = np.radians(yaw)
    rays = np.stack(
        (
            np.cos(angle) + x * np.sin(angle),
            np.sin(angle) - x * np.cos(angle),
            -y,
        ),
        axis=-1,
    )
    bounds = np.array([settings["bounds_m"][axis] for axis in "xyz"])
    limits = np.where(rays > 0, bounds[:, 1], bounds[:, 0])
    with np.errstate(divide="ignore", invalid="ignore"):
        distances = (limits - eye) / rays
    return np.array(eye) + rays * np.min(distances, axis=-1)[..., None]


def view(
    texture: np.ndarray, settings: dict, eye: tuple, yaw: float
) -> np.ndarray:
    """Sample fixed room textures from a moving observer."""
    delta = room_hits(settings, eye, yaw) - settings["capture_position_m"]
    angle = np.radians(settings["projection_yaw_deg"])
    forward = delta[..., 0] * np.cos(angle) + delta[..., 1] * np.sin(angle)
    left = -delta[..., 0] * np.sin(angle) + delta[..., 1] * np.cos(angle)
    u = 0.5 - np.arctan2(left, forward) / (2 * np.pi)
    v = 0.5 - np.arcsin(delta[..., 2] / np.linalg.norm(delta, axis=-1)) / np.pi
    rows, columns = texture.shape[:2]
    # A nearest-pixel diagnostic is sufficient to show geometry and parallax.
    return texture[
        np.clip((v * rows).astype(int), 0, rows - 1),
        (u * columns).astype(int) % columns,
    ]


def main() -> None:
    """Save side-by-side before/after views and label their limited scope."""
    directory = ROOT / "scenes/versteel_box_pick_place"
    settings = json.loads((directory / "room.json").read_text())
    texture = np.array(
        Image.open(directory / settings["texture"]).convert("RGB")
    )
    sheet = Image.new("RGB", (1600, 1110), "#20242a")
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (15, 12),
        "CPU projection only / not Isaac / task geometry omitted",
        fill="white",
    )
    origin = tuple(settings["capture_position_m"])
    forward_shift = tuple(a + b for a, b in zip(origin, (0.1, 0, 0)))
    left_shift = tuple(a + b for a, b in zip(origin, (0, 0.1, 0)))
    for index, (title, eye, yaw) in enumerate(
        (
            ("Forward: capture position", origin, 0),
            ("Forward: observer moved +Y 0.10 m", left_shift, 0),
            ("Right / blinds: capture position", origin, -90),
            ("Right / blinds: observer moved +X 0.10 m", forward_shift, -90),
        )
    ):
        x, y = index % 2 * 800, 40 + index // 2 * 535
        sheet.paste(Image.fromarray(view(texture, settings, eye, yaw)), (x, y))
        draw.text((x + 12, y + 510), title, fill="white")
    output = ROOT / "artifacts/projected-room/projection-preview.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)
    print(output)


if __name__ == "__main__":
    main()
