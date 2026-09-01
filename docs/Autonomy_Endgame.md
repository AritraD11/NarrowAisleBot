# The Autonomy Endgame — from here to "tap a point, it drives there"

**Written 28 Aug 2026.** Companion to `docs/Where_We_Stand.md`.
Target: **Saturday 5 September 2026** — a recorded run where a point is tapped
on the dashboard map and the robot drives there and stops, repeatably.

---

## Part 1 — What "entirely autonomous" actually means on this robot

### 1.1 It is three separate activities, and conflating them is the trap

| Phase | How often | What happens | Who does it |
|---|---|---|---|
| **Commission** | Once per site | Manual drive with SLAM running; save the map | Technician |
| **Teach** | Once per location | Drive to a spot, name it | Technician |
| **Operate** | Every day | Load saved map; AMCL localises; tap; drive | Operator |

**Today the project only ever does Commission, and then tries to Operate
inside it.** That is the single architectural mistake standing between the
current state and point-and-go, and it is not a tuning problem.

### 1.2 Why you cannot navigate reliably inside a live SLAM session

Live SLAM anchors the `map` frame wherever the robot happened to be at its
first scan, and then **keeps moving that frame for the whole session** —
that is what `map→odom` *is*. On 28 Aug it moved **11.08 m in total across
21.85 m of driving.**

So when you tap a point on the dashboard:

1. The pixel is converted to a coordinate **in the map frame as it exists at
   that instant**.
2. That coordinate is sent to `bt_navigator` as a fixed goal.
3. The map frame then **moves underneath the goal** while the robot drives.
4. The robot arrives at a floor tile that no longer corresponds to the pixel
   you tapped.

**This is the real explanation for "where I clicked and where the goal was
deployed are different."** The click→world maths is exact — verified to 1e-6
at device pixel ratios 1, 2 and 3 in headless Chromium. The *frame* the answer
is expressed in is what moves.

Two consequences follow, and both are load-bearing:

- **A saved map + AMCL is not a nice-to-have. It is the mechanism that makes
  a tapped point mean a fixed floor tile.** AMCL corrects the robot's pose
  *within* a fixed map. SLAM corrects the map's pose *around* a drifting robot.
  For navigation you want the first one.
- **Fixing the SLAM front end is still required** — not so navigation works,
  but so the *saved map is geometrically true*. A folded map produces a
  correct-looking navigation to the wrong physical place.

### 1.3 The claim to hold onto

> **Commissioning quality is a mapping problem. Operating quality is a
> localisation problem. They fail differently, they are fixed differently,
> and the project has been trying to solve the second by tuning the first.**

---

## Part 2 — The full chain, link by link

Every link must hold for a tap to become motion. This is the diagram to be able
to draw from memory in a review.

```
  finger on glass
        |
 [1] canvas pixel  --(pan/zoom/dpr inverse)-->  map-frame metres
        |
 [2] /goal_pose  (geometry_msgs/PoseStamped, frame_id: map)
        |
 [3] goal_pose_adapter   (yaw_offset_deg, axis convention §17.38)
        |
 [4] bt_navigator  --> behaviour tree: ComputePathToPose / FollowPath
        |                             + recoveries: spin, backup, wait
        |
 [5] planner_server (NavFn, Dijkstra)  <-- global_costmap
        |                                   <-- static layer   (THE SAVED MAP)
        |                                   <-- obstacle layer (/scan_reliable)
        |                                   <-- inflation layer (0.65 m)
        |
 [6] nav_msgs/Path
        |
 [7] controller_server (MPPI)          <-- local_costmap (rolling, 3x3 m)
        |                                   <-- obstacle layer (/scan_reliable)
        |
 [8] /cmd_vel_nav --> velocity_smoother --> collision_monitor --> /cmd_vel
        |
 [9] cmd_vel_axis_adapter  (§17.38 body-frame convention)
        |
[10] esp32_bridge  --(serial)-->  ESP32: inverse kinematics + 4x PID @ 50 Hz
        |
[11] wheels --> encoders --> odometry_publisher --> /odom
        |
[12] TF:  odom -> base_link       (continuous, never jumps)
[13] TF:  map  -> odom            (discontinuous; SLAM or AMCL owns it)
```

