# Where We Stand — a full-stack audit, 28 August 2026

**Written for the strategic review of 28 Aug 2026.** Every claim below carries
an evidence grade. Nothing is asserted because it was asserted before.

This document exists because §17.38 (the map-frame rotation bug) proved that a
wrong belief can survive two weeks of active work if nobody ever writes down
*which category* a claim is in. That will not happen twice.

> **Updated 29 Aug 2026 after the first hands-on day of the endgame week
> (§17.44).** G1 and G2 both passed; the deployment debt in §6 is cleared;
> §2's layer 6 and 7 numbers, §4's grades and §8's ranking are revised. The
> one structural change: **rotating in place maps nothing**, so the
> commissioning procedure itself was wrong, not only its tuning.

---

## 0. Evidence grades used throughout

| Grade | Means |
|---|---|
| ✅ **MEASURED** | Measured on this hardware, **and reproduced** on a second run or by a second instrument. Build on it. |
| 🟡 **SINGLE** | Measured once, on real hardware. Probably true. Do not build a fix on it alone. |
| 🔷 **HYPOTHESIS** | Reasoned, not measured — or measured on a stack now known to have been broken. Must be re-confirmed. |
| ⛔ **RETRACTED** | Was believed, is now known false. Recorded so it does not get re-derived. |
| ⬜ **NEVER RUN** | The code exists. It has never executed once. Unknown, not working. |

---

## 1. The one-paragraph answer

**Everything below the map is measured and good. The map is the only broken
layer, and one parameter family inside the SLAM front end is breaking it.**

The motors track. The encoders are clean. The odometry integration is exact.
The kinematics are exact. The TF frame composition is exact to four decimals.
Nav2 plans, controls, and reaches goals. The dashboard renders and its
click-to-goal is exact to 1e-6. On the longest drive in the project's history
(21.85 m), **wheel odometry came back 0.229 m from the mark — 1.27%, dead on
its own spec — and SLAM took that estimate and made it 0.477 m worse.**

The robot's cheapest sensor is currently its most trustworthy one, and the
expensive one is overruling it.

---

## 2. Layer-by-layer state

Read this table top to bottom. The break is at layer 6.

| # | Layer | State | Grade | The number that says so |
|---|---|---|---|---|
| 1 | **Motor control** (ESP32, PID+FF, 50 Hz, HW PCNT) | Working | ✅ | All four motors 0.043–0.046 rad/s RMS tracking error, **zero saturation, zero sign mismatch, no dead feedback**, over 20 940 samples (§17.42) |
| 2 | **Encoders / wiring** | Working | ✅ | Travel spread ratio 1.00 on a non-rotating square; 1.12 on a rotating traverse, which is expected by construction, not a fault (§17.42) |
| 3 | **Kinematics** (asymmetric mecanum) | Exact | ✅ | Forward model reproduces ground-truth twist to 1.7e-16 over 20 000 random twists. Both the journal's §2.5 form and `odometry_publisher`'s form are unbiased (see §7 below) |
| 4 | **Odometry integration** | Exact | ✅ | `wheel_forensics.py` re-integrated a whole run offline from raw encoders: **max divergence from the live `/odom` 0.0054 m, final divergence 0.0000 m.** The integrator is eliminated as a suspect |
| 5 | **`/odom` physical accuracy** | At spec, and it is the ceiling | ✅ | 2.58 cm closure on a 38 s square; 4.3 cm (1.1%) on a 4 m out-and-back; **0.229 m (1.27%) and 10.53° over 21.85 m** |
| 6 | **`map→odom`** (SLAM front end) | 🔴 **BROKEN — this is the project** | ✅ | **One correction per pose-graph node, every node** — 18 nodes / 17 corrections at a 3.65 s cadence (§17.44). Improved but not fixed: max correction 0.696 m → **0.202 m**, max heading step 18.40° → **4.57°**, cumulative per metre 0.507 → **0.163 m/m** |
| 7 | **Saved map** | 🔴 **Does not exist** | ✅ | Best map to date graded `FOLDED`: **D2 doubled walls 1.9%** (gate <1.0%), improved from 5.0%; return-to-mark 0.257 m (gate <0.15). **There is still no accepted commissioning map** |
| 8 | **AMCL localisation** | Never executed | ⬜ | The whole `amcl` block in `nav2_params.yaml` has never run once. Its `robot_model_type` value is suspect (see §5) |
| 9 | **Global planner** (NavFn) | Working, starved | 🟡 | Plans successfully; runs at **1.25 Hz against 5 Hz requested** |
| 10 | **Local controller** (MPPI) | Working, starved | ✅ | Two `Goal succeeded` (25.9 s, 21.0 s). Control loop **7.5–13.7 Hz against 20 Hz requested** |
| 11 | **Safety chain** (`collision_monitor` → wheels) | Wired, degraded | 🟡 | Chain confirmed end-to-end (§17.17). Stale-scan warnings under CPU load |
| 12 | **Dashboard** | Working; one build pending | ✅ | Headless-Chromium round trip: **click pixel → world coordinate exact to 1e-6 at device pixel ratios 1, 2 and 3** |
| 13 | **Location library** ("go to Rack A3") | Does not exist | ⬜ | Designed in `Production_Architecture.md` §3.3. No code written |

