# The Pi and its ROS 2 stack, end to end, and what stands between it and an autonomous robot

Written 17 Oct 2026, from the live Pi (read-only, over the `ro` SSH key) and from the repo
after it was synced with the Pi the same day. It builds on `docs/Firmware_Inventory.md`
(30 Sep) and `docs/Year2_Autonomy_Research.md` (29 Sep) and does not repeat their detail.
Where this file disagrees with them, section 3 says so.

Evidence grades, as in the handoffs: **[live]** measured on the robot today,
**[source]** read in code or config, **[inferred]** reasoning from the two.
Nothing here was driven. The robot sat still on the floor for every measurement.

What was **not** checked: the ESP32 and Mega firmware versions (no gate verb can query
them), anything that needs the LiDAR or Nav2 running (neither is up at boot), the physical
state of the robot (level, wiring, battery), and CPU or temperature under load.

---

## 0. The short version

1. **The base platform is in good shape.** Drive control, telemetry, the velocity chain
   with its stacked watchdogs, the dashboard and the boot process all run cleanly. Wheel
   odometry and telemetry arrive at 20.000 Hz with 0.1 ms jitter, the IMU at 49.999 Hz
   with 0.07 ms jitter. The Pi has 3.2 GiB of free RAM, 14 GB of free disk and a load
   average of 0.4. [live]
2. **Nothing autonomous has been shown to work since the 5 to 6 Oct axis refactor.**
   The whole stack moved from a private frame (+X right) to standard REP-103 (+X nose).
   The newest Nav2 log (6 Oct, 17:09) holds no goal result, and the Nav2 params header
   itself says the footprint "has NOT been checked against the live
   `/local_costmap/published_footprint` since the 5 Oct 2026 axis change; do that before
   the first autonomous run". The refactor's own regression goals are not recorded
   anywhere in the repo. [live, source]
3. **The IMU hardware is healthy at rest, but nothing uses it and its state is
   invisible.** Timing, quaternion validity, gyro bias and accelerometer gain all pass
   (section 5). Two findings need action before configuring anything: the sensor reads
   a **10 degree roll at rest** (accelerometer and fusion agree, so it is mounting or the
   floor, not an algorithm fault), and the calibration and self-test state **never reach
   ROS**. `/imu/data` has no subscriber. [live, source]
4. **Mode 1, navigating a saved map, is mostly present as parts and not as a workflow.**
   AMCL, the map server and the Nav2 chain are installed and configured. None of it has
   ever run on this robot. The operator interface cannot start it, cannot set an initial
   pose, and cannot choose a map. The AMCL block would read the raw mirrored `/scan`. The
   map folder is empty, and no pose graph or named location exists. [live, source]
5. **Mode 2, exploring unknown space, is the larger gap.** No exploration node is
   installed or written. The live map is wheel odometry drawn in LiDAR ink (scan matching
   is off, so there is no loop closure), the LiDAR is capped at 2.5 m, and there is a
   blind rear wedge. [live, source]
6. **Safety gaps matter more than either mode.** There is no hardware E-stop, no battery
   measurement and no bumper, and the default Nav2 `BackUp` recovery now reverses
   straight into the masked rear wedge. [source, inferred]

Section 7 turns this into a build order. The IMU work comes first, as you asked.

---

## 1. The machine as it stands today [live unless marked]

