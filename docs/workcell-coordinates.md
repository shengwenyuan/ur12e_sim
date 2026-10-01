# Versteel Workcell Layout Reference

All coordinates are world coordinates in meters. This reference applies to
scenes/versteel_box_pick_place/scene.usda, not the older tabletop scenes.

The origin (0, 0, 0) is on the floor directly below the robot mounting base.
The robot mounting plane is (0, 0, 0.85). +X follows table length from the base
toward the carton; +Y points left while looking along +X; +Z points upward.
Robot installation yaw -180 degrees does not change this world coordinate frame.

Table1 is the robot workbench at /World/Table. Its tabletop measures
1.8288 x 0.7620 m, with its top at Z=0.8500 m. Its center
is (0.2441, 0, 0.8500). Corners refer to the upper tabletop surface, not its feet.

| Corner | Description when looking along +X | X | Y | Z |
| --- | --- | ---: | ---: | ---: |
| A | Base-end right | -0.6703 | -0.3810 | 0.8500 |
| B | Carton-end right | 1.1585 | -0.3810 | 0.8500 |
| C | Carton-end left | 1.1585 | 0.3810 | 0.8500 |
| D | Base-end left | -0.6703 | 0.3810 | 0.8500 |

A-B-C-D is counterclockwise viewed from above. AB is the right long edge (-Y),
CD the left long edge (+Y), AD the base-end short edge (-X), and BC the carton-end
short edge (+X). These names are reference labels, not new USD marker geometry.
They were verified against the saved tabletop's world-space USD bounding box,
rounding floating-point geometry bounds to four decimal places.

For future placement, use an edge/corner name, an inward offset, a world XYZ
position, and the object's heading. Positive yaw rotates +X toward +Y about +Z.


## Table2

The second table is /World/Table2 and reuses the identical static Versteel asset.
Its top is also at Z=0.85 m; its local A/B/C/D labels rotate with the table.
The corrected distance is Table1 B to Table2 D, not Table2 C: 0.5461 m.
D2 lies on the +X extension of Table1 AB as inferred from the qualitative sketch
and accepted by the user in the rendered preview. This is not a surveyed pose.

Table2 yaw is +70 degrees: its A-to-B long edge points toward +X/+Y, while its
A-to-D short edge points toward -X/+Y. The latter makes 160 degrees with Table1
A-to-B, equivalent to a 20-degree acute angle between the straight lines.

| Table2 corner | X | Y | Z |
| --- | ---: | ---: | ---: |
| A | 2.4206 | -0.6416 | 0.8500 |
| B | 3.0461 | 1.0769 | 0.8500 |
| C | 2.3301 | 1.3375 | 0.8500 |
| D | 1.7046 | -0.3810 | 0.8500 |

The Table1 coordinates and world axes above remain unchanged.
