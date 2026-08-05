# tools/ — Pi-side and PC-side scripts

Scripts split by where they run. The Pi-side ones talk to the ESP32
directly over USB serial, so they work whether or not ROS 2 is up. The
PC-side one runs on the Windows machine to pull data off the Pi.

(Not to be confused with `docs/tools/`, which holds the offline HTML
analysis tools.)

| Script | Runs on | What it does |
|---|---|---|
| `nab_pid_logger.py` | Pi | Drives a scripted bench test on the ESP32 and writes the result to a CSV in `~/aislebot_logs/`. Replaces the serial-monitor copy-paste workflow. |
| `analyze_bench_log.py` | Pi or PC | Turns one telemetry CSV into a markdown report + 2 plots — the same checks (RMS error, saturation, rotation-aware diagonal deviation, sign-mismatch, clock sanity) applied by hand to every run so far. See `data/bench_logs/README.md` for the full log this feeds. |
| `sync_bench_logs.ps1` | Windows PC | Incremental download of new CSVs from `~/aislebot_logs` on the Pi — lists what's already local, pulls only what's missing. No rsync needed, just the OpenSSH client. |

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
