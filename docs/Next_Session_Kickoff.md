# Next Session Kickoff — paste this to start

Self-contained prompt for the next Claude Code session. It assumes no memory
of the previous conversation — everything needed is here or in the repo
(`docs/Axis_Convention.md`, `docs/Research_Journal.md`,
`docs/Dashboard_Map_System.md`, `docs/Important_Commands.md`,
`docs/MATLAB_Navigation_Reference.md`, `tools/README.md`).

**Rewritten 27 Aug 2026 (§17.38–§17.39).** The 22 Aug version is superseded
in full. The axis and map-frame work it was organised around is **closed and
merged to `main`**; this file is now organised around the one thing that is
not: **loop-closure reliability**.

---

## ⏸ RESUME HERE — the SLAM problem

**Everything up to and including the map frame is done. The pose graph is
not.** That is the whole agenda.

### The problem, in four numbers

From `run_20260827_140207` — a 38-second W→D→S→A square, no rotation
commanded, full bundle at `data/field_runs/run_20260827_140207_bundle.json`:

| | Closure over the same square |
|---|---|
| **Wheel odometry** | **2.58 cm** |
| **SLAM corrected pose** | **6.2 cm** |

Odometry path 1.42 m; map path 2.47 m. The extra 1.05 m is correction
applied. **The pose graph made the estimate worse than dead reckoning.**

Three correction events, all flagged `pose graph moved, robot did not`:

| # | t | Correction | Odom moved | Yaw | at map |
|---|---|---|---|---|---|
| 1 | 32.2 s | **0.327 m** | 0.005 m | −8.2° | (0.14, 0.30) |
| 2 | 42.5 s | **0.386 m** | 0.005 m | −10.8° | (0.21, −0.19) |
| 3 | 52.3 s | **0.416 m** | 0.005 m | +18.2° | (−0.35, −0.02) |

All three inside the first minute, and **growing** — 0.327 → 0.386 → 0.416.
Event 1 is on video —
`docs/evidence/axis_frame_fix/02_square_wdsa_after_fix.mp4` at 17–18 s, the
pose card jumping `X 0.114, Y 0.304` → `X 0.012, Y 0.013` in a single 10 Hz
sample.

**This is §17.32's open question, unchanged.** The axis fix had nothing to do
with it and could not have improved it.

### ⚠ Re-test rather than inherit

§17.28–§17.32's loop-closure conclusions were drawn on a stack that we now
know had a **rotated map frame** (§17.38). The scan matcher's input was fine
— `scan_relay`'s mirror is calibrated in `base_link`, which never moved — so
most of it should still hold. But "should still hold" is exactly the kind of
assumption that cost two weeks last time. **Treat prior loop-closure
conclusions as hypotheses to re-confirm, not as settled facts**, and say
which category any given claim is in.

Two that are safe, because they are about code rather than geometry:

- **This `slam_toolbox` build (2.8.5) emits no per-closure signal** — no
  console line, no topic, no service. Verified against source *and* the live
  node (§17.29). Don't go looking for one.
- **`publishGraph()` carries node positions and edge endpoint coordinates
  only** — no node ids, no edge measurement, no information matrix (§17.35).
  A true χ² residual is **not computable** from `/slam_toolbox/graph_visualization`.
  `graph_residuals.py` works by *differencing successive publications*
  instead, which is why it exists in the form it does.

---

## Step 0 — the instrument that has never run

`tools/graph_residuals.py` was built for exactly this problem and **has never
met the live node**. It is not on the Pi (no git clone there). One transfer:

```powershell
# Windows, from the staging folder
curl.exe -sSL -o graph_residuals.py "https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/tools/graph_residuals.py"
Get-FileHash graph_residuals.py -Algorithm SHA256
scp graph_residuals.py aritra@10.42.0.1:~/tools/graph_residuals.py
```

```bash
sha256sum ~/tools/graph_residuals.py       # match it before running
source /opt/ros/jazzy/setup.bash
python3 ~/tools/graph_residuals.py --selftest        # first, on the Pi
python3 ~/tools/graph_residuals.py --watch --log ~/aislebot_logs/graph.jsonl
```

