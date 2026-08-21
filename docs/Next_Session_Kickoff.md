# Next Session Kickoff — paste this to start

Self-contained prompt for the next Claude Code session. It assumes no memory of
the previous conversation — everything needed is either here or in the repo
(`docs/Dashboard_Map_System.md`, `docs/Research_Journal.md`,
`docs/Production_Architecture.md`, `docs/Important_Commands.md`).

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/mapping-autonomous-nav-695glw`. Read `docs/Dashboard_Map_System.md`
> in full, plus `docs/Research_Journal.md` §17.31, before doing anything else
> — the plan for today is already written there and reasoned through. Don't
> re-derive it.
>
> Today we build the robot's own map system. The goal is one clean saved map
> plus AMCL localising on it, which is what unblocks the dashboard product
> (map in the browser, click-to-goal, named locations — no Foxglove).
>
> Start with the pre-flight audit in this file — I want to know what's
> actually on the Pi before we touch anything, because it has drifted from the
> repo before. Then Stage A, and don't skip it: three sessions have suspected
> loop closure without measuring it.
>
> Walk me through it on hardware step by step — I'll run each command and
> paste the output. Don't assume a step succeeded.

---

## The user's coordinate convention

The user reports positions in **their own body-frame convention**, not raw
map-frame TF numbers:

- **Origin is the robot** (`base_link`), not the map origin
- **Forward = positive Y**, **right = positive X**
- **Values in cm**

"We are at 3,0" means ~3 cm to the robot's right, 0 cm forward — *not* a
map-frame coordinate. Translate explicitly in both directions and always say
which frame a number is in. The tools (`nav_goal.py`, action feedback,
`tf2_echo`) all print map frame natively.

## Working style that has been productive

Hands-on-hardware, one command at a time, user pastes every output, nothing
assumed to have succeeded. Keep doing that. When something looks wrong, say so
plainly rather than narrating around it — and when the user's own analysis is
right (it often is), say so and build on it rather than re-deriving.

---

## Pre-flight — what's actually on the Pi

The user asked for this explicitly, and it is not ceremony: a full deploy audit
on 21 Aug found the Pi had drifted from the repo in **nine files**, including
the SLAM config and the entire manual-override layer, plus `esp32_bridge`
pinning a CPU core at 99.9 % since boot (`Production_Architecture.md` §7).

```bash
ssh aritra@10.42.0.1

# 1. What's running right now
ros2 node list
ps aux | grep -E "slam_toolbox|mapping_full|controller_server|bt_navigator" | grep -v grep
systemctl is-active aislebot.service

# 2. CPU headroom — §17.25 killed slam_toolbox outright by starvation
top -bn1 | head -15

# 3. The live SLAM config (workspace ROOT, not in a package)
cat ~/ros2_ws/slam_nodom.yaml | grep -E "loop_|max_laser|minimum_travel"

# 4. Does the deployed code match the repo?
ls -la ~/ros2_ws/src/mecanum_robot/mecanum_robot/
ls -la ~/ros2_ws/src/mecanum_navigation/mecanum_navigation/
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py

