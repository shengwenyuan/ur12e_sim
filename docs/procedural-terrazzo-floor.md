# M14: Simple Procedural Terrazzo Floor

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted on 2026-10-03. The user approved the interior-only floor and requested its commit; the darker material was committed in 9f43641.
The photograph is visual reference only; it is not imported as a texture.

## Scope

Bind one small project MDL material to /World/Floor. Use NVIDIA's built-in
base::worley_noise_texture in cell mode, world metric coordinates, an approximately
4 mm cell scale and 20% nominal selected-cell coverage. Selected irregular cells
vary from light gray to white on a gray cement-colored base. Target the requested
2-6 mm visual range rather than asserting strict per-cell geometric dimensions.
Use the installed scratched_plastic dielectric with roughness 0.75 and IOR 1.5.
Do not add bump, normal, displacement, seams, texture images or extra geometry.
Retain the 16 x 16 x 0.02 m floor, transform, top Z=0 and collision settings.

Keep authoring in one small floor material helper and the procedural shader in
assets/materials/terrazzo.mdl; use a uniform-gray PreviewSurface fallback for
non-MDL viewers. Reference the MDL using a scene-relative asset path. No SDK
installation or vendored noise library. Existing uncommitted extinguisher work
is preserved and remains separate from the already committed wall refactor.

Official API reference:
https://github.com/NVIDIA/MDL-SDK/blob/master/examples/mdl/nvidia/sdk_examples/procedural_noise.mdl
The implementation calls the built-in base function; it does not copy the SDK
example or its noise implementation.

## Steps and acceptance

1. Freeze the pre-material scene; add the compact MDL and binding helper.
2. Regenerate the scene. Compare all prior fields: allow only the floor's
   material binding and new material subtree. Existing collision geometry,
   robots, walls, assets, cameras and fixture layout remain unchanged.
3. Resolve local USD/MDL dependencies, run relevant workcell/camera/rebuild
   tests and Python formatting/lint. No new test framework or synthetic
   shader tests for this low-impact material edit.
4. Synchronize an isolated station workspace and render overview plus a close
   floor patch. Check native MDL compilation and actual visible color grains.
   Keep timeline stopped, zero physics steps and no hardware connection.
5. Record results and show previews. No commit or push in this request.

## Results

- PASS: the procedural MDL is 834 bytes; no texture images or SDK dependency
  were added. Native Isaac renders show irregular light-gray/white color grains
  on the gray floor. No MDL compilation error was found in the render logs.
- PASS: compared 2,564 prior authored fields. The sole existing-field change is
  adding MaterialBindingAPI to the floor; the binding and material subtree are
  new. Floor geometry, transform, collision, layout and scene report are unchanged.
- PASS: 12 relevant tests passed locally and on the station (wall composition,
  box scene and calibrated cameras). Black checked the three touched Python
  files; Pylint scored 10.00/10.
- PASS: isolated station rendering used Isaac Sim 6.0.1.0 and the RTX 2000 Ada.
  Overview and floor close-up were captured with the timeline stopped, zero
  physics steps, no hardware connection and no scene save. Scene SHA-256:
  `645d1db26e350ea344e2680115093df03f9cdbccac5c2fb4590993652cc8101b`.
- The first close-up was clipped by the camera's default near plane. Reshooting
  with a session-only 5 mm near plane resolved the framing; the saved scene
  camera was not changed. The render process exited; GPU use returned to 17 MiB.
- Evidence: `artifacts/terrazzo-floor-20261003/`; corrected close-up:
  `render/views-close/02_floor_patch.png`, overview: `render/01_overview.png`.
- Visual scale and coverage are approximate procedural settings, not measured
  aggregate dimensions. Non-MDL viewers use the uniform gray fallback.
  User visual acceptance remains pending. No commit or push was made.

## Darker base-color adjustment (2026-10-03)

The user accepted the first material and requested a slightly darker gray base.
Reduce linear RGB from (0.18, 0.19, 0.18) to (0.14, 0.15, 0.14), keeping grains,
coverage, scale and roughness fixed. Update both MDL defaults and the authoring
helper/fallback, then rebind the saved floor and render the same close-up.
Acceptance: only the two base-color inputs may change in the stage; geometry,
collision and other material inputs must remain exact.

- PASS: exact prior-field comparison found only the MDL base-color input and
  PreviewSurface diffuse-color input changed. All other authored fields match.