**What it gives you that nothing else does.** The graph is republished every
`map_update_interval` (1.0 s). A node that moves between two publications was
moved by the optimiser; differencing the *edge sets* over the same two
messages names **which closure arrived in the update that moved things**.
That is the per-closure signal §17.29 concluded does not exist — it does not
exist as an *event*, but it does as a *difference*.

And it can be judged, which a raw jump size cannot:

```
implied drift rate = shift / metres driven since the closed-on node
```

A legitimate closure cancels drift accumulated since the robot was last
there, so the rate should land near this robot's measured **1.5%** (§17.32's
3.4 m box), 2.4% forward/back, 3.3% lateral (§17.30). **20% means it
corrected drift that never accumulated.** The 10% ceiling is the single
judgement call in the tool and it is a parameter.

**Applied to the three events above, computed from the bundle's own pose
CSV**, using total odometry path driven since the run started:

| Event | Correction | Odom path driven | Implied rate |
|---|---|---|---|
| t=32.2 s | 0.327 m | 0.447 m | **73%** |
| t=42.5 s | 0.386 m | 0.869 m | **44%** |
| t=52.3 s | 0.416 m | 1.300 m | **32%** |

Against a measured 1.5%. These are **conservative lower bounds**: the tool
measures against distance since the *closed-on node*, which is more recent
than the run start, so a smaller denominator would push every one of these
higher.

**That is the number to explain.** Corrections are cancelling drift that
could not physically have accumulated — on a robot whose wheel odometry
closed the same square to 2.58 cm.

---

## Step 1 — the first real commissioning drive

**There is still no accepted commissioning map.** Everything driven so far
has been an axis test.

`run_bundle.py`'s own header records that `run_20260825_113735` and
`_151713` "were analysed at length on 26 Aug before anyone noticed they were
30-second bug-fix checks rather than commissioning drives." They were never
candidates.

**Drive it like this**, all from the dashboard:

1. **STOP MAP** if a session is running — discard it.
2. Park physically on the mark. **ZERO** (two taps; must precede MAP).
3. **MAP**, then **VIEW** and keep it open. A fold is visible the moment it
   happens, which no after-the-fact screenshot gives you.
4. **Perimeter, nose leading, rotating at the corners** so the LiDAR sweeps
   every wall. 0.5–1.5 m off the walls, slow, one direction, close at the
   mark. Longer beats shorter — the 20-minute run had 10× the wall cells of
   the 5-minute one.
5. **MAP** again to stop; it saves automatically.

**Why rotation matters and a square will not do.** The rear 90° is
permanently blind behind the mast. A non-rotating square keeps that blind
cone pointed at the *same world direction* for the entire run, so one whole
side of the room is never observed — which is exactly why
`run_20260827_140207` came back 87% unknown and `SUSPECT`.

**This drive is also the first hardware test of the frame at non-zero
headings.** The invariant is verified in simulation at seven headings
(`verify_axis_chain.py`) but on hardware only at yaw ≈ 0. Rotating at the
corners tests it for real. If the map ever appears to grow sideways relative
to actual motion, stop — the arithmetic says it cannot, so that is real
information.

Run `graph_residuals.py --watch` alongside. Then:

```bash
./tools/run_bundle.py --latest        # refuses runs under 60 s
```

Open the bundle in `docs/tools/run_viewer.html`.

### Acceptance

| Check | Pass condition |
|---|---|
| Return-to-mark | HUD ≈ `(0, 0)`, **`NOSE ≈ 0°`** (not −90° — that changed in §17.38) |
| Map integrity | no folds, tears, doubled walls — `map_integrity.py`, D2 is the headline |
| Walls present | real occupied cells, not just free space |

Single-sample step size is **diagnostic, not pass/fail**: a legitimate
correction of accumulated drift trips it exactly as hard as a bad one. That
is why `graph_residuals.py`'s implied-drift-rate exists.

---

## The levers, and the one that is explicitly gated

Deployed now (`system/slam_nodom_stageB.yaml`, on the Pi as
`~/ros2_ws/slam_nodom.yaml`, sha `7ec7904a…`). **Verify with
`ros2 param get /slam_toolbox <name>` against the live node, never by reading
the file** — that is the discipline that caught §17.32:

