# Next Session Kickoff — one accepted map, then Nav

**Rewritten 29 Aug 2026 after §17.44, for the session of Monday 31 Aug.**
Paste §0 into a fresh session.

**Schedule reality.** Demo is **Sat 5 Sep**. Sunday 30 Aug is not a lab day,
so Monday is the commissioning-map day and there are five working days left.
`Autonomy_Endgame.md`'s Day 2 (CPU headroom, G3) is **deferred** — it is a
quality-of-life gain, and G4 is the critical path.

The order is unchanged and is not a preference: **SLAM must be trustworthy
before Nav means anything.** What changed on 29 Aug is *why* the maps have
been failing — the commissioning procedure itself was discarding its own
corner observations. That is fixed by driving differently, not by tuning.

---

## 0. THE PASTE BLOCK

> Copy everything between the rules into a new Claude Code session.

---

Continue NarrowAisleBot on branch `claude/narrowaislebot-mapping-reliability-038ike`.

**Read first, before doing anything:** `docs/Next_Session_Kickoff.md` (this
whole file), then `docs/Where_We_Stand.md` §2, §4 and §6, then
`docs/Research_Journal.md` §17.44. `docs/evidence/rotation_deadzone/README.md`
if anything about rotation or the circle tests comes up.

**Closed, do not reopen:** the §17.38 map-frame rotation fix. **Never fix an
axis, placement or trajectory-shape complaint in the dashboard** — §17.38 hid
for two weeks that way, and §17.44 caught the same reflex a third time when
the spiky trail looked like a rendering bug and was not.

**Passed, do not re-litigate:** G1 (deployment, verified on the live node) and
G2 (max correction 0.202 m, max heading step 4.57°).

**Retracted, do not re-derive:** "strafe is the weak axis"; `minimum_travel_heading`
as the rotation gate; `angle_variance_penalty` as a useful lever.

**Treat as hypotheses:** §17.28–§17.32's loop-closure conclusions, the
false-closure co-location, "speed matters", the degenerate-geometry
explanation, and the `shouldProcessScan()` distance-only mechanism.
Tell me which category any claim you make is in.

**The goal, in order:**
1. **SLAM** — produce **one accepted commissioning map**. There has never
   been one. Everything else is downstream of this.
2. **Nav** — save it, bring up AMCL, point-and-go on a *fixed* frame.

**How I want to work:**
- Robot is SSH'd and parked on the zero mark. Dashboard is up. Pi is on its
  own AP (`10.42.0.1`), no internet. **Every file: Windows downloads → `scp`
  to Pi.** Never `curl` on the Pi.
- **Copy-paste commands for everything.** One step at a time. Wait for me to
  report back. **Never assume a step succeeded.**
- **Verify config with `ros2 param get` against the live node, never by
  reading a file. Hash every transferred file on arrival, per file.**
- Every logger and every analysis on every drive — `graph_residuals.py
  --watch` live, then `run_bundle.py`, `map_integrity.py`,
  `wheel_forensics.py`, `run_analyzer.py`.
- **Short and crisp.** Command block, what to look for, one line of why.
  Prose goes in the journal.

**Monday's order, and do not skip S0 for the drive:**
1. **§2 health check.** Nothing is pending deployment — confirm what is
   running before anything else.
2. **§4 S0 — `scan_quality.py` at two positions.** 10 minutes, no driving.
   It has never met real data and it tests the one open hypothesis. The
   prediction is already written down; read the row we land on.
3. **§6 items 1 and 2** — the two `run_analyzer.py` guards, while the robot
   is idle. Re-run a 29 Aug baseline through both versions so the change is
   attributable.
4. **§4 S1 — the commissioning drive**, by the §3 rules.

**I owe you this before the drive plan is final:** usable floor dimensions
(length × width, tape-measured), a photographed hand sketch marking the zero
mark and the obstacles, and three photos — down the long axis from the mark,
the narrowest point, the widest open area. **My space is tight**, which is
why a wide-radius corner may not be available and the plan has to fit what
the room allows.

Do not deploy anything until I confirm what is actually running.

---

## 1. Session constants — memorise, do not re-derive

