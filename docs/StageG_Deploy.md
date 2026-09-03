# Stage G — deploy, verify, drive, score

**Written 3 Sep 2026, before the drive.** Every prediction in §3 is
registered here in advance, per standing rule #2: a prediction that can
fail is worth more than an explanation that cannot.

Branch: `claude/autonomous-vehicle-hardware-btgtga`, cut from
`claude/narrowaislebot-goal-obstacle-avoidance-f2t3aa` (`1cf9392`).

---

## 1. What changes, and the measurement behind each

Six values. Nothing else.

| # | File | Parameter | From | To |
|---|---|---|---|---|
| 1 | `ydlidar_params.yaml` | `frequency` | 10.0 | **6.0** |
| 2 | `ydlidar_params.yaml` | `range_max` | 12.0 | **10.0** |
| 3 | `slam_nodom_stageB.yaml` | `max_laser_range` | 10.0 | **5.0** |
| 4 | `slam_nodom_stageB.yaml` | `use_scan_matching` | true | **false** |
| 5 | `nav2_params.yaml` | `xy_goal_tolerance` | 0.02 | **0.05** |
| 6 | `nav2_params.yaml` | `batch_size` | 500 | **300** |

Plus one feature: a live LiDAR overlay on the dashboard, carrying the
valid/flicker statistics §17.45 could only recover offline.

### 1.1 Why, in one paragraph each

**#1, 6 Hz.** Points per revolution is `sample_rate / frequency`, so
10 Hz gives 500 and 6 Hz gives 833. **+67% angular density, free.**
§17.44 showed cumulative correction invariant to 2% across three
parameter sets (2.80 / 2.85 / 2.86 m) — every one of them a *search*
parameter. §17.45 then measured the input: 74.8–78% of rays flip
valid/invalid between consecutive scans **with the robot stationary**.
A search cannot be tuned over an objective function that moves. Density
is an input-side lever and no input-side lever has ever been pulled.

> **Recommendation overruled, and recorded.** 7.0 Hz was recommended:
> it is the datasheet nominal and 6 Hz sits nearer the bottom of the
> motor's range, where speed ripple becomes angular error distributed
> differently every sweep. That is a HYPOTHESIS, never measured on this
> unit. The operator chose 6.0 for the extra density. §4's rate check
> settles it either way, and the fallback to 7.0 is one line.

**#2, `range_max: 10.0`.** A correctness fix, open since §17.6. The
X4 Pro is rated 0.12–10 m; 12.0 was inherited from the originally
planned RPLiDAR A1. Readings past 10 m were noise carrying a number,
published into `/scan_reliable`, and therefore counted in `scan_quality.py`'s
own statistics.

**#3, `max_laser_range: 5.0`.** This is a triangulation scanner, so ray
error grows with the *square* of distance: ~32 mm at 1.6 m, ~100 mm at
5 m, ~200 mm at 10 m. Measured corrections are 26–163 mm (§17.49) — the
same order as a single long ray's error. The **measured median scan range
in this lab is 1.6 m**, so a 5 m cap discards a small tail here and would
discard most of the cloud in an open warehouse aisle. That asymmetry is
exactly why this is being validated in the lab first.

**#4, `use_scan_matching: false`.** The headline. Over the same 21.85 m
drive: wheel odometry alone closed **0.229 m** (1.27%, on spec); odometry
plus this front end closed **0.706 m**. The expensive estimator is 3×
worse than the cheap one. Turning it off is not a workaround; it is
selecting the better of two measured estimators.

**#5, `xy_goal_tolerance: 0.05`.** 0.02 asked the controller to converge
inside its own noise floor while `map→odom` stepped 26–163 mm per node.
Deliberately not Appendix B.7's proposed 0.12 — that number was written
while the map frame was jumping 150–370 mm, and 0.12 leaves only 3 cm of
margin against G6's 0.15 m gate. 0.05 leaves 10 cm and is 3× the
demonstrated 1.7 cm cross-track capability.

**#6, `batch_size: 300`.** `nav2_params.yaml` already named 300 as the
first response if "Control loop missed its desired rate" appeared. It
appeared: 7.5–13.7 Hz against 20 requested, planner 1.25 against 5.
Taking the file's own advice.

---

## 2. Deploy

The Pi hosts its own AP and has no uplink, so files go Windows → `scp`.

### 2.1 Fetch on Windows