| Item | State |
|---|---|
| Computer | Raspberry Pi (aarch64), Ubuntu 24.04.4, kernel 6.8.0-1061-raspi, ROS 2 Jazzy, Cyclone DDS, domain 42. The inventory names it a Pi 5. |
| Memory, disk | 3.9 GiB total, 697 MiB used, swap unused. Disk 29 GB, 53 % used. |
| Load | 0.43 / 0.55 / 0.53 with only the base stack running |
| USB | CH340 (Mega), two CP210x (ESP32 and the LiDAR adapter). `/dev/esp32` and `/dev/mega` resolve. |
| Boot | `aislebot.service` active, started by systemd, restarts on failure [source] |
| Running at boot | 11 nodes: `joy_node`, `joy_to_aislebot`, `phone_dashboard`, `twist_mux`, `teleop_asym`, `esp32_bridge`, `odometry_publisher`, `arm_bridge`, `lcd_display`, `foxglove_bridge`, `robot_state_publisher` |
| Not running | LiDAR driver, `scan_relay`, slam_toolbox, Nav2, AMCL, EKF. All start on demand. |
| ROS packages installed | Nav2 in full (MPPI, Smac, NavFn, RPP, graceful and rotation-shim controllers, AMCL, map server, waypoint follower, route, `opennav_docking`), `slam_toolbox`, `robot_localization`, `twist_mux`, `rosbag2` with MCAP, `diagnostic_updater`, `cv_bridge`, `vision_msgs`, `rplidar_ros` |
| Not installed | any exploration package (`explore_lite`, `frontier_exploration`), any IMU filter, any camera driver |
| Workspace packages | `mecanum_robot`, `mecanum_navigation`, `scan_relay`, `ydlidar_ros2_driver` |
| Last time driven | 6 Oct 2026. The newest run files are `run_20261006_*`. Nothing since. |
| Saved maps | 275 `.pgm`/`.yaml` pairs in `~/aislebot_logs/`, one per mapping run. `~/ros2_ws/maps/` is empty. No `.posegraph` or `.data` file exists anywhere. |
| Named locations | `~/locations.json` does not exist. The feature has never been used on the robot. |

Rates measured today: `/wheel_odom` 20.000 Hz (window 368, spread 0.049 to 0.051 s),
`/motor_telemetry` 20.000 Hz, `/imu/data` 49.999 Hz.

---

## 2. The architecture, from hardware to operator

```
OPERATOR      phone browser / PC  --Wi-Fi AP aislebot-ap (10.42.0.1:8080)-->  phone_dashboard
                                                       Foxglove (8765) <-- foxglove_bridge

STATE MACHINE (none)  mapping and Nav2 are started by hand or by dashboard buttons, one process
                      group each. There is no mode manager.

PLANNING      bt_navigator -> planner_server (NavFn, A*) -> controller_server (MPPI, omni)
  (Nav2)         |               global costmap                  local costmap 3 x 3 m rolling
                 +-- behavior_server (Spin, BackUp, Wait), waypoint_follower
                 map->odom: slam_toolbox (mapping, matching OFF)  or  AMCL (saved map, never run)

PERCEPTION    ydlidar X4 Pro -> /scan (BEST_EFFORT) -> scan_relay -> /scan_reliable
                 scan_relay: mirror, yaw 180, mask rear 90 deg to NaN, range cap 2.5 m
              (no camera, no depth, no sonar, no bumper)

POSE          encoders -> ESP32 -> /wheel_velocities_actual -> odometry_publisher
                 -> /wheel_odom + TF odom->base_link      <- the ONLY pose source
              BNO055 -> ESP32 -> esp32_bridge -> /imu/data   <- published, nobody subscribes
              (robot_localization is installed; no EKF runs)

VELOCITY      NAV:    controller/behavior -> /cmd_vel_nav -> velocity_smoother
                         -> collision_monitor (1 polygon, scan only) -> /cmd_vel_baselink
                         -> cmd_vel_axis_adapter (IDENTITY since 5 Oct) -> /cmd_vel_nav_out
              MANUAL: joystick / dashboard -> /cmd_vel_manual
              both -> twist_mux (manual 100, nav 10, 0.5 s timeouts) -> /cmd_vel
                 -> teleop_asym (inverse kinematics) -> /wheel_speeds -> esp32_bridge
                 -> <V,fr,fl,rr,rl> -> ESP32 (100 Hz PID, 750 ms watchdog, latching E-STOP)

HARDWARE      ESP32 drive MCU (USB serial 921600) + Mega arm MCU (115200), 4 mecanum wheels
              with encoders through a level shifter, YDLIDAR, BNO055 on ESP32 G13/G14
```

