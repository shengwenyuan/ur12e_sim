# Versteel Workcell Layout Reference

All coordinates are world coordinates in meters. This reference applies to
scenes/versteel_box_pick_place/scene.usda, not the older tabletop scenes.

The origin (0, 0, 0) is on the floor directly below the robot mounting base.
The robot mounting plane is (0, 0, 0.85). +X follows table length from the base
toward the carton; +Y points left while looking along +X; +Z points upward.
Robot installation yaw -180 degrees does not change this world coordinate frame.

The tabletop measures 1.8288 x 0.7620 m, with its top at Z=0.8500 m. Its center
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