### 2.1 Where each link stands

| Link | State | Failure mode if it breaks |
|---|---|---|
| 1 | ✅ exact to 1e-6 | Goal lands at the wrong pixel |
| 2–3 | ✅ working | Goal rotated 90°, or mirrored |
| 4 | ✅ working | `Goal aborted`, infinite recovery loop |
| 5 | 🟡 working at 1.25 Hz | Stale paths; robot follows a plan for a world that moved |
| 6 | ✅ | — |
| 7 | 🟡 working at 7.5–13.7 Hz | Jerky control, overshoot, progress-checker aborts |
| 8 | 🟡 stale-scan warnings | Safety stop fires late, or spuriously |
| 9–11 | ✅ measured exact | Wrong direction of travel |
| 12 | ✅ 1.27% over 21.85 m | Slow, smooth accumulation of error |
| 13 | 🔴 **11.08 m of correction over 21.85 m** | **Pose jumps; goals move; the map folds** |

**Twelve of thirteen links are sound.** The project's entire remaining
difficulty is link 13, plus the CPU starvation degrading 5, 7 and 8.

---

## Part 3 — The seven gates to point-and-go

Each gate has a **pass criterion that is a number**, not an impression. Do not
proceed past a gate on "it looked better."

| Gate | Pass criterion | Instrument |
|---|---|---|
| **G1 — Deployment truth** | Every pending file hashed on arrival; every changed param confirmed by `ros2 param get` on the live node | `sha256sum`, `ros2 param get` |
| **G2 — Angular gate closed** | On a repeat of the 1047 s traverse: **no correction > 0.30 m**, and the largest heading step **< 10°** | `run_analyzer.py` |
| **G3 — CPU headroom** | Control loop **≥ 15 Hz** sustained; zero TF-extrapolation errors in a 5-minute window | `top`, node logs |
| **G4 — An accepted map** | `map_integrity.py` returns **not `FOLDED`**; **D2 doubled walls < 1.0%**; unknown < 50%; return-to-mark **< 0.15 m** | `map_integrity.py` + a tape measure |
| **G5 — AMCL alive** | `navigation.launch.py` reaches `Managed nodes are active` on a **saved** map; `/amcl_pose` covariance converges after one manual drive-around | node log, `ros2 topic echo /amcl_pose` |
| **G6 — Point-and-go** | 5 consecutive tapped goals, each `Goal succeeded`, each within **0.15 m / 10°** of the tapped point measured on the floor | dashboard + tape measure |
| **G7 — Named locations** | 3 taught locations recalled after a **full power cycle**, each reached within 0.15 m | location library JSON |

**G4 is the gate. Everything before it is preparation; everything after it is
comparatively easy engineering.**

---

## Part 4 — The week, day by day

Today is **Friday 28 August**. Demo is **Saturday 5 September**. Eight working
days. This plan is deliberately front-loaded: the hard, uncertain work happens
first, so there is slack at the end.

> **Standing rules for the whole week, from this project's own scar tissue:**
> 1. **One parameter at a time.** §17.25 changed six at once and paid for three
>    sessions.
> 2. **Write the prediction down before the test.** A prediction that can fail
>    is worth more than an explanation that cannot.
> 3. **Verify against the live node, never the file.**
> 4. **Hash every file on arrival, per file, never per batch.**
> 5. **Never fix an axis complaint in the dashboard.** That is what hid §17.38
>    for two weeks.

---

### Day 0 — Friday 28 Aug (today, no lab)

Reading only. `Where_We_Stand.md`, this document, and `APS_Study_Guide.md`
§1–§3. Nothing to deploy.

---

### Day 1 — Saturday 29 Aug: clear the debt, then Stage D

