# Session handoff, 30 Sep to 1 Oct 2026

APS is behind us (23 Sep, passed). This session was the first Year 2 working
session: pose and navigation on the real robot, a full inventory of what runs
on it, and a first end-to-end test of "does it remember what it left behind".

Two sessions follow from this one, and they should stay separate.

1. A firmware session. Turn `docs/Firmware_Inventory.md` into the document
   the professor meeting needs, with a proper flow chart. Everything that
   session needs is already in the repo (section 1 below). It does not need
   anything from the autonomy thread.
2. This autonomy session, which continues. Section 2 onward is its brief.

Read `CLAUDE.md` first (the dashboard HTML rule and the operating discipline
both still apply), then this file, then `docs/Year2_Autonomy_Research.md`.

---

## 1. The firmware and node inventory, for the firmware session

All of it is in git. Nothing about the ROS 2 stack lives only in a chat.

| What | Where |
|---|---|
| Every launch file, node, topic, TF frame, Nav2 and slam_toolbox value, ESP32 and Mega protocol, dashboard message, tool | `docs/Firmware_Inventory.md` (sections 1 to 17, two Mermaid drafts, a live-graph section from 30 Sep) |
| Ten things found while reading the code | `docs/Firmware_Inventory.md` section 14 |
| Source, ROS 2 packages | `src/mecanum_robot`, `src/mecanum_navigation`, `src/scan_relay` |
| ESP32 drive firmware v3.0 (1154 lines) and arm firmware v8 | `aislebot_esp32.ino`, `aislebot_arm.ino` |
| Bench and mini-prototype sketches | `firmware/` |
| Live-system config copies | `system/` |
| Operator tools | `tools/` |

What the repo cannot show is the Pi itself: which package versions are
installed, which files on the Pi differ from the repo, the live parameter
values. `tools/verify_live_config.sh` and `tools/pi_audit.sh` exist for that.
The live graph in the inventory was captured on 30 Sep with a `check_ros.sh`
that lives on the Pi and is not in the repo. If the firmware session wants it
back, it can be rewritten from the commands the inventory lists.

Known gaps in the inventory, so nobody assumes more than is there:
the Mermaid diagrams were drafted, and only the first was checked in a
renderer. Nothing in it was validated by driving the robot. The values were
read from code and from live `ros2 param` dumps, and where the two could
differ the live dump wins.

---

## 2. State of the autonomous navigation stack, as measured on 30 Sep

Evidence grade is given in brackets: measured live, read from source, or
inferred.

### Pose

Pose is wheel odometry only. [measured] Scan matching is off (Stage G), there
is no IMU, and the `map` to `odom` correction is exactly zero. `lateral_scale`
is 0.92. Straight-line distance is good (1.503 m driven against about 150 cm,
5 mm closure). So the instinct that "pose estimation is off" is partly right:
nothing corrects drift, and rotation and strafing have not been characterised
the way straight lines have. Whether pose is the limiting error for navigation
has not been shown. The failed run below does not point at it.

### Two config fixes, deployed and verified live

Commit `b7aaa04`, `src/mecanum_navigation/config/nav2_params.yaml`,
sha256 `7d802fb0...613c204e`. On the Pi the file is
`~/ros2_ws/src/mecanum_navigation/config/nav2_params.yaml`; the `build/` and
`install/` copies are symlinks into `src`, so edit `src` only. The backup of
the old file is `~/nav2_params.yaml.bak_2026-09-30`.

1. `controller_server.odom_topic: "/wheel_odom"`. It was unset, so the
   controller listened on `odom`, which nothing publishes. It had no measured
   velocity.
2. MPPI `ax_max 0.3`, `ax_min -0.5`, `ay_max 0.3`, `ay_min -0.5`, `az_max 0.6`,
   matching `velocity_smoother`. They were 3.0 m/s^2 defaults.

Verified after relaunching Nav2 on the live node: `controller_server`
subscribes to `/wheel_odom`, `/odom` is unknown, the accel limit reads 0.3.
This changes how the controller behaves, but no goal has succeeded since, so
"improved" is not yet something we can claim.

