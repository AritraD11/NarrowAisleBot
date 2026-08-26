# tools/ — Pi-side and PC-side scripts

Scripts split by where they run. The Pi-side ones talk to the ESP32
directly over USB serial, so they work whether or not ROS 2 is up. The
PC-side one runs on the Windows machine to pull data off the Pi.

(Not to be confused with `docs/tools/`, which holds the offline HTML
analysis tools.)

| Script | Runs on | What it does |
|---|---|---|
| `nab_pid_logger.py` | Pi | Drives a scripted bench test on the ESP32 and writes the result to a CSV in `~/aislebot_logs/`. Replaces the serial-monitor copy-paste workflow. |
| `analyze_bench_log.py` | Pi or PC | Turns one telemetry CSV into a markdown report + 2 plots — RMS error, saturation, rotation-aware diagonal deviation, sign-mismatch, clock sanity. See `data/bench_logs/README.md`. |
| `sync_bench_logs.ps1` | Windows PC | Incremental download of new CSVs from `~/aislebot_logs` on the Pi — pulls only what's missing. Just the OpenSSH client, no rsync. |
| `map_corpus.py` | Pi or PC | Compares every mapping run in a folder side by side — size, occupied/free/unknown, metres of wall against the bounding perimeter. Answers "is this map better than the last one" across the archive instead of one run at a time. |
| `map_integrity.py` | Pi or PC | Measures whether a saved map **folded**. Doubled walls, skeleton forks, wall thickness, orientation coherence, free-space connectivity — the §17.32 acceptance gate as numbers rather than an eyeball. Writes an annotated PNG. |
| `run_analyzer.py` | Pi or PC | **One report for one drive.** Map integrity + SLAM path + wheel odometry + per-wheel telemetry, read together, with the cross-checks between them. Writes an annotated PNG. |
| `graph_residuals.py` | Pi (needs ROS) | Differences successive publications of `slam_toolbox`'s pose graph and names the closure that moved it. The one Tier 1 MATLAB item worth building (`MATLAB_Navigation_Reference.md`). |
| `pi_audit.sh` | Pi | Read-only inventory — disk, network, services, deployed code, run data, cleanup candidates. Deletes nothing. With `--online`, diffs every deployed source file against GitHub. |
| `pi_clean.sh` | Pi | Removes accumulated waste (journald, `~/.ros/log`, stale snaps, old kernels, dead workspace code). **Dry run by default**; `--apply` to execute. |

---

## `map_integrity.py`

Answers the question §17.34 closed on: **did this map fold?** — without
requiring anyone to stare at a grid and decide.

```bash
./tools/map_integrity.py data/field_runs/run_20260825_151713.pgm
./tools/map_integrity.py --corpus data/field_runs --csv integrity.csv
./tools/map_integrity.py run_20260825_151713.pgm --png annotated.png
./tools/map_integrity.py --selftest
```

Needs the `.pgm` and its `.yaml` side by side. Pure standard library — no
numpy, no PIL, no PyYAML — so it runs on the Pi and on the Windows laptop
without installing anything.

### What it measures

| | Detector | Signature it is looking for |
|---|---|---|
| D1 | wall thickness | a fold that lands nearly on itself **fattens** the wall instead of duplicating it |
| D2 | **doubled walls** | two near-parallel walls with **free** space between them, across a gap narrower than the robot |
| D3 | forks | branch points on the thinned wall skeleton — a corridor that splits where the real one does not |
| D4 | orientation | a chunk rotated a few degrees puts a satellite peak beside the dominant wall axis |
| D5 | free space | a fold can strand free space outside the room outline |

**D2 is the one that carries the verdict.** Its argument: free cells between
two walls mean the LiDAR returned through that space, so something stood
between them and saw both faces — but the gap is under the robot's own
0.48 m width, so that something cannot have been this robot. Two walls whose
far faces were both observed across a gap nothing could occupy is the
geometry a false loop closure leaves when it fuses two poses that are not
the same pose.

