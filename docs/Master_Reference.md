> Converted from `AisleBot_Master_Doc.docx` (v4.0, March 2026). Original preserved at `docs/originals/AisleBot_Master_Doc.docx`. Note: the Research Journal (`Research_Journal.md`) is dated later (9 June 2026) and is the more current source where the two disagree — this document is the deeper hardware/wiring/firmware reference.

**AisleBot**

Asymmetric Omnidirectional Warehouse Robot

*Master Reference Document — Version 4.0*

**Aritra Das (Roll No. 25D0074)**

Department of Biosciences and Bioengineering

Indian Institute of Technology Bombay

*Supervisor: Prof. Ambarish Kunwar*

March 2026

Supersedes:

Aislebot_Complete_System_Architecture_v2.docx \| AisleBot_ESP32_Complete_Manual_v2.docx

AisleBot_ESP32_Wiring_Guide.docx \| AisleBot_Autonomy_Roadmap.md

**1. Project Overview & Research Vision**

AisleBot is an asymmetric mecanum-wheeled omnidirectional mobile robot designed for autonomous navigation in narrow-aisle environments — airplane cabins, railway coaches, and congested warehouses. Its defining novelty is the non-collinear, asymmetric wheel placement: the two outer wheels (FR, RL) are positioned further from the robot centre than the two inner wheels (FL, RR). This reduces the robot's overall width to approximately half that of a conventional mecanum robot with collinear wheels, enabling access to aisles that would otherwise be too narrow for motorised platforms.

The project is structured in five sequential phases: Phase 1 — closed-loop PID motor control (current); Phase 2 — odometry and IMU-fused state estimation; Phase 3 — LiDAR SLAM; Phase 4 — Nav2 autonomous path planning; Phase 5 — warehouse-specific adaptive intelligence.

**⚠ This document reflects the corrected system. Two firmware-level errors discovered in March 2026 are documented in Section 5 with exact fixes. All firmware written before v4.0 of this document used incorrect kinematics for the WiFi joystick path.**

**1.1 Current System State (March 2026)**

Phase 1 is complete in software and under hardware validation. The ESP32 has replaced the Arduino Mega as the motor controller. The ROS2 stack on the Raspberry Pi 5 sends wheel velocity commands over USB serial. The phone WiFi joystick provides manual override. All four motors are responding. Ground testing with telemetry logging is the immediate next step.

|                    |                                                                                              |
|--------------------|----------------------------------------------------------------------------------------------|
| **Component**      | **Current Status**                                                                           |
| **Motor hardware** | ESP32 PID, 4× Rhino RMCS-2086, Cytron MDD20A × 2                                             |
| **Compute**        | Raspberry Pi 5, Ubuntu 24.04, ROS2 Jazzy                                                     |
| **Control mode**   | WiFi phone joystick (primary) + ROS2 serial (secondary)                                      |
| **Telemetry**      | ESP32 CSV → Pi aislebot_telemetry_logger.py → .xlsx/.csv                                     |
| **PID status**     | Kp=50, Ki=30, Kd=3 \| Kff calibrated in air — ground recalibration pending                   |
| **Known issues**   | RL wheel partial ground contact, E-STOP 50ms auto-clear bug, WiFi IK firmware error (see §5) |

**2. Hardware Specifications**

**2.1 Chassis & Geometry**

AisleBot uses the Variant 1 asymmetric layout from the IIT Bombay paper, with outer wheels at the longitudinal extremes and inner wheels offset inward. The asymmetry offset of 70 mm is the key differentiator — this is what constrains robot width.

|                                         |            |            |          |
|-----------------------------------------|------------|------------|----------|
| **Parameter**                           | **Symbol** | **Value**  | **Unit** |
| Chassis length                          | —          | **1000**   | mm       |
| Chassis width                           | —          | **250**    | mm       |
| Total mass                              | m          | **45.54**  | kg       |
| Outer wheel longitudinal dist. (FR, RL) | **l₁**     | **403**    | mm       |
| Inner wheel longitudinal dist. (FL, RR) | **l₂**     | **333**    | mm       |
| Half track width (all wheels)           | **d**      | **157.69** | mm       |
| Asymmetry offset                        | l₁ − l₂    | **70**     | mm       |
| Wheel radius                            | **a**      | **76.2**   | mm       |
| Max wheel speed                         | ω_max      | **6.28**   | rad/s    |
| Max robot linear speed                  | v_max      | **0.48**   | m/s      |

ℹ l₁, l₂, d and wheel radius a are sourced from the SolidWorks URDF model and are the ground-truth values for all kinematics. Do not change without re-measuring the physical robot.

**2.2 Wheel Layout (Top View)**

FRONT FL (inner) FR (outer) l₂ = 333 mm l₁ = 403 mm ╔═══════════════════╗ ║ ║ ║ CHASSIS ║ 1000 mm ║ ║ ╚═══════════════════╝ RL (outer) RR (inner) l₁ = 403 mm l₂ = 333 mm REAR \|←——— 250 mm track (2d) ———→\|

**2.3 Motors — Rhino RMCS-2086**

|                                        |                             |                             |
|----------------------------------------|-----------------------------|-----------------------------|
| **Parameter**                          | **Value**                   | **Notes**                   |
| **Model**                              | Rhino RMCS-2086             | Planetary geared DC         |
| **Operating voltage**                  | 24V DC                      | From boost converter        |
| **Rated output speed**                 | 60 RPM                      | = 6.28 rad/s                |
| **Gear ratio**                         | 1:47                        | Motor shaft to output shaft |
| **Base motor no-load speed**           | 2800 RPM                    |                             |
| **Rated torque**                       | 160 kg·cm                   | 1.57 N·m                    |
| **Stall torque**                       | 380 kg·cm                   | 3.73 N·m                    |
| **No-load current**                    | 1.12 A                      |                             |
| **Stall current**                      | Up to 30 A                  | Why 50A SSR relay is used   |
| **Encoder type**                       | 500-line optical quadrature |                             |
| **CPR — full quadrature (ESP32 PCNT)** | **93,132**                  | 500 × 4 × 47                |
| CPR — CHANGE mode (old Arduino)        | 46,566                      | 500 × 2 × 47 — legacy only  |
| **Shaft diameter**                     | 12 mm                       |                             |
| **Motor weight**                       | 1.9 kg                      | × 4 = 7.6 kg total          |

