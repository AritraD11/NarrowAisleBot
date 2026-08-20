# Next Session Kickoff — paste this to start

This is the self-contained prompt for the next Claude Code session. It assumes
no memory of this conversation — everything it needs is either in this file
or in the repo itself (`docs/Research_Journal.md`, `docs/Navigation_Theory.md`,
`docs/SLAM_Theory.md`).

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/mapping-autonomous-nav-695glw`. Read `docs/Research_Journal.md`
> §17.25–§17.28 and `docs/Next_Session_Kickoff.md` in full before doing
> anything else — don't re-derive what's already documented there.
>
> The robot is parked at the physical zero mark right now, SLAM already
> running. Today's goal is diagnostic, not the full mapping drive yet: the
> last drive (§17.28) showed repeated large pose jumps while commanding
> pure forward motion — perceptual aliasing / spurious loop closure is
> suspected but not confirmed. Capture a short drive with BOTH the Foxglove
> trajectory plot AND the raw `slam_toolbox` terminal log running together,
> correlate them by timestamp, and tell me whether a bad loop-closure match
> is actually what's firing. Walk me through it step by step on hardware —
> I'll report back what each command prints and paste terminal output; don't
> assume a step succeeded.

---

## What's true right now (don't re-derive this)

- **Robot is parked at the physical zero mark, SLAM already running** —
  this session doesn't need to start from scratch. If in doubt whether the
  current `map→odom` is trustworthy, `sudo systemctl restart aislebot.service`
  while parked there re-zeroes cleanly (costs nothing, cheap insurance).
- **Suspected, unconfirmed issue (§17.28): perceptual aliasing.** A clean
  controlled test (§17.27: rotate 90°, drive ~2m out, drive back, rotate
  back) read ≈2cm/0.17° error — loop closure working correctly, a single
  clean correction. The very next drive — pure forward, no rotation
  commanded — showed the robot's displayed pose (not the map, which stayed
  correctly fixed) jumping repeatedly through large, inconsistent positions
  and headings. Working hypothesis: today's loop-closure tuning (`635e4b6`,
  §17.25) loosened match-acceptance thresholds to fix closures not firing at
  all, and that same loosening may now accept spurious matches in this map's
  self-similar corridor-junction shape (flagged as a risk back in §17.13/
  §17.15, before the numbers were ever chosen). **This is a hypothesis, not
  a diagnosis** — nothing has been re-tuned on the strength of it. The
  point of today's session is to get the evidence that confirms or kills it.
- `twist_mux` and `navigation.launch.py` (map_server + amcl) were built and
  pushed (`bd4fb1a`, `129150d`) but have **zero hardware confirmation**.
  Not today's priority — they need a saved map first, and no map exists yet.
- `docs/Navigation_Theory.md` and `docs/SLAM_Theory.md` are current and
  cross-referenced against the actual deployed config (MPPI, not DWB;
  AMCL's real role) as of the prior session.
- ROS 2 distro is confirmed **Jazzy** (Ubuntu 24.04), not the Foxy the
  reference tutorials were filmed on — use `ros-jazzy-*` package names.
- Front two encoders were swapped to GTK08 (186,264 CPR); rear keep the
  original RMCS-2086 (93,132 CPR) — firmware v3.0 carries this as a
  per-motor array. Lives in `odometry_publisher.py`/ESP32 firmware,
  untouched by anything above.

## Today's actual task: capture a correlated trajectory + raw-log record

`tools/trajectory_viz.py` now writes an `epoch_s` column (wall-clock,
`time.time()` — the same clock ROS 2's own console output uses) alongside
its CSV, added specifically for this. The plan is to run it side-by-side
with a captured `slam_toolbox` terminal log, so a jump visible in the plot
can be looked up directly in the log at the same wall-clock second.

**1. Confirm nothing Nav2-related is running** (shouldn't be, but check):
```bash
ps aux | grep -E "controller_server|planner_server|bt_navigator" | grep -v grep   # should print nothing
```

**2. If `mapping_full.launch.py` isn't already running this session, start it
capturing its own output to a timestamped log file:**
```bash
cd ~/ros2_ws && ros2 launch mecanum_robot mapping_full.launch.py 2>&1 | \
  tee ~/aislebot_logs/slam_$(date +%Y%m%d_%H%M%S).log
