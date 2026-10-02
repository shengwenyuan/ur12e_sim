# M14: Chair-Side Glass Partition

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted for static layout delivery on 2026-10-03. The user clarified direction, centered wall
thickness, clear panel width and three consecutive units on 2026-10-03.
The preceding width refinement is delivered separately in 66321a9.

## Scope and placement

Place the straight run at the outward-facing surface midpoint of the BC
short wall circled in the user's screenshot. In Table2 B-origin coordinates
this attachment is u=0.14605 m (outer wall face), v=0.642/2=0.321 m, z=0.
Keep the first three units parallel to AB and the wood boards, pointing +u.
The original long-wall-centered preview is superseded by this placement.
Preserve the chair and all existing wall geometry.

Use eight consecutive static units: three straight, then five turning units.
Each has 32 inches = 0.8128 m clear glass width, plus two separate 0.005 m
gray edge strips. Unit pitch is 0.8228 m. The straight run is 2.4684 m;
the complete eight-unit centerline path is 6.5824 m.
The five additional headings relative to the straight run are +18, +36, +54,
+72 and +90 degrees: one 18-degree turn at each connection, toward the table
side (+v). The user's 90-degree turn is implemented as a five-facet bend,
not a curved mesh. Each unit starts at the preceding unit's centerline end.
Retain separate gray edge strips and metallic skirting segments at the angled
joints; static box corner surfaces can overlap locally at the hinge.

Overall height is 3 m: the lowest 0.10 m is a silver-white metallic skirting
box of 0.03 m thickness; glass occupies z=[0.10,3.00] m, height 2.90 m and
thickness 0.02 m. Center glass and gray strips across the skirting thickness,
leaving 0.005 m recess on each face. Edge strips are 0.005 x 0.02 x 2.90 m.
This retains the overall-height interpretation from the aligned draft.

Reuse Thin Walled OmniGlass from the existing room. Silver-white skirting uses
OmniPBR with metallic=1, roughness=0.25; gray unpainted adhesive proxy uses
metallic=0, roughness=0.95. Both have portable PreviewSurface fallbacks. These
are visual approximations, not measured material properties. All geometry has
simple enabled static box collision; no source meshes or textures are needed.

## Implementation and acceptance

1. Share focused PBR material authoring and existing static-box/glass helpers.
2. Add /World/Furniture/ChairSideGlass with eight repeated units, per-unit heading transforms and reproducible
   layout metadata. Scene payloads inherit Git LFS.
3. Validate metric dimensions, exact wall-end attachment and centerline,
   adjoining intervals, centered glass, 5 mm strips, materials, static
   collisions and measured separation from the unchanged chair.
4. Compare all prior authored scene fields, including tables, robot HOME,
   props, chair, old walls/glass, observer, lights and three calibrated cameras.
   Run relevant USD checks, formatting and lint.
5. Synchronize an isolated dependency closure; render stopped-timeline overview,
   top and glass detail views in station Isaac 6.0.1. No robot connection or
   physics steps. Update this plan and show the previews for user acceptance.

## Results — 2026-10-03

- PASS: three 0.8128 m clear panes, each with two 0.005 m edge strips,
  0.8228 m unit pitch and 2.4684 m total length. Each unit is 3 m high,
  including a 0.10 m skirting box; panes/strips are 2.90 m high and 0.02 m
  thick, centered in 0.03 m skirting (0.005 m recess on either face).
- PASS: the run attaches at the existing long wall's B endpoint, parallel to
  Table2 AB and the boards, along the existing wall's thickness centerline.
  No chair relocation; measured normal separation from chair geometry is
  0.88805294 m. Existing short and long walls remain unchanged.
- PASS: three metallic silver-white skirting boxes, six rough gray strips and
  three Thin Walled panes, with 12 enabled static collision boxes. Material
  bindings, metallic/roughness values and contiguous unit spans pass.
- PASS: all 1,261 prior authored fields match committed revision 66321a9.
  The partition subtree is additive; tables, robot HOME, props, chair, old
  walls/glass, three calibrated cameras, lights and observer are identical.
- PASS: the same 15 relevant tests (test_box_scene.py,
  test_calibrated_cameras.py, test_scene.py, test_cut_wood_board.py) run on Mac
  Python 3.12.13 / USD 26.8 and on the station's bundled USD libraries.
  Existing workcell checks include the new partition geometry validator.
  Black and Pylint 10/10 for all three changed/new Python scripts.
- The first static aggregate-BBox check overestimated rotated unit bounds.
  Unioning individual boundable shapes in the partition frame corrected the
  measurement; exact metric dimensions now pass.
