# Navigation Theory — Costmaps, Footprint, and Autonomous Path Planning

Companion to `SLAM_Theory.md`. That document covers how the robot builds a map
and knows where it is; this one covers how it decides **where to go and how to
get there without hitting anything**. Same convention: every claim traces to a
paper in `research_articles/`, because the point is to know *why* a choice is
right, not just that it runs.

**Scope.** 2D navigation on a planar floor (SE(2) — x, y, heading). No 3D
mapping, deliberately: the robot drives on a flat warehouse floor, the LiDAR
is a single horizontal scan plane, and every algorithm below is formulated in
2D. Adding a third dimension would cost compute and buy nothing here.

---

## 1. The one idea that makes obstacle avoidance work: the robot is not a point

A path planner searching a grid naturally treats the robot as a dimensionless
point — it finds a sequence of free cells from A to B. But a real robot is a
rigid body with extent. A path that threads a point through a gap narrower than
the robot is not a path; it's a collision.

There are two ways to reconcile this, and understanding which one is in play
matters for every parameter below:

1. **Footprint (exact).** Declare the robot's outline as a polygon in the base
   frame. For every candidate pose, test whether that polygon — rotated and
   translated to the pose — overlaps any occupied cell. Exact, but expensive:
   a full polygon-vs-grid test per candidate pose.

2. **Inflation (approximate, and what actually gets used).** Instead of growing
   the robot, grow the *obstacles*. Expand every occupied cell outward by the
   robot's radius, then plan with a point robot on the inflated grid. Cheap —
   the expansion is computed once per costmap update, and planning is then a
   plain grid search.

`nav2_costmap_2d` uses both, at different stages: inflation for fast global
planning, exact footprint collision-checking for local trajectory validation.

### 1.1 Inflation, precisely

Two radii characterize any footprint polygon:

- **Inscribed radius** $r_{\text{in}}$ — radius of the largest circle that fits
  *inside* the footprint. For a rectangle of width $w$: $r_{\text{in}} = w/2$.
- **Circumscribed radius** $r_{\text{circ}}$ — radius of the smallest circle
  *containing* the footprint. For an $l \times w$ rectangle centered on the
  origin: $r_{\text{circ}} = \tfrac{1}{2}\sqrt{l^2 + w^2}$.

The costmap assigns each cell a cost in $[0, 254]$ by distance $d$ to the
nearest obstacle:

$$
c(d) = \begin{cases}
254 \ (\text{LETHAL}) & d = 0 \quad \text{(the obstacle cell itself)}\\
253 \ (\text{INSCRIBED}) & 0 < d \le r_{\text{in}}\\
\left\lceil 252\, e^{-\alpha (d - r_{\text{in}})} \right\rceil & r_{\text{in}} < d \le r_{\text{inflation}}\\
0 \ (\text{FREE}) & d > r_{\text{inflation}}
\end{cases}
$$

where $\alpha$ is `cost_scaling_factor` and $r_{\text{inflation}}$ is
`inflation_radius`.

The semantics of that middle band are the part worth internalizing:

- $d \le r_{\text{in}}$ is marked `INSCRIBED` (253) because **any** robot pose
  whose center is that close to an obstacle is in collision *regardless of
  heading* — the inscribed circle is inside the footprint at every rotation.
  Planning must treat these as blocked.
- $r_{\text{in}} < d \le r_{\text{circ}}$ is where collision *depends on
  heading*. A point-robot planner cannot resolve this, which is exactly why the
  local controller re-checks the true polygon.
- Beyond $r_{\text{circ}}$, the decaying cost is not a collision statement at
  all — it's a *preference*. It biases paths toward the middle of free space
  without forbidding proximity.

**Consequence for a narrow-aisle robot, and this is a real trap:** setting
`inflation_radius` too large makes an aisle that the robot physically fits
through appear impassable, because inflation from both walls meets in the
middle and the planner sees no free corridor. Inflation radius must be tuned
against the *narrowest aisle the robot must traverse*, not set generously "for
safety." Safety comes from the footprint check; inflation is about path
preference.

### 1.2 Layered costmaps

`nav2_costmap_2d` composes the costmap from ordered **layers**, each of which
may write to the master grid (Lu, Hershberger & Smart, 2014 — the paper this
architecture comes from directly). The layers this robot uses:

