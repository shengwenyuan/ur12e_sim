# M14: Calibrated 480p Three-Camera Preview

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: static preview accepted for delivery, 2026-10-02. Physical mount
confirmation remains pending. The user requested selecting
appropriate September 30 intrinsics, configuring this workcell and returning
three screenshots for human acceptance. The agent selects the canonical
480p camera matrices with the better-supported 720p distortion for D435IF;
pure-480p solves remain available as a comparison. All RGB outputs are 640x480.

## Scope and interfaces

Add portable RGB camera prims to the accepted Versteel box workcell, preserving
all scene geometry, HOME, mounting yaw, lighting and the saved observer.
Store a small calibration snapshot with source revision, paths, hashes and
original optical model. Camera names and serials are authoritative; +Y/-Y
placement labels must not silently become a policy's unconfirmed input order.
This preview does not change the fixture-only inference adapter or its gates.
No hardware connection, robot control, depth simulation or physics playback.

Use camera_1 D405 (260522273667), camera_2 D435IF (327122073926), camera_3
D435IF (327122075735). Read canonical intrinsics/result.yaml and each
handeye/final_result_all_30.yaml. Intrinsics are September 30 Beijing time;
extrinsics are September 27, not a new 480p hand-eye solve. Record pure-480p
D435IF alternatives without presenting their distortion as equally validated.

Extrinsic matrices use column vectors and meters, optical +X right, +Y down,
+Z forward. Convert once to USD +X right, +Y up, -Z forward. Fixed cameras use
the controller base frame (world orientation identity, origin Z=0.85 m).
D405 uses actual_tcp from calibration, provisionally interpreted as zero-TCP
tool0, not the differently oriented URDF flange. TCP offset and unchanged
physical camera mounts remain unconfirmed. Preserve these limitations in the
snapshot and report rather than claiming real-world optical acceptance.

Use native OpenCV lens schema for complete fx/fy/cx/cy and distortion.
D405 reports inverse Brown-Conrady; do not silently reuse these as forward
OpenCV coefficients. A bounded numerical conversion fits the actual librealsense 2.58.4 projection
implementation to the native OpenCV renderer, retaining source coefficients
and checking 307,200 rays over the 480p normalized domain plus a 5% margin.
The SDK model name must not be interpreted as a reason to invert coefficient
signs: its projection implementation applies radial terms before tangential
terms. This is a small difference from OpenCV, not an opposite radial model.
If it cannot meet 0.1 px, stop this optical path and report the limitation.

The user explicitly accepts the carton being outside D405's HOME field of
view; the two third views supply task context. Do not alter camera poses,
HOME or object placement to center the carton in the wrist image.

## Steps and acceptance

1. Freeze source calibration and selection rationale; create the camera layer
   and reusable camera-authoring helper.
2. Check frame composition, optical axis conversion, full intrinsic values,
   inverse-model approximation, wrist attachment and retained-scene identity.
3. Synchronize only approved files to ur12e-collection. Render three 640x480
   PNGs through Isaac Sim 6.0.1 from the unchanged static HOME scene.
4. Save a report with resolution, calibration provenance, scene hash, stopped
   timeline and untouched saved layers. Present screenshots for user review.
5. Record actual checks and the user's static-preview acceptance here.

M14 camera-preview cases (supplementary to existing A01/A02):
- CP01: source identity, serials, K/D selection, optical model and timestamps.
- CP02: correct controller-base/tool0 attachment and optical-to-USD axes;
  wrist follows a changed simulated tool pose without moving fixed cameras.
- CP03: all existing retained workcell scene tests, formatting and lint.
- CP04: three real Isaac RGB captures at 640x480, unchanged world/timeline.
- CP05: user visual acceptance; no hardware or policy acceptance inferred.

## Results

- CP01 PASS: frozen source revision 7cd6dea and serial-specific canonical
  parameters. Pure-480p alternatives and the blended provenance are retained.
  D405 matches the factory SDK projection within 0.003975 px maximum and
  0.001228 px RMS on a dense 640x480 ray grid with 5% margin. An initial
  generic inverse-polynomial interpretation was discarded after checking
  the actual SDK implementation; only the corrected coefficients are saved.
- CP02 PASS: controller base is world identity at Z=0.85 m; optical +Z
  matches USD -Z, optical down matches USD -Y. A 23-degree tool0 rotation
  carries D405 while leaving both fixed views unchanged. The importer has
  two base-named prims; select the canonical direct child of base_link.