The command chain and its three stacked watchdogs (twist_mux 0.5 s, bridge 0.5 s, ESP32
750 ms) are as `Firmware_Inventory.md` section 5 describes, and they are unchanged except for
the adapter becoming an identity. [source] That chain is the best-engineered part of
the robot.

What the live graph shows that the documents did not [live]:

- `/imu/data` has one publisher (`esp32_bridge`) and **zero subscribers**.
- The dashboard now subscribes to `/plan` (it did not on 30 Sep).
- `twist_mux` publishes `/diagnostics`. It is the only diagnostics source on the graph.
  There is no aggregator and no health node.
- The topic list still shows `/map`, `/plan` and `/scan_reliable` with no publisher.
  Those are stale entries in the ROS 2 daemon cache from processes that already exited
  (the 30 Sep inventory describes the same effect). `ros2 daemon stop` clears them.

---

## 3. What has changed since the 30 Sep inventory

The inventory is accurate for its date. These points have moved:

| Inventory said | Now [source unless marked] |
|---|---|
| `base_link` +X = right, +Y = forward | Standard REP-103 since 5 Oct (+X nose, +Y left). `odometry_publisher`, the URDF, `nav2_params.yaml`, `goal_pose_adapter` and `cmd_vel_axis_adapter` were rewritten. The refactor plan is `docs/Axis_Refactor_Plan.md`, **which is not in the repo**. |
| `cmd_vel_axis_adapter` rotates x and y | An identity pass-through. Its docstring says it stays until the refactor's stage 6 regression goals have driven, then it is deleted. |
| "No IMU fitted" | A BNO055 is wired and streaming at 50 Hz, so the ESP32 firmware is v3.1 or later (v3.0 answers `<N1>` with an error). The ESP32 acknowledges `[OK,IMU_STREAM=1,HZ=50.0]` every 5 s. [live] |
| Controller `odom_topic` unset (section 14, item 3) | Fixed: `controller_server.odom_topic: "/wheel_odom"`. |
| MPPI acceleration limits 3.0 default | The Pi's file has 3.0 (the 0.3 experiment of 30 Sep to 1 Oct did not stay). |
| `scan_relay` yaw 270, mask -135 to -45 | yaw 180, mask 135 to -135 (rear wedge in the new frame), and a new **`range_cap_m` 2.5** ("fixed 5 Oct 2026"). |
| Dashboard has map start and stop only | Adds `nav2_start` and `nav2_stop`, and subscribes to `/plan`. It can start Nav2 only in the live-SLAM mode (`nav2_slam.launch.py`). |
| AMCL reads the raw `/scan` (item 2) | **Still open.** The `amcl` block has no `scan_topic`. |
| v3.1 firmware "never flashed" | Superseded by the live IMU stream. |

Repo state after today: the Pi's nine newer files and three more (`cmd_vel_axis_adapter.py`,
`goal_pose_adapter.py`, `mecanum_navigation/package.xml`) were copied into git
(`b218406`, `7cc9678`), byte-identical to the Pi's. Still not in the repo: about seven
tools that exist only on the Pi (`bag_tf_diff`, `map_watch`, `pathlog`,
`repeatability_test`, `scan_bearing`, `trajectory_viz`, `zero_point_scan`), and the 5 to 6 Oct
journal entries. `docs/Research_Journal.md` ends on 3 Sep.

---

## 4. Sensing and state estimation, as built

**Pose.** Every pose the robot believes is wheel dead reckoning. `map->odom` is held at
identity, because slam_toolbox runs with `use_scan_matching: false` (Stage G). With
matching off, Karto builds no pose graph, so loop closure is not merely unobserved, it is
impossible (`Year2_Autonomy_Research.md` section 3). Documented drift: 1.1 to 1.5 % of path
on long routes, a phantom yaw of about 4 degrees, and a lateral scale that depends on the
floor (0.92 on one, 0.80 on another). [source]

