# Next Session Kickoff — SLAM first, then Nav

**Rewritten 29 Aug 2026.** Paste §0 into a fresh session. Everything the
assistant needs is in this file or in the four documents it points at.

The order is fixed and is not a preference: **SLAM must be trustworthy before
Nav means anything.** A goal sent into a map frame that is still moving lands
somewhere the operator did not click — that is measured, not theorised
(§17.43).

---

## 0. THE PASTE BLOCK

> Copy everything between the rules into a new Claude Code session.

---

Continue NarrowAisleBot on branch `claude/narrowaislebot-mapping-reliability-038ike`.

**Read first, before doing anything:** `docs/Next_Session_Kickoff.md`
(this whole file), then `docs/Where_We_Stand.md` §2 and §6, then
`docs/Autonomy_Endgame.md` Parts 3–4. `docs/Axis_Convention.md` if anything
axis-related comes up.

**Closed, do not reopen:** the §17.38 map-frame rotation fix. **Never fix an
axis or goal-placement complaint in the dashboard** — that is what hid it for
two weeks, and §17.43 caught the same reflex a second time.

**Treat as hypotheses, not facts:** §17.28–§17.32's loop-closure conclusions
(drawn on a rotated map frame), the false-closure co-location (n=3), and
"speed matters". "Strafe is the weak axis" is **retracted** — do not
re-derive it. Tell me which category any claim you make is in.

**The goal, in order:**
1. **SLAM** — close the angular gate, then produce **one accepted
   commissioning map**. There has never been one.
2. **Nav** — save that map, bring up AMCL, then point-and-go on a *fixed*
   frame.

**How I want to work:**
- Robot is SSH'd and parked on the zero mark. Dashboard is up. Pi is on its
  own AP (`10.42.0.1`), no internet. My Windows PC has LAN internet — so
  **every file: Windows downloads → `scp` to Pi**. Never `curl` on the Pi.
- **Give me copy-paste commands for everything.** One step at a time. Wait
  for me to report back. **Never assume a step succeeded.**
- **Verify deployed config with `ros2 param get` against the live node, never
  by reading a file. Hash every transferred file on arrival, per file.**
- I will eyeball, and I want every logger and every analysis run on every
  drive — `graph_residuals.py --watch` live, then `run_bundle.py`,
  `map_integrity.py`, `wheel_forensics.py`, `run_analyzer.py` after.
- **Keep your messages short and crisp.** Command block, what to look for,
  one line of why. Save the prose for the journal.

Start with the §1 health check. Do not deploy anything until I confirm what
is actually running.

---

## 1. Session constants — memorise these, do not re-derive them

| | |
|---|---|
| **Pi login** | `ssh aritra@10.42.0.1` — password typed **interactively only** |
| ⚠ | **Never put the password on a command line.** It once got appended to an `scp` destination and created a file named `mapping_full.launch.py<PASSWORD>` |
| **Pi on eduroam instead** | address changes daily — `ip -4 -br addr` on the Pi, then use the IP. `aritra-desktop.local` often fails to resolve from Windows |
| **Branch** | `claude/narrowaislebot-mapping-reliability-038ike` |
| **Raw base URL** | `https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike` |
| **Windows staging** | `C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download` |
| **Windows data drop** | `C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test` |
| **ROS workspace** | `~/ros2_ws` · deployed code in `~/ros2_ws/src/mecanum_robot/` |
| **Live SLAM config** | `~/ros2_ws/slam_nodom.yaml` ⚠ repo file is named `slam_nodom_stageB.yaml` |
| **Tools** | `~/tools/` — but `run_bundle.py` has been living in `~/aislebot_logs/`. Check both |
| **Run data + maps** | `~/aislebot_logs/run_<stamp>.{csv,pgm,yaml,_report.json}` |
| **Node log** | `~/aislebot_boot.log` (not `journalctl` — that only shows systemd start/stop) |
| **Dashboard** | `http://10.42.0.1:8080` · WebSocket `ws://10.42.0.1:8765` |
| **ROS domain** | `42` |

**The transfer rule.** The Pi hosts its own AP and has **no uplink**. Windows
has LAN internet. So every file moves in two hops: `curl.exe` on Windows →
`scp` to the Pi. A `curl` line in these docs is **never** a Pi command.

---

## 2. Health check — run before touching anything

**On the Pi.** Paste as one block.

