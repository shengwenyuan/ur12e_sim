"""Exercise physical HOME hold, joint response and inference-time freezing."""

import time

import _physics_app


def probe(_app, root, _args):
    """Run the diagnostic after Kit has initialized its extension imports."""
    # Kit imports must follow SimulationApp startup.
    # pylint: disable=import-outside-toplevel,import-error
    import numpy as np
    from physics.world import World

    world = World(root, root / "scenes/tabletop_home/scene.usda")
    print("DOFS", world.robot.dof_names, flush=True)
    world.step(480)
    initial = world.state()
    print("INITIAL", initial, flush=True)
    target = world.home.copy()
    target[0] += 0.05
    target[6] = 128
    world.command(target)
    world.step(480)
    moved = world.state()
    print("MOVED", moved, flush=True)
    stamp = world.clock
    before = world.state()
    time.sleep(1)
    after = world.state()
    report = {
        "initial": initial.tolist(),
        "moved": moved.tolist(),
        "home_error": float(np.max(abs(initial[:6] - world.home[:6]))),
        "target_error": float(np.max(abs(moved[:6] - target[:6]))),
        "wait_state_error": float(np.max(abs(after - before))),
        "wait_sim_time_change": world.clock - stamp,
    }
    world.reset()
    world.step(480)
    report["reset_epoch"] = world.epoch
    report["reset_error"] = float(
        np.max(abs(world.state()[:6] - world.home[:6]))
    )
    report["passed"] = (
        report["reset_epoch"] == 1
        and report["reset_error"] < 0.02
        and report["home_error"] < 0.02
        and report["target_error"] < 0.02
        and report["wait_state_error"] == 0
        and report["wait_sim_time_change"] == 0
    )
    return report


if __name__ == "__main__":
    raise SystemExit(_physics_app.diagnostic(probe))
