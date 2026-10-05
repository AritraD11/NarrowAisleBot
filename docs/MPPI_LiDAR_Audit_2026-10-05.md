# MPPI and LiDAR settings audit, 5 Oct 2026

Read from the repo at commit `192038f`. Nothing here was checked on the live
Pi yet except what the earlier steps of this session already confirmed (the
three deployed files, their hashes, odometry at 0,0,0). Section 4 is the
live check that still has to be run.

There is no "perfect" MPPI to compare against. What can be checked is whether
each value is consistent with the measurements we have, and which values are
still guesses. That is what this lists.

## 1. MPPI (`nav2_params.yaml`, `controller_server.FollowPath`)

### Proven by a run

| Setting | Value | Evidence |
|---|---|---|
| Model | `Omni` | strafing and reversing are in scope, and the model samples vx, vy and wz together |
| Speed caps | 0.12 m/s both axes, 0.30 rad/s | the 2 Oct 0.6 m goal ran under them |
| Accel limits | ±3.0, 3.5 | 2 Oct: goal SUCCEEDED in 35 s with these live. With 0.3 / -0.5 / 0.6 the same goal crept at 4.4 mm/s and aborted. Now in the repo (`7472b5e`). |
| `odom_topic` | `/wheel_odom` | verified on the live node 30 Sep. Not the cause of the crawl. |
| Critics | Constraint, Cost, Goal, GoalAngle, PathAlign, PathFollow, Twirling | every one checked axis-agnostic against Nav2 source (header comment). PreferForward and PathAngle are left out on purpose. |
| `consider_footprint` | true | the footprint is 1.12 x 0.48 m, circumscribed radius 0.62 m. A circle would be wrong along the whole length. |
| Goal check | 5 cm, 0.05 rad | the 2 Oct run ended about 5 cm out in odometry |

### Consistent on paper, not yet measured

| Setting | Value | What is open |
|---|---|---|
| Horizon | 40 steps x 0.05 s = 2.0 s | only 0.24 m of lookahead at 0.12 m/s. Fine for a 3 m local costmap, but it was never tuned. |
| Batch | 300 | cut from 500 for the Pi (loop rate). No data on how much 300 costs in path quality. |
| Sampling std | 0.06 / 0.06 / 0.15 | about half the speed cap by design. Never swept. |
| `temperature` 0.3, `gamma` 0.015 | | 0.015 is the stock gamma. Temperature never swept. |
| Real acceleration | unknown | the robot's own limit is not measured. See 2. |

### Mismatches that are known

1. **The loop does not run at the rate the model assumes.** `controller_frequency`
   is 20 Hz and `model_dt` is 0.05 s. The measured loop is 5.5 to 14 Hz
   (G3, 7.5 to 13.7). MPPI's own guidance is that `model_dt` should equal the
   control period. This is the largest candidate for a better MPPI. The
   candidate change is 10 Hz, `model_dt` 0.1, `time_steps` 20 (same 2 s
   horizon, half the compute). It needs the loop rate measured during a drive
   first, and it is one change on its own.
2. **MPPI plans at 3.0 m/s^2 and the smoother caps the robot at 0.3.**
   `velocity_smoother` still has `max_accel [0.3, 0.3, 0.6]` and
   `feedback: OPEN_LOOP`. The goal worked, but MPPI is planning harder
   than the robot can follow. Measure real acceleration on a straight run
   before choosing the permanent value.
3. **`NavfnPlanner` `tolerance: 0.5`.** The controller judges success against
   the end of the path, so a blocked goal can "succeed" up to 0.5 m short.
   The first goal on 1 Oct failed planning five times even at 0.5, so
   tightening it needs its own test.
4. **Spin recovery stays in the behaviour tree.** The 92 degree turn on
   1 Oct was a Spin. In a 0.6 to 1.1 m aisle that hits a wall. Remove or
   limit it before any aisle test.
5. **BackUp strafes left** until the axis refactor lands.
6. **Progress checker floor is 10 mm/s** (0.10 m in 10 s). The final approach
   of the 2 Oct run was about 8 mm/s for a few seconds. A longer slow
   approach could abort falsely. Check against the bag.

## 2. LiDAR settings

