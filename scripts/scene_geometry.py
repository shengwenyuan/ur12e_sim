"""Independent measurements in explicit local coordinate frames."""

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom

# pylint: enable=import-error


def table_frame(corners: dict) -> tuple:
    """Return ground B and unit vectors A-to-B / B-to-C in world XY."""
    a, b, c = (Gf.Vec3d(*corners[key]) for key in ("A", "B", "C"))
    b[2] = a[2] = c[2] = 0
    return b, (b - a).GetNormalized(), (c - b).GetNormalized()


def bounds_in_frame(stage: Usd.Stage, path: str, frame_path: str) -> Gf.Range3d:
    """Union leaf geometry in a frame; avoid inflated rotated-group bounds."""
    frame = stage.GetPrimAtPath(frame_path)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    bounds = Gf.Range3d()
    for shape in Usd.PrimRange(stage.GetPrimAtPath(path)):
        if shape.IsA(UsdGeom.Boundable):
            bounds.UnionWith(
                cache.ComputeRelativeBound(shape, frame).ComputeAlignedRange()
            )
    return bounds
