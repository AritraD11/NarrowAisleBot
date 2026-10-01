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

---

# Part 2. The hardware session of 1 Oct, afternoon

Read this before section 4. Section 4's first two steps are done, and the
answer to both was "no". The planner is fine, the start pose is not in
collision, and the fault turned out to be somewhere else.

## 6. What we ran, in order

1. Clean start at the zero mark. Order that works: stop Nav2, stop the map,
   re-zero odometry, start the map, wait 30 s, start Nav2. Moving the robot by
   hand moves odometry too, so re-zero before the map starts, never after.
2. Local costmap `get_cost` at the zero mark, centre point 0.0 and padded
   footprint 196. Nothing sits within 0.65 m of the centre and the box is not
   in collision. The "start pose already inside an inflated zone" idea is not
   supported. [measured]
3. The dashboard map twice showed one occupied cell inside the robot's box,
   about 10 cm left and 17 cm ahead of the centre. It never appeared in a
   costmap query and was gone in the later session. Unexplained. The dashboard
   map is the slam map, not a costmap, so it cannot predict a costmap reading.
4. First goal, (-0.23, 1.80). The planner failed five times ("Failed to create
   plan with tolerance of: 0.5"), the behaviour tree spun the robot +92 degrees
   (the "random turn"), BackUp strafed it 0.31 m left, and then the planner
   worked but the controller barely moved. The cause of that first planner
   failure is not known. [measured, log and wheel CSV]
5. Planner-only test, `/compute_path_to_pose`, no motion: it succeeded from
   y = 0.49 and again from the zero mark after a clean restart. [measured]
6. Global costmap `get_cost` at (0,0): footprint 254 while the robot was
   actually at y = 0.49 (so it described the wrong spot), then 164 once the map
   had grown. Probable cause, not confirmed: the padded box hanging off the
   edge of the map.
7. Goal 0.6 m straight ahead, (0.0, 0.6). ABORTED, error 105, 16 recoveries,
   194 s, no contact. End pose (-0.244, 0.249), yaw about -0.3 degrees. The
   robot crept about 1.5 mm/s toward the goal, and the progress checker needs
   0.10 m in 10 s.

## 7. The key result: the speed is lost inside MPPI

A bag of the 0.6 m run (`~/aislebot_logs/bags/fwd06_151045` on the Pi, 53 MB,
plus `fwd06_small`, 4.7 MB, with only the command chain, the collision monitor
state, `/plan` and the footprint) gives the speed at every stage of the chain
between MPPI and the wheels, first 40 s of the goal, mean and peak in m/s:

| Stage | 0 to 10 s | 10 to 20 s | 20 to 30 s | 30 to 40 s |
|---|---|---|---|---|
| `/cmd_vel_nav` (MPPI) | 0.0044 / 0.0084 | 0.0051 / 0.0103 | 0.0038 / 0.0089 | 0.0044 / 0.0092 |
| `/cmd_vel_smoothed` | 0.0044 / 0.0084 | 0.0051 / 0.0103 | 0.0038 / 0.0089 | 0.0043 / 0.0092 |
| `/cmd_vel_baselink` | 0.0044 / 0.0084 | 0.0050 / 0.0103 | 0.0038 / 0.0089 | 0.0043 / 0.0092 |
| `/cmd_vel` | 0.0044 / 0.0084 | 0.0050 / 0.0103 | 0.0038 / 0.0089 | 0.0043 / 0.0092 |

The numbers are the same at every stage, so `velocity_smoother`,
`collision_monitor`, `cmd_vel_axis_adapter`, `twist_mux` and the ESP32 are
cleared. MPPI itself is asking for about 4 mm/s. The collision monitor changed
state only 14 times in 12 minutes, always to APPROACH and back, and always
during a recovery behaviour, never while the controller was driving. Motor PWM
peaked near 29 out of 255 during the stall. [measured]

Two pieces of context, neither of them proof.

- The size of the output matches averaging noise. `vx_std` and `vy_std` are
  0.06 m/s over 300 samples, and 0.06 divided by the square root of 300 is
  3.5 mm/s, against a measured 4.4 mm/s. That says the optimizer is hardly
  preferring any direction. [arithmetic, matches]
- The 30 Sep run, before the acceleration edit, had mean wheel commands 5 to
  10 times larger than this run. My acceleration edit limits one 0.05 s step to
  0.3 x 0.05 = 0.015 m/s, which is the scale of what we see. But the 30 Sep run
  also stalled in places, so the edit is a suspect, not the cause. [suggestive]

## 8. State when the session ended

- `mapping_full` running, started with the robot on the zero mark and odometry
  at 0, 0. Nav2 up (`nav2_slam.launch.py`, started after the map). Robot on
  the zero mark.
- MPPI acceleration limits set LIVE to the stock values: `ax_max 3.0`,
  `ax_min -3.0`, `ay_max 3.0`, `ay_min -3.0`, `az_max 3.5`, confirmed with
  `ros2 param get` (`ay_max` reads 3.0). The repo file still says
  0.3 / -0.5 / 0.3 / -0.5 / 0.6. The live change is lost when Nav2 restarts.
  `velocity_smoother` still caps real acceleration at 0.3 m/s^2.
- The 0.6 m goal has not been re-sent since the change.

## 9. Next steps, in order (replaces the order in section 4)

1. Confirm the live parameters with `ros2 param get`, then send the 0.6 m goal
   again with a hand on the E-STOP (Ctrl+C in the terminal cancels the goal).
   Written prediction: it reaches the goal, about 60% confidence.
   ```
   ros2 action send_goal --feedback /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: map}, pose: {position: {x: 0.0000, y: 0.6000, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
   ```
2. If it drives: choose permanent acceleration values (measure the real
   acceleration on a straight run), edit `nav2_params.yaml`, hash it, deploy,
   verify against the live node.
3. If it still creeps at about 4 mm/s, the acceleration limits are not the
   cause. Next suspects: `temperature` (0.3), the sampling spread (0.06), the
   critic weights, and the real loop rate (5 to 14 Hz) against the 20 Hz and
   0.05 s the model assumes.
4. Then the ladder: 1 m forward, 1 m sideways, a 90 degree turn, a reverse with
   the sheet behind it, then the explorer.

## 10. Rules that bit us on 1 Oct

- Query the robot's real pose before any `get_cost`. A reading at (0,0) is
  meaningless if the robot is at y = 0.49.
- The two services are `/local_costmap/get_cost_local_costmap` and
  `/global_costmap/get_cost_global_costmap`. The planner uses the global one,
  MPPI and the collision monitor use the local one.
- A bag that is not closed has no `metadata.yaml` and may be unreadable. Stop
  the recorder with `pkill -INT -f "ros2 bag record"`, wait for `metadata.yaml`.
- Trim a big bag on the Pi before moving it, with `ros2 bag convert -i <bag>
  -o small.yaml` (an `output_bags` list with `uri`, `storage_id: mcap` and
  `topics: [...]`).
- Read a bag anywhere with `tools/bag_cmd_chain.py` (needs `pip install mcap
  mcap-ros2-support`). It prints the table in section 7 for any run.
- Not in the repo: both bags, and the CSVs for `run_20261001_120846` (on the
  Pi in `~/aislebot_logs/` and on the operator's PC).
