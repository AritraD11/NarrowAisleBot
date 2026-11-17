# Year 2 autonomy: research notes and a build order

*29 Sep 2026, six days after the first APS. Research and planning only:
nothing in this file has run on the robot. Read it alongside
`Navigation_Theory.md`, `SLAM_Theory.md` and `Hardware_Roadmap.md`. Where it
disagrees with one of them it says which one, and why.*

Evidence grades follow `Hardware_Roadmap.md`: **measured** (this robot's own
logs), **source-checked** (read in upstream code or a datasheet this session),
**principle** (sound reasoning, untested here), **judgement** (a trade-off with
a side picked). Every geometric number below comes from
`tools/sensor_coverage.py`, which has a `--selftest` and runs in under a
second, so none of them has to be taken on trust.

---

## Where I land, before the detail

Do goal 2 first, the saved map. It's closer than it looks. AMCL has never run
on this robot, but the thing blocking it was never AMCL. It was a map
acceptance gate whose failing criterion (unknown cells) measures the room more
than the map. AMCL only needs the walls to be in the right places. G5 can run
on the hardware you already have, within weeks.

Goal 1, precise navigation on a map that's still being built, is limited by
sensing, and no parameter fixes it. With scan matching off, the live map is
wheel odometry drawn in LiDAR ink. Goals a few metres away land within
centimetres. Goals ten metres of driving later inherit 11 to 15 cm of drift.
Making it "very precise" needs a heading reference (the IMU) and probably a
better scanner, in that order.

