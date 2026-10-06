# Axis refactor: everything back to the standard (REP-103)

2 Oct 2026. The operator asked for it, after the 1 Oct hardware session and
the first successful 0.6 m goal. It is the audit (every place the current
convention shows up) and the order of work, so each stage can be checked
before the next one starts.

**Status, 5 Oct 2026: stage 1 is done (offline edits, nothing deployed).**
The code, the tests and the docs are converted and the gate
(`tools/verify_axis_chain.py` plus every test in `tools/tests/`) is green.
Stages 2 to 6 need the robot. See `docs/Session_Handoff_2026-10-05.md` for
the exact next step. Two things turned up that this plan did not list:
`~/locations.json` holds old-frame coordinates (the dashboard now ignores a
file without a frame marker and keeps the old one as `.pre_rep103`), and the
dashboard's "masked" count was counting every NaN beam, not just the rear
wedge.

Read `Axis_Convention.md` for why the current convention exists (a LiDAR
labelling choice from 11 Aug, journal §17.9 and §17.10). That file stays
accurate until the last stage of this plan rewrites it.

## 1. The target

REP-103 for every frame the stack publishes or reads:

```
base_link / odom / map:   +X = NOSE (forward)   +Y = LEFT   +Z = UP
yaw = angle of the nose from map +X, counterclockwise positive
```

Nothing physical changes. The robot, the wheels and the LiDAR stay where they
are. Only the labels move.

### The conversion, old to new

```
x_new =  y_old        (old +Y was forward, new +X is forward)
y_new = -x_old        (old +X was right, new -Y is right)
yaw_new = yaw_old     (numerically the same, see below)
```

Why yaw is unchanged: in the old frame, yaw 0 meant the robot's right side
pointed along map +X, so the nose pointed along +Y (a direction angle of 90
degrees). The new map frame is the old one rotated by -90 degrees, so that
direction becomes 0 degrees. A robot standing on the zero mark reads
`[0, 0, 0] @ 0 deg` before and after.

Old data (saved maps, CSVs, bags) stays in the old frame. Convert with the
two lines above, or flag the frame when analysing.

## 2. What is already standard, and stays untouched

- Wheel kinematics (`mecanum_teleop_asymmetric.py`) and odometry's internal
  integration. Both speak REP-103 already.
- Dashboard joystick output (`sendDrive()`), `twist_mux`, `/cmd_vel_manual`,
  `/cmd_vel`.
- ESP32 firmware, PID, encoders.
- `slam_params.yaml` and `ekf_params.yaml` (frame names only, no axis
  numbers). MPPI speed and accel numbers, since the old strafe and forward
  limits are numerically equal (0.12 both ways).

## 3. Everything that changes

Old values are quoted so the diff can be checked against this list.

| # | File | Change |
|---|---|---|
| 1 | `src/mecanum_robot/mecanum_robot/odometry_publisher.py` | `pub_x = self.x`, `pub_y = self.y`, `pub_vx = vx`, `pub_vy = vy` (were `-self.y`, `self.x`, `-vy`, `vx`). `pub_theta` and `wz` unchanged. Docstring and comments. |
| 2 | `src/scan_relay/scan_relay.py` | `yaw_offset_deg` default 270 to 180 (true = 180 - reported, the mirror stays). Mask `mask_min_deg` -135 to 135 and `mask_max_deg` -45 to -135, which wraps through 180 (the code already handles a wrapped arc). Docstring bearings. |
| 3 | `src/mecanum_robot/urdf/aislebot.urdf` | Chassis box `0.36 1.0 0.15` to `1.0 0.36 0.15` (visual and collision). Cushion box `0.48 1.12 0.01` to `1.12 0.48 0.01`. Wheel origins `(x, y)` to `(y, -x)`: FR `0.403 -0.15769`, FL `0.333 0.15769`, RR `-0.333 -0.15769`, RL `-0.403 0.15769`. Wheel axes `1 0 0` to `0 1 0`, wheel visual rpy `0 1.5708 0` to `1.5708 0 0`. `laser_joint` `0 0.27 0.275` to `0.27 0 0.275`. Banner comment. Inertia diagonal swaps ixx and iyy. |
| 4 | `src/mecanum_navigation/config/nav2_params.yaml` | Both footprints `[[0.24,0.56],[0.24,-0.56],[-0.24,-0.56],[-0.24,0.56]]` to `[[0.56,0.24],[0.56,-0.24],[-0.56,-0.24],[-0.56,0.24]]`. `collision_monitor.cmd_vel_out_topic` `cmd_vel_baselink` to `cmd_vel_nav_out` once the adapter is gone. Header and MPPI comments (the AXES banners, the vx/vy naming, the dropped-critics text). AMCL `initial_pose` yaw stays 0.0. |
| 5 | `src/mecanum_navigation/mecanum_navigation/cmd_vel_axis_adapter.py` | Stage 4: make it an identity (`out.x = in.x`, `out.y = in.y`) so the topology stays the same while the frame changes. Stage 6: delete it, remove it from both launch files and `setup.py`, rewire collision_monitor. |
| 6 | `goal_pose_adapter.py` | No change. Already a pass-through at 0.0. |
| 7 | `src/mecanum_navigation/launch/nav2_slam.launch.py`, `navigation.launch.py` | Comments now, adapter removal in stage 6. |
| 8 | `src/mecanum_robot/launch/sensors.launch.py` | `ZERO_POINT_YAW` stays 0.0. Comment only. |
| 9 | `src/mecanum_robot/mecanum_robot/phone_dashboard.py` | `vecToYaw` to `Math.atan2(dy, dx)`, `yawToVec` to `{x: cos, y: sin}`. `FOOT_HALF_X`/`FOOT_HALF_Y` swap (0.56 along x, 0.24 along y). Laser offset `LASER_BX/BY` to `0.27, 0`. `DISPLAY_ROT` set so the nose still points up the screen (the code for it is already there, and its sign gets tested, not guessed). Axis labels on the grid. Header text. `sendDrive()` unchanged. |
| 10 | `tools/nav_goal.py`, `tools/zero_point_scan.py`, `tools/repeatability_test.py`, `tools/trajectory_viz.py` | `body_to_map` (right/forward to map) becomes the standard form, forward feeds x and left feeds y. `repeatability_test.py` `SIDE_VECTOR` follows. CLI flag names (`--forward`, `--right`) stay. |
| 11 | `tools/sensor_coverage.py`, `tools/drive_circle.py` | `LIDAR = (0.27, 0.0)`, cone bearings turn by 90 degrees, half-length constants move from y to x. |
| 12 | `tools/wheel_forensics.py` | Remove the `pub_x = -y` comparison mapping. |
| 13 | `tools/map_watch.py`, `tools/scan_bearing.py` | Doc text only. `scan_bearing.py` already describes REP-103 bearings and becomes correct as written. `map_watch.py` says "-90 = parked square", which has been wrong since §17.38. |
| 14 | `tools/verify_axis_chain.py` | Rewrite for the new frame. This is the gate for every stage (see below). |
| 15 | `tools/tests/` | `dashboard_goal_roundtrip.py`, `dashboard_scan_geometry.py`, `scan_relay_gate.py` (default yaw 270) updated to the new expectations. They have to pass before any hardware step. |
| 16 | Docs | `Axis_Convention.md` rewritten, `Firmware_Inventory.md`, a journal entry, the handoff. |

