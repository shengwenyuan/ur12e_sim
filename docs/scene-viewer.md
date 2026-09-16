# M14: Portable Scene and Native Kinematic Follower

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: native integration implemented, human direction acceptance pending,
2026-09-12. This architecture supersedes the former read-only URSim view proposal.

## Current contract

The Ubuntu collector reads GELLO directly and owns mapping, limits, HOME,
following, stop and the native Isaac execution endpoint. This scene project
supplies relative USD assets and `runtime/pose.py`; it owns no USB or control
transport. Configure the project root and adapter through the collector's
`config/teleop.isaac.json`. URSim is not in this topology.

The fixed workcell is 2.2 x 1.2 m with tabletop Z=1.2 m, base at
(2.2/3, 0.6, 1.2) m and HOME [0,-90,-90,-90,90,0] degrees. Mounting yaw and
nominal tool geometry retain the previously accepted scene. Apply executed
simulated joint radians in a session layer. Keep the base fixed and carry
Hand-E with tool0; apply the native executed gripper position to both fingers
and reset the bounded TCP trail at ownership changes.
Physics remains off. No calibrated clearance or contact acceptance is claimed.

## Acceptance

Retain the five static USD checks and add three native pose checks covering
HOME, signed single-axis and mixed poses, joint anchors, tool attachment,
unchanged saved layers, bounded trail and relocated asset dependencies.
Native runtime timing, owner isolation and operator launch live in the
collector's `docs/m14-digital-twin/native-teleop.md`.

The following sections preserve static scene provenance and earlier acceptance
history; they do not define the current runtime or active launch interface.

## Sources

