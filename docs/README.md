# NarrowAisleBot — Documentation Index

Markdown is the source of truth here (diffs cleanly, renders on GitHub, greppable). Original `.docx`/`.pdf` files are kept in `originals/` as the source of record.


## ⭐ Start here — the 28 Aug 2026 strategic package

Four documents written together as one package. Read them in this order.

| # | Document | What it answers |
|---|---|---|
| 1 | [`Where_We_Stand.md`](Where_We_Stand.md) | **Where does the project actually stand?** A full-stack audit with an evidence grade on every claim — measured / measured-once / hypothesis / retracted / never-run. Layer-by-layer state, what is confirmed about the SLAM break, what must be re-confirmed, and what is holding the project. |
| 2 | [`Autonomy_Endgame.md`](Autonomy_Endgame.md) | **How do we get to "tap a point, it drives there"?** The full autonomy chain link by link, why a saved map + AMCL is the mechanism rather than an optimisation, seven numbered gates, and a day-by-day plan to Saturday 5 Sept with exact commands and a fallback ladder. |
| 3 | [`StageG_Deploy.md`](StageG_Deploy.md) | **What is deployed right now, and what it is expected to do.** The 3 Sep input-side change — six values, the first ever made upstream of the scan matcher — with the deploy recipe, per-file hashes, the live-node verification, the drive procedure, and every prediction registered **before** the drive (including the one expected to go the wrong way, and the result that would falsify the whole model). Read this before touching the robot. |
| 4 | [`Hardware_Roadmap.md`](Hardware_Roadmap.md) | **Planning, nothing installed.** The IMU/optical-flow/collision-ring/E-stop list argued out in chat during the Stage G session, written down before it is lost, plus three new subsystems researched from scratch: battery % (reusing the same INA226 already on the list, since a LiFePO4 flat discharge curve makes plain voltage-to-percent genuinely wrong), autonomous charging docks (pogo-pin contacts, IR alignment, why the charger lives in the dock not the robot), and a 360°/~1 m collision ring (ToF over ultrasonic, and why — with the existing `RangeSensorLayer`/`collision_monitor` integration point, not a new one). No code, no parts bought — read before ordering anything. |
| 3 | [`APS_Study_Guide.md`](APS_Study_Guide.md) | **What do I need to know for the review?** The numbers to memorise, full derivations (including the slip residual and why it is the disagreement between two independent yaw estimates), SLAM front end vs back end, costmaps, MPPI, AMCL, and a tiered question bank with answers. |
| 4 | [`Vision_Indian_Market.md`](Vision_Indian_Market.md) | **Where does this go commercially?** The narrow-aisle thesis, why labour-arbitrage pitches fail in India, who pays, the wedge, what is actually defensible, the honest kill-risks, and the numbers that must be sourced before citing any of it. |

---