- PASS: the three existing box-scene tests and Black check passed locally.
- PASS: Isaac Sim 6.0.1.0 rendered the same close-up with the darker floor base,
  zero physics steps and zero timeline time; the saved camera was unchanged.
  Scene SHA-256: `c894e486e9cb2033e513329ec34ef23888ccd3262d3d046a3b1d02c65d0a7722`.
- Evidence: `artifacts/terrazzo-floor-darker-20261003/`; new image:
  `render/views/02_floor_patch.png`. Original visual design is accepted;
  darker-base visual confirmation remains pending. No commit or push made.

## Final three-view review and delivery (2026-10-03)

The user accepted the darker floor and requested an overview plus the two
saved D435 views, followed by a commit. All three rendered successfully in
Isaac Sim 6.0.1.0 from scene SHA-256
`c894e486e9cb2033e513329ec34ef23888ccd3262d3d046a3b1d02c65d0a7722`.
The overview is 1600 x 1000; camera_2 (serial 327122073926) and camera_3
(serial 327122075735) are native 640 x 480 calibrated views. Camera extrinsics
and native lens parameters are unchanged. Render evidence records zero
physics steps, timeline time zero, no hardware control and no scene save.

PASS: all 19 relevant tests passed on the local USD runtime; Black checked
seven modified Python files and Pylint scored 10.00/10. The selected source,
asset dependency closure and documentation were manually reviewed before
staging; this is not an automated secret scan. The source asset and scene
continue using existing Git LFS rules. Ignored screenshots/logs are not staged.

Evidence: `artifacts/terrazzo-floor-darker-20261003/final-review/scene-review/`
contains `01_overview.png`, `02_d435_left.png`, `03_d435_right.png` and the
native runtime report. This commit also includes the previously implemented
wall-mounted extinguisher and its documented static acceptance results.

## Interior-only floor extent (2026-10-03)

Status: aligned with the user's instruction to keep terrazzo inside the glass
walls and use a simple implementation. Keep the approved shader unchanged.
Add one horizontal, double-sided USD polygon at Z=0.0002 m, bound to the
existing floor material. Derive its perimeter from the painted back corner,
short wall, all glass-run endpoints and the far end of the perpendicular
room wall. Close the existing unbuilt room opening by a straight segment
between those two wall endpoints; this adds no closing wall. The perimeter
runs beneath the wall centerlines, so it does not require offsets, boolean
cuts, triangulation code or shader masks. Record its world XY points in layout.

Keep the original 16 m square support/collider at Z=0, remove its terrazzo
binding and leave its plain default gray appearance. The new interior finish
has no collision API and no displacement. Preserve all other geometry,
lights, camera optics/poses, material values and existing layout/report fields.

Acceptance: verify retained fields and the collider, a single valid planar
polygon, portable material binding, interior coverage of both table feet and
exclusion of the exterior red wall; run relevant existing tests, Black/Pylint,
and render an overview plus the two saved D435 views without timeline play.
No commit or push is requested for this adjustment.

- PASS: one 12-point planar polygon uses the unchanged approved floor material.
  Both tables' XY bounds and the robot/task area lie inside; the exterior red
  wall lies outside. The floor finish has no collision API. Its 0.2 mm visual
  offset avoids coincident surfaces without changing the support plane.
- PASS: all prior authored fields remain exact except removal of the original
  floor material binding and MaterialBindingAPI. Only /World/RoomFloor is added.
  Existing layout keys and the scene report are unchanged; layout gains one
  floor entry with its boundary points and closure convention.
- PASS: 19 existing relevant tests passed locally; the three box tests passed
  again with added binding/planarity/no-collision checks. Black formatted the
  three touched Python files; Pylint scored 10.00/10. The first comparison
  assertion omitted one metadata field on the removed binding; accounting
  for that deleted relationship resolved it. The geometry check then passed.
- PASS: Isaac Sim 6.0.1.0 overview and both native 640 x 480 D435 views show the
  patterned floor within the room and plain gray outside. The concave single
  face renders correctly without custom triangulation. Source SHA-256:
  `4f6843f1e05025af169084648b75177634149374dc36af98a8f10143fe09d5da`.
  Timeline=0, physics_steps=0, hardware_control=false, scene_saved=false.
- Evidence: `artifacts/interior-floor-20261003/` contains the prior snapshot,
  retained-field and coverage checks, static-check summary and render captures.
  User visual acceptance of the extent remains pending; no commit or push made.

User acceptance: the user requested the interior-floor commit on 2026-10-03 after reviewing the render. The extent is accepted.
