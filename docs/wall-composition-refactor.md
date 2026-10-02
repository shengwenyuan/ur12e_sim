# M14: Wall Composition Refactor

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted on 2026-10-03. The user approved the unchanged previews and requested a commit. The user approved the proposed WallPanel /
WallAssembly composition and requested refactoring, tests and unchanged renders.
Baseline: main 164acc8c630909b1e01f128099de7a09172794fc.

## Scope and boundaries

Separate immutable metric layout parameters, reusable USD wall/material
construction, and independent geometry measurements/acceptance. Keep scene
specific placement formulas in the existing focused builders. WallPanel is a
static box description; WallAssembly composes named panels and nested local
assemblies. Use composition, no abstract base classes or plugin registry.

Centralize the existing furniture, room, partition and red-wall dimensions in
one Python layout module. Keep materials in a standalone authoring module,
without a glass partition importing another wall builder to locate its material.
Centralize local-frame bounds; validators must measure actual USD geometry
and remain separate from construction. Preserve existing prim paths, xform
operation order/types, references, bindings, metadata and JSON schema.

No change to robot HOME, object placement, tables, chair, floor, lights,
calibrated camera intrinsics/extrinsics, physics settings or observer. No
hardware connection or timeline play. No collection/inference refactor.
The runtime scene remains the existing USD; configuration is authoring-only.

## Steps and acceptance

1. Freeze the baseline scene and preview evidence. Introduce focused immutable
   panel/assembly descriptions, metric configuration and material authoring.
2. Migrate the four wall/furniture builders; isolate measurement and validators.
   Keep compose_box_scene.py as the scene orchestration entry point.
3. Add a regression that rebuilds the Furniture subtree from the existing
   layout in a disposable relocated workspace and compares every authored
   field to the accepted USD. Verify transformed nested panels independently.
4. Run relevant workcell, camera, base-scene and board-crop checks plus new
   regression tests on Mac and station USD; run Black, Pylint and diff checks.
5. Rebuild the complete scene from the collection HOME profile and require
   unchanged scene, layout and report data. Preserve the baseline payloads.
6. Deploy an isolated station workspace, render the same overview, complete
   top and interior views in Isaac 6.0.1, and compare the captured images.
   Record numerical differences honestly; renderer noise is distinct from
   a geometry change. User visual acceptance follows the previews.

Local acceptance cases: WCR-01 authored field and layout equivalence;
WCR-02 shared composition/material/measurement behavior;
WCR-03 existing scoped tests and tooling; WCR-04 static Isaac preview.
These are scene checks under M14, not a replacement for its trajectory sink
acceptance IDs or physical contact acceptance.

## Resulting structure

- wall_layout.py: frozen, metric FurnitureLayout / RoomLayout /
  PartitionLayout / RedWallLayout specifications and stable prim/material
  paths. Derived widths and heights remain explicit properties.
- wall_components.py: WallPanel authors one static bound collision box;
  WallAssembly composes named panels and nested local frames. Assemblies
  without a pose leave implicit groups untouched, preserving existing USD.
- wall_materials.py: shared paint, PBR and Thin Walled glass authoring with
  PreviewSurface fallbacks. Materials use explicit paths; the partition can
  initialize its glass without importing the room builder.
- scene_geometry.py: Table2 frame and exact leaf-bound unions in an explicit
  measurement frame. This replaces the duplicated room/partition helpers.
- wall_validation.py: geometry/material/collision acceptance only; it imports
  no construction module. The four original builders now handle placement
  and layout metadata; compose_box_scene.py orchestrates them and validation.

To extend the scene, describe dimensions in wall_layout.py, compose panels in
one focused builder and measure the resulting geometry in wall_validation.py.
Do not put scene-specific furniture anchors into WallPanel / WallAssembly.
Each build targets a fresh stage/subtree; these authoring methods are not
incremental editing or real-time physics APIs.

## Actual acceptance (2026-10-03)

- WCR-01 PASS: reconstructed all four furniture/wall modules in a disposable
  relocated dependency closure after removing the accepted Furniture subtree.
  Every authored field and the four returned layout dictionaries match the
  accepted scene. A complete scene rebuild using the unchanged collection
  HOME profile matches all 2,549 authored fields, layout.json and
  scene-report.json exactly. The original and rebuilt scene SHA-256 are both
  92179315de2e0a9984b5396cdaaca9359abe59aa6c9d8e1258a2531d23666413.
  The checked-in scene/JSON payloads were not modified by this refactor.
- WCR-02 PASS: independent nested-frame test verifies a panel's world pose,
  local metric bounds, shared binding and static collision under two rotated
  assemblies. Invalid dimensions/material paths are rejected before panel
  geometry is authored. The partition builds with valid Thin Walled glass
  without invoking or importing room_extension.
- WCR-03 PASS: 19 relevant tests on each of Mac Python 3.12.13 / USD 26.8 and
  Ubuntu Python 3.12.3 / bundled USD 25.11. Patterns: test_wall_composition.py
  (4), test_box_scene.py (3), test_calibrated_cameras.py (5), test_scene.py (5),
  test_cut_wood_board.py (2). Black passes for all 12 changed/new Python
  files; Pylint scores 10/10. Native USD bindings are excluded from static
  attribute inspection. Two narrowly documented dimensional-dataclass lint
  exceptions preserve cohesive specifications rather than artificial groups.
  git diff --check passes. Unrelated inference/control tests are outside scope.
- WCR-04 PASS (technical): bounded static Isaac 6.0.1.0 renders on ur12e-flexlab
  / RTX 2000 Ada, driver 595.84. The isolated station workspace is
  ~/ur12e-sim/artifacts/wall-refactor-20261003/workspace/. Existing unrelated
  station checkout changes are preserved. Overview, complete top and interior
  frames use the same camera settings as the preceding accepted previews.
  Source checksum stays unchanged, timeline remains zero, physics_steps=0,
  hardware_control=false and scene_saved=false. Both render jobs exited.
- Screenshots are not pixel-identical: mean absolute RGB channel differences
  on the 0-255 scale are 0.291 (overview), 0.131 (top), 0.222 (interior with
  matching capture order). Geometry/materials and camera values are identical.
  An initial combined-run interior capture differed by 2.827; matching the
  earlier standalone capture order reduced that difference. These are render
  differences, not an accepted change to the scene. Reports retain both runs.
- User visual acceptance: PASS on 2026-10-03. Dynamic contacts and real
  hardware behavior: NOT RUN, outside this unchanged static-scene scope.
  No robot connection/control occurred; the previously stopped model service
  remains off. The user requested delivery of the verified refactor as a separate commit.

Evidence is retained under artifacts/wall-refactor-20261003/ on the Mac and
station. Local equivalence.json and full-rebuild.log describe the complete
rebuild; mac-static-check.log records the 19 local tests. The render directory
contains station logs, reports, comparison metrics and captures. Review
render/01_overview.png, render/02_top_view.png and
render/views-inside/03_inside_out.png.

Reproduce with unittest discovery for the five patterns above in the existing
USD-enabled runtime. The new equivalence test relocates actual dependencies
and compares against the checked-in accepted USD; it requires no collection
package, Kit or hardware. To regenerate the complete scene, use
scripts/compose_box_scene.py --collection-root ../ur12e_collection and compare
against baseline revision 164acc8; this also checks the real HOME source.