### Obstacle memory, tested

The local costmap is a rolling 3 x 3 m window with obstacle and inflation
layers and no static layer. A mark persists until a laser ray clears it or it
leaves the window. [measured] With a wooden sheet placed behind the robot,
the memory held at about 1 m for about 100 s after the robot turned its back on
it. [measured] The collision monitor has no memory at all, only live
`/scan_reliable`. [read from config]

Inflation is a flat 253 within about 25 cm of an obstacle and decays as
`252 * exp(-5 * (d - 0.25))` beyond that. Footprint is 0.48 x 1.12 m padded,
circumscribed radius 0.62 m. The rear wedge (107 beams, -135 to -45 deg) is
masked, so the memory only exists for things the LiDAR saw earlier.

### The failed goal run, 30 Sep (`run_20260930_160613`)

A goal whose heading needed a 174 degree turn. The robot stalled for about
100 s, then the controller commanded a reverse toward the wall in the rear
blind zone. Why it stalled is not established. Candidates: the padded
footprint against the wall, MPPI's collision cost, or collision-monitor
scaling. All three are unproven. The CSVs are on the Pi in
`~/aislebot_logs/` and on the operator's PC. They are not in the repo.

### Test A, the backward goal (aborted)

Setup: wooden sheet about 30 cm behind the robot's back end, robot facing
180 degrees away from the sheet. Command:

```
python3 ~/ros2_ws/tools/nav_goal.py --forward=-0.10
```

which printed GO `(-0.0016, +0.1000)` at yaw about 180, and a RETURN goal to
`(-0.0006, 0.0000)`. Prediction written before the drive: reverse 10 cm,
gap to the sheet about 20 cm, success, no contact.

Result: ABORTED, `error_code 105`, 15 recoveries, about 198 s,
`distance_remaining` frozen at 0.318 m. Robot ended near `(0.27, -0.01)`,
yaw about 173.7 degrees. The operator reports no contact, the sheet did not
move, and the gap is still about 30 cm. So the robot did not reverse toward
the sheet. The 27 cm sideways displacement is about one BackUp recovery, and
BackUp is a strafe on this robot (below), so recovery probably moved it, not
the controller.

The prediction was wrong. The honest status is "unexplained, safe".

### What the source says (read, not run)

- `BackUp` and `DriveOnHeading` command `linear.x` and check collisions along
  the base frame's x axis. base_link +X is the robot's right here, so BackUp is
  a 30 cm strafe to the left, not a reverse. An earlier version of the
  research doc said the opposite. It is corrected in `b7aaa04`.
- MPPI `CostCritic` sets a trajectory's cost to 1,000,000 when any sampled
  pose is in collision, and sets `fail_flag` when every trajectory collides.
  A start pose already inside an inflated zone would therefore stall the
  controller. Whether that happened is the question below.
- MPPI has `vx_min` but no `vy_min`, so reverse speed cannot be capped
  separately on this robot. `PathAngleCritic` and `PreferForwardCritic` were
  dropped because they assume forward is +x.
- The controller loop was measured at 5.5 to 8.9 Hz against 20 Hz requested
  (300 samples x 40 steps x 0.05 s). Gate G3 stays open.

### Mistakes made this session, so they are not repeated

- Said BackUp reverses into the rear wedge. It strafes left. Source-confirmed.
- Said a 30 cm test object would do. The scan plane is about 0.35 m above the
  floor, so the object must be 40 cm or taller.
- Predicted 253 at a point 40 cm out. Inflation decays past 25 cm.
- Suggested the start pose was already inside the sheet's inflation. A 30 cm
  gap at the back end does not put the robot's centre inside it, so that
  explanation is not supported until something else near the centre is found.

---

## 3. Requirements and decisions that stand

- Reversing, holonomic and omnidirectional motion are the research
  contribution ("that is my work"). A forward-only policy was proposed and
  rejected. Do not propose it again.
- The robot must remember what it saw and avoided behind it, including the
  immediate rear that the LiDAR cannot see. The failure to guard against is:
  turn 180 degrees after seeing an obstacle, then reverse into it.
