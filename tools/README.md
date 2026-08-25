# tools/ — Pi-side scripts

Standalone scripts that run on the Raspberry Pi 5. No ROS 2 required —
they talk to the ESP32 directly over USB serial, so they work whether or
not the ROS stack is up.

(Not to be confused with `docs/tools/`, which holds the offline HTML
analysis tools.)

| Script | What it does |
|---|---|
| `nab_pid_logger.py` | Drives a scripted bench test on the ESP32 and writes the result to a CSV in `~/aislebot_logs/`. Replaces the serial-monitor copy-paste workflow. |
| `map_corpus.py` | Compares every mapping run in a folder side by side — size, occupied/free/unknown, metres of wall against the bounding perimeter. Answers "is this map better than the last one" across the archive instead of one run at a time. |
| `map_integrity.py` | Measures whether a saved map **folded**. Doubled walls, skeleton forks, wall thickness, orientation coherence, free-space connectivity — the §17.32 acceptance gate as numbers rather than an eyeball. Writes an annotated PNG. |
| `graph_residuals.py` | Live per-edge residual analysis of `slam_toolbox`'s pose graph, from `/slam_toolbox/graph_visualization`. The one Tier 1 MATLAB item worth building (`MATLAB_Navigation_Reference.md`). |
| `pi_audit.sh` | Read-only inventory of the Pi — disk, network, services, deployed code, run data, cleanup candidates. Deletes nothing. With `--online`, diffs every deployed source file against GitHub. |

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
| `staircase` | PWM ramped up from rest in steps of 2. Finds per-motor breakaway PWM = `Kstat`. Run once in the air, once on the floor; the difference is the ground-load correction. |
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
