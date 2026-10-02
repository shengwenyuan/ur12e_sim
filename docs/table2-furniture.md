# M14: Table2 Furniture and Walls

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted. The user approved committing and pushing the width
refinement on 2026-10-03 after the station preview. Retain historical results.

## Scope and interfaces

Reuse Table2's measured A/B/C/D coordinates and local axes. Import only the
Isaac dependency closure of wood_board and red_cushion_caster_chair. Assets and
scene payloads use Git LFS. Original source exports remain untouched.

Place upright 2 m and 1.4 m wide, 2.5 m high, 18 mm thick boards outside AB.
The first ends at BC and extends along B-to-A; the next touches it, forming
a 3.4 m run. The second board is cut at its far end, preserving its texture
scale and the seam with the first board.
Keep their front faces toward the table and their bottoms on the floor.
Place the chair outside CD near C, facing C-to-D, with its back beyond BC.
Use 50 mm nominal lateral clearance from the tabletop and keep the chair clear
of the perpendicular wall.

Create two static wall boxes, height 3 m and thickness 5.75 inches = 0.14605 m.
The long wall follows the boards' 3.4 m run, immediately behind them. The short
wall follows BC from B toward C for 0.642 m (120 mm shorter than the table).
Both walls use a shared white OmniPBR material, roughness 0.9, metallic 0.
OmniPBR.mdl is a built-in Isaac runtime dependency, not a bundled asset. A USD
PreviewSurface fallback permits inspection in generic USD tools. Missing mesh
or texture references remain failures; only the built-in MDL name is exempt
from generic USD file resolution.

Preserve Table1, Table2, robot HOME, tool, props, saved observer and lighting.
New environment geometry lives under /World/Furniture. Disable rigid-body
motion on the boards and chair, retain enabled colliders. No robot connection,
physics stepping, driver changes or inferred manipulation behavior.

## Implementation and acceptance

1. Import minimal asset closures with English provenance and checksums.
2. Add an isolated furniture composer using shared asset placement code.
3. Measure grounded geometry, board seams/end alignment, wall dimensions,
   chair direction and separation, static flags, materials and colliders.
4. Run existing scene checks, formatting and lint. Compare previously authored
   stage fields to the accepted Table2 scene.
5. Synchronize to ur12e-collection and render overview, top and detail views in
   Isaac 6.0.1; keep observer edits session-only and timeline stopped.
6. Record results here and present the preview for user visual acceptance.

## Results — 2026-10-02

- PASS: actual composed geometry is grounded; board seams and BC-end alignment
  pass; both board fronts face the table. Board1 center is
  (2.71257, 0.13412, 1.25) m and Board2 (2.02853, -1.74527, 1.25) m.
- PASS: chair front follows C-to-D; its back extends beyond BC. Measured side
  clearance is 0.05158 m; the chair is outside the short wall's end.
- PASS: 1 enabled collider per board, 115 on the chair, 1 per wall. Boards and
  chair have rigid-body motion disabled. Wall boxes are grounded and static.
  The two wall faces meet through the 18 mm board end at B; the short wall's
  span along BC is exactly 0.682 m. OmniPBR settings and bindings pass.
- PASS: all 342 retained authored scene fields match accepted Table2 revision
  48ab3c4; the Furniture subtree is additive. Robot HOME, props, tables,
  lighting and persistent observer are unchanged.
- PASS: eight existing scene checks on Mac USD 26.8 and station Isaac USD
  libraries; Black and Pylint 10/10 for all four touched Python files.
- PASS: four 1600x1000 views rendered in Isaac 6.0.1.0 on ur12e-collection /
  li1013-MS-7E11 / RTX 4070 Ti SUPER / NVIDIA 595.91.07. The installed built-in
  OmniPBR.mdl is present; no MDL compilation or material errors were logged.
  Overview/top images were inspected. Timeline remains at zero, no physics
  steps or hardware connection, and camera edits remain session-only.
- PASS: minimal source asset closure totals 9,692,378 bytes, without raw photos,
  Blender, Gazebo, duplicate USD exports or manufacturing files. Asset and
  scene paths inherit the repository's Git LFS rules.
- PASS: user accepted the rendered furniture layout and authorized its commit
  on 2026-10-02. The separate Table2 commit is 48ab3c4.
- NOT RUN: motion/contact settling, outside this static layout's scope.

Evidence: ignored artifacts/table2-furniture-20261002/ on both computers has
four PNGs and report.json; the station log is
artifacts/table2-furniture-20261002.log. Scene SHA-256:
10c54c2d56824dd1998694f575829ee6770918c89d723bc1a9922edb640f2386.

Generic USD dependency scanning warns about OmniPBR.mdl, which it cannot resolve
without Isaac's MDL search paths. This single known built-in is explicitly
allowed; missing textures or USD references are never ignored.

Material authoring follows the official NVIDIA USD API example:
https://docs.omniverse.nvidia.com/dev-guide/latest/programmer_ref/usd/materials/create-mdl-material.html

## Width refinement — 2026-10-02

Aligned by the user's exact request after the three-camera comparison:

- Shorten the BC wall from 0.682 m to 0.642 m, keeping its B endpoint fixed.
- Cut 30% from Board2's original 2 m width, leaving 1.4 m. Keep Board1 and
  the joining end fixed; crop the original geometry and UVs rather than scale
  the board. Close the exposed cut face and resize its static box collider.