```bash
echo "=== NETWORK ==="; ip -4 -br addr | grep -v " lo "
echo "=== ROS ENV ==="; echo "DOMAIN=$ROS_DOMAIN_ID  RMW=$RMW_IMPLEMENTATION"
echo "=== NODES ==="; ros2 node list
echo "=== SLAM LIVE PARAMS ==="
ros2 param get /slam_toolbox correlation_search_space_dimension
ros2 param get /slam_toolbox coarse_search_angle_offset
ros2 param get /slam_toolbox distance_variance_penalty
ros2 param get /slam_toolbox angle_variance_penalty
echo "=== DEPLOYED HASHES ==="
sha256sum ~/ros2_ws/slam_nodom.yaml \
          ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py \
          ~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf 2>&1
ls -la ~/tools/ ~/aislebot_logs/*.py 2>&1 | head -30
echo "=== CPU / THERMAL ==="; uptime; vcgencmd measure_temp; vcgencmd get_throttled
echo "=== FRAMES ==="; timeout 3 ros2 run tf2_ros tf2_echo odom base_link 2>&1 | tail -12
```

**Expected, as of the last session:**

| Reading | Expected now | After §3 deploy |
|---|---|---|
| `correlation_search_space_dimension` | `0.3` | `0.3` |
| `coarse_search_angle_offset` | `0.349` (stock) | **`0.175`** |
| `slam_nodom.yaml` sha256 | `e90aee53…` (Stage C) | **`0e88d60c…`** |
| `phone_dashboard.py` sha256 | old — **not** `5b30a91d…` | `5b30a91d…` |
| `get_throttled` | `0x0` | `0x0` |

⚠ **If a node list is missing `/slam_toolbox`, no mapping session is running** —
that is fine, and parameters cannot be read until one is. Start MAP first,
then re-read.

---

## 3. Deploy — the five steps, no step skipped

### 3.1 Windows downloads

```powershell
cd "C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download"
$B = "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike"

curl.exe -sSL --retry 3 --retry-all-errors -o slam_nodom.yaml     "$B/system/slam_nodom_stageB.yaml"
curl.exe -sSL --retry 3 --retry-all-errors -o phone_dashboard.py  "$B/src/mecanum_robot/mecanum_robot/phone_dashboard.py"
curl.exe -sSL --retry 3 --retry-all-errors -o wheel_forensics.py  "$B/tools/wheel_forensics.py"
curl.exe -sSL --retry 3 --retry-all-errors -o aislebot.urdf       "$B/src/mecanum_robot/urdf/aislebot.urdf"
```

### 3.2 Windows pushes — type the whole destination including the filename

```powershell
scp slam_nodom.yaml    aritra@10.42.0.1:~/ros2_ws/slam_nodom.yaml
scp phone_dashboard.py aritra@10.42.0.1:~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
scp wheel_forensics.py aritra@10.42.0.1:~/tools/wheel_forensics.py
scp aislebot.urdf      aritra@10.42.0.1:~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf
```

⚠ **The config lands as `slam_nodom.yaml`, not `slam_nodom_stageB.yaml`.**
`mapping_full.launch.py:66` loads the former. Wrong name = old file keeps
running, silently, and every measurement after that is worthless.

### 3.3 Pi hashes — per file, never per batch

```bash
sha256sum ~/ros2_ws/slam_nodom.yaml
# 0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f
sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py
# 5b30a91dc7614d73848357bcedd66771cb332eddd12d1de06ed58dce47ad43d1
sha256sum ~/tools/wheel_forensics.py
# 27858ce417f3f39e56db3b87b31644fc11a9292aba7247f1c8d9a2d80bf96236
sha256sum ~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf
# ea6619ff3999b856fc3c1632041bd3a151eb8732f9c782d90207831ce1b0a81c

ls -la ~/tools/ ~/ros2_ws/*.yaml     # nothing with a password stuck on the end
```

### 3.4 Pi rebuilds — only for files under `~/ros2_ws/src`

```bash
cd ~/ros2_ws && colcon build --packages-select mecanum_robot --symlink-install
sudo systemctl restart aislebot.service
python3 ~/tools/wheel_forensics.py --selftest      # 6 tests, all PASS
```

### 3.5 Pi verifies against the LIVE NODE

**slam_toolbox reloads parameters only on a fresh bring-up.**
**STOP MAP → park on the mark → ZERO (two taps) → MAP.** Then:

```bash
ros2 param get /slam_toolbox coarse_search_angle_offset            # 0.175
ros2 param get /slam_toolbox correlation_search_space_dimension    # 0.3
```

**If either reads stock, stop.** The file did not take, and nothing measured
after that point means anything.

---

## 4. PHASE 1 — SLAM

### S1 · Stage D A/B  →  gate **G2**