# 5. What maps and logs already exist
ls -la ~/aislebot_logs/ | tail -20
```

Compare (3) against `system/slam_nodom.yaml` in the repo and (4) against local
`sha256sum` of the same files. **Report differences before changing anything.**

---

## What's true right now — don't re-derive this

### Drive accuracy: validated, and not today's problem

- **Forward/back:** 0.5 m round trip, ~1.2 cm net error, confirmed three
  independent ways — TF math, tape measure, and `trajectory_viz.py`'s own
  summary (§17.29 kickoff, §17.30).
- **Pure lateral:** 0.5 m round trip, 1.63 cm net — same tier. §17.30's
  conclusion: **lateral motion is as accurate as forward motion.** The original
  "lateral drift" framing is closed.
- Final resting error sits at 1.97–1.99 cm regardless of recovery count. That
  is `SimpleGoalChecker`'s tuned `xy_goal_tolerance: 0.02` doing its job, not
  drift. Don't chase it.

**Do not spend today re-testing drive accuracy.** It passes.

### The actual open problem: live-SLAM pose jumps

§17.31 captured the strongest dataset yet — 4,818 samples, and re-derived
independently from the raw CSV rather than trusting the recorder's summary:

- **16 single-sample steps > 5 cm**, totalling 3.04 m = **27.6 % of the entire
  reported path length**
- Largest: **31.1 cm in one 0.10 s sample** ≈ 3.1 m/s apparent, against a
  0.15 m/s dashboard cap and a 0.48 m/s kinematic cap — **6–20× physically
  impossible**, so these are corrections, not motion
- Roughly one correction per ~18 s of driving

Four properties that identify it as pose-graph re-optimisation rather than
noise: every jump carries a yaw change (one hits 12.8°); directions are bimodal
(early ~+28…+93°, late ~−38…−143°) rather than uniform; magnitude grows
monotonically through the run; and two "doublets" fire 0.10 s apart.

Cause, near-certain but **not yet measured**: §17.25 relaxed exactly the
parameters that reject a bad loop closure, in an environment that is a junction
of similar-looking aisles with a permanent 90° rear blind sector.
`slam_nodom.yaml`'s own comment predicted this in writing. **Stage A measures
it before anything is tuned.**

### The reframe that makes this tractable

**Live SLAM is not what the product navigates on.** `map_server` + AMCL is
(`Production_Architecture.md` §3.1). AMCL localises against a *fixed* map and
never re-optimises a pose graph, so this failure mode doesn't exist there.

> Live SLAM doesn't need to be perfect. It needs to build **one clean map, once.**

That is today's actual goal. See `docs/Dashboard_Map_System.md` §0.

### Consequence: stop chaining goals under live SLAM

§17.31's compound four-waypoint test failed on leg 4 with 5 progress-checker
stalls, a **timed-out `Spin`** and a **timed-out `BackUp`** — the first
behaviour-server recovery failures in this project's history — and never
reached its goal. Legs 2 and 4 targeted the *same pose*; leg 2 was clean. That
comparison rules out goal tolerance and points at the state the stack was in.
Chaining goals through a pose estimate that snaps every ~18 s is measuring the
estimate, not the drive stack.

### Foxglove click-to-goal now works — and how, because it isn't discoverable

Reached for the first time 21 Aug. Three things must all be right, and each one
fails silently:

1. 3D panel settings → **Publish** section (below Topics/Custom layers) →
   **"2D pose (geometry_msgs/PoseStamped)"** — *not* "2D pose estimate"
   (`/initialpose`), *not* "2D point" (`/clicked_point`)
2. Its Topic field is **free text, no dropdown** — type `/goal_pose_click`
3. Then **select that tool** from the toolbar flyout. The toolbar defaults to
   the point tool, which publishes a `PointStamped` Nav2 ignores — a yellow dot
   appears, nothing moves, nothing errors anywhere

Foxglove stays a debugging instrument. Nothing in the product may depend on it.

### Physical/service state at session end (21 Aug)

Everything was **left running and healthy** after a full clean restart:
`aislebot.service` restarted on the mark (`odom→base_link` = `[0,0,0] @ -90°`
confirmed), `mapping_full.launch.py` up with LiDAR + SLAM, `nav2_slam.launch.py`
up to `Managed nodes are active`, no errors. It has since been left overnight —
**verify, don't assume.** Robot position on the mark is unconfirmed after the
last click-to-goal drive.

---

## Today's plan

Full detail, with parameter-level reasoning and the code shapes for the
dashboard build, is in **`docs/Dashboard_Map_System.md`**. Summary:

| Stage | What | Time | Gate |
|---|---|---|---|
| **A** | Split the jump: `map→odom` vs `odom→base_link` | 20 min | Pre-committed decision tree — decide before looking |
| **B** | Tune 3 params: `loop_search_maximum_distance 5.0→2.0`, `loop_match_minimum_chain_size 5→8`, `max_laser_range 12.0→10.0` | 20 min | Only if A says SLAM. Only these three |
| **C** | Commissioning drive: one wall-hugging circuit, return to mark, save the map | 60 min | 3-part acceptance gate before saving |
| **D** | AMCL first run on the saved map | 45 min | Fix suspected `robot_model_type` bug first |
| **E** | Dashboard map rendering | hours | Not gated on A–D; pure software |

**If the day ends after Stage C with one good saved map, that is a success.**
It would be the first stable coordinate frame this project has ever had, and
every product feature depends on it.

### Three things to get right

1. **Don't tune before Stage A.** §17.28 already recorded the lesson: changing
   loop-closure parameters without evidence repeats the exact mistake being
   diagnosed. Three sessions have now suspected loop closure without measuring
   it. `tools/bag_tf_diff.py` was built for this and has never been run.
2. **This `slam_toolbox` build (2.8.5) has no loop-closure signal at all** — no
   console output, no topic, verified against both source and the live node's
   topic list (§17.29). Don't grep for it. TF differencing is the only
   observation available.
3. **Nothing that stores a coordinate may be built before Stage D.** Live-SLAM
   coordinates don't survive a restart (§17.12/§17.18), so a location taught
   today points at a different floor tile tomorrow.

### Two code traps found by reading (§17.31)

- **`src/mecanum_robot/resource/dashboard.html` is never read by anything.**
  The served page is the `DASHBOARD_HTML` constant at `phone_dashboard.py:112`.
  Editing the `.html` file does nothing.
- **The dashboard WebSocket is client→server only.** No broadcast path exists;
  building it is the first step of Stage E and everything else depends on it.

---

## After today — the product build order

Unchanged from `Production_Architecture.md` §7, with today's stages mapped on:

```
0. Drive accuracy          ✅ PASSED (§17.30)
1. Mapping drive             <- Stage C
2. Save the map              <- Stage C
3. AMCL localization         <- Stage D
4. Location library + teach flow
5. Map rendering in dashboard  <- Stage E (parallelisable)
6. Goal sending from dashboard
7. UI rework — map-first, overlay controls
```

## Lower priority, worth remembering

- Test whether a pure-*forward* move introduces a small lateral component —
  §17.30's candidate explanation for the original 1–3 cm side offset, never
  tested directly.
- The recovery-count cold-start pattern (worst on the first lateral goal after
  a fresh bringup): stiction vs. MPPI warm-up, undistinguished. Low priority —
  final accuracy is unaffected.
- The `base_link` non-REP-103 axis convention is "the stack's deepest open
  issue" per `nav2_params.yaml`'s own header, and has bitten the project five
  times. The permanent fix (move the −90° into the URDF's `laser_joint`) is a
  large cross-cutting refactor — deliberately deferred, but every new component
  that carries a notion of "forward" needs checking against it. The dashboard
  canvas is the next such component.