Goal 3 is a good idea, but I'd buy a different first sensor than
`Hardware_Roadmap.md` suggests. One small DTOF 2D LiDAR at a rear corner does
three jobs at once. It covers the blind wedge. It runs the scanner comparison
the APS report promised as future work. And if it turns out cleaner than the
X4 Pro, it becomes the answer to goal 1 too. The ToF ring still earns its
place, for obstacles below the scan plane, but it needs a different layout from
the eight-modules-pointing-outward sketch (§5.3 shows why: that layout sees
15 % of the robot's surroundings at 10 cm).

While reading slam_toolbox's source for this, I also found that the 0.183 m
"metronome" from Stage H is slam_toolbox's own scan-admission gate, to within a
few millimetres. That doesn't overturn the Stage H result, but it does change
two sentences that shouldn't go into a paper as written. §3 has it.

---

## 1. What "very precise" has to mean on this chassis

Precision without a number is a mood. These are the numbers that set it.

The robot is 1.00 m long and 0.36 m wide at the wheels. Nav2's padded
footprint is 1.12 × 0.48 m. Turning on the spot needs a clear circle of
1.063 m diameter bare, 1.219 m padded. So any aisle narrower than about
1.1 m is one the robot enters aligned and can't turn around in. That's the
regime the project exists for, and it's the regime the precision spec has to
be written for.

In that regime heading matters more than position. `sensor_coverage.py aisle`
gives the largest yaw error the rectangle tolerates, centred in the aisle,
before a corner touches a wall:

| Aisle width | Clearance per side | Max yaw, bare 1.00 × 0.36 m | Max yaw, padded 1.12 × 0.48 m |
|---|---|---|---|
| 0.60 m | 12 cm | 14.6° | 6.3° |
| 0.70 m | 17 cm | 21.4° | 11.9° |
| 0.80 m | 22 cm | 29.0° | 17.8° |
| 1.00 m | 32 cm | 50.4° | 32.0° |

Each degree of yaw swings the ends of a 1 m body by 8.7 mm. The phantom yaw
measured in §17.55 and §17.56 (3.85° and 4.49° over whole routes, roughly 0.4
to 0.6° per metre) is estimator error, not motion, but a navigation stack that
trusts it steers the real robot to match. At 4.49° that's about 39 mm at each
end of the body, and 0.39 m of sideways walk over 5 m of travel. Now look at
the 0.60 m row again. The padded heading budget is 6.3°, and at the measured
rate the estimator uses all of it in something like 10 to 15 m of driving,
with nothing on board able to notice.

In a narrow aisle, heading is the binding term. That's the sharpest form of
the IMU argument I can find, and it's sharper than the one in the report.

A working spec. Edit the numbers if you disagree, but write one down before
measuring anything:

| Quantity | Target | Why |
|---|---|---|
| Localisation, lateral, in an aisle | σ ≤ 3 cm | 3σ = 9 cm stays inside a 12 cm clearance |
| Localisation, heading | σ ≤ 1° | 3σ = 3°, half the padded budget at 0.60 m |
| Goal arrival, free space | ≤ 5 cm, ≤ 2° | tighter than G6's 15 cm / 10°, which was a demo gate |
| Station arrival ("very precise") | ≤ 1 cm, ≤ 0.5° | only reachable with a local reference at the station (§4.6) |

The last row is the honest one. Map-based localisation with a 2D LiDAR in the
price class this project can afford lands at a few centimetres on a good day.
Nobody gets 1 cm out of AMCL alone. Robots that stop within a centimetre
(docking, conveyor transfer) do it by measuring the station itself during the
last half metre. That's a separate subsystem, and Nav2 Jazzy already ships one.

---

## 2. What is on the robot today

Short, because `Where_We_Stand.md`, the two 15 Sep handoffs and the submitted
report carry the detail.

Scan matching is off (Stage G) because on this LiDAR it made pose worse: on
one drive the robot's own odometry closed at 16.2 mm and the matched estimate
at 206.7 mm. So `map→odom` is constant and the live map is wheel odometry plus
LiDAR returns. Wheel odometry closes at 1.1 to 1.5 % of path on long,
rotation-heavy routes and about 0.1 % on short straight ones, and it carries a
heading error class (3.85°, 4.49°) that no fitted instrument can see.

The X4 Pro gives about 430 points at 11.35 Hz, 47.4 % valid at any instant.
Stationary scatter is 12 to 14 mm below 1.5 m, 22 to 32 mm at 1.5 to 2.0 m,
and 55 to 200 mm past 2.5 m, where two captures disagree with each other. A
90° wedge behind it (107 beams) is masked for the mast.

Nav2 runs NavFn (A*, `allow_unknown: true`, `tolerance: 0.5`), MPPI with the
omni model, and `collision_monitor` with one polygon and one source, the scan.
AMCL is configured and has never executed. The named-location library (G7) is
written and unit-tested, never deployed. Planner, controller and safety chain
run below their requested rates on the Pi 5 (G3: 7.5 to 13.7 Hz against 20).
And there's an open report from 15 Sep that Nav2 "doesn't replan when
blocked", with no diagnostic data yet.

---

## 3. A correction to the Stage H story, from slam_toolbox's source

*Source-checked, slam_toolbox `jazzy` branch, 29 Sep 2026.*

This doesn't overturn Stage H. It changes how two claims should read, and it
matters because Year 2 will reopen scan matching with better inputs and needs
the diagnostic to be right.

The claims were that all 17 corrections "fired at a mean odometry cadence of
0.183 m with a 1 cm spread", that they "track pose-graph node creation, not
scan disagreement", and that this also explains why loop closure never fired,
because "a closure arrives off-cadence". The submitted report carries the
first half as "corrections firing on a fixed odometry cadence rather than on
scan disagreement".

Here's what the code does. `SlamToolbox::shouldProcessScan()` in
`src/slam_toolbox_common.cpp` admits a scan only once the odometric pose has
moved far enough. With the default `check_min_dist_and_heading_precisely:
false`, the test is `dist2 < 0.8 * min_dist2` → reject. The deployed
`minimum_travel_distance` is 0.2 m, so a scan is admitted every
√0.8 × 0.2 = **0.179 m** of travel. Add up to one scan period of motion (about
9 mm at 0.1 m/s and 11.35 Hz) and you get the measured 0.183 m ± 1 cm.

Next, `SlamToolbox::addScan()` only calls `setTransformFromPoses()`, the
function that moves `map→odom`, when that admitted scan was processed. And
inside Karto's `Mapper::Process()` (`lib/karto_sdk/src/Mapper.cpp`), the
sequential match, `AddVertex`, `AddEdges` and `TryCloseLoop` all run in the
same call, for the same new node.

So:

1. Every correction slam_toolbox can make, sequential match or loop closure,
   lands on the node cadence by construction. The metronome is the admission
   gate. It can't tell noise-driven corrections from real ones; the size of
   each per-node correction is where that evidence lives.
2. "No correction arrived off-cadence, so no loop closure fired" isn't a valid
   test. A loop closure would have arrived on-cadence as well.
3. `AddVertex` and `TryCloseLoop` sit inside `if (m_pUseScanMatching->GetValue())`.
   With matching off (Stage G), Karto builds no graph at all. Loop closure
   wasn't just unobserved there, it was impossible. That's a simpler
   explanation for §17.56's "the graph never published, twice" than anything
   the journal considered.

What stands untouched: the 32× degradation on a drive with its own odometry as
control, cumulative correction invariant to within 2 % across three parameter
sets, and the decision to keep matching off on this sensor.

A loop-closure test that doesn't depend on timing: `slam_toolbox/graph_visualization`
publishes one sphere per node (marker `id` = node id) and a `LINE_LIST` of
edges whose endpoints are copied from the same corrected poses
(`LoopClosureAssistant::publishGraph()`). Match each edge endpoint to its node
by position, then count edges whose node ids differ by more than
`scan_buffer_size` (10 in the deployed config). Those link a new scan to old
map. Zero of them after a closed loop is real evidence nothing closed. A
non-zero count followed by a step in `map→odom` is a closure.

I'd add a short journal entry correcting the §17.40 and Stage H readings, and
keep the "cadence rather than scan disagreement" sentence out of any paper.

---

## 4. Goal 2 first: a saved map, localisation on it, named locations, routing around blockages

### 4.1 Why this one goes first

It's the most reachable goal and the most product-like, and every piece of
software it needs already exists in Jazzy. It also produces a measurement goal
1 needs: once AMCL runs, you get an independent read on how wrong the wheel
odometry was, on every drive, for free.

### 4.2 The map doesn't have to pass G4 to be useful

G4 has four criteria. AMCL cares about two. It needs walls in the right place
(doubled walls under 1 %, not FOLDED), and it needs the map not to be bent over
the area the robot will work in, which return-to-mark roughly checks. It
doesn't care how many cells inside the bounding box are unknown. The outside
review said unknown-% measures the room's shape. It was right, and here that's
decisive.

So re-scope the gate for this use. Take the best existing map by doubled walls
and closure (the 15 Sep matching-off circle closed at 6.4 mm with 0.8 %
doubled walls), or record a fresh one with the 8 m rolling-corner procedure.
Then clean it: erase stray obstacle pixels in free space, close obvious gaps in
walls, keep the original next to it, hash both. Editing a map is ordinary
practice as long as the edit is recorded.

### 4.3 AMCL, and what this sensor means for its settings

`Navigation_Theory.md` §6.3 already covers the particle filter (Fox et al.,
1999). What's missing is what the X4 Pro's numbers imply for the sensor model.

Start with beam count. `max_beams: 60` is spread evenly over 430 points. Take
off the 107 masked beams, keep 47.4 % of the rest, and each update scores about
**21 usable beams**. That's thin. At 120 it's about 43; at 180, about 64. Nav2's
likelihood-field model skips NaN and max-range returns instead of scoring them
(*source-checked*: `likelihood_field_model.cpp` `continue`s on both), so
flicker costs information, not correctness, and each extra beam is one
distance-table lookup per particle. Raising `max_beams` is cheap and it's the
first change I'd make.

Starting values for one-at-a-time tuning, not a deploy. Confirm the current
values with `ros2 param get /amcl ...` on the live node before changing
anything, since several of these are unset in `nav2_params.yaml` and ride on
Nav2 defaults:

| Parameter | Now | Try | Reason |
|---|---|---|---|
| `max_beams` | 60 | 120 | about 21 → 43 valid beams per update |
| `laser_max_range` | unset (Nav2 default) | 4.0 | scatter past 2.5 m is 55 to 200 mm and not repeatable between captures |
| `sigma_hit` | unset (default 0.2) | keep, then 0.1 once tracking is stable | has to absorb scan scatter (1 to 3 cm) plus map error from an odometry-built map |
| `z_hit` / `z_rand` | unset (defaults) | keep | the defaults already tolerate a lot of random returns |
| `alpha1`..`alpha5` | 0.2 / 0.1 | keep, fit later | lateral scale moved from 0.80 to 0.92 between floors; strafe noise deserves to stay generous |
| `update_min_d` / `_a` | 0.15 m / 0.1 rad | keep | odometry adds about 2 mm per 15 cm between updates; arrival error doesn't come from here |

G5 as I'd write it now: the particle cloud converges from the zero-mark
initial pose within 2 m of driving, `/amcl_pose` gives σx, σy ≤ 0.10 m and
σyaw ≤ 3°, and `map→odom` never steps more than 5 cm between updates while
driving past walls. My prediction, registered now: it converges, and σ lands
at 5 to 10 cm and 2 to 4°. If σ comes in under 3 cm I was too pessimistic about the
sensor, and that's worth knowing.

One thing to watch the first time it runs. AMCL doesn't use slam_toolbox's
correlative matcher at all. If AMCL behaves on the same scans that broke the
front end, the fault sits with that matcher and its search on this data, not
with the sensor alone. If AMCL struggles too, the sensor is the common cause.
Either result is informative, which is a good reason to run it soon.

### 4.4 Recording the map "manually and autonomously"

Manual recording works today (dashboard MAP, the 8 m procedure). "Autonomous"
covers two very different things.

Frontier exploration (Yamauchi, 1997) drives toward the boundary between
known-free and unknown space until none is left. ROS 2 implementations exist:
`m-explore-ros2`, a port of `explore_lite`, and a newer
`frontier_exploration_ros2` that targets Jazzy. I'd hold it back for now, for
reasons specific to this robot. It trusts the live map, which is goal 1's weak
point. It knows nothing of the project's own finding that rotation in place
maps nothing while wall-parallel translation maps well. The rear wedge keeps
regenerating frontiers behind the robot. And in narrow aisles it'll choose
frontier goals the 1.12 m footprint can't turn toward.

Teach-and-repeat mapping is the one I'd build first. Drive the commissioning
route once by hand, logging poses from the zero mark. After that the robot
replays the route through `NavigateThroughPoses` while slam_toolbox maps. It
encodes the rolling-corner, wall-offset procedure exactly, and it makes maps
comparable run to run, which every A/B in this project has needed and
hand-driving has never delivered. Better experiment, better demo.

Save two forms every time: `.pgm`/`.yaml` for AMCL, and slam_toolbox's
serialized pose graph (`serialize_map`) so a map can be extended later rather
than re-driven.

### 4.5 Named locations

G7 already stores a pose and refuses to recall on the wrong map. To do what
goal 2 asks it needs three more things. Each location should carry a heading
and an approach type (free space, aisle-aligned, station), because in an aisle
the heading is the constraint and a free-space approach will happily try to
arrive nose-first from the wrong end. Tolerance should be per location rather
than one global `xy_goal_tolerance`. And the planner tolerance has to come down
first, or a location taught near a rack will "succeed" in the wrong place.

That last one deserves a paragraph (*source-checked*, navigation2 `jazzy`).
NavFn runs with `tolerance: 0.5`. If the requested goal lies in a cell costed
253 or higher, which a location taught close to a shelf easily can be, NavFn
searches a ±0.5 m box around it for the closest reachable point
(`navfn_planner.cpp`, `makePlan`), plans there, and the path it returns ends
there (`smoothApproachToGoal(best_pose, plan)`). The controller server then
sets `end_pose_ = path.poses.back()` and runs the goal checker against that,
not against the pose you asked for. So the robot can report "Goal succeeded"
up to 0.5 m per axis (0.71 m on the diagonal) from the location, with nothing
in the logs to say so. For precise locations, drop `tolerance` to 0.05 to 0.10
and let an unreachable goal fail loudly. A goal tapped against a wall is a
thirty-second hardware check of all this.

(If any of this touches `DASHBOARD_HTML`, `CLAUDE.md`'s rule applies: run
`tools/tests/dashboard_html_syntax.py` before committing, and open the browser
console after deploying.)

### 4.6 "Very precise" arrival: the Docking Server

Nav2's Docking Server (`opennav_docking`) shipped with Jazzy. It drives to a
staging pose with ordinary navigation, detects where the dock actually is, and
servoes onto it with its own controller. It has non-charging dock plugins,
which is exactly what a precise "station" is. The documented examples detect
the dock with a camera and an AprilTag. Any node publishing the detected dock
pose works, so a LiDAR-visible feature at the station (a V-notch, a patterned
board) would do too, but that detector would have to be written.

This is the only credible route to the 1 cm row in §1. Two catches: it assumes
the robot approaches along its own +X (or backwards via a parameter), which on
this robot is sideways (§7.1), and it needs a detector that doesn't exist yet.
Second half of Year 2.

### 4.7 Finding another path when blocked

Nav2's default Jazzy behaviour tree (`navigate_to_pose_w_replanning_and_recovery.xml`,
*source-checked*) replans at 1 Hz, and `nav2_params.yaml` doesn't override it.
So "not replanning" nearly always means the planner doesn't see what you see,
or the replan keeps finding the same path. For this robot I'd test four
hypotheses, in this order:

1. **The obstacle is invisible.** Anything shorter than the scan plane
   (about 0.275 m, a height nobody has measured) or inside the rear wedge never
   reaches either costmap or `collision_monitor`. Test with a tall box, then a
   low box, same spot. I expect the tall one to produce a new `/plan` within
   about 2 s and the low one to get driven into. If so, it's a sensing problem
   and goal 3 is the fix.
2. **Maybe the only route runs through it,** and the recovery then erases it.
   When the planner returns `NO_VALID_PATH`, the default tree's first recovery
   is `ClearEntireCostmap` on the global costmap. That deletes the obstacle from memory, so the next plan goes
   straight back through it. In a single aisle this looks exactly like "doesn't
   replan". Test: block a dead-end aisle and read the BT log for the clear
   followed by a plan through the box.
3. **NavFn plans something the footprint can't follow.** NavFn is a
   point-robot planner. It blocks only cells within the inscribed radius
   (0.25 m here), so it'll route a 1.12 m-long robot through any gap wider
   than about 0.5 m, including gaps that need a turn the body can't make.
   MPPI checks the real footprint and finds nothing feasible, the progress
   checker times out after 10 s, and the next replan returns the same
   impossible path. Test: a doorway-width gap that needs a 90° turn.
4. **Or Nav2 simply never learns the robot stopped.** `collision_monitor` sits
   after the controller and only scales `cmd_vel`, so the controller keeps
   commanding a path the costmap still calls valid. Test: log
   `collision_monitor_state` next to `/plan`.