---

## 3. What is confirmed about the break, and how strongly

### 3.1 ✅ The jumps are the SLAM **front end**, not loop closure

Confirmed by two independent instruments, and then a third time by prediction.

- `graph_residuals.py --watch` reported `moved=0, max_shift=0.000` for
  **645 seconds through all 19 loop closures**. A back-end re-solve moves
  pose-graph nodes. Nothing moved.
- `run_analyzer.py` on the same drive reported **48 correction events, 48 of
  48 with wheel odometry stepping normally** — the signature of `map→odom`
  moving while `odom→base_link` stays smooth.

Both are correct and they do not contradict each other: the tool watches
pose-graph *node positions* (the back end), while `map→odom` is **also** moved
by the front end, which touches no node.

### 3.2 ✅ The correction magnitude is *set by* the search window

This is the strongest result in the project, because it was **predicted before
the test and then produced on command**:

| Deployed `correlation_search_space_dimension` | Largest correction ÷ search half-width |
|---|---|
| 0.7 | **0.96** |
| 0.3 | **1.05** |

Change the parameter, and the corrections scale with it — landing on the
boundary either way. A hypothesis that predicts a number in advance and then
produces it is worth more than one that explains a number afterwards.

### 3.3 ✅ The remaining large corrections are **heading** snaps

`coarse_search_angle_offset` is stock `0.349 rad = 20°` and **has never been
set in this project's config file, in any session.** On the 1047 s drive the
largest correction was 0.696 m — **4.6× the deployed translational half-width
of 0.150 m**, so it cannot be a translational snap. Checked against pure yaw
about the map origin, `2·r·sin(θ/2)`:

| corr (m) | yaw | lever r | predicted | ratio |
|---|---|---|---|---|
| 0.696 | **−18.40°** | 2.06 m | 0.660 | **0.95** |
| 0.500 | 15.00° | 2.13 m | 0.555 | 1.11 |
| 0.431 | 12.80° | 2.53 m | 0.563 | 1.31 |
| 0.388 | 12.00° | 2.30 m | 0.481 | 1.24 |
| 0.261 | −7.20° | 1.94 m | 0.244 | 0.93 |

**18.40° is 92% of the 20° window.** Same saturation signature, on the axis
nobody had closed. Honest caveat: smaller events fit this model poorly (ratios
0.10–0.49), so translation still contributes at short range. The model explains
**3.59 m of the 4.80 m** total correction — it is a description of the large
events, not of all of them.