**Objective: G1 and G2.**

#### 1a. Deploy all four pending files

On **Windows** (the Pi has no uplink — it hosts its own AP):

```powershell
cd "C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download"
$B = "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike"

curl.exe -sSL --retry 3 --retry-all-errors -o phone_dashboard.py  "$B/src/mecanum_robot/mecanum_robot/phone_dashboard.py"
curl.exe -sSL --retry 3 --retry-all-errors -o wheel_forensics.py  "$B/tools/wheel_forensics.py"
curl.exe -sSL --retry 3 --retry-all-errors -o aislebot.urdf       "$B/src/mecanum_robot/urdf/aislebot.urdf"
curl.exe -sSL --retry 3 --retry-all-errors -o slam_nodom.yaml     "$B/system/slam_nodom_stageB.yaml"

scp phone_dashboard.py aritra@10.42.0.1:~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
scp wheel_forensics.py aritra@10.42.0.1:~/tools/wheel_forensics.py
scp aislebot.urdf      aritra@10.42.0.1:~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf
scp slam_nodom.yaml    aritra@10.42.0.1:~/ros2_ws/slam_nodom.yaml
```

⚠ **The destination filename for the config is `slam_nodom.yaml`, not
`slam_nodom_stageB.yaml`.** `mapping_full.launch.py:66` loads the former. Land
it under the wrong name and the old file keeps running, silently.

On the **Pi** — hash each one separately, and check nothing has a password
stuck on the end of the filename:

```bash
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
# 5b30a91dc7614d73848357bcedd66771cb332eddd12d1de06ed58dce47ad43d1
sha256sum ~/tools/wheel_forensics.py
# 27858ce417f3f39e56db3b87b31644fc11a9292aba7247f1c8d9a2d80bf96236
sha256sum ~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf
# ea6619ff3999b856fc3c1632041bd3a151eb8732f9c782d90207831ce1b0a81c
sha256sum ~/ros2_ws/slam_nodom.yaml
# 0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f

ls -la ~/tools/ ~/ros2_ws/*.yaml

cd ~/ros2_ws && colcon build --packages-select mecanum_robot --symlink-install
sudo systemctl restart aislebot.service

python3 ~/tools/wheel_forensics.py --selftest      # 6 tests, all must PASS
```

**STOP MAP → park on the mark → ZERO (two taps) → MAP.** Parameters only
reload on a fresh bring-up. Then, against the **live node**:

```bash
ros2 param get /slam_toolbox coarse_search_angle_offset            # 0.175
ros2 param get /slam_toolbox correlation_search_space_dimension    # 0.3
```

If either reads a stock value, **stop**. The file did not take. Nothing after
this point means anything.

#### 1b. The Stage D A/B — a repeat, not a new experiment

Re-run **the same traverse as 28 Aug**: perimeter of the junction, nose
leading, rotating at every corner, 0.5–1.5 m off the walls, slow, one
direction, closing at the mark. Aim for **15–18 minutes**. Longer beats
shorter.

```bash
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph_stageD.jsonl
```

**Prediction table — fill in the right column before you drive, not after:**

| Outcome | Reading | What to do |
|---|---|---|
| Largest correction **< 0.30 m**, largest heading step **< 10°** | The angular gate was the lever. **G2 passes.** | Straight to Day 2 |
| Corrections reappear **pinned near 0.30 m** with heading steps near **10°** | The window clamped the symptom again. The matcher still *prefers* to disagree with odometry | Stage E: `angle_variance_penalty` 1.2 → 0.6 |
| **Track lost at a corner** — pose freezes or the map tears at a rotation | Cut too far below the prior's real uncertainty | `coarse_search_angle_offset` → 0.25 (14.3°), which is above `minimum_travel_heading` |
| No change at all | The angular window is not the gate; the lever-arm model described a coincidence | Stage E directly, and re-open `distance_variance_penalty` |

Then:

