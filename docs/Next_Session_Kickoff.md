# Next Session Kickoff — paste this to start

Self-contained prompt for the next Claude Code session. It assumes no memory of
the previous conversation — everything needed is either here or in the repo
(`docs/Dashboard_Map_System.md`, `docs/Research_Journal.md`,
`docs/Production_Architecture.md`, `docs/Important_Commands.md`,
`docs/MATLAB_Navigation_Reference.md`).

**Rewritten 22 Aug 2026 (§17.32).** The 21 Aug version of this file is
superseded: Stage A has now been run, Stage B is deployed, and the whole
workflow has moved off the terminal and into the dashboard.

---

## ⏸ RESUME HERE — 25 Aug 2026 (§17.34)

**The platform is fixed and verified. The map integrity check is the only
thing standing between you and Stage D.**

### State of the robot — verified, not assumed

- **All 30 deployed files hash-match `main` byte-for-byte**, including
  `~/ros2_ws/slam_nodom.yaml` (`7ec7904aa3ab…`, Stage B) and
  `params/ydlidar.yaml` (`049fbbe7bff9…`). First fully known state this
  project has had.
- `phone_dashboard.py` is `b920e6652ab7c92f…` (103,005 B).
- **A map now survives a restart**, confirmed on hardware:
  `run_20260825_151713.pgm`, 27,383 B, header stamped
  `# CREATOR: phone_dashboard from cached /map`.
- The map view no longer drives the robot when you touch it.
- Pi boots to `multi-user.target`; 2 GB reclaimed; journald capped.

### THE ONE OPEN QUESTION — do this first

**Is any of today's maps clean enough for AMCL?** Nobody has looked at the
grid itself. Numbers alone cannot settle it and have already pointed both
ways on the same map:

| | `run_20260825_113735` | `run_20260825_151713` |
|---|---|---|
| Size | 26,011 B, 134×194 | **27,383 B, 138×198** |
| Occupied | 540 cells (2.08%) | not yet measured |
| Unknown | 80.95% — its report says *"not yet a usable map for navigation"* | not yet measured |
| Wall vs bounding perimeter | **27 m / 32.8 m = 0.82** — the drive got round most of the room | — |

Those two readings disagree. "81% unknown" measures how much of a
*bounding box* is unmapped, and if the space is L-shaped or has shelving,
most of that box was never floor. The wall ratio is the more meaningful
number. **Settle it by looking:**

```powershell
curl.exe -sSL -o map_viewer.html https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/docs/tools/map_viewer.html
```

Double-click it, drag in the `.pgm` **and** `.yaml` together. Judge on
§17.32's revised gate — **walls present / map integrity / return-to-mark**:

- **Continuous, single-thickness walls** → good, proceed to Stage D.
- **A doubled wall, a fork, a corridor appearing twice** → a false loop
  closure fused two places that are not the same place. That map cannot
  localise and the run has to be repeated.

Single-sample step size is **diagnostic, not pass/fail** (§17.32).

### Also worth knowing

- **Best return-to-mark ever: 1.9 cm / 0.2°** on a ~30 s drive
  (`MAP x 0.018 y -0.006`, `NOSE -90.2°`). One drive, not a repeatability
  claim — and its map was lost to the very bug fixed later that day.
- `tools/map_corpus.py` compares every run in a folder at once. Needs the
  files gathered in one place; ~20 of them are already in
  `C:\Users\aritradas\Documents\data\field_runs`.
- **Never analysed as a corpus:** 70+ maps, 73 run reports, 124 telemetry
  CSVs, and three `.mcap` rosbags in `~/slam_tests` (two of which have
  never been opened). Every finding in Part XVII comes from reading exactly
  one run.
- **`AISLEBOT_VIDEO_DECODER_APP`** — recommended against on reasoning
  (video is derived from what the Pi already logged, and lossier), but the
  implementation has never been read. Owed a proper look.

### Traps that bit on 25 Aug

- **`curl --retry` does not retry TLS failures.** Use
  `--retry-all-errors`. When eduroam blocks HTTPS from the Pi entirely,
  relay through the PC — `Important_Commands.md` §2.1.
- **Check the Pi's address every session** (`ip -4 -br addr`). Its eduroam
  lease moved twice in two days, and `aritra-desktop.local` fails to
  resolve from Windows often enough not to trust.