ℹ The datasheet confirms: 'Gear ratio is 1:47. The optical encoder coupled with the base motor is a quad encoder which provides 93132 Counts per Revolution (CPR).' The ESP32 PCNT hardware counts all four edges (full quadrature), giving 2× better resolution than the Arduino CHANGE-mode ISR.

**2.4 Wheels — DekuPro 6-inch SR Mecanum**

|                                |                                                      |
|--------------------------------|------------------------------------------------------|
| **Parameter**                  | **Value**                                            |
| **Model**                      | DekuPro 6-inch SR Mecanum Wheels (dekuprobotics.com) |
| **Outer diameter**             | 152.4 mm (6 inches)                                  |
| **Wheel radius (a)**           | **76.2 mm = 0.0762 m**                               |
| **Roller count**               | 10–12 rollers at 45°                                 |
| **Equivalent AndyMark design** | am-3479                                              |
| **Max load per wheel**         | 90 kg                                                |

**⚠ WHEEL_RADIUS in the ESP32 WiFi joystick IK was 0.05 m (WRONG). Correct value is 0.0762 m. This caused a 52% velocity scaling error for all phone joystick commands. See Section 5 for the fix.**

**2.5 Electronics & Control Hardware**

|                     |                   |                                                                            |
|---------------------|-------------------|----------------------------------------------------------------------------|
| **Component**       | **Model**         | **Specification**                                                          |
| **Compute**         | Raspberry Pi 5    | Ubuntu 24.04 LTS, ROS2 Jazzy, 8GB RAM                                      |
| **Microcontroller** | ESP32-WROOM-32    | Robocraze 38-pin, CP2102 USB-UART, 240MHz dual-core, 520KB SRAM            |
| **Motor drivers**   | Cytron MDD20A × 2 | 20A continuous, 6–30V, PWM+DIR control, logic threshold 1.5V               |
| **Level shifter**   | 8-channel discrete MOSFET (BSS138-style) × 1 | Bidirectional, 3.3V ↔ 5V. All 4 motors × 2 encoder channels on one board — see note below |
| **Battery**         | SM12830SL LiFePO4 | 12.8V, 30Ah, 384Wh                                                         |
| **Power relay**     | SSR-50DD          | Solid State Relay, 50A, 5–200V switching, 3–32VDC trigger, −20 to 85°C     |
| **Boost converter** | 1200W DC-DC       | 12.8V → 24V for motors                                                     |
| **Buck converter**  | DFRobot 60W       | 12.8V → 5V for encoders + level shifter HV rail                            |

> **⚠ HARDWARE CHANGE, 4 Aug 2026.** The dual-TXS0108E design below (§3–§4.4) was replaced with a single **8-channel discrete MOSFET (BSS138-style) bidirectional level shifter board** — no IC, no OE pin, per-channel LEDs, `LV+/LV−/HV+/HV−` power rails, `H0–H7` (5V side) / `L0–L7` (3.3V side) signal rails. All four encoders (both channels each) run through this one board. It was adopted after the TXS0108E interface failed for the third time (`Research_Journal.md` §7.12, and the 3 Aug all-four-dead bench run that `LevelShifter_Wiring.md` was written to diagnose) — the discrete-MOSFET board removes the OE pin entirely, which is one of the two failure modes that kept recurring. Root cause of that specific 3 Aug failure turned out to be a wiring cross-connection, not the shifter part itself, but the discrete board was already the planned replacement and is what's actually installed now.
>
> **Current wiring reference:** `Bench_Test_Map.md` §"Full 8-channel wiring — all four encoders on one board". `LevelShifter_Wiring.md` (below) documents the retired TXS0108E design and is kept for history — its signal-direction and grounding principles still apply, but its pin tables describe hardware no longer on the robot.

**3. Power Architecture**

**3.1 Power Distribution**

LiFePO4 Battery (12.8V, 30Ah) │ ├── SSR-50DD Relay ──► Boost Converter ──► 24V DC │ │ │ ├──► MDD20A Driver 1 VB+/VB- │ └──► MDD20A Driver 2 VB+/VB- │ │ │ 4× Rhino RMCS-2086 Motors │ ├── SSR-50DD Relay ──► Buck Converter ──► 5V DC │ │ │ ├──► Encoder VCC (all 4, Red wires) │ └──► TXS0108E VCCB (5V side) │ └── Pi 5 Power Supply ──► Raspberry Pi 5 │ └── USB-A ──► ESP32 USB-C │ └── AMS1117 ──► 3.3V │ ├──► ESP32 chip └──► TXS0108E VCCA + OE

**⚠ When Pi USB powers ESP32: Pi SMPS switching noise + PWM-induced GND transients cause jitter. Use a powerbank for ESP32 during bench tests. For final deployment: cut VBUS in the Pi→ESP32 USB cable and power ESP32 via its VIN pin from the 5V buck converter.**

**3.2 Ground Bus — CRITICAL**

ALL grounds must share a single common reference. Missing any connection causes phantom motor behaviour.

- ESP32 GND → MDD20A Driver 1 logic GND

- ESP32 GND → MDD20A Driver 2 logic GND

- ESP32 GND → TXS0108E GND

- Buck converter GND → common bus