The fixes follow the causes. Goal 3's sensors fix the first. For the second, a
custom tree that tries `Wait` and a fresh plan before any clearing, and clears
a window around the robot rather than the whole global costmap. For the third,
an SE(2) planner (next section). For the fourth, give the costmaps every
source `collision_monitor` has, so planner and safety layer see one world.

The same default tree has a problem that isn't about replanning at all. Its
general recovery round-robin includes `Spin` by 1.57 rad and `BackUp` by
0.30 m. A quarter turn needs 1.2 m of clear width for the padded footprint,
so in an aisle it can only fail. `BackUp` needs a correction, made on
30 Sep 2026 after reading Nav2's `DriveOnHeading` source (and made obsolete by the 5 Oct 2026 axis change: in the standard frame BackUp is a real reverse into the rear blind sector): it commands
`linear.x` (negative for a back-up) and checks for collisions along the base
frame's x axis. On this robot base_link +X is the robot's right, so `BackUp`
is a 30 cm strafe to the LEFT, and its collision check looks left, not
backwards. It does not reverse into the rear wedge. (An earlier version of this
paragraph said it did. That was wrong.) The default tree still has no
recovery that moves along the robot's real forward axis, and a left strafe is
not what anyone wants from "back up". The custom tree should use `Wait` and
a fresh plan first, and take Spin only where the width allows it.

Two more settings belong to saved-map mode specifically, which argues for
keeping two parameter sets, live-map and saved-map. On a cleaned saved map,
`allow_unknown` should be `false`: left `true`, the planner can route out
through any gap in a wall into unknown space. And Nav2's costmap filters
(keepout zones, speed-limit zones) are made for this. A slow zone inside every
aisle is an obvious first use.

### 4.8 The planner: NavFn is the wrong tool for this footprint