- **Static layer** — the SLAM/map-server occupancy grid. Long-lived structure.
- **Obstacle layer** — live LiDAR returns. Does two distinct things per scan:
  **marking** (a beam that terminates at range $r$ marks that cell occupied)
  and **clearing** (raytracing along the beam from the sensor to $r$, clearing
  every cell passed through). Clearing is what lets a moved obstacle disappear
  rather than smearing across the map forever.
- **Inflation layer** — applies §1.1 to whatever the layers beneath wrote.

Lu et al.'s central argument is that keeping these separate and ordered — rather
than fusing all sensor data into one grid — is what makes the system
maintainable and context-sensitive: each layer owns its own semantics and update
rule, and layers can be added (keepout zones, speed-restricted zones) without
touching the others. That extensibility is directly relevant here: a future
"no-go zone near the loading area" is a new layer, not a rewrite.

---

## 2. Global planning: finding a path at all

The global planner searches the global costmap for a path from the current pose
to the goal. Nav2's default `NavfnPlanner` implements Dijkstra or A\* over the
grid.

A\* minimizes $f(n) = g(n) + h(n)$ — cost-so-far plus an admissible heuristic
(Euclidean distance to goal). With $h \equiv 0$ it degenerates to Dijkstra:
still optimal, but expanding many more nodes. A\* is the right default; the
heuristic costs nothing and prunes heavily.

**`allow_unknown` is the parameter that decides whether exploration is possible
at all.** With `allow_unknown: false`, the planner refuses to route through
cells the map marks unknown. On a fully pre-mapped floor that's the safe choice.
But when SLAM is building the map live and most of the world is still unknown
(the placement-trial maps were **85% unknown**, §17.4), it means the planner can
essentially never find a path to anywhere interesting. For navigating an
initially-unknown space, this must be `true`, with the local costmap and
footprint check providing the actual safety.

---

## 3. Local control: turning a path into wheel commands

The global path is geometric — a line through free space, computed on a
possibly-stale map, ignoring robot dynamics. The local controller converts it
into velocity commands at ~20 Hz, reacting to obstacles the global map doesn't
know about.

### 3.1 DWA / DWB — the incumbent, and why it is a defensible starting point

The Dynamic Window Approach (Fox, Burgard & Thrun, 1997 — 3677 citing
publications; `dwb_core` is its Nav2 descendant) searches directly in
**velocity space** rather than position space. Its three ideas:

1. **Search over velocities**, $(v_x, v_y, \omega)$, not positions. Each
   candidate velocity, held for a short horizon, implies a trajectory.
2. **Restrict to the dynamic window** — only velocities reachable from the
   current velocity within one control period given acceleration limits. This
   is what makes it dynamically feasible rather than a kinematic fantasy:
   $V_d = \{(v,\omega) : v \in [v_c - \dot{v}\Delta t,\ v_c + \dot{v}\Delta t]\}$.
3. **Admissibility** — discard any velocity from which the robot cannot stop
   before hitting the nearest obstacle on that trajectory:
   $v \le \sqrt{2 \, d(v,\omega)\, \dot{v}_b}$.

Surviving candidates are scored by a weighted sum of *critics* — in DWB, plugins
scoring goal progress, path alignment, obstacle proximity (via the true
footprint), and oscillation. Highest score wins; its velocity is published.

The 1997 paper is explicit that incorporating the robot's dynamics — not just
its kinematics — is the contribution, which is why it works at speed where
purely geometric reactive methods fail.

**Known limitation, and it matters for narrow aisles:** because DWA only
considers velocities within the current dynamic window and does not reason about
free-space connectivity, it is susceptible to **local minima** — most classically
a U-shaped obstacle or dead-end alcove, where the locally-best velocity leads
into a trap the controller cannot see out of (Li, Liu & Liu, 2017, who diagnose
exactly this and note the standard DWA additionally ignores robot size when
judging whether a gap is traversable). In Nav2 this is mitigated, not solved, by
the global planner replanning and by behavior-tree recovery behaviors.

### 3.2 MPPI — the upgrade path, and the honest cost