```
If it's already running from before, that's fine too — just note it wasn't
tee'd from the start, so this run's log will only cover the drive itself,
which is what actually matters here.

**3. In a second terminal, the trajectory recorder** — same "graph plotter"
setup as before (Fixed Frame = `zero_point` in Foxglove, plus a Grid
display), now with the epoch column:
```bash
python3 ~/ros2_ws/tools/trajectory_viz.py --no-reference --map-frame zero_point
```
It prints its start epoch on launch — note it, or just use the CSV's own
`epoch_s` column afterward.

**4. Drive a short, simple pattern** — doesn't need to be the full
wall-hugging loop yet, just enough to either reproduce the jumping or
confirm it doesn't happen again under the same conditions. Pure forward is
what triggered it last time; repeat that first.

**5. The moment a jump is visible in Foxglove** (or afterward, from the
CSV), note the `epoch_s` value at that row, then:
```bash
grep -A5 -B5 "<epoch or nearby wall-clock time>" ~/aislebot_logs/slam_*.log
```
Look specifically for loop-closure-related lines — candidate matches,
accept/reject decisions, correlation response scores. That's the evidence
that either confirms perceptual aliasing (a low-confidence match got
accepted) or points somewhere else entirely (e.g. a TF timing issue would
look different in the log).

**6. Report back** what the log shows at that timestamp — that decides the
next step: if it's confirmed as a bad loop closure, the fix is a partial
re-tightening of `loop_match_minimum_chain_size` and
`loop_match_minimum_response_coarse`/`_fine` (not a full revert — the
original §17.25 problem was real too), tuned to find a middle ground rather
than guessed.

## After the aliasing question is settled — the original mapping-drive plan

Once confirmed fixed (or confirmed not an issue after all), this is still
the next real milestone, unchanged from before:
- Wall-hug the walls, translate rather than rotate (§17.13, §17.20).
- Return to the physical zero mark, `ros2 run tf2_ros tf2_echo zero_point
  base_link` — near-zero passes, tens of centimetres means stop and
  diagnose rather than save.
- Ctrl-C the trajectory recorder for its summary + CSV — real numbers for
  the APS.
- If the loop-closure check passes, save the map (SLAM Toolbox's Save Map
  panel/service) before stopping `slam_toolbox` — that's what
  `navigation.launch.py` needs to run for the first time.

## Also worth doing, lower priority than the above

- **Hardware prerequisite for `navigation.launch.py`/`twist_mux`, whenever
  they're actually tried:**
  ```bash
  # on eduroam or wherever the Pi has internet, THEN switch to AisleBot-Pi AP
  sudo apt install ros-jazzy-twist-mux
  cd ~/ros2_ws/src/NarrowAisleBot && git pull origin claude/mapping-autonomous-nav-695glw
  ```
- **Foxglove + MCP — solved, no custom server needed.** Foxglove Desktop
  ships a built-in local MCP server (Settings → Personal → Agents & MCP →
  Local MCP server), documented at
  https://docs.foxglove.dev/docs/agents/mcp-server. Listens on
  `127.0.0.1:7333`, local-only; connect with `claude mcp add --transport
  http foxglove http://127.0.0.1:7333/mcp --header "Authorization: Bearer
  <token>"`. **Only works from a Claude Code session on the SAME machine as
  Foxglove Desktop** — a remote/cloud session (like the one that wrote this
  file) cannot reach `127.0.0.1` on the user's laptop.
- Full Phase 1 tape-measured manual-drive validation (straight/strafe/
  diagonal vs. physical tape, Nav2 off) — still open from the original plan.