| Document | What it covers | Currency |
|---|---|---|
| [`Research_Journal.md`](Research_Journal.md) | The living project journal — vision, mechanical/electrical design, control-system debugging narrative, hurdles catalogue, autonomy roadmap, ESP32 firmware deep-dive, LiDAR/SLAM bringup (Part XIII), infrastructure & repo history (Part XIV), current status (Part XV), open TODOs. **This is the primary document — keep it updated as the project progresses.** | v2.0, 8 July 2026 (most current) |
| [`Master_Reference.md`](Master_Reference.md) | Deep hardware/wiring/firmware reference — pin assignments, power architecture, PID+FF parameters, serial protocol, commissioning checklist. | v4.0, March 2026 |
| [`Mini_Prototype_Architecture.md`](Mini_Prototype_Architecture.md) | Full architecture for the small-scale ESP32 prototype — PG36M555 motors, 537.6 CPR encoders, MDD10A/SmartElex 13D drivers, 80–100 mm wheels, BNO055, reused Pi 5 + X4 Pro, scaled asymmetric geometry, kinematics, power budget (incl. PDB-XT60 / 4S-battery notes), and a right/wrong review. Companion firmware in `firmware/`, sim in `sim/wokwi/`, ROS profile in `ros2/`. | v1.0, current |
| [`PID_Calibration.md`](PID_Calibration.md) | **Calibration record for firmware v3.0** — the source data behind every gain in `aislebot_esp32.ino`, the two-term feedforward fit, why `Ki` went from 30 to 250, the one gain still estimated (`Kp`, because plant τ is unmeasured), and the three bench runs that would finish the job. Read this before changing any gain. | v3.0, 4 Aug 2026 (air-calibrated) |
| [`Adaptive_Control_Roadmap.md`](Adaptive_Control_Roadmap.md) | **Where the control architecture goes after static calibration** — Scite-verified citation check on two external research documents (one citation's claims didn't match its paper — see §1), the case for RLS/disturbance-observer adaptation over live PID retuning, why ML isn't the right tool for the wheel-control loop, and a staged roadmap (RLS on the ESP32 → disturbance observer → the already-planned `robot_localization` EKF) sequenced against what's actually been measured on this robot. Read before deciding what to build after Stage 0 (static ground calibration) finishes. | v1.0, 7 Aug 2026 |
| [`Bench_Test_Map.md`](Bench_Test_Map.md) | **RESOLVED 4 Aug 2026** — breadboard bench test that isolated the encoder feedback fault. All 4 encoders + all 8 level-shifter channels confirmed healthy; root cause was a FR/FL wiring cross-connection, not the shifter or any encoder. Kept as the diagnostic record and method reference. | v2.0, resolved |
| [`LevelShifter_Wiring.md`](LevelShifter_Wiring.md) | **RETIRED 4 Aug 2026** — TXS0108E wiring (both boards, power rails, OE), superseded by the single 8-channel discrete MOSFET board (`Bench_Test_Map.md`). Kept for the still-applicable principles: signal direction, common ground, and the GTK08-vs-RMCS wire-colour difference (§5). | v1.0, retired |
| [`RMCS-2086_Encoder_Replacement.md`](RMCS-2086_Encoder_Replacement.md) | The NAB's current blocker — dead front-motor encoders. Identifies the exact encoder (500-line optical, 5 V, ~93,132 CPR), a free-first diagnostic path, and ranked India-market replacement options (new RMCS-2086 vs AS5047P magnetic retrofit vs output-shaft encoder), with firmware impact. | v1.0, current |
| [`LiDAR_SLAM_Bringup.md`](LiDAR_SLAM_Bringup.md) | YDLIDAR X4 Pro + slam_toolbox bringup guide — hardware gotchas, confirmed driver params, the manual 3-terminal launch sequence. | Verified 26 June 2026 |
| [`Network_SelfHosted_AP.md`](Network_SelfHosted_AP.md) | Self-hosted WiFi AP setup (`AisleBot-Pi` @ 10.42.0.1) and the ESP32's own backup AP. | Current |
| [`Setup_Manual.md`](Setup_Manual.md) | Narrative fresh-Pi setup manual. Largely superseded by the root `install.sh` one-liner — kept as historical reference. | Superseded, historical |
| [`Axis_Convention.md`](Axis_Convention.md) | **The one authoritative reference for `+X`/`+Y` on this robot.** `+X=right,+Y=forward` — and since §17.38 that holds for `odom` and `map` too, not just `base_link`, so forward drive increases map `Y`. Lists the two remaining conversion points and a hop-by-hop trace from keypress to display. Read this before touching anything axis-related, and before trusting any axis fix from outside this repo. Executable companion: `tools/verify_axis_chain.py`. | v2.0, 27 Aug 2026 |
| [`evidence/axis_frame_fix/`](evidence/axis_frame_fix/) | **Hardware video evidence for the map-frame rotation and its fix** (§17.38–§17.39). Two side-by-side recordings — physical robot left, live map right — one showing the fault (`W` increasing map `X`), one showing the corrected W→D→S→A square. The second also captures a ~31 cm loop-closure pose jump, which is a separate and still-open problem. See the folder README. | v1.0, 27 Aug 2026 |

Where documents disagree on a fact, prefer the one with the later date — the Research Journal is generally authoritative for current project state.

## Interactive tools

Three standalone HTML tools — double-click to open, no server or internet needed. See [`tools/README.md`](tools/README.md) for details.

| Tool | What it's for |
|---|---|
| [`tools/telemetry_analyzer.html`](tools/telemetry_analyzer.html) | Load a telemetry CSV → per-motor tracking plots, error/PWM analysis, saturation and diagonal-mismatch diagnostics, multi-run comparison. |
| [`tools/mecanum_physics_guide.html`](tools/mecanum_physics_guide.html) | Interactive field guide to mecanum wheels and omnidirectional motion — live physics, inverse kinematics, wheel comparison, research-grounded limitations. |
| [`tools/mini_prototype_architecture.html`](tools/mini_prototype_architecture.html) | Interactive architecture explorer for the ESP32 prototype — live asymmetric-kinematics bench, system block diagram, BOM, power budget, pin map, and right/wrong verdict. |