```powershell
cd "C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download"
$B = "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/autonomous-vehicle-hardware-btgtga"

curl.exe -sSL --retry 3 --retry-all-errors -o ydlidar.yaml         "$B/system/ydlidar_params.yaml"
curl.exe -sSL --retry 3 --retry-all-errors -o slam_nodom.yaml      "$B/system/slam_nodom_stageB.yaml"
curl.exe -sSL --retry 3 --retry-all-errors -o phone_dashboard.py   "$B/src/mecanum_robot/mecanum_robot/phone_dashboard.py"
curl.exe -sSL --retry 3 --retry-all-errors -o nav2_params.yaml     "$B/src/mecanum_navigation/config/nav2_params.yaml"
curl.exe -sSL --retry 3 --retry-all-errors -o verify_live_config.sh "$B/tools/verify_live_config.sh"
```

### 2.2 Copy to the Pi

⚠ **`slam_nodom_stageB.yaml` lands as `slam_nodom.yaml`.**
`mapping_full.launch.py:63` loads the latter. Wrong name, old file keeps
running, silently.

⚠ **The LiDAR params go to TWO places.** `mapping_full.launch.py:71`
reads `get_package_share_directory('ydlidar_ros2_driver')/params/ydlidar.yaml`
— the **install** tree, not `src/`. Copying only to `src/` changes nothing
until that third-party package is rebuilt, and copying only to `install/`
is reverted by the next rebuild. Do both.

```bash
scp ydlidar.yaml          aritra@10.42.0.1:~/ros2_ws/src/ydlidar_ros2_driver/params/ydlidar.yaml
scp ydlidar.yaml          aritra@10.42.0.1:~/ros2_ws/install/ydlidar_ros2_driver/share/ydlidar_ros2_driver/params/ydlidar.yaml
scp slam_nodom.yaml       aritra@10.42.0.1:~/ros2_ws/slam_nodom.yaml
scp phone_dashboard.py    aritra@10.42.0.1:~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
scp nav2_params.yaml      aritra@10.42.0.1:~/ros2_ws/src/mecanum_navigation/config/nav2_params.yaml
scp verify_live_config.sh aritra@10.42.0.1:~/tools/verify_live_config.sh
```

Never put the password on the command line. It once got appended to an
`scp` destination.

### 2.3 Hash every file on arrival — per file, not per batch

```bash
sha256sum ~/ros2_ws/src/ydlidar_ros2_driver/params/ydlidar.yaml
# e201ea2c91c636745dbbee846e54e6d2a40c10449a658cad6acb8c3ff48ef092
sha256sum ~/ros2_ws/install/ydlidar_ros2_driver/share/ydlidar_ros2_driver/params/ydlidar.yaml
# e201ea2c91c636745dbbee846e54e6d2a40c10449a658cad6acb8c3ff48ef092
sha256sum ~/ros2_ws/slam_nodom.yaml
# b10a13839759764c0a41af654f17e064e4e8e5532f5aa4e4e27f8ab0c8138e96
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
# 597fa120021862e4757ce7a5d5c0f57a73d5cc67f926c4f3525cc7639843b778
sha256sum ~/ros2_ws/src/mecanum_navigation/config/nav2_params.yaml
# 7d9adfac6aee2035538bd5b1f6eaa470e3e11e84f68e6fd25cd8685edd54f162
sha256sum ~/tools/verify_live_config.sh
# a5353cdb15fcab057277675228cea53e0d3c3353892558f9291ade5592767c82
```

A mismatch here means the transfer is the bug. Do not go on.

### 2.4 Build

`slam_nodom.yaml` and `ydlidar.yaml` need no build. The dashboard and
`nav2_params.yaml` do.

⚠ **Do not use `--symlink-install` on `mecanum_navigation`.** It was
previously built without symlinks, colcon does not reconcile the two
modes, and the result is `PackageNotFoundError` at runtime while the build
prints `Summary: 2 packages finished` (§17.49).

```bash
cd ~/ros2_ws
colcon build --packages-select mecanum_robot mecanum_navigation
source install/setup.bash
```

If `mecanum_navigation` misbehaves:

```bash
rm -rf build/mecanum_navigation install/mecanum_navigation
colcon build --packages-select mecanum_navigation
```

then **relaunch what you deployed**.

---

## 3. Predictions, registered before the drive

Score every row. A wrong prediction is a result, not a failure.

### 3.1 Immediate, before driving a single metre