The known hole in the argument: a genuine narrow gap between shelves, seen
end-on down its length, looks the same. That is why flagged cells are
**clustered and reported with map coordinates** rather than only counted —
a real end-on gap is one place you can walk to, a fold is a whole wall
duplicated. `--png` writes the map with those cells in red, so the number
and the picture can be checked against each other.

### Thresholds

Provisional, and labelled as such in the output. They stop being guesses
when `--corpus` is run over the archived runs: the same room mapped 70 times
gives a distribution, and the percentiles it prints are what a threshold
should be set from.

`--selftest` builds five synthetic rooms with known answers — a clean
rectangle, a planted 0.35 m ghost wall, two walls that close with
**unknown** between them, a real 0.85 m aisle, and a genuinely thick wall —
and asserts that the fold is caught and the other four are not. Run it after
touching any of the geometry.

---

## `run_analyzer.py`

Everything one mapping run produced, analysed together instead of one file at
a time. Point it at a run and it finds the rest alongside:

```bash
./tools/run_analyzer.py ~/aislebot_logs/run_20260826_143000
./tools/run_analyzer.py run_20260826_143000 --png run.png --json run.json
./tools/run_analyzer.py --selftest
```

| Reads | For |
|---|---|
| `run_<stamp>.pgm` / `.yaml` | map integrity (delegates to `map_integrity.py`) |
| `run_<stamp>_pose.csv` | SLAM pose, **wheel odometry**, and the correction between them |
| `run_<stamp>.csv` | 13-column per-wheel telemetry |
| `run_<stamp>_report.json` | duration, sample counts |

Missing files are reported, not fatal — every other section still runs.

### The point is the cross-checks

Three instruments watched the same drive and can be asked whether they agree.

**Wheel odometry cannot jump.** It integrates encoder ticks and has no
opinion about the world; it drifts, but it has no mechanism for a
discontinuity. So when the `map→odom` correction moves while odom steps
normally, **the pose graph moved and the robot did not.** §17.32 established
that once, from a rosbag, with a separate tool. The dashboard now logs the
same quantity every run, so every run gets it for free — per event, with a
timestamp and a map coordinate.

**A false closure leaves two marks:** a correction when it fires, and a
doubled wall where it fired. `map_integrity.py` finds the second, this finds
the first, and when both land within a metre of each other that is two
independent witnesses to the same event — stronger evidence than this project
has previously been able to produce about any closure.

**A slipped wheel corrupts odometry**, which corrupts the scan matcher's
starting guess. A correction coinciding with PWM saturation or a
commanded/actual sign mismatch is a mechanical fault, not a SLAM parameter —
so the tool flags that pairing separately and says so.

### Two numbers this project did not previously have

- **Wheel closure** — if the robot physically ended on its mark, the final
  odom reading *is* the wheels' accumulated drift over the whole run,
  separated from SLAM's correction of it.
- **Cumulative correction** — how much SLAM moved the estimate in total,
  against how far the robot actually drove.

### Wheels: health only, deliberately

Per-wheel RMS tracking error, PWM saturation, commanded/actual sign
mismatch, mean speed, and arc length, plus the busiest/laziest travel ratio.
It does **not** re-derive chassis position from wheel speeds: that is the
odometry node's job, it already does it, and the pose CSV now records the
result. Re-deriving it here against a guessed sign convention would only add
a second thing to doubt — the same reasoning `odometry_publisher.py` gives
for leaving its longitudinal scale at 1.0.

`--png` draws the map with doubled walls in red, the SLAM path in blue, the
wheel path in green, and a yellow cross at each correction. Where blue and
green diverge is exactly where SLAM overruled the wheels.

`--selftest` needs no data: it builds a clean synthetic run, one with a
planted 0.40 m correction while odometry steps smoothly, a planted wheel
sign-mismatch at the same instant, and a pre-26-Aug 4-column pose CSV, and
asserts each is read correctly — including that the legacy file loads and
says odometry is unavailable rather than inventing it.

---

## `graph_residuals.py`

The one Tier 1 item from `docs/MATLAB_Navigation_Reference.md` worth
building, and the answer to a limitation §17.29 established: this
`slam_toolbox` build emits **no per-closure signal at all** — no console
line, no topic, no service. So "was that a good closure?" cannot be answered
by watching for the event.