### 3.4 ✅ Why Stage C looked like a win and did not hold

The Stage C A/B stayed within ~1 m of origin, where the lever arm is short and
error is mostly translational — exactly what Stage C bounds. The commissioning
drive reached 3.5 m out, where the same angular error costs three to four times
as much.

**A fix validated near the origin was extrapolated to a drive that goes
further, and the extrapolation failed.** That is a methodological caution, not
just a parameter note. It applies to every remaining fix in this project.

### 3.5 ✅ The frame composition is exact and should stop being suspected

`R(corr)·odom + corr` reproduces the map pose to the fourth decimal. §17.38's
axis work is **not implicated in any of this**. Closed. Do not reopen.

---

## 4. Claims that must be re-confirmed, not built on

These were drawn on a stack that had a rotated map frame, or measured once, or
have since been contradicted. **Every one of them is a hypothesis today.**

| Claim | Grade | Why it is not settled |
|---|---|---|
| §17.28–§17.32's loop-closure conclusions | 🔷 | Drawn before the §17.38 frame fix. Every conclusion in them rests on numbers read out of a rotated map frame |
| False closures cause the doubled walls | 🟡 | First-ever co-location evidence: 3 corrections within 1.0 m of a doubled wall, sizes 0.364 / 0.208 / 0.058 m. **n=3. Suggestive, not conclusive** |
| The doubled walls are "matched the wrong aisle" | 🔷 | Argues *against*: the clusters sit **within** individual arms (pairs 0.29 m and 0.38 m apart in the same arm), not across different arms. More consistent with "matched the right aisle at a drifted pose" |
| "Strafe is the weak axis" | ⛔ **RETRACTED** | A third recording failed on the `W`/`S` leg at the same speed on the same day. The failure is **intermittent, not axis-locked**. A mechanism had nearly been invented for a phenomenon that does not exist. **Do not re-derive this from the §17.40 drive in isolation** |
| "Speed matters" (0.10 m/s worse than 0.05) | 🔷 | Consistent with the window being reached more readily, but uncontrolled. Weaker than the retracted claim above |
| The pose-graph back end is healthy | 🟡 | `moved=0` through 19 closures is consistent with "healthy and correctly finding nothing to fix" **and** with "the closures fired and were inert." The second reading is supported by the 0.477 m terminal miss |
| Loop closure will help once the front end is fixed | 🔷 | Untested. 19 closures fired and the map still folded |
| **Rotation in place adds no node and no map cell** | ✅ **MEASURED** | Three runs, 29 Aug. A deliberate 714° / 642 s test produced **43 occupied cells = 2.1 m of wall and zero corrections**. `/scan_reliable` measured at 11.4 Hz throughout, so it is not starved scans (§17.44) |
| `minimum_travel_heading` is what blocks rotation | ⛔ **RETRACTED** | Set to 0.05 and verified on the live node; a full 360° still gave `n=1, e=0` for 166 s. **Not the gate** |
| `shouldProcessScan()` gates on distance only, ahead of Karto's heading test | 🔷 | Predicts every observation, but **recalled from source, not read**. Verify against the installed `slam_toolbox` before citing |
| Turning **while translating** maps normally | ✅ **MEASURED** | A 111 s `W`+`E` arc: 18 nodes, **1545 cells = 77.2 m of wall** — 88% of the 621 s perimeter drive's coverage in 18% of its time |
| The tight circle is a **degenerate geometry** for scan matching | 🔷 | At 5 m range 1° of heading ≈ 8.7 cm of translation. Predicts the measured signature (heading right to ~4°, position 27.6 cm out, wheels 0.008 m) and explains why **cumulative correction stayed 2.80 / 2.85 / 2.86 m across three parameter sets**. Not yet tested against a controlled wide-radius arc |
| `angle_variance_penalty` is a useful lever | ⛔ **RETRACTED** | Stage E, 1.2 → 0.6: max correction went 0.229 → 0.366 m and the cumulative total did not move |

