# M14: Second Versteel Table

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted. Static checks, simulator rendering and user visual alignment
pass. The user authorized committing this table layout on 2026-10-02.

## Scope and placement — 2026-10-02

The user names the existing robot workbench Table1 and requests Table2 using
exactly the same Versteel mesh, 0.85 m tabletop height and static collision model.
The corrected constraint is Table1 B to Table2 D = 1 ft 9.5 in = 0.5461 m.
Table1 AB and Table2 AD make an acute straight-line angle of 20 degrees (the
oriented A-to-B/A-to-D vectors make 160 degrees for the selected placement).
Use the qualitative sketch's long-edge A-to-B progression toward +X/+Y, hence
Table2 yaw +70 degrees. Its corner labels preserve A-B-C-D counterclockwise.
The sketch's numbers are not measured coordinates; opposite short edges must
remain parallel and have identical A-to-D and B-to-C directions.

For this preview, infer Table2 D on Table1 AB's +X extension from the sketch:
D2=(1.7046, -0.3810, 0.85) m. This extension alignment is an interpretation of the
qualitative placement, not an additional surveyed fact. No arbitrary 45-degree
gap bearing is introduced. The user accepted this extension alignment in the rendered preview.

Preserve /World/Table as the stable Table1 prim and reference the same asset
at /World/Table2. Share table placement code; do not duplicate mesh payloads.
Keep Table1, robot/HOME, gripper, props, floor, lighting and saved observer
unchanged. The layout report records Table2's placement and measured corners.

## Implementation and acceptance

1. Add the referenced second table and retain static rigid-body/collision flags.
2. Check actual composed tabletop corners, B1-D2 distance, straight-line angle,
   identical dimensions/support height, collider coverage and table separation.
3. Run existing static checks and lint; compare every retained scene field with
   the accepted clean workcell.
4. Synchronize the uncommitted preview and render an overview and top view with
   Isaac 6.0.1 on ur12e-collection, using session-only observer adjustments.
5. Update this plan and coordinate reference with actual results. Present views
   for user alignment before any commit. No hardware connections or motion.

## Acceptance results — 2026-10-02

- PASS: composed Table1 B to Table2 D distance 0.5461000134 m; oriented vector
  angle 160 degrees / acute line angle 20 degrees. D2 remains on the +X extension
  of AB. Recorded corner positions come from the actual tabletop USD bounds.
- PASS: identical 1.8288 x 0.762 m tabletop, 0.85 m top, grounded feet, static
  rigid-body override and all 40 collision shapes enabled. Whole-table world
  bounds are separated from Table1. No asset payload changes or mesh duplication.
- PASS: every prior authored stage field is identical to the accepted single-table
  clean scene; the new Table2 prim is additive. HOME, props, floor, lighting and
  saved camera remain unchanged.
- PASS: eight existing scene/workcell checks on Mac USD 26.8 and station Isaac
  6.0.1 USD libraries, Black, and Pylint 10/10. The station's initial isolated
  static invocation lacked libpython3.12.so.1.0; adding the managed Python lib
  directory to LD_LIBRARY_PATH resolved setup and all eight checks passed.
- PASS: Isaac 6.0.1 opens and renders four 1600x1000 views on li1013-MS-7E11 /
  RTX 4070 Ti SUPER / NVIDIA 595.91.07. Agent reviewed overview and top view;
  both tables are visible, separated, and match the chosen skew. Observer changes
  remain in the USD session layer; source checksum is unchanged by rendering.
  Timeline time is 0 and no hardware connection is made.
- NOT RUN: settling or motion; these are not required for this static layout.
  User visual alignment PASS: the rendered placement and extension interpretation
  were accepted on 2026-10-02. Commit is authorized; do not push automatically.

Station evidence: artifacts/table2-20261002/ contains report.json and four PNGs;
artifacts/table2-20261002.log records the completed render. The same images/report
are retained under local ignored artifacts/table2-20261002/. Scene SHA-256:
172dd1178174c1abb435e0a518f89bf4194171b8449555cfff3e4d7ebcdb0d7d.
