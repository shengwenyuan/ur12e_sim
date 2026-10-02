# M14: Visual D435 Tripod Instances

**Code style requirement: Economical code, exceptional readability, and excellent abstraction design.**

Status: accepted; the user requested commit and push on 2026-10-03. Scope follows the user's 2026-10-03 request to import tripod_d435 and
place two grounded visual instances near the calibrated D435 positions.
Exact agreement between coarse asset geometry and optical extrinsics is
explicitly unnecessary. The interior floor prerequisite is committed in ef35b22.

## Scope and simple placement

Retain only the self-contained native isaac/tripod_d435.usdc under
assets/props/tripod_d435/isaac/. No printing/Gazebo exports, source history,
reference photographs, duplicate ASCII USD or nominal camera configuration.
The source asset is metric and Z-up, about 1.041 m high, with ground-origin
feet, camera front +X, one rigid body and 40 colliders. Preserve its bytes.

Add two references under /World/CameraTripods, named camera_2 and camera_3.
Read the already-authored calibrated USD camera transforms. Rotate each visual
assembly's +X toward the camera's horizontal viewing direction. Align the
source nominal RGB optical point's XY to the calibrated camera XY, then put
its lowest geometry on Z=0. Preserve native scale and horizontal head tilt;
do not stretch legs or move any optical camera to fit the mesh. Record actual
visual/calibrated positions and their separation in layout.json.

Keep the assemblies static by overriding their placed rigid body to disabled,
retaining source colliders. Deactivate each referenced Sensors subtree so its
four nominal cameras cannot become competing sensor inputs. The existing
calibrated camera_2/camera_3 remain the only active D435 views. Reuse the shared
asset-placement and calibrated-frame helpers; one small dedicated builder is
sufficient, with no new generic attachment framework.

## Steps and acceptance

1. Freeze the accepted scene and copy the minimal USD dependency closure.
2. Add the focused tripod builder after calibrated camera authoring; append
   visual-placement metadata, preserving all existing layout/report fields.
3. M14-TR01: verify two metric, grounded references with static collision shapes,
   matching horizontal headings and no active nominal Sensors subtrees.
4. M14-TR02: retain all prior authored fields and calibration bytes; resolve
   portable dependencies and run focused existing/regression checks, Black/Pylint.
5. M14-TR03: render overview/detail and the two original calibrated D435 views
   in Isaac 6.0.1 without timeline play or device connections. Check for visual
   interference and record any approximate placement limitations.

The user authorized this approximate placement directly; no mechanical fit or
calibration-consistency gate is imposed. Render visual acceptance remains with
the user. No follow-on tripod commit or push is requested in this instruction.

## Results

- M14-TR01 PASS: imported one self-contained USDC, 2,682,090 bytes; no external
  textures or mesh layers. SHA-256 matches the original:
  `b168f85329683322045458776ee24b5f63ead8b15ec6ae04cee0fb8a6d5c4f92`.
  Its project path inherits assets/** Git LFS. Native assembly height is about
  1.041 m; both instances retain native scale, lowest bound Z=0, 40 enabled
  colliders each, disabled placed rigid bodies and inactive Sensors subtrees.
- M14-TR01 PASS: camera_2 tripod ground origin is approximately
  (-0.2219705, -0.9073550, 0) m, yaw 42.0876 degrees; camera_3 origin is
  (-0.1064367, 0.8943689, 0) m, yaw -59.1623 degrees. Visual RGB centers align
  in XY with the original optical centers but remain at native height 1.0285 m,
  about 30.779 / 30.190 mm below the calibrated centers. This approximation
  is permitted by the user's explicit scope; roll/pitch are not imposed.
- M14-TR02 PASS: every one of 2,650 prior authored scene fields is unchanged.
  Only /World/CameraTripods is added; old layout/report content is exact with
  one new layout entry. No local Documents dependencies enter the scene.
  The calibration snapshot remains unchanged, SHA-256:
  `4f8116c15732f6baca383e4fafbed1c8be8f2ad02df321274c7c2dd4890c39c7`.
- M14-TR02 PASS: 20 local tests (wall composition, box scene including a new
  independent grounded/static/heading check, calibrated cameras, scene and
  board cutting), plus 13 station tests (wall composition, box and cameras).
  Black formats the three touched Python files; Pylint scores 10.00/10.
  The initial single-function builder exceeded the local-variable limit;
  asset measurement and instance placement were split into short focused
  functions. Subsequent lint and behavior tests pass without suppressing it.
- M14-TR03 PASS: Isaac Sim 6.0.1.0 / RTX 2000 Ada rendered overview, tripod
  detail and both original 640 x 480 calibrated D435 views. Inspected images
  show two grounded black assemblies beside Table1, aimed toward the task.
  Neither calibrated view has new tripod obstruction of the box/cube.
  No camera pose or lens parameter was adjusted to accommodate the mesh.
  Timeline=0, physics_steps=0, hardware_control=false, scene_saved=false.
  Rendered scene SHA-256:
  `cf34b354fc7df23e3e611ba72375fe6669b310e2aa94dd12863fab5b5524317b`.
- User delivery acceptance: requested commit and push after the rendered review.
  Mechanical fit, exact optical coincidence,
  dynamic tripod settling and real hardware tests: NOT RUN, outside scope.
  The floor commit ef35b22 is complete; the user authorized delivery of the
  tested tripod asset, placements and documentation to origin/main.

Evidence: ignored artifacts/camera-tripods-20261003/ stores the before-scene
snapshot, asset/retention records, checks and render logs/reports/captures.
The isolated station workspace preserves unrelated station checkout edits.
Reproduce with scripts/compose_box_scene.py --collection-root ../ur12e_collection
and the five local unittest patterns listed above. Render review images:
render/views/01_overview.png, 02_d435_left.png, 03_d435_right.png and
04_tripods_detail.png. No additional calibration or hardware inputs required.