| Parameter | Deployed | Stock |
|---|---|---|
| `loop_search_maximum_distance` | **2.0** | 5.0 |
| `loop_match_minimum_chain_size` | **8** | 5 |
| `max_laser_range` | **10.0** | 12.0 |
| `loop_match_minimum_response_coarse` | 0.25 | 0.25 |
| `loop_match_minimum_response_fine` | 0.35 | 0.35 |
| `minimum_travel_distance` | 0.2 | 0.2 |
| `map_update_interval` | 1.0 | — |

**Do not raise `_coarse`/`_fine` to 0.30/0.40 on a hunch.** That lever is
explicitly gated on "if the map visibly folds", and as of
`run_20260827_140207` it does not: D2 doubled walls reads 4 cells, 0
clusters — essentially clean. Raising the gate to fix corrections that are
firing on a *clean* map treats the symptom and hides the cause.

**Chain size 8 × `minimum_travel_distance` 0.2 ≈ 1.6 m before closure is
eligible at all.** On short drives that lands closures in the back half,
which is where §17.32 saw them cluster — that clustering may be *eligibility*
rather than aliasing. A long perimeter drive is the test that separates them.

---

## Paste this as the first message of the new session

> Continue work on AritraD11/NarrowAisleBot. `main` is current at `5466f3e`
> and everything below is merged into it — cut a fresh branch from `main`.
> Read `docs/Next_Session_Kickoff.md` (start at RESUME HERE),
> `docs/Axis_Convention.md`, and `docs/Research_Journal.md` §17.38–§17.39
> before doing anything else.
>
> **Closed last session — do not reopen:** the map frame was rotated −90°
> because `odometry_publisher.py` published a rotated orientation with an
> unrotated translation. Fixed, deployed, verified on hardware, demonstrated
> on video, guarded by `python3 tools/verify_axis_chain.py` (38 checks, fails
> if anyone edits it back out). Four downstream −90° compensations were
> deleted with it. §17.36/§17.37's "the axis stack is coherent" conclusion
> was wrong about the map frame and is corrected in place — don't cite them
> against §17.38. **Never fix an axis complaint in the dashboard**; that is
> what hid this for two weeks.
>
> **This session is SLAM — the pose graph, which the frame work did not
> touch and could not have fixed.** On a 38 s square: wheel odometry closed
> to 2.58 cm, SLAM's corrected pose closed to 6.2 cm. Three corrections of
> 0.416 / 0.386 / 0.327 m, all "pose graph moved, robot did not", one caught
> on video jumping 31 cm inside a single 10 Hz sample. Computed against
> odometry path driven, those corrections imply drift rates of **73% / 44% /
> 32%** where this robot measures **1.5%** — and those are lower bounds.
> That is what I want explained.
>
> Careful with the prior work: §17.28–§17.32's loop-closure conclusions were
> drawn on a stack with a rotated map frame. Treat them as hypotheses to
> re-confirm, not settled facts, and tell me which category a claim is in.
>
> Step 0 needs no drive: `tools/graph_residuals.py` was built for exactly
> this and has never met the live node. It's not on the Pi — one `scp`, then
> `--selftest` there before trusting it.
>
> Then the first real commissioning drive: perimeter, **nose leading,
> rotating at corners** so the LiDAR sweeps every wall — a non-rotating
> square leaves the blind rear 90° pointed one way all run, which is why the
> last map came back 87% unknown. That drive is also the first hardware test
> of the frame at non-zero headings.
>
> I want to run the drive itself **from the dashboard, not the terminal**.
> Walk me through it step by step — I'll do each thing and report back.
> Don't assume a step succeeded. Verify deployed config with `ros2 param get`
> against the live node, never by reading a file, and **hash every
> transferred file on arrival, per file** — an `scp` reported `100%` while
> writing to a mistyped destination path and the build silently used the old
> file.

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
**return-to-mark**, plus `graph_residuals.py`'s implied drift rate.

---

## Instruments — what exists, and what has met real data

| Tool | Status |
|---|---|
| `verify_axis_chain.py` | 38 checks, passing, guards the §17.38 fix |
| `map_integrity.py` | self-tests clean; **has met one real map** (27 Aug) |
| `run_bundle.py` / `run_analyzer.py` | **used in anger 27 Aug**, worked |
| `graph_residuals.py` | self-tests clean, **never met the live node** ← Step 0 |
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