**The single most important line in this table:** the closures were **inert** —
they fired and changed nothing, while the estimate was half a metre wrong.

---

## 5. Things that have never executed once

Not "working". Not "broken". **Unknown**, and each one is a potential
bringup-aborting failure sitting between here and the demo.

| Thing | Risk | Specific known hazard |
|---|---|---|
| **AMCL** (the entire block) | 🔴 High | `robot_model_type: "omnidirectional"` is the pre-Galactic bare-string form. Jazzy loads this as a pluginlib class name and expects `"nav2_amcl::OmniMotionModel"`. **A plugin that fails to load aborts the whole `lifecycle_manager` bringup** — the same all-or-nothing failure mode §17.17 already hit once. Check before the first run: `grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml` |
| **`map_server` loading a saved map** | 🟡 | Never done, because no map has ever been accepted |
| **`navigation.launch.py`** (the saved-map path) | 🟡 | Only `nav2_slam.launch.py` has ever been launched |
| **`tools/bag_tf_diff.py`** | 🟢 | Built for the decisive `map→odom` vs `odom→base_link` split, never run once. Now largely superseded — `run_analyzer.py` answered the same question on 48 events |
| **`robot_state_publisher` on the real robot** | 🟢 | `/robot_description` exists only in the Gazebo sim launch |

---

## 6. Deployment debt — CLEARED 29 Aug, verified against the live node

**All four files below were deployed on 29 Aug (§17.44), hashed individually
on arrival, rebuilt, and confirmed by `ros2 param get` against the running
node: `coarse_search_angle_offset 0.175`, `correlation_search_space_dimension
0.3`.** Before deployment the live node read stock `0.349`, which confirmed
the debt by measurement rather than by report.

The table is kept as the record of what was owed and what hash satisfied it.

| File | Repo SHA-256 | Needs `colcon build`? | What it buys |
|---|---|---|---|
| `src/mecanum_robot/mecanum_robot/phone_dashboard.py` | `5b30a91dc7614d73848357bcedd66771cb332eddd12d1de06ed58dce47ad43d1` | **Yes** | Layer toggles (current trail / past trails / goals / footprint / axes), goal persistence, CLEAR |
| `tools/wheel_forensics.py` | `27858ce417f3f39e56db3b87b31644fc11a9292aba7247f1c8d9a2d80bf96236` | No | Full offline re-integration + slip residual + 32-column CSV export |
| `src/mecanum_robot/urdf/aislebot.urdf` | `ea6619ff3999b856fc3c1632041bd3a151eb8732f9c782d90207831ce1b0a81c` | No (comment-only) | §17.38 axis-convention note |
| `system/slam_nodom_stageB.yaml` **(Stage D, new)** | `0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f` | No | `coarse_search_angle_offset` 20° → 10° |

**Already on the robot and verified:** `tools/graph_residuals.py`
(`9ead3a6f…`), and Stage C's `slam_nodom.yaml` (`e90aee53…`, superseded by the
Stage D hash above).

Deploy procedure: `docs/Important_Commands.md` §3.2. Two rules that are not
negotiable — **hash every file on arrival, per file**, and **verify deployed
config with `ros2 param get` against the live node, never by reading a file.**

---

## 7. A discrepancy found during this audit, resolved

The journal's §2.5 and the running code disagree on the yaw estimator:

```
§2.5:                  ω_z = r/(2(l₁+l₂+2d)) · (ω_FR − ω_FL + ω_RR − ω_RL)
odometry_publisher.py: ω_z = (r/4)(ω_FR/K_out − ω_FL/K_in + ω_RR/K_in − ω_RL/K_out)
```

**Both are unbiased** (verified: max error 1.67e-16 over 20 000 random twists).
They are two different *weightings of the same two independent measurements* —
see `APS_Study_Guide.md` §2.4 for the full derivation, because it is the single
best piece of theory this robot's geometry produces.

