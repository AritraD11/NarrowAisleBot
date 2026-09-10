# NarrowAisleBot — Knowledge Base for NotebookLM / Gemini

**What this file is.** A single dense document covering the whole project, written to sit alongside the GitHub repo as a NotebookLM source. NotebookLM's GitHub connector tends to ingest a repo shallowly — the landing page more than the file tree — so this file exists to carry the numbers, terminology, current status, and known traps a query might otherwise miss. It is a compressed index over the real sources, not a replacement for them: every section names the file(s) it was drawn from, and `docs/Research_Journal.md` (3,660 lines, entries §1–§17.57) remains the actual primary record. When this file and the journal disagree, the journal wins — this file could be stale by the time you read it.

**Provenance.** Generated 10 Sep 2026 by Claude Code, reading the repository directly (not from memory). Repo: `AritraD11/NarrowAisleBot` (private), default branch `main`.

---

## 1. What this project is

An asymmetric-wheelbase mecanum robot built to navigate warehouse aisles too narrow for a conventional (symmetric) mecanum platform. Built by Aritra Das (25D0074) at IIT Bombay, Dept. of Biosciences & Bioengineering, under Prof. Ambarish Kunwar.

The defining mechanical idea: the four mecanum wheels are **not** at the corners of a symmetric rectangle. The outer diagonal pair (FR, RL) sits farther from the robot's longitudinal centre than the inner pair (FL, RR). This "Variant 1 asymmetric layout" (from the cited IIT Bombay paper — see §11) roughly halves the effective chassis width compared to a symmetric mecanum robot with the same wheel hardware, at the cost of asymmetric inverse kinematics. Real-time motor control runs on an ESP32 (hardware-PCNT PID at 50 Hz); planning, teleop, and SLAM run on a Raspberry Pi 5 under ROS 2 Jazzy.

Long-term intent (per `docs/Vision_Indian_Market.md`): warehouse and eventually food-cart/hospitality delivery in aisle-constrained Indian settings — see that document for market framing, not repeated here.

---

## 2. Current status — read this section skeptically, then read §3

Two documents in the repo disagree about how far along the project is, and you should know both rather than trust either alone:

- **`README.md`'s phase table** (last touched 3 Sep 2026) says: Phase 1 (PID motor control) done; Phase 2 (odometry + IMU) *not started, IMU not procured*; Phase 3 (LiDAR SLAM) in progress; Phase 4 (Nav2) *not started, blocked on Phase 2*; Phase 5 not started.
- **`docs/Where_We_Stand.md`** (28–29 Aug 2026, a graded full-stack audit — see its own evidence-grade legend in §0) says wheel odometry is **measured, exact, and working** without an IMU (layers 1–5 all ✅), Nav2's planner and MPPI controller are **working** (layers 9–10), and the dashboard's click-to-goal is exact to 1e-6. The one broken layer is layer 6, `map→odom` (the SLAM front end), which was actively corrupting an otherwise-good odometry estimate.

**Resolution, as of the journal's latest entry (§17.57, 3 Sep 2026, "Stage G closes"):** the SLAM front-end corruption was worked around, not fixed at the root, by setting `use_scan_matching: false` in the SLAM config — this removes `map→odom` correction entirely. Two independent hardware drives confirmed **zero correction events** under that setting. A second finding fell out of the same investigation: **the odometry itself invents heading it did not physically accumulate** (the "phantom yaw" result, §17.55–§17.56), on the same order as the drift the project had spent months blaming on physical wheel slip. This is a new, still-open finding, not yet root-caused.

**What Stage G did not reach:** a scored G4 (a real closed-loop navigation drive meeting the acceptance gate in `Where_We_Stand.md` §8 / journal Appendix B.7: `map_integrity.py` verdict not `FOLDED`, doubled walls <1.0%, unknown <50%, return-to-mark <0.15 m). Whether `use_scan_matching: false` also silently disables pose-graph construction (which would make loop closure inert) was flagged as the first question for the next session and, per the branch table below, is `claude/amr-and-slam`'s explicit scope.

**Bottom line for anyone querying this corpus:** treat the README phase table as *aspirational/outdated framing*, and `Where_We_Stand.md` + journal §17.4x–§17.57 as the *actual, evidence-graded state*. Neither the IMU nor a LiDAR upgrade is the current bottleneck; the SLAM front end and the phantom-yaw odometry bug are.

---

## 3. Hardware — bill of materials and specs

Source: `README.md` "Hardware" table, `docs/Master_Reference.md` §2–§2.5, cross-checked against CAD in §7 below.

