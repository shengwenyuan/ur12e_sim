# M14: Contact-Physics Inference Client

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: foundation implemented and synthetically validated on 2026-09-15;
checkpoint and final task acceptance pending. The implementation and actual
results are recorded below. This plan does not authorize hardware motion.

## Confirmed scope

Build an Isaac Sim 6.0.1 inference client on `ssh ur12e-collection`, sharing the
NVIDIA RTX 2000 Ada GPU with a separate VLA server process. Keep model loading,
checkpoint paths, normalization and model-specific preprocessing on the server.
Support pi05 and a pi05-training-RTC checkpoint, without asynchronous RTC during
this simulation evaluation. Checkpoint/model configuration remain placeholders.

The user will supply task assets, matching USD scenes and three camera
calibrations. Do not use the screwdriver as the target task. Begin from a saved
static initialization, then run genuine contact dynamics for pick-and-place.
A visible, smooth trajectory and ultimately successful pick-and-place are the
user's evaluation objectives; do not build a benchmark/scoring framework now.

## Existing boundaries and required change

`runtime/pose.py` is a kinematic pose display. It updates transforms and cannot
serve as evidence of physical grasping. The inference world must instead use
physics-driven articulation targets and read back simulated joint states.
Initial placement/reset may assign poses; normal execution must not teleport
links or attach the task object to the gripper to fake success. Rig the tool to
the robot consistently and remove conflicting world anchors in the physical
scene variant. Preserve visual scene and existing teleoperation entrypoints.

The sibling `ur12e-training-infer` repository already supplies a WebSocket binary
protocol, model handshake, request identity and action chunks. Its current
external action contract is H x 7: absolute six-joint radians and gripper
0..255, with server-side unnormalization/absolute conversion. Reuse that boundary
where applicable; do not make Isaac understand pi05 internal tensors. Confirm
compatibility when the actual checkpoint arrives. The model's action period and
executed prefix length are explicit configuration, not inferred from horizon or
collector servo rate. No real policy is executed with unspecified timing.

Observation: task prompt, measured simulated state, and RGB roles `wrist`,
`third_left`, `third_right`, all from one frozen world state and simulation epoch.
Capture only after all three render results correspond to the requested state;
never relabel old frames with a new timestamp. Future depth is optional and
carries units/validity/registration explicitly. Camera intrinsics, extrinsics
and image preprocessing configuration remain placeholders, not invented lab
calibration. Temporary camera fixtures must be visibly labeled as such.

## Simulation clock and resource policy

Use one owner of explicit physics stepping. The evaluation loop is:
initialize and settle -> capture coherent observation -> request chunk while
simulation time is frozen -> apply targets through physical substeps -> observe
again. UI processing during server wait must not advance physics or sensors.
Record simulation time, inference wall time and wall-clock throughput separately.
Server timeout or invalid output freezes execution; do not replay stale chunks.
Epoch/reset changes revoke prior requests and queued actions.

Proposed baseline: one environment, fixed physics dt 1/240 s, display rendering
10 Hz or lower, no depth initially. Physics/controller/action/display rates are
separate. The model observation is freshly rendered at each inference boundary;
viewport throttling must not silently stale model inputs or alter action timing.
Exact action Hz, horizon and executed prefix length await model configuration.
A synchronous full-chunk path can be the first fixture, with configurable prefix
execution for later receding-horizon evaluation.

Serialize GPU-heavy rendering and inference. Low render frequency reduces
compute contention but does not remove persistent GPU allocations. Measure
combined model/Isaac memory after the checkpoint is available; do not promise
fit from the 16 GB capacity alone. If using the current JAX backend, configure
allocation to avoid claiming most GPU memory up front. Any reduced precision,
quantization or offload requires model-specific validation, not silent changes.
Do not replace the existing Isaac environment.

Frozen-time inference evaluates policy behavior without inference delay. It does
not establish real-time deployment readiness. Later real-world evaluation must
restore wall-clock latency, watchdogs and continuous physical execution; RTC may
then become relevant again.

## Aligned development sequence

1. Physics world/reset/hold and tool rigging; prove basic contact with temporary
   analytic fixtures, not a claimed final pick-and-place task.
2. Three-camera observation bundle and independently paced display, using
   explicitly temporary camera parameters until calibrated values arrive.
3. Model-neutral client and synchronous world-step scheduler using fake chunks,
   then integrate the existing server contract. Leave checkpoint placeholders.
4. Load the user-provided task scene, assets and calibration; profile shared GPU
   resources with the actual pi05 backend; run visual pick-and-place trials.

Keep checks small but meaningful: physics actually advances only on explicit
steps, joints move through physics, contact is active, observation frames share
the intended state, and network waits do not change world state. Preserve
M14-A01 target/feedback provenance and M14-A02 isolation from hardware/collector.
No new numerical task-success thresholds are required before user trials.

## Contact-model assessment

Isaac 6.0.1 supports physical grasp simulation; success still depends on
collision geometry, friction, mass/inertia, solver settings, drive gains and
physics dt. Its official robot tips retain gripper/contact troubleshooting.
RoboLab itself warns that contact-rich outcomes can change between simulator
versions. Do not interpret a newer version as guaranteed contact fidelity or
accept cosmetic attachment as physical pick-and-place success. The user's
historical term "cosmetic" is not assumed to identify a specific old workaround.

