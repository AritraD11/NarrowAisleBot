# Stack Assessment — 1 September 2026

**Branch:** `claude/narrowaislebot-goal-obstacle-avoidance-f2t3aa`, cut from
`claude/narrowaislebot-mapping-reliability-038ike` (`42e73f6`), which is **20
commits ahead of `main` and unmerged**. `main` is stale as of 27 Aug.

Written in response to a request for an honest, calibrated rating of every
layer. Ratings are deliberately harsh where the evidence is harsh. Every score
cites a measured number.

---

## 1. The headline

**Everything below the LiDAR rates 9/10. Everything from the LiDAR up rates
1–3/10.** That is not a gradual decline, it is a cliff, and the cliff is at one
component.

| # | Layer | Score | The number |
|---|---|---|---|
| 1 | Kinematics (asymmetric mecanum) | **10** | forward model reproduces ground truth to 1.7e-16 over 20 000 random twists |
| 2 | Motor control (ESP32, PID+FF, 50 Hz) | **9** | this run: 0.019–0.024 rad/s RMS all four, 0% saturation, 0% sign mismatch, max PWM 67/255 |
| 3 | Wheel odometry | **9** | integrator verified offline to 0.0000 m final divergence; 1.1–1.5% closed loop; 3.3 mm on a 0.5 m circle |
| 4 | TF / axis convention | **9** | 38 executable checks, ≤1.2 mm cross-axis on 180 mm moves |
| 5 | Instrumentation / tooling | **9** | six self-tested tools, a written falsification record, predictions registered before tests |
| 6 | Engineering process | **9** | evidence grades, recorded retractions, per-file hashing, "a repo value is not a robot value" |
| 7 | Nav2 configuration | **8** | two stock critics dropped for source-verified reasons; every axis-sensitive parameter deliberately swapped |
| 8 | SLAM back end (pose graph) | **7** | four independent drives: closures fire, `moved=0`, `max_shift 0.000 m` |
| 9 | Local nav + obstacle chain | **7** | 4× `Goal succeeded`; whole chain runs in `odom`/`base_link`, insulated from the map error |
| 10 | Dashboard | **6** | canvas math exact to 1e-6 — and every commanded heading has been 90° wrong |
| 11 | **LiDAR sensing** | **3** | **74.8–78% of rays flicker valid/invalid while the robot is stationary**; 47.4% valid |
| 12 | **Autonomy as delivered capability** | **3** | drives where you click, slowly, sometimes, at the wrong heading, on a map wrong by half a metre |
| 13 | **SLAM front end (scan matching)** | **2** | one correction per node, **every** node, 0.175 m ± 6 mm apart; makes the estimate worse than dead reckoning |
| 14 | **Occupancy map** | **1** | ~70 attempts, every one grades `FOLDED`; today 82.9% unknown |
| 15 | **Global localisation / point-and-go** | **1** | AMCL has never executed once; no saved map exists to localise against |

**Overall: 5/10.** A stack with an excellent lower half, a world-class
measurement culture, and one component that poisons everything above it.

---

## 2. The finding that reframes the SLAM work

Two facts already in this journal have never been read against each other.

**Fact A — §17.44.** Cumulative `map→odom` correction across three different
parameter sets: **2.80 / 2.85 / 2.86 m. Invariant to within 2%.** Every
parameter tried was a *search* parameter — `correlation_search_space_dimension`
(0.7→0.3), `coarse_search_angle_offset` (20°→10°), `angle_variance_penalty`
(1.2→0.6), `minimum_travel_heading` (0.2→0.1). The tuning moved the
*distribution* of the error and never the *amount*.

**Fact B — §17.45.** The scan input was measured for the first time.
**74.8–78.0% of rays change valid/invalid between consecutive scans with the
robot completely stationary.** 47.4% valid rays. Per-ray range noise p90
22.8 mm, max 79.9 mm.

Read together they say one thing:

> **The matcher is not searching badly. It is being handed a different point
> cloud every scan.** No search parameter can fix a moving objective function,
> which is exactly why five sessions of search tuning produced a 2% change.