- Boost converter GND → common bus

- Encoder 1, 2, 3, 4 Black wires → common bus

Pi GND connects to ESP32 GND automatically through the USB cable.

**4. ESP32 Pin Assignment & Complete Wiring**

**4.1 ESP32 Board Overview — Robocraze 38-pin (CP2102)**

|                       |                                          |                                                                      |
|-----------------------|------------------------------------------|----------------------------------------------------------------------|
| **Category**          | **Pins**                                 | **Rule**                                                             |
| **SAFE — use freely** | G4,G13,G14,G16-G19,G21-G27,G32-G35,SP,SN | No restrictions. All motor and encoder GPIOs are from this category. |
| **STRAPPING — avoid** | G0,G2,G5,G12,G15                         | Affect boot mode. Must be LOW or floating at power-on.               |
| **FORBIDDEN**         | G6,G7,G8,G9,G10,G11                      | Internal SPI flash. Will crash ESP32 if used.                        |
| **INPUT ONLY**        | SP(36),SN(39),G34,G35                    | Cannot output voltage. Perfect for encoder reading.                  |
| **IN USE — serial**   | G1(TXD),G3(RXD)                          | USB serial to Pi. Do not use for anything else.                      |

✓ AisleBot firmware v4.0 uses ZERO strapping pins. All GPIOs are from the SAFE or INPUT ONLY category.

**4.2 Motor Driver Outputs — RIGHT Side of Board → MDD20A**

All 8 motor control pins are on the right side of the ESP32 board. 3.3V logic from ESP32 is directly accepted by MDD20A (threshold 1.5V). No level shifting required.

|           |              |                 |          |                |                 |
|-----------|--------------|-----------------|----------|----------------|-----------------|
| **Motor** | **Function** | **Board Label** | **GPIO** | **Driver Pin** | **Ribbon Wire** |
| **FR**    | PWM          | G4              | **4**    | Driver 1 PWM1  | Wire 1          |
| **FR**    | DIR          | G16             | **16**   | Driver 1 DIR1  | Wire 2          |
| **FL**    | PWM          | G17             | **17**   | Driver 1 PWM2  | Wire 3          |
| **FL**    | DIR          | G18             | **18**   | Driver 1 DIR2  | Wire 4          |
| **RR**    | PWM          | G19             | **19**   | Driver 2 PWM1  | Wire 1          |
| **RR**    | DIR          | G21             | **21**   | Driver 2 DIR1  | Wire 2          |
| **RL**    | PWM          | G22             | **22**   | Driver 2 PWM2  | Wire 3          |
| **RL**    | DIR          | G23             | **23**   | Driver 2 DIR2  | Wire 4          |

ℹ Motor wiring is identical for all 4 motors: Red → MxA, Black → MxB. Direction differences between left and right sides are handled purely in software via MOTOR_DIR_SIGN\[\].

**4.3 Encoder Inputs — LEFT Side of Board via Level Shifter**

