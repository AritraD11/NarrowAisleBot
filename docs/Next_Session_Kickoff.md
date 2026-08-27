# Next Session Kickoff — paste this to start

Self-contained prompt for the next Claude Code session. It assumes no memory
of the previous conversation — everything needed is here or in the repo
(`docs/Axis_Convention.md`, `docs/Research_Journal.md`,
`docs/Dashboard_Map_System.md`, `docs/Important_Commands.md`,
`docs/MATLAB_Navigation_Reference.md`, `tools/README.md`).

**Rewritten 27 Aug 2026 (evening), §17.40.** The morning version of this file
was organised around loop-closure reliability. That framing is now known to
be aimed at the wrong half of `slam_toolbox`, and this file is reorganised
around what the jumps actually are: **the front-end scan matcher**.

---

## ⏸ RESUME HERE — one deploy, one drive, one comparison

**A parameter change is committed and NOT yet on the robot.** Everything
below is downstream of getting it there and re-running one 90-second drive.

### What changed yesterday, in one paragraph

The pose-graph jumps are not loop closures. On a 153-second `W`/`S`/`D`/`A`
drive, `graph_residuals.py` reported `moved=0, max_shift=0.000` for the
entire run — **not one pose-graph node was ever moved by the optimiser** —
while the dashboard HUD threw three corrections of **0.336 / 0.302 /
0.240 m** with `NOSE` stepping to −13.4°, on a drive where `Q` and `E` were
never pressed. A back-end re-solve moves nodes. Nothing moved. The
corrections come from the front end, and their size is set by
`correlation_search_space_dimension`, which was live-verified at `0.7` —
±0.35 m of freedom to place each scan away from a prior that is good to
about 4 mm over the same interval. Full reasoning in §17.40.

### Step 1 — deploy Stage C and verify it on the node

Committed as `2a3e83b`: `correlation_search_space_dimension` **0.7 → 0.3**,
in `system/slam_nodom_stageB.yaml`. Exactly one value changed, verified by
parsing both YAMLs rather than reading the diff.

```powershell
curl.exe -sSL --retry 3 --retry-all-errors -o slam_nodom.yaml "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/narrowaislebot-mapping-reliability-038ike/system/slam_nodom_stageB.yaml"
scp slam_nodom.yaml aritra@10.42.0.1:~/ros2_ws/slam_nodom.yaml
```

⚠ **Note the destination filename.** The repo file is
`slam_nodom_stageB.yaml`; `mapping_full.launch.py:66` loads
`~/ros2_ws/slam_nodom.yaml`. Land it under the wrong name and the old
file keeps running, silently.

```bash
sha256sum ~/ros2_ws/slam_nodom.yaml
# must be e90aee539b0c7f245f2386ba9e9c80ab08a5ee475c02a0600fb74a98158a5d71
```

Then **STOP MAP → park on the mark → ZERO (two taps) → MAP**; parameters
only reload on a fresh bring-up. Then, against the live node, never the
file:

```bash
ros2 param get /slam_toolbox correlation_search_space_dimension    # 0.3
```

If it still says `0.7`, stop — the file did not take.

### Step 2 — the A/B, and it is a repeat, not a new experiment

Re-run **the identical drive**: `W` 1 m, `S` back, `D` 1 m, `A` back, at
**SLOW (0.05 m/s)**, no `Q`, no `E`, with

```bash
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph_stageC.jsonl
```

and the dashboard HUD visible. The baseline it is being compared against,
measured 27 Aug at the same speed:

| | `W`/`S` leg | `D`/`A` leg |
|---|---|---|
| HUD tracked to | 0.988 m of 1 m, back to 0.017 | jumps at X 0.357, 0.312, −0.313 |
| Corrections | ≤ 6 cm | **0.336 / 0.302 / 0.240 m** |
| `NOSE` | 0.0° → −0.6° | −0.8° → **−13.4°** |
| Graph node spacing | 0.37, 0.36, 0.36, 0.36 m | **0.02, 0.00, 0.03 m** |
| Chain accumulated | 1.45 m | **0.05 m** |
| Pose graph | `moved=0` | `moved=0` |

**The prediction, written before the test so it can fail:**