| Observation | Prediction |
|---|---|
| `ros2 topic hz /scan` | 6.0 Hz ± 0.3, **deviation tight** |
| Beams per scan | ~833 (5000 / 6) |
| Dashboard VALID, parked | 40–55% |
| Dashboard FLICKER, parked | **60–80%**, on a robot that is not moving |
| `map → odom` at bringup | identity, and it **stays** identity |

The FLICKER row is the one to photograph. It is §17.45's central finding,
readable live for the first time.

### 3.2 During the drive

| Observation | Prediction |
|---|---|
| `run_analyzer.py` corrections | **≈ 0**. The 0.175 m metronome stops |
| Dashboard trail | smooth. The spikes *were* the corrections |
| JUMPS counter | 0, or only at loop closures |
| Control loop rate (if Nav2 up) | ≥ 15 Hz, from batch_size 300 |

### 3.3 The map, scored on all four G4 criteria

| Criterion | Gate | Prediction |
|---|---|---|
| `map_integrity.py` verdict | not `FOLDED` | **passes** |
| D2 doubled walls | < 1.0% | **improves sharply** — doubling is what a pose jump between two passes of one wall looks like |
| Unknown | < 50% | **worse than 82.9%** — the one that degrades |
| Return to mark | < 0.15 m | **~0.13 m** on a ~10 m perimeter (1.27% of path) |

### 3.4 What would falsify the whole model

**If the map still grades `FOLDED` with scan matching off**, then the
front end was never the cause and five sessions of suspicion pointed the
wrong way. That is the largest finding this project could produce right
now. Record it with the same care as a success.

---

## 4. Verify against the LIVE nodes, never the files

§17.32 is why this step is not optional: a config committed on 19 Aug
never reached the Pi, and three days of drives were reasoned about
parameters that were never active.

```bash
bash ~/tools/verify_live_config.sh
```

It checks all six values against the running nodes, measures the actual
scan rate and beam count, and refuses to clear you to drive on a mismatch.

**The rate check is the one that can surprise you.** `frequency: 6.0` is a
*request*. `support_motor_dtr` is false, so the driver may not command the
motor at all and the hardware can ignore it. If the script reports ~10 Hz,
the density gain did not happen and every prediction in §3 resting on 833
points is void.

It also settles a contradiction in our own docs: `Stack_Assessment` §3A
computes 5000/f (833 at 6 Hz) while `README.md` states ~1258 pts/scan at
~11.5 Hz, which implies ~14.5 kHz rather than 5. Both cannot be right.
Whichever loses, fix that document before citing it again.

---

## 5. The drive

1. Park on the physical zero mark. **Tape-measure and photograph it** —
   B.7 has wanted this ground truth for a week and it costs thirty seconds
   and cannot be recovered afterwards.
2. `ZERO` the odometry.
3. Start mapping. **Do not run Nav2** — a manual drive gives slam_toolbox
   a whole Pi instead of a starved one, for free.
4. Open the map view. Watch VALID and FLICKER for **60 seconds without
   touching anything**. Screenshot.
5. Drive the perimeter with **rolling turns**. Never rotate in place:
   §17.44 measured 714° of in-place rotation producing 43 occupied cells
   and zero corrections. Corners are taken while still moving.
6. Return to the mark. Tape-measure the error before stopping the session.
7. Save the map.

Do not restart `mapping_full.launch.py` mid-run. Restarting re-plants the
map origin wherever odometry currently is (§17.18/§17.19).

---

## 6. Scoring

```bash
python3 ~/tools/map_integrity.py  <map.pgm> <map.yaml>
python3 ~/tools/run_analyzer.py   <run.csv>
python3 ~/tools/scan_quality.py                 # the 6 Hz input, measured
```

Fill in §3's tables with what actually happened, including the rows that
went the wrong way. Then, and only then, decide the next single variable.

---

## 7. If it works, the next three questions, in order

1. **Turn scan matching back on** against this same improved input. Does
   the matcher now *beat* odometry instead of losing to it? That is the
   clean A/B this stage is built to enable, and `max_laser_range` is one
   line away from 10.0 for the same comparison.
2. **`resolution: 0.05 → 0.03`.** A 250 mm chassis in narrow aisles wants
   finer cells. Costs CPU. One variable, after there is a map to compare
   against.
3. **AMCL, which has never executed once.** `robot_model_type` is already
   corrected to `nav2_amcl::OmniMotionModel`, and the launch split
   (`sensors.launch.py`) exists. It needs a saved map, which is what this
   stage is for.