| | |
|---|---|
| **Pi login** | `ssh aritra@10.42.0.1` — password typed **interactively only** |
| ⚠ | **Never put the password on a command line.** It once got appended to an `scp` destination and created `mapping_full.launch.py<PASSWORD>` |
| **Pi on eduroam instead** | address changes daily — `ip -4 -br addr` on the Pi. `aritra-desktop.local` often fails to resolve from Windows |
| **Branch** | `claude/narrowaislebot-mapping-reliability-038ike` |
| **Raw base URL** | `https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike` |
| **Windows staging** | `C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download` |
| **Windows data drop** | `C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test` |
| **ROS workspace** | `~/ros2_ws` · deployed code in `~/ros2_ws/src/mecanum_robot/` |
| **Live SLAM config** | `~/ros2_ws/slam_nodom.yaml` ⚠ repo file is `slam_nodom_stageB.yaml` |
| **Tools** | `~/tools/` — **except** `run_bundle.py`, `map_integrity.py`, `run_analyzer.py`, `scan_quality.py`, which live in `~/aislebot_logs/` |
| **Run data + maps** | `~/aislebot_logs/run_<stamp>.{csv,pgm,yaml,_report.json}` |
| **Node log** | `~/aislebot_boot.log` (binary; `grep -a`) |
| **Dashboard** | `http://10.42.0.1:8080` — HTTP **and** WebSocket both on 8080 |
| ⚠ | **8765 is `foxglove_bridge`, not the dashboard.** Earlier versions of this file said otherwise |
| **ROS domain** | `42` |

**The transfer rule.** The Pi hosts its own AP and has **no uplink**. A `curl`
line in these docs is **never** a Pi command.

**Dashboard keys** (`phone_dashboard.py:975–999`): `W`/`A`/`S`/`D` translate,
`Q` = CCW, `E` = CW, `m` toggles MAP. Held keys accumulate in a `Set`, so
**`W`+`E` together is a forward arc** — that is how you turn while rolling.
A drag on the YAW slider overrides the keys and gives a gentler turn.

---

## 2. Health check — before touching anything

```bash
echo "=== NETWORK ==="; ip -4 -br addr | grep -v " lo "
echo "=== ROS ENV ==="; echo "DOMAIN=$ROS_DOMAIN_ID  RMW=$RMW_IMPLEMENTATION"
echo "=== NODES ==="; ros2 node list
echo "=== SLAM LIVE PARAMS ==="
ros2 param get /slam_toolbox coarse_search_angle_offset
ros2 param get /slam_toolbox correlation_search_space_dimension
ros2 param get /slam_toolbox minimum_travel_distance
ros2 param get /slam_toolbox minimum_travel_heading
ros2 param get /slam_toolbox angle_variance_penalty
echo "=== DEPLOYED HASHES ==="
sha256sum ~/ros2_ws/slam_nodom.yaml \
          ~/ros2_ws/src/mecanum_robot/mecanum_robot/phone_dashboard.py \
          ~/ros2_ws/src/mecanum_robot/urdf/aislebot.urdf 2>&1
echo "=== CPU / THERMAL ==="; uptime
awk '{printf "%.1f C\n", $1/1000}' /sys/class/thermal/thermal_zone0/temp
cat /sys/devices/platform/soc/soc:firmware/get_throttled
echo "=== SCAN RATE ==="; timeout 8 ros2 topic hz /scan_reliable --window 30
```

**Expected, as deployed 29 Aug:**

| Reading | Expect |
|---|---|
| `coarse_search_angle_offset` | **0.175** |
| `correlation_search_space_dimension` | 0.3 |
| `minimum_travel_distance` / `_heading` | 0.2 / 0.2 |
| `angle_variance_penalty` | 1.2 |
| `slam_nodom.yaml` | `0e88d60c34dfd9aada3f0fb5ab39523f45800bc8e4fba2385c6f9a3ba4ce3e5f` |
| `phone_dashboard.py` | `5b30a91dc7614d73848357bcedd66771cb332eddd12d1de06ed58dce47ad43d1` |
| `aislebot.urdf` | `ea6619ff3999b856fc3c1632041bd3a151eb8732f9c782d90207831ce1b0a81c` |
| `get_throttled` | `0` |
| `/scan_reliable` | ~11.4 Hz, std dev <0.01 s |

⚠ **Parameters can only be read while a MAP session is running.** No
`/slam_toolbox` in the node list means no session — start MAP, then re-read.

⚠ **Runtime `ros2 param set` does not survive.** Every value reverts from the
YAML when the next MAP starts a fresh node. Set *after* MAP, never before,
and always re-verify.

