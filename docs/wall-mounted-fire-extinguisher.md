# M14: Wall-Mounted Fire Extinguisher

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: implemented / user visual acceptance pending on 2026-10-03. Scope follows the user's concrete placement/import request.
Refactor prerequisite is committed separately as 4182964.

## Scope and placement

Import only isaac/fire_extinguisher.usdc and its three actual PNG dependencies
from the user-provided fire_extinguisher asset. Keep the source binary and
textures unchanged under assets/props/fire_extinguisher/{isaac,textures}/.
Do not include duplicate ASCII USD, drop-test scenes, printing, Gazebo,
Blender, source scripts or unused interchange meshes. Assets and scene files
inherit the existing Git LFS rules.

Mount on the room's right white corner column, /World/Furniture/Room/EndWall,
on its room-facing +Y surface in the Room frame. This face runs along Table2
AB (+u), adjoining the perpendicular glazed room extension. Center the full
fixture width on the exposed column face beyond the glazing's thickness;
keep it entirely within the column and clear of the glass. The source asset
front faces -Y, so rotate it 180 degrees in the Room frame to face +Y.

Interpret 26 inches as the fixture's lowest geometry above the ground:
0.6604 m. Preserve native metric dimensions (approximately 0.2493 x 0.1545 x
0.556 m). Place its rear bound 5 mm from the wall as a small mounting gap.
Override the placed rigid body as disabled/static while retaining all enabled
source colliders. Do not alter source mass estimates or create a dynamic
hanging constraint. No wall bracket geometry is requested.

## Implementation and acceptance

1. Freeze the accepted scene baseline. Copy the minimal USD dependency closure
   and record source hashes and size in this plan's results.
2. Add a focused fixture builder and immutable mounting parameters. Derive
   placement from actual column/glass and asset bounds; preserve all existing
   layout and authoring responsibilities. Do not change the wall abstractions.
3. Keep independent acceptance checks: 660.4 mm bottom, facing direction,
   metric dimensions, wall stand-off, exposed-column containment, glass
   clearance, enabled static collisions and portable dependency paths.
4. Integrate fixture layout/report metadata and extend the relocated Furniture
   reconstruction test so the complete furniture subtree remains reproducible.
   Compare retained fields with the pre-fixture scene and run scoped tests,
   Black and Pylint. No collection or real-robot behavior changes.
5. Synchronize an isolated station workspace and render overview/corner detail
   in Isaac 6.0.1 with timeline stopped and zero physics steps. Show results
   for user visual acceptance. The new fixture remains uncommitted until review.

## Results

- PASS: copied only one native USDC and its three referenced textures, totaling
  1,621,122 bytes. Their SHA-256 hashes match the source files. The project
  asset is assets/props/fire_extinguisher/isaac/fire_extinguisher.usdc, with
  ../textures references preserved. Native USD dependency closure resolves;
  all four files inherit the assets/** Git LFS rule.
- PASS: fixture lowest geometry is exactly 0.6604 m above the floor. Native
  dimensions are (0.2492963374, 0.1545000002, 0.5559999943) m. The fixture's
  front faces Room +Y / Table2 +v. Room-frame origin is approximately
  (0.2139481685, 0.0790000019, 0.6604) m; world origin is
  (1.6342855462, -2.1781864981, 0.6604) m, world yaw 250 degrees.
- PASS: rear bound is 5 mm from the EndWall's +Y face. The fixture is centered
  within the exposed column face beyond the perpendicular glazing's 80 mm
  thickness and clears that glazing by 13.1518 mm. Whole fixture bounds stay
  within the column width/height. Its source root rigid body is disabled in
  the scene; all 29 source collision shapes remain enabled and static.
- PASS: every one of the 2,549 previously authored scene fields is unchanged.
  Prior layout and report values are identical; the fixture and its metadata
  are additive. Robot HOME, objects, tables, chair, walls/glass, lights,
  observer and calibrated cameras were preserved.
- PASS: 19 relevant tests each on Mac Python 3.12.13 / USD 26.8 and Ubuntu
  Python 3.12.3 / bundled USD 25.11: test_wall_composition.py (4),
  test_box_scene.py (3), test_calibrated_cameras.py (5), test_scene.py (5),
  test_cut_wood_board.py (2). The relocated reconstruction includes the new
  fixture and compares all authored fields. Existing independent workcell
  validation includes the mounting/scale/collision checks. Black and Pylint
  10/10 passed for the five changed/new Python files; diff whitespace checks
  pass. No unrelated collection/inference acceptance is claimed.
- The first generation run hit an acceptance tuple editing error; it was
  corrected before deployment. Subsequent generation and both test runs pass.
- PASS: isolated dependency closure deployed to
  ~/ur12e-sim/artifacts/fire-extinguisher-20261003/workspace/. Existing unrelated
  station checkout changes are untouched. Overview, corner and close-up RGB
  captures rendered in Isaac 6.0.1.0 on ur12e-flexlab / RTX 2000 Ada with
  driver 595.84. Close-up and corner views were inspected: red bottle, hose,
  handles, label and photo tag appear on the white corner-column face,
  next to the wooden board and perpendicular glazing. No texture failures.
- PASS: rendered source SHA-256 is
  1cd8818aab45d19bac273af64ec27f2dc7d7aaf3a1280d21161e72a5be86e029.
  Session-only observers leave the scene file and saved cameras unchanged.
  Timeline=0, physics_steps=0, hardware_control=false, scene_saved=false.
  The bounded renderer exited; no hardware connection/control occurred.
  The previously stopped model service remains off.
- User visual acceptance: pending. Dynamic wall mounting/contact and physical
  hardware tests: NOT RUN, outside this static layout scope. The fixture and
  new scene edits are uncommitted; 4182964 contains only the prior refactor.

Evidence: ignored artifacts/fire-extinguisher-20261003/ contains the baseline,
import-and-retention.json (file hashes and retained-field comparison), local
static checks, render scripts and station logs/reports/captures. Review
render/01_overview.png, render/02_corner.png and render/03_fixture_detail.png.
Station artifacts use the same run name and an isolated workspace. Reproduce
with scripts/compose_box_scene.py --collection-root ../ur12e_collection,
then run the five unittest discovery patterns above in a USD-enabled runtime.

## Scene commit delivery (2026-10-03)

The user requested a commit of the latest reviewed scene after accepting the
darker floor. Include this previously implemented fixture in that scene
snapshot. The final overview and camera_3 calibrated view show its placement
on the corner column. All 19 relevant local tests, Black and Pylint pass at
this delivery point. The final review uses scene SHA-256
`c894e486e9cb2033e513329ec34ef23888ccd3262d3d046a3b1d02c65d0a7722`
and records zero physics steps and no hardware control. Evidence is under
`artifacts/terrazzo-floor-darker-20261003/final-review/`.
