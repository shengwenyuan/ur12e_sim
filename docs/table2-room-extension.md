# M14: Far-End Wall and Glazed Room Extension

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted. The user approved the board-width refinement commit and
push on 2026-10-03 after station rendering.

## Scope

Retain the accepted workcell from 3d20126. Add matte white paint walls at the
opposite end of the 3.4 m board run, followed by an orthogonal glazed room wall.
Use the Table2 frame from docs/workcell-coordinates.md: u points A-to-B,
v points B-to-C. The board run goes from B toward -u. The far-end
anchor is B - 3.4u = (1.88326, -2.11806, 0) m.

The end-wall footprint is 14 inches = 0.3556 m along u (board width direction) and 0.1524 m
along v (normal to board face), confirmed by the user. It extends beyond the
board's far end in -u and from the board back face toward +v. Its height is 3 m.
In the Table2 B-origin frame it occupies u=[-3.7556,-3.4], v=[-0.018,0.1344].

The room wall is 4.0465 m long, 3 m high and 0.08 m thick. It extends toward +v
(table side), perpendicular to the boards. Align its outer face to the end
wall's outer -u face: u=[-3.7556,-3.6756]. Start at the end wall's room-side face
v=0.1344 and end at v=4.1809. The length excludes the end-wall footprint.

Glass panes have bottoms at 16 inches = 0.4064 m above the floor, heights
2.4 m and thicknesses 0.02 m, centered in the 0.08 m wall thickness. Tops
are at 2.8064 m, leaving 0.1936 m to the 3 m ceiling plane. Pane widths are
93.5 inches = 2.3749 m and 48 inches = 1.2192 m; a 1.5 inch frame is 0.0381 m.
Both widths are clear glass sizes. Each pane has a four-sided 0.0381 m border.
Place the 2.3749 m glass first, then the 1.2192 m glass along +v, with adjoining
frames and no intervening paint wall. The two frames remain distinct (their
adjacent vertical borders together span 0.0762 m). The framed opening widths
are 2.4511 m and 1.2954 m, totaling 3.7465 m. Begin the first frame at the wall
start and add exactly 0.3 m of solid white wall at the far end. The wall
length is derived from the unchanged 3.7465 m framed openings plus this tail.

Frame material is the same white matte paint; frame depth is 0.08 m. Glass is
centered across the wall thickness, with 0.03 m recess on both sides. Window
frame bottom/top are 0.3683/2.8445 m; retain white wall below and above these
openings. Segment wall geometry around real openings, with no opaque box
behind either glass pane.

Use the existing shared OmniPBR white matte paint. Use Isaac's built-in glass
MDL with Thin Walled enabled, and a portable USD preview where feasible.
Keep simple static box collisions for paint, frames and glass. This is a room
layout preview, not an optical or material-measurement calibration.

## Implementation and acceptance

1. Record the user's selected orientation, dimensions and window layout.
2. Add focused room-composition helpers, sharing existing wall material/box
   construction without altering robot, furniture or persistent observer.
3. Validate opening extents, wall/pane centering, border sizes, 90-degree join,
   grounded geometry, collision coverage and built-in MDL bindings.
4. Run existing static checks, formatting and lint; compare retained scene
   fields against the accepted furniture scene.
5. Synchronize to ur12e-collection and render bounded Isaac 6.0.1 views from
   both sides. No physics stepping or hardware connection.
6. Update this document with actual results and show the user the preview.

## Initial preview results (20-inch end width; superseded)

- PASS: the end-wall footprint is 0.508 x 0.1524 m and the extension follows
  +v at 90 degrees to the board run. The room-frame origin is
  (1.3780107, -3.1132763, 0) m; the outer -u faces are aligned.
- PASS: composed cube corners show centered 0.02 m glass with 0.03 m recess
  on each wall face, clear widths 2.3749/1.2192 m, and 0.4064/2.8064 m glass
  bottom/top. Framed intervals touch exactly; there is no intermediate white
  wall. The far solid length measures 1.25349998 m. No opaque box intersects
  either clear opening.
- PASS: 14 new static collision boxes are enabled, including both panes and
  their frames; no rigid-body motion is enabled. Thin Walled is enabled on
  the shared OmniGlass material and material bindings are correct.
- PASS: eight existing scene checks on Mac USD 26.8 and the station's Isaac USD
  libraries; Black and Pylint 10/10 for the four touched Python files.
  The first aggregate-BBox measurement overestimated a rotated window group;
  measuring its actual composed cube corners resolved the validation failure.