**Nothing is pending deployment.** The debt was cleared on 29 Aug.

---

## 3. HOW TO DRIVE — the rules that changed

**This section is the product of 29 Aug. Read it before the drive, not after.**

### 3.1 Never stop and spin

**Rotating in place adds no pose-graph node and no map cell.** Measured three
times (§17.44): a deliberate 714° turn over 642 s produced **43 occupied
cells = 2.1 m of wall** and zero corrections. It is not a threshold that can
be tuned — `minimum_travel_heading` was set to 0.05 and verified live, and a
full 360° still gave `n=1, e=0`.

Every stop-and-spin corner driven since §17.39 contributed **nothing**. That
is the best explanation available for maps returning 63–87% unknown.

### 3.2 Turn only while rolling

Hold `W` and feather the yaw. A 111 s `W`+`E` arc produced **18 nodes and
1545 cells = 77.2 m of wall** — 88% of the 621 s perimeter drive's coverage
in 18% of its time.

### 3.3 But do not turn *tightly*

`W`+`E` at full deflection gives a **0.54 m radius** circle, and that is a
degenerate geometry: from a 1 m disc in a 10 m room, 1° of heading error is
indistinguishable from 8.7 cm of translation, so the matcher cannot separate
them. Measured cost: **5.3 corrections/m and a 0.367 m maximum**, against the
perimeter drive's **1.0/m and 0.202 m**.

**Corners as wide as the floor allows.** Drag the YAW slider partway instead
of holding `E`, which overrides the key and gives a gentler radius.

### 3.4 Hug the walls, 0.5–1.5 m

Close walls are what makes the matcher well-conditioned. The circle failed
partly because it stared at far walls from a tiny disc.

### 3.5 MAP again to stop — it is the only thing that saves the map

A `systemctl restart`, a reboot, or forgetting entirely loses it. **This cost
a run on 29 Aug**: `run_20260829_163147` was analysed with `-- pgm -- yaml`
because the session was never stopped.

### 3.6 Change nothing

The deployed YAML is the configuration that passed G2. Carry no parameters
over from the circle work — they revert on the next MAP anyway.

---

## 4. PHASE 1 — the commissioning map → gate **G4**

### S0 · First: measure what the LiDAR gives the matcher — 10 min, no drive

`scan_quality.py` is the only instrument in this project that has **never met
real data**, and it measures exactly what the degenerate-geometry hypothesis
predicts: conditioning as `λ_min/λ_max` over surface normals, with the bearing
of the weak direction. **MAP must be running** — `/scan_reliable` only exists
while `mapping_full.launch.py` is up.

```bash
python3 ~/aislebot_logs/scan_quality.py --selftest
```

Parked on the zero mark, MAP on, room still:
```bash
python3 ~/aislebot_logs/scan_quality.py --seconds 30 --save ~/aislebot_logs/scan_mark.json
```

Moved to within ~0.7 m of a wall, parked:
```bash
python3 ~/aislebot_logs/scan_quality.py --seconds 30 --save ~/aislebot_logs/scan_wall.json
```

**Read `conditioning`** — `< 0.15` poor, `< 0.35` marginal — plus the weak
direction's bearing and the stationary stability.

**Prediction, pre-registered 29 Aug:** poor in the open middle, better near
the wall. If it holds, the degenerate-geometry hypothesis is measured rather
than reasoned, and it names which parts of the lab the robot can localise in
at all. Stability steady to a few mm means the sensor is fine and the fault
is the matcher's; ranges wandering centimetres mean the matcher is fed a
moving target and no tuning fixes it.

### S1 · The drive

1. **STOP MAP** if anything is running. Discard it.
2. Park on the mark. **Note which way the nose points** — ZERO fixes position,
   not orientation, and on 29 Aug two otherwise-identical runs came back with
   wall-orientation histograms 44° apart, most likely for that reason.
3. **ZERO** (two taps), then **MAP**, then **VIEW** and keep it open.
4. Perimeter, nose leading, **0.5–1.5 m off the walls**, SLOW (0.05 m/s),
   one direction, **corners as wide rounded turns taken while rolling**.
5. **10–15 minutes.** Longer beats shorter.
6. Close at the mark. **MAP again to stop.**

Live, in a second window:

```bash
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph_commission.jsonl
```

**Watch `n=`.** It must climb steadily. If it plateaus for more than ~15 s
while the robot is moving, something is being rejected — note the time and
what you were doing.

