# Next Session Kickoff — the obstacle test, and AMCL's first breath

Self-contained. Assumes no memory of the previous conversation — everything
needed is here or in the repo (`docs/Stack_Assessment_2026-09-01.md`,
`docs/Where_We_Stand.md`, `docs/Axis_Convention.md`,
`docs/Research_Journal.md`, `docs/Important_Commands.md`).

**Rewritten 1 Sep 2026 (§17.49).** The 29 Aug version is superseded in full.
It was organised around getting a commissioning map (G4). That is no longer
the top of the list, and §17.49 explains why with a tape measure.

---

## 0. THE PASTE BLOCK

> Continue AritraD11/NarrowAisleBot. `main` is current at `5cace67` and
> everything is merged into it — cut a fresh branch from `main`. Read
> `docs/Next_Session_Kickoff.md` first, then `docs/Research_Journal.md`
> §17.49 and `docs/Stack_Assessment_2026-09-01.md`.
>
> **The goal is to take every layer to 10/10 except the LiDAR, which is a
> hardware limit.** Seven layers can genuinely get there in software; four
> cannot, because they *are* the LiDAR's output. §1 below has the split.
>
> **Today's job, in order:** (1) the obstacle-avoidance test — this branch's
> actual purpose and never once run; (2) AMCL's first-ever bringup, now that
> `sensors.launch.py` makes it possible; (3) whatever's left in §6.
>
> **Do not re-derive these** — all measured, all in §17.49: the SLAM front
> end causes *physical* positioning error because Nav2 closes its loop on the
> map pose (two tape measurements, 9 cm and on-the-mark, from opposite ends);
> wheel odometry is excellent (4.582 m closed to 3.1 mm) and agrees with the
> tape to ~1 cm; peak `map→odom` is 20.3 cm and 56–59% of every run sits past
> 5 cm regardless of route, controller or `use_scan_barycenter`.
>
> Operational discipline, unchanged: copy-paste commands, one step at a time,
> never assume a step succeeded, verify config with `ros2 param get` against
> the **live node** not a file, hash every transferred file **per file** on
> arrival, short and crisp in chat with the prose in the journal.

---

## 1. What can and cannot reach 10/10

The rating that matters, from `Stack_Assessment_2026-09-01.md`. **This is a
cliff, not a slope: everything below the LiDAR is 9–10, everything from the
LiDAR up is 1–3.**

| reachable in software | now | capped by the sensor | now |
|---|---|---|---|
| Kinematics | **10** | LiDAR (excluded by decision) | 3 |
| Motor control | 9 | **SLAM front end** | 2 |
| TF / axes | 9 | **Occupancy map** | 1 |
| Instrumentation | 9 | **Global positioning** | 1 |
| Process | **10** ✅ | Wheel odometry (heading needs a magnetometer) | 9 |
| Nav2 config | 8 | | |
| Dashboard | 9 | | |
| **Local nav + obstacle chain** | **7** ← today | | |

⚠ **You cannot exempt the sensor and demand its outputs be perfect.** The map
*is* the LiDAR's output; global positioning is the map's. Chasing those to 10
in software is the thing this project has already done five times, and
§17.44's invariance result says it does not work.

---

## 2. Health check — before touching anything

```bash
echo "=== NETWORK ==="; ip -4 -br addr | grep -v " lo "
echo "=== NODES ==="; ros2 node list
echo "=== DEPLOYED HASHES ==="
sha256sum ~/ros2_ws/slam_nodom.yaml \
          ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py \
          ~/ros2_ws/src/mecanum_navigation/config/nav2_params.yaml 2>&1
echo "=== CPU / THERMAL ==="; uptime
awk '{printf "%.1f C\n", $1/1000}' /sys/class/thermal/thermal_zone0/temp
cat /sys/devices/platform/soc/soc:firmware/get_throttled
```

**Expected, as deployed 1 Sep:**

| file | sha256 |
|---|---|
| `slam_nodom.yaml` | `e8825eda73e67526860fb5adfde3b7e2cb8dac270ba59818a1038c2a80882fe5` (Stage F) |
| `phone_dashboard.py` | `8c41c6fa7e7ec867c1c1e4e823f154f1db6a3e47b78f7bba232b9bbf52268f5a` |
| `nav2_params.yaml` | `40fdf96ea7906f20d726bdd440a94f3c38690842b3b442cdaadcadc5e4a4617f` |
| `get_throttled` | `0` |