> **⚠ Table below (and §4.4) describes the retired TXS0108E design.** Current hardware is the single 8-channel discrete MOSFET board — see the callout in §2.5 and `Bench_Test_Map.md`. The GPIO/PCNT/Dir-Sign columns are still correct (the ESP32 side of the interface didn't change); only the shifter part and its pin names changed. Also note: front (GTK08) and rear (RMCS-2086) encoders use **different wire colours for A/B** — the Yellow/Green convention below is the RMCS (rear) convention only. See `LevelShifter_Wiring.md` §5 before wiring a front channel.

Encoder signals are 5V. ESP32 GPIOs are 3.3V. Level shifting is MANDATORY.

|           |                    |                   |            |            |               |              |
|-----------|--------------------|-------------------|------------|------------|---------------|--------------|
| **Motor** | **Enc A (Yellow)** | **Enc B (Green)** | **A GPIO** | **B GPIO** | **PCNT Unit** | **Dir Sign** |
| **FR**    | SP                 | SN                | **36**     | **39**     | PCNT_UNIT_0   | **−1**       |
| **FL**    | G34                | G35               | **34**     | **35**     | PCNT_UNIT_1   | **+1**       |
| **RR**    | G32                | G33               | **32**     | **33**     | PCNT_UNIT_2   | **−1**       |
| **RL**    | G25                | G26               | **25**     | **26**     | PCNT_UNIT_3   | **+1**       |

ℹ Encoder wiring is identical for all 4 motors. Yellow → Ch A, Green → Ch B. Red encoder wire → 5V BUCK (not ESP32). Black → common GND. Direction sign corrects for motor mounting orientation in software — no wire swapping needed.

**⚠ MOTOR_DIR_SIGN and ENC_DIR_SIGN MUST be identical per motor. If they differ, the PID loop sees positive feedback → motor runaway.**

**4.4 TXS0108E Level Shifter Wiring (RETIRED — see §2.5)**

|                  |                                     |                                  |
|------------------|-------------------------------------|----------------------------------|
| **TXS0108E Pin** | **Connect To**                      | **Notes**                        |
| **VCCA**         | ESP32 3V3 pin                       | 3.3V low-voltage side            |
| **VCCB**         | Buck converter 5V output            | 5V high-voltage side             |
| **GND**          | Common GND bus (ESP32 + Buck)       | Bridges both voltage domains     |
| **OE**           | ESP32 3V3 (tie to VCCA)             | Output Enable — 3.3V = always on |
| A1               | ESP32 SP (GPIO 36)                  | FR Encoder A — 3.3V side         |
| A2               | ESP32 SN (GPIO 39)                  | FR Encoder B                     |
| A3               | ESP32 G34 (GPIO 34)                 | FL Encoder A — 3.3V side         |
| A4               | ESP32 G35 (GPIO 35)                 | FL Encoder B                     |
| A5               | ESP32 G32 (GPIO 32)                 | RR Encoder A — 3.3V side         |
| A6               | ESP32 G33 (GPIO 33)                 | RR Encoder B                     |
| A7               | ESP32 G25 (GPIO 25)                 | RL Encoder A — 3.3V side         |
| A8               | ESP32 G26 (GPIO 26)                 | RL Encoder B                     |
| **B1–B8**        | Encoder signal wires (Yellow/Green) | 5V signals from encoder boards   |

**⚠ Power-up order matters: GND first, then VCCA (3.3V), then VCCB (5V). One TXS0108E provides 8 channels — exactly the number needed for 4 motors × 2 encoder channels.**

**4.5 Spare Pins for Future Expansion**

|           |          |                                                               |
|-----------|----------|---------------------------------------------------------------|
| **Label** | **GPIO** | **Recommended Use**                                           |
| G27       | **27**   | Best spare — no restrictions. Buzzer, LED, or general sensor. |
| G14       | **14**   | I2C SDA for IMU (BNO055) or LCD. Use Wire.begin(G14,G13).     |
| G13       | **13**   | I2C SCL for IMU (BNO055) or LCD.                              |

ℹ G21 and G22 are now used for RL motor PWM and DIR. Future I2C (IMU, LCD) should use G14 + G13 with Wire.begin(G14, G13).

**5. Critical Firmware Corrections (v4.0)**

**⚠ These errors existed in all firmware before this document version. They affected every WiFi joystick session. Fix both before running ground tests.**

**5.1 Error 1 — WHEEL_RADIUS Wrong by 52%**

The ESP32 WiFi joystick IK used WHEEL_RADIUS = 0.05 m. The DekuPro 6-inch wheel has an outer diameter of 152.4 mm, giving a radius of 76.2 mm = 0.0762 m. This means every velocity command from the phone was scaled by a factor of 0.0762/0.05 = 1.524. The firmware was commanding 52% more wheel speed than intended for every joystick input.

// WRONG (before v4.0):

const float WHEEL_RADIUS = 0.05f;

// CORRECT (v4.0+):

const float WHEEL_RADIUS = 0.0762f; // DekuPro 6-inch: 152.4mm OD / 2

**5.2 Error 2 — Symmetric IK with Wrong K (Core Novelty Ignored)**

The ESP32 firmware used a single ROBOT_K = 0.20 for all four wheels. This is wrong on two counts: (1) the robot is asymmetric, requiring two different K values; (2) 0.20 is far below the correct values (outer: 0.5607, inner: 0.4907). Every rotation command from the phone produced only 36% of the intended angular velocity. The asymmetry — the defining novelty of the research — was completely absent from the WiFi control path.

// WRONG (before v4.0) — single symmetric K:

const float ROBOT_K = 0.20f;

targets\[FR\] = (vx + vy + ROBOT_K \* wz) / WHEEL_RADIUS; // same K for all

// CORRECT (v4.0+) — asymmetric K from SolidWorks measurements:

const float L1 = 0.403f; // FR and RL: outer wheel longitudinal distance

const float L2 = 0.333f; // FL and RR: inner wheel longitudinal distance

const float D = 0.15769f; // half track width (all wheels identical)

float k_outer = L1 + D; // = 0.5607 m (FR and RL)

float k_inner = L2 + D; // = 0.4907 m (FL and RR)

targets\[FR\] = ( vx + vy + k_outer \* wz) / WHEEL_RADIUS;

targets\[FL\] = ( vx - vy - k_inner \* wz) / WHEEL_RADIUS;

targets\[RR\] = ( vx - vy + k_inner \* wz) / WHEEL_RADIUS;

targets\[RL\] = ( vx + vy - k_outer \* wz) / WHEEL_RADIUS;

ℹ The ROS2 mecanum_teleop_asymmetric.py node is CORRECT and has always used the proper l1, l2, d values. Only the ESP32 internal WiFi joystick IK was wrong. Serial commands from ROS2 to the ESP32 (\<V,fr,fl,rr,rl\>) bypass the ESP32's IK and are correct.

**5.3 Error 3 — E-STOP Auto-Clear Safety Bug**

The emergency stop command \<S\> auto-cleared after 50ms. This means pressing stop did not stop the robot — it resumed 50ms later. This is a safety bug, not a feature.

// REMOVE this block entirely from the Core 1 PID task:

if (emergency_stop && (millis() - estop_time \> 50)) {

emergency_stop = false; // DELETE THIS ENTIRE BLOCK

}

// CORRECT behaviour: E-STOP latches until cleared by \<E1\> or new \<V,...\>

**⚠ Do not run motors on the ground without fixing the E-STOP bug first. The 50ms auto-clear means the robot cannot be reliably stopped if it misbehaves.**

**6. ESP32 Firmware Architecture**

**6.1 Dual-Core FreeRTOS Layout**

|            |                                                                           |                    |                                          |
|------------|---------------------------------------------------------------------------|--------------------|------------------------------------------|
| **Core**   | **Task**                                                                  | **Rate**           | **Priority**                             |
| **Core 1** | PID loop: read PCNT encoders, compute PID+FF, write PWM                   | 50 Hz (20ms fixed) | Priority 2 — highest. Never interrupted. |
| **Core 0** | WiFi AP, WebSocket server (port 81), HTTP server (port 80), Serial parser | Continuous         | Priority 1                               |
| **Core 0** | Telemetry broadcast (WebSocket to phone + Serial CSV to Pi)               | 10 Hz (100ms)      | Priority 1                               |

**6.2 PID + Feedforward Parameters**

> **⚠ SUPERSEDED by firmware v3.0 (4 Aug 2026). See [`PID_Calibration.md`](PID_Calibration.md) for the current values and the data behind them.**
>
> The table below documents v2.0 and is kept for history. Three things in it are now known to be wrong:
> - **`Encoder CPR = 93,132` is only true for the rears.** FR/FL now carry GTK08 encoders at **186,264 CPR**. A single shared constant makes the fronts read double their true speed and run at half the commanded velocity.
> - **The per-motor `Kff` spread (40.2 – 47.9) is an artefact** of the faulty-encoder era. Re-measured on the confirmed-good path, all four motors fall inside a 3 % band: `{37.3, 38.4, 38.3, 38.0}`.
> - **`Ki = 30` is roughly an order of magnitude too low.** It moved the output ~3 PWM/s at 0.1 rad/s of error, which is the direct cause of the 3.79 s worst-case settling time recorded on 14 May. v3.0 uses **250**, derived from the measured plant gain.
>
> v3.0 also drops the ESP32-hosted WiFi joystick entirely — the Pi is the only command source — so the WiFi override row no longer applies.

|                           |             |                                                                                                                       |
|---------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------|
| **Parameter**             | **Value**   | **Description**                                                                                                       |
| **Kp**                    | **50.0**    | Proportional gain — main push toward target                                                                           |
| **Ki**                    | **30.0**    | Integral gain — eliminates steady-state error. Anti-windup ±200.                                                      |
| **Kd**                    | **3.0**     | Derivative gain — viable only with ESP32 PCNT (zero noise). D-filter α=0.3                                            |
| **Kff \[FR\]**            | **42.1**    | Feedforward: PWM per rad/s. Air-calibrated — recalibrate for ground.                                                  |
| **Kff \[FL\]**            | **40.2**    | Fastest motor, least FF needed                                                                                        |
| **Kff \[RR\]**            | **43.7**    | Mid-range motor                                                                                                       |
| **Kff \[RL\]**            | **47.9**    | Slowest motor. RL has +0.131 rad/s SS overshoot at 3.0 rad/s — increase Ki for RL after ground recalibration.         |
| **Encoder CPR**           | **93,132**  | 500 lines × 4 edges (full quad) × 47 ratio. PCNT hardware — zero CPU load.                                            |
| **PID loop rate**         | **50 Hz**   | 20ms per cycle, Core 1 dedicated                                                                                      |
| **VEL_FILTER_ALPHA**      | **0.5**     | EMA on measured velocity. Lower to 0.3 if ground vibration causes D-term noise.                                       |
| **D_FILTER_ALPHA**        | **0.3**     | EMA on derivative term. Lower if Kd causes audible buzzing.                                                           |
| **MIN_PWM_THRESHOLD**     | **15**      | Deadband — PWM below this forced to zero. Calibrated in air. Increase for ground (likely 25–40). Calibrate per-motor. |
| **Watchdog timeout**      | **1000 ms** | Motors stop if no command from any source for 1s.                                                                     |
| **WiFi override timeout** | **200 ms**  | WiFi joystick stays active 200ms after last touch. Then reverts to serial.                                            |

**6.3 Command Arbitration**

Two command sources coexist:

- USB Serial (Pi / ROS2) — sends \<V,fr,fl,rr,rl\> wheel velocities in rad/s

- WiFi Joystick (phone) — sends body velocities (vx,vy,wz); ESP32 runs corrected asymmetric IK internally

Rule: WiFi overrides serial while joystick is touched (within 200ms timeout). Release joystick → serial resumes within 200ms.

**6.4 Serial Command Protocol**

|                       |                                                                        |
|-----------------------|------------------------------------------------------------------------|
| **Command**           | **Description**                                                        |
| **\<V,fr,fl,rr,rl\>** | Set 4 wheel velocities in rad/s via PID                                |
| **\<M,fr,fl,rr,rl\>** | Direct PWM −255 to +255, bypasses PID entirely                         |
| **\<T,idx,vel\>**     | Test single motor. idx: 0=FR, 1=FL, 2=RR, 3=RL                         |
| **\<G,Kp,Ki,Kd\>**    | Set PID gains live — resets all integrals                              |
| **\<F,fr,fl,rr,rl\>** | Set per-motor feedforward gains live                                   |
| **\<S\>**             | Emergency stop. FIXED in v4.0 — now latches until cleared by \<E1\>    |
| **\<?\>**             | Query live state: targets, actuals, PWM, error                         |
| **\<I\>**             | System info: gains, CPR, wheel radius, WiFi status                     |
| **\<L1\> / \<L0\>**   | Enable / disable CSV telemetry on Serial (for Pi logger)               |
| **\<E1\> / \<E0\>**   | Enable / disable all motors. Use \<E0\> for safe deadband calibration. |
| **\<W1\> / \<W0\>**   | Enable / disable watchdog timer                                        |
| **\<P\>**             | Ping → replies \[PONG\]                                                |
| **\<H\>**             | Print full help to Serial                                              |

**6.5 CSV Telemetry Format (when \<L1\> enabled)**

timestamp_ms, FR_tgt, FR_act, FR_pwm, FL_tgt, FL_act, FL_pwm, RR_tgt, RR_act, RR_pwm, RL_tgt, RL_act, RL_pwm

13 columns. Velocities in rad/s. Logged at 10Hz. The Pi logger (aislebot_telemetry_logger.py) reads this via --port /dev/ttyUSB0 and computes error = actual − target on the Pi side.

**6.6 WiFi Configuration (REMOVED in firmware v3.0 — historical)**

> **⚠ The ESP32 hosts no WiFi network as of v3.0 (4 Aug 2026).** The radio, WebSocket server and joystick page were removed; the Pi is the sole command source. The table below describes v2.0 and is retained for history only. See `Research_Journal.md` Part XVI §16.6 and `Network_SelfHosted_AP.md`.

|                      |                                                                                                  |
|----------------------|--------------------------------------------------------------------------------------------------|
| **Setting**          | **Value**                                                                                        |
| **SSID**             | **AisleBot-Control**                                                                             |
| **Password**         | aislebot123                                                                                      |
| **Mode**             | SoftAP — ESP32 creates its own network. No router.                                               |
| **IP Address**       | 192.168.4.1 (default SoftAP gateway)                                                             |
| **Web Joystick URL** | http://192.168.4.1/                                                                              |
| **WebSocket**        | ws://192.168.4.1:81/                                                                             |
| **Tx Power**         | ~20 dBm. Effective range: 5–8m. Call WiFi.setTxPower(WIFI_POWER_19_5dBm) in setup() to maximise. |

**7. ROS2 System Architecture**

**7.1 Node Graph**

Phone (WiFi joystick) │ SoftAP 802.11 ▼ ESP32 PID ─────────── USB Serial (115200 baud) ──────────► Raspberry Pi 5 (Core 1: motors) CSV telemetry ◄──────────────────── (ROS2 Jazzy) \<V,fr,fl,rr,rl\> commands ────────► │ ┌─────────────────────┘ │ /joy topic ▼ joy_node ──► mecanum_teleop_asymmetric.py │ /wheel_speeds \[FR,FL,RR,RL\] rad/s ▼ arduino_bridge.py (ESP32 bridge node)

**7.2 Kinematics Node — mecanum_teleop_asymmetric.py**

This is the CORRECT implementation of asymmetric mecanum IK. It has always used the proper parameters.

|               |                                                                    |
|---------------|--------------------------------------------------------------------|
| **Parameter** | **Value & Source**                                                 |
| **l1**        | 0.403 m — FR and RL outer wheel longitudinal distance (SolidWorks) |
| **l2**        | 0.333 m — FL and RR inner wheel longitudinal distance (SolidWorks) |
| **d**         | 0.15769 m — half track width (SolidWorks)                          |
| **a**         | 0.0762 m — wheel radius (DekuPro 6-inch actual)                    |

Inverse Kinematics (from IIT Bombay paper, Equation 1):

ω_FR = (1/a) × (u + v + r × (l1 + d)) → k_outer = 0.5607 m

ω_FL = (1/a) × (u - v - r × (l2 + d)) → k_inner = 0.4907 m

ω_RR = (1/a) × (u - v + r × (l2 + d)) → k_inner = 0.4907 m

ω_RL = (1/a) × (u + v - r × (l1 + d)) → k_outer = 0.5607 m

Forward Kinematics:

vx = (a/4) × (ω_FR + ω_FL + ω_RR + ω_RL)

vy = (a/4) × (ω_FR - ω_FL - ω_RR + ω_RL)

ωz = (a / (2×(l1+l2+2d))) × (ω_FR - ω_FL + ω_RR - ω_RL)

**7.3 ROS2 Topics**

|                   |                            |                           |                           |
|-------------------|----------------------------|---------------------------|---------------------------|
| **Topic**         | **Type**                   | **Publisher**             | **Subscriber**            |
| **/joy**          | sensor_msgs/Joy            | joy_node                  | mecanum_teleop_asymmetric |
| **/wheel_speeds** | std_msgs/Float64MultiArray | mecanum_teleop_asymmetric | arduino_bridge            |

**7.4 Speed Limits (aligned across full stack)**

|                     |           |                              |
|---------------------|-----------|------------------------------|
| **Constant**        | **Value** | **Location**                 |
| **MAX_LINEAR**      | 0.15 m/s  | mecanum_teleop_asymmetric.py |
| **MAX_ANGULAR**     | 0.3 rad/s | mecanum_teleop_asymmetric.py |
| **max_wheel_speed** | 3.0 rad/s | arduino_bridge.py            |
| **MAX_WHEEL_SPEED** | 3.0 rad/s | ESP32 firmware               |
| **SAFE_MAX_RAD_S**  | 3.0 rad/s | ESP32 firmware               |

**7.5 Key Files — Raspberry Pi 5 (username: aritra)**

|                                  |                                            |
|----------------------------------|--------------------------------------------|
| **File**                         | **Path / Description**                     |
| **mecanum_teleop_asymmetric.py** | ~/ros2_ws/src/mecanum_robot/mecanum_robot/ |
| **arduino_bridge.py**            | ~/ros2_ws/src/mecanum_robot/mecanum_robot/ |
| **hardware.launch.py**           | ~/ros2_ws/src/mecanum_robot/launch/        |
| **aislebot_telemetry_logger.py** | ~/ (run with --port /dev/ttyUSB0)          |
| **aislebot.service**             | systemd autostart → ~/start_aislebot.sh    |

**8. Ground Testing Protocol & Telemetry Logging**

**8.1 Current Test Architecture**

Phone (WiFi joystick) drives the robot. Raspberry Pi logs telemetry over USB serial. No ROS2 commands sent — Pi is a passive observer only. All four motors confirmed responding in air (March 2026 test run, 514 samples, 51.6s).

**8.2 Pi Logger Fixes Required Before First Use**

**⚠ The logger (aislebot_telemetry_logger.py) was written for Arduino. Four changes are required before it works with ESP32.**

Fix 1 — correct serial port (line 119):

port: str = '/dev/ttyUSB0' \# was /dev/ttyACM0 (Arduino)

Fix 2 — parser column count (line 231):

if len(parts) \< 13: \# was 17

Fix 3 — 3 fields per motor, compute error (line 239):

idx = 1 + i \* 3 \# was i \* 4

sample.motors\[i\].error = actual - target \# computed, not read from CSV

Fix 4 — add phase classifier method and column to export:

def \_classify_phase(self, motors):

fr,fl,rr,rl = \[m.target for m in motors\]

t = 0.15

if fr\>t and fl\>t and rr\>t and rl\>t: return 'FWD'

elif fr\<-t and fl\<-t and rr\<-t and rl\<-t: return 'REV'

elif fr\<-t and fl\>t and rr\>t and rl\<-t: return 'STRAFE-L'

elif fr\>t and fl\<-t and rr\<-t and rl\>t: return 'STRAFE-R'

elif fr\>t and fl\<-t and rr\>t and rl\<-t: return 'ROT-CW'

elif fr\<-t and fl\>t and rr\<-t and rl\>t: return 'ROT-CCW'

elif all(abs(v)\<t for v in \[fr,fl,rr,rl\]): return 'STOP'

else: return 'MIXED'

**8.3 Ground Run Step-by-Step**

1.  Fix E-STOP bug (§5.3) in firmware. Flash updated firmware to ESP32.

2.  Deadband calibration: \<E1\> then \<T,motor,pwm\> stepping 10→50. Find actual start-of-motion PWM on floor per motor. Update MIN_PWM_THRESHOLD.

3.  Start Pi logger: python3 ~/aislebot_telemetry_logger.py --port /dev/ttyUSB0. Type 'start' at prompt.

4.  Drive with phone: FWD 10s → REV 10s → STRAFE-L 10s → STRAFE-R 10s → ROT-CW 10s → ROT-CCW 10s.

5.  Stop and export: type 'stop' → 'export' → 'csv'. Files saved to ~/aislebot_logs/ with timestamp.

6.  Post-run analysis: open Excel. Filter Phase=FWD. Compare RL vs FR PWM — if RL lower than FR at same setpoint, RL has insufficient ground contact.

**8.4 Air-Test Telemetry Results (Baseline)**

|                             |                                                                                   |        |        |            |
|-----------------------------|-----------------------------------------------------------------------------------|--------|--------|------------|
| **Metric**                  | **FR**                                                                            | **FL** | **RR** | **RL**     |
| **Global MAE (rad/s)**      | 0.0479                                                                            | 0.0532 | 0.0704 | **0.0979** |
| **RMSE (rad/s)**            | 0.0929                                                                            | 0.0984 | 0.1068 | **0.1328** |
| **SS overshoot @3.0 rad/s** | +0.047                                                                            | −0.016 | +0.052 | **+0.131** |
| **SS PWM @3.0 rad/s**       | 121.7                                                                             | 80.7   | 79.9   | 126.1      |
| **FF expected PWM @3.0**    | 126.3                                                                             | 120.6  | 131.1  | 143.7      |
| **PID loop timing jitter**  | **Mean 100.5ms, σ=0.67ms, Max 103ms, Zero gaps \>200ms — PID loop is rock-solid** |        |        |            |

**9. Commissioning Checklist**

**9.1 Pre-Power Verification**

- All motor wires: Red → MxA, Black → MxB (identical all 4 motors)

- All encoder wires: Yellow → Enc_A, Green → Enc_B (identical all 4)

- Encoder 5V from buck converter — NOT from ESP32

- TXS0108E: VCCA=ESP32 3V3, VCCB=Buck 5V, OE=ESP32 3V3, GND=common

- MDD20A Driver 1 logic GND → ESP32 GND

- MDD20A Driver 2 logic GND → ESP32 GND

- 24V from boost converter to both MDD20A VB+/VB-

- ESP32 connected to Pi (or PC) via USB

- Battery relay OFF (motors unpowered) for initial firmware test

- **E-STOP auto-clear bug removed from firmware**

- **WHEEL_RADIUS = 0.0762f in firmware**

- **Asymmetric IK with L1=0.403, L2=0.333, D=0.15769 in firmware WiFi joystick handler**

**9.2 Step-by-Step Testing Sequence**

**Step 1: Verify Boot**

- Upload sketch → Serial Monitor at 115200 baud → confirm \[READY\]

- Type \<P\> → confirm \[PONG\]

- Type \<I\> → verify system info (gains, CPR, wheel radius, WiFi status)

**Step 2: Encoder Test (battery OFF, spin by hand)**

- Type \<L1\> to enable telemetry

- Spin each wheel forward by hand → verify POSITIVE velocity reading

- If negative: flip ENC_DIR_SIGN for that motor (−1 ↔ +1)

**Step 3: Motor Direction (battery ON, one motor at a time)**

- \<T,0,1.0\> → FR forward \| \<S\> → \<T,1,1.0\> → FL forward \| \<S\>

- \<T,2,1.0\> → RR forward \| \<S\> → \<T,3,1.0\> → RL forward \| \<S\>

- If any wheel spins backward: flip MOTOR_DIR_SIGN (−1 ↔ +1)

**Step 4: WiFi Joystick**

- Phone connects to AisleBot-Control (aislebot123)

- Open http://192.168.4.1 → touch joystick forward → all wheels forward

- Verify PID graphs update in real time

**Step 5: PID Tuning**

- \<V,2.0,2.0,2.0,2.0\> → all wheels at 2.0 rad/s → actual converges within 0.5s

- Oscillating: reduce Kp → \<G,40,30,3\> \| Slow: increase Kp → \<G,60,30,3\>

- Steady-state error: increase Ki → \<G,50,40,3\>

**9.3 Direction Troubleshooting**

|                                          |                                                  |                                                                       |
|------------------------------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| **Symptom**                              | **Cause**                                        | **Fix**                                                               |
| **Motor spins backward**                 | MOTOR_DIR_SIGN wrong                             | Flip −1 ↔ +1 in array                                                 |
| **Encoder reads negative going forward** | ENC_DIR_SIGN wrong                               | Flip −1 ↔ +1 in array                                                 |
| **PID oscillates violently / runaway**   | MOTOR and ENC signs disagree — positive feedback | **Both signs MUST match per motor**                                   |
| **Motor hums but doesn't spin**          | Below deadband threshold                         | Normal — MIN_PWM=15. Increase for ground.                             |
| **No response from any motor**           | Missing GND between ESP32 and driver             | Connect logic GND wire                                                |
| **Jitter when Pi USB powers ESP32**      | Pi SMPS noise + motor PWM GND transients         | Use powerbank or cut VBUS in USB cable; power ESP32 via VIN from buck |

**10. Autonomy Roadmap — Five Phases**

**Phase 1: Closed-Loop Motor Control (CURRENT)**

Status: ESP32 PID complete. Air-test validated. Ground testing in progress. The foundation for all subsequent phases — every layer above assumes motors track commanded velocity within 2%.

- PID + Feedforward per motor at 50Hz on dedicated Core 1

- ESP32 PCNT full quadrature — 93,132 CPR, zero CPU overhead

- Air-test results: FR MAE=0.0479, RL MAE=0.0979 (RL requires ground Kff recalibration)

- Immediate: fix firmware errors (§5), ground deadband calibration, 3–4 logged ground runs

**Phase 2: Odometry + IMU State Estimation**

Goal: Fused position and heading estimate reliable enough for SLAM input. Galati et al. (2022) showed open-loop heading drift of 4.56°/10m on concrete — catastrophic for 1.2m-wide aisles where robot width is ~0.5m.

- Wheel odometry from encoder feedback using asymmetric forward kinematics (FK equation above)

- IMU: BNO055 recommended (onboard sensor fusion, calibrated yaw output) via I2C on G14/G13

- EKF fusion: ROS2 robot_localization package fuses /odom (wheel) + /imu/data → /odometry/filtered

- Target: heading error \< 0.5° per 10m (from Galati baseline of 4.56° open-loop)

- Prerequisite: 3–4 ground run logs to measure actual drift — then set EKF process noise from data

**Phase 3: LiDAR SLAM**

Goal: Occupy a 2D map of the environment accurate enough for path planning.

- Sensor: RPLiDAR A2 (USB to Pi, /scan topic at 10Hz)

- SLAM: slam_toolbox in ROS2 Jazzy — online mode for map building, lifelong mode for updates

- Narrow-aisle specific: aisle width 1.0–1.5m — slam_toolbox needs scan_match_minimum_run_distance \< 0.05m to update at low speeds

**Phase 4: Nav2 Autonomous Path Planning**

Goal: Robot navigates from A to B without human input.

- Global planner: NavFn or Smac (grid-based A\*) — generates waypoint path from costmap

- Local planner: DWB controller (initial) → MPPI (after Phase 3 validation) for dynamic obstacle avoidance

- Costmap: inflation radius = robot_radius + clearance. For AisleBot in 1.2m aisle: inflation ≈ 0.35m

**Phase 5: Warehouse Intelligence**

Goal: Adaptive behaviour for real warehouse conditions — payloads, floor variations, tight turns.

- Adaptive heading correction (per adaptive heading correction paper): measure yaw error from IMU, apply correction bias to IK wz term

- Gain scheduling for payload: heavier loads need higher Kff — detect load from current draw change

- Roller radius variation compensation: r(α) = R_mean + ΔR·cos(n·α) for odometric accuracy on mecanum rollers

- Narrow-aisle trajectory optimisation: pre-planned entry/exit angles for aisle transitions

**11. Quick Reference**

**11.1 Wheel Direction Reference (Top View)**

|                  |        |        |        |        |
|------------------|--------|--------|--------|--------|
| **Motion**       | **FR** | **FL** | **RR** | **RL** |
| **Forward**      | FWD    | FWD    | FWD    | FWD    |
| **Backward**     | REV    | REV    | REV    | REV    |
| **Strafe Right** | FWD    | REV    | REV    | FWD    |
| **Strafe Left**  | REV    | FWD    | FWD    | REV    |
| **Yaw CW**       | FWD    | REV    | FWD    | REV    |
| **Yaw CCW**      | REV    | FWD    | REV    | FWD    |

**11.2 Arduino IDE Settings for ESP32**

|                        |                                                                                             |
|------------------------|---------------------------------------------------------------------------------------------|
| **Setting**            | **Value**                                                                                   |
| **Board**              | ESP32 Dev Module                                                                            |
| **Upload Speed**       | 921600                                                                                      |
| **CPU Frequency**      | **240MHz (WiFi/BT) — critical for dual-core PID + WiFi**                                    |
| **Flash Size**         | 4MB (default)                                                                               |
| **Partition Scheme**   | Default 4MB with spiffs                                                                     |
| **PSRAM**              | Disabled                                                                                    |
| **Board Manager URL**  | https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json |
| **Required Library 1** | **WebSockets by Markus Sattler (Links2004) — NOT the Arduino one**                          |
| **Required Library 2** | ArduinoJson by Benoit Blanchon                                                              |

**11.3 Version History**

|             |          |                                                                                                                                                                            |
|-------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Version** | **Date** | **Changes**                                                                                                                                                                |
| v1.0        | Jan 2026 | Initial system architecture — Arduino Mega + Grove Shield                                                                                                                  |
| v2.0        | Jan 2026 | ESP32 manual v2.0 — updated pin config, strapping pins eliminated                                                                                                          |
| v3.0        | Mar 2026 | Open-loop deployment — ROS2 Jazzy, speed scaling fix, phantom disconnection fix                                                                                            |
| **v4.0**    | Mar 2026 | **MASTER DOCUMENT. Fixed WHEEL_RADIUS (0.05→0.0762), Fixed asymmetric IK in ESP32 WiFi path, Fixed E-STOP bug, Added ground run logging protocol, Consolidated all docs.** |

*AisleBot Master Reference — v4.0 — IIT Bombay BSBE — Aritra Das (25D0074)*
