# Contact Physics and Inference Runtime

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

This implements the foundation approved in [the M14 plan](inference-client.md).
It is an independent Isaac client; it imports no collector control backend,
opens no robot connection and sends no leader/gripper hardware commands.

## Ownership

- `runtime/physics/rig.py`: session-only physical material, finger inertia,
  collision and joint-drive overrides for the nominal imported assets.
- `runtime/physics/world.py`: one fixed-base UR12e/Hand-E articulation,
  source-URDF limits, measured state, explicit stepping and scene reset.
- `runtime/physics/cameras.py`: three render products from one frozen state.
- `runtime/physics/client.py`: model-neutral synchronous WebSocket client,
  response identity validation, chunk execution and separate timing records.
- `runtime/physics/wire.py`: bounded MessagePack/NumPy codec, copied unchanged
  from `ur12e-training-infer/infer/common/wire.py` on 2026-09-15. SHA-256:
  `5997e972e8e6a513660899d57d2df48817f06aff0785cbf5a2138a4e17fbf8b4`.
- `tests/fake_server.py` and `tests/fixtures/cameras.json`: removable synthetic
  inputs. Probe scripts are explicit diagnostics, not final task policies.

`runtime/physical.py` remains the collector-owned native teleoperation adapter.
It has a collector dependency and a different clock owner; this independent
client does not import or change it. Consolidating that adapter onto the tested
physics helpers requires a separate teleoperation regression, not an untested
replacement here. Both entrypoints share the existing robot/gripper USD assets.

## Physics profile

All execution uses force-limited articulation targets and solved feedback.
Only initialization/reset can place bodies directly. The tool is physically
fixed to wrist3; the task object is never constrained to the hand.

| Property | Initial diagnostic value |
|---|---|
| Physics | CPU PhysX TGS, 240 Hz |
| Robot joint targets | Six absolute radians; source URDF limits/efforts |
| Arm stiffness/damping | 100000 Nm/rad, 10000 Nm s/rad; converted to USD degree units |
| Hand-E opening | Two independent 0..25 mm finger joints |
| Model closure | 0 = 50 mm total opening; 255 = closed |
| Finger stiffness/damping | 4000 N/m, 40 N s/m |
| Finger drive limit | 25 N per finger |
| Material friction | Static 1.0, dynamic 0.8; restitution 0 |
| Contact/rest offsets | 0.5 mm / 0 mm |
| Collision meshes | Convex decomposition |
| Hand-E finger inertia | Uniform-box estimate replacing upstream 1e-9 placeholders |

These are provisional simulation values, not measured Hand-E dynamics. Initial
self-collision is disabled; robot/environment and finger/object contact are
active. This profile does not establish self-collision safety or fidelity.
Imported task mass, friction and collision geometry must be reviewed when the
actual assets arrive. The default material applies to the robot and components without a supplied
physics material. Imported prop physics materials and static-body overrides
are preserved; task-specific tuning remains explicit.

The contact probe uses a 30 x 25 x 60 mm, 50 g free box and a physical vertical
lift joint. Open-lift, close, lift, hold and release distinguish real frictional
contact from visual attachment. This proves isolated hand contact; it is not a
complete UR12e pick-and-place trial.

## Observation, action and clock contract

The request uses the existing version-1 server envelope:
`request_id`, `epoch`, `anchor`, `contract_id`, `model`; responses must echo it.
`prefix` is empty and `delay=0`, so this path does not perform asynchronous RTC.
The observation includes the task prompt, actual seven-value state and uint8 RGB
images named `wrist`, `third_left`, `third_right`. This client owns no checkpoint,
normalization, image resize/crop or model internals.

The entire H x 7 chunk must be finite and inside joint/closure limits before
any action executes. Action Hz is required; currently it must divide the 240 Hz
physics rate. Horizon is not an action period. Execute the complete chunk by
default, or specify `--execute-steps` for a prefix before observing again.
Targets and actual states are logged separately. Server waits advance no physics.
NaN, stale identity, timeout or reset invalidate execution; no stale-chunk retry.

Camera fixtures are 640 x 480 with explicitly uncalibrated centered pinholes.
All three images are rendered at the same frozen physics state and share its
simulation epoch/time. Wrist attachment follows the physical wrist link.
`--allow-fixture-cameras` is mandatory. A file marked `calibrated` is rejected
until the full real camera adapter is implemented from supplied intrinsics and
extrinsics. Depth remains a future contract extension, not a fabricated channel.

`Session.reset()` releases render products, reloads the saved static scene,
increments the epoch, settles for two simulated seconds and rebuilds cameras.
The reset discards physical/contact history and earlier response identity.
Session traces retain the epoch, so time restarting at zero is unambiguous.

Optional `--gui` updates the viewport at most 10 Hz in simulation time. Fresh
policy observations are rendered at inference boundaries independently. The
synchronous network wait blocks the GUI too, keeping physics frozen. A responsive
waiting overlay is deferred; there is no claim of a continuously responsive UI
while a model is thinking. Headless app-update clock isolation is tested; visible
GUI/user motion appraisal is still pending.

## Ubuntu launch

Use the existing environment; no Isaac reinstall or Docker image is required:

```bash
cd ~/ur12e-sim
~/venv/isaacsim-6.0.1/bin/python -m pip install \
  --no-deps --only-binary=:all: --target .deps/inference \
  -r requirements-inference.txt

# Terminal 1: fixture server, localhost only.
~/venv/isaacsim-6.0.1/bin/python tests/fake_server.py

# Terminal 2: independent client with temporary views and explicit timing.
~/venv/isaacsim-6.0.1/bin/python scripts/inference_client.py \
  --server ws://127.0.0.1:18080 \
  --scene scenes/tabletop_home/scene.usda \
  --cameras tests/fixtures/cameras.json --allow-fixture-cameras \
  --action-hz 30 --prompt "fixture motion only" --chunks 4 \
  --output artifacts/inference/manual
```

Add `--gui` when launching in an Ubuntu desktop session. No checkpoint argument
belongs to this client; replace the server address after its model configuration
is ready. Stop the fixture server with Ctrl+C after use.

Reproduce bounded physics and invalid-response checks:

```bash
~/venv/isaacsim-6.0.1/bin/python tests/run_physics.py \
  --output artifacts/contact/recheck
~/venv/isaacsim-6.0.1/bin/python -m unittest discover \
  -s tests -p test_inference.py -v
```

The harness uses localhost port 18081 and fresh Isaac processes. It records both
JSON outcomes and actual OS exit codes, including expected failure cases. Logs
and downloaded Python dependencies are ignored/removable. Fast shutdown is kept
at the installed runtime default; the local 6.0.1 `SimulationApp.close(exit_code)`
support preserves failure statuses. Full cleanup caused post-result native
segfaults in this installation and is not used as the validated launch path.

## Next required inputs

1. Model server/checkpoint configuration, training action period and chunk-prefix
   policy; verify seven-value action semantics against real training data.
2. Task assets and static scene, with object mass, collision geometry and friction.
3. Three camera calibrations and training image preprocessing conventions.

Then evaluate actual pick-and-place and shared GPU memory/latency. The current
frozen-time loop does not establish real-world inference responsiveness or
transfer of contact parameters.