| Outcome | Reading |
|---|---|
| `D`/`A` corrections **< 0.15 m**, lateral node spacing stops collapsing | The window was the lever. Go to the perimeter drive on this config. |
| Corrections reappear **pinned near 0.15 m** | The window only clamped the symptom. `distance_variance_penalty` 0.7 and `angle_variance_penalty` 1.2 are the real lever — same stale §17.21 premise, deliberately left for this step. |
| `W`/`S` leg **degrades** | Over-constrained. Back off to 0.5. |

Change one parameter at a time. §17.25 changed six at once and paid for it
across three sessions.

### Step 3 — only then, the commissioning drive

**There is still no accepted commissioning map**, and yesterday's session
deliberately did not attempt one. Building a 20-minute map on a front end
that loses a third of a metre per strafe would produce a misleading
artefact, not a commissioning map. Once Step 2 comes back clean:

1. **STOP MAP** if a session is running — discard it.
2. Park on the mark. **ZERO** (two taps; must precede MAP).
3. **MAP**, then **VIEW** and keep it open. A fold is visible as it happens.
4. **Perimeter, nose leading, rotating at the corners** so the LiDAR sweeps
   every wall. 0.5–1.5 m off the walls, slow, one direction, close at the
   mark. Longer beats shorter.
5. **MAP** again to stop; it saves automatically.

`graph_residuals.py --watch` alongside. Then `./tools/run_bundle.py --latest`
(refuses runs under 60 s), and open the bundle in
`docs/tools/run_viewer.html`.

**Why rotation and not a square.** The rear 90° is permanently blind behind
the mast. A non-rotating square keeps that cone pointed at the same *world*
direction all run, so one whole side of the room is never observed — which
is why `run_20260827_140207` came back 87% unknown and `SUSPECT`. It is also
the first hardware test of the frame at non-zero headings; the invariant is
verified in simulation at seven headings and on hardware only at yaw ≈ 0
(now confirmed at metre scale, §17.40).

| Acceptance check | Pass condition |
|---|---|
| Return-to-mark | HUD ≈ `(0, 0)`, **`NOSE ≈ 0°`** (not −90°; changed in §17.38) |
| Map integrity | no folds, tears, doubled walls — `map_integrity.py`, D2 is the headline |
| Walls present | real occupied cells, not just free space |

---

## One retracted lead, and one weak one

- ~~**Strafe is the weak axis.**~~ **Retracted before it was ever acted on.**
  The §17.40 drive had `W`/`S` clean and `D`/`A` failing, which looked like a
  real axis effect — a `scan_relay` reflection explanation was already being
  considered. A third recording from the same day
  (`docs/evidence/frontend_scan_matcher/01_ws_slow_three_resets.mp4`) fails on
  `W`/`S`, at the same speed. **The failure is intermittent, not axis-locked.**
  Do not re-derive this lead from the §17.40 drive in isolation — that is
  exactly how it arose.
- **Speed matters** — weak. 0.10 m/s produced corrections of 0.36–0.45 m,
  0.05 m/s produced 0.24–0.34 m. Consistent with the search window being
  reached more readily, but not controlled. Don't build on it.

**What that third recording did strengthen:** its three corrections measure
**0.340, 0.340, 0.340 m** — identical to the millimetre, against a search
window half-width of **0.35 m**. Corrections that do not vary with anything
the robot did, sitting on the edge of the window, is the best single argument
that Stage C is aimed at the right parameter.

## What §17.40 did NOT overturn

§17.28–§17.32's loop-closure conclusions are **out of scope for these
events**, which is different from refuted. Their tuning may still matter for
genuine closures on a long drive — no drive so far has been long enough to
produce one. `loop_search_maximum_distance` 2.0, `loop_match_minimum_chain_size`
8, and the 0.25/0.35 response gates all remain deployed and live-verified;
leave them alone until the perimeter drive gives real closures to judge.

**Still true and load-bearing:** `graph_residuals.py`'s implied-drift-rate is
the right instrument for a **back-end** closure and the wrong one for a
front-end snap, and it cannot currently distinguish them on its own — that
is what `moved` is for. §17.39's 73/44/32% figures are retired: they were
computed as if the corrections cancelled drift, and they do not.

## One small debt from §17.38

