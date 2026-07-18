# NarrowAisleBot — Documentation Index

Markdown is the source of truth here (diffs cleanly, renders on GitHub, greppable). Original `.docx`/`.pdf` files are kept in `originals/` as the source of record.

| Document | What it covers | Currency |
|---|---|---|
| [`Research_Journal.md`](Research_Journal.md) | The living project journal — vision, mechanical/electrical design, control-system debugging narrative, hurdles catalogue, autonomy roadmap, ESP32 firmware deep-dive, LiDAR/SLAM bringup (Part XIII), infrastructure & repo history (Part XIV), current status (Part XV), open TODOs. **This is the primary document — keep it updated as the project progresses.** | v2.0, 8 July 2026 (most current) |
| [`Master_Reference.md`](Master_Reference.md) | Deep hardware/wiring/firmware reference — pin assignments, power architecture, PID+FF parameters, serial protocol, commissioning checklist. | v4.0, March 2026 |
| [`Mini_Prototype_Architecture.md`](Mini_Prototype_Architecture.md) | Full architecture for the small-scale ESP32 prototype — PG36M555 motors, 537.6 CPR encoders, MDD10A drivers, 80 mm wheels, BNO055, reused Pi 5 + X4 Pro, scaled asymmetric geometry, kinematics, power budget, and a right/wrong review. Companion firmware in `firmware/`, sim in `sim/wokwi/`, ROS profile in `ros2/`. | v1.0, current |
| [`LiDAR_SLAM_Bringup.md`](LiDAR_SLAM_Bringup.md) | YDLIDAR X4 Pro + slam_toolbox bringup guide — hardware gotchas, confirmed driver params, the manual 3-terminal launch sequence. | Verified 26 June 2026 |
| [`Network_SelfHosted_AP.md`](Network_SelfHosted_AP.md) | Self-hosted WiFi AP setup (`AisleBot-Pi` @ 10.42.0.1) and the ESP32's own backup AP. | Current |
| [`Setup_Manual.md`](Setup_Manual.md) | Narrative fresh-Pi setup manual. Largely superseded by the root `install.sh` one-liner — kept as historical reference. | Superseded, historical |

Where documents disagree on a fact, prefer the one with the later date — the Research Journal is generally authoritative for current project state.

## Interactive tools

Three standalone HTML tools — double-click to open, no server or internet needed. See [`tools/README.md`](tools/README.md) for details.

| Tool | What it's for |
|---|---|
| [`tools/telemetry_analyzer.html`](tools/telemetry_analyzer.html) | Load a telemetry CSV → per-motor tracking plots, error/PWM analysis, saturation and diagonal-mismatch diagnostics, multi-run comparison. |
| [`tools/mecanum_physics_guide.html`](tools/mecanum_physics_guide.html) | Interactive field guide to mecanum wheels and omnidirectional motion — live physics, inverse kinematics, wheel comparison, research-grounded limitations. |
| [`tools/mini_prototype_architecture.html`](tools/mini_prototype_architecture.html) | Interactive architecture explorer for the ESP32 prototype — live asymmetric-kinematics bench, system block diagram, BOM, power budget, pin map, and right/wrong verdict. |