### S2 · The analysis, every drive

```bash
cd ~/aislebot_logs
TS=$(ls -1t run_*.csv | head -1 | sed 's/^run_//; s/\.csv$//'); echo "TS=$TS"
python3 ~/aislebot_logs/run_bundle.py --latest --folder ~/aislebot_logs
python3 ~/aislebot_logs/map_integrity.py run_$TS.pgm
python3 ~/aislebot_logs/run_analyzer.py run_$TS
python3 ~/tools/wheel_forensics.py run_$TS --csv ~/aislebot_logs/${TS}_wheels.csv
```

⚠ `map_integrity.py` takes **one** target, not pgm + yaml.
⚠ `wheel_forensics.py`'s `--csv` is an **output** path; the run is positional.

### S3 · Acceptance — G4

| Check | Pass |
|---|---|
| `map_integrity.py` verdict | **not `FOLDED`** |
| D2 doubled walls | **< 1.0%** (29 Aug best: 1.9%) |
| unknown | < 50% |
| physical return-to-mark, tape | **< 0.15 m** (29 Aug best: 0.257 m) |

**Budget three attempts.** A bad map poisons everything downstream.

Once accepted:

```bash
mkdir -p ~/maps
cp ~/aislebot_logs/run_<TS>.pgm  ~/maps/lab_commission_v1.pgm
cp ~/aislebot_logs/run_<TS>.yaml ~/maps/lab_commission_v1.yaml
sed -i 's|^image:.*|image: lab_commission_v1.pgm|' ~/maps/lab_commission_v1.yaml
cat ~/maps/lab_commission_v1.yaml && sha256sum ~/maps/lab_commission_v1.*
```

### If G4 still fails after three attempts

**Do not reach for another parameter.** Three sets left cumulative correction
at 2.80 / 2.85 / 2.86 m — invariant to within 2%. The next move is diagnosis,
in this order:

1. **Record a rosbag** of `/scan_reliable` + `/tf` + `/odom` on the next
   drive. Everything so far has been un-replayable, so every experiment has
   cost a physical drive. A bag makes offline A/B possible and is the single
   biggest speed-up available.
2. **Run `scan_quality.py` on real scans** — it has self-tests and has
   *never* met real data. If the matcher's *input* is degraded, no amount of
   matcher tuning helps.
3. **Read `shouldProcessScan()`** in the installed `slam_toolbox` and settle
   the distance-only hypothesis from source rather than inference.

---

## 5. PHASE 2 — Nav, unchanged and still never run

