# M14: Exterior Red Wall beside the Third Turning Glass Panel

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted for static layout delivery on 2026-10-03; the user requested commit and push after reviewing the previews.

## Scope and coordinate interpretation

Reference the third panel of the five-panel turning section, not the third
straight panel: /World/Furniture/ChairSideGlass/Unit6. Its heading is 54 degrees
relative to the straight run, or 124 degrees world yaw. Keep the glass layout
and all existing geometry fixed.

Add one grounded static box: 3 m long, 3 m high, 0.10 m thick. Use a shared
OmniPBR red material, roughness 0.9, metallic 0, with PreviewSurface fallback.
No texture or mesh asset is required; the scene stays under Git LFS.

Let t follow the referenced unit from its starting edge to its ending edge.
The room interior is on the left of this glass path, so the outward normal
is n=(t.y,-t.x,0). Looking outward with +Z up, viewer-right is -t and
viewer-left is +t. Thus the glass's right clear edge is its starting edge
plus the 5 mm adhesive strip; the red wall's left end is its +t end.

Interpret the requested 3 m distance as clear surface-to-surface separation.
The center-plane offset is 3 + 0.02/2 + 0.10/2 = 3.06 m along n. Align the
wall's +t endpoint with the glass's starting clear edge along n; extend the
wall 3 m toward -t. Preserve the floor (16 x 16 m), lights, observer, tables,
robot HOME, props, chair, existing walls and calibrated cameras.

## Implementation and acceptance

1. Add a focused wall helper using the actual composed glass-unit transform,
   existing PBR material and static collision box interfaces.
2. Persist reference-panel, outward direction, clearance, wall pose and
   viewer-defined endpoint semantics in layout.json.
3. Measure actual box corners in the glass frame: parallel direction,
   3 m face clearance, aligned clear-edge endpoint, 3 x 0.10 x 3 m dimensions,
   grounded support, material and enabled static collider.
4. Compare all prior authored fields; run relevant workcell/camera tests,
   formatting and lint. No tests of unchanged base-scene behavior are needed.
5. Synchronize an isolated workspace and render a complete top view plus
   interior-to-exterior view in Isaac 6.0.1. No timeline play, physics steps
   or hardware connection. Record results and present images for review.

## Actual results (2026-10-03)

- Actual Unit6 heading: 124 degrees world yaw. Wall center is
  (6.813454705, 5.728402342, 1.5) m, with dimensions 3 x 0.10 x 3 m.
  It is grounded, parallel to Unit6, and has one enabled static collider.
- Independently measured clear face distance is 3 m. In the Unit6 frame,
  the wall's maximum X matches the glass's minimum X: viewer-left wall end
  aligns with viewer-right clear glass edge. The center-plane offset is
  3.06 m; the 5 mm adhesive strip is excluded from the clear-edge alignment.
- All 2,463 previously authored fields are unchanged. The red wall and
  its material are additive; floor, retained objects, HOME, lighting,
  observer and calibrated cameras are preserved.
- Mac USD and Ubuntu USD runs each passed eight relevant tests: three
  workcell tests and five calibrated-camera tests. The workcell validation
  includes the wall's dimensions, pose, clearance, endpoint, collision and
  material checks. Black and Pylint passed for red_wall.py and
  compose_box_scene.py; Pylint scored 10/10. This is scoped scene validation,
  not a claim about the unrelated inference or collection test suites.
- Rendered on ur12e-flexlab with Isaac Sim 6.0.1.0 / Python 3.12.3,
  RTX 2000 Ada and driver 595.84. The isolated test workspace is
  ~/ur12e-sim/artifacts/red-wall-20261003/workspace; the main remote checkout
  was not overwritten. Native OmniPBR and OmniGlass materials resolved.
- Overview, complete top view and interior-to-exterior views succeeded.
  The initial close interior framing cropped the wall vertically; a second
  interior capture moved only the temporary session camera 4 m inside the
  reference glass and shows the complete wall. Source and saved observer
  were unchanged. Timeline remained 0, physics steps were 0 and no hardware
  connection or control command was made. Both bounded render jobs exited.
- Tested scene SHA-256:
  92179315de2e0a9984b5396cdaaca9359abe59aa6c9d8e1258a2531d23666413.
  Logs, reports and images are retained locally and remotely under
  artifacts/red-wall-20261003/. Prefer views/01_overview.png,
  views/02_top_view.png and views-inside/03_inside_out.png for review.
- Static/render acceptance: PASS. Layout delivery: approved by the user's
  commit-and-push request on 2026-10-03.
  Dynamic contact behavior: not run for this layout-only change.
  The previously stopped model service remains off. Delivery includes the adjoining eight-panel glass run and the red wall.