The robot's shape is the whole point of the project, and NavFn ignores it. The
chassis needs a planner that searches over position and heading, SE(2), and
checks the full footprint at every expansion. In Nav2 that's the Smac family
(Macenski et al., 2024). Smac 2D is still a point search, so it doesn't help.
Hybrid-A* assumes car-like motion. State Lattice is the one: it searches over
precomputed motion primitives, and the `jazzy` branch ships sample sets for
`ackermann`, `diff` and `omni` (*source-checked*:
`nav2_smac_planner/lattice_primitives/sample_primitives/5cm_resolution/0.5m_turning_radius/`).
The omni set includes lateral moves.

Two cautions before switching. There's an open Nav2 issue (#5231, reported on
Humble) that the lattice planner's analytic expansion is hard-coded for
car-like motion, so a plain strafe can come out as turn, drive, turn back. Test
whether it bites on Jazzy, and whether shrinking the analytic expansion avoids
it. And SE(2) search with a 1.12 m footprint costs far more CPU than NavFn, on a
Pi that's already missing rates, so measure planning time before trusting it.

For warehouse aisles there's a complementary tool, the Nav2 Route Server
(`nav2_route`). It plans over a hand-drawn graph of nodes and edges (aisle
entry, aisle exit, one-way rules, per-edge speed) and leaves free-space
planning to the short connecting pieces. It's a Kilted feature; the `jazzy`
branch of navigation2 also carries the package, but check
`apt-cache policy ros-jazzy-nav2-route` on the Pi before designing around it.

My recommendation: prototype Smac Lattice (omni) in Gazebo on a narrow-aisle
world first, keep NavFn as the fallback, and add the route server as the
warehouse layer once the saved-map loop works end to end.

---

## 5. Goal 3: the rear, and everything below the scan plane

### 5.1 The blind region is bigger than "behind"

The mask removes bearings −135° to −45° from a LiDAR that sits 0.27 m forward
of base_link. Because of that offset, the wedge's edges run diagonally back
along both flanks. From `sensor_coverage.py blind`:

| Stand-off from the flank | Unseen stretch of each 1.00 m flank |
|---|---|
| 5 cm | 0.54 m, from just ahead of centre to the rear corner |
| 10 cm | 0.49 m, the whole rear half |
| 20 cm | rear 0.39 m |
| 30 cm | rear 0.29 m |

At a typical aisle clearance of 10 cm, then, the rear half of both sides is
unseen, and so is everything behind. At 10 cm stand-off the X4 Pro sees 50 %
of the robot's surroundings, and 0 % of the rear face. Driving forward that's
survivable, because those cells were seen on the way in and the obstacle layer
remembers them. Reversing out of an aisle, or strafing, it isn't. None of it
helps with anything lower than the scan plane either: pallet feet, a carton on
the floor, a foot, fork tines.

One free option I checked and wouldn't lean on: moving the X4 Pro forward. A
90° wedge whose nearest returns sit at 0.12 to 0.13 m implies an obstruction
about 26 cm wide, 13 cm behind the LiDAR (inferred, not measured). Move the
LiDAR 0.20 m forward and the same obstruction subtends about 43°; flank
coverage at 10 cm rises from 50 % to 74 %. The rear face stays at 0 %, since
the mast's shadow always points straight back. Worth a tape measure, not a
solution.

### 5.2 The options

| Option | What it covers | Where it falls short | How it plugs in |
|---|---|---|---|
| Rear 2D DTOF LiDAR. RPLIDAR C1: 0.05 to 12 m on white, 6 m on black, ±30 mm, 5 kHz, 10 Hz. LDROBOT LD19 (also sold as STL-19P / D500 kit): 0.02 to 12 m, 4.5 kHz, 5 to 13 Hz | the whole rear, plus one flank if mounted at a corner | still a single plane, so blind to overhang; corner mounting is mechanical work | USB serial; merge with `dual_laser_merger` (has a `jazzy` branch), or give each scan to the costmaps as its own source |
| Multizone ToF ring. VL53L7CX: 60° × 60°, 8 × 8 zones, to 3.5 m, 60 Hz at 4 × 4. VL53L5CX: 45° × 45°, 15 Hz at 8 × 8, to 4 m | near field all round, below the scan plane, floor-level objects, drop-offs | about 86 KB of firmware uploaded to each module at every power-up (SparkFun measured 1.4 to 1.7 s per VL53L5CX at 1 MHz I²C); cover-glass crosstalk; many small parts | its own MCU → `PointCloud2` → costmap obstacle layer and `collision_monitor` |
| Single-zone ToF (VL53L1X, 27°) | point ranging, cheap | narrow cones, so many more units | `Range` → `RangeSensorLayer` |
| Ultrasonic, analog IR | cheap | ruled out in `Hardware_Roadmap.md` §1.3 (specular misses; colour and angle dependence) | |
| Depth camera | a volume ahead | narrow FoV, USB and CPU load on a Pi already short of cycles, cost | point cloud → voxel layer |

Indian stockists that list these: RPLIDAR C1 at Robu, Evelta and Hubtronics;
LD19 at Robu, Fab.to.Lab and Robotools; VL53L7CX as the Pololu 3418 carrier at
Fab.to.Lab, or ST's SATEL board at element14 India. I couldn't find rupee
prices I'd trust in search results, so price them at order time.

### 5.3 The ToF ring: aim along the body, not away from it

