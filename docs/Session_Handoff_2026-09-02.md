# Session handoff — 2 Sep 2026, 11:40 local

Written mid-session, with the robot powered and the stack running, because
the session that was driving it was about to be restarted. Everything below
is either (a) observed live in the last few minutes, or (b) explicitly
flagged as unverified. Nothing here is recalled from a summary.

---

## 1. What is physically true right now

The robot is **powered, parked on the ground zero mark, and fully brought
up**. Do not re-zero it and do not restart anything before reading §4.

| Layer | State | Evidence |
|---|---|---|
| `aislebot.service` | up | odom TF present, dashboard renders a pose |
| Odometry zero | zeroed twice, robot on the ground mark | dashboard `X 0.000  Y 0.000  NOSE 0.0°` |
| `mapping_full.launch.py` | **running**, mapping session live | dashboard shows a live occupancy grid |
| `map -> odom` | identity | dashboard `DRIFT 0.000 m`, `map−odom 0.000, 0.000` |
| `nav2_slam.launch.py` | **running, all managed nodes active** | launched 11:36:40, log below |
| Distance driven this session | **zero** | no goal has been sent |

Nav2 bringup at `2026-09-02-11-36-40` was clean. The four lines that matter:

    [cmd_vel_axis_adapter-9]  cmd_vel_baselink -> cmd_vel_nav_out
    [goal_pose_adapter-10]    /goal_pose_click -> /goal_pose, yaw +0.0 deg
    [collision_monitor-6]     [FootprintApproach]: Making footprint subscriber
                              on /local_costmap/published_footprint topic
    [lifecycle_manager-11]    Managed nodes are active

The first two are the nodes that silently died on 1 Sep and cost a whole
run (§17.49 — the `--symlink-install` build-mode trap). They are alive.

`StaticLayer: Resizing costmap to 196 X 115 at 0.050000 m/pix` matches the
dashboard's own `196 x 115 - 0.05 m/cell`, which means `/map` was already
being published when `global_costmap` configured. No `Received map message
is malformed` spam this time. MAP-then-NAV order was followed.

Two warnings appeared and are known-benign, not new:

    [bt_navigator]      Error_code parameters were not set. Using defaults
    [controller_server] Parameter controller_server.verbose not found

---

## 2. What is NOT verified — check, do not assume

- **Whether PR #10 is deployed to the robot.** The branch carries the
  launch split (`sensors.launch.py`, and `mapping_full.launch.py` rewritten
  to include it). Belief is that it is NOT deployed and the robot is
  running the pre-split installed copy. That belief is not evidence.
  Check on the Pi:

      ls ~/ros2_ws/install/mecanum_robot/share/mecanum_robot/launch/

  If `sensors.launch.py` is absent, the robot is pre-split. That is FINE
  for today's work — the split only matters for AMCL, which is not today's
  job. Do not rebuild mid-session to fix it.

- **Whether the FootprintApproach polygon is actually receiving a
  footprint.** This is the single most important unverified thing in the
  whole stack, see §3.

- The room layout, obstacle, and goal. Never answered. See §5.

---

## 3. The job this branch exists for

> A detected obstacle must stop the robot **regardless of an active goal**,
> using the cushioning value already configured.

This is not a new safety system to design. It is
`collision_monitor`'s `FootprintApproach` polygon in
`src/mecanum_navigation/config/nav2_params.yaml`, and the task is to
**verify it for real, on hardware, with a physical obstacle**. It has never
once been exercised.

Configured values, read from the file on 2 Sep:

    action_type:            "approach"
    footprint_topic:        "/local_costmap/published_footprint"
    time_before_collision:  1.2
    simulation_time_step:   0.1
    min_points:             6
    observation_sources:    ["scan"]
    scan.topic:             "/scan_reliable"

The footprint is the 1.12 x 0.48 m cushioned rectangle; `inflation_radius`
is 0.65 on both costmaps.

### 3a. Verify against the LIVE node before driving

File values are not runtime values. Run these and read the answers:

    ros2 param get /collision_monitor polygons
    ros2 param get /collision_monitor FootprintApproach.action_type
    ros2 param get /collision_monitor FootprintApproach.time_before_collision
    ros2 param get /collision_monitor FootprintApproach.min_points
    ros2 param get /collision_monitor observation_sources
    ros2 param get /collision_monitor scan.topic

### 3b. The silent-failure check that matters most

`FootprintApproach` defines no polygon points. It logged:

    Polygon points are not defined. Using dynamic subscription instead.

So the entire safety layer is only as real as that subscription. If
`/local_costmap/published_footprint` never arrives, the polygon is empty,
`min_points: 6` is never met, and **collision_monitor becomes a silent
no-op that logs nothing and stops nothing**. Prove it arrives:

    ros2 topic echo /local_costmap/published_footprint --once
    ros2 topic hz  /local_costmap/published_footprint