**The one change:** `coarse_search_angle_offset` stock `0.349` (20°) →
**`0.175`** (10°). Already committed. Nothing else changed — verified by
parsing both YAMLs: 35 params before, 36 after, one difference.

**The drive:** repeat the 28 Aug traverse *exactly* — perimeter of the
junction, **nose leading, rotating at every corner**, 0.5–1.5 m off the
walls, SLOW (0.05 m/s), one direction, closing at the mark. 15–18 min.

**Instrument it live, in a second SSH window:**

```bash
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph_stageD.jsonl
```

**Prediction table — read the row you land on, do not improvise:**

| Outcome | Reading | Next |
|---|---|---|
| max correction **< 0.30 m**, max heading step **< 10°** | The angular gate was the lever. **G2 passes** | → S2 |
| corrections pinned near **0.30 m**, heading near **10°** | Window clamped the symptom; matcher still *prefers* to disagree | Stage E: `angle_variance_penalty` 1.2 → 0.6 |
| **track lost at a corner** — pose freezes, map tears at a rotation | Cut below the prior's real uncertainty | → `0.25` (14.3°), **not** back to 0.349 |
| no change | Angular window is not the gate | Stage E, and re-open `distance_variance_penalty` |

**Then, robot physically back on the zero mark, read all three:**

```bash
ros2 run tf2_ros tf2_echo map base_link      # SLAM's opinion
ros2 run tf2_ros tf2_echo odom base_link     # odometry's opinion
ros2 run tf2_ros tf2_echo map odom           # the correction between them
```

28 Aug baseline: **0.477 m / 0.229 m / 0.271 m**. Under **0.15 m** on the
first is a pass.

### S2 · CPU headroom  →  gate **G3**

Control loop is 7.5–13.7 Hz against 20 requested; planner 1.25 against 5.
Measure, then one change at a time, re-measuring after each.

```bash
top -b -n 1 -o %CPU | head -20
uptime && vcgencmd measure_temp && vcgencmd get_throttled
```

| Order | Change | Where |
|---|---|---|
| 1 | MPPI `batch_size` 1000 → 400 | `ros2 param set /controller_server FollowPath.batch_size 400` |
| 2 | `map_update_interval` 1.0 → 2.0 | `slam_nodom.yaml` |
| 3 | global costmap `update_frequency` → 1.0, `publish_frequency` → 0.5 | `nav2_params.yaml` |

**Pass:** control ≥ 15 Hz sustained, zero TF-extrapolation errors over 5 min.

> `Parameter goal_checker.xy_goal_tolerance not found` from
> `controller_server` is **MPPI's ParametersHandler being noisy, not a
> failure**. The values do take. Do not chase it.

### S3 · The commissioning map  →  gate **G4**   ← the day it turns

1. **STOP MAP** if anything is running. Discard it.
2. Park on the mark. **ZERO** (two taps — must precede MAP).
3. **MAP**, then **VIEW**, and keep VIEW open the whole run. A fold is
   visible as it happens.
4. Perimeter, **nose leading, rotating at every corner**.
5. **MAP again to stop — this is the only thing that saves the map.** A
   `systemctl restart`, a reboot or a crash loses it entirely.

**Why rotation and not a square:** the rear 90° is permanently blind behind
the mast (107 of 430 beams masked NaN). A non-rotating square keeps that cone
pointed at the same *world* direction all run — which is why an earlier map
came back **87% unknown**.

```bash
python3 ~/tools/map_integrity.py ~/aislebot_logs/run_<TS>.pgm ~/aislebot_logs/run_<TS>.yaml
```

**Accept only if** verdict ≠ `FOLDED` · **D2 doubled walls < 1.0%** ·
unknown < 50% · physical return-to-mark **< 0.15 m**.
28 Aug failed on D2 at **5.0% across 5 clusters**.

**Budget three attempts.** A bad map poisons everything downstream.

**Once accepted, promote it out of the run folder:**

```bash
mkdir -p ~/maps
cp ~/aislebot_logs/run_<TS>.pgm  ~/maps/lab_commission_v1.pgm
cp ~/aislebot_logs/run_<TS>.yaml ~/maps/lab_commission_v1.yaml
sed -i 's|^image:.*|image: lab_commission_v1.pgm|' ~/maps/lab_commission_v1.yaml
cat ~/maps/lab_commission_v1.yaml && sha256sum ~/maps/lab_commission_v1.*
```

**Photograph the robot on the zero mark and tape-measure it to two walls.**
Thirty seconds, and it cannot be recovered afterwards.

---

## 5. PHASE 2 — Nav