- [Official UR12e visual configuration](https://github.com/UniversalRobots/Universal_Robots_ROS2_Description/blob/rolling/config/ur12e/visual_parameters.yaml)
- [Official UR12e nominal kinematics](https://github.com/UniversalRobots/Universal_Robots_ROS2_Description/blob/rolling/config/ur12e/default_kinematics.yaml)
- [Robotiq Hand-E manual](https://blog.robotiq.com/hubfs/support-files/Hand-E_Manual_Generic_PDF_20240402.pdf)
- [Isaac Sim 6.0.1 stage units and axes](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/robot_setup_tutorials/tutorial_intro_environment_setup.html)
- [Isaac Sim 6.0.1 URDF importer](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/importer_exporter/ext_isaacsim_asset_importer_urdf.html)
- [Isaac Sim 6.0.1 scene authoring](https://docs.isaacsim.omniverse.nvidia.com/6.0.1/python_scripting/environment_setup.html)

## Aligned immediate GUI/render check

The user authorized starting visualization on the Ubuntu display on 2026-09-12
and will close it personally. First author a clearly labeled table-only
`render_probe.usda`, with base and desired TCP XY position markers, then open it
in the existing Isaac 6.0.1 venv. This is a renderer/desktop smoke, not the final
robot scene. Preserve the already-running unsaved Isaac window; use a separate
preview process, leave it running for the user and do not start physics or any
robot connection. Verify USD geometry, GPU initialization and a mapped viewport;
record model import and live joint visualization as pending.

### Render probe results — 2026-09-12

- **PASS:** Ubuntu `ur12e-flexlab`, existing
  `~/venv/isaacsim-6.0.1` (Python 3.12.3, Isaac Sim 6.0.1.0, OpenUSD 0.26.8),
  NVIDIA RTX 2000 Ada. No environment replacement or package upgrade.
- **PASS:** `scripts/table_scene.py` authored and reopened the table-only USD;
  the tabletop bounding-box maximum Z is 1.5 m within floating-point tolerance.
- **PASS:** `scripts/render_probe.py` opened a separate mapped Isaac window,
  selected `/World/Camera` and completed 120 viewport updates. Kit logs also
  confirmed progressing rendered frames. The captured window visibly shows the
  table, lighting, shadows and both position markers. Initial RTX compilation
  made first startup take approximately 100 seconds.
- **PASS:** Black and Pylint checks for both scripts (Pylint 10.00/10).
- The preview is left running for the user to close. The pre-existing unsaved
  Isaac window was preserved. No robot connection, control signal or physics
  timeline playback was started.
- Evidence: remote `~/ur12e-sim/artifacts/history/table-layout-20260912/` contains the
  stage, launch log, report and viewport screenshot. Local ignored copies are
  under `artifacts/isaac-render-probe/`. Source changes are uncommitted.
- **NOT RUN:** UR12e/Hand-E import, HOME FK, live measured joints and the new
  viewer's M14-A01/A02 acceptance. This smoke validates desktop rendering only;
  it does not establish articulated-scene or motion acceptance.

### Table dimension revision — 2026-09-12

The user accepted the layout and changed the table to 2.2 m long, 1.2 m wide,
with its top at 1.2 m. Preserve proportional placement: base at
(2.2/3, 0.6, 1.2) m and the approximate TCP XY guide at (4.4/3, 0.6) m.
Updated the layout configuration and regenerated the local and Ubuntu
`render_probe.usda` using the existing Isaac environment. **PASS:** reopened USD
bounds confirm length 2.2 m, width 1.2 m and top Z 1.2 m within 1e-6 m.
The running viewport was not restarted or remotely reloaded; reopen the USD to
show the changed geometry if the application retains its previous in-memory
stage. Robot import and live joint visualization remain pending.

## Aligned robot import and collision preview — 2026-09-12

The user explicitly requested importing the robot and gripper with collision
geometry and opening the resulting scene on Ubuntu. Implement the already
planned static model import now, with collision authoring promoted from later
scope. Keep the timeline stopped and do not connect to hardware or URSim.
Use pinned Universal Robots Jazzy UR12e kinematics/visual/collision sources and
Hand-E CAD-derived meshes from `macmacal/robotiq_hande_description` (upstream
credits Robotiq CAD). Preserve both licenses and the exact provenance. Its
standard coupling and fingertips are nominal until compared with the lab tool.
Show static open jaws, not measured gripper state. Preserve the six HOME angles.

Use the Isaac 6.0.1 URDF importer for articulated USD assets. Retain separate
visual and collision representations, enable colliders on the robot, fingers,
table and floor, and use convex collision approximations suitable for robot
links. Compose through relative USD references and save HOME transforms so the
pose appears before physics playback. Validate link/joint coverage, enabled
colliders, geometry units, HOME and reload, then open a separate Ubuntu preview
for visual review. Collision authoring does not establish contact dynamics or
physical safety acceptance; M14-A01/A02 live-view checks remain NOT RUN.

### Static robot/collision preview results — 2026-09-12

**PASS — user visual acceptance:** the user inspected the Ubuntu display and
accepted the scene ("cool ... no problem ... end this round"). The final window
remains open for the user to close. The table is 2.2 x 1.2 m with top Z 1.2 m;
UR12e uses unchanged collection HOME with its nominal tool pointing down.
Nominal fingertip TCP is (1.446329, 0.600000, 1.720350) m. The chosen mounting
yaw is -2.8948451343 rad; it changes world placement, not joint calibration.

**PASS — assets and collision authoring:** imported official UR12e and
CAD-derived Hand-E sources at the revisions in `assets/manifest.json`, retaining
licenses and per-file hashes. Separate arm and tool assets are referenced by
`scenes/tabletop_home/scene.usda`. Enabled collision coverage: 7 arm mesh
colliders, 6 gripper colliders (body/coupler cylinders and 4 finger meshes),
5 table boxes and 1 floor box. The importer retained convex hulls on instanced
meshes despite requesting decomposition; composition explicitly makes collider
instances editable and authors `convexDecomposition`, verified on the saved USD.
Static jaws are open, with a nominal 50 mm opening; mesh tip separation checked
at approximately 50.02 mm. The lab adapter and fingertip geometry remain nominal.

**PASS — verification:** five Ubuntu OpenUSD tests cover resolved relative asset
dependencies, dimensions/downward HOME, collision coverage/approximations,
coincident anchors for all six revolute joints, and a known transform-order
fixture. Run `~/venv/isaacsim-6.0.1/bin/python ur12e-sim/tests/test_scene.py -v`
from a repository deployment. Black passes; Pylint reports 10.00/10 for scripts
and tests. Actual viewport startup passed and the final screenshot shows the
complete arm, downward gripper and table. The camera was reframed after an
initial render cropped the upper arm.

Runtime remains the existing Ubuntu Isaac 6.0.1.0 environment. No hardware or
URSim connection, motor writes, collection changes or physics playback occurred.
Evidence is in remote `~/ur12e-sim/` (import and launch logs,
render reports and viewport images); local ignored screenshots are under
`artifacts/isaac-robot-preview/`. Current source changes remain uncommitted.

**NOT RUN:** contact simulation/collision response, calibrated physical tool
clearance, live URSim measured-joint viewing and its M14-A01/A02 isolation gates.
The separate gripper is positioned statically on tool0; a dynamic attachment is
not yet configured. This acceptance covers model geometry, enabled collision
shapes and the static rendered scene only. No further test is started this round.

## Standalone location — 2026-09-12

The user requested moving the local project beside the other UR12e projects:
`/Users/shengwenyuan/neu/ur12e-sim`, with Ubuntu deployment at `~/ur12e-sim`.
This directory owns the scene assets, scripts, tests and this plan. The collector
retains the M14 interface contract and a pointer to this project. The scene
composer accepts an explicit `--collection-root` to validate HOME without
assuming the two projects share a parent/source layout. USD references remain
relative. Earlier Ubuntu preview evidence is retained under `artifacts/history/`.

Relocation acceptance: **PASS** — local and Ubuntu project directories moved
to the requested names; all five static USD tests pass from `~/ur12e-sim`,
including dependency resolution. Composer Black/Pylint checks pass. The old
Ubuntu `~/ur12e-sim-preview` directory is removed after preserving its evidence.
No simulator or hardware control process was started during relocation.

## Default view reversal — 2026-09-12

The user requested the opposite side as the persistent initial view. Rotate
the saved viewpoint 180 degrees around the table center in XY: camera position
changes from (3.8, -4.0, 3.0) to (-1.6, 5.2, 3.0) m, preserving look-at
(1.1, 0.6, 1.25) m, Z-up and 22 mm focal length. Update both the composer and
saved scene; author `cameraSettings:boundCamera` as `/World/Camera` for direct
Isaac stage opens. The preview launcher already selects this camera explicitly.

**PASS:** Ubuntu USD save/reopen confirms the opposite camera position,
22 mm focal length and persistent camera selection. Updated scene synchronized
to the local project. Composer Pylint passes at 10.00/10. No GUI or motion test
was started; next launch uses the saved new viewpoint.



## Native gripper extension — 2026-09-12

`runtime/pose.py` now accepts the executed simulated gripper component alongside
six arm joints. Both fingers move symmetrically across the model's 0..0.025 m
joint range. Arm placement, tool attachment, saved layers and physics-off mode
are preserved. Nine Ubuntu tests pass, including the full/half/closed finger
transform check with unchanged arm pose. The collector owns relative mapping,
rate limits and stop behavior; no serial or physical gripper transport lives
in this scene adapter. Operator gripper acceptance remains pending.
