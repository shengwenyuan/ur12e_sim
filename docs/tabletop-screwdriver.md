# Tabletop Screwdriver Scene

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: aligned by the user's explicit request on 2026-09-12 to import the
provided Isaac asset, deploy it to the PC and place it on the table in a new USD
scene. This adds an object scene; it does not change collector control behavior.

Copy the complete supplied `husky_screwdriver/isaac` directory into
`assets/props/husky_screwdriver/`, retaining original files and hashes. The model
is a photo-derived estimate of approximately 100 mm, not a measured manufacturer
SKU; preserve its embedded dimension and physical-property qualifications.

Create `scenes/tabletop_screwdriver/scene.usda` as a relative sublayer composition
of `tabletop_home/scene.usda`, with the source USDC referenced beneath
`/World/Props/HuskyScrewdriver`. Place it horizontally at XY (1.42, 0.70) m,
yaw 25 degrees, with the lowest visual/collision bound 1 mm above the tabletop.
Keep native scale, materials, rigid body and collision properties. Inherit the
opposite-side default camera, robot HOME and tool mounting from the base scene.

Verify complete relative dependency resolution, enabled object colliders,
containment within the tabletop, support clearance, robot/tool presence and
saved default camera. Synchronize only the new asset, scene, script and docs to
`~/ur12e-sim` on `ssh ur12e-collection`; preserve concurrent native follower work.
No hardware commands or physics playback are part of this change. Contact
response remains NOT RUN. Record actual results below after validation.

## Acceptance — 2026-09-12

**PASS:** source USDA, USDC and standalone drop-test scene copied intact with
SHA-256 provenance in the asset's `manifest.json`. New scene generated and
reopened using the existing Ubuntu Isaac 6.0.1 OpenUSD runtime. All external
references resolve and are relative. The source rigid body and 15 enabled
colliders are retained. Measured asset bounds are approximately
100 x 13.4 x 13.4 mm, preserving the source's estimated size.

Placement is (1.42, 0.70, 1.2077000002) m with yaw 25 degrees. Bounds remain
inside the tabletop in XY, with minimum Z exactly 1 mm above its top within
1e-6 m. UR12e, Hand-E and the opposite-side default camera remain present.
The local and Ubuntu base scenes have identical SHA-256 hashes. The new scene
and placement report are synchronized to the local project. Black and Pylint
pass for the composer (10.00/10).

**NOT RUN:** new-scene GUI rendering and dynamic contact/settling. An existing
native follower session was running and was preserved without reloading or
restarting it. No hardware signals or physics steps were sent by this task.

Scene: `scenes/tabletop_screwdriver/scene.usda`.
Rebuild from the project parent directory with:
`~/venv/isaacsim-6.0.1/bin/python ur12e-sim/scripts/compose_screwdriver.py`.
