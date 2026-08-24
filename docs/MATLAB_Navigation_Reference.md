# MATLAB Navigation Toolbox — cross-referenced against AisleBot

**Written 22 Aug 2026.** The user extracted the full contents of MathWorks'
Mapping, Motion Planning, and Localization Algorithms documentation hubs (this
environment's network policy blocks `mathworks.com` directly, so the user did
the fetching). This document is not a re-paste of that material — it's every
piece of it cross-referenced against AisleBot's *actual* files, config values,
and hardware, ranked by whether it's buildable now, later, or not at all.

Where a claim below depends on a file or parameter, it was read directly
before being written down, not recalled from memory — the same discipline
this project's other theory docs (`SLAM_Theory.md`, `Navigation_Theory.md`)
already hold to.

---

## Tier 1 — concrete, cross-referenced, buildable soon

### 1. IMU-assisted scan matching → precisely scopes the unfinished Phase 2 work

MATLAB's docs state plainly: IMU data can constrain the rotation-angle search
window in grid-based scan matching, which directly narrows the ambiguity
space perceptual aliasing exploits — this is the same "look-alike aisles,
scan matcher picks the wrong plausible match" mechanism this project has been
chasing since §17.28.

**This isn't hypothetical for AisleBot — the software half already exists,
unused, and reading it precisely settles what "Phase 2" actually means:**

- `esp32_bridge.py` has a complete, working IMU code path: parses a BNO055
  quaternion + angular velocity + linear acceleration frame off the wire
  (`[IMU]qw,qx,qy,qz,gx,gy,gz,ax,ay,az`) and publishes `sensor_msgs/Imu` —
  gated behind `enable_imu` (**default `False`**).
- `src/mecanum_navigation/config/ekf_params.yaml` is a fully-written
  `robot_localization` EKF config fusing wheel odometry + IMU, tuned process
  noise included.
- **But `navigation.launch.py`'s own header comment is explicit and final:**
  *"robot_localization EKF: deliberately not started... it fuses an IMU
  (BNO055) that is still **unpurchased** Phase 2 work."* There is no physical
  IMU on the robot. This is scaffolding for hardware that doesn't exist yet,
  not a dormant capability waiting for a flag flip.

**So the real value of this MATLAB material is turning a vague "Phase 2 IMU
fusion" line-item (already sitting in `research_articles/README.md`'s
citation list, motivating nothing concrete) into a scoped task list:**

1. Buy a BNO055 and wire it to the ESP32 — firmware protocol is already
   defined and the parser already exists.
2. `enable_imu:=true` on `esp32_bridge`.
3. **A real bug, found by reading, not guessed:** `ekf_params.yaml` subscribes
   `imu0: imu/data`, but `esp32_bridge.py` publishes to `imu/data_raw`. Those
   are different topics. As written today, even with the IMU physically
   installed and enabled, the EKF would receive nothing — silently, no error,
   the exact "silent blocker" pattern `LiDAR_SLAM_Bringup.md` already warns
   about for this project. Fix the topic name (or remap) before trusting this
   config.
4. `slam.launch.py` is stale relative to the actual bringup — it loads
   `config/slam_params.yaml` (the confirmed-decoy config; the live one is
   `~/ros2_ws/slam_nodom.yaml`, §17.31/§17.32) and doesn't include the
   LiDAR/`scan_relay` pipeline. It needs rewriting against
   `mapping_full.launch.py`'s actual node set before EKF can be folded in for
   real, not just launched standalone.
5. Once EKF publishes a fused `odom`, `slam_toolbox`'s `odom_frame` prior
   becomes IMU-informed, which is the actual mechanism MATLAB's docs describe.

Not urgent — gated on a purchase — but now a precise, four-step list instead
of an open-ended aspiration.

### 2. Pose-graph residual analysis — the direct answer to the still-open jump question

MATLAB's `trimLoopClosures` (§17.32's docs, Graduated Non-Convexity + Truncated
Least Squares) doesn't watch for bad closures as they happen — it computes
`edgeResidualErrors` across the whole solved pose graph afterward and flags
statistical outliers.

This matters specifically *because* §17.29 already proved `slam_toolbox`
2.8.5 has **zero** observable per-closure signal — no console line, no topic —
for accept/reject events. MATLAB's approach sidesteps that limitation
entirely: don't watch the event, analyze the graph. `slam_toolbox` already
publishes `/slam_toolbox/graph_visualization` (confirmed live in this
session's Foxglove config) — nodes and edges are already on the wire. A
script that subscribes to it and computes per-edge residual the way MATLAB's
`edgeResidualErrors` does would settle, with actual numbers, whether a given
correction was legitimate drift-cancellation or a bad match — stronger
evidence than "did the map visibly fold," which is what §17.32's corrected
acceptance gate currently relies on.

### 3. Occupancy-grid rendering saturation — a second, independent lever

Separate from Stage B's pose-graph-level loop-closure tuning: MATLAB's
`ProbabilitySaturation` (default `[0.001 0.999]`, `[0.12 0.97]` suggested for
dynamic environments) caps how far a cell's log-odds can drift, so a cell that
was observed occupied 50 times doesn't need 50 contrary observations to flip
back — directly relevant to a warehouse where pallets move.

`slam_toolbox` renders its final `/map` from the solved pose graph via a
comparable hit/miss log-odds accumulation (distinct from the `map→odom`
pose-graph correction Stage A/B already addressed) — this is the *other* half
of the pipeline, occupancy-grid construction rather than pose estimation.
**Not verified against this build's exact parameter names** — check
`ros2 param list /slam_toolbox | grep -i pass` and
`ros2 param list /slam_toolbox | grep -i threshold` against the live node
before assuming anything is tunable here. Flagged as a lead, not a fact.

### 4. A path-clearance metric — small, cheap, and specific to this robot's actual mission

`pathmetrics`' clearance concept — minimum distance from the path to the
nearest known obstacle — isn't in `tools/trajectory_viz.py` today (it reports
length, net displacement, deviation from a reference line). For a robot whose
entire premise is fitting through *narrow* aisles, "how close did it actually
come to the shelf" is a more mission-relevant number than most of what's
already recorded. Cheap to add: sample the local costmap (or the saved map)
at each recorded pose, report the minimum. A genuinely small, high-relevance
addition once Stage C's map exists to check against.

