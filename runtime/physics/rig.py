"""Physics overrides for the nominal Hand-E assets; never modifies sources."""

# OpenUSD and Kit extensions are supplied by the Ubuntu Isaac runtime.
# pylint: disable=import-error
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, PhysxSchema


def fixed_frame(joint, child, parent=None):
    """Anchor the joint at the child's current frame without a pose jump."""
    cache = UsdGeom.XformCache()
    child_world = cache.GetLocalToWorldTransform(child)
    frame = child_world
    if parent:
        joint.GetBody0Rel().SetTargets([parent.GetPath()])
        frame = (
            child_world * cache.GetLocalToWorldTransform(parent).GetInverse()
        )
    else:
        joint.GetBody0Rel().ClearTargets(True)
    joint.GetBody1Rel().SetTargets([child.GetPath()])
    joint.CreateLocalPos0Attr(Gf.Vec3f(frame.ExtractTranslation()))
    joint.CreateLocalRot0Attr(Gf.Quatf(frame.ExtractRotationQuat()))
    joint.CreateLocalPos1Attr(Gf.Vec3f(0))
    joint.CreateLocalRot1Attr(Gf.Quatf(1))


def drive(prim, kind, stiffness, damping, force):
    """Configure a force-limited physical joint position drive."""
    api = UsdPhysics.DriveAPI.Apply(prim, kind)
    api.CreateTypeAttr("force")
    api.CreateStiffnessAttr(stiffness)
    api.CreateDampingAttr(damping)
    api.CreateMaxForceAttr(force)
    return api


def prepare(stage):
    """Flatten body transforms and tune collision/material/hand properties."""
    cache = UsdGeom.XformCache()
    bodies = [
        (p, cache.GetLocalToWorldTransform(p))
        for p in stage.Traverse()
        if p.HasAPI(UsdPhysics.RigidBodyAPI)
        and UsdPhysics.RigidBodyAPI(p).GetRigidBodyEnabledAttr().Get()
    ]
    for prim, matrix in bodies:
        xf = UsdGeom.Xformable(prim)
        xf.MakeMatrixXform().Set(matrix)
        xf.SetResetXformStack(True)
        api = UsdPhysics.RigidBodyAPI(prim)
        api.CreateKinematicEnabledAttr(False)
        api.CreateRigidBodyEnabledAttr(True)
        physx = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        physx.CreateSolverPositionIterationCountAttr(32)
        physx.CreateSolverVelocityIterationCountAttr(4)
        if prim.GetName().endswith("_finger"):
            # Bounding-box inertia estimate replaces upstream 1e-9 placeholders.
            mass = UsdPhysics.MassAPI(prim)
            x, y, z, weight = 0.0452, 0.03144, 0.0619, 0.03804
            mass.CreateDiagonalInertiaAttr(
                Gf.Vec3f(
                    weight * (y * y + z * z) / 12,
                    weight * (x * x + z * z) / 12,
                    weight * (x * x + y * y) / 12,
                )
            )
            mass.CreateCenterOfMassAttr(Gf.Vec3f(0, 0, 0.027))
    material = UsdShade.Material.Define(stage, "/World/ContactMaterial")
    api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    api.CreateStaticFrictionAttr(1.0)
    api.CreateDynamicFrictionAttr(0.8)
    api.CreateRestitutionAttr(0)
    for prim in list(Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())):
        if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.IsInstanceProxy():
            parent = prim.GetParent()
            while parent.IsInstanceProxy():
                parent = parent.GetParent()
            parent.SetInstanceable(False)
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(True)
            if prim.IsA(UsdGeom.Mesh):
                UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(
                    "convexDecomposition"
                )
            api = PhysxSchema.PhysxCollisionAPI.Apply(prim)
            api.CreateContactOffsetAttr(0.0005)
            api.CreateRestOffsetAttr(0)
            bind_material(prim, material)
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
        if prim.IsA(UsdPhysics.PrismaticJoint) and "finger" in prim.GetName():
            drive(prim, "linear", 4000, 40, 25).CreateTargetPositionAttr(0.025)
            prim.CreateAttribute(
                "state:linear:physics:position", Sdf.ValueTypeNames.Float
            ).Set(0.025)
    return {p.GetName(): p for p, _ in bodies}


def physics_scene(stage):
    """Use CPU TGS and explicit 240 Hz stepping for one manipulation world."""
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(9.81)
    api = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
    api.CreateSolverTypeAttr("TGS")
    api.CreateEnableGPUDynamicsAttr(False)
    api.CreateBroadphaseTypeAttr("MBP")
    api.CreateTimeStepsPerSecondAttr(240)
    return scene


def bind_material(prim, material) -> None:
    """Tune robot contact while retaining explicitly supplied prop materials."""
    binding = UsdShade.MaterialBindingAPI.Apply(prim)
    existing, _ = binding.ComputeBoundMaterial(materialPurpose="physics")
    robot = str(prim.GetPath()).startswith(("/World/UR12e/", "/World/HandE/"))
    if robot or not (
        existing and existing.GetPrim().HasAPI(UsdPhysics.MaterialAPI)
    ):
        binding.Bind(material, materialPurpose="physics")