| Component | Detail |
|---|---|
| Compute | Raspberry Pi 5, Ubuntu 24.04 LTS, ROS 2 Jazzy, 8 GB RAM |
| Drive controller | ESP32-WROOM-32 (Robocraze 38-pin, CP2102 USB-UART) → `/dev/esp32` @ 921600 baud |
| Arm controller | Arduino Mega 2560 → `/dev/mega` @ 115200 baud, arm + UV-lighting firmware v8 |
| LiDAR | YDLIDAR X4 Pro → `/dev/ydlidar` @ 128000 baud, single-channel. **~430 pts/scan @ ~11.35 Hz**, measured 3 Sep 2026 — the driver's `frequency:` parameter has no effect on this unit (`support_motor_dtr: false`; the head free-runs at native speed). Max range 10 m (note: `system/slam_nodom.yaml` still has a stale `max_laser_range: 12.0` inherited from an originally-planned RPLiDAR A1 — known, not yet fixed) |
| Drive motors ×4 | Rhino RMCS-2086 — planetary geared DC, 24 V, 60 RPM rated, 1:47 gear ratio, 500-line optical quadrature encoder (2000 PPR at base shaft ×4 quadrature → **93,132 CPR at the wheel**), 160 kgcm rated torque / 380 kgcm stall, 12 mm shaft, 1.9 kg each |
| **Front encoders (FR, FL) — REPLACED** | The integrated RMCS-2086 encoders on the two front motors failed. Front motors now use **GTK08** encoder units instead. Their A/B wire colours differ from the rear (RMCS-2086) encoders — see the warning table in §5 below. Source: `docs/RMCS-2086_Encoder_Replacement.md`, `docs/Bench_Test_Map.md` |
| Motor drivers ×2 | Cytron MDD20A, 20 A continuous, 6–30 V, PWM+DIR, logic threshold 1.5 V (accepts ESP32's 3.3 V logic directly, no level shifting) |
| Wheels ×4 | DekuPro 6-inch SR Mecanum, outer diameter 152.4 mm (radius 76.2 mm = 0.0762 m), 10–12 rollers at 45°, AndyMark-equivalent part `am-3479`, max load 90 kg/wheel |
| Level shifter | **Deployed hardware is an 8-channel discrete-MOSFET (BSS138-style) board** — no OE pin, LV+/LV−/HV+/HV− rails, per-channel LEDs. Replaces an earlier TXS0108E IC design (retired 4 Aug 2026 after repeated interface failures). `docs/Master_Reference.md` §4.3/§4.4 still describe the *retired* TXS0108E wiring and are explicitly flagged in the doc as superseded — don't wire from those sections. Current wiring: `docs/Bench_Test_Map.md` "Full 8-channel wiring" |
| Battery | SM12830SL LiFePO4, 12.8 V, 30 Ah, 384 Wh |
| Power relay | SSR-50DD solid-state relay, 50 A, 3–32 V trigger |
| Boost converter | 1200 W DC-DC, 12.8 V → 24 V (motor rail) |
| Buck converter | DFRobot 60 W, 12.8 V → 5 V (encoder + level-shifter HV rail) |
| Arm | 2× NEMA23 (TB6600 drivers) + 1× NEMA34 linear (BH-MSD-6A-W) + 3-tube staged UV lighting, firmware v8 |
| Sensors | YDLIDAR X4 Pro (live); BNO055 IMU (planned, not yet procured — Phase 2 in the README framing, but see §2 above on what that framing does and doesn't mean); 16×2 I2C LCD |

**Kinematic geometry** (ground truth, sourced from CAD — see §7 for exactly how each was confirmed):

| Symbol | Meaning | Value |
|---|---|---|
| L | Chassis plate length | 1000 mm |
| W | Chassis plate width | 250 mm |
| l₁ | Outer-wheel (FR, RL) longitudinal distance from centre | 403 mm |
| l₂ | Inner-wheel (FL, RR) longitudinal distance from centre | 333 mm |
| l₁ − l₂ | Asymmetry offset — the whole point of the design | 70 mm |
| d | Half track width (lateral offset of all 4 wheel centres from centreline) | 157.69 mm |
| a | Wheel radius | 76.2 mm |
| K_outer | = l₁ + d, used directly in the IK | 0.5607 m |
| K_inner | = l₂ + d, used directly in the IK | 0.4907 m |

**A documentation trap worth knowing about:** `docs/Master_Reference.md` §2.2's ASCII top-view diagram labels 250 mm as "track (2d)". It is not — 2d = 2 × 157.69 = 315.38 mm. The 250 mm figure is the bare plate width; the wheels stand ~32.7 mm proud of each plate edge. Both numbers are individually correct, the diagram's caption conflates them. Confirmed from the DXF export, not just inferred (§7).

**Known firmware corrections (v4.0), from `docs/Master_Reference.md` §5:** the ESP32 WiFi-joystick path previously used `WHEEL_RADIUS = 0.05` instead of the correct 0.0762 m — a 52% velocity-scaling error affecting every phone-joystick command (serial commands from ROS 2 bypass this IK path and were never affected). Fixed in v4.0.

---

## 4. Electronics wiring / circuit diagram

A full deployed-electronics circuit diagram exists in the repo: `docs/hardware/nab_circuit_diagram.svg` (+ `.png` render), generated by `docs/hardware/circuit_diagram.py` from the wiring tables in `Master_Reference.md` §4 and `Bench_Test_Map.md`. It covers power distribution (battery → SSR → boost/buck), compute & command (Pi, ESP32, LiDAR, Mega), and drive/odometry feedback (drivers, motors, level shifter, encoders), colour-coded by voltage domain (12.8 V / 24 V / 5 V / 3.3 V / USB-serial / encoder-A-B).

**ESP32 GPIO map** (Master_Reference.md §4.1–§4.2, firmware v4.0 uses zero strapping pins):

| Motor | PWM GPIO | DIR GPIO |
|---|---|---|
| FR | G4 | G16 |
| FL | G17 | G18 |
| RR | G19 | G21 |
| RL | G22 | G23 |

**Encoder channel map** (current, discrete-MOSFET shifter — `Bench_Test_Map.md` "Full 8-channel wiring"):

| Motor | A/B wire colour | 5 V side | 3.3 V side | ESP32 GPIO | PCNT unit | Dir sign |
|---|---|---|---|---|---|---|
| FR | Green/White | H0/H1 | L0/L1 | 36/39 | PCNT_0 | −1 |
| FL | Green/White | H2/H3 | L2/L3 | 34/35 | PCNT_1 | +1 |
| RR | Yellow/Green | H4/H5 | L4/L5 | 32/33 | PCNT_2 | −1 |
| RL | Yellow/Green | H6/H7 | L6/L7 | 25/26 | PCNT_3 | +1 |

**Wiring trap, explicitly flagged in `Bench_Test_Map.md`:** the front (GTK08) and rear (RMCS-2086) encoders use *different* A/B wire-colour conventions (Green=A/White=B on front vs Yellow=A/Green=B on rear). This exact mix-up already corrupted a channel once in this project. Verify against the physical wire, never from memory or from a table alone.

**Deployment note carried into the diagram:** powering the ESP32 from the Pi's USB couples SMPS switching noise and PWM ground transients into the encoder counts. For bench work use a powerbank; for deployment, cut VBUS in the Pi→ESP32 cable and feed the ESP32's VIN from the 5 V buck converter directly.

**Ground bus:** ESP32 GND, boost GND, buck GND, both MDD20A logic GND, shifter LV−/HV−, and all 4 encoder Black wires must all share one rail. Missing any one connection produces phantom motor behaviour (`Master_Reference.md` §3.2).

---

## 5. Firmware

Two `.ino` files live at the repo root (not in a subfolder — see repo map in §9):

| File | Target | Baud |
|---|---|---|
| `aislebot_esp32.ino` | ESP32-WROOM-32, drive control | 921600 |
| `aislebot_arm.ino` | Arduino Mega 2560, arm + UV lighting (v8) | 115200 |

PID gains (current): Kp=50, Ki=30, Kd=3, feedforward (Kff) calibrated in air, ground recalibration still pending per the README phase table (though see §2 on how stale that framing may be relative to the journal).

`firmware/` (repo subfolder) holds bench-diagnostic ESP32/Mega sketches, not the production firmware: encoder isolation tests, level-shifter tests, hand-turn diagnostics, a "mini" prototype sketch. `past_iterations/firmware/` holds superseded production firmware from earlier in the project.

---

## 6. Software architecture (ROS 2, on the Pi)

Two ROS 2 packages under `src/`, plus one plain script package:

**`src/mecanum_robot/`** — the core drive/teleop package.
- Nodes: `esp32_bridge.py` (serial bridge to ESP32), `arm_bridge.py` (serial bridge to Mega), `mecanum_teleop_asymmetric.py` (the *correct* asymmetric-mecanum inverse kinematics — always used the right l₁/l₂/d parameters, unlike the ESP32's own WiFi-joystick IK which had the WHEEL_RADIUS bug in §3), `odometry_publisher.py`, `phone_dashboard.py` (web dashboard + click-to-goal, WebSocket has no server→client broadcast path yet — a known gap, see §8), `joy_to_aislebot.py`, `keyboard_teleop.py`, `lcd_display.py`, `gazebo_bridge.py`, `run_report.py`.
- Launch files: `aislebot_full.launch.py` (primary), `mapping_full.launch.py`, `sensors.launch.py`, `simulation.launch.py`.
- `urdf/aislebot.urdf` — note this uses a **non-standard base_link convention**: +X = right, +Y = forward (the reverse of REP-103), a deliberate consequence of an odometry fix (journal §17.10) that every x/y-labelled Nav2 parameter had to be swapped to match.

**`src/mecanum_navigation/`** — Nav2/SLAM integration.
- Nodes: `cmd_vel_axis_adapter.py`, `goal_pose_adapter.py`.
- Launch files: `slam.launch.py`, `navigation.launch.py`, `nav2_slam.launch.py`.
- `config/`: `ekf_params.yaml`, `nav2_params.yaml`, `slam_params.yaml` — but the config **actually live on the robot** is `system/slam_nodom.yaml` (and `slam_nodom_stageB.yaml`), not the vendored `slam_params.yaml`.

**`src/scan_relay/scan_relay.py`** — a plain script (no ROS build), republishes `/scan` (best-effort) as `/scan_reliable`, and applies the self-occlusion angular mask (see §8).

**`tools/`** — a substantial offline analysis toolkit built up over the debugging saga: `wheel_forensics.py` (re-integrates odometry offline from raw encoders), `graph_residuals.py` (watches SLAM pose-graph node movement, the instrument that proved loop closure wasn't the cause of the "jumps"), `run_analyzer.py`, `map_integrity.py` (grades a saved map FOLDED/pass), `bag_tf_diff.py` (built to split `map→odom` from `odom→base_link` across a jump event — designed in §17.29, still never run as of the journal's end), `zero_point_scan.py`, `scan_bearing.py`, `scan_quality.py`, `repeatability_test.py`, `trajectory_viz.py`, `verify_axis_chain.py`, `pi_audit.sh`/`pi_clean.sh`. See `tools/README.md`.

**`data/`** — `bench_logs/` (ground + bench PID telemetry, with pre-generated analysis PNGs under each run's `analysis/` folder) and `field_runs/` (dated full-drive logs, e.g. `run_20260831`, `run_20260901`).

---

## 7. CAD — what's exact, what's estimated, what's still missing

Full detail: `cad/README.md` and `cad/extracted_geometry.md`. Summary:

**In the git repo** (`cad/`): the SolidWorks base-platform assembly (`AislebotBasePlatform_SteelChasis.SLDASM`), two wheel assemblies (native `.SLDASM` + neutral `.STEP`), the motor part (`.SLDPRT`), one real SolidWorks top-view render (`AislebotBasePlatform_SteelChasis.JPG`), and a dimensioned version of that render (`cad/renders/chassis_top_dimensioned.png`, built by `cad/annotate_chassis.py`).

**`.SLDASM`/`.SLDPRT`/`.SLDDRW` are proprietary SolidWorks binaries** — nothing but SolidWorks or eDrawings opens them; they exist in the repo as source-of-record files, not as something this analysis pipeline can read directly.

**What is exact, not estimated**, pulled directly from DXF exports (plain-text format, machine-parsed): the base platform is a flat 1000×250 mm rectangle with **no fillets, no cutouts**; its 12 wheel-mount holes independently confirm l₁=403 mm and l₂=333 mm and the 70 mm asymmetry (visible directly in the hole-pair spacing); the top plate is 300×250 mm with R10 corners and a waist cutout. Also exact: a `SteelChasisBreadthRodMiddle` STL part measures 40×244×68 mm — the **68 mm figure is the only known measurement of chassis frame height**, not recorded anywhere else in the repo.

**Still unknown / not in the repo:** plate thickness, steel gauge, and bracket standoff height (a flat DXF outline carries no third-dimension information for these). The `.SLDDRW` dimensioned drawing sheets that would answer this exist in the project's Google Drive (`Aislebot_Assembly` folder) but have not been exported to a form this pipeline can read (PDF or DXF) or committed to git as of this writing.

**A methodology note worth preserving:** dimension callouts on `cad/renders/chassis_top_dimensioned.png` were placed by pixel-measuring the actual render (luminance thresholding), not eyeballed — the four wheel-centre pixel positions recovered that way matched the CAD-predicted positions to under half a pixel, which is what validates that the render is to scale and the callouts are trustworthy.

---

## 8. The SLAM/Nav2 debugging saga — a compressed timeline

This is the single longest thread in `docs/Research_Journal.md` (roughly §17.1 through §17.57) and the part most likely to need real narrative detail beyond this summary — go to the journal directly for anything below this doesn't answer.

- **Self-occlusion / blind sector**: the robot's own chassis blocks ~90° of the LiDAR sweep (measured, refined from an initial ~120° estimate), masked in `scan_relay.py`.
- **Axis convention bug**: `base_link` ended up with a non-standard +X=right/+Y=forward convention after an odometry fix, requiring every Nav2 x/y parameter to be swapped to match (§17.10).
- **Footprint bug**: Nav2's costmap footprint was set smaller than the real robot (a collision bug, not a conservative margin) until tape-measured and corrected to 1.12×0.48 m (§17.7-adjacent).
- **First Nav2 hardware launch** (§17.17): reached with two real bringup bugs found and fixed along the way.
- **The "jumps" investigation** (§17.25 onward): repeated large pose jumps during autonomous drives, eventually isolated to the SLAM **front end** (scan matching), not loop closure — proven by two independent instruments (`graph_residuals.py` showing zero pose-graph node movement across closures, `run_analyzer.py` showing correction events consistent with `map→odom` moving while `odom→base_link` stayed smooth) and confirmed a third way by successfully predicting that shrinking the scan-matcher's search window would shrink the jump magnitude, then producing that result on command (§17.40–§17.43).
- **`Where_We_Stand.md`** (28–29 Aug): the full graded audit — see §2 above.
- **Stage G** (early Sep, §17.50–§17.57): `use_scan_matching: false` deployed, confirmed on two drives to fully suppress the front-end corruption, **merged to `main`**. Discovered along the way: the odometry itself fabricates yaw it never physically accumulated ("phantom yaw"), an open, separately-tracked issue.
- **What's unresolved going forward** (journal Appendix B.7/B.8, and the branch table in §10): whether disabling scan matching also disables pose-graph construction/loop-closure entirely; the phantom-yaw root cause; no commissioning map has ever passed all four acceptance-gate criteria at once.

**Known, currently-inert bugs** (don't re-discover these): `phone_dashboard.py`'s WebSocket has no server→client broadcast path (tracked, not yet built); `src/mecanum_robot/resource/dashboard.html` is dead code, superseded by an inline HTML string in `phone_dashboard.py`; `joy_to_aislebot.py` publishes `/cmd_vel` on idle-gamepad zeros (harmless only because no gamepad is currently attached); `amcl.robot_model_type` in `nav2_params.yaml` may need to be the Jazzy pluginlib class name rather than the pre-Galactic bare string — never actually tested, since the whole `amcl` block has never run.

---

## 9. Repo map

```
NarrowAisleBot/
├── README.md                    ← start here; phase table is dated, see §2 above
├── NAB_KNOWLEDGE_BASE.md         ← this file
├── aislebot_esp32.ino            ← production ESP32 firmware (drive)
├── aislebot_arm.ino              ← production Mega firmware (arm + UV)
├── install.sh                    ← one-shot Pi setup script
│
├── docs/                         ← ~30 markdown docs; docs/README.md is the index
│   ├── Research_Journal.md       ← THE primary record, §1–§17.57, read this for narrative
│   ├── Master_Reference.md       ← hardware/wiring/firmware deep reference (§4.3/4.4 partly retired, see §4 above)
│   ├── Where_We_Stand.md         ← graded full-stack audit, 28-29 Aug 2026
│   ├── Hardware_Roadmap.md       ← planning only: IMU, collision ring, charging dock, battery %
│   ├── Bench_Test_Map.md         ← current (non-retired) wiring tables
│   ├── RMCS-2086_Encoder_Replacement.md
│   ├── LiDAR_SLAM_Bringup.md, Navigation_Theory.md, SLAM_Theory.md, Dashboard_Map_System.md
│   ├── Vision_Indian_Market.md   ← market/business framing
│   ├── Production_Architecture.md, Adaptive_Control_Roadmap.md, Autonomy_Endgame.md
│   ├── hardware/                 ← circuit_diagram.py + generated SVG/PNG, lab photos
│   ├── robot_photos/             ← dated hardware-trial photo sets
│   ├── evidence/, originals/ (.docx/.pdf source-of-record), tools/ (standalone HTML tools)
│
├── cad/                          ← SolidWorks source + extracted geometry, see §7 above
│   ├── chassis/, wheels/, motor/ ← native .SLDASM/.SLDPRT + neutral .STEP
│   ├── renders/                  ← dimensioned PNG figures
│   ├── extracted_geometry.md     ← exact numbers pulled from DXF, with provenance
│   └── annotate_chassis.py       ← the pixel-measurement dimensioning script
│
├── src/                          ← ROS 2 workspace, see §6 above
│   ├── mecanum_robot/, mecanum_navigation/, scan_relay/
│
├── system/                       ← mirrors what's actually deployed on the Pi
│   ├── slam_nodom.yaml           ← the SLAM config actually in use (not src/…/slam_params.yaml)
│   ├── 99-aislebot.rules, aislebot.service, start_aislebot.sh, ydlidar_params.yaml
│
├── firmware/                     ← bench-diagnostic .ino sketches (not production)
├── tools/                        ← offline analysis scripts, see §6 above
├── data/                         ← bench_logs/, field_runs/ — real telemetry + pre-rendered plots
├── research_articles/            ← cited literature
├── past_iterations/              ← superseded firmware/launch/ros2_nodes from earlier project phases
├── sim/                          ← Gazebo/Wokwi simulation assets
└── ros2/                         ← (see repo for current contents)
```

---

## 10. Branches (as of 10 Sep 2026 — this changes; check GitHub for current truth)

| Branch | Scope |
|---|---|
| `main` | Default, stable baseline, current through Stage G + this session's CAD/circuit-diagram work |
| `claude/aps-report-draft-2nywbq` | The year-1 APS report draft, figures, regeneration scripts — independent of robot-control work |
| `claude/amr-and-slam` | Scoped to closing the G4 gate: a real loop-closing perimeter drive, and confirming whether loop closure fires at all under `use_scan_matching: false` |

Branches already fully merged into `main` and deleted: `claude/narrowaislebot-mapping-reliability-038ike`, `claude/narrowaislebot-goal-obstacle-avoidance-f2t3aa`, `claude/autonomous-vehicle-hardware-btgtga`, `claude/nab-charging-safety-hardware` (superseded before landing any unique work), `AritraD11-patch-1` (this session's CAD/circuit-diagram branch, merged via PR #13).

---

## 11. Glossary / symbols

| Term | Meaning |
|---|---|
| NAB | NarrowAisleBot, the project's own shorthand for itself throughout the journal |
| l₁, l₂, d, a | See the kinematic geometry table in §3 |
| K_outer, K_inner | l₁+d and l₂+d — the coefficients the asymmetric IK actually multiplies angular velocity by |
| FR/FL/RR/RL | Front-right / front-left / rear-right / rear-left, the four wheel positions |
| PCNT | ESP32's hardware pulse-counter peripheral, used for full-quadrature encoder reading |
| CPR | Counts per revolution (at the wheel, after gearing) |
| Kp/Ki/Kd/Kff | PID + feedforward gains for the per-wheel velocity controller |
| `map→odom`, `odom→base_link` | The two halves of the standard ROS TF chain; SLAM corrects the former, wheel odometry integrates the latter — central to the whole debugging saga in §8 |
| Phantom yaw | The odometry-fabricates-heading-it-never-accumulated bug found in §17.55–56, unresolved |
| G4 | The project's own name for its loop-closure/commissioning acceptance gate (see Appendix B.7 in the journal) |
| Stage A–G | Sequential named SLAM-tuning experiments/config changes, chronicled across journal §17.32 onward |
| MPPI | Model Predictive Path Integral, the Nav2 local controller in use (replaced DWB, §17.23) |

---

## 12. If you (NotebookLM / Gemini) are asked something this file doesn't cover

Go to `docs/Research_Journal.md` first — it is the authoritative, dated, entry-numbered narrative that this file compresses. For hardware/wiring specifics not in §3–§4 above, check `docs/Master_Reference.md` (mind the retired §4.3/§4.4 caveat) and `docs/Bench_Test_Map.md`. For anything about the SLAM debugging history beyond §8's summary, the journal's §17.x entries and `docs/Where_We_Stand.md` are the sources — do not guess at technical claims from this file's compressed language; when in doubt, say the underlying document should be checked rather than asserting confidently from this summary alone.