```bash
python3 ~/aislebot_logs/run_bundle.py --latest --folder ~/aislebot_logs
python3 ~/tools/wheel_forensics.py --csv ~/aislebot_logs/stageD_wheels.csv
```

**Physically park the robot back on the zero mark and read three things**
before you leave:

```bash
ros2 run tf2_ros tf2_echo map base_link      # SLAM's opinion
ros2 run tf2_ros tf2_echo odom base_link     # odometry's opinion
ros2 run tf2_ros tf2_echo map odom           # the correction between them
```

Those three numbers are the row that goes in the journal. On 28 Aug they were
**0.477 m / 0.229 m / 0.271 m**. Anything under **0.15 m** on the first one is
a pass.

---

### Day 2 — Sunday 30 Aug: CPU headroom

**Objective: G3.** This day exists because a control loop at 7.5 Hz makes every
subsequent measurement noisier, and because it is the cheapest large win
available.

Measure first:

```bash
top -b -n 1 -o %CPU | head -20
uptime                                    # load average vs 4 cores
vcgencmd measure_temp && vcgencmd get_throttled   # 0x0 = never throttled
```

Then apply, **in this order, measuring after each** (one change at a time):

| # | Change | Where | Expected saving |
|---|---|---|---|
| 1 | `batch_size` 1000 → 400 | `nav2_params.yaml`, `FollowPath` | Largest single MPPI saving; MPPI cost is linear in batch × horizon |
| 2 | `map_update_interval` 1.0 → 2.0 | `slam_nodom.yaml` | Occupancy-grid raster is a fixed periodic cost |
| 3 | Global costmap `update_frequency` → 1.0, `publish_frequency` → 0.5 | `nav2_params.yaml` | Publishing a full costmap is pure overhead when only the dashboard reads it |
| 4 | `enable_interactive_mode: false` | already set | — |
| 5 | Drop the dashboard's map-refresh rate while navigating | `phone_dashboard.py` | Serialising a grid over WebSocket is not free |

```bash
ros2 param set /controller_server FollowPath.batch_size 400
ros2 param get /controller_server FollowPath.batch_size
```

**Pass criterion:** control loop ≥ 15 Hz sustained, zero TF-extrapolation
errors in a 5-minute window.

> **Note on a warning that is not a bug.** `controller_server` prints
> `Parameter goal_checker.xy_goal_tolerance not found`. That is MPPI's
> `ParametersHandler` being noisy — the same shape as
> `controller_server.verbose not found`. The values **do** take. Proven: 68 s
> with zero progress failures where one had previously fired every 10 s. Do
> not chase it.

---

### Day 3 — Monday 31 Aug: the commissioning map

**Objective: G4. This is the day the project turns.**

1. **STOP MAP** if anything is running. Discard it.
2. Park on the physical zero mark. **ZERO** (two taps — must precede MAP).
3. **MAP**, then **VIEW**, and keep VIEW open for the whole run. A fold is
   visible as it happens; catching it at minute 4 saves 15 minutes.
4. Drive the **perimeter, nose leading, rotating at every corner**.
5. **MAP** again to stop. **This is the only action that saves the map** —
   `stop_mapping()` shells out to `map_saver_cli` before tearing down. A
   `systemctl restart`, a reboot or a crash loses it entirely.

**Why rotation and not a square.** The rear 90° is permanently blind behind
the mast — 107 of 430 beams masked NaN. A non-rotating square keeps that cone
pointed at the same *world* direction for the whole run, so one whole side of
the room is never observed. That is why `run_20260827_140207` came back **87%
unknown** and `SUSPECT`.

Then grade it, and be willing to throw it away:

```bash
python3 ~/tools/map_integrity.py ~/aislebot_logs/run_<TS>.pgm ~/aislebot_logs/run_<TS>.yaml
```

**Accept only if:** verdict is not `FOLDED`, **D2 doubled walls < 1.0%**,
unknown < 50%, and the physical return-to-mark is **< 0.15 m**.