This also explains the two things that have most resisted explanation:

- **Intermittency (§17.47/§17.48, three outcomes on one route).** Ray dropout is
  stochastic. Same aisle, different valid-ray set, different answer.
- **One correction per node, magnitude uncorrelated with anything.** Confirmed
  again today on a *Nav2* run, for the first time:

| corrections in `run_20260901_132022` | value |
|---|---|
| inter-correction odometry spacing | **0.175 m, sd 0.006 m** (n=9) |
| correction magnitude | **0.026 – 0.163 m** — a 6× spread |
| odom motion within the jump sample | **2–4 mm**, every event |

The *timing* is a metronome. The *magnitude* is random. That is a mechanism
firing on schedule and computing a different answer each time.

### Why the sensor is not "faulty"

YDLIDAR X4 Pro is a **triangulation** scanner: 0.12–10 m, **accuracy < 2% of
range**, angular resolution **0.63°**, 5 kHz ranging. At the measured 1.6 m
median range, 2% is **32 mm** — so §17.45's p90 of 22.8 mm is *within spec*.

That is the uncomfortable part. **The sensor is performing to specification and
the specification is not good enough for what is being asked of it.** At 5 m one
ray carries 100 mm of range error and 55 mm of angular quantisation; at 10 m,
200 mm and 110 mm. The measured corrections (150–370 mm) are the same order.

Low-cost triangulation units also ship with no intensity channel, no dual
return and no per-ray diagnostics, so there is no signal available to reject a
bad measurement — confirmed in the driver config: `intensity: false`,
`isSingleChannel: true`.

---

## 3. Three input-side levers, none of which has ever been tried

Every SLAM change to date has been downstream of the scan. These are upstream.

### A. Scan frequency 10 Hz → 7 Hz  *(highest value, one line)*

`system/ydlidar_params.yaml` sets `frequency: 10.0` with `sample_rate: 5`
(5 kHz). Points per revolution = 5000 / f:

| frequency | points/rev | valid @ 47.4% |
|---|---|---|
| 10.0 Hz (deployed) | 500 | ~237 |
| **7.0 Hz (datasheet nominal)** | **714** | **~338** |

**+43% angular density for free.** Cost: 143 ms per revolution instead of
100 ms, so motion skew rises from ~12 mm to ~17 mm at 0.12 m/s — against
corrections of 150–370 mm. The trade is strongly favourable and the datasheet
nominal is 7 Hz anyway.

### B. `range_max: 12.0` → `10.0` in the driver

The X4 Pro's rated maximum is **10 m**. The driver is currently told to accept
returns to 12 m — 20% beyond specification, where returns are not valid
measurements. `slam_nodom_stageB.yaml` clips at `max_laser_range: 10.0`, so
slam_toolbox is protected, but the published `/scan_reliable` is not, and
`scan_quality.py`'s valid/flicker statistics are computed over it. The costmaps
are already safe (`obstacle_max_range: 8.0`, `raytrace_max_range: 9.0`).

### C. `max_laser_range` ablation: 10.0 vs 6.0  *(two-sided — an experiment, not a fix)*

At 10 m a single ray carries ~200 mm of range error; at 6 m, ~120 mm. Cutting
range reduces per-ray error but discards the distant features that constrain
motion *along* a corridor — the classic degeneracy case. **Must be run as an
ablation with the result recorded either way**, not applied as a fix.

---

## 4. The cheap test that has the best odds on G4

**Run a commissioning drive with `use_scan_matching: false`.**

This is not a hack. It is using the measurably better estimator:

| over 21.85 m | closure |
|---|---|
| wheel odometry alone | **0.229 m (1.27%)** |
| odometry + SLAM front end | 0.706 m |

The front end makes it **0.477 m worse**. On a ~10 m perimeter, odometry alone
projects to ~0.13 m — **inside G4's <0.15 m return gate**, which five sessions
of scan-matcher tuning have never reached.

Two things to verify rather than assume:
1. whether loop closure still functions with the sequential matcher disabled
   (it has its own matcher — check against source and the live node, do not
   infer);