`Hardware_Roadmap.md` §1.3 sketched about eight VL53L5CX modules pointing
outward around the chassis. For a body this long and thin, the cone geometry
doesn't support it. A cone pointing straight out of a flank covers only
2·d·tan(θ/2) of that flank at stand-off d, which is 8 cm of a 1 m side at
10 cm with a 45° module.

`sensor_coverage.py ring` puts numbers on the alternatives: the fraction of the
robot's outline, at stand-off d, that at least one module sees (horizontal
cones, chassis opaque):

| Layout | Modules | 45° modules, d = 5 / 10 / 30 cm | 60° modules, d = 5 / 10 / 30 cm |
|---|---|---|---|
| Pointing outward: ends, corners, mid-sides (my reading of the roadmap's eight) | 8 | 7 / 15 / 40 % | 12 / 22 / 54 % |
| Pointing outward, five per long side | 16 | 14 / 32 / 74 % | 25 / 48 / 89 % |
| **Two per corner, grazing** | 8 | 100 / 100 / 92 % | 100 / 100 / 100 % |
| Grazing pairs + one rear-centre module, with the X4 Pro | 9 + LiDAR | 100 % from 5 to 80 cm | 100 % from 5 to 80 cm |

The fix is geometric, not a bigger order. Mount the modules in pairs at the
four corners and aim them along the body. A module at the front-right corner,
aimed back down the right flank and toed out by half its field of view, has
its inner edge running along the flank and its whole cone covering the strip
beside the robot. Its partner at the same corner does the same across the front
face. Eight VL53L7CX modules in four corner pairs cover the whole outline out to
30 cm in this model. With 45° modules the ends thin out past about 20 cm; the
X4 Pro covers the front at that range and a ninth module covers the rear.

What the model leaves out. It uses horizontal cones only. In reality the lower
zone rows of a module mounted at 10 cm hit the floor within about 17 cm (60°
vertical FoV). That's useful, since a known floor distance per zone row lets
you detect drop-offs, but it needs a per-row floor model. Grazing modules will
see the robot's own wheels near their inner edge; mask those zones in software,
the same idea as `scan_relay.py`'s wedge. And this is a screen for CAD, not a
substitute for it.

How close does the ring have to see? Stopping distance is v·t + v²/2a. Take
0.25 s from detection to motor command and the velocity smoother's 0.5 m/s²
deceleration: 4.4 cm at today's 0.12 m/s cap, 16.5 cm at 0.3 m/s, 37.5 cm at
0.5 m/s. At current speeds, guaranteed coverage at 10 cm is enough to stop. At
warehouse speeds it isn't, and that's where the grazing layout's coverage at
30 cm starts paying for itself.

### 5.4 Wiring and software for the ring

Keep it off the drive ESP32. The PID loop there is the one part of the stack
that's measured and working, and nine multizone modules mean nine firmware
uploads at boot plus a continuous stream of 8 × 8 frames. Give the ring its
own microcontroller (an ESP32-S3 or an RP2040 board, both have two I²C
controllers). Set addresses at boot through each module's LPn pin, or use a
TCA9548A mux, and send frames to the Pi over USB under a pinned udev name, the
same pattern as `/dev/esp32` and `/dev/ydlidar`.

On the Pi, one node turns each module's zones into 3D points (each zone has a
known direction inside the 8 × 8 grid) and publishes `PointCloud2` in the
module's frame, with the module poses in the URDF. That feeds two consumers:
the costmap obstacle layer as a `pointcloud` source with `min_obstacle_height`
just above floor noise, and `collision_monitor`, whose Jazzy docs list scan,
pointcloud and range sources. `RangeSensorLayer`, which the roadmap named, is
right for single-zone sensors and wrong for 64-zone modules.

A design problem to solve on paper rather than discover on the floor: zones
that report "no target" produce no points, so nothing clears the cells an
obstacle left behind when it moves. Either publish a clearing cloud at maximum
range for no-target zones, or use a layer that decays old observations.

Bench two things before buying nine. Crosstalk between two adjacent modules
aimed at overlapping space, since they emit at the same wavelength. And the
cover window: ST quotes cover-glass crosstalk immunity beyond 60 cm for the
VL53L7CX, and the ring lives almost entirely inside 60 cm, so run the modules
bare or do ST's crosstalk calibration with the real window fitted.

Later, the ring can drive a hardware protective stop. The ring MCU raises a
GPIO into the ESP32 when a zone in the direction of travel reads under a
threshold, and the ESP32 zeroes PWM without asking the Pi. That's the "second
witness that fails differently" the roadmap wanted, with teeth. It has to know
the direction of travel, though, because in a 12 cm aisle the side modules see
racking all the time.

### 5.5 My recommendation for goal 3

Buy one DTOF LiDAR before any ToF modules.

Mounted at a rear corner, around 0.15 m up, it takes the robot's surroundings
at 10 cm stand-off from 50 % seen to 86 %, and it sees the entire rear face.
More useful still: park it next to the X4 Pro and run the existing stationary
captures (`scan_quality.py`, `scan_range_envelope.py`) on both, same spot, same
minute. The report lists "repeat the routes with a higher-grade scanner" as
future work. This is the cheapest version of that experiment there is, and its
answer decides goal 1's sensor as well.

