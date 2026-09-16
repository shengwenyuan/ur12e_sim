# Minimal Isaac Asset Delivery

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

## Aligned scope — 2026-09-16

Keep the dependency closure of every existing Isaac scene, the UR/Hand-E URDFs
used by forward kinematics, the active 4K photographic texture and coverage mask,
scene configuration, asset provenance and required licenses. Preserve the latest
finite-distance background implementation and all scene/robot geometry.
Remove alternate render formats, source meshes already embedded in USD, Blender,
Gazebo and print exports, unused HDRIs, duplicate 8K/PNG panoramas and previews.
Remove the unused MuJoCo USD variants and their payloads, retaining PhysX, generic
physics and no-physics variants. Original assets under Documents/mesh are untouched.

Reimporting robot assets is an optional development operation. Its scripts must
accept an external --source-root containing the pinned upstream packages, instead
of requiring their raw meshes in this delivery. Keep source URLs and revisions
in assets/manifest.json. Existing runtime paths remain unchanged.

The user explicitly approved rebuilding main as a single clean initial commit
and discarding old history without backup. The configured remote currently has
no advertised branch heads. Preserve its URL; do not push. Remove old local
branches, unreachable Git history and obsolete LFS objects after validation.
This operation applies to this local standalone repository, not collector history
or the Ubuntu checkout. The user will publish the new main.

## Checks

Resolve all scene USD references in a relocated minimal checkout, verify retained
file hashes, run existing static scene/projection tests, lint modified scripts,
and validate the clean root's LFS payload and object set. Record results below.

## Acceptance — 2026-09-16

PASS: five saved USD entrypoints resolve wholly inside an isolated relocated
directory. The existing five scene and seven finite-room tests pass there. The
Versteel composer rebuilds successfully using external collection HOME; the CPU
projection preview generates under ignored artifacts/. All retained source and
generated hashes in assets/manifest.json match. Black and Pylint pass for the
three modified tooling scripts; both reimport CLIs accept --source-root.

The delivery retains 48 asset/scene files totaling 23,780,307 bytes (23.78 MB),
down from approximately 348.28 MB of tracked assets/scenes. 210 files were
removed and one compact asset README added: about 93.2% less payload. Licenses
and source revisions remain; active USD geometry, texture pixels and camera
configuration are unchanged. Only unused MuJoCo variant declarations were
removed from the robot USD wrappers.

NOT RUN: a new Ubuntu RTX render, physical settling, robot reimport from external
packages or hardware actions. No visual mesh or physical material was edited;
existing finite-room rendering and unresolved settling status remain as recorded
in the workcell plan. This is a dependency/packaging acceptance.

Git delivery: rebuild main as one root commit with no parent. Historical commit
IDs in older acceptance notes describe prior local runs and will not resolve in
the new history. Remove the old development branch and unreachable Git/LFS
objects; retain the configured origin and leave publication to the user.
The Ubuntu checkout has not been reset or synchronized by this local cleanup.
