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

## ⏸ RESUME HERE — session paused mid-deploy, 24 Aug 2026 (§17.33)

**The robot has not moved since 22 Aug. No map was made on 24 Aug.** The
session was spent auditing and cleaning the Pi before driving, which found
two real defects. Full detail in §17.33; what you need to restart is here.

### One command resumes the work

SSH in (`ssh aritra@10.42.0.1` if the Pi rebooted onto its own AP, else
`ssh aritra@<eduroam-ip>`) and paste this **single line** — it re-verifies
both files and only builds if they are correct:

```
cd ~/ros2_ws/src/mecanum_robot/mecanum_robot && printf '336764e83c193b0869ce3cbe4ec66a860e0884984d155331ebd599a99e56231d  phone_dashboard.py\n143702e8511f7d8bed64811abb61a6903c2d10da8e60f1e61d6bcbe9ccd1860b  odometry_publisher.py\n' | sha256sum -c - && cd ~/ros2_ws && colcon build --packages-select mecanum_robot && sudo systemctl restart aislebot.service && sleep 10 && (ros2 topic list | grep -E 'odom/reset|goal_pose_click' ; echo '--- nodes ---' ; ros2 node list)
```

Success looks like: two `: OK` lines, `1 package finished`, **`/odom/reset`
present in the topic list**, and 11 nodes. `/odom/reset` is the ZERO
button's plumbing and the clearest single proof the new dashboard is live.

If `sha256sum -c` says FAILED for `phone_dashboard.py`, re-fetch it. Note
that **`curl --retry` does not retry TLS handshake errors** — it only
retries transient HTTP responses and timeouts, so `--retry-all-errors` is
required. That bit us once already on 24 Aug:

```
curl -sSL --retry 5 --retry-delay 2 --retry-all-errors -o phone_dashboard.py https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/mapping-autonomous-nav-695glw/src/mecanum_robot/mecanum_robot/phone_dashboard.py
```

This needs internet, so it must happen on eduroam, not the AisleBot-Pi AP.

### Exact deploy state — do not assume either way

| File | State |
|---|---|
| `odometry_publisher.py` | **Verified deployed** — `143702e8511f7d8b…`, 12,425 B |
| `phone_dashboard.py` | **Probable, unverified.** Correct hash appeared in a scrambled terminal paste. Treat as unknown until `sha256sum -c` says OK. |
| `colcon build` | **NOT RUN** |
| `systemctl restart` | **NOT RUN** |

So the robot is still executing the old `install/` tree — the running
dashboard is `fe2c3be`, with **no ZERO button and no save-on-stop**. The
`src/` tree is in a mixed state. Build before drawing any conclusion from
dashboard behaviour.

### What changed on the Pi on 24 Aug

- **2.0 GB reclaimed**, 58% → 51%. journald vacuumed and capped at 100 MB;
  `~/.ros/log`'s 5,269 run dirs, `~/.vscode`, the YDLidar SDK build tree,
  the superseded kernel, and eight snaps (firefox, thunderbird, snap-store
  and bases) all removed.
- **The Pi now boots to `multi-user.target`, not GNOME.** ~250 MB RAM and a
  core handed back to the ROS stack during mapping — §17.25 is a recorded
  case of CPU starvation killing SLAM outright. Reverse with
  `sudo systemctl set-default graphical.target`; start a desktop on demand
  with `sudo systemctl isolate graphical.target`.
- **Dead code removed**, tarballed first to `~/aislebot_deadcode_<stamp>.tar.gz`:
  `phone_dashboard.bak.py`, `arm_bridge.bak.py`, `hardware.launch.py`, and
  `rf2o_laser_odometry` (a dead end recorded in §13.5).
- **`system/ydlidar_params.yaml` was a live landmine and is fixed.** It was
  committed flat, with no `ros__parameters` nesting, so ROS 2 would have
  bound none of it and dropped the X4 Pro to compiled defaults.
  `install.sh:220` would have overwritten the Pi's working copy. It never
  fired only because install.sh has not run since 26 June. **Do not
  "simplify" that file back to a flat list.**

### Data now safely off the Pi — and unanalysed

`~/aislebot_logs` (192 MB, 369 files) and `~/slam_tests` (133 MB) are both
copied to the PC and to Drive. `~/slam_tests` holds three **MCAP rosbags**:
`slam_test_01` (94.4 MB, 20 Aug), `slam_test_02` (27.4 MB, 20 Aug) and
`jump_154512` (11.8 MB, 22 Aug — Stage A's recording). **The two from 20 Aug
have never been opened.**

Open workstream, not started: **no finding in Part XVII has ever come from
more than one run.** 70 maps, 73 run reports and 124 telemetry CSVs have
never been analysed as a corpus. Three questions are answerable offline
without driving — map repeatability across 70 grids of the same space
(which *is* Stage C's integrity criterion), whether §17.30's cold-start
recovery pattern survives 73 reports rather than the four goals it was
inferred from, and whether per-wheel behaviour has drifted over three weeks.

### Then pick up the plan below at "Today's plan"

Skip step 1's `colcon build` line — the command above does it. Everything
from **Stage C** onward is unchanged and still the goal: park on the mark,
ZERO, MAP, VIEW, drive the perimeter 0.5–1.5 m off the walls, MAP to stop
and save.

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