If the DTOF unit is clearly cleaner, buy a second and mount the pair at
diagonal corners, front-left and rear-right. In the coverage model that pair
sees 100 % of the outline with no mask at all, which is why industrial AMRs put
their safety scanners at opposite corners. The X4 Pro then retires to
comparison duty. If it isn't cleaner, the X4 Pro stays as the SLAM and AMCL
sensor and the rear unit feeds the costmaps only.

My registered prediction for that comparison: the DTOF unit's stationary
valid-return fraction comes in above 90 %, against the X4 Pro's 47.4 %. I'm
fairly confident about the direction and not at all confident about the size.

The ToF ring then follows as its own milestone, for below-plane obstacles: one
module on the bench, then a corner pair, then all four pairs.

---

## 6. Goal 1: precise navigation on a map that's still being built

### 6.1 What precision can mean on a live map

Two frames do two different jobs. The local costmap and MPPI work in `odom`, a
rolling 3 × 3 m window fed straight from the current scan, so avoiding
obstacles near the robot is as good as the scan and has nothing to do with the
map's global accuracy. The goal, though, is a point in `map`. Tap a goal beside
a shelf on the live map and its position relative to that shelf is correct in
the map. What the robot drives to is the goal's coordinates, through its
current pose estimate. The error on arrival is whatever drift that estimate
picked up between the moment the shelf was mapped and the moment the robot
gets there.

With matching off, that drift is wheel odometry: 1.1 to 1.5 % of the path
driven in between, less on straight runs. A goal 3 m away on a fresh map lands
within 3 to 5 cm. A goal reached after 10 m of driving lands 11 to 15 cm off.
That's why rung C (live-map tap-to-goal) has always worked, and why it can't be
called precise at warehouse scale.

A useful property falls out of this. The robot is currently in the rare regime
where better odometry improves the map one for one, because no matcher sits in
between. Merrick and Nandikolla (2026) fused wheel speed with IMU yaw rate in
an EKF and cut raw-odometry pose error by 61 to 75 % in translation and 65 to
77 % in rotation, but saw much smaller, algorithm-dependent gains once SLAM ran
on top. When SLAM is doing the correcting, the EKF's gain gets diluted. With
matching off, it wouldn't be.

### 6.2 The order

**First, the IMU and an EKF.** A BNO085 on the ESP32's reserved I²C pins
(G13/G14), published over the existing serial link at about 100 Hz, fused with
wheel odometry in `robot_localization`'s EKF (Moore & Stouch, 2015) in 2D mode.
Fuse wheel vx and vy (vy with its covariance inflated, given the 0.80 vs 0.92
lateral-scale surface dependence) and IMU yaw rate. Leave the magnetometer out,
using the game rotation vector, until a measured comparison says it helps next
to a 24 V motor bus. Exactly one node may publish `odom→base_link`: when the
EKF comes up, `odometry_publisher`'s TF goes off.

The Phase 2 test already exists. Re-drive a phantom-yaw route and check it with
photogrammetry. I'd predict an EKF heading error under 1° where
wheel odometry reported 3.85 to 4.49°. The gyro also separates the two
explanations the report left standing. A wheel-to-gyro yaw ratio that holds
steady across turns is a scale error, fixed by recalibrating the lever arms. One
that jumps now and then is rigid slip.

**Second, the scanner question** (§5.5). It's the same purchase as goal 3.

**Third, reopen scan matching once, with both.** Matching is supposed to work
as a tight search window over a good prior. Stage H tested a tight window over
a wheel-only prior with the X4 Pro. The Year 2 test is the same A/B (matching
off vs on, same route, one variable changed) with the EKF prior and whichever
scanner won §5.5, scored by the loop-closure edge count from §3 rather than by
cadence. If matching helps now, goal 1 becomes precise at range and loop
closure bounds the drift. If it still hurts with a DTOF scanner and an IMU
prior, that's a strong, publishable negative result about the correlative
front end at this scale.

**Throughout, the test space.** The report is right that a lab circuit of a few
metres limits everything map-related. A 15 to 20 m loop with some aisle-width
stretches is the first practical task of the year, and it isn't a technical
one.

---

## 7. Two decisions that cut across all three goals

### 7.1 The axis convention, now that Year 2 adds consumers

`Axis_Convention.md` says the convention isn't up for discussion, and I'm not
arguing it was wrong. It was a sound local decision with hardware validation
behind it. The cost side has moved, though. `nav2_params.yaml` itself calls the
non-REP-103 `base_link` "the stack's deepest open issue" and lists five
components already caught assuming +X is forward. Year 2 adds at least three
more with a built-in idea of forward: Smac Lattice's primitives (the
non-lateral ones move along +X, which on this robot is its right side), the
Docking Server's approach direction, and any controller or critic that prefers
forward motion. The IMU and EKF don't care, as long as TF is right.

So it's your call, with my recommendation attached. Do the refactor the config
comment already describes (REP-103 `base_link`, the −90° moved into
`laser_joint`) once, in simulation, before any of the new consumers land, with
`verify_axis_chain.py` rewritten as the guard. Doing it after Smac Lattice and
docking are tuned means tuning both twice. If you'd rather not, every new
component needs a source read for "forward" before it's trusted, and the
lattice primitives would need regenerating with the nose on +Y.

### 7.2 Compute