- The axis convention (+X right, +Y forward) costs real work: BackUp, MPPI
  critics, RViz, every Nav2 default. Reverting to REP-103 was recommended,
  staged, and not first. No go-ahead has been given. The touch list is
  `odometry_publisher.py`, the URDF, `nav2_params.yaml`,
  `cmd_vel_axis_adapter`, `goal_pose_adapter`, the zero-point marker,
  `scan_relay` yaw offset and rear mask (the mirror stays, TF cannot express a
  reflection), the dashboard, `nav_goal.py`, `zero_point_scan.py`, and tests,
  gated by `tools/verify_axis_chain.py`.
- Saved-map and AMCL work is paused by the operator. Autonomous navigation and
  mapping in unknown space comes first.

---

## 4. Next steps, in order

1. Run two read-only checks on the Pi, one at a time, with the robot where it
   is (the last known pose was x 0.269, y -0.011, yaw 3.032 rad; change the
   numbers if it moved):

   ```
   ros2 service call /local_costmap/get_cost_local_costmap nav2_msgs/srv/GetCost "{x: 0.269, y: -0.011, theta: 3.032, use_footprint: false}"
   ros2 service call /local_costmap/get_cost_local_costmap nav2_msgs/srv/GetCost "{x: 0.269, y: -0.011, theta: 3.032, use_footprint: true}"
   ```

   Prediction: the first reads well under 253. If it reads 253, something
   other than the sheet (a wall) is within about 29 cm of the robot's centre,
   and the sheet was never what blocked the goal.
2. Repeat the same 10 cm reverse with the sheet removed. If it succeeds, the
   sheet's memory is what refused the goal. If it fails the same way, the
   fault is elsewhere.
3. Any further drive gets a bag recording first: `/cmd_vel_nav`,
   `/cmd_vel_smoothed`, `/cmd_vel_baselink`, `/cmd_vel_nav_out`,
   `/collision_monitor_state`, `/wheel_odom`, `/tf`, `/plan`. That shows which
   stage zeroed the command.
4. Then, in open floor: a 1 m forward goal, a 1 m sideways goal, a 90 degree
   turn. Predictions written before each.
5. Retune MPPI toward 10 Hz and a 0.1 s model step, only after measuring CPU
   and the real loop rate during a run (`top`, `ros2 topic hz /cmd_vel_nav`,
   temperature).
6. Decide the REP-103 refactor, with a staged plan and a gate per stage.
7. Rear sensing hardware (rear DTOF LiDAR, ToF ring) per
   `docs/Year2_Autonomy_Research.md`. The software memory covers what was seen,
   not what is behind the robot on a cold start.

Operator notes: do not re-zero odometry with Nav2 running. E-STOP on the
dashboard also stops mapping by design, which kills slam_toolbox and the
LiDAR chain. After Nav2 exits, the ROS 2 daemon cache shows ghost services;
`ros2 daemon stop` clears them. `service call` for `get_cost` takes `x`, `y`,
`theta` in the costmap frame, which is `odom`, the same as `map` today.

---

## 5. Still open, and not blocking

AMCL has no `scan_topic` set and would read raw `/scan`, and `install.sh`
still copies the pre-Stage-G SLAM file. Both are in the inventory's section
14 and both wait on the saved-map work. The `BackUp` comment in
`nav2_slam.launch.py` and the `nav2_params.yaml` header comments still use
the old reading; comment-only, not yet fixed.

Command chain for reference, since every drive passes through it:
`controller_server` and `behavior_server` to `/cmd_vel_nav`, then
`velocity_smoother`, `collision_monitor`, `cmd_vel_axis_adapter`
(`out.x = in.y`, `out.y = -in.x`), `twist_mux` (manual priority 100, nav 10),
`/cmd_vel`, `teleop_asym`, `/wheel_speeds`, `esp32_bridge`, the ESP32
(100 Hz PID), encoders, `odometry_publisher`, `/wheel_odom` and the
`odom` to `base_link` transform.