- **`10.42.0.1` only exists while the Pi hosts its own AP.** On eduroam it
  gives a timeout that looks exactly like the robot being down.

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/mapping-autonomous-nav-695glw`. Read this file and
> `docs/Research_Journal.md` §17.32 in full before doing anything else.
>
> Today's goal: **one clean commissioned map with real walls in it, saved,
> then AMCL localising on it.** Stage A and B are done — don't redo them.
>
> I want to run the whole thing **from the dashboard, not the terminal**.
> The MAP button brings the stack up and saves the map on stop; the joystick
> drives; VIEW shows the map live; ZERO re-zeros. All of that is built but
> **none of it has run on hardware once** — expect first-run bugs and help me
> work through them.
>
> Walk me through it step by step — I'll do each thing and report back.
> Don't assume a step succeeded.

---

## The user's coordinate convention

The user reports positions in **their own body-frame convention**, not raw
map-frame TF numbers:

- **Origin is the robot** (`base_link`), not the map origin
- **Forward = positive Y**, **right = positive X**
- **Values in cm**

"We are at 3,0" means ~3 cm to the robot's right, 0 cm forward — *not* a
map-frame coordinate. Translate explicitly in both directions and always say
which frame a number is in.

## Working style

Hands-on-hardware, one step at a time, nothing assumed to have succeeded.
**Never mark a step done without seeing its actual output.** When something
looks wrong, say so plainly. When the user's own analysis is right (it often
is), say so and build on it rather than re-deriving it.

The user is moving deliberately away from the terminal. Prefer a dashboard
path over an SSH command wherever one exists, and when one doesn't, say so
rather than quietly falling back to SSH.

---

## THE BIG FINDING OF 22 AUG — read this before trusting any earlier entry

**`system/slam_nodom.yaml`'s loop-closure tuning was committed on 19 Aug and
never reached the robot.** `install.sh:228` is the only mechanism that copies
it to `~/ros2_ws/slam_nodom.yaml`, `mapping_full.launch.py:62` loads the Pi's
copy, and that copy's mtime was **26 June** — i.e. the last time `install.sh`
ran. Every drive from 19–21 Aug ran on `slam_toolbox` **stock defaults**.

Consequences for the journal:

- §17.28–§17.31's hypothesis — "§17.25 over-relaxed the closure gate, causing
  false positives" — was diagnosing **parameters that were never active**.
  Stock is *stricter* than §17.25's values, not looser.
- §17.27's "first hardware confirmation of the tuning, 50 cm → 2 cm" cannot
  have been the tuning. **What did cause it is an open question, not a
  settled one.** The user confirms the robot was physically parked on the
  mark and returned to it, so the naive "it was a re-zero artefact"
  explanation does not fit either. Leave it open; don't invent a cause.

**Lesson worth keeping:** a value in the repo is not a value on the robot.
Verify deployed config with `ros2 param get` against the *live node*, not by
reading a file — that is what caught this.

---

## What's true right now — don't re-derive

### Drive accuracy: validated, closed

0.5 m forward/back ≈ 1.2 cm net; 0.5 m pure lateral ≈ 1.63 cm. Final resting
error 1.97–1.99 cm is `SimpleGoalChecker`'s `xy_goal_tolerance: 0.02` doing
its job, not drift. **Do not spend time re-testing this.**

### Stage A: RUN, and it answered the question

`tools/bag_tf_diff.py`'s first-ever run, on a 233.8 s drive:

| Pair | Distinct changes | Behaviour |
|---|---|---|
| `map→odom` | **3** | flat all run, then **39.57 cm / −13.80°**, then **39.00 cm / +13.80°** 12.5 s later, landing back within 0.7 cm |
| `odom→base_link` | 787 | smooth, ~2.3 mm per tick — **including at both jump instants** |

Wheel odometry did not blink at the moment `map` moved 40 cm. That is row 1 of
the pre-committed decision tree: **SLAM pose-graph correction, not odometry.**
Settled. Don't re-measure it.

### Stage B: DEPLOYED and verified live

`system/slam_nodom_stageB.yaml` is on the Pi as `~/ros2_ws/slam_nodom.yaml`
(sha256 `7ec7904a…0093ba`), confirmed by `ros2 param get` on the running node:

| Parameter | Was | Now |
|---|---|---|
| `loop_search_maximum_distance` | 5.0 | **2.0** |
| `loop_match_minimum_chain_size` | 5 | **8** |
| `max_laser_range` | 12.0 | **10.0** |

Baseline backed up at `~/ros2_ws/slam_nodom_baseline_<stamp>.yaml`.

### Stage B's measured effect — real, partial

Two drives on Stage B, both from a verified `[0,0,0] @ -90°` re-zero:

| Drive | Path | Final `map→base_link` | Steps > 10 cm |
|---|---|---|---|
| out-and-back over the same line (confounded) | — | **36.3 cm**, 5° off | 9, spread throughout |
| a closed box, each leg new ground | 3.4 m / 223 s | **5.0 cm**, 0.75° off | 5, **all in the last 30 s** |

Before Stage B the jumps came roughly every 18 s throughout a run. On the box
drive the first 185 s had **zero**. The remaining 5 cluster exactly where
loop closure first becomes eligible.

**Probable explanation, not yet confirmed:** `minimum_travel_distance: 0.2`
puts a graph node every 20 cm, and chain size 8 needs 8 consecutive nodes
≈ **1.6 m of driving** before closure can fire at all. On a 3.4 m drive that
lands in the back half — which is where the jumps are. So the clustering may
be eligibility, not aliasing.

**Evidence they are *correct* closures:** the map came out visibly clean (no
fold, tear, doubled wall, or forked corridor) and the robot landed 5 cm from
truth. A wrong closure gives you neither.

### Consequence: the acceptance gate needs a fix

`Dashboard_Map_System.md` §3 says "no single-sample step > 10 cm". That
criterion was written to catch bad closures, **but it cannot tell a good
closure from a bad one** — a legitimate correction of accumulated drift trips
it just as hard. The two criteria that actually discriminate are **map
integrity** and **return-to-mark accuracy**. Judge on those.

**Do not raise `loop_match_minimum_response_coarse`/`_fine` to 0.30/0.40.**
That lever is explicitly gated on "if the map visibly folds" and it did not.

---

## What was built 22 Aug — all code-complete, NONE hardware-tested

### The dashboard is now the whole workflow

`phone_dashboard.py` gained, in one session:

- **Server → client WebSocket broadcast.** The socket was client → server only
  before; this was the single largest missing piece. ROS callbacks write plain
  node attributes, one async task reads them on a timer and pushes — one
  writer, one reader, no locks, no cross-thread asyncio.
- **Live map + pose in the browser** (`VIEW` button). Occupancy grid streamed
  raw and rendered client-side; robot drawn as its **real 1.12 × 0.48 m
  footprint**, not a dot, so "does it fit this aisle" is answerable.
- **Click-to-goal** with a two-tap arm, publishing `/goal_pose_click`.
- **`ZERO` button** — re-zero without a terminal. This needed a new
  `/odom/reset` topic in `odometry_publisher.py`, because the old route
  (`systemctl restart aislebot.service`) also kills the dashboard.
  **It refuses while mapping is active**, enforcing §8's ordering.
- **Pose CSV** written automatically for the duration of every mapping run
  (`run_<stamp>_pose.csv`, columns `epoch_s, map_x, map_y, yaw_deg`), so jump
  analysis no longer needs a separately-launched terminal tool.

### Already there, discovered by reading — don't rebuild

- **`stop_mapping()` already saves the map** via `map_saver_cli`, to
  `~/aislebot_logs/run_<stamp>.pgm/.yaml`. The MAP button is already a full
  start-stack / stop-stack-and-save cycle. There is no separate save button
  and none is needed.
- The dashboard's telemetry CSV is the 13-column motor format
  `telemetry_analyzer.html` expects. That pairing was always intended.

### `docs/tools/map_viewer.html` — new

`telemetry_analyzer.html`'s map dropzone only unlocks after loading a valid
13-column run, so it cannot open a bare map. `map_viewer.html` takes just the
`.pgm` + `.yaml` pair. Parses P5/P2 PGM and `map_saver_cli`'s YAML entirely
client-side; verified against a synthetic file before shipping.

---

## Today's plan

### 1. Pre-flight (short — most of it was settled 22 Aug)

```bash
ros2 node list                                    # expect the full 11-node set
ros2 param get /slam_toolbox loop_search_maximum_distance   # MUST read 2.0
ros2 param get /slam_toolbox loop_match_minimum_chain_size  # MUST read 8
ros2 param get /slam_toolbox max_laser_range                # MUST read 10.0
```

Then **deploy the new dashboard**, which has not run once:

```bash
cd ~/ros2_ws && colcon build --packages-select mecanum_robot
sudo systemctl restart aislebot.service     # robot need not be on the mark yet
```

Open `http://10.42.0.1:8080` on the phone. **Expect first-run bugs** in the
map view, the broadcast loop, or the ZERO button — none of it has hardware
time. Budget for that; don't treat a failure there as a SLAM problem.

