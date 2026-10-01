# M14: Versteel Box Placement Workcell

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: photographic and finite-distance backgrounds removed on 2026-10-02.
Local and station static checks pass; isolated Isaac 6.0.1 installation, startup
and four-view RTX rendering pass. The user accepted the clean stage and
authorized its commit on 2026-10-02.
PhysX settling remains pending. Earlier results are historical.
Existing HOME and contact-client boundaries remain valid.
No physical robot or leader control is authorized or required.

## Original concrete layout (superseded by finite-distance update)

Import the complete user-provided `versteel_table_3072` and `open_dynamixel_box`
asset folders, preserving source provenance and portable USD dependencies.
Keep the table's native 1.8288 x 0.762 m footprint and 0.8128 m tabletop height;
use its static/locked-caster USD variant. World X follows table length, +Y its
width, Z up, with origin beneath the tabletop's lower-left corner.

The selected width edge is the short edge at X=1.8288 m. Center the carton across
the table width (Y=0.381 m). Rotate its source +Y back direction toward world +X,
so the hinge/back exterior plane is at X=1.5938 m, 235 mm from that edge. The
source 47 mm front/back dimension places the body center at X=1.5703 m.
Put the UR12e base 900 mm before the body center on the same centerline:
X=0.6703 m, Y=0.381 m, Z=0.8128 m. Preserve collection HOME joint angles and the
nominal Hand-E mount, with its horizontal reach toward +X.

Create a red 30 mm cube, with analytic collision, explicit mass and inertia.
Assume solid PLA at 1240 kg/m3: mass 0.03348 kg. This is an estimate for 100%
infill, not a measured printed part; sparse prints require measured mass later.
Density reference: https://prusament.com/wp-content/uploads/2022/10/PLA_Prusament_TDS_2021_10_EN.pdf
The initial tabletop pose used seed 3072. The refined scene fixes cube XY at
(1.280, 0.400) m and retains the originally sampled yaw of 173.62582178591697
degrees; roll/pitch remain zero for stable initialization.

A saved camera looks toward a long edge from +Y, with the side-on L-shaped arm,
carton and red cube in frame. Keep the old scenes available. The new scene is
`scenes/versteel_box_pick_place/scene.usda`; portable references point to assets.
Preserve actual table/cube/carton contact geometry and the hollow carton opening.

## Implementation and checks

1. Import assets and create the cube; compose through existing HOME FK helpers.
2. Check distances, support, opening orientation, dimensions, mass, collisions,
   HOME and reference portability; inspect a rendered Ubuntu preview.
3. Preserve the imported table's disabled rigid-body flag in the physics overlay;
   test a short no-action settle with no hardware connections.
4. Initialize the independent Git repository (it has none), using LFS for every
   file under assets/ and scenes/. Include the existing standalone foundation
   and background library; exclude artifacts, dependencies, caches and plans.
5. Commit the validated project, verify LFS pointer/storage integrity, then
   synchronize materialized assets/scene and the Git snapshot to the Ubuntu
   project without deleting station-only artifacts/dependencies.

Acceptance results, commit and delivery status will be recorded below.


## Initial scene acceptance — 2026-09-15

- PASS: static USD dependencies resolve after relocation to an isolated Ubuntu
  candidate directory, with no absolute asset references.
- PASS: table retains 40 enabled colliders and its static body override; carton
  retains nine separate collision panels and its open cavity; red cube has one
  analytic collider, 30 mm edge and 0.03348 kg estimated mass.
- PASS: carton back-to-short-edge distance is 0.235 m, centerline is Y=0.381 m,
  and robot-base-to-carton-body-center distance is 0.900 m in XY.
- PASS: cube pose uses seed 3072: (0.99188168, 0.43669626, 0.8288) m; yaw is
  recorded in layout.json. X lies between the base and carton. Initial clearance
  above the table is 1 mm for both props.
