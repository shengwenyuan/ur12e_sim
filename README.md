# UR12e Scenes and Native Digital Twin

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Author reusable UR12e/Hand-E USD assets and workcell scenes for the existing
Isaac Sim 6.0.1 environment on `ssh ur12e-collection`:
`~/venv/isaacsim-6.0.1`. The collector owns native teleoperation and the Isaac kinematic follower.
This project owns portable scene assets and the configured pose adapter.

The first scene is `scenes/tabletop_home/scene.usda`: a 2.2 x 1.2 m table with its top
at 1.2 m, the robot base at (2.2/3, 0.6, 1.2) m, and collection HOME. Its TCP should
roughly point toward (4.4/3, 0.6) m in XY. Model mounting yaw is independent of HOME.

Status: [layout](scenes/tabletop_home/layout.json) and
[architecture](docs/scene-viewer.md) are recorded. The remote
Isaac runtime, arm/gripper import, static HOME scene and 19 enabled collision
shapes are verified. The user accepted the Ubuntu rendered scene. Native simulated arm movement and tool attachment pass software/render checks.
Human leader-direction acceptance and contact response remain pending.

The scene will reference reusable robot/gripper assets using relative paths.
Deliver the scene and referenced assets together. This replaces the initial
browser-viewer proposal and does not require Gazebo or a new runtime image.


## Calibrated 480p workcell views

The Versteel box scene includes serial-specific camera_1 (D405) and camera_2/3
(D435IF) RGB cameras using config/cameras/rig_480p.json. All views are 640x480;
D435IF uses the September 30 canonical 480p K with wider-field distortion.
The wrist references tool0 under the provisional zero-TCP assumption.
See [configuration and acceptance](docs/calibrated-camera-preview.md) for
provenance, pure-480p alternatives, reproduction and remaining confirmations.
The existing fixture-only inference adapter has not been changed.


## Ubuntu GUI render probe

A table-only stage is available at
[`scenes/tabletop_home/render_probe.usda`](scenes/tabletop_home/render_probe.usda).
Green marks the robot base XY position; orange marks the intended TCP XY
projection, not its height. Robot and gripper meshes are not present yet.

Using the existing Isaac Python environment in an Ubuntu desktop session:

```bash
~/venv/isaacsim-6.0.1/bin/python ur12e-sim/scripts/render_probe.py \
  ur12e-sim/scenes/tabletop_home/render_probe.usda \
  --report /tmp/ur12e-render-report.json
```

The window runs until the user closes it. It opens a separate Isaac instance,
keeps the physics timeline stopped and never opens a robot connection. The first
RTX shader compilation can take longer than subsequent launches.

## Robot scene

Open `scenes/tabletop_home/scene.usda` using the same viewer command above,
substituting that path for `render_probe.usda`. The arm uses the official UR12e
joint description; Hand-E includes a nominal standard IO coupler and fingertips.
Jaws are statically open, not driven by measured feedback. Physics stays paused.

The committed USDs run without authoring sources. To optionally reimport them,
provide an external directory containing `ur_description/` and
`robotiq_hande_description/` at the revisions in `assets/manifest.json`, including
their meshes. Then use Ubuntu ROS Jazzy and Isaac:

```bash
source /opt/ros/jazzy/setup.bash
/usr/bin/python3 ur12e-sim/scripts/prepare_urdf.py --source-root /path/to/packages
~/venv/isaacsim-6.0.1/bin/python ur12e-sim/scripts/import_assets.py --source-root /path/to/packages
~/venv/isaacsim-6.0.1/bin/python ur12e-sim/scripts/compose_scene.py \
  --collection-root /path/to/ur12e_collection
~/venv/isaacsim-6.0.1/bin/python ur12e-sim/tests/test_scene.py -v
```

Deliver the curated `assets/` and `scenes/` trees together. They contain the
runtime dependency closure, not Blender/Gazebo/print exports or duplicate source
meshes. Upstream provenance and generated hashes are recorded in
`assets/manifest.json`; regenerating assets requires refreshing those hashes.
See [minimal asset delivery](docs/asset-delivery.md). No collector image rebuild
is required.

## Project locations

This is a sibling project of the collector, not a collector subdirectory.
Local source: `/Users/shengwenyuan/neu/ur12e-sim`.
Ubuntu deployment: `~/ur12e-sim` on `ssh ur12e-collection`.
Run the commands above from the parent directory. Scene generation requires an
explicit `--collection-root` to check HOME against the chosen collector checkout;
opening the saved scene and running static tests require no collector checkout.
Earlier preview logs are preserved under Ubuntu `artifacts/history/`.

## Native follower integration

