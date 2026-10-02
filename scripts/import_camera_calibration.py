"""Freeze RGB calibration sources and convert D405's inverse optical model."""

import argparse
import hashlib
import json
import pathlib
import subprocess

import numpy as np
import yaml
from scipy.optimize import least_squares


def distort(points: np.ndarray, coefficients: list) -> np.ndarray:
    """Apply five-term Brown-Conrady to normalized XY coordinates."""
    x, y = points.T
    k1, k2, p1, p2, k3 = coefficients
    radius = x * x + y * y
    radial = 1 + radius * (k1 + radius * (k2 + radius * k3))
    return np.column_stack(
        (
            x * radial + 2 * p1 * x * y + p2 * (radius + 2 * x * x),
            y * radial + p1 * (radius + 2 * y * y) + 2 * p2 * x * y,
        )
    )


def factory_projection(points: np.ndarray, coefficients: list) -> np.ndarray:
    """Match librealsense 2.58.4's inverse-Brown projection implementation.

    The SDK applies radial scaling before its tangential terms for this model.
    This differs slightly from OpenCV; the model name alone is insufficient.
    """
    k1, k2, p1, p2, k3 = coefficients
    radius = np.sum(points**2, axis=1)
    radial = 1 + radius * (k1 + radius * (k2 + radius * k3))
    scaled = points * radial[:, None]
    x, y = scaled.T
    return scaled + np.column_stack(
        (
            2 * p1 * x * y + p2 * (radius + 2 * x * x),
            p1 * (radius + 2 * y * y) + 2 * p2 * x * y,
        )
    )


def forward_approximation(intrinsics: dict) -> tuple:
    """Fit the factory SDK projection to OpenCV; refuse error above 0.1 px."""
    width, height = intrinsics["image_width"], intrinsics["image_height"]
    focal = np.array([intrinsics["fx"], intrinsics["fy"]])
    center = np.array([intrinsics["cx"], intrinsics["cy"]])

    def rays(columns, rows):
        x, y = np.meshgrid(columns, rows)
        # A 5% margin covers rays extending beyond the nominal image domain.
        return (np.column_stack((x.ravel(), y.ravel())) - center) / focal * 1.05

    ideal = rays(np.linspace(0, width - 1, 81), np.linspace(0, height - 1, 61))
    distorted = factory_projection(ideal, intrinsics["distortion_coefficients"])
    result = least_squares(
        lambda coefficients: (
            (distort(ideal, coefficients) - distorted) * focal
        ).ravel(),
        np.array(intrinsics["distortion_coefficients"]),
        xtol=1e-13,
        ftol=1e-13,
        gtol=1e-13,
    )
    # Dense verification is independent of the coarse fitting grid.
    ideal = rays(np.arange(width), np.arange(height))
    distorted = factory_projection(ideal, intrinsics["distortion_coefficients"])
    errors = np.linalg.norm(
        (distort(ideal, result.x) - distorted) * focal, axis=1
    )
    maximum = float(errors.max())
    if not result.success or maximum > 0.1:
        raise ValueError(
            f"Factory-model approximation exceeds 0.1 px: {maximum}"
        )
    return result.x.tolist(), {
        "method": "forward OpenCV fit to librealsense inverse-Brown projection",
        "sdk_version": "2.58.4",
        "reference": (
            "https://github.com/realsenseai/librealsense/"
            "blob/v2.58.4/src/rs.cpp"
        ),
        "fit_grid": [81, 61],
        "verification_ray_grid": [width, height],
        "normalized_domain_margin": 1.05,
        "max_error_px": maximum,
        "rms_error_px": float(np.sqrt(np.mean(errors**2))),
        "limit_px": 0.1,
    }


def source_record(root: pathlib.Path, relative: str) -> tuple:
    """Load one YAML and retain portable provenance without capture images."""
    content = (root / relative).read_bytes()
    value = yaml.safe_load(content)
    record = {
        "path": relative,
        "sha256": hashlib.sha256(content).hexdigest(),
        "timestamp": value["timestamp"],
        "source": value.get("source", "solved"),
    }
    return value, record


def snapshot(source: pathlib.Path) -> dict:
    """Select canonical 480p results; preserve pure-480p alternatives."""
    config = {
        "schema_version": 1,
        "status": "preview_pending_mount_confirmation",
        "resolution": [640, 480],
        "fps": 30,
        "source_repository": "camera_calibration_ur12e",
        "source_revision": subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
        ).strip(),
        "tcp_offset_assumption": (
            "zero; calibration reads actual_tcp, " "not URDF flange"
        ),
        "mounts_unchanged": "unconfirmed",
        "cameras": {},
    }
    for name in ("camera_1", "camera_2", "camera_3"):
        intrinsic, intrinsic_source = source_record(
            source, f"data/{name}/intrinsics/result.yaml"
        )
        extrinsic, extrinsic_source = source_record(
            source, f"data/{name}/handeye/final_result_all_30.yaml"
        )
        if [intrinsic["image_width"], intrinsic["image_height"]] != config[
            "resolution"
        ]:
            raise ValueError(f"Expected 480p intrinsics: {name}")
        if intrinsic["camera_serial"] != extrinsic["camera_serial"]:
            raise ValueError(f"Camera serial mismatch: {name}")
        spec = {
            "serial": intrinsic["camera_serial"],
            "model": "D405" if name == "camera_1" else "D435IF",
            "reference_link": "tool0" if name == "camera_1" else "base",
            "reference_status": (
                "zero_tcp_assumed" if name == "camera_1" else "controller_base"
            ),
            "optical_to_reference": extrinsic["transform"],
            "extrinsics_source": extrinsic_source,
            "extrinsics_original_meaning": extrinsic["transform_meaning"],
            "extrinsics_warnings": extrinsic.get("warnings", []),
            "intrinsics_source": intrinsic_source,
            "intrinsics": {
                key: intrinsic[key] for key in ("fx", "fy", "cx", "cy")
            },
            "source_distortion": intrinsic["distortion_coefficients"],
            "renderer_model": "opencvPinhole",
        }
        if name == "camera_1":
            spec["source_distortion_model"] = intrinsic["factory"][
                "rs_distortion_model"
            ]
            if (
                spec["source_distortion_model"]
                != "distortion.inverse_brown_conrady"
            ):
                raise ValueError("Unexpected D405 factory model")
            spec["renderer_distortion"], spec["conversion"] = (
                forward_approximation(intrinsic)
            )
        else:
            spec["source_distortion_model"] = "opencv_brown_conrady"
            spec["renderer_distortion"] = spec["source_distortion"]
            spec["blend"] = intrinsic["blend"]
            alternative, provenance = source_record(
                source, f"data/{name}/intrinsics/result_480p_solved.yaml"
            )
            spec["pure_480p_alternative"] = {
                "source": provenance,
                "intrinsics": {
                    key: alternative[key] for key in ("fx", "fy", "cx", "cy")
                },
                "distortion": alternative["distortion_coefficients"],
                "status": (
                    "comparison_only; distortion " "observability inconclusive"
                ),
            }
        config["cameras"][name] = spec
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot(args.source), indent=2) + "\n")