Sources:
- https://docs.isaacsim.omniverse.nvidia.com/6.0.1/robot_simulation/robot_simulation_tips.html
- https://docs.isaacsim.omniverse.nvidia.com/6.0.1/sensors/isaacsim_sensors_multitick_rendering.html
- https://github.com/NVlabs/RoboLab#requirements

Acceptance is recorded below; shared-GPU model loading and actual task trials
remain NOT RUN.
Assets, camera calibration and actual model configuration remain user-provided
follow-ups; they do not block the isolated foundation and fake-server work.

## Implementation alignment — 2026-09-15

The user approved proceeding with gripper contact debugging first, then the
physics/client/observation foundation until real checkpoints and task assets
are required. Use an explicitly synthetic box for contact diagnostics only.
Run CPU PhysX at 240 Hz initially, with independently throttled rendering.
First verify gripping, lifting and release without attaching the box to the
hand. Record unresolved limits and do not call this final task acceptance.

## Implemented foundation and acceptance — 2026-09-15

Status: **implemented; synthetic contact/client acceptance PASS; actual task and
checkpoint acceptance pending**. See [runtime and launch instructions](contact-runtime.md).
Changes are deployed to the independent `~/ur12e-sim` project on the Ubuntu
station and mirrored in the Mac sibling project. No collector image rebuild,
physical robot connection or leader motor write is involved.

Environment: Ubuntu station `ur12e-collection`, Python 3.12.3, Isaac Sim 6.0.1.0,
OpenUSD 0.26.8, NumPy 2.3.1, websockets 12.0, project-local msgpack 1.1.1;
NVIDIA RTX 2000 Ada, 16380 MiB. Mac protocol tests use Python 3.12.13, NumPy
2.2.6 and the same wire dependencies. Black 25.1.0 and Pylint 3.3.6 pass on the
new files. Existing collector-native physical adapter is unchanged.

| Check | Result | Observed conclusion |
|---|---|---|
| Isolated physical Hand-E contact | PASS | Open lift leaves the 50 g box on the floor; closing lifts it 98.9 mm; hold maintains height; opening releases it to the floor. No object/hand attachment. |
| Physical arm HOME and target | PASS | Maximum final joint error 0.000647 rad (0.037 degrees) for the tested small base movement; not a full-workspace accuracy claim. |
| Frozen inference wait | PASS | Actual solver clock and measured state remain unchanged during wait. |
| Three RGB cameras | PASS | Three 640 x 480 x 3 uint8 images; all change with physical arm motion and retain the shared frozen state/time. Example views inspected. Fixture calibration only. |
| Scene/session reset | PASS | Reloads static initialization, rebuilds cameras, increments epoch; 16 actions executed across epochs 0 and 1. Headless viewport updates do not advance physics. |
| Delayed fake server | PASS | Four H=8 chunks at 30 Hz execute 32 actions and 1.0667 simulated seconds; 1.2246 seconds of network/model wait are excluded. |
| NaN / stale epoch from server | PASS | Each exits with code 1, retains the error report, and executes zero actions. |
| Wire/scheduler regression | PASS | 13 tests pass on Mac and Ubuntu, including real localhost WebSocket timeout, invalid chunk tail, prefix execution, reset invalidation and unowned steps. |
| Runtime process exit | PASS | Successful runs exit 0; deliberate invalid responses exit 1 using default fast shutdown. |
| M14-A01 provenance | PASS for this client | Per-step target and solved actual state are separate, with epoch and simulation time. |
| M14-A02 isolation | PASS for this client | No collector control import or hardware endpoint; an unavailable server cannot drive a physical device. This does not re-certify the collector's existing gates. |
| Original scene and assets | PASS | Five existing static scene tests pass; all 39 manifest file hashes match. |
| Actual checkpoint/shared GPU | NOT RUN | No checkpoint; the fake-server headless baseline peaks at 1431 MiB device memory (0.5-second samples), not a guarantee of model fit. |
| Final asset/camera/pick-and-place | NOT RUN | Await task assets, scene, camera calibration and action timing/model configuration. |
| Visible GUI/user trajectory appraisal | NOT RUN | Headless rendering and viewport clock isolation tested; no visible desktop session launched this round. |

Evidence on the station: `artifacts/contact/accepted/summary.json`, per-case
logs/reports and traces in that directory, plus
`artifacts/contact/session-reset2/report.json` for combined session reset and
headless viewport stepping. Reports are also copied to Mac project artifacts.
`tests/run_physics.py` reproduces the bounded physical/network cases; the fixture
server and synthetic camera inputs remain under `tests/`.

Failures retained for diagnosis:
- The original lift anchor did not expose a controllable DOF; a proper physical
  anchor/body/prismatic tree fixed it.
- Initial finger joint states differed from open USD transforms and displaced
  the box before the test; initializing both states at 25 mm fixed it.
- Full Kit cleanup after successful checks segfaulted; restoring the installed
  default fast shutdown fixed process status, with errors persisted first.
- A direct float32 closure was rejected by the experimental SDK; explicitly
  converting the scalar at the SDK boundary fixed the reset/hold diagnostic.

Remaining contact limitations are explicit: provisional finger inertia and
friction, self-collision disabled in this initial profile, and isolated-gripper
contact rather than complete arm pick-and-place. No cosmetic attachment is used.
Continue with the actual model/task/calibration inputs, then tune contact and
review visual behavior. Real-world inference still needs continuous-time safety
and latency validation, separate from this frozen-time simulation.