---

## Tier 2 — real, not urgent

### 5. Boustrophedon coverage planning → the UV-C subsystem has no autonomy behind it

This project already has a working UV-C tube lighting subsystem end to end —
`arm_bridge.py`, `UV_ON`/`UV_OFF` wired into the dashboard's `_dispatch`. It
has zero path planning behind it: someone drives manually with UV on.
`polygonSweep`/boustrophedon decomposition (§2.4 of the extraction) is
precisely the missing algorithm class for "autonomously sweep this aisle for
disinfection." Real, hardware-backed, currently-unbuilt capability — worth a
line in `Production_Architecture.md`'s deferred-features list, not something
to build before the map/localization work in `Dashboard_Map_System.md` lands.

### 6. Dynamic/moving-obstacle prediction

Nav2's `collision_monitor` + `obstacle_layer` react to the *current* LiDAR
scan only — no prediction of where a moving person will be. MATLAB's
`trackerGridRFS`/`predictMapToTime` is a real, documented gap relative to
what this robot has, and it's a real safety-relevant one given the permanent
90° rear blind sector (§17.15) in a space shared with foot traffic. Big lift
(a moving-obstacle tracker + costmap layer is genuine new engineering, not a
parameter change) — a Phase 3+ item, after static navigation and the map
system are solid.

### 7. TEB as an alternate local planner

Nav2 has a real `teb_local_planner` package, matching MATLAB's
`controllerTEB`. Not a recommendation to switch — MPPI is already producing
clean 0.5m round trips and the open problems this session (leg-4 stalls, pose
jumps) have been traced to localization, not the local planner. Worth knowing
exists as a fallback if controller-side issues resurface *after* the
localization work is done — switching now would confound two variables.

---

## Tier 3 — validates decisions already made; good material for the theory docs

- **NavfnPlanner (grid-based, closer to `plannerAStarGrid`) is the correct
  global planner choice, not Hybrid A\*.** Hybrid A* exists specifically for
  vehicles with a minimum turning radius constraint (cars). Mecanum is
  omnidirectional — no such constraint exists to plan around. This isn't a
  gap, it's confirmation the right tool was already chosen.
- **`nav2_amcl`'s `alpha1-5` and `recovery_alpha_slow/fast`** (already sitting
  in `nav2_params.yaml`, never yet run on hardware) are the same parameters
  MATLAB's MCL/KLD-sampling theory describes — the AMCL block is shaped
  correctly going into Stage D, not something assembled by guesswork.
- **`slam_nodom.yaml`'s `correlation_search_space_dimension/resolution/
  smear_deviation` and `coarse_search_angle_offset`/`fine_search_angle_offset`**
  are exactly the coarse-to-fine grid-search scan-matching algorithm MATLAB's
  `matchScansGrid` describes. Explains what those already-tuned numbers are
  actually doing, which nothing in this project's docs previously spelled out.
- **Mecanum has no built-in MATLAB wheel-odometry object** (Ackermann,
  bicycle, differential-drive, unicycle are covered; asymmetric mecanum is
  not). `odometry_publisher.py`'s custom kinematics were necessary, not a
  shortcut that skipped an available library.

---

## Not applicable — checked and excluded, not just skipped

- **3-D occupancy maps / octrees** — single-plane 2D LiDAR only, no 3-D
  sensing on this robot.
- **MPNet (deep-learning planning)** — needs Deep Learning Toolbox + training
  infrastructure; this stack is ROS2/Nav2 at runtime, not MATLAB.
- **Frenet-coordinate lane trajectories** — built for structured road lanes
  with lead vehicles; a warehouse aisle has neither.
- **Factor graphs / VIO** — multi-sensor graph optimization for
  camera+IMU+GPS fusion is real overkill for a single 2D LiDAR + (eventually)
  one IMU indoor robot.

---

## What to actually do next

Nothing here should preempt `Dashboard_Map_System.md`'s A→B→C→D sequence —
none of Tier 1's items are prerequisites for getting one clean saved map.
Item 2 (pose-graph residual analysis) is the one worth picking up first once
that sequence is stable, since it directly targets the still-open "what
caused the jumps" question that §17.32 explicitly left unresolved.