The Pi 5 already misses rates with NavFn, MPPI and SLAM. Year 2 adds AMCL, an
EKF, a scan merger, a point-cloud source and maybe a lattice planner. The EKF
and merger are cheap. AMCL is moderate. SE(2) planning isn't. Measure with
`ros2 topic hz` and `top` after each addition. If the controller falls further
below 20 Hz, the report's own conclusion applies ("a faster host raises all
three"), and an x86 mini PC as the robot computer is a smaller change than it
sounds. Whatever happens, `collision_monitor` and the stop path stay on the
robot and never cross Wi-Fi.

---

## 8. Build order and gates

Continuing the G-numbers. Predictions are registered here, before any of it
runs.

| # | Phase | Gate | Pass | Prediction |
|---|---|---|---|---|
| 0 | desk | axis decision (§7.1); narrow-aisle Gazebo world with 0.6, 0.8 and 1.1 m aisles | decision written; world loads | |
| 1 | parts | BNO085, one DTOF LiDAR, one or two VL53L7CX for the bench, plus the roadmap's INA226 and E-stop | parts in hand | |
| G5 | saved map | AMCL on a cleaned existing map | σxy ≤ 10 cm, σyaw ≤ 3°, no `map→odom` step > 5 cm | converges at 5 to 10 cm, 2 to 4° |
| G6 | saved map | five tapped goals | 5/5 within 15 cm; report each error against the 5 cm target | 5/5, mean 5 to 10 cm |
| G7 | saved map | three named locations recalled after a full power cycle | 3/3 within 15 cm | 3/3 |
| G8 | saved map | blocked-route tests from §4.7: tall box on a two-route loop, then a low box, then a dead-end aisle | tall: new route within 3 s; low: cause 1 confirmed or ruled out; dead end: waits, never clears and drives back in | tall passes; low box not seen; dead end fails today |
| G9 | state estimation | IMU + EKF on the phantom-yaw route, photogrammetry | heading error < 1° | 0.3 to 1.0° |
| G10 | sensing | DTOF vs X4 Pro stationary capture, same spot | a number, whichever way it goes | DTOF valid fraction > 90 % vs 47.4 % |
| G11 | sensing | 20 trials of a 10 cm box placed behind and beside the rear half while reversing | 20/20 stops | ToF ring 20/20; LiDAR-only misses the low box |
| G12 | goal 1 | matching off/on A/B with the EKF prior and the winning scanner, on the test-space loop | loop-closure edges counted; closure at mark no worse than matching off | genuinely uncertain; this is the experiment |
| G13 | station | Docking Server to a non-charging station | 10 approaches within 1 cm and 0.5° | needs a detector; late Year 2 |

G5 to G8 need no new hardware, and they're the next month. G9 and G10 start
the week the parts arrive. The ring and docking are the second half of the
year.

---

## 9. Sources

Papers, retrieved through Scite:

- Fox, D., Burgard, W., Dellaert, F., & Thrun, S. (1999). Monte Carlo localization for mobile robots. *Proceedings of the IEEE International Conference on Robotics and Automation*, 2, 1322–1328. https://doi.org/10.1109/ROBOT.1999.772544
- Macenski, S., Martín, F., White, R., & Ginés Clavero, J. (2020). The Marathon 2: A navigation system. *arXiv*. https://doi.org/10.48550/arXiv.2003.00368
- Macenski, S., Booker, M., & Wallace, J. (2024). Open-source, cost-aware kinematically feasible planning for mobile and surface robotics. *arXiv*. https://doi.org/10.48550/arXiv.2401.13078
- Merrick, C., & Nandikolla, V. K. (2026). Evaluating the impact of extended Kalman filter odometry on the performance of 2D LiDAR SLAM algorithms. *Sensors, 26*(17), 5468. https://doi.org/10.3390/s26175468
- Moore, T., & Stouch, D. W. (2015). A generalized extended Kalman filter implementation for the Robot Operating System. In *Intelligent Autonomous Systems 13* (pp. 335–348). Springer. https://doi.org/10.1007/978-3-319-08338-4_25
- Yamauchi, B. (1997). A frontier-based approach for autonomous exploration. *Proceedings of the IEEE International Symposium on Computational Intelligence in Robotics and Automation*, 146–151. https://doi.org/10.1109/CIRA.1997.613851

Source code read this session (all on GitHub, `jazzy` branches unless noted):

- slam_toolbox: `src/slam_toolbox_common.cpp` (`shouldProcessScan`, `addScan`), `lib/karto_sdk/src/Mapper.cpp` (`Process`, `HasMovedEnough`), `src/loop_closure_assistant.cpp` (`publishGraph`).
- navigation2: `nav2_route/`, `nav2_docking/`, `nav2_smac_planner/lattice_primitives/sample_primitives/`; issue #5231 (Smac Lattice omni analytic expansion, open).

Documentation and datasheets:

- ST VL53L7CX datasheet (st.com); SparkFun VL53L5CX hookup guide (firmware upload size and time; 15 Hz at 8 × 8, 60 Hz at 4 × 4).
- SLAMTEC RPLIDAR C1 product page and datasheet listings (DFRobot, Evelta); Waveshare LD19 wiki.
- Nav2 Jazzy release announcement (Docking Server); Nav2 collision monitor docs for Jazzy (source types).
- `dual_laser_merger` (Humble, Jazzy, Rolling); `m-explore-ros2`; `frontier_exploration_ros2` (Jazzy and Humble).