- PASS: 61-file closure, 25,251,378 bytes, synchronized to the isolated
  ~/ur12e-sim/artifacts/chair-side-glass-20261003/workspace/. Existing unrelated
  station checkout edits are untouched. Six 1600x1000 RGB views rendered in
  Isaac 6.0.1.0 / Python 3.12.3 on ur12e-flexlab, RTX 2000 Ada 16 GiB, NVIDIA
  595.84. The overview was inspected: three adjoining panes, vertical glue
  seams and silver-white skirting are visible, clear of the chair.
- PASS: saved scene checksum unchanged by rendering; timeline is zero,
  physics steps are zero and no hardware control occurs. Temporary observers
  stay in the session layer. Model service remains off as requested earlier;
  the bounded renderer exited and final GPU memory usage is 17 MiB.
- NOT RUN: user visual acceptance and dynamic/contact testing. The latter is
  outside this static layout scope. The new partition is not yet committed.

Evidence: ignored artifacts/chair-side-glass-20261003/ on both hosts contains
static-check.log, render.log and views/*.png plus views/report.json. Scene
SHA-256: c0900bcc29e4522d0c16501c9c726c434194225171148656be6141a5e410601b.

Reproduce geometry with scripts/compose_box_scene.py --collection-root PATH;
run the four unittest discovery patterns above. Rendering uses the existing
station venv and the isolated test workspace, without starting any collector
or robot driver.


## Placement and five-panel bend refinement — 2026-10-03

The user circled the attachment wall face and requested five connected panels
beyond the third, each turning 18 degrees for 90 degrees total. Implement the
above short-wall-face midpoint attachment; preserve three straight units and
add five identical units with local heading transforms. The turn toward +v is
the stated preview assumption; user visual direction acceptance is pending.
Validate wall-face midpoint, every shared centerline endpoint, total heading,
per-unit geometry/materials, static collisions and chair clearance. Compare
all authored fields outside ChairSideGlass, run the relevant tests and render
an overview plus top view that includes the entire eight-unit run.

The new endpoint reaches world Y=6.7268 m, beyond the old 12 x 12 m
floor. Expand only the floor footprint to 16 x 16 m, retaining its center,
height, thickness and collision configuration. Keep all other non-partition
authored fields unchanged.

Refinement results:

- PASS: attachment is the BC short-wall outer face midpoint, u=0.14605,
  v=0.321 m. The straight run remains parallel to AB; old walls and chair
  remain fixed. The minimum measured chair/partition separation is 0.47603 m.
- PASS: three straight units and five headings +18,+36,+54,+72,+90 degrees.
  Every unit's start matches the preceding centerline endpoint within 1e-6 m;
  the last direction is exactly +v (90 degrees from the straight run).
  The full path is 6.5824 m; its world endpoint is approximately
  (1.5589481,6.7267958,0) m. All eight units retain the prior pane, glue,
  skirting and material dimensions, with 32 enabled static collision boxes.
- PASS: 1,261 retained authored fields outside ChairSideGlass were compared;
  only /World/Floor.xformOp:scale changes, from 12x12 to 16x16 m footprint.
  Robot HOME, both tables, objects, chair, old walls, lights, saved observer
  and three calibrated cameras remain unchanged.
- PASS: 15 relevant USD tests on Mac and the station; Black and Pylint 10/10
  for chair_side_glass.py, workcell_furniture.py and compose_box_scene.py.
- PASS: isolated station workspace synchronized at
  ~/ur12e-sim/artifacts/curved-glass-20261003/workspace/. Four 1600x1000 views
  rendered in Isaac 6.0.1.0 on ur12e-flexlab / RTX 2000 Ada 16 GiB. Overview
  and attachment views were inspected. The first top framing cropped the
  outermost pane; a wider top view from Z=28 m was rendered and inspected,
  showing the complete five-facet bend. Persistent camera settings are fixed.
- PASS: both render reports record timeline=0, physics_steps=0,
  hardware_control=false and scene_saved=false; scene checksum is unchanged.
  The renderer exited, model server remains off and GPU usage returned to
  17 MiB. No physical robot commands or hardware connections occurred.
- NOT RUN: user acceptance of the attachment and turn direction, and dynamic
  contact tests. The latter are outside this static preview scope. Changes
  remain uncommitted pending the visual layout review.

Evidence: artifacts/curved-glass-20261003/{static-check.log,render.log,views/}
plus views-top/02_top_view.png and views-top/report.json on both hosts.
The saved scene SHA-256 is
c258b53fcfecbf4d1d00101015e0968a7701edcde1dc3ca19c0fccdf2414caa3.
Earlier three-panel results remain historical evidence only.

## Delivery alignment — 2026-10-03

Following the combined glass and red-wall previews, the user requested commit
and push of the current scene. This approves the static layout for delivery;
earlier pending/uncommitted statements describe their historical review
stages. Dynamic contact testing remains outside this layout scope.