⚠ **`sensors.launch.py` is NOT yet deployed** — it was written on 1 Sep after
the robot was switched off. See §5.

**Rollback point:** `~/ros2_ws/slam_nodom.pre_stageF.yaml`, sha
`0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f` — the
Stage D config that passed G2 on 29 Aug.

---

## 3. TODAY'S MAIN EVENT — the obstacle test

**This is the branch's stated purpose from §17.48 and it has never been run.**
The hard requirement, in the operator's words: *a detected obstacle must stop
the robot regardless of an active goal, using the cushioning value already
configured.* Not a new safety system to design — the existing one to verify.

### Why it is worth doing before anything else

It is the one big win **completely insulated from the LiDAR's accuracy
problem**. `local_costmap` is `global_frame: odom`, `rolling_window: true`,
3×3 m; `collision_monitor` works in `base_link` against
`/local_costmap/published_footprint`. **Nothing in that chain reads
`map→odom`.** A 20 cm map error does not touch it. 7 → 10 in one session.

### What is already confirmed (do not re-verify)

- `collision_monitor` **active and bonded** on every Nav2 launch
- it is **not** spuriously blocking — the robot drove 2.3 m through it on
  1 Sep with zero interventions logged
- `FootprintApproach`, `action_type: approach`, `time_before_collision: 1.2`,
  `min_points: 6`, footprint from `/local_costmap/published_footprint`,
  `inflation_radius: 0.65` on both costmaps
- goals reach `bt_navigator`, and **abort-free** since
  `required_movement_radius` went to 0.10

### The three questions to ask the operator FIRST

Asked on 1 Sep and never answered — the drive cannot be designed without them.

1. **Which aisle**, and its clear length and width **in tiles** (62 × 62 cm,
   tape-measured, §17.47) from the zero mark.
2. **The obstacle** — what object, rough footprint, and **height**. The LiDAR
   plane is at **0.351 m** (`0.275` laser_joint + `0.0762` base_footprint), so
   anything under ~40 cm is invisible to it and the test measures nothing.
3. **The gap either side.** This decides the whole test: with
   `inflation_radius: 0.65` and a 1.12 m robot, an obstacle in an open aisle
   just gets planned around and `collision_monitor` never fires — which proves
   avoidance but **not** the override. A gap narrow enough that a centred
   obstacle leaves no route is the stronger test and the one §17.48 asked for.

### The run

**Part A — static.** Obstacle placed before the goal is sent. MPPI should route
around it. Proves the local costmap sees it and the inflation is respected.

**Part B — the real one.** Same goal, obstacle walked into the path mid-drive.

⚠ **HANDS COMPLETELY OFF THE KEYBOARD.** `twist_mux.yaml` gives `manual`
priority **100** against `navigation`'s **10**, and `collision_monitor` sits
only in the navigation branch. One keypress bypasses the safety layer entirely
and the test measures nothing.

Record the intervention rather than inferring it:

```bash
ros2 topic echo /collision_monitor_state
```

**Ordering, from §17.49:** MAP first, **then** `nav2_slam.launch.py`. Launched
the other way round the global costmap has no map and logs `Received map
message is malformed. Rejecting.` once a second — measured at 29 consecutive
seconds.

---

## 4. AMCL's first-ever bringup

Split cleanly in two, because only one half is blocked:

| | needs | status |
|---|---|---|
| **(a) does the AMCL block bring up at all?** | *a* map file — any of the ~70 archived | **unblocked** |
| **(b) does it localise accurately?** | a *good* map | blocked on G4 |

**(a) is the valuable half** and it is what `Where_We_Stand.md` §8 item 5 asked
for: *"a one-line plugin-name error can abort the ENTIRE bringup — discover
that on a Tuesday, not on demo day."* `robot_model_type` was corrected to
`nav2_amcl::OmniMotionModel` against upstream source and **never verified on
hardware**. 1 → 4 without a good map.

**And there is reason for optimism.** AMCL does not use slam_toolbox's
correlative matcher — it scores rays independently against a precomputed
likelihood field, so flickering rays cost it *votes* rather than deforming a
cost surface. `max_beams: 60` already subsamples 432 rays down to 60. **The
sensor defect that wrecks the SLAM front end is a much weaker problem for a
particle filter.** Global positioning may be more reachable than 1/10 suggests.

