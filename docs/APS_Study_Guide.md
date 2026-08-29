# APS Study Guide — the fundamentals behind NarrowAisleBot

**Written 28 Aug 2026, for the review and report due 30 September 2026.**

> **Assumption stated up front:** this is written for a *panel review with a
> written report* — a technical presentation where reviewers can ask anything
> from "what is SLAM" to "justify that number." If the format turns out to be
> narrower, the material still covers it; nothing here is wasted.

**How to use this.** §1 is memorisation — know those numbers cold, because
being unable to state your own robot's dimensions is the single worst
impression available. §2–§9 are the theory, each section built around
*something this robot actually measured*. §10 is the question bank. §11 is the
three questions that can go badly, and how to answer them well.

**The one rule for the whole review:** never present a number without its
evidence grade. "We measured 1.27% over 21.85 m" beats "it's about 1%", and
"we haven't tested that" beats a guess every time.

---

## 1. The numbers to know cold

### Geometry

| Symbol | Value | What it is |
|---|---|---|
| L × W | 1000 × 250 mm | Chassis footprint |
| m | 45.54 kg | Total mass |
| l₁ | 0.403 m | Longitudinal distance, **outer** wheels (FR, RL) |
| l₂ | 0.333 m | Longitudinal distance, **inner** wheels (FL, RR) |
| l₁ − l₂ | **70 mm** | **The asymmetry. The project's central geometric novelty** |
| d | 0.15769 m | Half track width |
| r | 0.0762 m | Wheel radius (DekuPro 6" SR mecanum, 45° rollers) |
| K_outer | l₁ + d = **0.56069 m** | Yaw lever arm, FR and RL |
| K_inner | l₂ + d = **0.49069 m** | Yaw lever arm, FL and RR |
| K_o/K_i | **1.142656** | The slip-residual coefficient |

### Performance

| Quantity | Value | Grade |
|---|---|---|
| Max wheel speed | 6.28 rad/s (60 rpm) | spec |
| Theoretical max linear | ≈ 0.48 m/s | derived |
| Operating limit | 0.15 m/s, 0.3 rad/s | set |
| Motor tracking RMS error | 0.043–0.046 rad/s, all four | ✅ measured |
| **Odometry closure** | **1.27% over 21.85 m** (0.229 m) | ✅ measured |
| Odometry closure, short run | 2.58 cm over a 38 s square | ✅ measured |
| Odometry heading drift | **10.53° over ~18 m** | ✅ measured |
| SLAM map error, same run | **0.477 m / 16.18°** | ✅ measured |
| Cumulative `map→odom` correction | **11.08 m across 21.85 m driven** | ✅ measured |

### Sensing and compute

| Quantity | Value |
|---|---|
| LiDAR | YDLIDAR X4 Pro, 10 m max range, ~11.5 Hz |
| **Blind sector** | **90° wedge behind the mast** (−135° to −45° true bearing), 107 of 430 relayed beams masked NaN |
| Map resolution | 0.05 m/cell |
| Compute | Raspberry Pi 5 (ROS 2 Jazzy) + ESP32 (motor control, 50 Hz) |
| Control loop, actual | 7.5–13.7 Hz against 20 Hz requested |

---

## 2. Kinematics — the best theory this robot produces

**If you learn one thing deeply for the review, learn this section.** It is
where the robot's unusual geometry produces a genuinely non-standard result,
and it is the part a reviewer cannot have seen in a textbook, because it
depends on l₁ ≠ l₂.

### 2.1 Why a mecanum wheel is holonomic

A mecanum wheel has passive rollers mounted at 45° to the hub axis. The wheel
can drive along its own rolling direction, and simultaneously **slide freely**
along the roller axis. Each wheel therefore constrains only *one* component of
its contact velocity instead of two. Four wheels → four constraints → three
controllable DOF (u, v, ω) with one left over. That leftover is §2.3, and it
is a gift, not a defect.

### 2.2 Inverse kinematics — the asymmetric form

With body velocities **u** (forward), **v** (strafe), **ω** (yaw rate), and
the roller handedness alternating diagonally (FR & RL one way, FL & RR the
other):

```
ω_FR = (1/r) ( u + v + K_outer·ω )      outer
ω_FL = (1/r) ( u − v − K_inner·ω )      inner
ω_RR = (1/r) ( u − v + K_inner·ω )      inner
ω_RL = (1/r) ( u + v − K_outer·ω )      outer
```

In matrix form, **ω_wheels = (1/r) · J · q** with q = [u, v, ω]ᵀ:

```
        ⎡ 1   +1   +K_o ⎤
   J =  ⎢ 1   −1   −K_i ⎥
        ⎢ 1   −1   +K_i ⎥
        ⎣ 1   +1   −K_o ⎦
```

**J is 4×3 of rank 3.** Note that a symmetric mecanum would have a single K
everywhere; every historical bug in this project's control code traces back to
some path using one K where two were needed. *The asymmetry must propagate
everywhere or the geometric novelty is silently erased.*

### 2.3 The redundancy, and the slip residual (derive this on the board)

Since J maps 3 dimensions into 4, the set of *physically consistent* wheel
velocity vectors is a 3-D subspace of ℝ⁴ — the **image** of J. Any measured
wheel vector with a component outside that subspace is reporting something no
rigid-body motion could have produced. **That component is slip.**

Find it by computing the orthogonal complement of the image, which is the null
space of **Jᵀ** (a 1-D space, since 4 − 3 = 1). Seek **n** = [a, b, c, d]ᵀ with
nᵀJ = 0:

```
column 1 (u):   a + b + c + d = 0
column 2 (v):   a − b − c + d = 0
column 3 (ω):   a·K_o − b·K_i + c·K_i − d·K_o = 0
```

Add the first two: `2a + 2d = 0` → **d = −a**.
Subtract them:    `2b + 2c = 0` → **c = −b**.
Substitute into the third: `2a·K_o − 2b·K_i = 0` → **b = a·(K_o/K_i)**.

So with `k = K_outer/K_inner = 1.142656`:

> ### **s = ω_FR + k·ω_FL − k·ω_RR − ω_RL**
>
> **Zero for any rigid-body motion whatsoever. Non-zero only when a wheel
> slips.** This is the slip residual implemented in `tools/wheel_forensics.py`,
> and it is exactly this null-space vector.

**A mistake worth mentioning if asked how it was derived**, because it shows
you understand *why* rather than *that*: the first attempt used the null space
of **J** itself. That is a different subspace, and it produced a residual of
1.72 on perfectly clean twists. The residual lives in the orthogonal complement
of the **image** of J, which is null(Jᵀ), not null(J). Caught by a numerical
check before it shipped.

### 2.4 What the residual physically *is* — the crown-jewel result

Look at the rows of J again. Rows 1 and 4 (FR, RL) share the translational
part `(u + v)`. Rows 2 and 3 (FL, RR) share `(u − v)`. So **each diagonal pair
can measure yaw rate on its own**, by differencing, with the translational
part cancelling exactly:

```
ω_FR − ω_RL = (2·K_outer/r)·ω        →   ω̂_outer = r(ω_FR − ω_RL) / (2·K_outer)
ω_RR − ω_FL = (2·K_inner/r)·ω        →   ω̂_inner = r(ω_RR − ω_FL) / (2·K_inner)
```

**Two independent measurements of the same physical quantity, using two
different lever arms.** Now compute their difference:

```
ω̂_outer − ω̂_inner  =  (r / (2·K_outer)) · s
```

> ### **The slip residual is exactly the disagreement between the robot's two independent yaw-rate estimates, one per diagonal pair — scaled by a constant.**

And the estimate the odometry node actually publishes is their **mean**:

```
ω_z = (r/4)( ω_FR/K_o − ω_FL/K_i + ω_RR/K_i − ω_RL/K_o )  =  ½(ω̂_outer + ω̂_inner)
```

**Sum and difference of the same two numbers.** The signal and its own error
bar come from one measurement. That is a complete, self-contained story with a
derivation, a physical meaning, and a working implementation — and it exists
*because* l₁ ≠ l₂ gives the two pairs different lever arms.

### 2.5 A discrepancy found by auditing, and the honest verdict

The journal's §2.5 gives a third form:

```
ω_z = r / (2(l₁ + l₂ + 2d)) · ( ω_FR − ω_FL + ω_RR − ω_RL )
```

Note that `l₁ + l₂ + 2d = K_outer + K_inner = 1.05138` exactly. Rewriting, this
is the **K-weighted mean** of the same two estimates:

| Estimator | w_outer | w_inner |
|---|---|---|
| `odometry_publisher.py` | 0.5000 | 0.5000 |
| Journal §2.5 | 0.5333 | 0.4667 |
| **Minimum-variance** (weights ∝ K², since the inner pair's shorter lever arm makes it noisier) | **0.5663** | **0.4337** |

Both implementations are **unbiased** — verified to 1.7e-16 over 20 000 random
twists. Under equal per-wheel noise, the extra yaw-rate noise standard
deviation is:

- equal weighting: **+0.89%**
- §2.5's K-weighting: **+0.22%**

**Verdict: do not change the code.** A 0.89% noise penalty cannot produce
10.53° of heading drift over 18 m; that drift is physical slip on tile. This is
an excellent exam answer and a poor engineering priority — and the ability to
tell those apart is what a review is testing.

---

## 3. Odometry and where its error comes from

### 3.1 Integration

Body velocities are integrated in the **world** frame each tick, using the
midpoint rule for heading (evaluating the rotation at θ + ½·ω·Δt rather than
at θ), which removes the first-order error of Euler integration on a turn:

```
θ_mid = θ + ½·ω·Δt
x += ( u·cos θ_mid − v·sin θ_mid )·Δt
y += ( u·sin θ_mid + v·cos θ_mid )·Δt
θ += ω·Δt
```

**This integration is verified exact.** `wheel_forensics.py` re-integrates a
whole run offline from raw encoder CSV: max divergence from the live `/odom`
**0.0054 m**, final divergence **0.0000 m**. The integrator is not a suspect.

### 3.2 `lateral_scale = 0.92`

Mecanum strafe is produced by roller side-slip, and rollers scrub. Measured:
wheel odometry **over-reported strafe by ~25%** before correction. `lateral_scale`
is a single empirical scale factor on `v`.

**Be ready to state its limits honestly**: it is one constant, calibrated on
one floor, for one payload. It is a correction, not a model. That honesty is
worth more than defending it.

### 3.3 Where the 1.27% actually goes

| Source | Contributes to |
|---|---|
| Roller scrub during strafe | Lateral position, partly corrected by `lateral_scale` |
| Wheel-radius error | Scale error, proportional to distance |
| Uneven tile flooring (observed) | Random walk in both axes |
| Unequal normal loads (45 kg, off-centre CoM) | Differential slip between the diagonals — **exactly what s measures** |
| Encoder quantisation | Negligible with hardware PCNT |

Error grows roughly as **distance travelled** for scale-type sources and as
**√distance** for random-walk sources. Heading error is the expensive one,
because a heading error θ at distance R from the origin costs a position error
of about **2R·sin(θ/2)** — the lever-arm relation, and the same one that
explained the SLAM corrections in §5.5.

---

## 4. Frames and TF — where most robotics marks are won or lost

### 4.1 The three frames (REP-105)

| Frame | Property | Owner |
|---|---|---|
| `base_link` | Rigidly attached to the robot | — |
| `odom` | **Continuous, smooth, never jumps.** Drifts without bound | `odometry_publisher` |
| `map` | **Bounded error, but discontinuous — it jumps** | SLAM, or AMCL |

The chain is `map → odom → base_link`. **Both properties are needed and they
are mutually exclusive**, which is why there are two frames and not one:

- Controllers need `odom` because a jump in the feedback signal makes a
  velocity controller do something violent.
- Goals need `map` because a frame that drifts without bound cannot hold a
  fixed destination.

**`map→odom` is not "where the robot is." It is the accumulated correction
between the two.** On 28 Aug that transform absorbed **11.08 m** across
21.85 m driven.

### 4.2 This robot's deliberate non-REP-103 convention

REP-103 says +X forward, +Y left. **This robot uses +X = right, +Y = forward**
for `base_link`, `odom` and `map`, fixed in §17.38.

Be ready to (a) state it, (b) say it is non-standard, and (c) say why it is
consistent: the convention is applied at the *publication* boundary
(`pub_x = −y, pub_y = +x`), so every consumer sees one convention, and the
composition `R(corr)·odom + corr` reproduces the map pose to four decimals.

**The lesson attached to it is the valuable part.** An axis error was
repeatedly "fixed" in the dashboard's rendering, which made the symptom vanish
while the fault stayed in the transform tree — and it hid the real bug for two
weeks. **A display fix for a data problem is worse than no fix, because it
removes the evidence.**

---

## 5. SLAM — front end and back end

### 5.1 The two halves, and why the distinction is the whole project

| | Front end | Back end |
|---|---|---|
| Job | Where does *this* scan go? | Are *all* poses mutually consistent? |
| Method | Scan matching against recent scans | Non-linear least squares over the pose graph |
| Runs | Every scan | On loop closure |
| Moves nodes? | **No** | **Yes** |
| Moves `map→odom`? | **Yes** | Yes |

**This table is the finding of the last three sessions.** Two instruments
appeared to contradict each other: `graph_residuals.py` reported
`moved=0, max_shift=0.000` for 645 s through **19 loop closures**, while
`run_analyzer.py` reported **48 correction events** on the same drive. Both
correct. The tool watches pose-graph *node positions*; `map→odom` is also moved
by the front end, which touches no node.

**Diagnostic rule worth stating in the report:** *if the pose jumps and the
graph did not move, it is the front end.*

### 5.2 Correlative scan matching (the front end here)

`slam_toolbox` inherits Karto's correlative matcher:

1. Rasterise recent scans into a **correlation grid**, blurred by
   `correlation_search_space_smear_deviation` (0.1) so near-misses still score.
2. Take the **prior** — the odometry-propagated pose.
3. **Brute-force search** a window around it:
   - translation: `correlation_search_space_dimension` **full width**, so
     ±dim/2, stepped by `correlation_search_space_resolution` (0.01 m)
   - rotation: ±`coarse_search_angle_offset`, stepped by
     `coarse_angle_resolution` (default 2°)
4. Score each candidate by summing grid values under the transformed scan.
5. **Penalise deviation from the prior**, scaled by
   `distance_variance_penalty` and `angle_variance_penalty`. In Karto's form
   the penalty *decreases* as the variance parameter grows — so **raising them
   means trusting odometry less.**
6. Refine at `fine_search_angle_offset`.

**Understand step 5 and you understand the bug.** These two parameters were
raised above stock (0.7 vs 0.5, 1.2 vs 1.0) on the reasoning that "wheel
odometry over-reports strafe by 25%." **That premise predates `lateral_scale`
and is now false.** The same odometry has since closed a 4 m path to 1.1%. The
config is currently instructing the matcher to distrust its best input.

### 5.3 Why the search window is the whole story

Between two consecutive pose-graph nodes, 0.36 m apart, odometry's expected
error is about **4 mm**. A 0.7 m window lets the matcher place each scan up to
0.35 m from the prior — **about 90× the actual uncertainty of the thing it is
allowed to overrule.**

Measured, and the strongest result in the project because it was **predicted
before the test**:

| Window | Largest correction ÷ half-width |
|---|---|
| 0.7 | **0.96** |
| 0.3 | **1.05** |

The corrections **scale with the parameter and saturate at the boundary either
way**. A matcher that always lands on the edge of its search window is telling
you the window, not the geometry, is setting the answer.

### 5.4 A second, unadvertised benefit: it is also a CPU fix

Candidate poses evaluated per scan ≈ (dim/res)² × (2·angle_offset/angle_res):

| Config | Translational | Angular | Candidates |
|---|---|---|---|
| Stock-ish (0.7, ±20°) | 70² = 4900 | ~21 | ~103 000 |
| Stage C + D (0.3, ±10°) | 30² = 900 | ~11 | **~9 900** |

**Roughly 10× fewer.** On a Pi already missing its control-loop deadline, an
accuracy fix that is also a compute fix is the best kind available.

### 5.5 The lever-arm insight

The 1047 s drive threw a **0.696 m** correction against a deployed
translational half-width of **0.150 m** — 4.6× the window, so it cannot be
translational. Test it against a pure yaw about the map origin,
**Δp = 2·R·sin(θ/2)**:

| corr | yaw | R | predicted | ratio |
|---|---|---|---|---|
| 0.696 | −18.40° | 2.06 m | 0.660 | 0.95 |
| 0.500 | 15.00° | 2.13 m | 0.555 | 1.11 |
| 0.261 | −7.20° | 1.94 m | 0.244 | 0.93 |

**18.40° is 92% of the stock 20° `coarse_search_angle_offset`** — the same
saturation signature on the axis nobody had closed. Honest caveat: the model
explains 3.59 m of the 4.80 m total; smaller events fit poorly, so translation
still contributes at short range.

### 5.6 Occupancy grids and log-odds

Each cell holds a **log-odds** value `l = log(p / (1−p))`. Bayesian update
becomes addition:

```
l_t = l_{t−1} + l_sensor(z) − l_0
```

Three reasons this representation is used: updates are additive (cheap),
values never saturate to exactly 0 or 1 (evidence remains reversible), and
independence between cells makes the update local.

### 5.7 Pose-graph optimisation (the back end)

Nodes are poses; edges are measured relative transforms with an information
matrix Ω (inverse covariance). Minimise:

```
F = Σ_ij  e_ij(x_i, x_j)ᵀ · Ω_ij · e_ij(x_i, x_j)
```

Solved by Ceres with `SPARSE_NORMAL_CHOLESKY` and Levenberg–Marquardt. Sparse
because each node touches few others.

**Loop closure** adds an edge between two non-consecutive nodes, which is what
lets accumulated drift be distributed backwards over the whole trajectory.

### 5.8 Why loop closure produced nothing for months — a structural answer

`loop_match_minimum_chain_size` is 8. **A graph with 8 nodes cannot contain an
edge spanning more than 8 nodes.** Every prior session's `loops = 0` was
therefore *guaranteed by construction, not observed*. The first drive long
enough to make closure structurally possible (62 nodes, 93 edges) produced
**19 closures** immediately.

**And the map still folded.** The closures fired and were **inert** — they
changed nothing while the estimate was half a metre wrong. That is worth saying
precisely, because "we enabled loop closure and it worked" would be false.

### 5.9 Aliasing — why this environment is hard

Two measured conditions, not assumed:

1. **107 of 430 beams are permanently NaN** — a 90° blind wedge behind the
   mast, in a fixed *body-relative* direction. A quarter of every scan is
   absent, always.
2. **The space is a junction with several look-alike radiating aisles.** Scan
   matching has genuinely ambiguous constraints, not merely noisy ones.

Because a genuine revisit scores lower with a quarter of the scan missing, the
response thresholds were **relaxed** from stock (0.25/0.35 vs 0.35/0.45),
trading a higher risk of a *wrong* closure for any closure at all — the right
trade when the measured state was zero closures and half a metre of drift.

Evidence of that trade going wrong: **3 corrections within 1.0 m of a
doubled wall.** n = 3 — **suggestive, not conclusive**, and it must be
presented that way. Interestingly the doubled-wall clusters sit *within*
individual arms (0.29 m and 0.38 m apart in the same arm), not across
different arms — which argues against "matched the wrong aisle" and for
"matched the right aisle at a drifted pose."

---

## 6. Costmaps and planning

### 6.1 The one idea: the robot is not a point

A planner that treats the robot as a point will plan through a gap the robot
cannot fit. Two ways out — inflate the obstacles, or check the full footprint
polygon. This robot does **both**, because at 1.12 × 0.48 m it is long and thin
and a circular approximation is badly wrong.

### 6.2 Inflation

Beyond the inscribed radius, cost decays exponentially with distance:

```
cost(d) = 252 · exp( −cost_scaling_factor · (d − r_inscribed) )
```

**`inflation_radius` must exceed the robot's padded circumscribed radius**, or
a footprint-aware checker can never rule a pose out cheaply and must run a full
polygon test every time. Here: corner (0.24, 0.56) plus 0.01 padding gives
`hypot(0.25, 0.57) = 0.6224 m`, so **`inflation_radius = 0.65`**. That number
is derived, not chosen — a good thing to be asked about.

### 6.3 Layered costmaps

| Layer | Source | Persists? |
|---|---|---|
| Static | the saved map | yes, fixed |
| Obstacle | live `/scan_reliable` | no, transient |
| Inflation | computed from the two above | — |

**This is the answer to "doesn't it need to keep mapping to avoid new
obstacles?"** No. The local costmap is rebuilt from live LiDAR every cycle
whether or not SLAM is running. A pallet left in an aisle appears in the
obstacle layer within one scan. **The map is remembered and stable; obstacle
avoidance is live and reactive. Both, without continuous SLAM.**

### 6.4 Global planner — NavFn

Dijkstra (or A*) over the global costmap. Complete and optimal on the grid,
cheap, and it needs no kinematic model — which is fine here because a
holonomic base can follow any geometric path.

### 6.5 Local controller — MPPI

Sampling-based model-predictive control:

1. Sample `batch_size` control sequences over a horizon, as noise around the
   previous solution.
2. Roll each forward through the motion model.
3. Score each: path alignment + goal distance + **obstacle cost with
   `consider_footprint: true`** + control smoothness.
4. Weight by `exp(−S(τ)/λ)` and take the weighted mean as the command.

**Why MPPI and not DWB for this robot:** DWB natively samples `(vx, vθ)`
circular arcs. A mecanum base's whole point is independent `vy`, and MPPI
treats it as a first-class control dimension. **The honest cost:** MPPI is
`O(batch × horizon)` per cycle and this Pi is missing its deadline —
which is why `batch_size` is the first CPU lever.

### 6.6 Behaviour trees and lifecycle nodes

- **`bt_navigator`** runs an XML behaviour tree: `ComputePathToPose` →
  `FollowPath`, with recoveries (`spin`, `backup`, `wait`) on failure. Recovery
  logic is *data*, not code — it can be changed without recompiling.
- **Lifecycle nodes** have explicit `unconfigured → inactive → active` states,
  managed by `lifecycle_manager`. **Bringup is all-or-nothing**: one plugin
  that fails to load aborts the whole stack. This project has been bitten by
  that once already, and the AMCL plugin-name risk is the same shape.

---

## 7. AMCL — localisation in a known map

Monte Carlo Localisation: represent the pose belief as a set of weighted
particles, and for each scan —

1. **Predict:** move every particle by the odometry increment plus noise
   (the motion model).
2. **Update:** weight each particle by how well the scan matches the known map
   from that pose (the measurement model — likelihood field).
3. **Resample:** draw a new particle set proportional to weight.

**Adaptive** = KLD sampling: use many particles when uncertain, few when
converged.

`robot_model_type` must be an **omnidirectional** motion model. A differential
model assumes lateral velocity is zero, which on a mecanum base is
structurally false — it would inject the strafe as unexplained noise and
inflate the covariance every time the robot moves sideways.

**AMCL vs SLAM, in one line for the review:**

> **SLAM corrects the map around a drifting robot. AMCL corrects the robot
> inside a fixed map. Navigation needs the second one.**

---

## 8. Motor control

Per-motor velocity control on the ESP32 at 50 Hz, with hardware PCNT for
encoder decoding:

```
u = K_ff · ω_target  +  K_p·e  +  K_i·∫e dt  +  K_d·ė       e = ω_target − ω_actual
```

**Feedforward carries the load; PID cleans up the residual.** At 45.54 kg with
mecanum rolling friction, the PWM needed just to *hold* a speed is large and
predictable — that is `K_ff`'s job, and making the integrator discover it every
time would be slow and would wind up.

Practical elements that are all real bug-fixes here: anti-windup, derivative
filtering, deadband, and a **sticky** E-STOP (a safety state that clears itself
is not a safety state).

**Result:** 0.043–0.046 rad/s RMS on all four motors, zero saturation, zero
sign mismatch, no dead feedback. ✅

---

## 9. Sensing

YDLIDAR X4 Pro, 10 m rated range, ~11.5 Hz. `max_laser_range` was **12.0** for
months — inherited from an originally-planned RPLiDAR — which fed the matcher
returns beyond the sensor's rated range **as if they were geometry**. Corrected
to 10.0.

QoS matters: the driver publishes `/scan` best-effort; `scan_relay.py`
republishes it as `/scan_reliable`, because a best-effort scan silently dropped
under CPU load becomes a costmap that thinks the corridor is empty.

**The blind sector is a navigation problem, not just a mapping annoyance.**
The mask makes 107 beams NaN rather than 0 — a 0 range would be read as an
obstacle at the sensor origin, which would make the robot refuse to move.

---

## 10. Question bank

### Tier 1 — will almost certainly be asked

**Q. What is SLAM?**
Simultaneous Localisation and Mapping: building a map while simultaneously
locating yourself in it — a chicken-and-egg problem, because a map needs known
poses and pose estimation needs a map. Solved by alternating: match each new
scan against the map so far (front end), then periodically re-optimise all
poses for global consistency (back end).

**Q. Why mecanum wheels?**
Narrow aisles. A differential-drive robot must rotate to change direction; a
1 m long robot rotating in a 1.2 m aisle sweeps a circle it does not have room
for. Mecanum wheels strafe sideways without rotating. The cost is slip —
rollers scrub — which is why odometry needed `lateral_scale` and why the slip
residual exists.

**Q. Why LiDAR and not a camera?**
Direct metric range, works in the dark, no scale ambiguity, and 2D LiDAR SLAM
is mature. A camera would add semantics (reading rack labels) — a sensible
*addition*, not a replacement.

**Q. What is odometry, and how accurate is yours?**
Dead reckoning from wheel encoders through the forward-kinematics model.
**1.27% of distance travelled over 21.85 m — 0.229 m — with 10.53° of heading
drift.** Verified: the integration itself is exact to 0.0000 m; the error is
physical slip.

**Q. Why a Raspberry Pi and an ESP32?**
Separation of timescales. The ESP32 runs a hard 50 Hz control loop with
hardware counters and no OS scheduler in the way; the Pi runs SLAM, planning
and the web UI where soft deadlines are acceptable. **Putting the motor loop on
Linux would make it jittery, and the current 7.5–13.7 Hz control-loop
starvation on the Pi is exactly the evidence for why.**

### Tier 2 — will be asked if the reviewer engages

**Q. Why four wheels for three degrees of freedom? Isn't one redundant?**
Yes — and the redundancy is *used*. Because J is 4×3 of rank 3, any consistent
wheel-velocity vector lies in a 3-D subspace of ℝ⁴. The component orthogonal to
it cannot be produced by any rigid-body motion, so it measures slip directly:
`s = ω_FR + 1.1427·ω_FL − 1.1427·ω_RR − ω_RL`. Physically it is the
disagreement between the two independent yaw-rate estimates, one per diagonal
pair — see §2.4.

**Q. What is a costmap and why inflate it?**
A grid of traversal costs. Inflation grows obstacles by the robot's radius so
the planner can reason about a point while producing paths a real body fits
through. Here `inflation_radius = 0.65 m`, derived from the padded
circumscribed radius 0.6224 m.

**Q. What are the three frames for?**
`odom` is smooth but drifts; `map` is bounded but jumps. Controllers need
smooth; goals need bounded. `map→odom` is the correction between them.

**Q. How do you avoid an obstacle that wasn't there when you mapped?**
Layered costmaps. The static layer is the saved map; the obstacle layer is
rebuilt from live LiDAR every cycle. New obstacles appear within one scan.
Continuous SLAM is not required and would cost stable coordinates.

**Q. Why 2 cm goal tolerance is wrong.**
It was 2 cm, which is smaller than the pose jitter of the estimate itself. A
controller cannot converge on a target tighter than its own noise floor; it
oscillates and the progress checker eventually aborts. Corrected to 0.12 m.

### Tier 3 — the deep ones

**Q. Your map is worse than your odometry. Why?**
Measured: odometry 0.229 m, SLAM 0.477 m, on the same run. The SLAM front end's
search window is far wider than the odometry prior's real uncertainty — ±0.35 m
of freedom against a ~4 mm per-node error — so where geometry is ambiguous the
matcher prefers an alignment away from a prior that was right. Confirmed by
making the corrections **scale with the parameter**: 0.96 of the half-width at
0.7, 1.05 at 0.3.

**Q. How do you know it's the front end and not loop closure?**
Two instruments. `graph_residuals.py` watched pose-graph node positions for
645 s through 19 closures: `moved = 0`. A back-end re-solve moves nodes.
Meanwhile 48 correction events were logged with `odom→base_link` stepping
normally. The corrections must therefore come from the half that moves
`map→odom` without moving nodes — the front end.

**Q. What is the biggest weakness of the current system?**
Heading. Odometry drifts 10.53° over 18 m, and no amount of SLAM tuning fixes
that — it is the ceiling on how good the prior can be. The known remedy is IMU
fusion (Galati et al. report ~88% heading-drift reduction), deliberately
deferred so that one failure mode is fixed at a time.

**Q. How do you know your map is folded, rather than your measurement being
wrong?**
Two independent instruments agreeing. A geometric detector on the saved grid
found doubled-wall clusters with gaps of 0.23, 0.23, 0.38, 0.41 and 0.53 m. A
tape measure against a floor mark found a **0.477 m** terminal miss. One is a
spatial artefact in the raster; the other is a physical measurement. They
report the same half-metre.

---

## 11. The three questions that can go badly

### 11.1 "So it doesn't actually work yet?"

**Do not get defensive, and do not overclaim.** The honest answer is stronger:

> *Twelve of the thirteen links in the autonomy chain are measured and
> working, including autonomous goal-reaching — two goals completed, 25.9 s
> and 21.0 s. The one broken link is the map-to-odom correction, and we have
> localised it to a specific parameter family in the SLAM front end, confirmed
> by predicting the correction magnitude before a test and then producing it.
> What we do not have yet is an accepted commissioning map.*

A reviewer who hears a precisely-bounded open problem hears an engineer. One
who hears "it basically works" starts probing for what you are hiding.

### 11.2 "Isn't the asymmetry just a manufacturing defect you rationalised?"

> *It's a design constraint that became the project's research question. The
> 70 mm offset is real and it forces every kinematic path to carry two lever
> arms instead of one — and several early bugs came from code that quietly
> collapsed them to one K. But the asymmetry also buys something a symmetric
> platform doesn't have: the two diagonal pairs measure yaw with **different**
> lever arms, so their disagreement is an observable slip signal. On a
> symmetric base the same residual exists but degenerates to the equal-weight
> case.*

### 11.3 "Why not just buy a commercial AMR?"

> *For a warehouse, you would. This platform exists for the case commercial
> AMRs don't serve: a 1 m long, 250 mm wide chassis for aisles under 350 mm
> clear. Commercial mecanum AMRs are square and symmetric because that's easy
> to control. The narrow, long, asymmetric geometry is the thing being
> researched — and it's what makes the kinematics non-standard.*

---

## 12. What to study, in priority order

| Priority | Topic | Where |
|---|---|---|
| 1 | §2 in full — derive the slip residual on paper without looking | this doc |
| 2 | §4 frames, §5.1 front-end/back-end | this doc; `docs/SLAM_Theory.md` |
| 3 | §1 numbers — memorise | this doc |
| 4 | §6 costmaps, inflation, MPPI | `docs/Navigation_Theory.md` |
| 5 | §7 AMCL | `docs/Navigation_Theory.md` §6.3 |
| 6 | §10 question bank — say the answers out loud | this doc |
| 7 | The evidence itself: §17.38–§17.42 | `docs/Research_Journal.md` |

**External reading, in order of value:**

1. Grisetti, Kümmerle, Stachniss, Burgard — *A Tutorial on Graph-Based SLAM*
   (2010). The single best source for §5.7.
2. Censi — *An ICP variant using a point-to-line metric* (2008). §5.2.
3. Thrun, Burgard, Fox — *Probabilistic Robotics*, ch. 4 (particle filters),
   ch. 8 (MCL), ch. 9 (occupancy grids).
4. Macenski et al. — *slam_toolbox* (JOSS 2021) and the *Nav2* paper.
5. Galati et al. (2022) on mecanum odometry drift — the source of the 88%
   heading-fusion figure.

---

## 13. A closing note on how to present this

The strongest thing this project has is not the robot. It is the **record**:
predictions written before tests, claims retracted when data killed them, and
every number carrying an evidence grade.

Show the retraction of the "strafe is the weak axis" lead. Show the prediction
table written before the Stage C test. Show the two instruments that appeared
to contradict each other and the reconciliation that turned out to be the
finding.

Most projects at this level present only successes. Presenting a falsification
record is rarer, harder to fake, and much more convincing.