**If it fails, drive it again.** Budget for three attempts today. A bad map
poisons every day after it, and Day 4 has no meaning without a good one.

Once accepted, promote it out of the run folder so it stops being one run
among many:

```bash
mkdir -p ~/maps
cp ~/aislebot_logs/run_<TS>.pgm  ~/maps/lab_commission_v1.pgm
cp ~/aislebot_logs/run_<TS>.yaml ~/maps/lab_commission_v1.yaml
sed -i 's|^image:.*|image: lab_commission_v1.pgm|' ~/maps/lab_commission_v1.yaml
cat ~/maps/lab_commission_v1.yaml
sha256sum ~/maps/lab_commission_v1.*
```

**Photograph the zero mark with the robot on it, and tape-measure its offset
from two walls.** That photograph is the ground truth for every later claim,
and it costs thirty seconds today and cannot be recovered later.

---

### Day 4 — Tuesday 1 Sep: AMCL's first breath

**Objective: G5.** This code has never executed. Expect it to fail the first
time; that is the point of doing it four days early.

**Before launching anything**, check the one known hazard:

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
```

If the plugin XML names `nav2_amcl::OmniMotionModel`, then
`nav2_params.yaml`'s `robot_model_type: "omnidirectional"` is the pre-Galactic
bare-string form and **will abort the entire `lifecycle_manager` bringup** —
the same all-or-nothing failure §17.17 already hit once. Fix it to the full
class name before the first launch.

```bash
ros2 launch mecanum_navigation navigation.launch.py \
    map:=/home/aritra/maps/lab_commission_v1.yaml 2>&1 | tee ~/aislebot_logs/amcl_first.log