```bash
ros2 node list | grep slam_toolbox     # MUST come back EMPTY first
ros2 launch mecanum_navigation navigation.launch.py \
    map:=/home/aritra/aislebot_logs/run_<pick one>.yaml
ros2 param get /amcl robot_model_type
ros2 param get /amcl initial_pose      # expect yaw 0.0, fixed §17.49
```

`navigation.launch.py` now starts the LiDAR itself (`with_sensors`, default
true), so **do not** have MAP running — that is two ydlidar drivers on one
serial port.

---

## 5. Pending deployment

| repo file | destination | takes effect on |
|---|---|---|
| `src/mecanum_robot/launch/sensors.launch.py` **(new)** | `~/ros2_ws/src/mecanum_robot/launch/` | build `mecanum_robot` |
| `src/mecanum_robot/launch/mapping_full.launch.py` | same dir | build `mecanum_robot` |
| `src/mecanum_navigation/launch/navigation.launch.py` | `~/ros2_ws/src/mecanum_navigation/launch/` | build `mecanum_navigation` |
| `src/mecanum_navigation/package.xml` | `~/ros2_ws/src/mecanum_navigation/` | build `mecanum_navigation` |

All four are the §17.49 launch split. Deploy them together — `mapping_full`
now *includes* `sensors.launch.py` and will fail without it.

⚠ **Two traps, both paid for on 1 Sep:**

1. **Switching a package between symlink and normal install needs a clean.**
   `rm -rf build/<pkg> install/<pkg>` first. A `colcon build` reported
   *"2 packages finished"* while leaving `mecanum_navigation` unable to load
   its own entry points, and both its nodes died at launch.
2. **Step 5 must LAUNCH what it deployed.** Verifying the file proved the yaml
   was right and said nothing about whether the executables existed.

**Verification for this one is: MAP still works.** Press MAP, then

```bash
ros2 node list | grep -E "ydlidar|scan_relay|zero_point|slam_toolbox"
```

All four must appear, exactly as before the split.

---

## 6. The rest of the road to 10, ranked

| | item | robot? | layer |
|---|---|---|---|
| 1 | **Obstacle test** (§3) | yes | local nav 7→10 |
| 2 | **AMCL first bringup** (§4) | yes | global pos 1→4 |
| 3 | `--corpus` over the ~70-map archive — replaces `map_integrity.py`'s guessed thresholds with measured percentiles | no | instrumentation 9→10 |
| 4 | Patch `run_analyzer.py`'s two known false positives — deliberately deferred mid-campaign, and we are now between campaigns | no | instrumentation |
| 5 | One long goal, **3–4 m** — settles why MPPI cruises at 23–31% of its 0.12 m/s cap. **Every goal ever sent has been ≤ 1.16 m**, inside `GoalCritic`'s `threshold_to_consider: 1.0` and 4× the 2.0 s horizon. This robot has never been asked to just *travel*. | yes | nav config 8→10 |
| 6 | `xy_goal_tolerance: 0.02` is below the estimate's own noise floor | yes | nav config |
| 7 | Move the axis rotation into the URDF and delete the last two conversion points | no | TF 9→10 |
| 8 | Stage F re-drive, properly, under Nav2 (§7) | yes | closes the last software lever |

---

## 7. Stage F — open, and deliberately not scored

`use_scan_barycenter: true → false`, deployed and **confirmed `False` on the
live node**. `docs/StageF_Ablation.md` holds the thresholds, registered before
the drive.

**It is unscored because the one run on it was hand-driven, not Nav2-driven**
(the goal path was broken by the build mistake in §17.49). By the letter of the
registration the net of 0.064 m falls between CONFIRMED (<0.06) and REFUTED
(0.091–0.137): **AMBIGUOUS**.

⚠ **Do not score it on the over-5 cm fraction or the peak.** Both point at
refutation, and both were chosen *after* seeing the data. That is exactly what
pre-registration exists to prevent.

⛔ Its took-effect check is **RETRACTED** — the 0.175 m baseline was an artefact
of measuring displacement-from-origin instead of path length. Real spacings:
baseline 0.441 m (sd 0.192), Stage F 0.391 m (sd 0.147), indistinguishable.

**One clean Nav2 re-drive settles it.** Route: (0, 1.02) → (−0.16, 2.03) →
(0, 0). Beat: peak 13.0 cm, 59% over 5 cm, 9 cm on the tape.

**Honest expectation: refutation.** Which is worth having — it closes the last
software lever and is what justifies a ToF scanner over a guess.

---

