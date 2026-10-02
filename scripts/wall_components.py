"""Reusable descriptions that author static panels and local assemblies."""

from dataclasses import dataclass

# OpenUSD is supplied by the independent USD/Isaac environment.
# pylint: disable=import-error
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

# pylint: enable=import-error

Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class WallPanel:
    """A metric static box with a material binding and local pose."""

    center: Vector3
    dimensions: Vector3
    material_path: str
    yaw_deg: float = 0

    def build(self, stage: Usd.Stage, path: str) -> Usd.Prim:
        """Author the box with stable transform order and enabled collision."""
        material = UsdShade.Material(stage.GetPrimAtPath(self.material_path))
        if not material:
            raise ValueError(f"Missing wall material: {self.material_path}")
        if any(value <= 0 for value in self.dimensions):
            raise ValueError("Wall dimensions must be positive meters")
        shape = UsdGeom.Cube.Define(stage, path)
        shape.CreateSizeAttr(1)
        shape.AddTranslateOp().Set(Gf.Vec3d(*self.center))
        shape.AddRotateZOp().Set(self.yaw_deg)
        shape.AddScaleOp().Set(Gf.Vec3f(*self.dimensions))
        UsdPhysics.CollisionAPI.Apply(shape.GetPrim()).CreateCollisionEnabledAttr(True)
        UsdShade.MaterialBindingAPI.Apply(shape.GetPrim()).Bind(material)
        return shape.GetPrim()


@dataclass(frozen=True)
class WallAssembly:
    """Named panels and nested assemblies; an optional local transform."""

    panels: tuple[tuple[str, WallPanel], ...] = ()
    children: tuple[tuple[str, "WallAssembly"], ...] = ()
    translation: Vector3 | None = None
    yaw_deg: float = 0

    def build(self, stage: Usd.Stage, path: str) -> None:
        """Compose children without inventing transforms for unposed groups."""
        if self.translation is not None:
            group = UsdGeom.Xform.Define(stage, path)
            group.AddTranslateOp().Set(Gf.Vec3d(*self.translation))
            group.AddRotateZOp().Set(self.yaw_deg)
        elif self.yaw_deg:
            raise ValueError("A rotated assembly requires an explicit translation")
        for name, panel in self.panels:
            panel.build(stage, path + "/" + name)
        for name, assembly in self.children:
            assembly.build(stage, path + "/" + name)