Model Predictive Path Integral control (Williams et al., 2016; extended with the
full information-theoretic derivation in Williams et al., 2018) takes a
different route to the same problem. It is a sampling-based stochastic optimal
control method: sample $K$ noisy control sequences, roll each forward through a
dynamics model over a horizon $T$, evaluate a cost per rollout, and form the
update as an **importance-weighted average** rather than picking a single best:

$$
u_t \leftarrow \sum_{k=1}^{K} w_k\, u_t^{(k)}, \qquad
w_k = \frac{\exp\!\left(-\tfrac{1}{\lambda} S(\tau_k)\right)}{\sum_j \exp\!\left(-\tfrac{1}{\lambda} S(\tau_j)\right)}
$$

where $S(\tau_k)$ is the rollout's accumulated cost and $\lambda$ the
temperature. Williams et al. derive this from the relationship between free
energy and relative entropy (KL divergence), giving a soft-min over trajectories
rather than DWA's hard arg-max over a discretized grid.

Why it's attractive here: it is **derivative-free**, handles non-smooth costs,
and — the practically relevant part — samples the full continuous
$(v_x, v_y, \omega)$ space, which suits a mecanum platform's genuine
omnidirectionality better than DWB's coarse `vy_samples` discretization.

Why not to start with it: the method's power comes from evaluating many rollouts
per control cycle, and Williams et al.'s own experiments run it on a **GPU**.
This robot is a Pi 5 with no GPU (the same constraint that ruled out RBPF-SLAM
in `SLAM_Theory.md` §5). Nav2's MPPI implementation is CPU-optimized and
vectorized, so this is a question of measurement, not a foregone conclusion —
but it is a question that must be *answered with a CPU measurement* rather than
assumed either way.

**Decision when written: start with DWB, instrument the CPU, treat MPPI as a
measured upgrade. Superseded — this project now runs MPPI** (`motion_model:
Omni`, `nav2_params.yaml`, decided and deployed in Research_Journal.md §17.23).
Worth recording *why* the original "start conservative" reasoning above turned
out wrong in practice, not just the new conclusion: DWB's `RotateToGoalCritic`
has a bit-exact rejection mechanism (`dwb_critics/rotate_to_goal.cpp`) that
throws out every candidate trajectory once the robot is near a goal but not yet
exactly aligned — read from source, not inferred from symptoms, after DWB
repeatedly failed rotation-only goals on hardware (§17.21–§17.22). That failure
mode is structural: DWB's critics can individually **reject** a trajectory
(reduce the candidate set to zero — "No valid trajectories!"), where MPPI's
critics only ever **add cost** to a trajectory (`data.costs += ...`, verified
directly against `nav2_mppi_controller`'s critic source for every critic this
robot enables). A weighted sum over K sampled trajectories cannot reach zero
candidates the way a sequence of hard admissibility filters can. The §3.2
tradeoff above — MPPI's per-cycle cost being the open question, "answered with
a CPU measurement, not assumed" — was answered on hardware: `batch_size: 500`
at `20 Hz` with full-footprint collision-checking held the Pi 5's control loop
rate with no `Control loop missed its desired rate` warnings (§17.23), so the
GPU-oriented origin of the algorithm (Williams et al. ran it on GPU) did not
turn out to be the binding constraint on this platform after all.

Two stock MPPI critics — `PathAngleCritic` and `PreferForwardCritic` — are
deliberately **not** enabled here. Both assume the robot's `+X` axis is its
forward direction (REP-103). This robot's `base_link` is not REP-103 by design
(see the AXES note in `nav2_params.yaml`), so either critic would silently
penalize the robot's actual forward motion as if it were sideways travel — the
same axis-convention bug class that has recurred five times on this project
(§17.14, §17.17, §17.19, §17.23).

---

## 4. Why self-occlusion is a navigation problem, not just a mapping annoyance

The robot's own structure — the rear lift mast and electronics stack — sits
inside the LiDAR's 360° sweep. Two distinct failure modes follow, and they need
different treatment:

- **Shadowing.** Nothing behind the structure is ever observed. Those cells stay
  `unknown` forever. With `allow_unknown: true` this is tolerable; the robot
  simply has no information there.
