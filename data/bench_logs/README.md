# NarrowAisleBot — Bench & Ground Test Log

Every telemetry CSV pulled off the Pi, plus a full analysis (report + plots)
for each, generated with `tools/analyze_bench_log.py`. This is the running
record for the PID/feedforward calibration effort — see
`docs/PID_Calibration.md` for the derivation these runs feed, and
`docs/Research_Journal.md` Part XVI for the narrative.

**Branch:** all calibration work (CSVs, analysis, gain updates) lives on
`claude/nab-hardware-calibration`.

## Layout

```
data/bench_logs/
  bench/              wheels in the air, robot on blocks
    run_*.csv
    analysis/
      run_*.md         per-run report
      run_*_tracking.png
      run_*_error_pwm.png
  ground/              robot on the floor, real load
    run_*.csv
    analysis/
      (same structure)
```

## How a new CSV gets in here

```bash
# 1. Pull new files from the Pi (Windows, incremental — skips what you have)
tools\sync_bench_logs.ps1

# 2. Analyze it (writes <name>.md + two PNGs into ./analysis/ next to the CSV)
./tools/analyze_bench_log.py data/bench_logs/bench/run_XXXXXXXX_XXXXXX.csv

# 3. Commit CSV + analysis together, on claude/nab-hardware-calibration
git add data/bench_logs/
git commit -m "..."
```

## Bench runs (wheels in air) — summary

| Run | Date | Firmware | Type | Worst RMS error | PWM sat | Sign faults | Verdict |
|---|---|---|---|---|---|---|---|
| [`run_20260702_183233`](bench/analysis/run_20260702_183233.md) | 2 Jul 2026 | v2.0, shared CPR=93132 | live drive | RR 4.5% of peak | 0% | 0 | Loop healthy under old gains. **Not usable to tune v3.0** — predates the per-motor CPR fix and is a continuous drive, not isolated steps. |
| [`run_20260804_193703`](bench/analysis/run_20260804_193703.md) | 4 Aug 2026 | v2.0, post encoder/CPR fix | live drive | RL 2.4% of peak | 0% | 0 | First run on the corrected encoder path. Confirms hardware health, still not isolated steps. |
| [`run_20260805_140048`](bench/analysis/run_20260805_140048.md) | 5 Aug 2026 | **v3.0** — recalibrated gains, two-term FF, per-motor CPR | scripted steps | RR 1.4% of peak | 0% | 0 | **Best tracking yet.** Confirmation run before the Block 1 plant/staircase/steps calibration sequence. |

Trend: worst-motor tracking error has gone 4.5% → 2.4% → 1.4% across the three runs, tracking each firmware/hardware fix in order (encoder/CPR fix, then the v3.0 gain recalibration). None of the three is a step-response or PWM-staircase test, so none of them can be used to *fit* `Kff`/`Ki`/τ — that's what `tools/nab_pid_logger.py`'s `plant`/`staircase`/`steps` tests are for. These three are the "is the loop healthy" checkpoints along the way.

## Ground runs (on the floor)

| Run | Date | Firmware | Type | Worst RMS error | Ground vs air PWM gap | Verdict |
|---|---|---|---|---|---|---|
| [`run_20260806_152810`](ground/analysis/run_20260806_152810.md) | 6 Aug 2026 | v3.0, air-calibrated gains (not yet ground-refit) | live drive, full weight | RL 4.0% of peak | **+12–15%** at matched velocities (measured, not just predicted) | Loop stable on real ground — zero saturation, zero sign faults. Confirms the predicted ground-load Kff increase quantitatively. New finding: ~3–5× more steady-state velocity ripple than air, cause not yet confirmed. **Not a substitute for the structured `staircase`/`plant` tests** — still a drive session, can't separate Kff from Kstat or measure τ. |

First real-floor data. Confirms the direction and rough size of the predicted ground-load correction (§7 in `PID_Calibration.md`) directly from driving, ahead of the structured tests. See the linked report for the full matched-plateau comparison and the ripple investigation.

## What every analysis checks

`tools/analyze_bench_log.py` runs the same checks by hand-analysis converged
on across these three runs:

- RMS tracking error, absolute and as % of peak commanded velocity
- PWM saturation % and headroom
- Direction-sign mismatches (target/actual opposite sign at speed — the
  tell for a `MOTOR_DIR_SIGN`/`ENC_DIR_SIGN` fault)
- Diagonal-pair deviation (FR−RL, FL−RR), **restricted to same-sign-target
  samples** — rotation commands legitimately put a diagonal pair at
  opposite-sign targets, and computing this over all samples produces a
  false alarm. (This mistake was made and caught once already — see
  `docs/Research_Journal.md` Part XVI §16.2 — the tool now does the
  correct thing by default.)
- Sample-rate / gap check
- Embedded-timestamp sanity: does `pi_time_s` decode to a plausible date
  that matches the filename (the Pi has no battery-backed RTC — Part XVI
  §16.4 — so this is checked on every run, not assumed)