```bash
source /opt/ros/jazzy/setup.bash
./tools/graph_residuals.py --watch                # run this during the drive
./tools/graph_residuals.py --watch --log g.jsonl  # ... and keep the record
./tools/graph_residuals.py --save g.json          # capture on the Pi
./tools/graph_residuals.py --load g.json          # analyse on the laptop
./tools/graph_residuals.py --selftest             # no ROS needed
```

### What the topic carries — and what it does not

Verified against `loop_closure_assistant.cpp`'s `publishGraph()`, not
assumed:

| | |
|---|---|
| **published** | node id → solved `(x, y)`, one SPHERE marker per vertex |
| | edges as two `LINE_LIST` markers whose points are pairs of endpoint **coordinates** |
| | republished every `map_update_interval` — 1.0 s here |
| **not published** | node **orientation** (`toMarker()` hardcodes `orientation.w = 1`) |
| | edge node **ids** — the line list carries geometry, not topology |
| | the edge **measurement**, which is what a true residual is measured against |
| | the information matrix |

So a true SE(2) chi-squared residual **is not computable from this topic**.
Topology is recovered by matching each line-list endpoint back to a node
marker by position — exact match, since both are the same doubles from the
same message, with a tolerance fallback and an unresolved count so a
mis-match cannot silently invent an edge.

### Where the signal actually is

The graph is republished every second, so successive messages can be
differenced. **A node that moves between two publications was moved by the
optimiser.** That is Stage A's method — §17.32 caught a 39.57 cm `map→odom`
jump by differencing TF — but at per-node resolution, and with the cause
attached: comparing edge sets across the same two messages says *which edge
arrived in the update that moved things*. A closure that appears in the same
update as a 40 cm shift is that shift's cause.

**This is the per-closure signal §17.29 concluded did not exist.** It does
not exist as an event. It exists as a difference.

And unlike a raw jump size, the difference can be judged:

```
implied drift rate  =        how far the graph moved
                      ---------------------------------------
                      metres driven since the closed-on node
```

A legitimate closure cancels drift accumulated since the robot was last at
that spot, so its implied rate should land near this robot's measured
odometry error — 1.5% over §17.32's 3.4 m box drive, 2.4% on 0.5 m
forward/back, 3.3% lateral (§17.30). A closure implying 20% corrected drift
that never accumulated. The `--max-drift-rate` ceiling defaults to 10%,
three to four times the worst measured rate, and it is **the one judgement
call in the tool** — everything else is measured.

`--watch` prints one line per update, marked `.` baseline, blank quiet,
`~` shift, `+` closure, `!` suspect closure, with map coordinates on every
closure so the location can be checked in `map_integrity.py --png`. A false
closure puts a doubled wall exactly where it strained the chain; the two
tools agreeing on a location is much stronger evidence than either alone.

A single snapshot has nothing to difference against, so snapshot mode
reports structure only — chain-edge length outliers by modified z-score
(the `trimLoopClosures` analogue on a solved graph) and the loop-edge
table — and says as much in its output.

`--selftest` needs no ROS. It plants a legitimate closure (8 m driven,
15 cm cancelled, 1.9%), a false one (3 m driven, 60 cm yanked, 20%), an
unchanged graph, and a stretched chain link, and asserts each is called
correctly — including that the topology is recovered from coordinates alone
every time.

---

## `pi_audit.sh`

Answers "what is actually on this robot, and is any of it stale?" in one
paste. It **only reads** — nothing is deleted, moved, or restarted.

```bash
curl -sSL -o /tmp/pi_audit.sh \
  https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/claude/mapping-autonomous-nav-695glw/tools/pi_audit.sh
bash /tmp/pi_audit.sh --online
```

`--online` adds section 16, which fetches each deployed source file from
GitHub and reports `match` / `DIFFERS` / `MISSING-ON-PI` / `EXTRA`. That is
the direct check for §17.32's lesson — **a value in the repo is not a value
on the robot** — and it needs the Pi on a network with internet (eduroam,
not the `aislebot-ap` AP, which has no uplink). Without the flag the rest of
the audit still runs offline.