- **False permanent obstacles.** This is the damaging one. If the structure is
  beyond the LiDAR's 0.12 m minimum range, it *returns a valid hit every scan*.
  The obstacle layer marks those cells occupied. Because they are fixed in the
  robot's frame, they translate and rotate with the robot — a permanent
  obstacle welded to the chassis, at a fixed bearing, that the robot can never
  escape or clear. The inflation layer then expands it, and the planner
  concludes that entire direction is blocked. Everywhere. Forever.

The correct fix is **not** a physical modification and **not** a footprint
change: it is to mark the affected angular sectors as *invalid measurements*
before the scan reaches SLAM or the costmap, so those beams neither mark nor
clear. A beam carrying no information must be dropped, not reinterpreted as
"free" (which would clear real obstacles) or "occupied" (the current bug).

Identifying which sectors: rotate the robot in place in a static environment and
compare scans. **Real features move in the laser frame as the robot rotates;
self-occlusion does not.** That invariance is the discriminator, and it needs no
props, no reference objects, and no physical construction.

**Measured, 13 Aug 2026 (Research_Journal.md §17.15).** The prediction above was
written before any real driving happened; this is the confirmation. `tools/
scan_bearing.py` was run at five headings roughly 90° apart, one full rotation,
against the corrected (post-mirror-fix, post-odometry-fix) `/scan_reliable`.
Cross-checking the five sector tables against each other rather than reading any
one of them in isolation: exactly one contiguous bearing block —
**`-135°` to `-45°` (true bearing, this robot's convention: `0°`=right, `+90°`=
forward, `180°`=left, `-90°`=behind)** — returned a nonzero `<1m` reading in
*every single one* of the five independent headings, at consistent percentages
each time (e.g. the `-90°..-75°` bin read `42%, 43%, 39%, 41%, 40%` across the
five runs — a ~4-point spread despite the robot facing a completely different
way each time). Every other sector that any individual run flagged "always
close" appeared in exactly one run and nowhere else — those are real walls the
robot happened to be facing at that particular heading, correctly *not*
persisting, which is the discriminator working as designed. The single nearest
point across all five scans, independently, clustered at `-104°` to `-125°`
bearing and `0.12–0.13 m` range every time — right inside the identified block,
right at the LiDAR's own minimum range, and the sort of five-way agreement that
is not plausible for a real object at that scale.

**Result: a 90° wedge centred on directly behind the robot** (`-90°` ± `45°`),
not the ~120° ("roughly a third") figure from the original pre-fix,
mirrored-frame measurement in §17.8 — a real refinement now that it has been
re-measured in the corrected frame, per the B.6 item that flagged exactly this.
Consistent with the returns being real-but-phantom rather than shadow (`hits%`
and `<1m%` are equal or nearly so throughout the block — whenever a beam
returns anything there, it is close), the fix per this section's own
prescription is to mask `[-135°, -45°]` as invalid in `scan_relay.py`, not to
mark it occupied or free. Not yet implemented in code as of this measurement;
tracked in B.6.

---

## 5. Putting it together — the autonomy stack for this robot

Two localization sources, never run together — see §6.3 for why. Everything
below `/cmd_vel_nav_out` is shared by both.

```
/scan (best-effort, from ydlidar driver)
   │
   ├─► scan_relay.py ──► /scan_reliable   (QoS bridge, §13.4; the natural
   │                                        place to also mask self-occluded
   │                                        sectors — one node, already in
   │                                        the path, already touching every scan)
   │
   ├─► EITHER slam_toolbox ──► /map + map→odom TF     (mapping.launch.py)
   │      OR  map_server + amcl ──► /map + map→odom   (navigation.launch.py,
   │                                                     §6.3, frozen map)
   │
   └─► nav2_costmap_2d (obstacle layer, both costmaps)

/map ──► global_costmap (static + obstacle + inflation)
              │
              └─► planner_server (NavFn A*) ──► path
                                                 │
local_costmap (obstacle + inflation, rolling) ──►┴─► controller_server (MPPI, §3.2)
                                                        │  + behavior_server (Spin/BackUp/Wait)
                                                        └─► velocity_smoother
                                                              │
                                                        collision_monitor (obstacle
                                                              │            avoidance, §6.2)
                                                        cmd_vel_axis_adapter (TF axes
                                                              │               → wheel axes)
                                                              ▼
                                                        /cmd_vel_nav_out
                                                              │
                          /cmd_vel_manual (joystick/phone) ──┤
                                                              ▼
                                                          twist_mux (manual
                                                              │       wins while active)
                                                              ▼
                                                           /cmd_vel
                                                              │
                                            teleop_asym ──► /wheel_speeds
                                                              │
                                                 esp32_bridge ──► ESP32 (PID)
```