**LiDAR.** One YDLIDAR X4 Pro, about 430 points at 11.35 Hz, 47.4 % valid at any instant,
12 to 14 mm scatter below 1.5 m and 55 to 200 mm past 2.5 m [source, 29 Sep]. `scan_relay`
now caps it at **2.5 m**. A 90 degree wedge behind the robot (107 beams) is masked, so
neither costmap nor `collision_monitor` sees anything there. The scan plane is about 0.275
m above the floor. Nothing below that, or behind, is sensed.

**IMU.** Section 5.

**Dependence between the three.** The Year 2 research found that with scan matching off,
better odometry improves the map one for one, because no matcher sits between them. So
the IMU is the first lever for both modes, and the reason it comes first.

---

## 5. The IMU health check

Captured 17 Oct at about 14:20 IST, robot stationary and the drive idle: 931 messages over 18.6 s
through `ros2 topic echo --no-arr /imu/data`, analysed offline (`imu_health.py`, run in
WSL).

| Check | Result | Verdict |
|---|---|---|
| Publish rate | 50.05 Hz by stamp, dt 20.00 ms, **stdev 0.07 ms**, min 19.61, max 20.38 | pass |
| Gaps and ordering | 0 gaps over 30 ms, 0 non-monotonic stamps | pass |
| Quaternion validity | length 1.00000, worst deviation 0.00000 | pass |
| Stuck data | 3 of 930 consecutive samples identical (0.3 %) | pass |
| Gyro bias at rest | x +0.002, y -0.135, z -0.048 mrad/s (all under 0.008 deg/s) | pass |
| Gyro noise | stdev 0.93, 1.23, 0.59 mrad/s, about one LSB | pass, see note 1 |
| Accelerometer gain | \|a\| 9.7705 m/s^2, error -0.036 against 9.8067 (-0.37 %) | pass |
| Accelerometer noise | stdev 0.011, 0.012, 0.013 m/s^2 | pass |
| Fused yaw, 18.6 s | +0.0000 degrees | pass, see note 2 |
| **Level** | roll **+9.98 deg**, pitch **+2.17 deg** at rest | **open**, see note 3 |
| Covariances as published | orientation 1e-3, gyro 3e-5, accel 1e-2 (placeholders in the bridge) | works, see note 4 |
| **Status visible in ROS** | calibration, self-test, I2C faults: **not published** | **gap**, see note 5 |
| **Consumers** | `/imu/data` has zero subscribers | gap |

Notes.

1. The BNO055 gyro resolves 0.0625 deg/s, which is 1.09 mrad/s. The smallest non-zero
   rate seen was 0.0011 rad/s, exactly one step. At rest the raw gyro therefore cannot
   show drift below about 3.75 degrees per minute. A stationary drift test has to read the
   fused yaw over minutes, not the raw rate. At the robot's top turn rate of 0.30 rad/s
   (17 deg/s) the quantisation is 0.4 %, which is fine.
2. A frozen fused yaw is what the BNO055 does when still, because it re-trims its gyro bias
   at rest. Yaw reads 0.225 degrees after about an hour of uptime, which is encouraging, but
   only if the robot has not been moved in that time. I do not know that. 18.6 s says
   nothing about drift under motion.
3. **The accelerometer alone gives roll 9.96 and pitch 2.19 degrees. The fused quaternion
   gives 9.98 and 2.17.** They agree, so the filter is not at fault. Either the sensor is
   mounted tilted in the chassis, or the robot is on a slope or on its stand. The URDF puts
   `imu_link` at (0, 0, 0.05) with rpy 0, which is a placeholder. A sensor tilted 10 degrees
   about x measures yaw rate as cos(10 deg) = 0.985 of the true value, a 1.5 % scale error
   in the one quantity the EKF would use most. Fixable in the URDF once the real mounting
   rotation is measured, or by levelling the sensor. First, find out which one it is.
4. The configured covariances are far looser than what was measured: gyro 3e-5 against
   0.35 to 1.5e-6 measured, accelerometer 1e-2 against 1.4e-4. A filter that is told to
   trust the IMU 20 to 70 times less than it deserves will under-use it. Tune after the
   dynamic tests, not before.