Override the branch with `AISLEBOT_BRANCH=<branch> bash /tmp/pi_audit.sh --online`.

Section 13 and 14 list cleanup candidates with sizes. Read them before
deleting anything — `~/ros2_ws/build`, `~/.ros/log` and old rosbags are
usually where the space went.

---

## `nab_pid_logger.py`

```bash
sudo apt install python3-serial          # once
chmod +x tools/nab_pid_logger.py         # once

./tools/nab_pid_logger.py --test plant
```

**Wheels in the air for every test except `record`.** Ctrl-C sends `<S>`
then `<E0>` — so does any crash or a SIGTERM.

| `--test` | Purpose |
|---|---|
| `plant` | Open-loop PWM steps, PID bypassed. Measures the plant time constant τ and DC gain, and prints the Kp/Ki they imply. **Run this first** — τ is the last unmeasured quantity in the controller. |
| `staircase` | PWM ramped up from rest in steps of 2. Fits per-motor `Kff` and `Kstat` together (least-squares through the moving points). Run once in the air, once on the floor; the difference is the ground-load correction. **On the ground this drives in a straight line and can cover several metres** — add `--mode rotate` if the floor space isn't there; the wheels get the mecanum spin sign-pattern instead of a straight drive, so the chassis turns roughly in place while still loading the wheels against the floor the same way. |
| `steps` | Closed-loop velocity steps. Rise, overshoot, settling time, steady-state error, PWM saturation — the verdict test for a gain set. |
| `sweep` | `steps`, repeated across several gain sets, one CSV each. `--gains "45,250,0.5 70,250,0.5"` |
| `record` | Log only. Drive the robot however you like (ROS 2 teleop, joystick); Ctrl-C to stop. |

Each run prints its own summary table as it finishes, so a bad run is
obvious on the bench rather than an hour later.

### Output

CSV in `~/aislebot_logs/<test>_<timestamp>.csv`. The first 13 columns are
exactly what `aislebot_pid_analysis_v2.py` and
`docs/tools/telemetry_analyzer.html` already expect:

```
pi_time_s, FR_target_rads, FR_actual_rads, FR_pwm, FL_…, RR_…, RL_…
```

Another 16 follow (`error`, `ff`, `iterm`, `pos_rad` per motor) from the
firmware's `<L2>` extended telemetry. The existing tools ignore them; the
tuning maths needs them.

See [`../docs/PID_Calibration.md`](../docs/PID_Calibration.md) for what
to do with the numbers that come out.

---

## `sync_bench_logs.ps1`

Run from PowerShell on the Windows PC — pulls new bench/ground CSVs off
the Pi without re-downloading ones you already have.

```powershell
tools\sync_bench_logs.ps1
```

Defaults to `aritra@10.42.0.1` (the fixed AisleBot-Pi AP address),
`~/aislebot_logs` on the Pi, and
`C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading`
locally. Override any of the three:

```powershell
tools\sync_bench_logs.ps1 -LocalDir "D:\backup\aislebot_logs"
```

Works by listing remote filenames over `ssh`, diffing against the local
folder, and `scp`-ing down only what's missing. Needs the Windows OpenSSH
client — already confirmed present if you've run `scp aritra@10.42.0.1:...`
successfully before.

## `analyze_bench_log.py`

```bash
./tools/analyze_bench_log.py data/bench_logs/bench/run_XXXXXXXX_XXXXXX.csv
```

Writes `<name>.md` + `<name>_tracking.png` + `<name>_error_pwm.png` into
an `analysis/` folder next to the CSV. Pass `--note "..."` (repeatable)
to add context lines to the report — firmware version at record time,
what the run was for, anything the numbers alone don't say.

This is the standing workflow now: every CSV that comes off the Pi gets
run through this and committed alongside its analysis, on
`claude/nab-hardware-calibration`. See `data/bench_logs/README.md` for
the index of everything analyzed so far.