Not yet read in full, and to be read before stage 2: the Gazebo section of the
URDF (laser pose is `0 0 0 0 0 0` inside `laser_frame`, so it should follow
automatically), `simulation.launch.py` and the worlds, `arm_bridge.py` and
`run_report.py` (grep found only the word "mirrors" there, not axes).

## 4. Behaviour that will differ, on purpose

- **BackUp becomes a real reverse.** Today it strafes 30 cm left. After this
  it drives 30 cm toward the tail, into the LiDAR's blind rear wedge. The
  costmap still remembers what was seen behind the robot, but a cold start
  has no memory there. Decision needed before stage 5: leave the recovery as
  it is for now, or accept the real reverse.
- **Stock Nav2 critics become usable.** `PathAngleCritic` could return, since
  the nose is +X. Not part of this refactor. It changes planning behaviour,
  and one change at a time is the rule.
- Foxglove and RViz default views read correctly (forward is +X).

## 5. The order, with a gate on each

| Stage | Work | Gate before moving on |
|---|---|---|
| 0 | Baseline: repo `nav2_params.yaml` gets the accel values that worked on 2 Oct (ax/ay +-3.0, az 3.5). Hash, deploy, check against the live node. | Live params equal repo. The 0.6 m goal still succeeds. |
| 1 | Offline edits on a branch, no deploy. Rewrite `verify_axis_chain.py` first so it fails on the old code. | Verify script and all `tools/tests` pass. The dashboard syntax test passes on the evaluated string (CLAUDE.md rule). |
| 2 | Bench, Nav2 off. Deploy odometry, URDF, scan_relay, launch files. | `tf2_echo odom base_link` reads 0,0,0 at the mark. `W` drives x up, `D` drives y down. A block placed in front of the nose shows at bearing 0 in `/scan_reliable`, a block on the right at -90, one behind at 180. The footprint in Foxglove is long along x. |
| 3 | Dashboard to the Pi. Open it in a real browser with the console open. | Nose points up the screen. A tapped goal lands where it was tapped. No console errors. |
| 4 | Nav2 with the identity adapter and the swapped footprint. | Slow 0.3 m forward goal first, hand on the E-STOP. Then the 0.6 m goal, which is the regression test (it succeeded on 2 Oct). Then 0.3 m sideways, and a 90 degree turn. |
| 5 | Reverse test with the sheet behind (see section 4). | Decided before it runs. |
| 6 | Delete the adapter, update docs and the journal. | Same drives as stage 4, repeated. |

Every stage ends with per-file hashes before and after, and a written
prediction before any drive.

## 6. Risks

- A wrong sign shows up as a drive in the wrong direction. That is why stage 2
  has no Nav2 in it, and why the first Nav2 drive is 0.3 m.
- A half-deployed set (new odometry, old scan_relay) gives a map rotated 90
  degrees against the scan. All of stage 2's files go to the Pi together, or
  none do.
- slam_toolbox must be restarted fresh after stage 2. A live map built in the
  old frame cannot be reused.
- The mirror in `scan_relay` stays. It is a reflection of the sensor's own
  angle indexing, so it is not part of the axis choice.