### N1 · AMCL's first breath  →  gate **G5**

**This code has never executed once.** Check the known hazard *before*
launching:

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
```

If the plugin XML names `nav2_amcl::OmniMotionModel`, then
`nav2_params.yaml`'s `robot_model_type: "omnidirectional"` is the
pre-Galactic bare-string form and **will abort the whole `lifecycle_manager`
bringup** — the same all-or-nothing failure §17.17 hit. Fix it first.

```bash
ros2 launch mecanum_navigation navigation.launch.py \
    map:=/home/aritra/maps/lab_commission_v1.yaml 2>&1 | tee ~/aislebot_logs/amcl_first.log
```

Wait for `Managed nodes are active`. Park on the mark, set the initial pose,
drive **manually** for two minutes while watching:

```bash
ros2 topic hz /amcl_pose
ros2 topic echo /amcl_pose --once
ros2 run tf2_ros tf2_echo map base_link
```

**Pass:** covariance diagonal **shrinks** as walls come into view, and
`map→base_link` stays smooth — no 0.3 m jumps. AMCL corrections should be
centimetres, because it corrects the robot inside a fixed map rather than
rebuilding the map.

### N2 · Point-and-go  →  gate **G6**

First raise the tolerance that cannot be met — 2 cm is smaller than the pose
jitter of the estimate itself:

```bash
ros2 param set /controller_server goal_checker.xy_goal_tolerance 0.12
ros2 param set /controller_server goal_checker.yaw_goal_tolerance 0.20
ros2 param get /controller_server goal_checker.xy_goal_tolerance
```

Five goals, **tap don't drag** (dragging sets an orientation and costs ~50 s
of nose-turning before it may declare success). Tape-mark the tapped point on
the floor *before* sending, then tape-measure where it stops.

| # | Tapped | Reached | Err (m) | Yaw err | Time | Result |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

**Pass: 5/5 succeeded, all within 0.15 m.** That table is a report figure
exactly as it stands.

### N3 · Named locations  →  gate **G7**

`~/locations.json` keyed to the map name; `POST /save_location {name}` reads
the live `map→base_link` and appends a row; `POST /goto_location {name}`
republishes it as a goal. Design in `Production_Architecture.md` §3.3.

**Pass: teach 3, full power cycle, recall all 3 within 0.15 m.** The power
cycle is the whole test.

---

## 6. Instrumentation — run all of it on every drive

**Live, during:**
```bash
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph_<label>.jsonl
```

**After, on the Pi:**
```bash
python3 ~/aislebot_logs/run_bundle.py --latest --folder ~/aislebot_logs    # refuses runs < 60 s
python3 ~/tools/map_integrity.py ~/aislebot_logs/run_<TS>.pgm ~/aislebot_logs/run_<TS>.yaml
python3 ~/tools/wheel_forensics.py --csv ~/aislebot_logs/<label>_wheels.csv
python3 ~/tools/run_analyzer.py ~/aislebot_logs/run_<TS>.csv
```

**Pull to Windows:**
```powershell
scp aritra@10.42.0.1:~/aislebot_logs/run_<TS>.* "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
scp aritra@10.42.0.1:~/aislebot_logs/*_bundle.json "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

Open the bundle in `docs/tools/run_viewer.html`, the map in
`docs/tools/map_viewer.html` (**not** `telemetry_analyzer.html` — its map
dropzone only unlocks after a valid 13-column run CSV).

---

## 7. Standing rules

1. **One parameter at a time.** §17.25 changed six at once and paid for three
   sessions.
2. **Write the prediction down before the test.** A prediction that can fail
   beats an explanation that cannot.
3. **Verify against the live node, never the file.**
4. **Hash every file on arrival, per file.** Two of three landing correctly
   is exactly why per-batch fails.
5. **Never fix an axis or goal-placement complaint in the dashboard.**
6. **STOP MAP is the only thing that saves a map.**
7. **Label every claim** — measured / measured-once / hypothesis / retracted /
   never-run.

---

## 8. Where the reasoning lives

| Question | Document |
|---|---|
| Why is the map worse than the odometry? | `Where_We_Stand.md` §3 |
| Why does the goal not land where I clicked? | `Autonomy_Endgame.md` §1.2 |
| What do these parameters actually do? | `APS_Study_Guide.md` §5 |
| What is still only a hypothesis? | `Where_We_Stand.md` §4 |
| The full day-by-day with fallbacks | `Autonomy_Endgame.md` Parts 4–5 |
| Session-by-session record | `Research_Journal.md` §17.38–§17.43 |
