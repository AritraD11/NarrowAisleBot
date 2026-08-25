# Ground test logs

Empty on purpose — no ground-floor run has been done yet. Ground testing
starts once the air-side calibration sequence is complete:

1. `./tools/nab_pid_logger.py --test plant` (air) — measures τ, finalizes `Kp`
2. `./tools/nab_pid_logger.py --test staircase` (air) — measures `Kstat` per motor
3. `./tools/nab_pid_logger.py --test steps` (air) — verifies the refit gains
4. Push refit gains, lower `max_wheel_speed` (`<X,4.2>`) — see `docs/PID_Calibration.md` §7
5. **Then** repeat staircase + plant on the floor — ground-load `Kff`/`Kstat`
   are expected to run 10–30% higher than air values

## Naming convention

Same as `bench/`: `run_YYYYMMDD_HHMMSS.csv`, straight off the Pi, no
renaming. Drop the analysis output in `ground/analysis/` alongside it,
same as `bench/analysis/`.

## What changes in the analysis once ground data exists

Everything `tools/analyze_bench_log.py` already checks still applies. Two
additional things become relevant on the floor and are worth checking by
hand until the tool grows them:

- **PWM headroom margin** matters more here — ground load eats into it
  directly, and this is exactly what could push a motor toward
  saturation that never saturated in the air.
- **Cross-run comparison against the matching air run** — same
  setpoints, air vs ground, is what actually quantifies the 10–30%
  ground-load feedforward increase `PID_Calibration.md` predicts, rather
  than leaving it as a predicted range.
