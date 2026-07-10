# Tools

Two standalone, self-contained HTML tools — no build step, no server, no internet connection required. Each is a single file with everything (styles, scripts, physics) inlined. **Download the file and double-click it** — it opens directly in your default browser and runs entirely on your machine.

| Tool | What it's for | Needs |
|---|---|---|
| [`telemetry_analyzer.html`](telemetry_analyzer.html) | Load one or more `aislebot_telemetry_logger.py` CSV runs (the 13-column `pi_time_s, {FR,FL,RR,RL}_{target,actual,pwm}` format) and get per-motor tracking plots, RMS/MAE error, PWM saturation, diagonal (FR-RL / FL-RR) mismatch, settling-time detection, and a findings panel that flags dead encoder feedback, saturation, and telemetry gaps automatically. Multi-run comparison table included. | Nothing — drag a CSV in, everything runs client-side in the browser. |
| [`mecanum_physics_guide.html`](mecanum_physics_guide.html) | An interactive field guide to mecanum wheels and omnidirectional motion — live force-decomposition physics, the four-wheel inverse-kinematics demo, roller-count/vibration trade-off, a wheel-type comparison (standard / omni / mecanum / ball / swerve), and a research-grounded section on why mecanum isn't more widely used, with 14 cited peer-reviewed sources. | Nothing — pure reference/teaching tool, no data to load. |

## Why these live here, not just as chat links

Chat-hosted links expire with the session or account. These files don't — once they're in the repo, they're yours forever, versioned alongside the robot's code, and rebuildable from source if anything ever needs fixing. Treat them the same as the firmware: if you improve one, commit the change.

## Opening them

- **From this repo (recommended):** clone or download the repo, then just double-click `docs/tools/telemetry_analyzer.html` or `docs/tools/mecanum_physics_guide.html`. Any modern browser opens them instantly — Chrome, Edge, Firefox, Safari all work.
- **From GitHub, one file at a time:** open the file on GitHub → the "Raw" button → save the page (`Ctrl+S` / `Cmd+S`) → open the saved file. GitHub renders `.html` as text, not as a live page, so you do need to download it first — there's no way around that for a private repo.

## The telemetry analyzer's expected CSV

```
pi_time_s, FR_target_rads, FR_actual_rads, FR_pwm,
           FL_target_rads, FL_actual_rads, FL_pwm,
           RR_target_rads, RR_actual_rads, RR_pwm,
           RL_target_rads, RL_actual_rads, RL_pwm
```

This is exactly what `phone_dashboard.py`'s record-run feature and the ESP32's `<L1>` telemetry stream already produce (see `docs/Research_Journal.md` Part VI §6.12) — no conversion needed, just point it at a run from `~/aislebot_logs/`.