The practical part: `odometry_publisher`'s equal weighting carries **0.89%**
more yaw-rate noise than the minimum-variance weighting; §2.5's carries
**0.22%** more.

**Verdict: do not change the code.** A 0.89% noise penalty cannot produce
10.53° of drift over 18 m. That drift is physical slip. This is a good exam
answer and a bad engineering priority — and knowing the difference is the
point of grading evidence.

---

## 8. The honest list of what is actually holding the project

Ranked by what unlocks the most, not by how hard each is.

1. 🔴 **No accepted map.** Everything named in `Production_Architecture.md` —
   stable coordinates, named locations, AMCL, point-and-go — rests on one
   saved grid that does not exist yet. **This is the critical path.**
2. 🔴 **The commissioning procedure itself.** "Rotating at every corner"
   discards its own corner observations — measured, three runs (§17.44).
   Corners must be taken as rounded turns *while rolling*. This costs
   nothing and is the single highest-value change available.
3. 🟠 **The residual front-end disagreement.** One correction per node, every
   node. Not reachable by the search or penalty parameters — three sets left
   cumulative correction at 2.80 / 2.85 / 2.86 m. Needs a diagnosis, not a
   tuning pass, and the next measurement must be taken on a **perimeter**
   drive rather than a circle.
   *(Closed: `coarse_search_angle_offset` 20° → 10°. G2 passed 29 Aug —
   max correction 0.202 m, max heading step 4.57°.)*
4. 🟠 **Pi CPU saturation.** Control 7.5–13.7 Hz vs 20 requested; planner
   1.25 Hz vs 5. This degrades *everything above it* and produces TF
   extrapolation errors and stale `collision_monitor` scans — which read as
   navigation bugs and are not.
5. 🟠 **AMCL has never run.** A one-line plugin-name error can abort the entire
   bringup. Discover that on a Tuesday, not on demo day.
6. 🟡 **`xy_goal_tolerance: 0.02`** is 2 cm — smaller than the pose jitter the
   estimate itself has. The controller cannot converge on a target tighter
   than its own noise floor.
7. 🟡 **Heading drift, 10.53° over 18 m.** The odometry ceiling. Relevant to
   the shelved IMU decision, which stays shelved unless the operator raises it.
8. ⬜ **No location library.** Pure software, no hardware risk, and it is what
   turns "a navigation demo" into "a product."

---

## 9. What this project has that most undergraduate robotics projects do not

Stated plainly, because it matters for the report and for the APS review:

- **A genuine geometric novelty.** The asymmetric wheelbase (l₁ = 0.403 m,
  l₂ = 0.333 m) is not a standard mecanum platform, and the asymmetry
  propagates correctly through inverse kinematics, forward kinematics,
  odometry, and the simulation bridge.
- **A measured error budget, not an assumed one.** 1.1–1.5% closed-loop
  odometry, with the integrator independently verified to 0.0000 m.
- **Purpose-built instrumentation.** `graph_residuals.py`, `run_analyzer.py`,
  `map_integrity.py`, `wheel_forensics.py`, `run_bundle.py` — five tools that
  exist because a question needed answering, each with self-tests.
- **A falsification record.** Predictions written *before* tests (§17.40's
  three-branch table), and claims publicly retracted when the data killed them
  (the strafe lead). That is the part reviewers respect and almost nobody has.

---

## 10. What to read next

| If you want | Read |
|---|---|
| How to get to point-and-go, and this week's plan | `docs/Autonomy_Endgame.md` |
| The theory, the derivations, and the likely APS questions | `docs/APS_Study_Guide.md` |
| Where this goes commercially | `docs/Vision_Indian_Market.md` |
| The raw session-by-session record | `docs/Research_Journal.md` §17.38–§17.42 |
| Exact deploy commands | `docs/Important_Commands.md` §3.2 |