5. The bridge parses `[IMUS,...]`, `[IMUC,...]` and `[IMUCAL,...]` and publishes nothing
   from them. The raw telemetry topic carries only wheel rows and `[OK,...]`
   acknowledgements. So whether the sensor has completed its self test, whether gyro and
   accelerometer are calibrated, and whether the I2C bus has been failing are all
   unknowable from the Pi today. The firmware keeps a calibration profile in flash (`<NS>`),
   so the hardware can be calibrated once and keep it, but nothing shows that it has been.

**Verdict.** The data path is healthy at rest. The health check is complete for what can
be judged without moving the robot. It is not complete for what matters most: sign
and scale of rotation, the accelerometer's per-axis offsets, long-run drift, behaviour with
the motors running, and calibration state.

**Dynamic checks still to do, each needing someone at the robot:**

| # | Test | Pass looks like | Written prediction |
|---|---|---|---|
| I1 | Robot on a known-level floor, repeat the 20 s capture | roll and pitch both under 1 deg | If the floor is level and the roll stays near 10 deg, the sensor is mounted tilted. 65 % |
| I2 | Rotate the robot by hand one full turn counter-clockwise seen from above, capturing | fused yaw increases by 360 +/- 3 deg, gyro z positive | sign right, scale within 1 % |
| I3 | Tilt the nose up, then the left side up | pitch and roll signs as REP-103 | signs right |
| I4 | Stationary, wheels idle, 10 minutes, read fused yaw | under 0.5 deg of change | 0.1 to 0.5 deg |
| I5 | Repeat I4 with the drive enabled and holding zero speed | no more than I4 plus 0.2 deg, accel noise under 3x | passes |
| I6 | Read calibration and self-test state (needs `<N?>` to the ESP32, which only the dashboard or your terminal can send) | gyro and accel at 3, self test 0x0F | gyro 3, accel not 3 until six-position calibration |
| I7 | Drive the 1 m straight, a 90 degree turn and a full circle, compare wheel yaw with IMU yaw | the ratio is steady across turns (a scale error) or jumps (slip) | steady, 0.97 to 1.03 |

I1 to I5 need no code. I6 needs a send path, and I7 needs a drive with the E-stop in reach.

**Configuration plan, once I1 to I7 are done** (this is the order, and it matches
`Year2_Autonomy_Research.md` section 6.2):

1. Fix the mounting. Level it, or measure the rotation and set `imu_joint` rpy in the URDF.
2. Make its state visible. Add a status publisher to `esp32_bridge` (`diagnostic_msgs`,
   or at minimum a latched string) for UP/DOWN, calibration, self test and I2C failures.
3. Calibrate and save (`<NS>`, drive disabled, gyro and accelerometer at 3).
4. Set the covariances from the measured noise, not placeholders.
5. Rewrite `ekf_params.yaml`. The committed draft was never run and has four problems:
   it fuses IMU linear acceleration (which leaks gravity through any tilt), it treats the
   IMU yaw as absolute (`imu0_relative: false`) although a sensor with no magnetometer
   reports yaw relative to power-on, it fuses absolute yaw from wheel odometry as well as
   the IMU (double counting), and it sets `publish_tf: true` while `odometry_publisher`
   already publishes `odom->base_link`. Only one node may publish that transform.
6. Run the EKF with `publish_tf: false` first, beside the wheel odometry, and compare on a
   drive. Switch the transform over only when it wins. Then remove it from
   `odometry_publisher`.

---

## 6. The gap analysis

Ranked by how much each gap can hurt. "Closes it" says what ends it.

### 6.1 Before any further autonomous drive (safety and validity)