Everything downstream of `/cmd_vel` already exists and is calibrated (Part XII —
the mecanum inverse kinematics and per-wheel PID). Nav2 is being bolted onto a
working velocity-control layer, which is the correct order: **autonomy on top of
a trusted controller, never the reverse.**

**AMCL must not run while SLAM is running.** Both publish the `map→odom`
transform; running both means two nodes fighting over the same TF edge, and the
resulting pose estimate is meaningless. AMCL is for *localizing against a
previously-saved map*; slam_toolbox in mapping mode does both jobs at once. Pick
one per run — `mapping_full.launch.py` for the former, `navigation.launch.py`
for the latter, never both.

---

---

## 6. Concepts from the reference tutorials, checked against this project

A set of introductory SLAM/Nav2 tutorial scripts was reviewed this session
(Research_Journal.md §17.26) alongside `SLAM_Theory.md` and the sections
above. Six concepts recur across that material: SLAM, frontier exploration,
cost-map pathfinding, pure pursuit, obstacle avoidance, and Monte Carlo
localization. Three of the six are already covered in depth elsewhere in this
pair of documents — SLAM in `SLAM_Theory.md` in full, cost-map pathfinding in
§1–2 above. This section covers the remaining three, each checked against
what this project actually runs rather than restated as a generic summary.
None of the three landmark papers below (Yamauchi 1997; Coulter 1992; Thrun,
Fox, Burgard & Dellaert 1999/2001) is yet in `research_articles/` — they are
well-established, widely-cited references, cited here by author/year in the
same spirit as the rest of this document, and worth adding to the local
library if this section's reasoning is built on further.

### 6.1 Frontier exploration — logical, and deliberately not used

Yamauchi (1997) frames autonomous mapping as a repeated choice: find the
boundaries between known-free and unknown space (*frontiers*), pick one to
drive to (commonly weighted by frontier size and travel distance — bigger
frontiers reveal more unmapped area, closer ones cost less to reach), and
repeat until no frontier remains. It is the standard way to make SLAM
*autonomous* rather than manually driven.