Gates and procedure as written in `Autonomy_Endgame.md` Part 3 (G5–G7). The
one hazard to check *before* the first launch:

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
ros2 node list | grep slam_toolbox     # MUST be empty before AMCL starts
```

---

## 6. Scheduled work that needs no robot

| # | Item | Why |
|---|---|---|
| 1 | **`run_analyzer.py` — turn-rate guard on the wheel-spread alarm** | Fires on every arc. At radius 0.54 m the ICR sits on the inner wheels (`K_o` = 0.56069 m), so 37–56:1 is correct. Suppress or rescale when integrated yaw is large relative to path |
| 2 | **`run_analyzer.py` — geometry guard on the co-location cross-check** | "Two independent witnesses" counted one wall seven times. Require *distinct* clusters, and suppress entirely when the trajectory's own extent is smaller than the coincidence radius |
| 3 | **`map_integrity.py --corpus`** over the ~70-map archive | Replaces guessed thresholds with percentiles. Still never run |
| 4 | **Turn off `foxglove_bridge`** (`use_foxglove:=false` in `~/start_aislebot.sh`) | Nothing in the dashboard path uses it; it predates the dashboard's map view. Free CPU toward G3 |
| 5 | **Journal revision table** has no rows for 27–28 Aug (§17.38–§17.43) | Pre-existing gap, noticed 29 Aug, deliberately not back-filled by guesswork |

**Do #1 and #2 before the next drive** — an instrument that cries wolf on
every arc will cost a real diagnosis eventually. Do them as a separate
commit with the baseline runs re-analysed before and after, so the change is
attributable.

---

## 7. Capture list — what to photograph and record

29 Aug produced good video and lost several stills, because dashboard
screenshots were pasted into chat rather than saved. **Save everything to the
Windows staging folder with the run stamp in the filename.**

**Per drive, minimum:**

| # | What | When | Why |
|---|---|---|---|
| 1 | Dashboard full screen, `X`/`Y`/`NOSE` legible | **freshly zeroed, before MAP** | the run's zero reference |
| 2 | Photo of the robot on the floor mark, showing **which way the nose points** | before MAP | §17.44's 44° histogram flip is probably this, and it is unrecoverable afterwards |
| 3 | Screen recording, dashboard + `graph_residuals.py` in one frame | **the whole drive** | the only way to align `n=` against what the robot was doing |
| 4 | Dashboard full screen | immediately after **MAP-to-stop**, before moving | SLAM's terminal claim |
| 5 | Photo of the robot where it actually stopped, next to the mark | before moving it | ground truth |
| 6 | **Tape measure**, two numbers, your convention (cm, +Y forward, +X right) | before moving it | the referee. State the axes explicitly — 29 Aug had one "0,−3, so just x drift" that reads as a Y offset |
| 7 | Dashboard full screen | after manually returning to the mark | SLAM's error at a known truth |

**For the accepted map, additionally:** tape-measure the robot's distance to
**two** walls, and photograph both. Thirty seconds, and it cannot be
recovered afterwards.

**Pull to Windows after every drive:**

```powershell
scp aritra@10.42.0.1:~/aislebot_logs/run_<TS>.* "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
scp aritra@10.42.0.1:~/aislebot_logs/*_bundle.json "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test"
```

Then open the bundle in `docs/tools/run_viewer.html` and the map in
`docs/tools/map_viewer.html` (**not** `telemetry_analyzer.html` — its map
dropzone only unlocks after a valid 13-column run CSV).

---

## 8. Decisions taken and closed — do not re-open casually

| Decision | When | Why |
|---|---|---|
| **No camera** — USB webcam(s) under the LiDAR | 29 Aug | `slam_toolbox` is 2D laser SLAM with **no camera input**; frames reach nothing. Using vision means replacing it, days before the demo, for a fault already diagnosed. Also: control loop already 7.5–13.7 Hz vs 20 requested; two UVC devices on one Pi bus commonly fail to negotiate; matching a 360°−90° field needs four cameras. Revisit only as a post-demo direction, or as a POV camera for report footage |
| **No IMU** | 22 Aug | No magnetometer means no absolute heading, which is the entire point; `ekf_params.yaml` fuses IMU yaw as truth, so a drifting signal would actively hurt. BNO055 remains the right part if ever prioritised |
| **Do not change the yaw estimator** | 28 Aug | Both forms unbiased; equal weighting costs 0.89% yaw-rate noise, which cannot produce 10.53° over 18 m. Good theory, bad engineering priority |
| **Do not smooth the trail display** | 29 Aug | The spikes are the per-node disagreement made visible. See rule 5 |

The pattern in all four: **do not add a component, or hide a signal, that does
not address the measured fault.**

---

## 9. Standing rules

1. **One parameter at a time.** §17.25 changed six and paid for three sessions.
2. **Write the prediction down before the test.**
3. **Verify against the live node, never the file.** And a runtime `param set`
   dies at the next MAP.
4. **Hash every file on arrival, per file.**
5. **Never fix an axis, placement or trajectory-shape complaint in the
   dashboard.** The display being ugly is usually the display being honest.
6. **STOP MAP is the only thing that saves a map.**
7. **Never stop and spin.** Turn only while rolling, and never tightly.
8. **Label every claim** — measured / measured-once / hypothesis / retracted /
   never-run.
9. **Do not change an instrument mid-campaign** without re-running the
   baseline through both versions.
10. **Do not derive map coverage from a screenshot.** Dark pixels include
    trail lines and UI chrome; the saved `.pgm` is the only truth.

---

## 10. Where the reasoning lives

| Question | Document |
|---|---|
| Why is the map worse than the odometry? | `Where_We_Stand.md` §3 |
| Why does rotating in place do nothing? | `Research_Journal.md` §17.44, `docs/evidence/rotation_deadzone/` |
| Why does the goal not land where I clicked? | `Autonomy_Endgame.md` §1.2 |
| What is still only a hypothesis? | `Where_We_Stand.md` §4 |
| The day-by-day plan and fallbacks | `Autonomy_Endgame.md` Parts 4–5 |
| Session-by-session record | `Research_Journal.md` §17.38–§17.44 |