- PASS: Ubuntu Isaac Sim 6.0.1 renders the full HOME arm, Hand-E, carton and cube
  from the long-edge viewpoint. The first close-up cropped the upper arm; the
  saved 27 mm view was widened and visually rechecked. See the scene preview.
- PASS: a two-second CPU PhysX settle keeps the table fixed and props supported;
  carton XY drift is under 0.02 mm, cube drift under 0.001 mm. Contact overlap
  of the carton is about 0.29 mm in this provisional profile; no high-fidelity
  paper-contact claim is made. Carton friction remains its source value 0.4.
- PASS: five existing static scene regressions, new script/rig Pylint and Black.
- NOT RUN: policy pick-and-place, real-camera matching, or physical hardware.

Evidence: scenes/versteel_box_pick_place/scene-report.json and preview.png;
full station logs remain under artifacts/versteel-box-scene-final/.
The pose is fixed in the saved scene; restarting does not rerandomize it.
To regenerate the current saved layout, run scripts/compose_box_scene.py
--collection-root /path/to/ur12e_collection using an OpenUSD/Isaac environment. Regeneration resets render/settle status
until scripts/check_box_scene.py is run again.

Git delivery uses assets/** and scenes/** LFS rules, including source metadata
and this preview. Existing background files downloaded on the station were
included in the initial standalone project snapshot. Imported source metadata
is preserved verbatim; this document defines the integration assumptions.

All 225 asset/scene index entries were verified as LFS pointers before commit.
Delivery identity and post-commit LFS checks are recorded in the deployment
receipt under artifacts/versteel-box-delivery.json on both machines.


## Layout refinement — 2026-09-15

Aligned by the user's explicit follow-up: use collection HOME, move the cube
closer to the carton along table length and toward the base centerline across
the width, and mirror the observer to the other long edge.

Collection `src/ur12e_collection/simulation/profile.py:HOME` is
[0, -90, -90, -90, 90, 0] degrees, matching the original scene. Scene generation
will require `--collection-root` and validate this source before authoring;
its SHA-256 is recorded for provenance. No hardware module is imported.

Override the sampled cube XY with (1.280, 0.400) m, retaining its original height
and yaw. Box and base both have Y=0.381 m: moving Y toward the base necessarily
also moves it toward the box's shared centerline. The final XY is explicit in
layout metadata; it is no longer an independently random placement.

Reflect camera Y about the table centerline: eye (1.04, 3.962, 2.2) m, target
(1.04, 0.381, 1.25) m. Keep world axes and all object/robot orientations fixed.
+X follows table length from base toward box; +Y points across the table toward
the new observer; +Z points up. The corner-based world origin remains on the
floor below the X=0,Y=0 tabletop corner. This is not the robot base frame.

Checks: collection-source HOME equality, exact cube placement, camera reflection,
portable USD composition, rendered visibility and short no-action settle.
Commit the validated refinement and synchronize the same snapshot to the station.


Refinement acceptance: PASS. Collection's three teleop READY configurations also
match the six HOME angles. All 14 saved UR link frames agree with HOME FK to a
maximum matrix-element difference of 2.23e-16. Cube XY and reflected camera eye
match the values above. The new Ubuntu preview includes the full arm and both
props; two simulated seconds of no-action settling pass. Black/Pylint pass.
The current scene report and preview replace the initial versions; logs are in
station artifacts/versteel-view-refinement/. No hardware control was involved.


## Fixed installation yaw — 2026-09-15

Explicitly approved correction: mounting yaw is -180 degrees, with all six
collection HOME joint angles unchanged. The source URDF, link transforms within
the robot, Hand-E mounting and TCP definition must not be adjusted to center the
TCP on the table. Its natural lateral offset is retained. The earlier approximate
two-thirds tabletop position is a visual trend, not an equality constraint.

The shared composer respects explicit mounting yaw and defaults to -180 degrees
when none is supplied; it no longer derives installation yaw from TCP bearing.
The active Versteel scene explicitly records -pi radians and a fixed-mount policy.
Cube, carton, camera, base position, and source robot/gripper assets stay unchanged.
Older saved scenes remain historical artifacts until explicitly regenerated.

Checks: collection HOME equality, aligned URDF base frame in world XY, unchanged
prop/camera transforms and asset hashes, physically derived TCP lateral offset,
Ubuntu preview and short no-action settle. Commit and synchronize the correction.


Fixed-yaw acceptance: PASS. Installation yaw is exactly -pi radians and the
URDF `base` frame aligns with world XYZ. All 14 UR link frames retain the same
HOME FK relative to the new mounting transform (maximum matrix error 2.23e-16).
Robot/gripper asset files, camera, table, base position and both prop transforms
are unchanged. The nominal TCP is (1.3617, 0.20685, 1.33315) m; its natural world
Y offset from the base is -0.17415 m. No TCP/link compensation was applied.
The updated Ubuntu preview and two-second no-action settle pass; Black/Pylint
pass. Evidence is embedded in the current scene report and preview, with station
logs in artifacts/versteel-fixed-yaw/. No physical hardware was controlled.


## Flex Lab panorama background — 2026-09-15 (retired)

Scope follows the user's explicit request to use panorama_v1 as the current
scene background, with the workstation ahead and left. From the saved +Y-side
observer, forward is -Y and left is +X. Place panorama longitude zero toward
(+X, -Y), at world azimuth -45 degrees. Preserve the camera, HOME, fixed -180
degree robot mounting yaw, TCP, props and contact geometry.

Import the complete 26 MB panorama_v1 delivery into
assets/backgrounds/flex_lab/panorama_v1, retaining both resolutions, coverage
masks and provenance. Use the compact 4096x2048 JPG by default as an sRGB LDR
latlong Dome Light texture; preserve the original pixels and gray missing areas.
Keep the existing key light. This is a visual background, not calibrated HDR
lighting, geometry or a source of synthetic depth.

Implementation: author portable texture reference and orientation in the scene
composer and layout metadata; render on Ubuntu Isaac Sim 6.0.1; check unchanged
scene object transforms and short physical settle; commit with Git LFS and sync
the same asset/scene snapshot to the station. No hardware control is involved.

Orientation convention reference:
https://openusd.org/release/user_guides/schemas/usdLux/DomeLight.html
The generic classic DomeLight convention has a +Y pole and longitude-zero +Z
bearing. The installed Isaac RTX renderer instead displayed this texture with
its pole aligned to stage Z and its center toward -X before rotation. Applying
the generic pole correction tilted the actual panorama by 90 degrees. Therefore
use the renderer-verified XYZ rotation (0, 0, 135) degrees: an upright workstation
at world azimuth -45 degrees. This saved orientation targets Isaac Sim 6.0.1;
other renderers require visual revalidation rather than an assumed USD mapping.

Acceptance: PASS for Ubuntu Isaac Sim 6.0.1 rendering, workstation orientation,
portable dependencies, all 25 imported files matching source bytes, and every
previously authored non-environment USD field remaining identical. Black and
Pylint pass. A two-second no-action physics settle passes with the table fixed,
props supported and source paper friction unchanged. No hardware was controlled.

The saved preview uses the unchanged observer camera. At a 45-degree left bearing,
the computer is mainly outside that narrow initial frame; turning left reveals it.
workstation-direction-preview.png records an upright, centered monitor from a
separate diagnostic camera aimed (+X,-Y), with the floor hidden only in that
session. The saved floor and collisions remain intact. They occlude the lower
part of the environment in the normal view; no geometry was removed for the photo.
Logs: station artifacts/versteel-panorama-final/ and versteel-panorama-upright/.
Assets and scenes remain Git LFS-managed; delivery uses the same committed
snapshot and LFS objects on the Ubuntu station.


## Panorama reference-axis correction — 2026-09-15

The user clarified that front-left is measured while looking along +X from
Y=0 toward the carton, not from the saved observer camera. Forward is +X, left
is +Y, right is -Y. Place the workstation approximately 45 degrees left of +X,
i.e. world (+X,+Y), by rotating the current Dome Light another +90 degrees.
The final Isaac RTX rotation is XYZ (0,0,225) degrees. The glass entrance should
lie farther left than the workstation and the gray blinds on the right. Preserve
the photograph's angular relationships; these verbal landmark directions are
approximate, not a surveyed room layout or a reason to warp the panorama.

The phone was approximately 1-2 m from the monitor during capture. Record this
user-supplied range as provenance, not a measured depth map, dome radius or
world-space monitor position. Dome lighting is infinitely distant and cannot
recover nearby furniture parallax from that range. Leave the saved camera, robot
HOME, mounting yaw, TCP, table, objects and physical materials unchanged.

Checks: only the environment transform changes in the saved USD; render the
normal view and separate workstation, left and right diagnostic views on Ubuntu
Isaac Sim 6.0.1; verify upright landmarks and portable references. Reuse the
existing bounded render/settle check, update evidence, commit and synchronize.
Code style requirement remains the prominent requirement at the top of this plan.
Acceptance: PASS for the corrected workstation bearing (+45 degrees from +X),
upright appearance and farther-left glass entrance, verified in independent
Ubuntu Isaac RTX renders. PASS for portable dependencies, all non-environment
authored USD fields unchanged, Black/Pylint, and the two-second physical settle.
The original camera remains on +Y looking toward -Y. No hardware was controlled.

Right-hand curtain appearance: BLOCKED by source coverage. The -Y diagnostic
view is mostly unphotographed neutral gray, so it cannot establish the complete
curtain's appearance or exact bearing. The unchanged default camera faces the
same region and now also shows mostly gray. Do not warp the image or move the
robot/camera to conceal the gap. A better-covered panorama is needed to validate
this landmark; the supplied 1-2 m capture distance does not fill the missing view.

Current evidence: scene-report.json, preview.png and the four direction previews
in the scene folder; full station logs under artifacts/versteel-panorama-axis-fix/.
Diagnostic cameras are at Y=0 with floor visibility overridden only in memory.
They do not alter the saved camera or physical scene. Prior orientation evidence
above is historical and superseded by this section.


## Finite-distance lab background — 2026-09-15 (retired)

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: implemented / rendering passed / PhysX settling pending. The user
approved this scope against
`18e6511` after agreeing the coordinate system, finite room projection, and
approximate capture measurements. This section supersedes the corner-based
coordinates and infinite visible background above. No new module ID is created.

### Aligned scope and coordinate contract

- World origin: floor directly under the robot mounting base. +X faces the wood
  wall and carton; +Y is left when looking along +X; +Z is up.
- Robot base: (0, 0, 0.85) m. Retain six collection HOME joint angles,
  mounting yaw -180 degrees, the Hand-E mount, and natural TCP offset.
- Capture/projection origin: approximately (0.30, 0, 1.20) m. It remains fixed
  when an observation camera moves. The camera faces +X, with wood ahead,
  monitor/workstation ahead-left, entrance farther left, and blinds toward -Y.
- User-estimated distances: monitor about 1.5 m; blinds about 0.5 m. Blinds
  initially occupy Y=-0.5 m. Monitor distance is not a measured wall distance.
- Retain the native table footprint. Apply a scene-only vertical scale from
  native 0.8128 m to 0.85 m, keeping its feet at the floor; do not edit source
  meshes. Convert all props and the observer into the new frame while keeping
  their relative XY placement, clearances, box orientation, masses and contact
  materials. Native robot/gripper geometry is never scaled.

### Implementation

1. Put editable, explicitly approximate room/capture parameters in a separate
   scene JSON. Start the wooden wall at X=2.0 m (1.7 m from capture), ceiling at
   Z=3.2 m, left boundary at Y=4.5 m, and rear boundary at X=-2.0 m. These are
   provisional room extents, not measured locations; the left extent also keeps
   the existing observer inside the room. Front-left furniture remains a
   photograph projected onto approximate support surfaces, not recovered meshes.
2. Create a portable background USD layer with six tessellated room surfaces.
   Bake equirectangular UVs from the fixed capture point. Use source sRGB pixels
   and their existing neutral missing regions; do not modify the panorama.
   The image center faces +X and increasing image longitude faces toward -Y.
3. Use an emissive photographic material, without diffuse relighting, and mark
   background meshes as not casting shadows. Keep physical support separate;
   background walls are visual proxies without collision. Use independent neutral
   Dome/key lighting rather than displaying an infinite photographic Dome.
4. Add a capture camera for inspection. Preserve the existing long-edge observer
   relative to the shifted workcell. Update scene validation and the existing
   settle probe to read the authored table height rather than a legacy constant.

### Acceptance

- M14-FB-01: fixed capture origin and cardinal UV orientation; moving an observer
  changes image sampling from finite walls while leaving geometry/UVs unchanged.
- M14-FB-02: table top/base at 0.85 m, table feet at floor, retained table footprint,
  box gap 235 mm, base-box distance 900 mm, unchanged HOME/yaw and robot geometry.
- M14-FB-03: portable USD/material/texture references, finite mesh bounds, correct
  sRGB texture wiring, explicit estimates, and retained neutral source gaps.
- M14-FB-04: local source/static tests and formatting/lint; deterministic CPU
  projection previews labelled separately from an Isaac render.
- M14-FB-05: Isaac Sim 6.0.1 material/visibility/parallax rendering and no-action
  PhysX settle. If unavailable locally, record NOT RUN; do not carry forward the
  pre-change scene's render/settle PASS. Remote synchronization and deployment
  are outside this local modification request.

No physical device connections or motion commands are part of this work.


### Finite-background acceptance results

- M14-FB-01 — PASS (local geometry): forward +X maps to image center, +Y to
  image-left, -Y to image-right, +Z to the upper pole. A 0.10 m observer
  translation shifts the blind sampling by 11.31 degrees at 0.5 m distance,
  versus 3.37 degrees for the wooden wall at 1.7 m. Capture origin and UVs
  remain fixed. No per-frame camera tracking is used.
- M14-FB-02 — PASS (local OpenUSD): tabletop and mounting base are at 0.85 m;
  the table feet remain grounded. Its footprint and the source asset bytes
  are preserved. Carton gap is 0.235 m, base-to-carton spacing is 0.900 m,
  and both props have 1 mm initial support clearance. All available UR link
  frames agree with HOME FK; mounting yaw remains -pi. Cube XY is now
  (0.6097, 0.019) m solely because the world origin moved. Nominal TCP is
  approximately (0.6914, -0.17415, 1.37035) m; no lateral compensation was added.
- M14-FB-03 — PASS (local OpenUSD): six finite room surfaces, portable relative
  dependencies, embedded ST, sRGB input, emissive photographic material, and
  explicit measurement/approximation metadata. Background surfaces have no
  collision; the hidden support slab retains its collider. The original
  panorama pixels and source robot/gripper/furniture assets are unchanged.
- M14-FB-04 — PASS: six new unit/static cases and five existing scene cases,
  Black and Pylint. OpenUSD 26.5, Python 3.12.13 on macOS. Pylint ignores
  member introspection only for the eight dynamically bound pxr modules
  used by these files; their APIs execute in the runtime tests.
  projection-preview.jpg is a reviewed CPU background-only projection check.
- M14-FB-05 — PARTIAL: renderer/material/visibility and 10 cm parallax checks
  PASS on Isaac Sim 6.0.1; PhysX settling remains NOT RUN. The rendering
  follow-up below records the exact result and remaining visual limitations.
  Earlier scene-folder PNG previews remain historical.

Reproduce local checks in an OpenUSD environment:

```sh
python -m unittest discover -s tests -p 'test_projected_room.py' -v
python -m unittest discover -s tests -p 'test_scene.py' -v
python scripts/preview_projected_room.py
```

The remaining Isaac check is the existing check_box_scene.py no-action settle
probe. Its support-height check now reads layout.json. Rendering and 0.10 m
camera-translation checks are complete as recorded below. The emissive
background is an appearance prototype,
not calibrated illumination or a replacement for real furniture depth.


### Multiview rendering follow-up — 2026-09-15

The user requested actual multiview screenshots of the latest setup. Rendered
an isolated copy under /tmp on ur12e-collection using Isaac Sim 6.0.1 and the
RTX 2000 Ada GPU; the station's deployed checkout was not replaced. Temporary
cameras live in the USD session layer. No hardware connections, commands, or
physics steps were used; timeline time stayed at 0.0 seconds.

- Initial render found that WoodWall, Blinds, and Ceiling faced outward.
  Their backs rendered black despite double-sided geometry. Reversed these
  three surface windings in the generator; retained the same spatial bounds,
  UV projection, texture pixels, HOME, mounting yaw, and task assets.
- After correction, all ten 1600 x 1000 PNG captures show the expected material.
  Seven targeted static/unit cases pass, including a regression check that all
  room front faces point into the room. Black and Pylint pass for the two changed
  Python files. The prior five independent base-scene tests were not repeated.
- M14-FB-05 rendering/parallax: PASS. For a 10 cm translation and 800 px focal
  length, front-wall texture features move 47.054 px (expected 47.059 px at
  1.7 m). Blind features move 159.989 px (expected 160 px at 0.5 m).
  Measurements use matched image features and the unchanged camera orientation.
- M14-FB-05 physics settling: NOT RUN; static screenshots do not validate contact.
- Visual fidelity remains approximate: oblique/distant views stretch furniture
  photographs and expose neutral missing regions. No furniture depth recovery,
  surveyed room dimensions, or calibrated illumination is claimed.

Local evidence: artifacts/finite-room-multiview-20260915/ (from the repository
root) contains ten PNGs,
gallery.html, report.json with camera poses and input scene hashes, parallax.json,
the exact render/measurement scripts, and the runtime log. Evidence is ignored
by Git; this summary remains sufficient to understand the acceptance result.
The isolated station copy is /tmp/ur12e-multiview-20260915-siv4Dt.


## M14: Clean workcell without photographic background — 2026-10-02

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Aligned scope: the user explicitly requested removing both panorama-based and
finite-distance background features, retaining the panorama files in Git LFS.
Remove the LabBackground layer/reference, photographic capture camera, room
configuration and projection/preview implementation. Preserve robot-base-centered
world coordinates, tabletop height 0.85 m, all asset geometry, mounting yaw -180
degrees, collection HOME, prop poses and the saved observer. Make the existing
physical floor visible and keep neutral lighting. The only scene objects are
the table, UR12e, Hand-E, open carton and red cube, plus floor/camera/lights/physics
support. New lab meshes will be aligned separately.

Implementation: remove the projection dependency from the composer; express the
existing tabletop height directly as a workcell constant; replace projection
tests with retained task-geometry tests and a background-free scene contract.
Regenerate, verify unchanged retained stage fields/asset hashes, run static tests
and render several views on ssh ur12e-collection. Synchronize the uncommitted
review snapshot, then align the rendered stage with the user before committing.
No physical robot or leader connections or motion commands are required.

Runtime discovery: the SSH alias now resolves to li1013-MS-7E11 (li1013), with
RTX 4070 Ti SUPER 16 GiB and the bundled ~/isaacsim/python.sh runtime. Its
VERSION is 5.1.0-rc.19+release.26219.9c81211b.gl; NVIDIA driver is 595.91.07.
This is a different installation from the previously accepted 6.0.1 station.
The scene loads through its bundled USD 24.5 libraries without Kit initialization.

Acceptance:

- PASS: all eight scene/workcell static checks on both Mac (USD 26.8) and station
  (bundled USD 24.5); Black and Pylint for the modified composer and new tests.
- PASS: all four remaining USD entrypoints resolve. The station active stage has
  no unresolved references or background dependency. Only Table, UR12e, HandE,
  carton and cube remain as task objects, with floor/lights/camera/physics support.
- PASS: every retained authored stage field is identical to the previous stage,
  except the floor visibility changing from invisible to inherited. Geometry,
  HOME FK, mounting yaw, prop poses and saved observer are unchanged. Retained
  panorama and model payloads are unchanged and remain managed by Git LFS.
- PASS: uncommitted review snapshot synchronized to ~/ur12e-sim on the station;
  active USD SHA-256 is
  ece45df51651f7e16d5e5438fdb5a9ea2469e6484273a363dc0437dc10b7ea18.
- Historical BLOCKED (resolved with 6.0.1 below): station 5.1 RTX rendering.
  Both headless and DISPLAY=:1 attempts crash
  with exit 139 in librtx.scenedb.plugin.so during SimulationApp initialization,
  before opening any project USD. The exact cause is not yet established. No
  driver changes or runtime replacement have been made. No new images exist.
- NOT RUN: PhysX settling or hardware actions; this change edits no colliders or
  physical material properties. Visual user alignment and commit remain pending.

Reproduce static checks with unittest discovery for test_box_scene.py and
test_scene.py. Station Python requires its omni.usd.libs extension directory
on PYTHONPATH and that extension's bin directory on LD_LIBRARY_PATH when using
~/isaacsim/python.sh outside SimulationApp.

Evidence: local artifacts/background-removal-20261002/local-checks.json;
station artifacts/background-removal-20261002/stage-inventory.json and
artifacts/background-removal-20261002[-display].log. Prior background acceptance
is retired. Resolve the station runtime startup failure, render the clean stage,
then align visually before committing.


### Isolated station runtime recovery — 2026-10-02

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

The user authorized retrying the installed simulator and, if it remained broken,
installing Isaac 6.0.1 in a separate home-directory virtual environment. A third
attempt with a visible GUI and desktop Xauthority still crashed with exit 139
before loading the stage. The 5.1 installation and NVIDIA driver remain intact.
Installing 6.0.1 is the selected recovery path, not proof of the crash's root cause.

Relevant station paths: ~/isaacsim is the installed standalone 5.1 runtime;
~/.local/share/applications/IsaacSim.desktop points to that installation.
~/Downloads/isaac-sim-standalone-5.1.0-linux-x86_64.zip is its installer.
The similarly named 6.0.0 Downloads ZIPs are asset archives, several with aria2
partial-download markers, not an installed executable runtime. No pre-existing
6.0.1 virtual environment was found. ~/ur12e-sim contains this scene project.

Selected environment: ~/venv/isaacsim-6.0.1, Python 3.12.14. Install using pip,
with torch==2.11.0+cu128 from https://download.pytorch.org/whl/cu128 and
isaacsim[all,extscache]==6.0.1.0 using PyPI plus https://pypi.nvidia.com.
These exact versions exist on their official indexes. Official instructions:
https://docs.isaacsim.omniverse.nvidia.com/6.0.1/installation/install_python.html
The 6.0.1 requirements list Linux driver 595.58.03 as tested; this station uses
595.91.07. Actual startup/rendering remains the acceptance condition, not driver
version similarity. The workstation has approximately 282 GiB available storage.

Execution: detached install.sh under artifacts/isaac601-install-20261002;
install.log, install.pid, status.txt and freeze.txt retain progress and resolved
packages. After pip check and the exact version check, the job automatically
renders four views with no timeline play or hardware connection. It verifies
that scene.usda's SHA-256 is unchanged before and after rendering. Output goes
under the same artifact directory's render/ and render.log. A renderer error or
failed report leaves a FAILED status; successful images still require user review.
No stage edits or commit are authorized until the recovered simulator validates
that the clean scene opens and renders. This background job does not commit.

Acceptance: 5.1 GUI retry FAIL; Python 3.12 virtual environment created and
torch==2.11.0+cu128 installed. Independent 6.0.1 installation IN PROGRESS; the
5.88 GB Kit cache wheel advanced from 119 MB to 1.77 GB over approximately 30
seconds, around 50 MB/s, without a download error. Detached installer PID is
121696; it continues independently of SSH. Per user instruction, stop download
supervision now and wait for the background installation/validation results.
6.0.1 startup/render NOT RUN yet. The original clean-scene static PASS results
remain valid. Check status.txt and actual render/report.json before updating
these conclusions or proceeding with visual alignment and commit.


### Recovered runtime and cleanup acceptance — 2026-10-02

- PASS: Python 3.12.14 environment at ~/venv/isaacsim-6.0.1; all installed Isaac
  packages pinned to 6.0.1.0, torch 2.11.0+cu128, and pip check reports no broken
  requirements. The detached install/render job finished successfully.
- PASS: actual RTX startup and four 1600x1000 views of the active clean workcell
  on li1013-MS-7E11 / RTX 4070 Ti SUPER / NVIDIA 595.91.07. Startup reaches app
  ready; total first capture job duration is approximately 103 seconds.
- PASS: agent review of all four images confirms no photographic panorama or
  finite-room background. Only the retained table, UR12e/Hand-E, open carton and
  red cube are visible with the neutral floor and lighting. The saved HOME and
  saved camera are unchanged. Timeline time is 0 and no hardware is accessed.
- PASS: source USD checksum is unchanged before/after rendering and matches the
  local clean scene. No source stage save occurred during the render probe.
- PASS: per the user's explicit removal request, delete ~/isaacsim (confirmed
  5.1.0-rc.19), the old IsaacSim.desktop launcher, its standalone 5.1.0 Downloads
  ZIP, and the empty ~/issacsim and ~/Downloads/issacsim directories. All five
  paths are now absent. No stale Isaac path appears in shell startup files.
  The 6.0.0 asset archives and ~/issac_assets were outside this runtime cleanup.
- NOT RUN: physical settling/motion. Human visual alignment PASS on 2026-10-02; the user authorized committing
  this scope. The environment recovery and clean-stage render are accepted.

Station evidence: artifacts/isaac601-install-20261002/status.txt records PASS;
freeze.txt records resolved packages; render/report.json and four PNGs record
actual cameras, timeline and scene hash. removed-51.json records exact removals.
The same render evidence is copied to local artifacts/isaac601-install-20261002/
render/. Keep it Git-ignored; versioned conclusions are recorded here.


### User alignment and layout reference — 2026-10-02

The user accepted the clean stage and authorized a commit. Background removal
and recovered-runtime rendering are accepted; broader PhysX settling and physical
motion acceptance remain outside this change. Preserve all panoramic source
payloads in LFS. Do not push automatically.

The user requested world-axis directions and named tabletop corners for future
layout instructions. See workcell-coordinates.md for A/B/C/D labels. Coordinates
were checked against the saved tabletop's world-space USD bounding box; this
reference document adds no stage geometry or behavior.


## Table2 addition — 2026-10-02

The existing workbench is named Table1. An identical static Table2 is added
using the corrected B1-D2 distance and 20-degree line angle. See
[the placement plan](table2-layout.md) and [coordinates](workcell-coordinates.md).
Static checks, simulator rendering and user visual alignment pass. The user
authorized committing the Table2 placement on 2026-10-02. Prior accepted robot/workbench/prop geometry remains unchanged.