Configure the collector's `config/teleop.isaac.json` with this project as
`scene.root`, `scenes/tabletop_home/scene.usda` as `scene.entrypoint`, and
`runtime/pose.py` as `scene.adapter`. Paths resolve relative to configuration.
The collector's `scripts/isaac_follower.py` opens the scene and owns native
kinematic execution; its `scripts/teleop.py` reads the PC USB leader in a
restricted container and sends locally accepted targets to that follower.

`Pose.apply(q, epoch, gripper_position)` receives six executed simulated joint
angles in radians and executed simulated closure in the 0..255 command domain.
It keeps the base mounting fixed, carries Hand-E on tool0, animates both fingers
from 50 mm total opening to closed, and
keeps a bounded nominal TCP trail. Changes stay in the USD session layer.
No URSim, Mac input relay, physical robot connection or physics is involved.
The collector M14 native-teleop plan owns runtime acceptance and launch details.

## Screwdriver workcell

Open `scenes/tabletop_screwdriver/scene.usda` for the HOME workcell with a
horizontal Husky screwdriver near the nominal TCP projection. It layers the
existing workcell and inherits its opposite-side default camera. The user-supplied
asset is stored under `assets/props/husky_screwdriver/`, with original materials,
rigid-body properties, 15 colliders and provenance. Its approximately 100 mm
length and physical parameters are estimates, not measured manufacturer data.
See [placement and acceptance](docs/tabletop-screwdriver.md).

Rebuild with `~/venv/isaacsim-6.0.1/bin/python
ur12e-sim/scripts/compose_screwdriver.py` from the project parent directory.
The scene is delivered without changing the active follower configuration.


The current native gripper adapter passes open/half/closed geometry checks;
all nine Ubuntu scene tests pass. The collector's gripper teleoperation plan
records relative 45-degree input mapping and installed runtime acceptance.
Human lever-direction/combined-motion acceptance remains pending. Saved USD
assets still open at HOME with open jaws; dynamic finger poses are session-only.


## Contact-physics inference client

The independent model-neutral client now has a physical UR12e/Hand-E world,
coherent three-view RGB, frozen-time chunk execution and scene/session reset.
Isolated Hand-E contact and delayed/invalid fake-server tests pass on Ubuntu.
Actual checkpoint, calibrated cameras and task pick-and-place remain pending.
See [plan and results](docs/inference-client.md) and
[physics profile, limitations and launch commands](docs/contact-runtime.md).
This runtime does not connect to physical hardware or change the native
collector teleoperation adapter.


## Versteel box workcell

Open [scenes/versteel_box_pick_place/scene.usda](scenes/versteel_box_pick_place/scene.usda)
for the Versteel table at 0.85 m, HOME UR12e/Hand-E, open Dynamixel carton and
30 mm red PLA cube. Placement, assumptions and validation are recorded in
[the workcell plan](docs/versteel-box-scene.md). The saved long-edge camera frames
all task elements; restarting preserves the saved cube pose.

The world origin is on the floor below the robot base. +X points toward the
carton, +Y is left while looking along +X, and +Z is up. Tabletop height is 0.85 m.
Named tabletop corners A/B/C/D and layout directions are recorded in
[the coordinate reference](docs/workcell-coordinates.md).
Table1 keeps the robot and props; Table2 reuses the same static mesh at +70
degrees, with D2 546.1 mm along the +X extension of Table1 AB from B1. See
[the Table2 placement plan](docs/table2-layout.md) for the interpretation and checks.
The active scene contains the two tables, UR12e, Hand-E, carton and red cube,
with a visible floor, neutral lighting and the saved observer camera.
Photographic panorama/finite-room backgrounds have been removed from the scene
and composer. The original panorama files remain in assets/backgrounds/ under
Git LFS as unused source assets for reference.

Rebuild using `scripts/compose_box_scene.py --collection-root /path/to/ur12e_collection`.
Run `tests/test_box_scene.py` for retained geometry and clean-scene checks.
See docs/versteel-box-scene.md for the current review and station evidence.

This standalone project uses Git LFS for **all assets/ and scenes/ files**.
Install Git LFS and run `git lfs pull` after cloning from a future Git/LFS host.
The remote URL is user-configured; this cleanup does not push any commits.

The Versteel scene also includes the accepted second table and a Table2 furniture
preview: two upright wood boards, a fixed red caster chair and matte white walls.
See [the furniture plan](docs/table2-furniture.md) for geometry and render results.
Wall OmniPBR comes from the Isaac runtime; generic USD uses a preview fallback.

The room extension preview adds a far-end wall and a perpendicular 4.0465 m wall
with two contiguous thin-walled glass panes. See the
[room extension plan](docs/table2-room-extension.md) for dimensions and results.
OmniGlass.mdl is supplied by the Isaac runtime, with a generic USD preview.