**Not used here, and not a gap — a deliberate scope decision.** This project's
mapping stage (Research_Journal.md §17.25's Stage 1, `mapping_full.launch.py`)
is driven manually from the dashboard, specifically because manual driving
lets a human apply domain knowledge frontier selection can't: hug the walls
rather than the aisle centreline (§17.13 — centreline driving produced thin,
poorly-defined "flower petal" map edges instead of solid walls), and translate
rather than rotate wherever possible (§17.20 — pure rotation gives the scan
matcher almost nothing to work with). Automating frontier selection would
have to re-encode both of those hard-won findings as an algorithm before it
could safely replace a person driving. Worth revisiting once a good map exists
and repeated-remapping-of-known-territory becomes the actual cost driver —
not before.

### 6.2 Pure pursuit and obstacle avoidance — both present, neither as a named standalone algorithm

**Pure pursuit** (Coulter, 1992, CMU-RI-TR-92-01) picks a look-ahead point
some distance down the reference path and steers the robot toward it; as the
robot advances, the look-ahead point advances with it. Its entire behaviour
is governed by one tuning knob, the look-ahead distance: too short and the
controller chases small path-tracking errors and oscillates, too long and it
cuts corners. It is a **geometric** path tracker — it has no model of dynamics
or of nearby obstacles; it assumes both are handled elsewhere.

This project's controller is MPPI (§3.2), which is a different mathematical
family (sampling-based stochastic optimal control, not geometric path
following) but **subsumes pure pursuit's actual job as one term in its cost
function.** `PathAlignCritic` and `PathFollowCritic` (`nav2_params.yaml`)
together penalize a sampled trajectory for straying from the reference path
and for making no progress along it — the same "stay near the path, keep
advancing along it" objective pure pursuit encodes geometrically, but folded
into a weighted sum alongside collision cost, goal distance, and heading, and
evaluated over many sampled trajectories rather than one hand-picked
look-ahead point. Pure pursuit is not missing; it's not present as a
separately-named module because MPPI's critic architecture generalizes it.
A standalone pure-pursuit controller would be a reasonable *simpler* fallback
if MPPI's per-cycle cost ever became the binding constraint on the Pi 5 — it
has not (§3.2) — but would need the same non-REP-103 axis handling
`cmd_vel_axis_adapter` provides MPPI today; it does not sidestep that problem,
it inherits it.

**Obstacle avoidance** is not one component either — it is layered, matching
Video 1's description of a live-updated cost gradient around detected
obstacles almost exactly:

1. The **obstacle + inflation costmap layers** (§1.2) mark live LiDAR returns
   and expand them into a cost gradient, so the *planner* routes around
   obstacles before the robot gets close.
2. **`collision_monitor`** (`nav2_slam.launch.py` / `navigation.launch.py`,
   last node before the wheel-axis adapter) is the hard safety layer: it
   forward-simulates the commanded velocity against the true footprint
   polygon in real time and can veto or slow a command the planner already
   approved, independent of costmap staleness. This is the node the §17.20
   comment calls "the one thing on this robot that must not be subtly
   wrong" — it is what `Spin`/`BackUp` recovery behaviours were found
   bypassing in §17.20/§17.21, and fixed to route through.

Both layers were already built before this review; nothing new was needed
here beyond confirming the tutorial's description matches what's deployed.

### 6.3 Monte Carlo localization — AMCL, the Stage-3 localization source

Thrun, Fox, Burgard & Dellaert (1999, extended 2001) formulate localization
as recursive Bayesian state estimation, approximated by a **particle
filter**: a set of $N$ weighted samples (particles), each a hypothesis
$(x, y, \theta)$ for the robot's pose, standing in for the full posterior
$p(x_t \mid z_{1:t}, u_{1:t})$ over poses given all sensor observations $z$
and controls $u$ so far. Each cycle:

1. **Motion update (prediction).** Every particle is moved forward by the
   commanded/measured motion, plus sampled noise drawn from a motion model —
   this is where `alpha1`–`alpha4` (`nav2_params.yaml`'s `amcl:` block)
   enter: they scale how much rotation-from-rotation, rotation-from-
   translation, translation-from-translation, and translation-from-rotation
   noise gets injected per particle, i.e. how much the filter distrusts the
   odometry it's given.
2. **Sensor update (reweighting).** Each particle's weight is scaled by how
   well its hypothesized pose predicts the actual LiDAR scan — `laser_model_
   type: likelihood_field` computes this by comparing each beam endpoint
   against the precomputed distance-to-nearest-obstacle field of the static
   map, over `max_beams` beams per scan.
3. **Resampling.** Particles are redrawn proportional to weight — low-weight
   hypotheses die out, high-weight ones multiply — so the cloud concentrates
   around the pose(s) best supported by the scan. `min_particles`/
   `max_particles` bound the cloud size; `recovery_alpha_slow`/`_fast` inject
   a small fraction of random particles when average weight drops sharply,
   the filter's built-in recovery from "the cloud converged to the wrong
   place."

**Configured but not yet hardware-tested here.** `nav2_params.yaml`'s `amcl:`
block predates this session and is the intended Stage-3 (§17.25/§17.26)
localization source — `robot_model_type: omnidirectional` (correct for
mecanum, where lateral motion carries its own noise character distinct from
forward motion), and `initial_pose`'s `yaw: -1.5708` already accounts for
this robot's non-REP-103 `base_link` convention (a robot facing forward along
map `+X` has base_link yaw `-90°` here, not `0°` — get this wrong and the
first scan match starts from a hypothesis rotated 90° from reality). It was
exercised for the first time this session, in the sense that
`navigation.launch.py` was rewritten to actually launch it correctly
(§17.26) — but no map has been saved yet for it to load, so the block remains
unverified against real particle convergence, real drift-under-motion, and
real recovery behaviour. That is the concrete next hardware milestone this
document's theory feeds into.

---

## References

See `research_articles/README.md` for the full citation list with DOIs and
per-paper relevance notes. Landmark papers cited in §6 (Yamauchi 1997;
Coulter 1992; Thrun, Fox, Burgard & Dellaert 1999/2001) are not yet in that
list — add them there before building further on §6's reasoning.