- CP03 PASS: five new camera tests, three retained workcell tests and five
  original static scene tests on Mac Python 3.12.13/OpenUSD 26.8. Comparison
  against accepted pre-camera scene ed3b56f checks 1,000 original authored
  fields with no changes. Only three camera subtrees were added. Black
  checks pass; Pylint 10/10. Pylint ignores only the pxr compiled modules
  whose dynamic members it cannot infer, rather than disabling no-member.
- CP04 PASS: final code rendered three 640x480 RGB PNGs through Isaac Sim
  6.0.1.0 on ur12e-flexlab, RTX 2000 Ada 16 GiB, using the existing
  ~/venv/isaacsim-6.0.1 runtime. Timeline time is zero, physics steps zero,
  and no device/control client is imported. Agent inspected all three views.
  D405 sees the cube; both third views see the cube and carton.
- CP05 PASS (static preview): after the three-view and real/sim comparison,
  the user authorized committing and pushing this version on 2026-10-02.
  TCP offset and unchanged physical mounts still require confirmation; this
  acceptance does not establish real-world optical agreement or policy quality.

The first render attempt failed the in-memory root-layer invariant: Kit added
only product targets beneath /Render despite session-only product creation.
The final entry compares every non-render scene field, restores transient
render bookkeeping, and verifies both root-layer content and saved file hash.
Two final captures passed. This is not a relaxed scene-geometry check.

The SSH alias was remapped by the user to the earlier ur12e-flexlab station.
Its ~/ur12e-sim checkout has unrelated edits, preserved in place. A dependency
closure (34 files, about 25 MB) was deployed to the isolated preview workspace:
~/ur12e-sim/artifacts/calibrated-camera-20261002/workspace/. This is not a
replacement of the station's main checkout. Local scene/config are updated.

Evidence: local artifacts/calibrated-camera-20261002/ and remote
~/ur12e-sim/artifacts/calibrated-camera-20261002/review/ contain three PNGs
and report.json. Scene SHA-256 is
c9cc7c93c2ec9ae2d5b54f3f2d00f8be48380888177ccb61c4d7821d7e15734f;
config SHA-256 is
4f8116c15732f6baca383e4fafbed1c8be8f2ad02df321274c7c2dd4890c39c7.

## Initial real/sim comparison and future refinement

The user authorized original MCAP images when no physical LeRobot export was
found on the remapped station. Uniformly selected one of 33 retained physical
UR episodes: session-1789413179504921013/episode-0000. Its first accepted frame
group (#0) has wrist timestamp 1789413223069741000 ns, 2026-09-15 03:13:43.069741
Beijing time. The corresponding D435IF frames precede it by 14.1695/12.73 ms.
Match serials, not world-side labels: camera_1=wrist/260522273667,
camera_2=recorded third_left/327122073926, and
camera_3=recorded third_right/327122075735. The first recorded follower state
is within 0.001591 degrees of configured HOME on every joint.

The 2128x1280 comparison places three real views above three simulation views.
Each 640x480 panel preserves original pixels without scaling, cropping,
mirroring or color adjustment. Evidence and provenance are retained locally
and on the station under artifacts/real-sim-initial-comparison-20261002/;
these disposable images and raw episode data are excluded from Git.

The user may refine camera extrinsic viewpoints later. Preserve the frozen
source calibration and provenance; record any visual placement correction as
an explicit scene override, distinct from a newly measured calibration. Render
another serial-matched comparison when refinements are requested. No viewpoint
correction is applied in this commit.

## Reproduction

The shipped scene and camera snapshot need no calibration repository at runtime.
Render from any complete project deployment using the existing station venv:

```bash
OMNI_KIT_ACCEPT_EULA=YES ~/venv/isaacsim-6.0.1/bin/python \
  scripts/calibrated_camera_preview.py --output artifacts/camera-review
```

Optional offline import/authoring uses Python 3.12, usd-core 26.8, NumPy 2.3.3,
SciPy 1.16.2 and PyYAML 6.0.3 (requirements-camera-authoring.txt). These are
authoring dependencies, not changes to the station Isaac installation:

```bash
python scripts/import_camera_calibration.py \
  --source /path/to/camera_calibration_ur12e \
  --output config/cameras/rig_480p.json
python scripts/calibrated_cameras.py
python -m unittest discover -s tests -p test_calibrated_cameras.py -v
```

The fixture-only inference camera adapter is still separate; no calibrated
policy input contract, depth registration or 30 Hz performance gate is claimed.

## Renderer references

https://docs.omniverse.nvidia.com/materials-and-rendering/latest/cameras.html
https://docs.isaacsim.omniverse.nvidia.com/6.0.1/py/source/deprecated/isaacsim.sensors.camera/docs/index.html
https://dev.realsenseai.com/docs/projection-in-realsense-sdk-2-0/