- Shorten the behind-board wall to the resulting 3.4 m run. Move the far-end
  block and the complete glazed extension by +0.6u, approximately
  (+0.2052121, +0.5638156, 0) m. Retain all local glass/frame dimensions.
- Preserve both tables, chair, robot HOME, props, all three calibrated cameras,
  observer and lighting. Share original textures through a referenced derived
  board asset; do not duplicate photos or modify the original 2 m asset.

Implementation: derive the cut board asset, use shared run lengths in both
furniture and room composers, regenerate the scene and layout reports, then
validate geometry, closed topology, retained UVs and unchanged scene fields.
Run existing USD checks and formatting/lint. Finally render a stopped-timeline
Isaac preview on ur12e-collection, without hardware access or physics steps.

Refinement results:

- PASS: 0.642 m short wall with its B endpoint fixed; widths 2.0/1.4 m and
  3.4 m long paint wall. Board seam and grounded support remain exact.
- PASS: cut mesh has 53 vertices, 102 nondegenerate triangles and 153 shared
  edges, each incident to two faces. The cap is closed and outward-facing;
  front-photo UVs retain the original scale and stop at 70% of photo width.
  The unscaled collider matches 1.4 x 0.018 x 2.5 m. The original source asset
  checksum is unchanged; the derived 20 KB layer shares original textures.
- PASS: room origin (1.6353467, -2.4062516, 0) m moves by exactly +0.6u.
  All local panes, frames, walls and materials retain their dimensions.
- PASS: 1,261 prior authored scene fields compared; exactly seven intended
  fields changed (Board2 reference/transform, long/short wall scale/position,
  and room translation). Tables, robot HOME, props, chair, three calibrated
  cameras, observer and lighting are unchanged.
- PASS: 15 relevant tests: two cut-asset, three workcell, five calibrated-camera
  and five base-scene checks on Mac Python 3.12.13 / USD 26.8. Black and Pylint
  10/10 for all four changed/new Python files. Reproduce using unittest
  discovery patterns test_cut_wood_board.py, test_box_scene.py,
  test_calibrated_cameras.py and test_scene.py.
- BLOCKED: broad discovery also attempted unrelated inference/physical/pose
  suites; their imports require websockets and the collection package, absent
  from this temporary USD-only environment. These suites were not executed;
  their discovery failures do not establish a full-suite pass.
- NOT RUN on 2026-10-02: station synchronization, Isaac rendering and user
  visual acceptance. The user deferred rendering while the station was
  unreachable; see the 2026-10-03 results below for the completed station run.
  No hardware connection or physics steps occurred.

Evidence: ignored artifacts/board-width-refinement-20261002/static-report.json.
The scene and derived asset inherit Git LFS. The seven changed authored fields
and scene checksum are recorded in that report. This refinement supersedes
the original width conclusions above; visual acceptance remains pending.

## Station validation — 2026-10-03

- PASS: SSH ur12e-collection reaches ur12e-flexlab, home
  /home/robot2026fall, NVIDIA RTX 2000 Ada Generation 16 GiB / driver 595.84.
  The existing ~/venv/isaacsim-6.0.1 runtime is Isaac 6.0.1.0, Python 3.12.3.
- PASS: synchronize the 60-file scene/asset/test closure (25,232,027 bytes)
  into ~/ur12e-sim/artifacts/board-width-refinement-20261003/workspace/.
  Existing unrelated checkout edits remain untouched. Scene and cut-asset
  checksums match the Mac sources.
- PASS: all 15 relevant tests above also pass against the station's bundled
  USD libraries, without starting Kit or connecting to hardware. The known
  generic-USD warnings for Isaac's two built-in MDLs remain exempt; the actual
  installed MDLs are verified by the subsequent renderer.
- PASS: five 1600x1000 RGB previews rendered in Isaac 6.0.1.0. Overview and
  top views were visually inspected: unequal board widths, the retained seam
  and adjoining matte/glazed walls are visible. No material compilation
  failure occurred in the successful run. Timeline is 0 seconds, physics
  steps are zero, hardware control is false, and the persistent camera and
  source scene are not saved or changed.
- The initial preview invocation used a relative workspace root and failed
  dependency resolution. Repeating with the absolute root passed; the failed
  attempt is retained on the station as render-attempt1.log and render-attempt1-report.json.
- The user explicitly requested closing the model service to release its
  approximately 12 GiB of GPU memory. The model server was stopped with
  SIGTERM; its listening port 8000 is closed and it was not restarted. The
  bounded Isaac process exited too; final GPU memory usage is 17 MiB.
- NOT RUN: user visual acceptance and dynamic/contact validation. This is
  static layout acceptance; the latter remains outside its scope.

Evidence: ignored artifacts/board-width-refinement-20261003/ on both hosts
contains static-check.log, render.log and views/{01_saved_view,02_room_overview,
03_top_view,04_windows_inside,05_windows_outside}.png plus views/report.json.
The remote test workspace remains separate from the station's main checkout.
Scene SHA-256: 48f816eecd59acb9ffce06f514749da328a358078fbcbf37563960a0e431af6b.
This run supersedes the prior station-connectivity blocker.

User acceptance — 2026-10-03: the user approved committing and pushing this
refinement after the station previews. Static geometry, regression and render
acceptance are PASS; dynamics remain outside the layout scope.