| # | Gap | Evidence | Closes it |
|---|---|---|---|
| S1 | **The post-refactor Nav2 chain has not been validated.** The params header demands a footprint check against the live `published_footprint`, and the adapter's own docstring requires the stage 6 regression goals. Neither is on record. | [source, live] | Footprint query, then 1 m forward, 1 m sideways, 90 degree turn, each with a written prediction and the bag recording from the 1 Oct handoff |
| S2 | **The default `BackUp` recovery now reverses straight into the masked rear wedge.** Until 5 Oct it was a sideways strafe (the 30 Sep source read). With +X forward, `BackUp` commands negative `linear.x`, which is backwards, over 0.30 m, into the 107 beams nothing sees. The stock behaviour tree runs it as part of recovery. | [inferred from source read and the axis change] | A custom behaviour tree without `BackUp`, or a collision check source behind the robot, before the next goal that can fail |
| S3 | **No hardware E-stop, no bumper.** The only stop is the dashboard and the ESP32 latch, both through the Pi and the phone link. | [source, Hardware_Roadmap] | Latching NC mushroom in series with the motor supply, bumper strip into the same loop |
| S4 | **No battery or power measurement.** The firmware and the Pi know nothing about voltage or current. A flat pack mid-run is invisible. | [source] | INA226 module and a `BatteryState` publisher, per the roadmap |
| S5 | **The rear and everything under 0.275 m are unsensed.** | [source] | Rear DTOF LiDAR and the ToF ring from `Year2_Autonomy_Research.md` section 5 |
| S6 | **No health reporting.** No diagnostics aggregator, no IMU status, ESP32 `[TRIP,...]` lines go to a topic with no subscriber. | [live] | `diagnostic_updater` on the bridge and a summary on the dashboard |

### 6.2 Foundation shared by both modes

| # | Gap | Evidence | Closes it |
|---|---|---|---|
| F1 | **Pose is wheel dead reckoning alone.** | [live] | Section 5 plan: IMU, then EKF, then reopen scan matching with the EKF prior |
| F2 | **The IMU is unused, mis-mounted or unlevelled (10 degrees) and its state is invisible.** | [live] | Section 5 |
| F3 | **Compute margin is unmeasured.** The 30 Sep controller loop ran at 5.5 to 8.9 Hz against 20 requested. Nothing has been measured with Nav2, SLAM, AMCL and an EKF together. | [source, 1 Oct handoff] | `top` and `ros2 topic hz` during a run, after each addition |
| F4 | **Speed limit is 0.12 m/s** (wz 0.30 rad/s). Teleop is 0.15. This is a safe commissioning value and far below a working warehouse robot. | [source] | Raise only after F1 and S1 to S6, in steps |
| F5 | **The LiDAR is a single 2D sensor at about 47 % valid points, capped at 2.5 m by `scan_relay`.** A 2.5 m cap also limits what AMCL and the SLAM front end can match. | [source] | Section 6.5 of the Year 2 research: a better scanner |
| F6 | **No mode manager.** Mapping, Nav2 and calibration are separate subprocesses started by dashboard buttons, with the order rules ("map first, then Nav2", "never re-zero with Nav2 running") held in the operator's head. | [source] | A small supervisor that owns the modes and refuses illegal transitions |
| F7 | **Repo and Pi drift apart.** Twelve files had to be copied back today, and the 5 to 6 Oct work has no journal entry. | [live] | Pull Pi changes into git as part of every session, and write the 5 to 6 Oct entries |
| F8 | **Dozens of stray backups and copies on the Pi** (`phone_dashboard_backup_*.py`, `stage*_dl`, `axis_backup_*`, a `repo_sync` folder). Harmless, but they make "which file is live" a question. | [live] | One cleanup session with `tools/pi_clean.sh` (dry run first) |

### 6.3 Mode 1: navigating a saved map (and saving one)

The chain, with its state per link:

| Link | State | Gap |
|---|---|---|
| 1. Record a good map | Works through the dashboard MAP button. All 275 saved maps are small test maps. The newest (6 Oct) is 61 x 92 cells, 3.05 x 4.6 m, 90.6 % unknown. [live] No map of a real working area exists. | Record one 15 to 20 m loop with aisle-width stretches (the first practical task of Year 2 per the research). |
| 2. Judge it | `map_integrity.py` and the G4 criteria exist. The Year 2 note re-scopes the gate (walls in the right place, not unknown %). [source] | Apply the re-scoped gate to the commissioning map. |
| 3. Save it | The dashboard saves `.pgm`/`.yaml` into `aislebot_logs/` with a timestamp name. No `maps/` folder in use, no names, no pose graph (`serialize_map` is never called). [live, source] | Name and store maps in one place, save the pose graph with each, hash both. |
| 4. Convert it | Every map before 6 Oct 12:55 is in the **old frame**. The conversion is x_new = y_old, y_new = -x_old (nav2 header). [source] | A converter, or discard the old maps. Do not feed an old one to AMCL. |
| 5. Load and localise | `navigation.launch.py` (map server + AMCL + the Nav2 set) has **never run on hardware**. The `amcl` block has **no `scan_topic`**, so it would subscribe the raw mirrored `/scan`. The initial pose is hard-coded to (0, 0, 0). The dashboard has no handler for any of it. [source] | Add `scan_topic: /scan_reliable` and a laser range matching the 2.5 m cap; a dashboard action to pick a map, start the saved-map mode and set the initial pose; run G5. |
| 6. Plan and drive | Nav2 present and untested since the refactor (S1). NavFn tolerance is 0.5 m with `allow_unknown: true`, so a goal on or near an occupied cell can "succeed" up to 0.5 m away with nothing logged. [source] | Tolerance to 0.05 to 0.10 and `allow_unknown: false` in saved-map mode, as the Year 2 note says. |
| 7. Handle blockages | Default behaviour tree: replans at 1 Hz, first recovery clears the entire global costmap, then `Spin` 1.57 rad (which needs 1.2 m of width) and `BackUp` (S2). [source] | The custom tree and the four-hypothesis tests of section 4.7 of the Year 2 note. |
| 8. Arrive precisely | 5 cm / 2.9 degree goal checker. No docking (`opennav_docking` is installed but has no dock detector and no station). [source] | A detector at the station, late Year 2. |
| 9. Named locations | Written and unit-tested, never deployed. `locations.json` is absent. Locations carry no heading, approach type or tolerance. [live, source] | The three additions in section 4.5 of the Year 2 note, then G7. |
| 10. Use it daily | Nothing starts Nav2 at boot. Everything is an operator action, with the order rules above. | F6 |

**Smallest path to a first saved-map run** (no new hardware): fix `scan_topic`, record the
commissioning loop in the new frame, save it with a pose graph, start the saved-map mode by
hand, set the initial pose from the zero mark, and measure AMCL's convergence (G5). That
is a few sessions of work, and it is the same plan as the Year 2 note's G5 to G7.

### 6.4 Mode 2: autonomous exploration of unknown space

| Link | State | Gap |
|---|---|---|
| 1. A live pose that holds up | Wheel odometry alone. | F1 and F2. This is the binding constraint, because exploration drives the robot far from the zero mark on a map that only odometry holds together. |
| 2. A live map | slam_toolbox mapping, matching off, no loop closure. Works in the way it worked on 1 Oct (live-map tap-to-goal). | Reopen matching with the EKF prior and a cleaner scanner (G12). |
| 3. Decide where to go | **Nothing.** No frontier node is installed (`explore_lite` and `frontier_exploration` are absent) or written. The dashboard has no explore action. | Choose and add one (below). |
| 4. Get there safely | Nav2, untested since the refactor, `allow_unknown: true`, `track_unknown_space: true`, which is what frontier goals need. [source] | S1 and S2. |
| 5. Know when it is done, and stop | None. | Termination (no reachable frontier), a time and distance budget, return to the start. |
| 6. Survive failure | No blacklist for frontiers that fail, no stuck detection beyond the progress checker (0.10 m in 10 s), recovery as in S2. | Frontier blacklist and a bounded retry policy. |
| 7. Cover what the sensor cannot see | Rear wedge masked, nothing below 0.275 m. A frontier explorer regenerates frontiers behind the robot forever. | S5, and mask-aware frontier filtering until then. |
| 8. Finish with a usable map | `map_stop` saves a `.pgm`/`.yaml` and no pose graph. | As link 3 of mode 1. |

Three robot-specific cautions from the project's own findings, which I would carry into
the choice of explorer:

