"""Author portable native RTX RGB cameras from a frozen calibration snapshot."""

import json
import pathlib

from pxr import Gf, Sdf, Usd, UsdGeom  # pylint: disable=import-error

CONFIG = "config/cameras/rig_480p.json"
PREFIX = "omni:lensdistortion:opencvPinhole:"
SCHEMA = "OmniLensDistortionOpenCvPinholeAPI"


def optical_matrix(spec: dict):
    """Transpose column-vector optical extrinsics for USD row vectors."""
    values = spec["optical_to_reference"]
    return Gf.Matrix4d(
        tuple(tuple(values[j][i] for j in range(4)) for i in range(4))
    )


def reference_link(stage, name: str):
    """Require one actual robot frame; do not select Hand-E's tool0."""
    links = [
        prim
        for prim in Usd.PrimRange(stage.GetPrimAtPath("/World/UR12e"))
        if prim.GetName() == name
        and (name != "base" or prim.GetParent().GetName() == "base_link")
    ]
    if len(links) != 1:
        raise ValueError(f"Expected one UR12e reference frame: {name}")
    return links[0]


def build(stage, config: dict) -> dict:
    """Attach wrist to tool0 and fixed cameras to the controller base."""
    paths = {}
    conversion = Gf.Matrix4d().SetScale(Gf.Vec3d(1, -1, -1))
    for name, spec in config["cameras"].items():
        parent = reference_link(stage, spec["reference_link"])
        path = str(parent.GetPath()) + "/" + name
        camera = UsdGeom.Camera.Define(stage, path)
        camera.MakeMatrixXform().Set(conversion * optical_matrix(spec))
        author_optics(camera, spec, config["resolution"])
        prim = camera.GetPrim()
        prim.CreateAttribute(
            "calibration:serial", Sdf.ValueTypeNames.String
        ).Set(spec["serial"])
        prim.CreateAttribute(
            "calibration:status", Sdf.ValueTypeNames.String
        ).Set(config["status"])
        prim.CreateAttribute("calibration:fps", Sdf.ValueTypeNames.Int).Set(
            config["fps"]
        )
        paths[name] = path
    return paths


def author_optics(camera, spec: dict, resolution: list) -> None:
    """Encode exact K/D in the native schema and a nominal pinhole fallback."""
    width, height = resolution
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.005, 100))
    camera.CreateFStopAttr(0)
    # Portable pinhole fallback; RTX uses the complete schema parameters.
    intrinsic = spec["intrinsics"]
    focal = intrinsic["fx"] * 20.955 / width
    camera.CreateFocalLengthAttr(focal)
    camera.CreateHorizontalApertureAttr(20.955)
    camera.CreateVerticalApertureAttr(focal * height / intrinsic["fy"])
    prim = camera.GetPrim()
    # Token authoring also works in standalone USD without Kit's registry.
    prim.AddAppliedSchema(SCHEMA)
    prim.CreateAttribute(
        "omni:lensdistortion:model", Sdf.ValueTypeNames.Token, custom=False
    ).Set("opencvPinhole")
    prim.CreateAttribute(
        PREFIX + "imageSize", Sdf.ValueTypeNames.Int2, custom=False
    ).Set(Gf.Vec2i(width, height))
    for key, value in intrinsic.items():
        prim.CreateAttribute(
            PREFIX + key, Sdf.ValueTypeNames.Float, custom=False
        ).Set(value)
    for key, value in zip(
        ("k1", "k2", "p1", "p2", "k3"),
        spec["renderer_distortion"],
        strict=True,
    ):
        prim.CreateAttribute(
            PREFIX + key, Sdf.ValueTypeNames.Float, custom=False
        ).Set(value)


def configure(root: pathlib.Path) -> dict:
    """Update saved camera prims without Kit or physical devices."""
    stage = Usd.Stage.Open(
        str(root / "scenes/versteel_box_pick_place/scene.usda")
    )
    paths = build(stage, json.loads((root / CONFIG).read_text()))
    stage.GetRootLayer().Save()
    return paths


if __name__ == "__main__":
    print(
        json.dumps(
            configure(pathlib.Path(__file__).resolve().parents[1]), indent=2
        )
    )
