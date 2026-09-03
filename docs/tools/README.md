# Tools

Five standalone, self-contained HTML tools — no build step, no server, no internet connection required. Each is a single file with everything (styles, scripts, physics) inlined. **Download the file and double-click it** — it opens directly in your default browser and runs entirely on your machine.

| Tool | What it's for | Needs |
|---|---|---|
| [`telemetry_analyzer.html`](telemetry_analyzer.html) | Load one or more `aislebot_telemetry_logger.py` CSV runs (the 13-column `pi_time_s, {FR,FL,RR,RL}_{target,actual,pwm}` format) and get per-motor tracking plots, RMS/MAE error, PWM saturation, diagonal (FR-RL / FL-RR) mismatch, settling-time detection, and a findings panel that flags dead encoder feedback, saturation, and telemetry gaps automatically. Multi-run comparison table included. **Map tab (added 7 Aug 2026):** drop a run's `.pgm` + `.yaml` pair from `map_saver_cli` alongside its CSV — renders the occupancy grid, reports resolution/extent/coverage (occupied/free/unknown %), and flags sparse or barely-mapped runs. Pairs a run's PID performance and the map it produced in one place, no separate tool needed. | Nothing — drag files in, everything runs client-side in the browser. |
| [`run_viewer.html`](run_viewer.html) | **The whole of one drive, in one page.** Drop the `run_<stamp>_bundle.json` that `tools/run_bundle.py` writes on the Pi and get: the map with doubled walls flagged, the SLAM path and the **wheel-odometry path drawn over each other** (where they separate is where SLAM overruled the wheels), every correction event with its time and map coordinate, per-wheel commanded-vs-actual panels, wheel travel distances, and the combined verdict. A run with no odometry log — anything recorded before 26 Aug 2026 — loads and says which sections are unavailable rather than guessing. | The `_bundle.json` only. Nothing is uploaded; it all runs in the browser. |
| [`map_viewer.html`](map_viewer.html) | Opens a bare `.pgm` + `.yaml` pair from `map_saver_cli` — the one thing `telemetry_analyzer.html` cannot do, because its map dropzone only unlocks after a valid 13-column run is loaded. Pan, zoom, and read the grid's extent and coverage. Use it when you want to eyeball a map on its own; use `run_viewer.html` when you want the map judged against everything else the run recorded. | The `.pgm` and `.yaml` together. |
| [`mecanum_physics_guide.html`](mecanum_physics_guide.html) | An interactive field guide to mecanum wheels and omnidirectional motion — live force-decomposition physics, the four-wheel inverse-kinematics demo, roller-count/vibration trade-off, a wheel-type comparison (standard / omni / mecanum / ball / swerve), and a research-grounded section on why mecanum isn't more widely used, with 14 cited peer-reviewed sources. | Nothing — pure reference/teaching tool, no data to load. |
| [`mini_prototype_architecture.html`](mini_prototype_architecture.html) | The full hardware architecture for the small-scale ESP32 prototype (PG36M555 motors, ME-37 537.6 CPR encoders, MDD10A drivers, 80 mm wheels, BNO055, reused Pi 5 + X4 Pro). A live asymmetric-kinematics bench (drive vx/vy/wz and watch per-wheel speeds), system block diagram, BOM, power budget, ESP32 pin map, and a what's-right/what-to-watch verdict. Pairs with `docs/Mini_Prototype_Architecture.md`. | Nothing — pure reference, runs client-side. |

## Why these live here, not just as chat links

Chat-hosted links expire with the session or account. These files don't — once they're in the repo, they're yours forever, versioned alongside the robot's code, and rebuildable from source if anything ever needs fixing. Treat them the same as the firmware: if you improve one, commit the change.

## Opening them

- **From this repo (recommended):** clone or download the repo, then double-click any of the five files in `docs/tools/`. Any modern browser opens them instantly — Chrome, Edge, Firefox, Safari all work.
- **From GitHub, one file at a time:** open the file on GitHub → the "Raw" button → save the page (`Ctrl+S` / `Cmd+S`) → open the saved file. GitHub renders `.html` as text, not as a live page, so you do need to download it first — there's no way around that for a private repo.

## The telemetry analyzer's expected CSV

```
pi_time_s, FR_target_rads, FR_actual_rads, FR_pwm,
           FL_target_rads, FL_actual_rads, FL_pwm,
           RR_target_rads, RR_actual_rads, RR_pwm,
           RL_target_rads, RL_actual_rads, RL_pwm
```

This is exactly what `phone_dashboard.py`'s record-run feature and the ESP32's `<L1>` telemetry stream already produce (see `docs/Research_Journal.md` Part VI §6.12) — no conversion needed, just point it at a run from `~/aislebot_logs/`.


## The run pipeline, end to end

One drive is everything between tapping MAP and tapping MAP again. It leaves
four files on the Pi, and the point of the pipeline is that they get read
**together**, because the interesting findings are in the disagreements
between them.

```
        on the Pi                                    on Windows
  ┌──────────────────────┐                    ┌──────────────────────┐
  │ MAP … drive … MAP    │                    │                      │
  │   run_<stamp>.pgm    │                    │   run_viewer.html    │
  │   run_<stamp>.yaml   │   run_bundle.py    │                      │
  │   ..._pose.csv       │ ─────────────────▶ │   drop the bundle,   │
  │   ..._report.json    │   _bundle.json     │   read everything    │
  │   run_<stamp>.csv    │                    │                      │
  └──────────────────────┘                    └──────────────────────┘
        analysis runs HERE                       viewing happens here
```

**Analysis runs on the Pi**, where the data already is — `run_analyzer.py`
does the work and `run_bundle.py` packages the result. Copying four files to
Windows per run and hoping you picked up the right four is how a stale copy
gets analysed. **Viewing happens on Windows**, because that is where the big
screen is.

`run_bundle.py` refuses runs shorter than 60 s unless forced. Of the 80 maps
in `~/aislebot_logs`, most are seconds-long fragments from testing something
else — and two of them were analysed at length on 26 Aug before anyone noticed
they were 30-second bug-fix checks rather than commissioning drives. A run too
short to contain a lap cannot answer a question about a lap.