- PASS: 500 retained authored fields match furniture commit 3d20126. The new
  Room subtree is additive. The field-comparison utility initially mistook
  virtual connection/target paths for missing specs; their parent connection
  lists compare identically, and the corrected comparison passes.
- PASS: Isaac 6.0.1.0 on ur12e-collection rendered five 1600x1000 views, including
  the persistent observer, room overview, top view, and glass from both sides.
  Agent inspected the overview, top and outside views. Both panes are
  transparent and the room geometry is visible. Timeline remains at zero;
  no physics steps or hardware connection; source checksum remains unchanged.
- NOT RUN: user visual acceptance. New room preview remains uncommitted.
- NOT RUN: dynamics/contact/optical calibration, outside this static layout.

Evidence: artifacts/room-extension-20261002/ on both computers contains five
PNGs and report.json. The station render log is
artifacts/room-extension-20261002.log. Scene SHA-256:
e1d5aff46a7e6993ba191923190544a89f10e7c44cd3bb1a295964884661b45c.

## Material dependency inspection

PASS: the station Isaac 6.0.1 runtime contains OmniGlass.mdl and defines
thin_walled, glass_color, glass_ior and frosting_roughness inputs. Rendering
with the configured windows is PASS. Follow the official glass definition:
https://docs.omniverse.nvidia.com/materials-and-rendering/latest/templates/OmniGlass.html

## Size refinement — 2026-10-02

The user corrected the end-wall u dimension from 20 to 14 inches and shortened
the far solid wall to 0.3 m. These exact revisions are aligned; retain all pane,
frame, height, thickness and orientation values. Move the entire room frame
by +0.1524u (world delta approximately +0.052124 X, +0.143209 Y, 0 Z m), keeping
its outer face aligned with the corrected end block. Total wall length becomes
4.0465 m. Preserve tables, boards, chair, robot HOME and saved observer.

Current refinement results:

- PASS: corrected end width 0.3556 m, unchanged depth 0.1524 m, and measured
  far white wall length 0.3000000119 m. Derived room wall length is 4.0465 m.
- PASS: new anchor (1.4301346, -2.9700672, 0) m; translation from the first
  preview is (+0.05212387, +0.14320916, 0) m, magnitude exactly 0.1524 m.
- PASS: comparison of 1,000 prior authored fields identifies only the five
  intended changes: room translation, end-block position/scale and far-wall
  position/scale. Local glass panes, frames and all retained furniture are
  identical; their world placement follows the shared room translation.
- PASS: geometry validation and three existing workcell tests on Mac USD 26.8;
  Black and Pylint 10/10 for the changed room composer. Existing unchanged
  scene checks are covered by the initial preview results above.
- PASS: five 1600x1000 views rendered in Ubuntu Isaac 6.0.1.0, no logged errors.
  The overview was visually reviewed; camera edits remain session-only,
  timeline time is zero, no physics steps and no hardware connection.
- PASS: user accepted the refined preview and authorized committing and
  pushing main on 2026-10-02.

Evidence: artifacts/room-refined-20261002/ on both computers contains the five
PNGs and report.json. The station render log is
artifacts/room-refined-20261002.log. Scene SHA-256:
ed3b56f010c6747e31b6548d60db2ce77fa570cc795ed48b91ed0c85f40b13f8.
Keep the initial preview evidence above as history; these refinement results
supersede its size and placement conclusions.

## Board-width refinement — 2026-10-02

See docs/table2-furniture.md for the aligned primary plan. The board run is
now 3.4 m, requiring the entire room frame to move by +0.6u while retaining
every local room shape, glass pane, frame and material. The new room origin
is approximately (1.6353467, -2.4062516, 0) m. The extension's dimensions
and the far solid wall's 0.3 m length are unchanged. Static checks pass,
including exactly +0.6u translation and unchanged local room fields; see the primary plan for results. The user deferred station
synchronization and rendering until an Isaac station is available.

Station follow-up on 2026-10-03: the primary furniture plan records PASS for
15 relevant station USD tests and five Isaac 6.0.1.0 static previews. Both
sides of the glazed wall were captured; scene checksum and persistent
observer remain unchanged. User visual acceptance is still pending.

The user approved committing and pushing the refined layout on 2026-10-03.
User visual acceptance for this refinement is PASS.
