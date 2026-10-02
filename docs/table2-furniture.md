# M14: Table2 Furniture and Walls

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted. Concrete geometry and wall thickness were
confirmed by the user on 2026-10-02 after Table2 acceptance.

## Scope and interfaces

Reuse Table2's measured A/B/C/D coordinates and local axes. Import only the
Isaac dependency closure of wood_board and red_cushion_caster_chair. Assets and
scene payloads use Git LFS. Original source exports remain untouched.

Place two upright 2 m wide, 2.5 m high, 18 mm thick boards outside AB. The first
ends at BC and extends along B-to-A; the next touches it, forming a 4 m run.
Keep their front faces toward the table and their bottoms on the floor.
Place the chair outside CD near C, facing C-to-D, with its back beyond BC.
Use 50 mm nominal lateral clearance from the tabletop and keep the chair clear
of the perpendicular wall.

Create two static wall boxes, height 3 m and thickness 5.75 inches = 0.14605 m.
The long wall follows the boards' 4 m run, immediately behind them. The short
wall follows BC from B toward C for 0.682 m (80 mm shorter than the table).
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