`aislebot.urdf` on the Pi is `31833ce0…`, the pre-§17.38 blob; repo `main`
has `ea6619ff…`. **Geometry is byte-identical** with comments stripped
(7105 chars, same hash both revisions) — the §17.38 diff is one hunk, +12/−2,
entirely inside the header comment. Nothing executes differently. What is
stale is the prose: the header on the robot still asserts the orientation-only
−90° rotation §17.38 removed. Deploy it whenever the workspace is next
rebuilt for another reason; it does not justify a rebuild on its own.
§17.38's "all five touched files are now deployed and hash-verified" is
corrected to four of five in §17.40.

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot, branch
> `claude/narrowaislebot-mapping-reliability-038ike`. Read
> `docs/Next_Session_Kickoff.md` (start at RESUME HERE) and
> `docs/Research_Journal.md` §17.40 before doing anything else.
>
> **Settled yesterday, do not reopen:** the pose-graph jumps are **not loop
> closures**. `graph_residuals.py` reported `moved=0, max_shift=0.000` across
> a whole 153 s drive — no graph node was ever moved — while the HUD threw
> corrections of 0.336 / 0.302 / 0.240 m with the nose stepping to −13.4°,
> on a drive where `Q`/`E` were never pressed. Two instruments agree leg by
> leg: graph node spacing is 0.36 m on `W`/`S` where the HUD tracks to within
> 6 cm, and collapses to 0.02 m on `D`/`A` where it jumps. It is the
> front-end scan matcher, and §17.39's "73%/44%/32% implied drift" is retired
> — those corrections overrule correct odometry rather than cancelling drift,
> so the ratio never meant anything.
>
> **This session is one deploy, one drive, one comparison.** Stage C
> (`2a3e83b`) sets `correlation_search_space_dimension` 0.7 → 0.3 and is
> committed but **not on the robot**. Deploy it to `~/ros2_ws/slam_nodom.yaml`
> — note the filename differs from the repo's — hash it on arrival against
> `e90aee53…`, restart mapping, confirm `0.3` with `ros2 param get` against
> the live node, then re-run the identical `W`/`S`/`D`/`A` drive at SLOW with
> `graph_residuals.py --watch`. The baseline table and the three predicted
> outcomes are in the kickoff doc.
>
> Only if that comes back clean, the commissioning perimeter drive — nose
> leading, rotating at corners.
>
> I want to run the drive from the dashboard, not the terminal. Walk me
> through it step by step — I'll do each thing and report back. Don't assume
> a step succeeded. Verify deployed config with `ros2 param get` against the
> live node, never by reading a file, and **hash every transferred file on
> arrival, per file** — an `scp` reported `100%` while writing to a mistyped
> destination path and the build silently used the old file.

---

## Transfers: one staging folder, both directions

```
C:\Users\aritradas\Documents\mecanum robot ROS2\for scp download
```

Everything pulled off the Pi, and everything downloaded on Windows on its way
*to* the Pi, lands here first. Details in `Important_Commands.md` §3.1.

> ⚠ **`scp` reporting `100%` does not mean the file arrived where you
> meant.** A password typed onto the end of a destination path before Enter
> produced a file at that name; `scp` created it, reported success, exited 0,
> and the build that followed silently used the old file. **Hash on arrival,
> per file, not per batch** — two of three in that batch landed correctly,
> which is exactly why a per-batch assumption fails.

**Also:** there is no persistent git clone on the Pi. Deployed code lives
only under `~/ros2_ws/src`, so repo tools (`tools/*.py`) have to be copied
across before they can run there.

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

Since §17.38 `map` and `odom` share this convention too, so map-frame numbers
and body-frame numbers finally agree on which way is which.

## Working style

Hands-on-hardware, one step at a time, nothing assumed to have succeeded.
**Never mark a step done without seeing its actual output.** When something
looks wrong, say so plainly. When the user's own analysis is right (it often
is), say so and build on it rather than re-deriving it.

The user is moving deliberately away from the terminal. Prefer a dashboard
path over an SSH command wherever one exists, and when one doesn't, say so
rather than quietly falling back to SSH.

**One worth carrying from 27 Aug:** the axis bug was found because the user
insisted the map was wrong while the repo's own documentation said it was
fine, and because the dashboard they happened to be running showed the raw
truth rather than a patched version of it. Both instincts beat the written
record.

---

## What's true right now — don't re-derive