### What is fixed now

`scan_relay.py` defaults: range cap 2.5 m, floor off, persistence 1 of 1
(off), rear mask on, mirror on, `yaw_offset` 270. Pinned by
`scan_relay_gate.py` section 13.

### Why 2.5 m is a reasonable choice, and what it costs

- Stationary scatter is 12 to 14 mm below 1.5 m, 22 to 32 mm at 1.5 to 2.0 m,
  and 55 to 200 mm past 2.5 m, where two captures disagreed
  (`Year2_Autonomy_Research.md`). The occupancy cell is 50 mm, so half a cell
  is 25 mm.
- **Nothing in the control chain can use more than 2.5 m.** MPPI looks 0.24 m
  ahead. The collision monitor looks 1.2 s ahead (0.14 m). The local costmap
  corner is 2.12 m away. Stopping from 0.12 m/s at 0.5 m/s^2 takes 1.4 cm.
  The cap only costs mapping reach, so maps need more driving.
- **The 2.0 to 2.5 m band was never measured.** The cap is the best fit to
  the data we have, not a proven edge. A 60 s parked capture through
  `scan_quality.py` and `scan_range_envelope.py` would settle it.
- Persistence stays off on evidence: on 15 Sep both persistence presets split
  the map into two disconnected regions, and RAW did not.
- No floor is set. Nothing measured supports one.

### Mismatches to clean up

| Where | Value | Issue |
|---|---|---|
| `slam_nodom_stageB.yaml` `max_laser_range` | 5.0 | no longer cuts anything, since the relay NaNs everything past 2.5 m |
| both costmaps `obstacle_max_range` / `raytrace_max_range` | 8.0 / 9.0 | same, nothing arrives past 2.5 m |
| dashboard `scan_trust_range` | 5.0 | the red/grey split is drawn at 5.0, so all points show red and none grey. `dashboard_scan_geometry.py` pins it equal to SLAM's range. |
| `ydlidar_params.yaml` `frequency` | 6.0 | the driver ignores it, the measured rate is 11.35 Hz. Documented, harmless. |

None of these change behaviour today, because the cut happens upstream. They
break the project's own rule that a range cap is only real if every consumer
agrees (`scan_range_envelope.py`, `CONSUMERS`). Setting SLAM, both costmaps and
the dashboard to 2.5 would make the numbers honest. That is a second deploy
and a change to the test that pins the dashboard value.

### An older known risk that is still open

The live SLAM file is `~/ros2_ws/slam_nodom.yaml`. The Stage G file
(`slam_nodom_stageB.yaml`, scan matching off) is deployed by hand under that
name. `install.sh` copies `system/slam_nodom.yaml`, which still has
`use_scan_matching: true` and `max_laser_range: 12.0`. A reinstall would
silently turn scan matching back on. The live node has to be checked.

## 3. Order of work this suggests

1. Run the live check in section 4 (needs MAP and NAV2 up).
2. Repeat the 0.6 m goal about 5 times with a bag. Read the loop rate from it.
3. Only then, one at a time: the 10 Hz / 0.1 s retune, the accel measurement,
   the Spin and tolerance changes.
4. Range consumers to 2.5, after the 2.0 to 2.5 m capture.

## 4. The live check

With MAP running and then NAV2 up, on the Pi:

```
ros2 param get /slam_toolbox use_scan_matching
ros2 param get /slam_toolbox max_laser_range
for p in range_cap_m range_floor_m persist_n persist_k mask_enabled; do echo -n "$p: "; ros2 param get /scan_relay $p; done
for p in ax_max ax_min ay_max ay_min az_max vx_max vy_max wz_max batch_size time_steps model_dt; do echo -n "$p: "; ros2 param get /controller_server FollowPath.$p; done
ros2 param get /controller_server controller_frequency
ros2 param get /controller_server odom_topic
```

Expected: scan matching `False`, SLAM range 5.0, relay 2.5 / 0.0 / 1 / 1 /
True, MPPI 3.0 / -3.0 / 3.0 / -3.0 / 3.5 / 0.12 / 0.12 / 0.3 / 300 / 40 /
0.05, controller 20.0, odom `/wheel_odom`.
