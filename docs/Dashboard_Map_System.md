# The AisleBot Map System — engineering plan

**Written 21 Aug 2026 (§17.31), for the session that follows it.** This is the
build plan for the thing `Production_Architecture.md` describes as the product:
the robot's own map, in the robot's own dashboard, with manual driving and
autonomous goals in one interface, no Foxglove and no laptop.

`Production_Architecture.md` says *what* is being built and *why*. This file
says *how*, in the order it has to happen, with the specific parameters,
commands and code shapes involved. Read that file first if you haven't; this
one assumes it.

---

> ## ⚠ Status as of 22 Aug 2026 (§17.32) — read before using §1–§3
>
> This plan was executed the day after it was written. Three corrections,
> in descending order of how badly they would mislead you:
>
> 1. **§2's stated *reason* for the parameter changes is falsified.**
>    `system/slam_nodom.yaml`'s §17.25 tuning **never reached the robot** —
>    `install.sh:228` is the only thing that copies it to
>    `~/ros2_ws/slam_nodom.yaml`, and the Pi's copy dated from 26 June. So
>    every drive from 19–21 Aug ran on `slam_toolbox` **stock defaults**, and
>    §2's premise — "§17.25 over-relaxed the closure gate" — was reasoning
>    about parameters that were never active. **The three changes below were
>    still made and still measurably helped; the argument given for making
>    them is not why.** Don't repeat the causal claim. See §17.32.
>
> 2. **§3's trajectory acceptance criterion is wrong and must not be used.**
>    "No single-sample step > 10 cm" was written to catch bad loop closures,
>    but it cannot distinguish a bad closure from a good one — a legitimate
>    correction of accumulated drift trips it just as hard. Judge on **map
>    integrity** and **return-to-mark accuracy** instead. Step size is
>    diagnostic, not pass/fail. Corrected inline in §3 below.
>
> 3. **§1 (Stage A) is done. Don't re-run it.** `bag_tf_diff.py`'s first-ever
>    run: `map→odom` made 3 distinct changes (flat, then 39.57 cm / −13.80°,
>    then 39.00 cm / +13.80° twelve seconds later) while `odom→base_link`
>    stayed smooth at ~2.3 mm/tick **through both jump instants**. That is
>    row 1 of the pre-committed decision tree: **SLAM pose-graph correction,
>    not odometry.** Settled.
>
> **The lesson worth carrying forward:** a value in the repo is not a value on
> the robot. Verify deployed config with `ros2 param get` against the *live
> node*, never by reading a file. That is what caught this, and it is the
> single most useful thing in this banner.
>
> Current session state and today's plan live in `Next_Session_Kickoff.md`,
> which was rewritten 22 Aug and takes precedence over §6's sequencing here.

---

## 0. The reframe this plan is built on

Read §17.31 before anything else here. The short version:

Live `slam_toolbox` is producing pose corrections of 10–31 cm roughly every
18 s of driving. The instinct is to treat that as a blocker on autonomous
navigation. **It isn't, because the product does not navigate on live SLAM.**

| Phase | What runs | Owns `map→odom` | Frequency |
|---|---|---|---|
| **Commission** | `slam_toolbox` (mapping) | pose-graph optimisation | once per site |
| **Teach** | `map_server` + AMCL | particle filter | once per location |
| **Operate** | `map_server` + AMCL | particle filter | every working day |

`slam_toolbox` re-optimises a pose graph, which retroactively moves the whole
trajectory — that is the mechanism behind the jumps. AMCL localises against a
**fixed** map and never does that. So:

> **Live SLAM does not have to be perfect. It has to be good enough to build
> one clean map, one time.**

That is a far narrower target than "make live-SLAM navigation reliable", and
it is the target this plan pursues. Everything downstream — stable
coordinates, named locations, click-to-goal, the whole dashboard — rests on
one good saved map existing, not on live SLAM behaving.

