# Next Session Kickoff — paste this to start

This is the self-contained prompt for the next Claude Code session. It assumes
no memory of this conversation — everything it needs is either in this file
or in the repo itself (`docs/Research_Journal.md`, `docs/Navigation_Theory.md`,
`docs/SLAM_Theory.md`).

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/mapping-autonomous-nav-695glw`. Read `docs/Research_Journal.md`
> §17.25–§17.26 and `docs/Next_Session_Kickoff.md` in full before doing
> anything else — don't re-derive what's already documented there.
>
> Today's goal: run the manual mapping drive that's been planned but not yet
> executed. SLAM only, Nav2 completely off. Fixed origin (`zero_point`),
> wall-hugging manual drive, return to the physical mark, and read the
> loop-closure number. Walk me through it step by step on hardware — I'll
> report back what each command prints and you decide what's next from
> there. Don't assume a step succeeded; ask me to paste the output.

---

## What's true right now (don't re-derive this)

- `twist_mux` (manual-override arbitration) and a rewritten
  `navigation.launch.py` (map_server + amcl) were built and pushed
  (`bd4fb1a`, `129150d`) but **have zero hardware confirmation**. Neither
  has been deployed to the Pi.
- `system/slam_nodom.yaml`'s loop-closure/scan-matcher tuning (`635e4b6`)
  **is now hardware-confirmed** (§17.27): a controlled rotate-90°/drive-out/
  drive-back/rotate-back test on the physical mark read back ≈2 cm / 0.17°,
  down from ≈50 cm pre-tuning. `twist_mux` is still untested.
- No map has ever been saved. `navigation.launch.py` cannot be usefully run
  until one exists. The full wall-hugging drive below is still worth doing
  before saving — §17.27's test was short and controlled, a good sanity
  check but not the richer loop-closure exercise a real map needs.
- `docs/Navigation_Theory.md` and `docs/SLAM_Theory.md` are current and
  cross-referenced against the actual deployed config (MPPI, not DWB;
  AMCL's real role) as of this session.
- ROS 2 distro is confirmed **Jazzy** (Ubuntu 24.04), not the Foxy the
  reference tutorials were filmed on — use `ros-jazzy-*` package names, not
  the tutorials' `ros-foxy-*`.
- Front two encoders were swapped to GTK08 (186,264 CPR); rear keep the
  original RMCS-2086 (93,132 CPR) — firmware v3.0 carries this as a
  per-motor array. This lives in `odometry_publisher.py`/ESP32 firmware,
  untouched by anything above. Worth knowing before trusting `/odom` blindly.

## Hardware prerequisite — deploy today's code first

```bash
# on eduroam or wherever the Pi has internet, THEN switch to AisleBot-Pi AP
sudo apt install ros-jazzy-twist-mux

# pull the branch onto the Pi (adjust to however this repo is normally synced there)
cd ~/ros2_ws/src/NarrowAisleBot && git pull origin claude/mapping-autonomous-nav-695glw

# redeploy the tuned SLAM config if it isn't already on this exact hash
curl -sSL -o ~/ros2_ws/slam_nodom.yaml \
  https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/mapping-autonomous-nav-695glw/system/slam_nodom.yaml
sha256sum ~/ros2_ws/slam_nodom.yaml
# expected: 68437ea90fb028fd124010680a8d501561650c93cb1b55a5397a2c1b644678e0
```

## The mapping drive itself

**1. Confirm nothing Nav2-related is running:**
```bash
pkill -f 'controller_server|planner_server|bt_navigator|behavior_server|collision_monitor|velocity_smoother|waypoint_follower|smoother_server|lifecycle_manager'
sleep 2
ps aux | grep -E "controller_server|planner_server|bt_navigator" | grep -v grep   # should print nothing
```

**2. Park on the physical zero mark, then re-zero and start mapping:**
```bash
sudo systemctl restart aislebot.service
cd ~/ros2_ws && ros2 launch mecanum_robot mapping_full.launch.py
```

**3. In a second terminal, start the trajectory recorder** — this is the
"graph plotter" piece: it samples `zero_point → base_link` continuously and
publishes a growing `/actual_path`, so the drive is visible as a line on a
fixed set of axes rather than something you have to infer from a moving dot.
```bash
python3 ~/ros2_ws/tools/trajectory_viz.py --no-reference --map-frame zero_point
```
Leave it running for the entire drive; Ctrl-C only at the very end.

**4. In Foxglove:**
- 3D panel → **Fixed Frame = `zero_point`**, not `map` and not `odom`. This
  is what makes the origin stop appearing to jump — `zero_point` is a static
  child of `map`, so the *view* stays anchored even while `map→odom` is
  being corrected underneath it.
- Add a **Grid** display (default XY plane through the origin). With Fixed
  Frame = `zero_point`, that grid *is* the fixed x/y axes.
- Enable `/map`, `/actual_path`, `/trajectory_markers`.

**5. Drive manually from the dashboard.** Two things that matter for map
quality, both already paid for in hardware sessions — don't re-learn them:
- **Hug the walls**, out close to one side, back close to the other.
  Centreline driving produced thin, ill-defined map edges (§17.13).
- **Translate, don't spin.** Pure rotation gives the scan matcher almost
  nothing to work with (§17.20).

**6. Drive back onto the physical zero mark**, then read the number that
actually matters:
```bash
ros2 run tf2_ros tf2_echo zero_point base_link
```
Near-zero (a few cm) → loop closure is working, proceed to save the map.
Off by tens of centimetres → the §17.25 tuning wasn't enough; don't save,
come back and diagnose before trying again.

**7. Ctrl-C the trajectory recorder** — it prints a path-length/efficiency
summary and writes a CSV to `~/aislebot_logs/`, real numbers for the APS.

**8. If the loop-closure check passed, save the map** (SLAM Toolbox's Save
Map panel in Foxglove, or the CLI equivalent) before stopping `slam_toolbox`.
That saved map is what `navigation.launch.py` needs to run for the first
time.

## Also worth doing this session, lower priority than the drive above

- **Foxglove + MCP — solved, no custom server needed.** Foxglove Desktop
  ships a built-in local MCP server (Settings → Personal → Agents & MCP →
  Local MCP server), documented at
  https://docs.foxglove.dev/docs/agents/mcp-server. It listens on
  `127.0.0.1:7333`, local-only, gated behind a developer seat + Pro/
  Enterprise/Academic plan and a generated access token; connect with
  `claude mcp add --transport http foxglove http://127.0.0.1:7333/mcp
  --header "Authorization: Bearer <token>"`.
  **This only works from a Claude Code session running on the SAME machine
  as Foxglove Desktop.** A remote/cloud Claude Code session (like the one
  that wrote this file) cannot reach `127.0.0.1` on the user's laptop —
  that loopback address means something different inside the cloud
  container. If robot-diagnosis-via-Foxglove-MCP is wanted, it has to
  happen in a **local** Claude Code CLI session on the machine actually
  running Foxglove Desktop, not here. Worth confirming which kind of
  session is picking this file up before assuming the MCP tools are
  available.
- Full Phase 1 tape-measured manual-drive validation (straight/strafe/
  diagonal vs. physical tape, Nav2 off) — still open from the original plan,
  and this session's mapping drive doubles as a good moment to also collect
  those numbers if time allows.
