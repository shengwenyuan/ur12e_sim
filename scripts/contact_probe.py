"""Hand-E contact diagnostic with a physical lift joint and a free test box."""

import json

import _physics_app

# Kit-only imports stay local; each diagnostic owns one bounded fixture.
# pylint: disable=too-many-locals


def probe(_app, root, args):
    """Run the diagnostic after Kit has initialized its extension imports."""
    # Kit imports must follow SimulationApp startup.
    # pylint: disable=import-outside-toplevel,import-error
    from isaacsim.core.simulation_manager import SimulationManager as Sim
    from isaacsim.core.experimental.prims import Articulation, RigidPrim

    stage = fixture(root)
    stage.GetRootLayer().Export(str(args.output / "fixture.usda"))
    Sim.set_physics_dt(1 / 240)
    Sim.set_device("cpu")
    Sim.initialize_physics()
    robot = Articulation("/World/HandE")
    box = RigidPrim("/World/Box")
    print("DOFS", robot.dof_names, flush=True)
    names = robot.dof_names
    log = []
    for phase, seconds, lift_target, jaw in [
        ("settle", 1, 0, 0.025),
        ("open_lift", 2, 0.1, 0.025),
        ("lower", 2, 0, 0.025),
        ("close", 2, 0, 0),
        ("lift", 2, 0.1, 0),
        ("hold", 2, 0.1, 0),
        ("release", 2, 0.1, 0.025),
    ]:
        for tick in range(round(seconds * 240)):
            robot.set_dof_position_targets(
                lift_target, dof_indices=names.index("Lift")
            )
            for side in ("left", "right"):
                robot.set_dof_position_targets(
                    jaw,
                    dof_indices=names.index(
                        f"robotiq_hande_{side}_finger_joint"
                    ),
                )
            Sim.step()
            if tick % 24 == 0:
                pos = box.get_world_poses()[0].numpy().tolist()[0]
                q = robot.get_dof_positions().numpy().tolist()[0]
                log.append(
                    {
                        "phase": phase,
                        "time": Sim.get_simulation_time(),
                        "box": pos,
                        "q": q,
                    }
                )
        print(phase, log[-1], flush=True)
    (args.output / "trace.json").write_text(json.dumps(log, indent=2))
    final = {
        phase: next(x for x in reversed(log) if x["phase"] == phase)["box"][2]
        for phase in ("settle", "open_lift", "hold", "release")
    }
    final["passed"] = (
        final["open_lift"] < 0.04
        and final["hold"] > 0.105
        and final["release"] < 0.04
    )
    return final


def fixture(root):
    """Build the isolated hand/lift rig and an unattached 50 g test box."""
    # Test-only USD authoring occurs after Kit startup.
    # pylint: disable=import-outside-toplevel,import-error
    import omni.usd
    from pxr import UsdGeom, UsdPhysics, Gf, PhysxSchema
    from physics import rig

    omni.usd.get_context().new_stage()
    stage = omni.usd.get_context().get_stage()
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/World").GetPrim())
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, "Z")
    hand = UsdGeom.Xform.Define(stage, "/World/HandE")
    hand.GetPrim().GetReferences().AddReference(
        str(root / "assets/grippers/hande/usd/hande/hande.usda")
    )
    hand.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.19))
    hand.AddRotateYOp().Set(180)
    # Initialize open before physics starts; no direct link changes afterward.
    for prim in stage.Traverse():
        if prim.GetName().endswith("_finger"):
            pos = prim.GetAttribute("xformOp:translate").Get()
            sign = 1 if "left" in prim.GetName() else -1
            prim.GetAttribute("xformOp:translate").Set(
                Gf.Vec3d(sign * 0.025, 0, pos[2])
            )
    for name, pos, size in [
        ("Floor", (0, 0, -0.01), (0.5, 0.5, 0.02)),
        ("Box", (0, 0, 0.03), (0.03, 0.025, 0.06)),
    ]:
        cube = UsdGeom.Cube.Define(stage, "/World/" + name)
        cube.CreateSizeAttr(1)
        cube.AddTranslateOp().Set(Gf.Vec3d(*pos))
        cube.AddScaleOp().Set(Gf.Vec3f(*size))
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        if name == "Box":
            UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
            UsdPhysics.MassAPI.Apply(cube.GetPrim()).CreateMassAttr(0.05)
    bodies = rig.prepare(stage)
    stage.GetPrimAtPath(
        "/World/HandE/Physics/robotiq_hande_coupler_joint"
    ).SetActive(False)
    anchor = UsdGeom.Xform.Define(stage, "/World/HandE/LiftAnchor")
    anchor.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0.19))
    anchor.SetResetXformStack(True)
    UsdPhysics.RigidBodyAPI.Apply(anchor.GetPrim())
    mass = UsdPhysics.MassAPI.Apply(anchor.GetPrim())
    mass.CreateMassAttr(1)
    mass.CreateDiagonalInertiaAttr(Gf.Vec3f(0.001))
    fixed = UsdPhysics.FixedJoint.Define(stage, "/World/HandE/Physics/Anchor")
    rig.fixed_frame(fixed, anchor.GetPrim())
    lift = UsdPhysics.PrismaticJoint.Define(stage, "/World/HandE/Physics/Lift")
    rig.fixed_frame(lift, bodies["robotiq_hande_coupler"], anchor.GetPrim())
    # World-frame vertical axis, with the child frame rotated back from Y=180.
    lift.CreateAxisAttr("Z")
    lift.CreateLowerLimitAttr(0)
    lift.CreateUpperLimitAttr(0.2)
    lift.CreateLocalRot0Attr(Gf.Quatf(1))
    lift.CreateLocalRot1Attr(
        Gf.Quatf(Gf.Rotation(Gf.Vec3d(0, 1, 0), 180).GetQuat())
    )
    rig.drive(
        lift.GetPrim(), "linear", 10000, 300, 300
    ).CreateTargetPositionAttr(0)
    UsdPhysics.ArticulationRootAPI.Apply(hand.GetPrim())
    PhysxSchema.PhysxArticulationAPI.Apply(
        hand.GetPrim()
    ).CreateEnabledSelfCollisionsAttr(False)
    rig.physics_scene(stage)
    return stage


if __name__ == "__main__":
    raise SystemExit(_physics_app.diagnostic(probe))
