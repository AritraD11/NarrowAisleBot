# tools/ — Pi-side scripts

Standalone scripts that run on the Raspberry Pi 5. No ROS 2 required —
they talk to the ESP32 directly over USB serial, so they work whether or
not the ROS stack is up.

(Not to be confused with `docs/tools/`, which holds the offline HTML
analysis tools.)

| Script | What it does |
|---|---|
| `nab_pid_logger.py` | Drives a scripted bench test on the ESP32 and writes the result to a CSV in `~/aislebot_logs/`. Replaces the serial-monitor copy-paste workflow. |

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