### Axes and frames: closed (§17.38)

`base_link`, `odom` and `map` all use **`+X = right, +Y = forward`**. A
freshly-zeroed robot on the mark reads `[0,0,0] @ 0°`. `W→+Y, S→−Y, D→+X,
A→−X`, measured on hardware with ≤1.2 mm cross-axis coupling on ~180 mm
moves. Two conversion points remain in the whole stack: `cmd_vel_axis_adapter`
(base_link ↔ wheel kinematics) and `scan_relay`'s LiDAR mirror (a reflection,
which no TF can express). `docs/Axis_Convention.md` is authoritative;
`tools/verify_axis_chain.py` is its executable form.

### Drive accuracy: validated, closed

0.5 m forward/back ≈ 1.2 cm net; 0.5 m pure lateral ≈ 1.63 cm. Final resting
error 1.97–1.99 cm is `SimpleGoalChecker`'s `xy_goal_tolerance: 0.02` doing
its job, not drift. **Do not re-test this.**

Wheels on the 27 Aug run: all four within 0.015–0.016 rad/s RMS, zero
saturation, zero sign mismatch, arc spread ratio **1.00**, zero anomalies.
The mechanical side is not contributing to the SLAM problem.

### Stage A: run, and it answered the question

`tools/bag_tf_diff.py` on a 233.8 s drive:

| Pair | Distinct changes | Behaviour |
|---|---|---|
| `map→odom` | **3** | flat, then 39.57 cm / −13.80°, then 39.00 cm / +13.80° 12.5 s later, landing back within 0.7 cm |
| `odom→base_link` | 787 | smooth, ~2.3 mm/tick — **including at both jump instants** |

Wheel odometry did not blink when `map` moved 40 cm: **SLAM pose-graph
correction, not odometry.** Settled. The 27 Aug run reproduces the same
signature per-event.

### THE BIG FINDING OF 22 AUG — still load-bearing

**`system/slam_nodom.yaml`'s loop-closure tuning was committed 19 Aug and
never reached the robot.** `install.sh:228` is the only thing that copies it;
that copy's mtime was 26 June. Every drive 19–21 Aug ran on **stock
defaults**, so §17.28–§17.31 were diagnosing parameters that were never
active. §17.27's "50 cm → 2 cm" cannot have been the tuning, and what did
cause it is **open, not settled** — don't invent a cause.

**The lesson is the rule this project now runs on:** a value in the repo is
not a value on the robot.

### The acceptance gate, corrected

`Dashboard_Map_System.md` §3's "no single-sample step > 10 cm" **cannot tell
a good closure from a bad one** — a legitimate correction trips it just as
hard. The criteria that discriminate are **map integrity** and
**return-to-mark**, plus `graph_residuals.py`'s `moved` / `max_shift`.

⚠ **§17.40:** the implied-drift-rate is the right instrument for a *back-end*
closure and the wrong one for a *front-end* snap, and cannot tell them apart
on its own. `moved=0` with a large HUD jump means the front end. §17.39's
73/44/32% figures are retired.

---

## Instruments — what exists, and what has met real data

| Tool | Status |
|---|---|
| `verify_axis_chain.py` | 38 checks, passing, guards the §17.38 fix |
| `map_integrity.py` | self-tests clean; **has met one real map** (27 Aug) |
| `run_bundle.py` / `run_analyzer.py` | **used in anger 27 Aug**, worked |
| `graph_residuals.py` | **met the live node 27 Aug**, found and fixed its own Ctrl-C bug (`4ece40c`), and produced §17.40's finding |
| `scan_quality.py` | self-tests clean, **never run on real scans** |
| `bag_tf_diff.py` | run once (Stage A), answered its question |
| `map_viewer.html`, `run_viewer.html`, `telemetry_analyzer.html` | working |

`--corpus` over the ~70-map archive still hasn't been run; it prints the
percentiles that should replace `map_integrity.py`'s guessed thresholds.

---

## Stage D — AMCL, still never run

Blocked only on having an accepted map. `nav2_params.yaml:57` **is fixed** —
it read `robot_model_type: "omnidirectional"`, which no one exports; now
`nav2_amcl::OmniMotionModel`. Confirmed against upstream on `jazzy` and
`humble`: `plugins.xml` declares only the two fully-qualified classes,
`amcl_node.cpp` defaults to the fully-qualified name, and it passes the
string straight to `createSharedInstance` with no shim and no try/catch on
`on_configure`. The old value would have aborted the **entire** bringup.