Expect a ~1.12 x 0.48 m rectangle of points and a steady rate. If this
topic is silent, STOP — nothing downstream is a valid test.

### 3c. Instrumentation for the drive itself

The proof of an intervention is a **throttled output while the input is
still commanding motion**. Watch, in three terminals:

    ros2 topic echo /collision_monitor_state
    ros2 topic echo /cmd_vel_smoothed    # input  to collision_monitor
    ros2 topic echo /cmd_vel_baselink    # output from collision_monitor

An intervention is: `/cmd_vel_smoothed` non-zero, `/cmd_vel_baselink`
driven toward zero, `/collision_monitor_state` naming the polygon.

### 3d. TRAP — do not touch the joystick during the test

`twist_mux` gives `/cmd_vel_manual` **priority 100** against navigation's
**10**. One keypress on the dashboard joystick routes around
`collision_monitor` entirely and the robot will drive into the obstacle
with the safety layer working perfectly. Hands off the pad. E-STOP is the
correct abort, not the joystick.

---

## 4. Do not do these

- Do not re-zero the odometry. It is zeroed and the robot is on the mark.
- Do not restart `mapping_full.launch.py`. Restarting it re-plants the map
  origin at wherever odometry currently is (§17.18/§17.19).
- Do not run `navigation.launch.py` (AMCL) while mapping. Both publish
  `map -> odom` and running both corrupts the estimate.
- Do not run `colcon build --symlink-install` on `mecanum_navigation`.
  It was previously built without symlinks, colcon does not reconcile the
  two modes, and the result is `PackageNotFoundError` at runtime while the
  build prints `Summary: 2 packages finished`. If a rebuild is genuinely
  needed: `rm -rf build/mecanum_navigation install/mecanum_navigation`
  first, then a clean build, then **relaunch what you deployed**.

---

## 5. The three blocking questions — still unanswered

The obstacle drive cannot be written without these:

1. **Which aisle**, and its clear length x width. Floor tiles are 62 cm.
2. **The obstacle** — object, footprint, and height. Must stand **>= ~40 cm**
   or the LiDAR plane at 0.351 m passes over it and the test measures
   nothing.
3. **The gap either side** once placed. A wide gap tests *avoidance*
   (planner reroutes). A gap too narrow to pass tests the *override*
   (obstacle stops the robot despite a live goal). The narrow case is the
   one the branch was created for and is the stronger result.

Ask these first. Do not propose a drive without them.

---

## 6. Repo state

- Branch: `claude/narrowaislebot-goal-obstacle-avoidance-f2t3aa`
- Cut fresh from `main` at `5cace67` (merge of PR #9, 27 commits — closed a
  5-day staleness that had an external audit written against an old tree).
- Commits on the branch: `d3c89d6` launch split, `7b53984` journal §17.49 +
  kickoff rewrite + axis-guard fix, plus this handoff.
- PR #10 open as **draft**. No CI in this repo — `.github/workflows` does
  not exist, so a green PR means nothing was checked automatically.
- Both local guards pass and should be re-run after any change:

      python3 tools/verify_axis_chain.py            # 43 checks
      python3 tools/tests/dashboard_goal_roundtrip.py  # 19 checks

---

## 7. Standing operating discipline

Carried unchanged across sessions. The operator asked for each of these.

- One step at a time, copy-pasteable. Wait for the result.
- Never assume a step succeeded. Ask for the output.
- Verify configuration with `ros2 param get` against the **live node**,
  never by reading the YAML.
- **Hash every transferred file on arrival, per file, not per batch.**
- Never put the password on a command line. It once got appended to an
  `scp` destination.
- Short and crisp in chat. Full prose in `Research_Journal.md`.
- SLAM is not abandoned; it is just not gating this branch. Fix mapping
  issues in place and record them.
- Every factual claim about this robot carries its provenance: read from a
  file this session, `ros2 param get` this session, a hash the operator
  pasted, or a timestamped log line. No provenance means say "I don't
  know, let's check" — see `.claude/skills/session-health/SKILL.md`.

---

## 8. Known-open, not today's job

- Stage F (`use_scan_barycenter: false`) re-drive on the registered route
  (0, 1.02) -> (-0.16, 2.03) -> (0, 0). Currently **AMBIGUOUS** and
  deliberately unscored — see `StageF_Ablation.md`, including the retracted
  0.175 m node-spacing measurement.
- AMCL has never been run once. Blocked until the launch split deploys.
- The LiDAR is hardware-limited (X4 Pro, measured p90 22.8 mm, within its
  own <2%-of-range spec). Rated 3/10 and not fixable in software. Every
  other layer is being taken to 10 in software instead.