## 8. What's true right now — don't re-derive

### The front end causes physical error (§17.49) — ✅ MEASURED, tape-confirmed

Nav2 closes its loop on the map pose. A corrupted estimate therefore becomes
*physical* mis-positioning, not just mis-reporting. Two runs prove it from
opposite ends, and wheel odometry agreed with the tape to ~1 cm in both.

### Odometry is the most trustworthy layer — ✅ MEASURED

4.582 m closed to **3.1 mm (0.07%)**. Integrator verified offline to 0.0000 m.
1.1–1.5% closed-loop. **Do not re-test.** Its one limit is heading: 10.53° over
18 m, which needs an absolute reference and is therefore capped in software.

### The sensor is in spec and the spec is not enough — ✅ MEASURED

X4 Pro is **triangulation**, rated **<2% of range**: 32 mm at the 1.6 m median,
200 mm at 10 m. §17.45 measured p90 22.8 mm — *within* spec. 48.8% valid rays,
**86% flickering while parked**, 44 of 314 rays present in every scan.

### Search parameters cannot fix it — ✅ MEASURED

§17.44: cumulative correction **2.80 / 2.85 / 2.86 m** across three parameter
sets, invariant to 2%. Every one of them changed how the matcher *searches*.
Read against §17.45's flicker, the matcher is handed a **different point cloud
every scan** — no search parameter fixes a moving objective function.

### Axes: closed (§17.38)

`base_link`, `odom`, `map` all `+X = right, +Y = forward`. A freshly-zeroed
robot on the mark reads `[0,0,0] @ 0°`. Guarded by
`tools/verify_axis_chain.py` (43 checks). **Never fix an axis complaint at the
display** — and note §17.49 found the *fifth* stale −90° compensation, in
AMCL's `initial_pose`.

### The dashboard tells the truth now (§17.49)

Goal headings correct, E-STOP survives reconnects, `send()` reports delivery,
and the pose card shows `ODOM` + `DRIFT` (red past 5 cm). Guarded by
`tools/tests/dashboard_goal_roundtrip.py`, 19 checks.
**Run it after any change to the pointer handlers, `w2s`/`s2w`, `vecToYaw`,
`send()`, or the E-STOP path.**

---

## 9. Standing traps

- **`base_link` is NOT REP-103: `+X` = RIGHT, `+Y` = NOSE.** Any new component
  with a notion of "forward" needs checking.
- **A repo value is not a robot value.** Check the live node.
- **A build that says `Finished` is not a package that runs.** §17.49.
- **MAP before Nav2**, always.
- **Never run AMCL and `slam_toolbox` together** — both publish `map→odom`.
  And since the split, `navigation.launch.py` starts its own LiDAR, so running
  it alongside MAP is two drivers on one serial port.
- **`slam_toolbox` 2.8.5 emits no loop-closure signal.** Don't grep for one.
- **Check the Pi's address every session** (`ip -4 -br addr`). `10.42.0.1` only
  exists while the Pi hosts its own AP, which has **no internet uplink** — a
  `curl` line in these docs is never a Pi command.
- **`scp` reporting `100%` does not mean the file arrived where you meant.**
  Hash on arrival, **per file**.
- **Nothing that stores a coordinate before AMCL works.** Live-SLAM
  coordinates don't survive a restart.

## 10. Deferred, still worth remembering

- Location library + teach flow (gated on AMCL)
- `scan_quality.py` at a third position, and at a different time of day —
  **ambient IR is an untested candidate for the §17.47/§17.48 intermittency**,
  and the split now lets it run without starting a mapping session
- LiDAR driver: `frequency: 10.0` against the X4 Pro's 7 Hz nominal (500 vs
  714 points/rev) and `range_max: 12.0` against a rated 10 m. **`range_max` is
  measured inert** — 0.0% of returns exceed 10 m — but `frequency` is untested
- `invalid_range_is_inf: false` means no-return beams clear no free space,
  which may explain maps at 77–83% unknown. **Dangerous to change** — it would
  clear through real obstacles the sensor failed to see. Needs a per-consumer
  split before it is safe
- `phone_dashboard.pre_light_theme.py` sitting in the package dir; dashboard
  reconnect has no backoff
- `src/mecanum_navigation/config/slam_params.yaml` is a third SLAM config that
  nothing launches
- IMU: decided against (22 Aug). BNO055 is the right part if ever prioritised.
  **Don't re-open unless the operator raises it.**