Still verify on the robot:

```bash
grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml
ros2 node list | grep slam_toolbox          # MUST come back empty
ros2 param get /amcl robot_model_type       # after bringup
ros2 param get /goal_pose_adapter yaw_offset_deg    # expect 0.0 since §17.38
```

`slam_toolbox` must be completely gone before AMCL starts — both publish
`map→odom`.

Then one goal from the dashboard, then the obstacle test — which needs no
extra work and does not depend on global pose accuracy: the local costmap
inflates live LiDAR returns (`inflation_radius: 0.65`) and MPPI plans around
them, while `collision_monitor` forward-simulates the padded footprint along
the commanded velocity and intervenes only if that path actually collides
within 1.2 s. Velocity-aware, not a static zone.

---

## Standing traps

- **`base_link` is NOT REP-103: `+X` = RIGHT, `+Y` = NOSE**, and since
  §17.38 `odom` and `map` match it. Any new component with a notion of
  "forward" needs checking — `tools/verify_axis_chain.py` is how.
- **Never fix an axis complaint at the display.** Four separate −90°
  display/goal compensations grew over one real frame fault and kept it
  invisible for two weeks (§17.38).
- **`slam_toolbox` 2.8.5 has no loop-closure signal** — no console output, no
  topic, no service. Verified against source *and* the live node. TF and
  graph differencing are the only observations available. Don't grep for it.
- **`src/mecanum_robot/resource/dashboard.html` is dead code.** The served
  page is the `DASHBOARD_HTML` constant in `phone_dashboard.py`.
- **Nothing that stores a coordinate before Stage D.** Live-SLAM coordinates
  don't survive a restart.
- **Never run AMCL and `slam_toolbox` together.** Both publish `map→odom`.
- **A repo value is not a robot value.** Check the live node.
- **Check the Pi's address every session** (`ip -4 -br addr`). Its eduroam
  lease has moved twice in two days, and `aritra-desktop.local` fails to
  resolve from Windows often enough not to trust.
- **`10.42.0.1` only exists while the Pi hosts its own AP.** On eduroam it
  gives a timeout that looks exactly like the robot being down. The AP has
  **no internet uplink**, so `curl` to GitHub fails from the Pi — relay
  through the PC.
- **`curl --retry` does not retry TLS failures.** Use `--retry-all-errors`.

## Deferred, still worth remembering

- Location library + teach flow (gated on Stage D)
- `lateral_scale` independent validation — the 27 Aug square's legs were
  unequal, so it measured nothing. Needs equal-duration legs and a tape
  measure.
- `--corpus` over the ~70-map archive for the threshold percentiles
- `scan_quality.py` on real scans
- Delete or wire up the dead `dashboard.html` — not during map work
- Whether a pure-*forward* move introduces a small lateral component (§17.30's
  untested candidate explanation for the original 1–3 cm side offset)
- The recovery-count cold-start pattern (stiction vs. MPPI warm-up)
- **`AISLEBOT_VIDEO_DECODER_APP`** — recommended against on reasoning, but the
  implementation has never been read. Still owed a proper look.
- MATLAB Tier 1 #3 (occupancy-grid saturation): parameter names still
  unverified. `ros2 param list /slam_toolbox | grep -iE "thresh|pass"` before
  assuming anything. Tier 1 #4 (path clearance) waits on one accepted map.
- **IMU: decided against for now (22 Aug).** MPU-6000/6050 rejected — no
  magnetometer means no absolute heading reference, which is the entire
  point, and `ekf_params.yaml` fuses IMU yaw as ground truth, so a drifting
  signal there would actively hurt. BNO055 remains the right part if this is
  ever prioritized — reasoning in `MATLAB_Navigation_Reference.md` §1.
  **Don't re-open unless the user raises it.**
- `ekf_params.yaml`'s `imu0_config` fuses `roll, pitch` while `two_d_mode:
  true` already forces those states toward zero — redundant, not broken.
  Clean up to `roll, pitch: false, false` (keep `yaw: true`) whenever that
  file is next touched for real hardware.