### 2. Stage C — the real commissioning drive

Everything below is dashboard-only:

1. Park physically on the mark.
2. **ZERO** (two taps). Must happen *before* MAP — the button enforces it.
3. **MAP** — brings up LiDAR + `scan_relay` + `slam_toolbox`, starts both CSVs.
4. **VIEW** — watch the map build live. This is the new instrument: a fold is
   visible *the moment it happens*, which no after-the-fact screenshot gives.
5. Drive the **perimeter** with the joystick: **0.5–1.5 m off the walls**,
   slow, one direction, full loop, back to the mark. The rear 90° is
   permanently blind (mast), so walls register only to the front/left/right.
   *This is what 22 Aug's test drives lacked — they were open-floor boxes and
   produced free space with no wall geometry.*
6. **MAP** again to stop — this saves the map automatically.

**Acceptance (revised — see above):**

| Check | Pass condition |
|---|---|
| Return-to-mark | VIEW's HUD reads ≈ `(0, 0)`, nose ≈ `-90°` |
| Map integrity | no folds, tears, doubled walls — check in `map_viewer.html` |
| Walls present | the map actually contains occupied cells, not just free space |

Single-sample step size is **diagnostic, not pass/fail**.

### 3. Stage D — AMCL, never run on hardware

**Verify the suspected bug first** (`nav2_params.yaml:57` has
`robot_model_type: "omnidirectional"`; on Jazzy this is a pluginlib class
name, so it likely needs `"nav2_amcl::OmniMotionModel"`):

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
```

Change it only if the plugin XML confirms. Getting it wrong means AMCL refuses
to configure and `lifecycle_manager` aborts the entire bringup.

Then: stop mapping completely (`ros2 node list | grep slam_toolbox` must come
back empty — AMCL and slam_toolbox both publish `map→odom` and must never run
together), park on the mark, launch `navigation.launch.py` against the saved
map, and confirm `map→base_link` ≈ `(0,0) @ -90°` **with no SLAM running**.

That is the first time this robot will know where it is on a remembered map.

### 4. First autonomous goal + the obstacle test the user has been waiting for

Once AMCL holds: send **one** goal from the dashboard (tap GOAL, tap the map,
drag to aim the nose). One goal, not a chain.

Then the obstacle-avoidance demo, which needs no extra work — it is already
configured and independent of pose accuracy:

- **Soft layer:** the local costmap inflates live LiDAR returns
  (`inflation_radius: 0.65`) and MPPI plans around them. This is what
  re-routes around a pallet that was not there when the map was made.
- **Hard layer:** `collision_monitor` forward-simulates the padded 1.12 × 0.48 m
  footprint along the commanded velocity and intervenes only if that path
  actually collides within 1.2 s. It is **velocity-aware, not a static zone** —
  a stationary robot near an obstacle correctly does nothing.

Put an obstacle in the path of a goal and watch both. This is safe to try
before Stage D if the user wants it early, since neither layer depends on the
global pose estimate.

---

## Standing traps

- **`base_link` is NOT REP-103: `+X` = RIGHT, `+Y` = NOSE.** Sixth place it
  has bitten the project. Any new component with a notion of "forward" needs
  checking against it — the dashboard canvas now does (verified numerically:
  at −90° the 1.12 m long axis lies along map `+X`, the nose direction).
- **This `slam_toolbox` build (2.8.5) has no loop-closure signal** — no
  console output, no topic. Verified against source *and* the live node. TF
  differencing is the only observation available. Don't grep for it.
- **`src/mecanum_robot/resource/dashboard.html` is dead code.** The served
  page is the `DASHBOARD_HTML` constant at `phone_dashboard.py:112`.
- **Nothing that stores a coordinate before Stage D.** Live-SLAM coordinates
  don't survive a restart, so a location taught today points at a different
  floor tile tomorrow.
- **Never run AMCL and `slam_toolbox` together.** Both publish `map→odom`.
- **A repo value is not a robot value.** Check the live node.

## Deferred, still worth remembering

- Location library + teach flow (gated on Stage D)
- Delete or wire up the dead `dashboard.html` — not during map work
- Whether a pure-*forward* move introduces a small lateral component (§17.30's
  untested candidate explanation for the original 1–3 cm side offset)
- The recovery-count cold-start pattern (stiction vs. MPPI warm-up)
- Moving the −90° into the URDF's `laser_joint` — large cross-cutting refactor
- **IMU: decided against for now (22 Aug).** Considered an MPU-6000/6050 as a
  cheap route in; rejected — no magnetometer means no absolute heading
  reference, which is the entire point, and `ekf_params.yaml` fuses IMU yaw
  as ground truth, so a drifting signal there would actively hurt. Orientation
  continues from wheel odometry + SLAM alone, same as today. BNO055 remains
  the right part if this is ever prioritized — full reasoning in
  `docs/MATLAB_Navigation_Reference.md` §1. **Don't re-open this unless the
  user raises it.**
- `docs/MATLAB_Navigation_Reference.md` has one more small, harmless-to-defer
  finding: `ekf_params.yaml`'s `imu0_config` fuses `roll, pitch` from the IMU
  while `two_d_mode: true` already forces those same states toward zero
  independently — redundant, not broken. Clean up to `roll, pitch: false,
  false` (keep `yaw: true`) whenever this file is next touched for real
  hardware.