**Corollary worth stating plainly:** stop testing autonomous accuracy under
live SLAM. Multi-leg goal chains (§17.31's compound test) are measuring the
pose estimate's stability, not the drive stack's accuracy. The 0.5 m
single-goal tests that came out clean (§17.30) were short enough to finish
between corrections; that is the whole difference.

---

## 1. Stage A — settle the jump question (one measurement, ~20 min)

**This is the §17.29 diagnostic that was designed and never run.** Do not tune
anything before it. Three sessions have now suspected loop closure without
measuring it, and §17.28 already recorded the lesson: *"Changing loop-closure
parameters again without evidence would repeat the exact mistake being
diagnosed."*

### The question

`map→base_link` is the composition of `map→odom` (SLAM's correction) and
`odom→base_link` (wheel odometry). The CSV records only the composition, so it
cannot say which half jumps. Splitting them settles it.

### Method 1 — live, quick (do this first)

Two terminals, side by side, while the robot does a short deliberate drive:

```bash
ros2 run tf2_ros tf2_echo map odom          # SLAM's correction only
ros2 run tf2_ros tf2_echo odom base_link    # wheel odometry only
```

Note `map odom`, **not** `map base_link` — the point is to isolate the
correction, not re-record the composition.

### Method 2 — rigorous, replayable

`tools/bag_tf_diff.py` exists for exactly this (added §17.29, `d2e0f10`) and
collapses the 50 Hz republish so only genuine changes print:

```bash
ros2 bag record -o ~/slam_tests/jump_$(date +%H%M%S) /tf /tf_static /scan_reliable /map
# ... drive ...
python3 ~/ros2_ws/tools/bag_tf_diff.py ~/slam_tests/jump_<stamp> --parent map --child odom
python3 ~/ros2_ws/tools/bag_tf_diff.py ~/slam_tests/jump_<stamp> --parent odom --child base_link
```

Note: this build of `slam_toolbox` (`2.8.5`) has **no** console or topic signal
for loop-closure accept/reject — confirmed against source *and* the live node's
topic list in §17.29. Do not spend time grepping for it. TF differencing is the
only available observation.

### Pre-committed decision tree

Decide before looking, so the result isn't rationalised:

| Observation | Conclusion | Action |
|---|---|---|
| `map→odom` steps 10–30 cm; `odom→base_link` smooth | **SLAM pose-graph correction.** Confirms §17.28. | Stage B tuning |
| Both step together at the same instant | Upstream — odometry, encoders, or `odometry_publisher` | Stop. Different investigation; Stage B is wrong |
| Neither steps, jumps don't reproduce | Map too empty to alias (as in §17.29's first redrive) | Drive over the same ground twice, then re-check |

Expected, on the §17.31 evidence: the first row. The four structural
properties in §17.31 (yaw coupled to every jump, bimodal directions, growing
magnitude, 0.1 s doublets) are pose-graph signatures, not odometry ones.

---

## 2. Stage B — tune for one clean map

**Done and deployed 22 Aug — this section is kept for its reasoning, not as an
instruction.** All three changes below are live on the Pi and verified with
`ros2 param get` against the running node.

**Read the banner at the top of this file first.** The framing below — that
these values were being walked back from §17.25's over-relaxation — is
**false**: §17.25's file never reached the robot, so the robot was on stock
defaults the whole time. The *changes* were right and measurably helped; the
*story* about what they were correcting was not. Where an argument below rests
on "§17.25 set X", treat the geometric reasoning as sound and the historical
premise as void.

Change three and nothing else, so the result stays attributable.

All three live in `system/slam_nodom.yaml` on the Pi at `~/ros2_ws/slam_nodom.yaml`.

### B.1 `loop_search_maximum_distance: 5.0 → 2.0` — the main one

This is the highest-leverage change and the argument for it is geometric.

§17.25 set 5.0 m reasoning that "a search radius has to comfortably exceed the
drift it is meant to correct", with 0.5 m of drift measured. Correct as far as
it goes — but it ignores the other side of the trade. **The explored workspace
is only a few metres across** (§17.31's recording spans ~1.0 × 1.15 m; §16.9's
first map was ~7 × 9.9 m). A 5 m search radius in a workspace that size makes
*essentially every node in the map* a loop-closure candidate for every new
scan — which is precisely the condition under which look-alike aisles produce
false matches.

The radius wants to be comfortably larger than expected drift and comfortably
smaller than the spacing between places that look alike. 2.0 m is 4× the
measured 0.5 m drift while excluding the far side of the junction.

### B.2 `loop_match_minimum_chain_size: 5 → 8`

This buys **discrimination**, which is different from strictness. The response
thresholds ask "does this one scan look like that one place?" — a question a
self-similar corridor answers wrongly all the time. Chain size asks "do N
*consecutive* nodes match N consecutive nodes over there?" A single false
match is easy; a false match sustained over a chain of 8 is much harder,
because the geometry has to alias continuously rather than momentarily.

§17.25 lowered this 10→5 because at `minimum_travel_distance: 0.2` a chain of
10 needs ~2 m of driving to become eligible. At 8 it needs ~1.6 m — still
reachable in this workspace, with materially better rejection.

### B.3 `max_laser_range: 12.0 → 10.0` — a correctness fix, independent of the above

Already an open item in Appendix B (§17.6): the value is inherited from the
originally-planned RPLiDAR A1 and exceeds the YDLIDAR X4 Pro's actual 10 m
maximum. Telling the matcher to use returns beyond the sensor's rated range
means feeding it points that are noise. Small, but it is free correctness and
it acts on the same subsystem.

### Deliberately NOT changed yet

`loop_match_minimum_response_coarse` / `_fine` stay at `0.25` / `0.35`. The
file's own warning names these as the first thing to raise — but they are also
the parameters that fixed §17.25's total closure failure, and raising them
risks going straight back to 50 cm of uncorrected drift. Try the two
aliasing-specific changes first; **if the map still folds, raise these to
`0.30` / `0.40` next, one step, and re-test.** Not both at once.

Also unchanged: `distance_variance_penalty` / `angle_variance_penalty`. These
control how much the odometry prior may veto a scan match, and §17.21's 25 %
strafe over-report is a real reason to distrust that prior. Revisit only after
the two above are exhausted.

### Deploy and verify

`slam_nodom.yaml` lives in the workspace root on the Pi, **not** in a package —
`colcon build` does not touch it and a `~` in the launch path silently fails
(`LiDAR_SLAM_Bringup.md`). Edit in place, then confirm the running node
actually took it:

```bash
ros2 param get /slam_toolbox loop_search_maximum_distance
ros2 param get /slam_toolbox loop_match_minimum_chain_size
ros2 param get /slam_toolbox max_laser_range
```

---

## 3. Stage C — the commissioning drive

This is `Production_Architecture.md` build-order steps 1–2, and it is the
single highest-value deliverable of the session. **Drive discipline is part of
the mitigation, not just procedure** — a wandering, revisit-heavy path gives
aliasing many chances to fire; a deliberate single-circuit path gives it few.

### Protocol

1. **Re-zero properly** (`Important_Commands.md` §8): park on the mark →
   `sudo systemctl restart aislebot.service` → confirm `tf2_echo odom base_link`
   reads `[0,0,0] @ 0.000°` (was `-90.000°` before §17.38) → start mapping → confirm `tf2_echo map base_link`
   reads the same. Both, every time. This is what makes map `(0,0)` mean the
   physical mark.
2. **Start the recorder** before moving:
   `python3 ~/ros2_ws/tools/trajectory_viz.py --no-reference --map-frame map`
3. **Capture the SLAM console**, which the dashboard MAP button discards
   (`stdout=DEVNULL` in `start_mapping()`) — so launch mapping from a terminal
   for this run, teed to a file, per `trajectory_viz.py`'s own header.
4. **Drive one wall-hugging circuit, manually, in one direction.** Slow. No
   back-and-forth, no re-crossing the middle. Close the loop once by returning
   to the mark at the end.
5. **Do not send Nav2 goals during this drive.** Commissioning is a manual job.

### Acceptance gate — all three, or the map is not saved

| Check | Pass condition | How it is checked |
|---|---|---|
| Return-to-mark | `tf2_echo map base_link` ≈ `(0, 0) @ 0°` (was `-90°` pre-§17.38) | the dashboard HUD, or `tf2_echo` |
| Map integrity | no folds, tears, or doubled walls | **`tools/map_integrity.py` reports `CLEAN`** |
| Walls present | actual occupied cells, not just swept free space | the same tool's occupied count, or `map_corpus.py` |

**Corrected 22 Aug (§17.32).** This table originally carried a third gate —
*"no single-sample step > 10 cm"* — and it has been removed rather than
softened. It was written to catch false loop closures, but it **cannot tell a
false closure from a correct one**: a legitimate correction of accumulated
drift produces exactly the same signature. On 22 Aug a drive that tripped it
five times also came out visibly clean and landed 5 cm from truth — a wrong
closure gives you neither. **Step size is diagnostic, not pass/fail.**

"Walls present" replaced it because it caught a real failure the step gate
never would have: 22 Aug's open-floor test drives produced maps of swept free
space with almost no wall geometry in them, which is useless for AMCL to
localise against no matter how smooth the trajectory looked.

**Map integrity stopped being a judgement on 26 Aug (§17.35).** It was "does
it look folded", which is a person staring at a grid — the weakest link in
calling mapping reliable. `tools/map_integrity.py` measures the fold
signature instead:

```bash
./tools/map_integrity.py ~/aislebot_logs/run_<stamp>.pgm --png check.png
```

Its headline detector flags two near-parallel walls with **free** space
between them across a gap narrower than the robot's own 0.48 m: free cells
mean the LiDAR returned through that space, so something saw both faces
across a gap nothing could occupy. Flagged cells come with **map
coordinates**, so a flag is a place to go and look, and `--png` writes the
grid with them in red — check the number against the picture, and against
`docs/tools/map_viewer.html`, rather than letting either replace the other.
(`map_viewer.html`, not `telemetry_analyzer.html`: the latter's map dropzone
only unlocks after loading a valid 13-column run, so it cannot open a bare
map.)

Its thresholds are provisional and the output says so. `--corpus` over the
archive prints the percentiles that should replace them.

A `FOLDED` verdict means Stage B needs its second step — raise the response
thresholds to `0.30` / `0.40`. That lever is still gated on the map actually
folding, and now the gate has a number behind it.

**Run `tools/graph_residuals.py --watch` during the drive** to catch the same
thing from the other side. It differences successive publications of
`/slam_toolbox/graph_visualization` and names the closure that moved the
graph, with the map coordinates where it happened. A false closure strains
the graph when it fires and puts a doubled wall where it strained it — the
two tools agreeing on a location is much stronger than either alone.

### Save it

```bash
ros2 run nav2_map_server map_saver_cli -f ~/aislebot_logs/warehouse_v1
```

Produces `warehouse_v1.pgm` + `warehouse_v1.yaml`. **Must run while
`slam_toolbox` is still alive** — `/map` dies with it. This would be the first
deliberately-commissioned map this project has produced.

---

## 4. Stage D — AMCL, the first time

Nothing here has ever run on hardware. `navigation.launch.py` was rewritten in
§17.26 and has zero hardware confirmation.

### D.1 `robot_model_type` — confirmed and fixed 26 Aug, still verify on the Pi

**The suspicion was right.** `nav2_params.yaml` now reads
`robot_model_type: "nav2_amcl::OmniMotionModel"`. It said `"omnidirectional"`,
which is not a class anyone exports, and the check was run against upstream
`nav2_amcl` source on both `jazzy` and `humble` rather than reasoned from
version history:

- `plugins.xml` declares exactly two classes,
  `nav2_amcl::DifferentialMotionModel` and `nav2_amcl::OmniMotionModel`.
  There is no alias for the bare strings anywhere in the package.
- `amcl_node.cpp`'s own default is the **fully-qualified**
  `"nav2_amcl::DifferentialMotionModel"`, not `"differential"` — the upstream
  default tells you the expected form.
- `amcl_node.cpp` calls
  `plugin_loader_.createSharedInstance(robot_model_type_)` with **no string
  translation, no legacy-name shim and no try/catch**, on the `on_configure`
  path.

So the old value threw out of `on_configure`, AMCL never reached ACTIVE, and
`lifecycle_manager` would have aborted the **entire** navigation bringup, not
just localisation — the same all-or-nothing failure mode §17.17 hit with
`docking_server`. It had never announced itself because this block has never
run on hardware.

Still check the installed package before the first bringup, because a repo
value is not a robot value (§17.32) and the installed `nav2_amcl` is the only
authority on what it exports:

```bash
ros2 pkg xml nav2_amcl | grep -i version
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
```

Then, once AMCL is up, confirm the value actually bound — reading the file
proves nothing:

```bash
ros2 param get /amcl robot_model_type
```

### D.2 Never run AMCL and slam_toolbox together

Both publish `map→odom`. `nav2_params.yaml`'s own header warns about it. Stop
`mapping_full.launch.py` completely before launching `navigation.launch.py`,
and confirm with `ros2 node list | grep slam_toolbox` returning nothing.

### D.3 The initial pose

`set_initial_pose: true` with `initial_pose: {x: 0, y: 0, yaw: -1.5708}` is
correct **only if** the robot is physically on the zero mark when AMCL starts,
and the map was commissioned from that mark by the §8 procedure. Since Stage C
does exactly that, this should work — but the comment block at
`nav2_params.yaml:59` is explicit that both numbers were wrong until §17.18 and
have never been hardware-confirmed. Park on the mark before launching.

### D.4 Acceptance

Restart the whole stack, park on the mark, launch on the saved map, and confirm
`tf2_echo map base_link` reads ≈ `(0,0) @ 0°` **without any SLAM running**
(`-90°` was the pre-§17.38 expectation — see `docs/Axis_Convention.md`).
That is the first time this robot will have known where it is on a remembered
map — and it is the moment stable coordinates, and therefore named locations,
become possible.

---

## 5. Stage E — the dashboard map

Pure software. Can be written any time, including off-robot. This is the part
that replaces Foxglove.

### E.0 Two traps, both found by reading the code (§17.31)

1. **`src/mecanum_robot/resource/dashboard.html` is a decoy.** It is installed
   by `setup.py` and read by nothing. The page actually served is the
   `DASHBOARD_HTML` string constant at `phone_dashboard.py:112`. Edit that.
   (Worth doing eventually: delete the decoy, or make `index()` actually read
   it. Don't do both halves of that in the same session as the map work.)
2. **The WebSocket is client→server only.** `ws_clients` is tracked but never
   broadcast to; the `/calib_status` handler documents the past decision not to
   build a push path. **That plumbing is E.1 and everything else depends on it.**

### E.1 Server → client broadcast

The ROS node spins on its own thread; uvicorn owns the asyncio loop. Pushing
directly from a ROS callback means cross-thread asyncio, which is a known
source of subtle breakage.

**Use the pattern this codebase already prefers:** ROS callbacks write the
latest state into plain node attributes; a single async task in FastAPI reads
those attributes on a timer and pushes. One writer, one reader, no locks
needed for whole-object replacement, no cross-thread scheduling.

```python
@app.on_event('startup')
async def _start_broadcast():
    asyncio.create_task(_broadcast_loop())

async def _broadcast_loop():
    tick = 0
    while True:
        await asyncio.sleep(0.1)                 # 10 Hz
        if not _node or not _node.ws_clients:
            continue
        payloads = [{'type': 'pose', **_node.latest_pose}] if _node.latest_pose else []
        tick += 1
        if tick % 10 == 0 and _node.map_dirty:   # 1 Hz, only when changed
            payloads.append({'type': 'map', **_node.latest_map})
            _node.map_dirty = False
        for p in payloads:
            dead = []
            for ws in list(_node.ws_clients):
                try:
                    await ws.send_json(p)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _node.ws_clients.discard(ws)
```

Rates matter: pose is small and wants to be smooth (10 Hz); the map is large
and changes slowly (`map_update_interval: 1.0`), so gate it on an actual
change rather than sending it every tick.

### E.2 Map streaming

Subscribe `/map` (`nav_msgs/OccupancyGrid`) with **transient-local, reliable**
QoS — it is a latched topic and a default subscription will silently receive
nothing.

Send the grid raw and render client-side. Three traps:

- **`data` is `int8`.** Unknown is `-1`, which becomes `255` if read as
  unsigned in JS. Map explicitly: `-1/255 → unknown`, `0 → free`,
  `100 → occupied`.
- **Row order is inverted relative to canvas.** OccupancyGrid row 0 is the
  *lowest* y; `ImageData` row 0 is the *top*. So
  `imageRow = height - 1 - gridRow`.
- **`info.origin` is the pose of cell (0,0) in the map frame**, and it is
  generally *not* `(0,0)` — slam_toolbox grows the grid in all directions.
  Every world↔pixel conversion must go through it.

```
col      = (wx - origin.x) / resolution
gridRow  = (wy - origin.y) / resolution
imageRow = height - 1 - gridRow
```

Payload:

```json
{"type":"map","w":133,"h":201,"res":0.05,
 "ox":-3.2,"oy":-5.1,"oyaw":0.0,
 "data":"<base64 of h*w int8 bytes>"}
```

**Sizing.** 133×201 = 26.7 KB raw → ~35.6 KB base64, at ≤1 Hz. Fine. A real
warehouse map (20 × 30 m at 0.05 = 400×600) is 240 KB → 320 KB base64 — still
workable on the robot's own AP but wasteful. **Scale path when it matters:**
`zlib.compress` (stdlib) on the grid bytes before base64, decompressed in the
browser with `DecompressionStream('deflate')`. Occupancy grids are mostly
uniform unknown regions and compress enormously. Don't build this for v1 —
build it when a map is actually big enough to need it.

### E.3 Live pose

A `tf2_ros` `Buffer`/`TransformListener` in `PhoneDashboard`, sampled by a ROS
timer at 10 Hz, looking up `map → base_link`, written to `latest_pose`.

Wrap the lookup in `try/except TransformException` and simply skip on failure —
the transform legitimately does not exist before SLAM/AMCL is up, and the
dashboard must not crash or spam when the map stack is down.

### E.4 Canvas rendering

Draw the robot as **its actual footprint rectangle, not a dot.** In a narrow
aisle the operator's real question is "does it fit", and a dot cannot answer
it. The polygon is already in `nav2_params.yaml:521`:

```
[[0.24, 0.56], [0.24, -0.56], [-0.24, -0.56], [-0.24, 0.56]]
```

Read as base_link axes — **`+X` is the robot's RIGHT, `+Y` its NOSE** (§17.10).
So ±0.24 m is half-width and ±0.56 m is half-length: the long axis runs along
`+Y`. Getting this backwards draws the robot sideways in its own aisle, and it
is the sixth place this axis convention has bitten the project
(`nav2_params.yaml` header lists the previous five).

Layers, back to front: map → LiDAR returns (`/scan_reliable`) → planned path
(`/plan`) → location pins → robot footprint → heading indicator.

### E.5 Click-to-goal

Publish to **`/goal_pose_click`, not `/goal_pose`.** `goal_pose_adapter`
already owns the −90° nose-vs-base_link conversion; going straight to
`/goal_pose` would duplicate that logic in a second place, which is exactly how
§17.19's axis bug happened.

Gesture: tap to place, drag to set heading, release to send — the same
semantics Foxglove's 2D Pose tool has, and now that the operator knows that
gesture it should not be re-invented.

**Two-tap arm, like CALIBRATE.** The precedent is already set in
`phone_dashboard.py` and the reasoning holds identically: one stray tap must
not start a 45 kg robot.

### E.6 Location library

```json
{"map": "warehouse_v1",
 "locations": [{"name": "Rack A3", "x": 2.31, "y": -1.74, "yaw": 0.40}]}
```

Store at `~/aislebot_logs/locations_<mapname>.json`. Endpoints: `GET` list,
`POST` add-from-current-pose (reads `latest_pose`, no hand measurement),
`DELETE` remove. Bind the file to the map name so re-commissioning visibly
invalidates the taught locations rather than silently pointing them at the
wrong floor tiles.

---

## 6. Sequencing, and what "done" looks like

```
A. Split the jump          20 min   ──┐
B. Tune (3 params)         20 min     │  hardware, needs the robot
C. Commissioning drive     60 min     │  and the operator present
D. AMCL first run          45 min   ──┘
                                     ─────────────────────────
E. Dashboard map           hours      pure software, any time
```

**A → B → C → D is the session.** If it ends after C with one good saved map,
that is a genuinely successful day: it is the first stable coordinate frame
this project has ever had, and every product feature depends on it.

**E is deliberately not gated on A–D.** Rendering `/map` and a live pose needs
the map topic to exist, not the goals to be accurate — `Production_Architecture.md`
§7 already flagged this as the safe piece to parallelise. It is also the better
instrument: watching the map build live in the browser during Stage C would
show a fold the moment it happens, which no amount of Foxglove screenshotting
after the fact can do.

If the session has two people or two sittings, run C on hardware and E in
parallel. If not, C first — the map is the unblocking artefact.

**What must not happen:** building the location library or the goal UI on top
of live SLAM. Coordinates from a live-SLAM session do not survive a restart
(§17.12/§17.18, two sessions spent proving it), so a "Rack A3" taught today
points at a different floor tile tomorrow. Stage D is the gate for anything
that stores a coordinate.