```

Wait for `Managed nodes are active`. Then set the initial pose (park on the
zero mark first), and drive **manually** around the room for two minutes while
watching:

```bash
ros2 topic echo /amcl_pose --once
ros2 topic hz /amcl_pose
ros2 run tf2_ros tf2_echo map base_link
```

**Pass criterion:** the covariance diagonal **shrinks** as the robot drives and
sees walls, and `map→base_link` stays smooth — no 0.3 m jumps. AMCL's
corrections should be centimetres, because it is correcting the robot inside a
fixed map rather than rebuilding the map.

**This is also the honest comparison the report needs**: the same physical
drive, once under live SLAM and once under AMCL on a saved map, with the
return-to-mark measured both times.

---

### Day 5 — Wednesday 2 Sep: point-and-go

**Objective: G6.**

First, fix the tolerance that cannot be met:

```bash
ros2 param set /controller_server goal_checker.xy_goal_tolerance 0.12
ros2 param set /controller_server goal_checker.yaw_goal_tolerance 0.20
ros2 param get /controller_server goal_checker.xy_goal_tolerance
```

`0.02` is 2 cm — smaller than the pose jitter of the estimate itself. **A
controller cannot converge on a target tighter than its own noise floor.**
0.12 m is defensible: it is under a quarter of the robot's width and well
inside any aisle clearance.

Then five tapped goals in one session, **without dragging** (dragging sets a
goal *orientation*, which costs the robot ~50 extra seconds turning its nose
89° before it may declare success — that is what the first attempts on 27 Aug
were fighting).

For each: mark the tapped point on the floor with tape *before* sending it,
then tape-measure where the robot actually stops.

| # | Tapped (m) | Reached (m) | Error (m) | Heading err | Time | Result |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

**Pass: 5/5 `Goal succeeded`, all within 0.15 m.** That table is a figure in
the report exactly as it stands.

---

### Day 6 — Thursday 3 Sep: named locations

**Objective: G7.** Pure software, no hardware risk — which is why it is here,
after the risky days.

Minimum viable location library, in `~/locations.json` on the Pi:

```json
{
  "map": "lab_commission_v1",
  "locations": [
    {"name": "Home",     "x": 0.00, "y": 0.00, "yaw": 0.00},
    {"name": "Aisle A",  "x": 0.00, "y": 0.00, "yaw": 0.00},
    {"name": "Staging",  "x": 0.00, "y": 0.00, "yaw": 0.00}
  ]
}
```

Two dashboard endpoints, both small:

- `POST /save_location {name}` — reads the live `map→base_link` transform and
  appends the row. **Nothing is measured by hand; the robot is driven to the
  spot and the spot is named.**
- `POST /goto_location {name}` — looks the row up and publishes it as a
  `/goal_pose`. Reuses the entire existing goal path.

Guard on the `map` field: if the loaded map name does not match, **say so in
the UI**. Re-mapping the site invalidates taught locations, and that should be
surfaced rather than hidden.

**Pass: teach 3 locations, full power cycle, recall all 3 within 0.15 m.** The
power cycle is the whole test — it is what proves the coordinate frame is
genuinely fixed and not an artefact of one session.

---

### Day 7 — Friday 4 Sep: rehearsal

No new code. No new parameters. Run the demo end to end, twice, with the
camera in the position it will be in on Saturday.

```bash
python3 ~/aislebot_logs/run_bundle.py --latest --folder ~/aislebot_logs
python3 ~/tools/wheel_forensics.py --csv ~/aislebot_logs/rehearsal_wheels.csv
```

Write down the failure you are most afraid of, and rehearse the recovery for
that one specifically.

---

### Day 8 — Saturday 5 Sep: the run

Record: the tap, the plan appearing, the drive, the stop, the tape measure.
One continuous shot beats five clips.

Capture for the report: `run_bundle` JSON, the wheel CSV, the map integrity
report, the map PNG, and the tapped-vs-reached table.

---

## Part 5 — Fallback ladder

If a day fails, **do not spend the next day on it.** Descend one rung and
protect the demo.

| Rung | Demo you can still give | Requires |
|---|---|---|
| **A — full** | Tap a name → robot drives there, on a saved map, after a power cycle | G1–G7 |
| **B — point-and-go** | Tap a point on a saved map → robot drives there | G1–G6 |
| **C — live-SLAM point-and-go** | Tap a point during a mapping session → robot drives there | G1–G3, G6. **This already worked on 27 Aug** |
| **D — scripted autonomy** | `nav_goal.py` sends a fixed goal; robot plans and drives it | Already works today |

**Rung C is already banked.** Two `Goal succeeded` on 27 Aug, 25.9 s and
21.0 s. Whatever else happens this week, there is a working autonomous
navigation demo in hand — which means the week can be spent going for A
without risking having nothing.

Say the caveat out loud when demonstrating rung C: *the robot completed its
goals; it did not return to (0,0), because the map frame was still moving.*
That is a more impressive thing to say than to hide, and it is true.

---

## Part 6 — Beyond this week

Ordered by what unlocks the most, not by difficulty.

1. **Stage E — `angle_variance_penalty` 1.2 → 0.6, `distance_variance_penalty`
   0.7 → 0.4.** Both were raised on the §17.21 premise that "wheel odometry
   over-reports strafe by 25%." **That premise is now false** — it predates
   `lateral_scale`, and the same odometry has since closed a 4 m path to 1.1%.
   The config currently instructs the matcher to distrust its best input.
2. **`robot_state_publisher` + URDF on the real robot** so `/robot_description`
   exists outside the sim.
3. **The IMU decision.** 10.53° over 18 m is the odometry ceiling and no amount
   of SLAM tuning moves it. Galati et al. report ~88% heading-drift reduction
   from fusion. **Deliberately shelved** — reopen only when the operator does.
4. **`twist_mux` or a `use_joystick:=false` guard.** `joy_to_aislebot.py`
   publishes `/cmd_vel` on idle-gamepad zeros. Inert today (no gamepad
   attached) but it would fight Nav2 at 25 Hz vs 20 Hz the moment one is
   plugged in.
5. **Multi-goal missions** — `nav2_waypoint_follower` is already configured and
   has never been used.
6. **Docking / last-metre alignment.** AprilTags for the cargo application.