- Rotation in place maps nothing; wall-parallel translation maps well (journal). A stock
  explorer that spins to look will waste time and add odometry error.
- The 1.12 x 0.48 m footprint needs 1.06 m bare and 1.22 m padded to turn on the spot, so
  a frontier goal inside a narrow aisle may be reachable only by a path the body cannot
  follow (NavFn plans for a point, not the footprint).
- The 2.5 m range cap hides frontiers: a frontier is where known meets unknown at range, and
  with a short cap everything past 2.5 m stays unknown, so the robot sees frontiers
  almost everywhere.

My recommendation matches the Year 2 note: build **teach-and-repeat mapping** first, which
needs only what exists (`NavigateThroughPoses` plus a hand-driven route) and gives repeatable
maps, and treat frontier exploration as a later step on top of the EKF and a better scanner.
If you want exploration sooner, `m-explore-ros2` is the realistic starting point. Install it
into the workspace and wrap it with the three cautions above as filters, and expect to tune it
more than to use it.

---

## 7. Proposed order of work

IMU first, as you asked. Each step has a gate and a prediction written before it runs.

| Step | Work | Needs | Gate |
|---|---|---|---|
| 1 | IMU tests I1 to I5 on the stationary robot, at the robot | you at the robot, no drive | roll and pitch understood, 10 min drift under 0.5 deg |
| 2 | Add IMU status to the bridge and publish it (code, pushed through the `rw` gate) | nothing new | state visible in `/diagnostics` |
| 3 | IMU tests I6 and I7 (calibration, driven yaw ratio) | send path for `<N?>`, E-stop in reach | calibration at 3 where possible, ratio steady |
| 4 | Fix the mounting in the URDF (or the hardware), set covariances from the measurements | measured rotation | |
| 5 | Footprint check and the stage 6 regression goals (S1), custom tree without `BackUp` (S2) | E-stop in reach, bag recording | three goals within tolerance |
| 6 | EKF in parallel (`publish_tf: false`), compare, then switch the transform over | step 4 | heading error under 1 degree on the phantom-yaw route (G9) |
| 7 | Saved-map loop: AMCL fix, commissioning loop, pose graph, G5 to G7 | steps 5 and 6 | the Year 2 gates |
| 8 | Hardware safety and sensing (S3 to S5) in parallel with step 7 | parts | per the roadmap |
| 9 | Teach-and-repeat, then explorer | step 7 | to be written |

Steps 1 and 2 can start today. Step 2 is the first thing I can do end to end through the
gate (edit, test, push, build, restart, verify).

---

## 8. Questions only you can answer

1. Is the robot standing level on the floor right now, or on a stand? (Settles I1.)
2. Where is the BNO055 mounted, and in what orientation relative to the nose?
3. Which ESP32 firmware version is flashed? (Boot banner, or `<I>` from your terminal.)
4. What happened in the 6 Oct drives after the refactor? The Pi holds the CSVs, but no
   write-up exists, and it would tell us whether stage 6 was run.
5. Do you want the explorer in this phase, or teach-and-repeat first?

---

## Appendix. How this was gathered

All reads used the `ro` key through the gate (`ls`, `cat`, `stat`, `sha256sum`,
`ros2 topic/node/param`, `journalctl`, `uptime`, `free`, `df`, `lsusb`). The IMU capture
(`ssh nab-pi-ro "ros2 topic echo --no-arr /imu/data" > cap.txt`, 931 messages) was analysed by
`tools/imu_health.py`; the same two commands repeat the check for tests I1, I4 and I5. The
capture file itself was not kept. Source files read were the Pi's own copies, now in the repo: `nav2_params.yaml`,
`navigation.launch.py`, `esp32_bridge.py`, `phone_dashboard.py`, `scan_relay.py`,
`cmd_vel_axis_adapter.py`, `goal_pose_adapter.py`, `aislebot.urdf`, `ekf_params.yaml`, and
the live `slam_nodom.yaml` (hash `a6b75d36...`, equal to `system/slam_nodom_stageB.yaml`).
