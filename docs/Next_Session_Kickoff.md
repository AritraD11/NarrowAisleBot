# Next Session Kickoff — paste this to start

This is the self-contained prompt for the next Claude Code session. It assumes
no memory of this conversation — everything it needs is either in this file
or in the repo itself (`docs/Research_Journal.md`, `docs/Production_Architecture.md`,
`docs/Navigation_Theory.md`, `docs/SLAM_Theory.md`).

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/mapping-autonomous-nav-695glw`. Read `docs/Research_Journal.md`
> §17.29–§17.30 and this file in full before doing anything else — don't
> re-derive what's already documented here.
>
> Today (21 Aug 2026) we ran the first-ever hardware-confirmed, tape-measured
> Nav2 goal round trip: forward 0.5m, then back. Forward/backward accuracy is
> now genuinely good — three independent measurements (TF math, tape measure,
> and `trajectory_viz.py`'s own summary) all converge on the same ~1.2cm net
> round-trip error. **Lateral drift is the open problem now** — same round
> trip left the robot ~1-3cm off to the side of where it started, and that's
> today's actual focus, not more forward/backward testing. Walk me through
> it step by step on hardware — I'll report back what each command prints
> and paste terminal output; don't assume a step succeeded.

---

## IMPORTANT: the user's coordinate convention for this session

Starting this session, the user reports positions in **their own convention**,
not raw map-frame TF numbers:

- **Origin is `base_link`** (the robot itself), not the map frame origin.
- **Robot moving forward = positive Y.**
- **Robot moving right = positive X.**
- **Values are given in cm.**

This is a body-frame, forward/right convention — different from the map-frame
`(x, y)` pairs `nav_goal.py` and the action feedback report. When the user
gives a number like "we are at 3,0 (cm)", that means ~3cm to the robot's
right and 0cm forward/back from where it started, **not** a map-frame
coordinate. Translate carefully between the two when explaining TF-derived
numbers back to the user — don't assume they mean map frame just because
that's what the tools print natively.

## What's true right now (don't re-derive this)

- **Forward/backward accuracy: confirmed good, from three independent
  sources.** Sequence run: robot at map-frame `(0.4853, -0.0697, -91.10°)` →
  commanded `+0.5m` forward via `nav_goal.py --forward 0.5` → goal
  `(0.9852, -0.0793)` → landed at `(0.9744, -0.0626)`, tape-measured at
  **0.48m** (vs 0.5m commanded). Then commanded back to the original pose →
  landed at `(0.4885, -0.0814)`.
  - TF math: outbound displacement ≈0.489m (vs 0.48m tape) — agree to ~1cm.
  - `trajectory_viz.py --no-reference --map-frame map`'s own summary over
    the whole round trip (8873 samples, 1141.3s): overall start
    `(0.4853, -0.0697)`, overall end `(0.4878, -00.0816)`, path travelled
    `1.0049m` (≈2×0.5m, correct for there-and-back), **straight-line (net)
    displacement 0.0122m**.
  - That 1.22cm figure from the recorder matches the TF-computed ~1.2cm
    return-target miss almost exactly. Three measurements, same number.
    This is a solid, well-triangulated result — treat forward/backward
    tracking as validated for now, don't re-test it without a reason.
- **Lateral drift is real and is the open problem.** The same round trip
  left the robot measurably off to the side — the user's tape/visual
  estimate was ~3cm, TF math from the return-target miss says ~1.2cm side
  component. Both point the same direction; the exact magnitude is fuzzy at
  this precision, so report it as a **range (roughly 1-3cm per meter of
  travel)**, not a single number.
- **One unexplained anomaly from today, not yet investigated:** the
  **return leg's** action feedback showed `number_of_recoveries: 1`; the
  **forward leg** showed `0`. Something triggered a Nav2 recovery behavior
  (backup / spin / clear-costmap — feedback doesn't say which) on the way
  back that didn't happen going out. **This has not been checked yet** —
  next session should grep Terminal 2's (`nav2_slam.launch.py`) console
  output or its log file for `behavior_tree`/recovery-related lines around
  that run and find out what fired and why. This could plausibly be related
  to the lateral drift — don't assume it is, but don't ignore it either.
- **A small mid-return pose discontinuity was also observed:** around
  `navigation_time ≈ 15.8s` into the return leg, the feedback jumped from
  `y=-0.0949` to `y=-0.0826` (≈1.2cm) in a single tick, with a small
  heading shift alongside it. Small-scale version of the same category of
  event (a discrete correction rather than smooth tracking) that originally
  motivated this whole investigation, just ~20x smaller than the 25cm jumps
  that kicked it off. Worth knowing about, not worth chasing right now —
  low priority relative to the lateral-drift work.
- **Dashboard vs. manual launch:** the phone dashboard's Map button only
  replaces Terminal 1 (`mapping_full.launch.py`) and discards its console
  output (`stdout=DEVNULL` in `phone_dashboard.py`'s `start_mapping()`) —
  fine for casual driving, but loses the SLAM log if debugging needs it.
  It does not touch Nav2, the trajectory recorder, or Foxglove's rendering
  load — switching to it will **not** fix Foxglove lag, which is a
  network/rendering issue independent of what launched the ROS nodes.
- **Physical/service state as of end of this session:** the user was in the
  process of (1) restarting Terminal 1 (`mapping_full.launch.py`) fresh —
  only the initial `[INFO] [launch]:` line was seen before this session
  ended, **configure/active status not yet confirmed**, check before
  assuming it's up; (2) placing the robot back on the physical zero floor
  mark; (3) planning to restart `aislebot.service`. **Verify all three
  actually happened** (ask directly, don't assume) before running any new
  goal — same discipline as always on this project.

## Today's actual task: characterize and reduce lateral drift

**1. Confirm the environment is actually in the state described above**
before doing anything else:
```bash
ps aux | grep -E "slam_toolbox|mapping_full" | grep -v grep   # Terminal 1 up and configured?
ps aux | grep -E "controller_server|planner_server|bt_navigator" | grep -v grep   # Nav2 up?
```
Ask the user to confirm: is the robot physically on the zero mark right now?
Was `aislebot.service` actually restarted?

**2. Check the outstanding recovery-event anomaly** from today's return leg
— grep Terminal 2's log/console for recovery/behavior-tree activity. This
is a loose thread from the previous session, worth closing before adding
new variables.

**3. Design a test that isolates lateral drift specifically**, rather than
re-running the same forward/back test. Options to consider with the user:
- Repeat the same forward+return test 2-3 times and check if the lateral
  offset is **consistent in direction and magnitude** each time (systematic
  → likely a mecanum kinematics/wheel-calibration scaling issue, tunable in
  software) vs. **random** each time (→ more likely wheel slip or a
  mechanical issue, not fixable by retuning gains).
- A pure lateral (strafe) command, if the mecanum drive supports commanding
  pure sideways motion, to directly measure strafe accuracy in isolation
  rather than inferring it as a side-effect of a forward move.
- Whichever test is chosen, use the user's coordinate convention (see above)
  when reporting results back to them, and be explicit about which frame
  any given number is in.

**4. If a systematic pattern emerges**, the likely places to look are the
mecanum inverse-kinematics matrix / wheel calibration constants (wherever
`cmd_vel` gets converted to individual wheel velocities) and
`cmd_vel_axis_adapter.py`'s axis handling — but don't go looking there
until the test data actually points to a systematic (not random) cause.

## After lateral drift is characterized — the original build-order plan

Unchanged from `docs/Production_Architecture.md` §7 — once drive accuracy
(now including lateral) is judged good enough:
- Wall-hug mapping drive, return to zero mark, tape-measure the error.
- Save the map (first one this project has ever produced).
- First hardware run of `navigation.launch.py` (saved map + AMCL).
- Then, and only then, the dashboard/UI work described in
  `docs/Production_Architecture.md`.

## Lower priority, worth remembering

- Full Phase 1 tape-measured manual-drive validation (straight/strafe/
  diagonal vs. physical tape, Nav2 off) — still open from the original plan,
  may now be directly useful for isolating the lateral drift's source.
- The original perceptual-aliasing jump investigation (`bag_tf_diff.py`
  against `slam_test_02`) is still technically open but superseded by this
  reliability-first work — don't resume it unless the user asks.