2. whether map cells still accumulate at the same rate.

---

## 5. What is actually blocking what

| Capability | Blocked by the SLAM front end? |
|---|---|
| Obstacle detection and avoidance | **No.** `local_costmap` is `global_frame: odom`, `rolling_window: true`, 3×3 m; `collision_monitor` works in `base_link` against the live footprint. Nothing in the chain reads `map→odom`. |
| Drive to a clicked point under live SLAM | Partially — works, lands ~0.5 m from where you meant |
| Saved map, AMCL, "go to Rack A3" | **Yes, completely.** |

This is `Next_Session_Kickoff.md` §11's fallback reasoning, now with a
mechanism instead of an assertion.

---

## 6. Dashboard defects found 1 Sep

1. **Goal heading is 90° wrong** whenever the drag exceeds 5 cm.
   `phone_dashboard.py:1653` writes `atan2(dy,dx)` (angle from **+X**) into the
   same variable line 1634 initialises from `robotPose.yaw` (angle from **+Y**).
   Two conventions, one variable.
2. **The two heading renderers disagree by 90° in the same frame.**
   `drawRobot:1465` draws the nose along `(−sin θ, +cos θ)` = **+Y**, correct.
   `drawGoalMarker:1406` draws the arrow along `(+cos θ, +sin θ)` = **+X**.
   Visible in a single video frame: `NOSE −0.6°`, nose line up, goal arrow right.
3. **Stale comment at 1683** claiming `goal_pose_adapter` applies −90°. False
   since §17.38; the live node logs `yaw +0.0 deg`. This comment is why nobody
   looked here.
4. **Click-to-goal lands right of the pointer** when the canvas element's CSS
   width has changed since `sizeCanvas()` last ran — the pointer path uses a
   live `getBoundingClientRect()` while `s2w()` uses cached `cssW`, so the
   marker lands at `sx · (r.width / cssW)`. There is no `ResizeObserver`, and
   the `resize` handler silently returns whenever the map view is hidden.
   *Hypothesis — falsify by comparing `r.width` to `cssW` in the console.*

The fixes go in the dashboard, at the one place a screen vector becomes an
angle. **Not** in `goal_pose_adapter` — that would also break the no-drag path,
which is currently correct, and it is the exact shape §17.38 deleted.

---

## 7. On the external audit doc (`NarrowAisleBot_SLAM_Diagnostic_and_Recovery_Plan.md`)

Its method is right and its central instruction — *characterise the input before
tuning the search* — is the correct one. Two corrections:

- **It audited `main`**, which is 20 commits stale, so it does not have
  §17.40–§17.48. Its picture of the project is four sessions old.
- **Its Experiment 1 (parked LiDAR stability) has already been run**, in
  §17.45, and came back its own **Case B** — "stationary scan wanders
  substantially → fix the sensor input first." §17.45 filed that as *a second,
  plausible contributor*. Against §17.44's invariance result it is better read
  as the primary one.
- **Its Experiment 4 (loop closure OFF) is largely pre-answered.**
  `graph_residuals.py` has shown `moved=0`, `max_shift 0.000 m` across four
  independent drives. The back end is not moving anything. Its **Experiment 5**
  (`use_scan_matching: false`) is the informative one and is promoted to §4 above.

Its §20 ("do not post-process the spikes away") and §21 ("do not add the IMU
first") are both correct and should be adopted verbatim.

---

## 8. Should the jumps be worried about?

**Yes — and they are now well enough characterised to stop re-diagnosing.**

Confirmed, do not re-derive: the jumps are `map→odom` corrections from the
sequential scan matcher; the robot moves 2–4 mm while the map moves 26–163 mm;
they arrive once per pose-graph node at a fixed 0.175 m odometry interval; the
pose-graph optimiser is not involved; their total is invariant to every search
parameter tried; and the plausible cause is a scan input that is not stable
scan-to-scan even when the robot is still.

What that means practically: **ignore them for obstacle-avoidance work**, which
never reads `map→odom`. **Treat them as a hard blocker for anything
map-referenced**, which includes every remaining item in
`Production_Architecture.md`.
