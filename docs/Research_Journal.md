> Originally converted from `AisleBot_Research_Journal.docx` (the pre-8-July source is preserved at `docs/originals/AisleBot_Research_Journal.docx`). Since v2.0 (8 July 2026) this Markdown file is the primary living document and the source of record — edit it here going forward and keep the revision log current. The `.docx` original is now a historical snapshot, not the live copy.

**NarrowAisleBot**

Asymmetric Mecanum-Wheeled Omnidirectional Robot

for Narrow-Aisle Autonomous Navigation

*Research Journal*

*(Living Document — Updated Across Project Lifecycle)*

**Aritra Das**

Roll No. 25D0074

Department of Biosciences and Bioengineering

Indian Institute of Technology Bombay

***Project Instructor: Prof. Ambarish Kunwar  
***

Last Updated: 8 July 2026

# About this journal

This is a living document. It grows alongside the project, and the intention is that it stays useful throughout — not just at the end. Every consequential design decision, every hardware specification, every debugging session that mattered, and every resolution is in here. New milestones get appended as revisions.

Unlike a final report, this journal keeps the path travelled. Dead ends are in here. Mid-course corrections are in here. The reasoning behind a working system is as valuable as the system itself, and this document tries to capture both.

## Who should read this

- Aritra Das — primary author, daily reference

- Prof. Ambarish Kunwar — academic advisor reviewing methodology and progress

- Future collaborators or successors picking up the project

- Reviewers evaluating the work for publication, demonstration, or grant purposes

## How this is organised

Fifteen parts plus appendices. Parts I–III build the conceptual and physical foundation: what this robot is, why it exists in this form, and what it's made of. Parts IV–V cover electrical and software architecture. Part VI is the narrative heart — the control-system journey in rough chronological order. Part VII catalogues every meaningful hurdle and how it got resolved. Parts VIII–IX synthesise the principles and document the (historical) current state. Part X is the autonomy roadmap. Part XI is a quick-reference section for tables, pins, and protocols. Part XII is the ESP32 firmware deep-dive added in v1.2. Part XIII (added v2.0) is the LiDAR + SLAM bringup that opened Phase 3. Part XIV (added v2.0) covers the desktop dashboard, the self-hosted network, and the repository consolidation. Part XV (added v2.0) is the current status snapshot — the most up-to-date single view of the system, superseding the older snapshot in Part IX.

## Revision discipline

Every meaningful change appends a dated entry to the revision log at the end. Version numbers increment when material has been added or corrected. The recommended cadence is one revision per debugging session, design pivot, or milestone.

# Executive Summary

AisleBot is an asymmetric mecanum-wheeled omnidirectional mobile robot, built at IIT Bombay under Prof. Ambarish Kunwar. The geometry is the interesting part: instead of placing all four wheels symmetrically at the corners of a rectangle, the two diagonal pairs sit at different distances from the body centre. The outer pair (FR, RL) is at l₁ = 403 mm; the inner pair (FL, RR) is at l₂ = 333 mm. That 70 mm offset produces a narrower chassis footprint than a conventional symmetric mecanum design, which is the whole point — the robot is meant to work in warehouse aisles, airplane cabins, railway coaches, and ultimately as an autonomous food-delivery cart in restaurant service aisles.

The control stack has three layers. A Raspberry Pi 5 running Ubuntu 24.04 with ROS 2 Jazzy handles planning. An ESP32 microcontroller runs a hardware-PCNT-based PID and feedforward velocity controller at 50 Hz — this is the real-time spine of the system. Four Rhino RMCS-2086 24 V geared motors, driving DekuPro 6-inch SR mecanum wheels through dual Cytron MDD20A drivers, do the actual work. A second microcontroller — an Arduino Mega 2560 — operates a separate UV-arm subsystem for cargo handling on the eventual food-cart variant.

As of May 2026, Phase 1 is done. On 14 May 2026, with the robot powered from the LiFePO₄ battery and elevated with wheels free in the air, all four motors tracked their commanded velocities at 99–100% across a multi-axis manoeuvre run. RMS tracking error was 0.12 rad/s. Zero PWM-saturation events.

Getting there took a substantial debugging campaign. Two encoder-wiring failures at the TXS0108E level-shifter interface. A 22× CPR error. A 52% wheel-radius error. A previously-overlooked inconsistency in how the asymmetric kinematics propagated across control paths. All of that is documented in detail in Parts VI and VII.

The current focus is ground-truth recalibration (the air-load feedforwards are expected to under-predict the on-floor operating point by 10–30%), followed by Phase 2 IMU sensor fusion, Phase 3 LiDAR SLAM, and Phase 4 Nav2 autonomous navigation. The foundation is solid. The roadmap is clear.

# Part I — Vision, Foundations, and Theoretical Basis

## 1.1 The application vision

AisleBot was designed for spaces that conventional differential-drive robots can't service: warehouse aisles barely wider than the robot itself, the central corridor of an airplane cabin, the longitudinal passage of a railway coach. Its eventual deployment target is restaurant service aisles, where it would operate as an autonomous food-delivery cart.

The unifying constraint across all these environments is a narrow corridor. You need full omnidirectional mobility — forward, backward, lateral strafing, in-place rotation — without ever needing to back up and three-point-turn the way a steered or differential platform has to.

Mecanum-wheel kinematics solve the omnidirectional requirement. The further constraint — that the chassis fit through genuinely narrow gaps — is what drove the central design decision: an asymmetric wheelbase.

## 1.2 The asymmetric wheelbase: the core geometric idea

A conventional symmetric mecanum platform places all four wheels at the corners of a rectangle. The chassis must be at least as wide as the wheelbase, plus mounting and clearance margins. AisleBot breaks this symmetry. The outer pair (FR, RL) sits at l₁ = 403 mm from the body centre; the inner pair (FL, RR) sits at l₂ = 333 mm. That 70 mm offset enables a narrower chassis without sacrificing the kinematic basis for omnidirectional motion.

There's a price for this. First, the inverse-kinematics matrix is no longer the textbook symmetric form — each wheel has its own coefficient. Second, the centre of mass and the geometric centre don't coincide exactly, which matters during trajectory tracking under load. Both consequences are tractable and have been accounted for in the control design (see Part VI).

## 1.3 The foundational paper

The project's geometric basis is documented in An Omnidirectional Asymmetric Mobile Robot for Narrow-Aisle Spaces, archived in the project documents. That paper establishes the kinematic equations for non-collinear mecanum wheel placement, derives the wheel-velocity-to-body-velocity transformation, and validates it in simulation. AisleBot extends this in two directions: a full physical implementation, and a closed-loop sensor-fused autonomy stack built on top of it.

## 1.4 The long-term goal: autonomous food-delivery cart

Every hardware and software decision gets evaluated against the eventual food-cart application. This imposes specific constraints that reach back into every layer.

The robot has to navigate dynamic environments with people walking through its path, not pre-mapped industrial floors. Smooth motion is non-negotiable — stutter or jitter during strafing risks spilling beverages or knocking over crockery. It has to be safe and predictable around people, with hardware-level emergency stops and software-level deceleration profiles. The cargo-handling arm must operate without destabilising the chassis. Battery life and acoustic noise become first-order design parameters.

Phase 1 — solid motor control — is the foundation everything else rests on.

# Part II — Mechanical Design and Geometry

## 2.1 Chassis dimensions

| **Parameter**    | **Symbol** | **Value** | **Notes**                                   |
|------------------|------------|-----------|---------------------------------------------|
| Chassis length   | L          | 1000 mm   | Front-to-back footprint                     |
| Chassis width    | W          | 250 mm    | Total robot width including wheel hubs      |
| Total mass       | m          | 45.54 kg  | Chassis + wheels + drivetrain + electronics |
| Asymmetry offset | l₁ − l₂    | 70 mm     | Differentiates outer vs inner wheels        |

These dimensions put AisleBot in a category no commercial off-the-shelf mecanum platform occupies: long enough to carry meaningful cargo (1 m), narrow enough for aisle widths under 350 mm clear, and heavy enough that mecanum-wheel rolling friction is non-negligible. That last point shows up in feedforward calibration.

## 2.2 Wheel placement geometry

The naming convention used throughout the project:

- FR — Front Right (outer)

- FL — Front Left (inner)

- RR — Rear Right (inner)

- RL — Rear Left (outer)

| **Parameter**                     | **Symbol** | **Value**             | **Applies to**        |
|-----------------------------------|------------|-----------------------|-----------------------|
| Outer-wheel longitudinal distance | l₁         | 0.403 m (403 mm)      | FR, RL                |
| Inner-wheel longitudinal distance | l₂         | 0.333 m (333 mm)      | FL, RR                |
| Half track width                  | d          | 0.15769 m (157.69 mm) | All wheels            |
| Wheel radius                      | r (a)      | 0.0762 m (76.2 mm)    | DekuPro 6" SR Mecanum |

The wheels are DekuPro 6-inch SR Mecanum, with rollers at the conventional 45° angle. Roller-direction handedness alternates diagonally so the standard mecanum velocity-mixing properties hold: FR and RL share one roller orientation; FL and RR share the opposite.

## 2.3 Derived kinematic constants

Two composite constants enter every inverse-kinematics equation. They act as the lever arm linking robot rotational velocity ω_z to wheel angular velocity at each corner.

| **Constant** | **Expression** | **Value** | **Used by**               |
|--------------|----------------|-----------|---------------------------|
| K_outer      | l₁ + d         | 0.5607 m  | FR, RL inverse kinematics |
| K_inner      | l₂ + d         | 0.4907 m  | FL, RR inverse kinematics |

> *Why these constants matter beyond the math: several historical bugs traced back to a single root cause — code paths that mixed up K_outer and K_inner, or used a symmetric K value everywhere. The asymmetric design is the project's central novelty. The first time it accidentally got papered over with a single K, the robot was effectively a normal symmetric mecanum platform with no geometric novelty in control. Every controller code path must use the correct K for each wheel.*

## 2.4 Inverse kinematics equations

Given desired body velocities u (forward, m/s), v (strafe, m/s), and r (yaw rate, rad/s), the four wheel angular velocities are:

> ω_FR = (1/r_w) × (u + v + r × K_outer) ← outer wheel
>
> ω_FL = (1/r_w) × (u − v − r × K_inner) ← inner wheel
>
> ω_RR = (1/r_w) × (u − v + r × K_inner) ← inner wheel
>
> ω_RL = (1/r_w) × (u + v − r × K_outer) ← outer wheel

where r_w = 0.0762 m, K_outer = 0.5607 m, K_inner = 0.4907 m

## 2.5 Forward kinematics equations

The inverse mapping — measured wheel speeds to body velocity — is used by both the simulation bridge and the wheel-odometry node:

> v_x = (r_w / 4) × ( ω_FR + ω_FL + ω_RR + ω_RL )
>
> v_y = (r_w / 4) × ( ω_FR − ω_FL − ω_RR + ω_RL )
>
> ω_z = (r_w / (2 × (l₁ + l₂ + 2d))) × ( ω_FR − ω_FL + ω_RR − ω_RL )

## 2.6 Maximum-speed envelope

| **Parameter**                          | **Symbol** | **Value**  | **Source**             |
|----------------------------------------|------------|------------|------------------------|
| Max wheel angular velocity             | ω_max      | 6.28 rad/s | 60 RPM × 2π / 60       |
| Max linear robot speed (theoretical)   | v_max      | ≈ 0.48 m/s | ω_max × r_w            |
| Conservative operating limit (current) | v_op       | 0.15 m/s   | Set in teleop & bridge |
| Max yaw rate (conservative)            | ω_z,op     | 0.3 rad/s  | Set in teleop & bridge |

The conservative limits exist because Phase 1 was validated in the air. Once ground testing recalibrates the feedforward values, these can safely be raised toward the theoretical maximum.

# Part III — Hardware Inventory

A complete list of every component currently installed on AisleBot, with the rationale for each choice and any non-obvious operating notes.

## 3.1 Compute layer

| **Component**     | **Specification**                                   | **Role**                                                                                                                |
|-------------------|-----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| Raspberry Pi 5    | Ubuntu 24.04.4 LTS + ROS 2 Jazzy                    | Planning, perception, ROS 2 nodes, future SLAM / Nav2                                                                   |
| ESP32-WROOM-32    | 38-pin module, CP2102 USB-UART, 240 MHz, 4 MB flash | Real-time PID + feedforward velocity controller at **100 Hz** (v3.0; was 50 Hz), encoder counting via PCNT. **WiFi removed in v3.0** — the Pi is the sole command source (Part XVI) |
| Arduino Mega 2560 | ATmega2560, 16 MHz                                  | UV-arm stepper controller (separate subsystem)                                                                          |

The dual-microcontroller split is deliberate. The ESP32 has the throughput and hardware peripherals needed for four-channel quadrature encoder counting at the ~93,000 pulses/second the drive motors produce under load. The Mega cannot service that interrupt rate while also handling stepper drivers, so responsibilities are partitioned by physical capability rather than by software architecture.

## 3.2 Drive motors

| **Specification**                  | **Value**                                |
|------------------------------------|------------------------------------------|
| Model                              | Rhino RMCS-2086                          |
| Operating voltage                  | 24 V DC                                  |
| No-load speed                      | 60 RPM (≈ 6.28 rad/s)                    |
| Gear ratio                         | 1 : 47                                   |
| Encoder type                       | Quadrature (A / B channels) — **two different types since Aug 2026, see below** |
| Encoder CPR (full quadrature)      | **Front (FR/FL) 186,264 · Rear (RR/RL) 93,132** counts per output revolution |
| Encoder pulses at max load (all 4) | ≈ 93 k pulses / second across the system |

**The four motors no longer carry identical encoders.** The two front units were replaced with GTK08 encoders after the original RMCS-2086 optical encoders failed (`RMCS-2086_Encoder_Replacement.md`); the rears keep the originals. They differ by exactly 2× in resolution:

| | Front — FR, FL | Rear — RR, RL |
|---|---|---|
| Encoder | GTK08 | RMCS-2086 built-in optical |
| Resolution | 1000 PPR | 500 lines |
| CPR at the wheel | 1000 × 4 × 46.566 = **186,264** | 500 × 4 × 46.566 = **93,132** |
| Supply | 5 V | 5 V |

Both are handled by a single per-motor `ENCODER_CPR[]` array in firmware, which normalises them to identical rad/s output — the mechanism, and the silent failure that results from getting it wrong, are documented in `PID_Calibration.md` §1. The motors and gearboxes themselves are unchanged and identical.

> *Why the encoder pulse rate matters: at the system-wide peak of ~93 k pulses/s, ISR-based encoder counting on an ATmega2560 saturates the CPU and corrupts the velocity estimate. This single fact is the technical reason the project migrated motor control off the Mega and onto the ESP32, whose PCNT hardware peripheral handles quadrature decoding with zero CPU overhead.*

## 3.3 Motor drivers

| **Specification**  | **Value**                                   |
|--------------------|---------------------------------------------|
| Model              | Cytron MDD20A × 2 (one per axle pair)       |
| Continuous current | 20 A per channel (2 channels per board)     |
| Operating voltage  | 6–30 V DC (set to 24 V for AisleBot)        |
| Control interface  | PWM + DIR (5 V logic compatible)            |
| Control logic      | PWM duty sets speed, DIR pin sets direction |

Each MDD20A has two independent channels. Driver \#1 controls FR and FL; Driver \#2 controls RR and RL. The 5 V logic level is upward-compatible with both ESP32 (3.3 V — needs level shifter) and Mega (5 V native, no shifter needed).

## 3.4 Wheels

| **Specification** | **Value**                             |
|-------------------|---------------------------------------|
| Model             | DekuPro 6-inch SR Mecanum Wheels (×4) |
| Outer diameter    | 152.4 mm (6 inch)                     |
| Roller angle      | 45° (standard mecanum)                |
| Wheel radius (a)  | 0.0762 m                              |
| Source            | dekuprobotics.com                     |

## 3.5 Battery and power conditioning

| **Component**       | **Specification**                                    | **Output**                                          |
|---------------------|------------------------------------------------------|-----------------------------------------------------|
| Battery             | SM12830SL LiFePO₄, 12.8 V / 30 Ah / 384 Wh           | 12.8 V DC                                           |
| Boost converter     | 1200 W DC-DC, input 8–60 V, output 12–83 V           | Set to 24 V (drives MDD20A → motors)                |
| Buck converter      | DFRobot 60 W adjustable                              | Set to 5 V (Mega, ESP32, LCD, level shifter B-side) |
| External arm supply | 24 V DC (separate)                                   | Powers NEMA 34 linear stepper through BH-MSD-6A-W   |
| Solid-state relay   | SSR-50DD: 50 A, 5–200 V switching, 3–32 V DC trigger | Main-bus disconnect, software-controllable          |

Choosing LiFePO₄ over Li-ion was a safety decision. Thermal runaway tolerance is dramatically better, the chemistry is more stable under partial-discharge cycling, and the flatter discharge curve keeps motor performance consistent until the battery is genuinely empty.

## 3.6 Level shifters

The ESP32 operates at 3.3 V logic; the motor encoders output 5 V signals, so a level shifter between them is mandatory.

**Current hardware (since 4 Aug 2026): one 8-channel discrete MOSFET (BSS138-style) bidirectional board** carrying all four encoders — both channels each — on a single part.

| **Rail / bus** | **Connects to** |
|---|---|
| `LV+` / `LV−` | ESP32 `3V3` / common GND — **LV must be the LOWER voltage** |
| `HV+` / `HV−` | Buck 5 V / common GND |
| `H0`–`H7` | Encoder A/B outputs (5 V side), in PCNT order FR, FL, RR, RL |
| `L0`–`L7` | ESP32 GPIO 36, 39, 34, 35, 32, 33, 25, 26 |

No OE pin (one of the two recurring TXS0108E failure modes is structurally impossible on this board), no external pull-ups needed (it has its own on both sides), and per-channel LEDs give a visual signal check before opening a serial monitor. Full pin-by-pin wiring: `Bench_Test_Map.md` §"Full 8-channel wiring".

*Retired:* the previous design used **two TXS0108E boards** (U1 front, U2 rear, 4 of 8 channels each). It is documented in `LevelShifter_Wiring.md`, kept for its still-valid principles — signal direction, common grounding, and the GTK08-vs-RMCS wire-colour trap. The swap rationale is in Part XVI §16.3.

Power is daisy-chained: ESP32 3V3 → U1 V_CCA → U2 V_CCA, and Buck 5 V → U1 V_CCB → U2 V_CCB. Output Enable (OE) is tied to V_CCA on both boards. This daisy-chain has been the source of two debugging episodes — a broken wire on U2 ch1/2 took down RR; a later break on U2 ch3/4 took down RL. See Part VII for details.

## 3.7 User-interface and status hardware

| **Component**             | **Specification**                                                                                   | **Role**                                                |
|---------------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| 16×2 character LCD        | I²C interface via PCF8574 backpack, address 0x27                                                    | On-robot status display: mode, wheel directions, errors |
| Xbox 360 controller       | Dual analog sticks + buttons over USB                                                               | Primary teleoperation input                             |
| ~~WiFi-based phone joystick~~ | ~~Hosted by ESP32 AP (SSID AisleBot-Control) at HTTP :80, WebSocket :81~~ | **REMOVED in firmware v3.0 (Aug 2026).** The ESP32 no longer runs a radio at all. Teleop is Pi-only; E-STOP now goes via the Pi dashboard or the serial link. See Part XVI §16.6 |

## 3.8 UV-arm subsystem (cargo handling)

Mounted above the chassis is a vertical-lift cargo arm that opens laterally to grip and release cargo. It has its own microcontroller (Mega 2560) and stepper drivers.

| **Component**            | **Specification**                                              | **Role**                                 |
|--------------------------|----------------------------------------------------------------|------------------------------------------|
| Lateral arms (×2)        | NEMA 23 stepper + TB6600 driver                                | Open / close to grip cargo               |
| Vertical lift            | NEMA 34 linear stepper + BH-MSD-6A-W driver                    | Raise / lower the platform               |
| TB6600 DIP switches      | SW1=OFF, SW2=ON; EN−=NC                                        | Microstep config and current limit       |
| BH-MSD-6A-W DIP switches | SW5=DOWN, SW6=UP, SW7=DOWN, SW8=DOWN (1600 steps/rev); ENA+=NC | Microstep configuration; accepts 24 V DC |

The arm subsystem is deliberately decoupled from the drive subsystem. The Mega serial protocol is independent, and a watchdog on the Mega (500 ms timeout) brings the steppers to a safe state if the ROS 2 bridge stops sending heartbeats.

# Part IV — Electrical and Signal Architecture

## 4.1 System block diagram

The power and signal flow, from battery to motor output, and from encoder output back to the ESP32:

> **LiFePO₄ Battery (12.8 V)**
>
> ├── Boost converter → 24 V → SSR → MDD20A ×2 → 4× Rhino RMCS-2086
>
> └── Buck converter → 5 V → Mega, LCD, level shifters (V_CCB)
>
> External 24 V → BH-MSD-6A-W → NEMA 34 linear arm
>
> **Raspberry Pi 5 (USB serial 921600 baud) ←→ ESP32**
>
> ESP32 GPIO (3.3 V) ← TXS0108E level shifters ← Motor encoders (5 V)
>
> Raspberry Pi 5 (USB serial 115200 baud) ←→ Arduino Mega 2560

## 4.2 Motor pin assignments

> *Note on left-side encoder wiring: when standing behind the robot and looking forward, the left-side motors are mounted facing the opposite direction from the right-side motors (mecanum-roller handedness requires it). On the ESP32 build, polarity correction is handled entirely in firmware via MOTOR_DIR_SIGN and ENC_DIR_SIGN arrays — no physical wire swap. See Part XII §12.4 for details.*

| **Motor** | **Driver / channel** | **PWM GPIO** | **DIR GPIO** | **Enc A GPIO** | **Enc B GPIO** |
|-----------|----------------------|--------------|--------------|----------------|----------------|
| FR        | MDD20A \#1 — CH1     | G4           | G16          | G36 (SP)       | G39 (SN)       |
| FL        | MDD20A \#1 — CH2     | G17          | G18          | G34            | G35            |
| RR        | MDD20A \#2 — CH1     | G19          | G21          | G32            | G33            |
| RL        | MDD20A \#2 — CH2     | G22          | G23          | G25            | G26            |

## 4.3 ESP32 pins to avoid (strapping pins)

GPIO 0, 2, 5, 12, and 15 are sampled at boot to determine the ESP32's operating mode. Driving these externally during a reset prevents normal boot. None of them are used in the current motor or encoder assignment. An earlier pin-assignment iteration had GPIO 2 and GPIO 5 in use — caught during a cross-check before any hardware was powered on.

## 4.4 Level-shifter wiring map

| **Shifter** | **Side A (ESP32 3.3 V)**           | **Side B (5 V)**                          | **Power**                                                |
|-------------|------------------------------------|-------------------------------------------|----------------------------------------------------------|
| U1 — front  | A1=FR-A, A2=FR-B, A3=FL-A, A4=FL-B | B1..B4 = matching encoder lines, OE=V_CCA | V_CCA from ESP32 3V3; V_CCB from Buck 5 V                |
| U2 — rear   | A1=RR-A, A2=RR-B, A3=RL-A, A4=RL-B | B1..B4 = matching encoder lines, OE=V_CCA | V_CCA from U1 V_CCA (daisy); V_CCB from U1 V_CCB (daisy) |

The daisy-chained power rails are the biggest reliability liability in the current build. Two separate encoder failures in May 2026 both traced back to broken solder joints at the level-shifter end of this chain. A future hardware revision should use point-to-point power from the regulator to each shifter, with strain relief at the connector.

## 4.5 Serial protocol summary

### ESP32 ↔ Pi (drive bus)

| **Direction** | **Frame format**                             | **Meaning**                           |
|---------------|----------------------------------------------|---------------------------------------|
| Pi → ESP32    | \<V,fr,fl,rr,rl\>                            | Set target wheel velocities (rad/s)   |
| Pi → ESP32    | \<S\>                                        | Emergency stop (latches E-STOP state) |
| Pi → ESP32    | \<P\>                                        | Ping → expect \[PONG\]                |
| Pi → ESP32    | \<G,Kp,Ki,Kd,Kff\>                           | Live PID-gain update                  |
| Pi → ESP32    | \<C0\> / \<C1\>                              | Mode: open-loop / closed-loop PID     |
| Pi → ESP32    | \<L1\> / \<L0\>                              | Enable / disable 10 Hz CSV telemetry  |
| Pi → ESP32    | \<W0\> / \<W1\>                              | Watchdog disable / enable             |
| ESP32 → Pi    | \[OK ...\] / \[PONG\] / \[WDOG\] / \[ESTOP\] | Acknowledgement and status replies    |

Baud rate is 921600 (confirmed on both sides). The firmware runs a FreeRTOS dual-core split: PID at 50 Hz on Core 1; serial, WiFi, and telemetry on Core 0.

### Mega ↔ Pi (UV-arm bus)

The Mega operates at 115200 baud. Its protocol is independent of the ESP32 bus and consumed by a separate ROS 2 node (arm_bridge.py). The arm boots into joystickMode = true, meaning the integrated joystick directly drives the steppers until ROS 2 takes over. Watchdog timeout is 500 ms.

# Part V — Software Architecture

AisleBot's software exists at three layers, each running on a different processor with a different real-time profile. Understanding the responsibility split is essential to debugging any unexpected behaviour, because failures at one layer often look like failures at another.

## 5.1 Software-layer responsibilities

| **Layer**             | **Where it runs**                           | **Real-time profile**             | **Responsibilities**                                                                            |
|-----------------------|---------------------------------------------|-----------------------------------|-------------------------------------------------------------------------------------------------|
| Planning & perception | Raspberry Pi 5 (Ubuntu 24.04 + ROS 2 Jazzy) | Soft real-time (10–50 Hz)         | Inverse kinematics, teleop, future SLAM, future Nav2, future EKF                                |
| Velocity control      | ESP32 (custom firmware)                     | Hard real-time (50 Hz loop)       | Encoder reading via PCNT, PID+FF computation, PWM/DIR output, serial protocol, WiFi joystick AP |
| Arm control           | Arduino Mega 2560 (custom firmware)         | Hard real-time (per AccelStepper) | Stepper acceleration profiles, joystick mode at boot, watchdog, ROS bridge                      |

## 5.2 ROS 2 workspace

All ROS 2 code lives in ~/ros2_ws on the Pi, structured as a standard colcon workspace built with --symlink-install so source edits don't require rebuilds for Python nodes.

The package is mecanum_robot, under src/mecanum_robot/. The active launch file is aislebot_full.launch.py, which brings up eight of the nine nodes (gazebo_bridge is excluded as it's for simulation only). The older hardware.launch.py is incomplete and deprecated — should be deleted to avoid confusion.

## 5.3 Node-by-node responsibilities

| **Node**                  | **Subscribes**                             | **Publishes**                              | **Brief**                                                                    |
|---------------------------|--------------------------------------------|--------------------------------------------|------------------------------------------------------------------------------|
| joy_to_aislebot           | /joy                                       | /cmd_vel                                   | Maps Xbox stick deflections to (u, v, ω_z)                                   |
| keyboard_teleop           | stdin                                      | /cmd_vel                                   | WASD/QE keyboard fallback                                                    |
| phone_dashboard           | /wheel_velocities_actual, /motor_telemetry | /cmd_vel, /arm/command                     | FastAPI server on :8080 for phone-based control + live telemetry CSV logging |
| mecanum_teleop_asymmetric | /cmd_vel                                   | /wheel_speeds                              | Asymmetric inverse-kinematics computation                                    |
| esp32_bridge              | /wheel_speeds, /estop                      | /wheel_velocities_actual, /motor_telemetry | Encodes \<V,...\> frames at 50 Hz; parses ESP32 replies                      |
| odometry_publisher        | /wheel_velocities_actual                   | /odom, tf (odom→base_link)                 | Forward-kinematics integration                                               |
| arm_bridge                | /arm/command                               | /arm/status                                | Stepper commands to Mega via separate serial port                            |
| lcd_display               | /wheel_velocities_actual, /system_state    | (I²C → LCD)                                | Live status on the on-robot 16×2 screen                                      |
| gazebo_bridge             | /wheel_speeds                              | /cmd_vel (sim)                             | Used only when simulating in Gazebo on the laptop                            |

## 5.4 udev rules — stable device naming

Without udev rules, the ESP32 and Mega get assigned /dev/ttyUSB0 vs /dev/ttyUSB1 depending on plug order. Fragile. The rules below pin them by USB vendor/product ID:

> \# /etc/udev/rules.d/99-aislebot.rules
>
> SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="esp32"
>
> SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="mega"

After the rules are reloaded, the launch file references /dev/esp32 and /dev/mega. Plug order no longer matters.

## 5.5 ESP32 firmware — aislebot_esp32_v2.ino

Five major design decisions in the active firmware:

- PCNT hardware peripheral for all four encoder channels — zero CPU overhead, full quadrature decoding.

- Dual-core FreeRTOS partition: Core 1 runs only the PID loop at 50 Hz; Core 0 handles serial, WiFi, telemetry.

- PID + Feedforward per motor, with anti-windup (INTEGRAL_MAX = ±200), derivative on filtered error (D_FILTER_ALPHA = 0.3), velocity filtering (VEL_FILTER_ALPHA = 0.5), and a minimum-PWM deadband (MIN_PWM = 15).

- E-STOP latches and does not auto-clear — a previous bug had the E-STOP clear itself on the next velocity command; now correctly held until an explicit \<C1\> clear command.

- Telemetry off by default; \<L1\> turns on 10 Hz CSV streaming.

### Current PID parameters (as of 14 May 2026)

| **Parameter**    | **Value** | **Notes**                                          |
|------------------|-----------|----------------------------------------------------|
| Kp               | 50        | Proportional gain                                  |
| Ki               | 30        | Integral gain                                      |
| Kd               | 3         | Derivative (acts on filtered velocity)             |
| Kff (FR)         | 42.1      | PWM per (rad/s) — air-calibrated                   |
| Kff (FL)         | 40.2      | Air-calibrated; later re-measurement suggests 46.9 |
| Kff (RR)         | 43.7      | Air-calibrated; later re-measurement suggests 45.3 |
| Kff (RL)         | 47.9      | Air-calibrated; later re-measurement suggests 48.4 |
| INTEGRAL_MAX     | ±200      | Anti-windup clamp                                  |
| MIN_PWM          | 15        | Deadband — anything below is set to 0              |
| VEL_FILTER_ALPHA | 0.5       | EMA on raw velocity                                |
| D_FILTER_ALPHA   | 0.3       | EMA on derivative term                             |
| Loop rate        | 50 Hz     | 20 ms per cycle                                    |

## 5.6 Arduino Mega firmware — aislebot_arm_v7.ino

The Mega drives the UV arm only. It uses the AccelStepper library for stepper-acceleration profiling, a 500 ms watchdog, and boots with joystickMode = true so the arm responds to the joystick the moment power is applied. A previous version had auto_enable_on_connect = false on the bridge side, meaning the steppers never actually energised when ROS 2 connected. Fixed in the current build.

## 5.7 Networking configuration

| **Link**               | **Subnet / address**                        | **Purpose**                                                           |
|------------------------|---------------------------------------------|-----------------------------------------------------------------------|
| Pi WiFi (college SSID) | 10.53.6.122 / 16                            | Primary network when in the lab                                       |
| Pi eth0 (laptop ICS)   | 192.168.137.x                               | Pi powered + tethered to Windows laptop's Internet Connection Sharing |
| ~~ESP32 WiFi (AP mode)~~ | ~~SSID AisleBot-Control~~                  | **REMOVED in v3.0** — ESP32 hosts no network. Part XVI §16.6          |
| Phone dashboard        | http://10.53.6.122:8080/                    | FastAPI/uvicorn UI served by phone_dashboard.py                       |

SSH access is over ethernet only — keeps the WiFi link free of bulk file transfers and avoids the latency variation that comes with college WiFi.

# Part VI — The Control Journey

This is the narrative core of the journal. The chronological story of how AisleBot's motor-control stack evolved from open-loop PWM commands to a validated closed-loop PID + feedforward controller on dedicated hardware. Each milestone explains what was tried, what worked, what didn't, and what came next.

## 6.1 Genesis — v3.0 open-loop system (Jan–Mar 2026)

The first complete iteration was an open-loop system. The Raspberry Pi 5 running ROS 2 Jazzy did inverse kinematics and shipped a four-tuple of wheel velocities to an Arduino Mega 2560 over USB serial at 115200 baud. The Mega translated each velocity into a PWM duty and a direction bit, and drove the four Cytron MDD20A channels. No encoder feedback in the control loop. The motors ran at whatever speed their internal characteristics dictated for a given PWM.

This worked in the loose sense that the robot moved when you pressed a key. The serial protocol was finalised, the inverse-kinematics validated with eight self-test cases at startup, the Cytron drivers behaved well, and the Pi-ROS-Mega-Driver chain was stable. The Aislebot v3 Open-Loop Manual (March 2026) is the artefact from this period.

## 6.2 The strafing stutter — diagnostics (Mar 2026)

The first signal that open-loop wasn't enough showed up during strafing tests. Forward and backward looked fine. Rotating in place looked fine. But strafing produced a visible stutter and audible chatter from the chassis.

A characterisation run at a fixed PWM of 120 across all four motors, with encoders sampled at 20 Hz, explained everything.

| **Motor** | **Mean (rad/s)** | **Std Dev** | **CV %** | **% of fastest**              |
|-----------|------------------|-------------|----------|-------------------------------|
| FL        | 2.983            | 0.0075      | 0.33%    | 100.0% (fastest)              |
| FR        | 2.853            | 0.0195      | 1.33%    | 95.6%                         |
| RR        | 2.743            | 0.0437      | 2.25%    | 91.9%                         |
| RL        | 2.507            | 0.0510      | 4.57%    | 84.0% (slowest — 16% deficit) |

RL was both the slowest motor and the most variable. But the deeper problem was this: during strafing, the mecanum wheels work as diagonal pairs — FR↔RL together, FL↔RR together. The FR↔RL pair had an 11–13% speed mismatch. Any time that pair was supposed to do equal work, one wheel was doing 12% more. That imbalance produced a net rotational torque that fought the lateral motion. The chassis tried to yaw while strafing, and the mecanum rollers fought back with friction. Result: the stutter.

> *Insight crystallised here: open-loop control is acceptable when motors are well-matched, or when you only care about going forward. The moment you need a pair of motors to act in concert, you need closed-loop feedback. The mecanum geometry made this inescapable for AisleBot.*

## 6.3 The plan — closed-loop PID + feedforward

The control architecture chosen was the textbook PID + feedforward velocity controller, one instance per motor. The reasoning behind each piece:

- Feedforward (Kff × target) provides an immediate, motor-specific PWM estimate from the start of a step input — no waiting for the PID to discover the right PWM through error accumulation.

- Proportional (Kp × error) gives speed of response.

- Integral (Ki × ∫error) eliminates steady-state error by accumulating a persistent offset.

- Derivative (Kd × d(error)/dt) damps overshoot — acts on a filtered version of the velocity signal to limit encoder noise amplification.

Per-motor feedforward calibration came from the open-loop data — take the speed each motor achieves at PWM 120, invert to PWM-per-(rad/s):

| **Motor** | **Speed at PWM 120 (rad/s)** | **PWM per (rad/s) = Kff** |
|-----------|------------------------------|---------------------------|
| FL        | 2.983                        | 40.2                      |
| FR        | 2.853                        | 42.1                      |
| RR        | 2.743                        | 43.7                      |
| RL        | 2.507                        | 47.9                      |

These Kff values say something physical: at a given commanded velocity, RL needs roughly 19% more PWM than FL to produce the same shaft speed. The cause — bearing friction, brush wear, gearbox losses — doesn't matter for the control loop. What matters is that each motor gets the right head start.

## 6.4 Migrating from Arduino Mega to ESP32

Implementing closed-loop control required encoder feedback, and that immediately exposed a hardware limit. The Rhino RMCS-2086 motors have 93,132 counts per output revolution in full-quadrature mode. At 60 RPM, each motor produces about 93,132 × 60 / 60 = ~93 k counts per second. Four motors together: nearly 372 k pulses per second.

The ATmega2560 cannot service interrupt-based encoder counting at this rate. At 372 kHz, every CPU cycle is consumed by encoder ISRs. Velocity estimates become corrupt, the main loop misses deadlines, and the PID loop can't run reliably.

The ESP32 solves this with hardware. Its PCNT peripheral has dedicated silicon for quadrature decoding — no CPU involvement once configured. Four PCNT units operate in parallel, each handling one motor's A and B channels, counting up to a 16-bit limit with hardware overflow handling. The CPU reads the count whenever convenient; the count never lies, never drifts, never misses pulses.

The migration also brought ancillary benefits: WiFi for a phone-based joystick fallback, dual-core for a clean separation between control loop and communication, and 240 MHz clock for comfortable timing margin on the PID computation.

## 6.5 The wheel-radius bug

Early ESP32 firmware iterations had a wheel radius of 0.05 m baked in. The actual radius is 0.0762 m. That's a 52% error in the velocity-to-RPM mapping. Every commanded velocity was 52% off from what the robot actually tried to produce, and every measured velocity was 52% off from what the encoder data actually meant.

The symptom: the robot moved at roughly half the expected speed for a given linear-velocity command, and encoder velocities never matched targets even with extreme Kp. The fix was a single constant. The lesson was that constants matter and must be checked against the physical wheel, not against a similar-sounding component.

## 6.6 The CPR bug

A related but distinct unit-scaling bug: early firmware used an encoder CPR of 2,068, derived from a motor that was not the Rhino RMCS-2086. The correct full-quadrature CPR is 46,566 per gearbox-output revolution. The ratio between the two is 22.5×.

The firmware computed velocities about 22× lower than actual physical velocity. The PID couldn't converge because the feedback signal was telling it the motor was nearly stopped even when the wheel was spinning at full speed.

The debug methodology that caught it was elimination: does it work in open loop? Yes. So the bug is in the feedback loop. Is the velocity reading correct? No — reads 70 when commanded 3. That's a 22× discrepancy. Is the CPR right? 2068 vs needed 46,566 = 22.5×. Match.

> *Lesson encoded in this episode: always isolate before tuning. If the loop is doing something inexplicable, take the loop apart. Run open-loop and verify physical motion. Verify the encoder signal is being read correctly. Verify the unit conversion from pulses to rad/s. Only then is it worth touching PID gains. Tuning a loop with a corrupt feedback signal can take days and produce only fragile, accidental near-stability.*

## 6.7 The asymmetric-kinematics propagation bug

The asymmetric design is the project's central novelty. It must propagate through every control path: the ROS 2 teleop_asym node, the Gazebo bridge, the wheel-odometry forward kinematics, and the ESP32 WiFi joystick handler. If any one of these uses a symmetric K value, that code path is driving a normal symmetric mecanum platform — the geometric novelty is silently lost in that branch.

This is exactly what happened in the ESP32 WiFi joystick path. It used a single composite K value for all four wheels. The fix was straightforward — replace it with K_outer for FR/RL and K_inner for FL/RR — but the lesson was structural: every control-path entry must use the asymmetric kinematics module, and there must be a regression check that catches a symmetric-K regression.

## 6.8 Speed-scaling consistency

A subtler bug: the three layers of the stack each had their own ceiling on commanded velocity, and they didn't match.

| **Layer**                       | **Old (mismatched) limit**                    | **Corrected limit (v3.0, Mar 2026)**   |
|---------------------------------|-----------------------------------------------|----------------------------------------|
| Teleop node (ROS 2)             | MAX_LINEAR = 1.0 m/s, MAX_ANGULAR = 1.0 rad/s | MAX_LINEAR = 0.15, MAX_ANGULAR = 0.3   |
| esp32_bridge                    | max_wheel_speed = 6.28, use_pid varied        | max_wheel_speed = 3.0, use_pid = false |
| ESP32 firmware (SAFE_MAX_RAD_S) | absent / inconsistent                         | 3.0 rad/s clamp at firmware level      |

The visible symptom: at about 46% joystick deflection, the motors saturated and stopped scaling further with stick input. That 46% corresponded to the ratio of the bridge's effective ceiling to the teleop ceiling. Once recognised, it immediately pointed at the mismatch. After alignment, the response scaled smoothly across the full deflection range.

## 6.9 The encoder-wiring failures (May 2026)

Two encoder failures occurred during the PID validation campaign, both at the TXS0108E level-shifter boards. The diagnostic signature of a level-shifter break is distinctive and worth recording: the PCNT count reads exactly zero with a standard deviation of exactly zero. Real motors, even when not moving, produce some noise — bearing micro-motion, electrical noise on the encoder lines, ground bounce. A perfectly zero signal with zero variance is not a motor that's sitting still. It's an encoder line that's not connected.

- First failure: RR encoder. Wiring break at U2 channel 1/2 (RR-A / RR-B). Repair was a re-solder.

- Second failure: RL encoder, discovered after RR was fixed. Wiring break at U2 channel 3/4 (RL-A / RL-B). Same repair.

During the RR failure investigation, the bench power supply was current-limiting under PID load — a second fault compounding the first, producing confusing voltage sag and misleading symptoms. The right diagnostic methodology was eventually:

> *Encoder-isolation diagnostic: 1) Disconnect level-shifter boards or jumper them out. 2) Run the motor in open-loop mode (\<C0\>, then \<T,...\>). 3) Confirm physical rotation. 4) Reconnect the level shifter and re-run open-loop. 5) Enable closed-loop (\<C1\>). If PID misbehaves but open-loop was fine, the encoder feedback path is the problem. 6) Read raw PCNT counts directly: any motor returning identically zero with zero variance during commanded rotation has a broken encoder line.*

## 6.10 May 14 2026 — PID validation run

With all encoder wiring repaired, the bench supply replaced by the LiFePO₄ battery, and PID parameters as listed in §5.5, a multi-axis manoeuvre was run with the robot elevated and wheels spinning free in the air.

| **Metric**            | **Result**                                                            |
|-----------------------|-----------------------------------------------------------------------|
| Tracking accuracy     | 99–100% across all four motors                                        |
| RMS tracking error    | 0.12 rad/s                                                            |
| PWM saturation events | 0% of the run                                                         |
| Target velocity range | ±0.6 to ±2.2 rad/s                                                    |
| Worst settling time   | FL at 3.79 s (consistent with FL having the smallest Kff in firmware) |

First run in the project's history where every motor tracked every commanded velocity profile across forward, backward, strafe, and rotation manoeuvres. Phase 1 is validated for in-air operation.

## 6.11 Re-calibration insight from the validation data

Back-calculating Kff from the steady-state PWM/velocity ratios of the validation run produced new air-load estimates that differ from the firmware values.

| **Motor** | **Firmware Kff** | **Measured (air)** | **Delta**                                    |
|-----------|------------------|--------------------|----------------------------------------------|
| FR        | 42.1             | 46.9               | −10% (firmware undercalibrated)              |
| FL        | 40.2             | 46.9               | −14% (worst — explains 3.79 s settling time) |
| RR        | 43.7             | 45.3               | −4%                                          |
| RL        | 47.9             | 48.4               | ≈ 0%                                         |

The integral term has been silently absorbing the under-calibration. At steady state the controller is fine, but transient response is slower than it could be because Kff isn't doing as much work as intended. Updating FR and FL Kff to ~47 would tighten settling times. The decision was made to defer this until ground testing — ground-load Kff values are expected to be 10–30% higher than air-load anyway, so recalibrating twice would be wasted effort.

## 6.12 Telemetry pipeline

During PID development, a telemetry-logging pipeline was built into phone_dashboard.py. CSV format is 13 columns: pi_time_s (Unix epoch), then for each of FR / FL / RR / RL: target rad/s, actual rad/s, PWM. The analysis notebook aislebot_pid_analysis_v2.py turns the CSV into per-motor tracking plots, PWM-saturation bars, and step-response settling times.

> *Two metrics in the analysis notebook are unreliable — ignore them. The 'Cross-Motor Diagonal Deviation' metric subtracts across the whole run, which only makes sense in pure forward/backward motion. And the 'Interpretation flags' text hardcodes phrases like 'RL weakest' even when the plot data clearly disagrees. Trust the per-motor plots and the PWM-saturation bar (Plot 3C). Ignore the auto-summary prose.*

**Browser-based alternative (added v2.0):** `docs/tools/telemetry_analyzer.html` reads the same 13-column CSV directly in the browser — no Python environment needed. It correctly separates diagonal mismatch per-motor rather than deviation-only, and its findings panel is data-driven (flags dead encoder feedback, saturation, and telemetry gaps from the actual numbers) rather than the hardcoded phrases the notebook has. Verified against a synthetic run with an injected feedback dropout and saturation window before being added to the repo — it caught both correctly. Prefer it for a quick look; keep the notebook for anything needing further numeric post-processing in Python.

## 6.13 Current debugging focus

Work currently in progress focuses on the motor-controller firmware, with commands sent over the serial monitor before changes are migrated to the ROS 2 bridge. Reported symptoms guiding this iteration: motors stopping unexpectedly, audible vibration, and command non-compliance in particular scenarios. The plan is to iterate on the firmware in isolation — serial monitor in, motor response out — until the behaviour is clean across all manoeuvres, then promote the change to the ROS 2 path.

This section will be appended as each debugging iteration completes, with the firmware version, the change, the symptom resolved, and any new symptom that emerged.

# Part VII — Hurdles and Resolutions

A curated catalogue of every meaningful hurdle, with the symptom, the diagnostic, the fix, and the lesson. Oldest first.

## 7.1 Wrong encoder CPR (Jan 2026)

|                |                                                                                                                                           |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | PID would not converge. Velocity reading was ~22× lower than expected (showed ~70 when commanded ~3).                                     |
| **Root cause** | Encoder CPR set to 2,068 — value from a similar but different motor. Correct value for Rhino RMCS-2086 is 46,566.                         |
| **Diagnostic** | Compared expected vs actual encoder count for one full revolution by hand. Ratio came out to 22.5× — matched the CPR ratio exactly.       |
| **Fix**        | Update CPR constant. PID then converged smoothly.                                                                                         |
| **Lesson**     | Verify hardware specifications against the actual part, not a similar one. Always isolate the feedback path before tuning the controller. |

## 7.2 Wrong wheel radius

|                |                                                                                                              |
|----------------|--------------------------------------------------------------------------------------------------------------|
| **Symptom**    | Robot moved at approximately half the expected linear speed for every commanded velocity.                    |
| **Root cause** | r_w = 0.05 m hard-coded; actual wheel radius is 0.0762 m. Off by a factor of 1.524.                          |
| **Diagnostic** | Compared measured chassis displacement against integrated command over a known straight-line run.            |
| **Fix**        | Update r_w = 0.0762 m everywhere.                                                                            |
| **Lesson**     | Wheel radius enters every linear-velocity computation. Wrong radius silently corrupts everything downstream. |

## 7.3 Asymmetric kinematics not propagated

|                |                                                                                                                                                  |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | WiFi joystick path produced behaviour inconsistent with the ROS 2 teleop path — robot felt different in the two modes.                           |
| **Root cause** | ESP32 WiFi joystick handler used a single symmetric K value for all four wheels.                                                                 |
| **Diagnostic** | Cross-checked inverse-kinematics output between teleop_asym and ESP32 WiFi handler for identical input. Outputs diverged.                        |
| **Fix**        | Replace single K with K_outer for FR/RL and K_inner for FL/RR throughout the WiFi handler.                                                       |
| **Lesson**     | Every control-path entry must use the same asymmetric kinematics module. A regression check on this is now part of the firmware self-test suite. |

## 7.4 ATmega encoder ISR saturation

|                |                                                                                                                        |
|----------------|------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | On Mega-based prototype, velocity readings became erratic at higher speeds; main loop missed deadlines.                |
| **Root cause** | ISR-based quadrature counting on Mega cannot service ~93 k pulses/s × 4 motors. CPU consumed entirely by encoder ISRs. |
| **Diagnostic** | Timed the encoder ISR; multiplied by expected pulse rate; result was \>100% CPU utilisation.                           |
| **Fix**        | Migrate motor control to ESP32, using the PCNT hardware peripheral for quadrature decoding. CPU overhead becomes zero. |
| **Lesson**     | Some problems are not software-solvable. Choose hardware that matches the workload.                                    |

## 7.5 ESP32 strapping-pin hazard

|                |                                                                                                                                                     |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | Initial pin assignment had GPIO 2 and GPIO 5 used for motor/encoder signals. ESP32 might have failed to boot when connected to the driver hardware. |
| **Root cause** | GPIO 0, 2, 5, 12, 15 are sampled at boot to determine flash voltage and download mode. External drive prevents normal boot.                         |
| **Diagnostic** | Cross-checked the pin assignment against an ESP32 datasheet excerpt with a secondary AI tool (Gemini), before powering on with the new wiring.      |
| **Fix**        | Move all motor/encoder lines off strapping pins to safe GPIOs.                                                                                      |
| **Lesson**     | Cross-check safety-critical pin assignments with an independent reference before applying power.                                                    |

## 7.6 Encoder polarity from mounting direction

|                |                                                                                                                                                                                                   |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | FL and RL encoders produced opposite-signed counts from FR and RR when the robot moved forward.                                                                                                   |
| **Root cause** | Left-side motors are mounted facing the opposite direction from right-side motors (a consequence of mecanum-roller handedness).                                                                   |
| **Diagnostic** | Single-motor rotation test with manual count inspection.                                                                                                                                          |
| **Fix**        | On the current ESP32 build: polarity corrected in firmware via MOTOR_DIR_SIGN and ENC_DIR_SIGN arrays (§12.4). The v3 Mega era used a physical wire swap — that approach is now retired.          |
| **Lesson**     | Direction inversion in a PID feedback signal turns the controller into a positive-feedback oscillator. Software correction must be applied consistently to both the motor drive and encoder read. |

## 7.7 Speed-scaling mismatch — saturation at 46%

|                |                                                                                                                                         |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | At ~46% joystick deflection, the response saturated; further stick movement produced no additional motion.                              |
| **Root cause** | Teleop, bridge, and firmware each had different velocity ceilings. The first to saturate clamped the chain.                             |
| **Diagnostic** | Logged each layer's effective output for a sweep of input. Identified the layer that clamped first.                                     |
| **Fix**        | Aligned MAX_LINEAR = 0.15 m/s and MAX_ANGULAR = 0.3 rad/s in teleop; max_wheel_speed = 3.0 in bridge; SAFE_MAX_RAD_S = 3.0 in firmware. |
| **Lesson**     | Limits at every layer must agree. The smallest one always wins, and that fact must not be hidden inside a layer the user can't see.     |

## 7.8 Phantom disconnections — ping health check

|                |                                                                                                                        |
|----------------|------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | arduino_bridge.py reported a disconnection every 5 seconds, even though communication was working.                     |
| **Root cause** | A periodic ping-based health check was racing with regular traffic and sometimes timing out.                           |
| **Diagnostic** | Disabled the health check temporarily — disconnections stopped.                                                        |
| **Fix**        | Removed the ping-based health check entirely. The bridge now treats arrival of normal traffic as evidence of liveness. |
| **Lesson**     | Don't add a heartbeat that competes for the same channel as the data it's supposed to be testing.                      |

## 7.9 LCD wheel-direction logic wrong

|                |                                                                                                                                                                 |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | On-robot LCD showed wrong direction labels during certain manoeuvres (e.g. 'FWD' during a tight rotation).                                                      |
| **Root cause** | Direction-decision code used a chain of threshold if/elif comparisons that didn't handle dominance correctly when two wheel velocities were close in magnitude. |
| **Diagnostic** | Hand-traced the decision logic for several known manoeuvres.                                                                                                    |
| **Fix**        | Replaced threshold elif chain with a dominance comparison: classify the manoeuvre by which body-velocity component is largest in magnitude (v_x, v_y, or ω_z).  |
| **Lesson**     | If/elif threshold chains are fragile when signals are noisy. Prefer winner-takes-all dominance for categorical labelling.                                       |

## 7.10 E-STOP auto-clear bug

|                |                                                                                                                       |
|----------------|-----------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | After a software E-STOP, the next velocity command silently re-enabled the motors — defeating the point of the latch. |
| **Root cause** | E-STOP state was reset implicitly on receipt of any new command in an early firmware revision.                        |
| **Diagnostic** | Followed the E-STOP code path; saw the implicit reset.                                                                |
| **Fix**        | Made E-STOP a sticky state cleared only by an explicit \<C1\> (resume closed-loop) command.                           |
| **Lesson**     | Safety states must be sticky. Any code path that implicitly clears them is a bug, no exceptions.                      |

## 7.11 arm_bridge.py — auto_enable_on_connect

|                |                                                                                                                                                                     |
|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | When the ROS 2 stack came up, the UV arm steppers appeared to receive commands but did not move.                                                                    |
| **Root cause** | auto_enable_on_connect was set to False. The bridge connected to the Mega but never issued the ENABLE command. Steppers received step pulses but weren't energised. |
| **Diagnostic** | Tried sending ENABLE manually from a separate terminal — arm responded. Read bridge source — found the flag.                                                        |
| **Fix**        | auto_enable_on_connect = True.                                                                                                                                      |
| **Lesson**     | Default values must produce a working system. 'Disabled by default for safety' sounds prudent but breaks things when not paired with a clear path to enable.        |

## 7.12 Encoder wiring failures — TXS0108E (May 2026)

|                |                                                                                                                                                                                                                               |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | RR motor read encoder count exactly 0 with σ = 0 even while the motor spun. PID saturated PWM trying to chase a non-changing feedback signal. After RR fix, identical signature appeared on RL a few sessions later.          |
| **Root cause** | Broken solder joint on the V_CCB-side daisy-chain at the TXS0108E (U2 channel 1/2 for RR; later U2 channel 3/4 for RL).                                                                                                       |
| **Diagnostic** | Encoder-isolation procedure (§6.9). The σ = 0 reading was the unique fingerprint of a disconnected encoder line.                                                                                                              |
| **Fix**        | Re-solder each joint. Tested by direct PCNT count inspection during a hand-rotation of the wheel.                                                                                                                             |
| **Lesson**     | Identical-zero readings with zero variance are not 'no motion' — they are 'no signal'. A real stationary motor produces some jitter, never exact zero. This fingerprint is now the first check before touching anything else. |

## 7.13 Bench-supply current-limiting confound

|                |                                                                                                                                                                                     |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Symptom**    | Voltage sag during PID runs, motors stalling intermittently, supply LED flickering.                                                                                                 |
| **Root cause** | Bench supply was current-limited at a level below peak PID demand. Aggravated by the encoder-wiring failure in §7.12 — PID was commanding full PWM trying to chase broken feedback. |
| **Diagnostic** | Switched to LiFePO₄ battery. Symptoms changed character — confirmed supply was at least part of the problem.                                                                        |
| **Fix**        | Use the battery for any PID-validation runs. Reserve bench supply for low-load firmware development.                                                                                |
| **Lesson**     | Two-fault situations are deceptive. If the symptom doesn't disappear after fixing what you thought was the cause, there's at least one more fault to find.                          |

# Part VIII — Key Learnings and Principles

Lessons distilled from the journey so far. These should guide every future decision on the project.

## 8.1 Hardware decisions are architectural

The Mega-to-ESP32 migration was not a software refactor — it was a hardware-driven necessity. ISR-based encoder counting at this pulse rate is not solvable in software on the Mega. No amount of clever interrupt prioritisation makes it work. The PCNT peripheral on the ESP32 is the architectural answer. Generalising: when a workload exceeds what the chosen processor can do, the answer is usually to change the processor, not to spend weeks finding the smartest workaround that still won't be enough.

## 8.2 Asymmetric kinematics must propagate everywhere

Every control entry point — ROS 2 teleop, Gazebo bridge, wheel odometry, ESP32 WiFi joystick, future Nav2 paths — must use the same asymmetric kinematics module. If even one branch uses a symmetric K, the project's central novelty is silently lost in that branch. The cleanest implementation is a single shared kinematics utility that every entry point calls. The second cleanest is a regression check that catches a symmetric-K regression.

## 8.3 Foundational constants must come from the physical part

Wheel radius, encoder CPR, gear ratio. These must come from a tape-measure reading, the vendor datasheet for the exact part on the chassis, or a hand-counted rotation test. Values from a similar component will silently corrupt every downstream computation in ways that look like control problems.

## 8.4 Always isolate before tuning

When a closed-loop system misbehaves, the first instinct is to retune the loop. That is almost always the wrong first move. Open the loop. Verify the actuator. Verify the sensor. Verify the unit conversions in the feedback path. Only after the components are individually known-good is it worth touching gains. Tuning a controller against a corrupt feedback signal can take days and produce only fragile, accidental near-stability. Isolation takes minutes.

## 8.5 Limits must agree at every layer

If teleop says 1 m/s but the bridge clamps at 0.5 and the firmware clamps at 0.3, the system saturates at 0.3 and the rest of the headroom is dead. The signature is response that scales smoothly up to some fraction of the input and then flattens. Every layer's clamp must be explicit, documented, and consistent with the others.

## 8.6 Safety states must be sticky

Emergency stop, watchdog timeout, and any other 'something is wrong, stop' state must require an explicit, deliberate clear action. Auto-clearing on the next normal command is a bug, every time, regardless of how convenient it seems.

## 8.7 The σ = 0 encoder fingerprint

A real, stationary motor produces some level of jitter in its encoder readings. A perfectly zero reading with exactly zero variance, especially during a commanded motion, is the signature of a broken signal path, not a stationary motor. This is now the first check when a motor 'isn't responding'.

## 8.8 RL is the weakest link

Across every characterisation run before PID, RL has been the slowest and most variable motor. The FR↔RL diagonal mismatch was the primary stutter source during strafing. Closed-loop PID compensates — RL simply gets more PWM than FL for the same target. But the mechanical asymmetry is worth remembering. If a future debug session shows behaviour that varies by manoeuvre direction, suspect FR↔RL first.

## 8.9 Prefer hardware validation over simulation-only results

Simulation is useful for checking that the math is consistent, and for end-to-end integration testing. But final claims about controller performance must come from real motors on a real surface, because the things that make control hard — friction, encoder noise, motor variance, surface conditions — are exactly what simulation doesn't capture by default.

## 8.10 Centre-of-mass eccentricity matters only under load

The asymmetric wheel placement means the geometric centre and the centre of mass don't coincide exactly. For single-motor velocity control with wheels free, this is irrelevant. For trajectory tracking with cargo, especially during cornering and strafing, it becomes a measurable effect. Worth measuring once cargo loads are characterised in Phase 5.

## 8.11 Documentation style — theory first, then implementation

The pattern that has produced clean understanding throughout this project: explain the principle first, derive what it implies, then point at the code. The reverse — paste code, then try to extract the principle — has produced gaps and confusion. This journal follows the theory-first style, and future updates should too.

# Part IX — Current Status (Snapshot, 16 May 2026)

This part is the most update-prone in the journal.

## 9.1 What works

- Closed-loop PID + feedforward velocity control on the ESP32, validated in air on 14 May 2026.

- All four encoder channels reading correctly through the TXS0108E level shifters.

- ROS 2 stack on the Pi (mecanum_robot package) — 9 nodes, single launch file (aislebot_full.launch.py), 9 console_scripts in setup.py.

- udev rules pin ESP32 to /dev/esp32 and Mega to /dev/mega regardless of plug order.

- WiFi joystick (phone or laptop browser to ESP32 AP) driving the motors.

- Xbox-controller path through joy_node → joy_to_aislebot → teleop_asym → esp32_bridge → ESP32, end-to-end.

- Phone dashboard at http://10.53.6.122:8080/ for live telemetry.

- UV-arm firmware (aislebot_arm_v7.ino) on the Mega correct and responsive.

- systemd service + start_aislebot.sh autostart the full stack on boot, with CycloneDDS loopback and explicit waits for /dev/esp32 and /dev/mega.

## 9.2 What is in flight

- Active debugging of motor behaviour: motors stopping unexpectedly, audible vibration, command non-compliance in specific scenarios. Iteration is on the motor-controller firmware, driven from the serial monitor in isolation.

- Ground-truth Kff calibration — air values are known to be 4–14% under-calibrated based on the May 14 back-analysis; ground values expected 10–30% higher again.

- ROS 2 → ESP32 serial path under motor load has not yet been stress-tested at full PID throughput with battery power.

## 9.3 Active firmware versions

| **Microcontroller** | **Firmware filename** | **Baud** | **Last confirmed state**                                                                                           |
|---------------------|-----------------------|----------|--------------------------------------------------------------------------------------------------------------------|
| ESP32 (drive)       | aislebot_esp32_v2.ino | 921600   | Validated 14 May 2026: PCNT PID 50 Hz, Kp=50, Ki=30, Kd=3, Kff per-motor, E-STOP latches, telemetry off by default |
| Arduino Mega (arm)  | aislebot_arm_v7.ino   | 115200   | AccelStepper, watchdog 500 ms, joystickMode=true at boot. Bridge auto_enable_on_connect=true.                      |

## 9.4 Outstanding TODOs

- Update start_aislebot.sh to wait for /dev/esp32 (currently still references ttyUSB0 in some branches).

- Add ENABLE button to phone dashboard for the arm.

- Stress-test the ROS 2 → ESP32 serial path with motors under battery-powered load.

- Measure UV-arm vertical travel limits and store them in the arm firmware as soft limits.

- Complete UV-arm ROS 2 integration: command topics for OPEN, CLOSE, RAISE, LOWER, and HOME procedures.

- Begin in-the-loop firmware debugging iterations as described in §9.2.

## 9.5 Workspace and tooling state

- Workspace: ~/ros2_ws, built with colcon build --symlink-install.

- RPLCD installed (for LCD). fastapi + uvicorn installed (for phone dashboard).

- Pi network IP on college WiFi: 10.53.6.122. SSH access exclusively over ethernet.

- Simulation: WSL2 Ubuntu 24.04 on Windows laptop with ROS 2 Jazzy desktop for Gazebo. Phase-C kinematics verified: 0.1 m/s forward → \[1.3123, 1.3123, 1.3123, 1.3123\] rad/s on /wheel_speeds.

**UV-C Tube Lighting Subsystem**

*Power Architecture, Staged Relay Switching, and Dashboard Integration*

|                 |                                                                                                                                                                                                           |
|-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Field**       | **Detail**                                                                                                                                                                                                |
| Status          | AS-BUILT: software live on robot; two hardware items still open (see §9)                                                                                                                                  |
| Author          | Aritra Das (Roll 25D0074), IIT Bombay, Dept. of Biosciences and Bioengineering                                                                                                                            |
| Supervisor      | Prof. Ambarish Kunwar                                                                                                                                                                                     |
| Date            | Compiled 22 June 2026; to be inserted as the next versioned Part of AisleBot_Research_Journal.docx                                                                                                        |
| Subsystem owner | Arduino Mega 2560 (aislebot_arm_v8.ino), sharing the Mega with the existing TB6600 + BH-MSD arm motion control; UV lighting and arm motion run as independent, non-blocking control loops on the same MCU |
| Related files   | aislebot_arm_v8.ino · arm_bridge.py · phone_dashboard.py · AisleBot_UV_Arm_System_v1.docx (hardware baseline)                                                                                             |

# 1. Purpose and Scope

This section documents the UV-C tube lighting subsystem end to end: the physical hardware identified from bench photographs, the power architecture finally settled on, the relay wiring and the cross-inverter safety rule it depends on, the Arduino firmware that drives the staged switching, the ROS2 / phone-dashboard integration that lets the cycle be triggered remotely, and the deployment that put all of it on the robot on 22 June 2026.

The UV lighting load shares the Arduino Mega 2560 with the disinfection arm steppers (aislebot_arm_v7.ino → v8) and shares the arm's 12.8V LiFePO4 battery. Nothing about the arm's motion control changed; the lighting subsystem was added alongside it as an independent control path with its own serial commands, its own relay hardware, and its own safety interlock through the existing ESTOP latch.

This is a living-document section in the same convention as the rest of the journal: hardware decisions are recorded with the reasoning that produced them, including the approaches that were considered and superseded, because that reasoning is part of the record.

# 2. Hardware Inventory (Identified from Bench Photographs)

Seven bench photographs were used to positively identify the ballast and inverter stock on hand before any wiring decision was made. Findings:

## 2.1 Ballasts on hand

|                                      |                                                            |                                              |                                                                                                          |
|--------------------------------------|------------------------------------------------------------|----------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **Ballast**                          | **Input**                                                  | **Rated for**                                | **Disposition**                                                                                          |
| Philips Sumo Xtreme EB-FN X 136      | 240VAC, 0.19A, auto shutdown on overvoltage/defective lamp | 1× TLD 36W / TL 40W                          | SELECTED: all six tubes standardised on this unit                                                        |
| Philips EB-T 136 TLD (EB-Transalume) | 240VAC, 0.15A, PF 0.98, rapid start                        | 1× TLD 36W                                   | Identified as an equally valid alternative; not used once six matching Sumo units were confirmed on hand |
| Philips EB-S 114 (EB-Standard)       | 220–240VAC, 0.11A                                          | Small lamps: TL13/TLD10/PLS11/TL514/PLC10-13 | Not used, undersized for a 36W tube                                                                      |
| Philips EB 128 TL5                   | 240VAC, 0.14A, PF 0.98                                     | 1× TL5 28W                                   | Not used, wrong tube family (TL5, not T8/TLD)                                                            |
| ZEDflow JAEK260033                   | 24VDC, 500mA max (no mains stage at all)                   | 11W UV lamp                                  | Not used for this build; flagged as a possible future low-voltage path (see §2.3)                        |

## 2.2 Inverters on hand

Two Sounce 300W modified-sine car inverters were confirmed to have a real rocker ON/OFF switch (no momentary push-button requiring a held-on state), and a third unit, labelled VANTRO, was identified as a third inverter on the bench rather than a battery, an early misreading in this conversation that was corrected once the photo was reviewed. The two 300W Sounce units are the ones built into the final circuit; the spare 200W units mentioned earlier in planning were not needed once the 3+3 tube split across two 300W inverters was confirmed comfortable on headroom.

## 2.3 Why Sumo Xtreme, and why not the 24V ZEDflow path

Six Sumo Xtreme units pull 6 × 0.19A at 240V ≈ 0.91A ≈ 216VA total, well inside two 300W inverters split 3+3 (≈74VA real per ballast × 3 ≈ 137VA per inverter, under half rated capacity). Power factor (~0.79 for this ballast, versus 0.98 for the EB-T 136 TLD) does not change the real-watt budget meaningfully at this scale, so using six identical Sumo units rather than mixing ballast models was preferred for behavioural consistency across all six channels.

The ZEDflow ballast is a genuinely different path: 24VDC straight to an 11W UV lamp, no inverter, no 240V anywhere, and the arm's existing 24V boost converter could feed it directly with trivial low-voltage relay switching. It was not used here because 11W per lamp is materially less UV-C dose than six 36W tubes for aisle-scale disinfection. It remains on the bench as a possible future low-power path and is noted here so the option is not lost.

# 3. Power Architecture (As-Built)

## 3.1 Battery

The lighting subsystem draws from the same 12.8V LiFePO4 pack already dedicated to the arm (steppers via the 24V boost, plus now the inverters and relay coils). This is a shared-bus decision, not a dedicated-battery one: a separate lighting battery was considered in early planning and dropped once the arm pack was confirmed to be the intended single source for arms and tubes both.

Open item:

the exact Ah and continuous-discharge BMS rating of this LiFePO4 pack has not been confirmed in this conversation. The combined load (six tubes ≈ 11A DC through the inverters, plus arm stepper current through the 24V boost) should be checked against the pack's BMS limit and terminal type before running long disinfection cycles. See §9 for the consolidated open-items list.

## 3.2 Inverters: continuously powered, not DC-switched

An early design in this conversation proposed switching each inverter's 12V DC input through a DC solid-state relay (SSR), so the Mega could cut inverter power entirely and stage the two inverters' turn-on to spread battery inrush. That design was superseded once it was established no SSR is actually on hand for this subsystem. The as-built design instead leaves both inverters powered continuously and performs all staging on the 240V side, tube by tube, through mechanical relays. This is the simpler build and is fully sufficient for the staggered-strike goal, at the cost of the inverters drawing their no-load idle current at all times the robot is powered. A no-load auto-shutoff check on the Sounce units (confirming they don't sleep with zero relay-gated load attached) is worth doing once but was not part of this session's bench tests.

## 3.3 Relay boards: two identical 4-channel modules

The final relay hardware is two identical 4-channel, 5V-coil, opto-isolated, active-LOW relay boards (Songle SRD-05VDC-SL-C relays, 10A 250VAC contacts). This superseded two earlier candidates considered mid-conversation: a generic 30A 2-channel module, and a mixed pairing of one 2-channel 24V-coil board (SLA-12VDC-SL-C / SRD-24VDC-SL-C) for “tube 1, both sides” plus one 4-channel 5V board for “tubes 2 and 3”. Standardising on two identical 4-channel 5V boards, one per inverter, removed the need for a second coil voltage rail and simplified both the wiring and the firmware.

|               |                          |                                                            |
|---------------|--------------------------|------------------------------------------------------------|
| **Board**     | **Channels used**        | **Drives**                                                 |
| Relay board 1 | CH1, CH2, CH3 (CH4 idle) | Inverter 1's choke 1, choke 2, choke 3 (tubes 1–3, side 1) |
| Relay board 2 | CH1, CH2, CH3 (CH4 idle) | Inverter 2's choke 1, choke 2, choke 3 (tubes 1–3, side 2) |

## 3.4 Relay coil power

Both boards' VCC (coil supply) is fed from a dedicated 5V buck converter stepping down the 12V bus, not from the Arduino's 5V pin and not into Vin. Two reasons drove this: four 5V coils per board pull close to 300mA together, more than the Mega's onboard regulator should be asked to source, especially while the Mega is already being powered over USB from the Pi; and feeding 5V into Vin bypasses the onboard regulator's minimum input voltage, which would leave the whole board's logic rail sagging. The buck's negative, both relay boards' GND, and the Mega's GND are bonded as one common ground, required because the IN-pin trigger signals need a return path through that shared net.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>Buck converter</p>
<p>IN+ ← 12V bus (after fuse)</p>
<p>IN− ← battery negative</p>
<p>OUT+ → VCC on relay board 1 AND board 2</p>
<p>OUT− → common ground (Mega GND, battery −, both boards' GND)</p></td>
</tr>
</tbody>
</table>

# 4. AC Wiring and the Cross-Inverter Rule

## 4.1 The rule

Each relay board is dedicated to exactly one inverter. No relay contact ever connects to both inverters' AC circuits. This was raised as an explicit question mid-conversation: specifically, whether paralleling “choke 2 of inverter 1” and “choke 2 of inverter 2” onto one relay channel was safe. The answer is no. Two inverters are independent oscillators with no shared phase reference; bridging their outputs through a shared choke effectively subtracts two out-of-sync waveforms across that choke, which can swing well past 240V at the peaks, trip the Sumo's overvoltage protection, or damage the ballast outright, and pushes circulating current back into both inverters.

The fix that preserves both the safety rule and the goal of both sides lighting in visual sync is to keep every relay contact inside a single inverter's circuit, and to do the synchronising on the control side instead, driving two separate Mega pins (one per board) in the same line of firmware code, which closes both relays within microseconds of each other. Paralleling on the logic/trigger side is harmless; paralleling on the 240V contact side is not. This distinction is the basis for §5.

## 4.2 Per-channel AC wiring

|                     |                                                                  |
|---------------------|------------------------------------------------------------------|
| **Terminal**        | **Connects to**                                                  |
| COM (middle screw)  | That inverter's own Line output only, never the other inverter's |
| NO (energised side) | The corresponding choke's red (Line-in) wire                     |
| NC                  | Left empty                                                       |

Neutral is never switched: every choke's black wire stays on its own inverter's common Neutral bus, untouched, for all six chokes. Only the Line side is broken and routed through a relay contact.

On these boards the silkscreen is rarely labelled, so confirming COM, NO, and NC by meter is worth doing per channel rather than assuming a layout. COM is reliably the middle screw of each three-terminal block. To find NO versus NC, power the board, leave the channel at rest, and meter for continuity between COM and each outer screw: the one that beeps at rest is NC (“normally closed”), and the one that only beeps once the channel is triggered is NO. Wire the choke to NO so the tube stays dark until commanded.

## 4.3 Sumo Xtreme ballast-to-tube wiring

Each ballast has a red/black input pair (to the inverter's 240V output, polarity not critical on modified-sine AC but kept consistent) and four output wires, two white and two grey, to the tube. The rule that resolved the original confusion: wires of the same colour go to the same end of the tube. Both whites land on the two pins at one end of the G13 bipin holder; both greys land on the two pins at the other end. If a particular unit's colours don't match that convention, the small printed diagram on the ballast housing (terminals 1–4, paired as 1–2 and 3–4) is authoritative. A split pair, one white and one grey landing on the same end, is the most common reason a tube fails to strike, since the ballast preheats each end's filament across its own two pins.

## 4.4 No additional switching hardware required

Nothing else sits between the inverter and the tube. The electronic ballast contains the choke and starter functions internally; no separate glow-starter, no separate choke, and no power-factor capacitor are needed or wanted on these tubes. The only physical additions beyond the ballast itself are the G13 lampholders (one pair per tube) and an enclosed AC junction box per inverter to fan its single socket out to three ballasts in parallel.

# 5. Control-Side Wiring (Mega ↔ Relays)

Three Mega pins drive the full six-tube staircase, because each pin's signal is paralleled across the matching channel on both relay boards: one write lights that tube stage on both sides simultaneously.

|              |                                  |                                                |
|--------------|----------------------------------|------------------------------------------------|
| **Mega pin** | **Drives**                       | **Result**                                     |
| D53          | IN1 on relay board 1 AND board 2 | Tube 1, both inverter sides; fires at t = 0    |
| D51          | IN2 on relay board 1 AND board 2 | Tube 2, both inverter sides; fires at t = +5s  |
| D49          | IN3 on relay board 1 AND board 2 | Tube 3, both inverter sides; fires at t = +10s |

CH4 on each board is unused; its IN4 is tied to that board's own VCC so the unterminated channel doesn't chatter (an unused active-low input left floating can oscillate near the logic threshold and wear the relay for no purpose, since nothing is wired to its contacts anyway).

Both boards are active-LOW: the relay closes (tube lights) when the IN pin is pulled LOW, and opens (tube dark) when the pin is HIGH. D13 was deliberately not used for any UV channel, since it is the Mega's onboard status LED pin and is actively toggled by the existing arm firmware's estop/homing blink patterns, which would have made a tube flicker in sync with arm status rather than the lighting sequence. D49/D51/D53 sit well clear of every pin the arm sketch already uses (D2–D7 steppers, A0–A2 joystick, D13 status LED).

Ganging the three trigger pins across both boards is the one place in this design where “paralleling” is correct rather than dangerous: it is the inverse case of §4.1. There, paralleling two inverters' live AC into one contact was the hazard. Here, paralleling two boards' 5V logic inputs onto one Mega pin is ordinary low-voltage fan-out (about 4mA per board through each opto, 8mA total per pin, well inside the Mega's 20mA-per-pin budget) and keeps the two inverter sides' contact circuits exactly as separate as §4.1 requires.

# 6. Known Open Issue: All Tubes Glow When the Mega Is Unpowered

**Status: identified, fix specified, not yet installed.**

During this session it was observed that with the relay boards powered (via the 5V buck, which is independent of the Mega) but the Mega itself disconnected, all six tubes light simultaneously; the moment the Mega boots, they all turn off.

### Root cause

The relay boards are active-LOW. With the Mega unpowered, its GPIO pins float rather than driving a defined level. A floating input on these boards is read as LOW by the opto-isolated input stage, which is indistinguishable from a commanded “on,” so every channel's relay closes. As soon as the Mega's setup() runs, it drives D49/D51/D53 HIGH (the very first lines of aislebot_arm_v8.ino do exactly this, before Serial.begin() or any motor initialisation), and the relays open again. The window of false “on” exists only between the relay boards' buck rail coming up and the Mega completing boot, but during that window all six tubes strike together, which is precisely the simultaneous-inrush event the staged-switching design exists to avoid.

### Specified fix (not yet built)

Add one 10kΩ pull-up resistor from each of the three ganged IN nets to that board's 5V rail, three resistors total, since each Mega pin's net already spans both boards. With the pull-up in place, a floating Mega pin is held HIGH (off) by the resistor instead of reading as an undefined LOW, so the tubes stay dark until the Mega actively pulls a pin low. The Mega's pin output, once booted, easily overrides a 10k pull-up. Verify by disconnecting the Mega's USB with the relay boards still powered: the tubes should now stay dark.

A stronger alternative, worth doing for a UV system specifically, is to separate each board's coil rail from its logic rail: pull the VCC–JD-VCC jumper, keep JD-VCC on the 5V buck for the coils, and move the small-current logic VCC pin to the Mega's own 5V output. With the Mega unpowered, the opto side has no supply at all and the relays cannot close regardless of pin state, a hard guarantee rather than a resistor-mediated one. The pull-up is the quicker fix and was the one specified in conversation; the opto-rail separation is noted here as the more dependable follow-up.

# 7. Firmware Changes: aislebot_arm_v7.ino → v8

v8 adds UV control as an independent, non-blocking state machine alongside the existing arm motion code. No arm pin, arm parameter, or arm behaviour was altered.

|                      |                                                                                                                                                                                                                                                                                                |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Area**             | **Change**                                                                                                                                                                                                                                                                                     |
| New pins             | D53/D51/D49 defined as UV_T1/UV_T2/UV_T3, set OUTPUT and driven HIGH as the very first lines of setup(), before Serial.begin(), so the tubes cannot be lit by an undefined pin state during the Mega's own boot                                                                                |
| New state            | uvActive (bool), uvStage (0–3), uvStartMs (millis() timestamp); mirrors the existing homing/estop state-flag pattern already used for arm motion                                                                                                                                               |
| New functions        | uvAllOff() drives all three HIGH and clears state. uvStart() lights tube 1 and arms the staircase. uvUpdate() is called every loop() iteration; it advances tube 2 at +5000ms and tube 3 at +10000ms using millis(), never delay(), so stepper motion is never paused by the lighting sequence |
| New serial commands  | \<U1\> start cycle, \<U0\> all off, \<U?\> status query; added to handleCommand() alongside the existing \<A,..\>/\<E1\>/\<S\> family                                                                                                                                                          |
| Safety integration   | \<S\> (serial ESTOP) and the joystick long-press ESTOP both now call uvAllOff() in addition to their existing motor-stop behaviour, so the same latch that stops the arm also kills the UV tubes                                                                                               |
| Explicitly not added | No watchdog on the UV state. A disinfection pass needs the tubes to stay lit through brief motion pauses, so UV is only ever cleared by \<U0\>, ESTOP, or loss of Mega power, a deliberate asymmetry from the arm's 500ms motion watchdog                                                      |

## 7.1 Serial command summary (new in v8)

|             |                                                                   |
|-------------|-------------------------------------------------------------------|
| **Command** | **Effect**                                                        |
| \<U1\>      | Begin UV cycle: tube 1 immediately, tube 2 at +5s, tube 3 at +10s |
| \<U0\>      | All tubes off immediately                                         |
| \<U?\>      | Returns \[UV,active,stage\]                                       |

# 8. Raspberry Pi Software Changes

The UV command path reuses the existing /arm/command topic and arm_bridge.py serial link rather than introducing a new topic or a second bridge node, since the Mega already owns both subsystems on one serial connection.

## 8.1 arm_bridge.py

|                       |                                                                                                                      |
|-----------------------|----------------------------------------------------------------------------------------------------------------------|
| **Change**            | **Detail**                                                                                                           |
| Discrete command dict | Added 'UV_ON' → '\<U1\>' and 'UV_OFF' → '\<U0\>' to the existing discrete-command mapping used by cb_command()       |
| shutdown()            | Now sends \<U0\> before \<E0\> on node shutdown, so a clean stop always drops the tubes along with disabling the arm |

## 8.2 phone_dashboard.py

|                       |                                                                                                                                                                                                                                                                         |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Change**            | **Detail**                                                                                                                                                                                                                                                              |
| UI                    | New “UV LIGHTS” button added to the bottom bar between RECORD RUN and E-STOP, with its own CSS state (idle / on, with a pulse animation while on)                                                                                                                       |
| WebSocket message     | New message type 'uv' with cmd 'on' / 'off', sent from the new button's touch handler                                                                                                                                                                                   |
| Server dispatch       | \_dispatch() routes type=='uv' to publish_arm('UV_ON') or publish_arm('UV_OFF')                                                                                                                                                                                         |
| Client-side cosmetics | The button's label mirrors the staircase (TUBE 1 → TUBE 1·2 → ALL ON) on local timers purely for display; the Mega's own millis() clock is the authority for actual timing, so a dropped WebSocket frame after the initial \<U1\> does not desynchronise the real tubes |
| ESTOP interaction     | Hitting E-STOP on the dashboard now also resets the UV button to its idle state client-side, matching the firmware's uvAllOff() on \<S\>                                                                                                                                |

## 8.3 Full command path

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<tbody>
<tr class="odd">
<td><p>Phone tap → WebSocket: {type:'uv', cmd:'on'}</p>
<p>→ phone_dashboard.py _dispatch() → publish_arm('UV_ON')</p>
<p>→ /arm/command (std_msgs/String)</p>
<p>→ arm_bridge.py cb_command() → discrete dict lookup → send('&lt;U1&gt;')</p>
<p>→ USB serial @ 115200 → Arduino Mega</p>
<p>→ aislebot_arm_v8.ino handleCommand() → uvStart()</p></td>
</tr>
</tbody>
</table>

# 9. Deployment Procedure (Executed 22 June 2026)

Performed over SSH against the Pi at 10.53.3.81 (the robot's DHCP address, which has changed more than once across sessions and is not itself part of the procedure).

1.  Flashed aislebot_arm_v8.ino to the Mega via the Arduino IDE on /dev/mega. No change to arm behaviour; UV pins added.

2.  Transferred the two updated Pi files from Windows via scp into the Pi's home directory.

3.  Located the live package source with find ~/ros2_ws/src -name arm_bridge.py to confirm the actual symlinked path rather than assuming it.

4.  Backed up the two existing files in place (arm_bridge.bak.py, phone_dashboard.bak.py) before overwriting, then copied the new files over the originals inside ~/ros2_ws/src/mecanum_robot/mecanum_robot/, restoring their real filenames in the process (the transferred copies had been renamed locally to avoid clobbering older downloads on the Windows side).

5.  Restarted the service: sudo systemctl restart aislebot. Because the workspace is built with --symlink-install and only existing nodes' .py contents changed (no new entry points), a colcon rebuild was not required for the bridge; a colcon build --symlink-install --packages-select mecanum_robot was run once as a precaution and completed in under 3 seconds, then the service was restarted again.

6.  Verified via journalctl -u aislebot -f that the bridge reconnected to /dev/mega cleanly with no serial errors.

7.  Opened the dashboard on the phone at http://\<pi-ip\>:8080, confirmed the new UV LIGHTS button rendered, and ran a live test.

# 10. Verification / Test Results

|                                                          |                                                                                                                                                                                      |
|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Test**                                                 | **Result**                                                                                                                                                                           |
| Dashboard UV button → staged relay clicks                | PASS: relay 1 audibly closed at t=0, second stage at +5s, third at +10s, both boards in audible sync                                                                                 |
| E-STOP during an active UV cycle                         | PASS: all three stages dropped immediately; UV button reset to idle on the dashboard                                                                                                 |
| Bridge reconnect / restart                               | PASS: clean reconnect to /dev/mega, no write errors in journalctl                                                                                                                    |
| Boot-time floating-pin behaviour                         | FAIL, expected per §6: all six tubes light when the Mega has no power; resolved only once the Mega boots and drives the pins HIGH. Pull-up fix specified but not yet installed.      |
| Shared LiFePO4 Ah / BMS rating vs combined load          | NOT TESTED: numeric spec of the pack not yet confirmed against the ~11A inverter draw plus arm stepper current                                                                       |
| Single-ballast 10-minute burn-in on modified-sine output | NOT YET RUN: recommended before running full six-tube cycles for any extended duration, to rule out the Sumo Xtreme's overvoltage auto-shutdown tripping on this inverter's waveform |

# 11. Safety Notes

- 254nm UV-C output burns corneas within seconds of direct viewing and reddens unprotected skin quickly; do not look at a lit tube and keep forearms covered during bench testing.

- Several germicidal ballasts/tubes also generate ozone; ventilate the bench area during extended test runs.

- Tubes are fragile mercury-filled glass and should be shock-mounted in proper G13 holders; a cracked tube on a moving chassis is both a UV and a mercury-cleanup event.

- A physical warning beacon or buzzer, energised whenever any UV relay channel is commanded on, is recommended but not yet implemented. The firmware change to drive it would sit alongside the existing UV_T1/T2/T3 writes in uvStart()/uvUpdate().

- The master battery disconnect remains the hard kill for the whole subsystem and should stay within reach during any bench test.

# 12. Consolidated Open Items

Carried forward explicitly so they are not lost now that the software deployment “worked perfectly”: the items below are hardware and verification steps, separate from the software rollout, and remain outstanding as of this entry.

1.  Install the three 10kΩ pull-up resistors (or the stronger opto-rail separation) per §6, to stop all six tubes lighting when the Mega is unpowered.

2.  Confirm the shared arm/lighting LiFePO4 pack's Ah and continuous-discharge BMS rating against the combined inverter + arm stepper load, and confirm its terminals are bolted rather than faston-tabbed.

3.  Run a single-ballast, single-tube, 10-minute burn-in on one Sounce inverter before relying on extended six-tube duty cycles, watching for the Sumo Xtreme's overvoltage auto-shutdown.

4.  Add a physical UV-on warning beacon/buzzer tied to the relay-commanded state.

5.  Push aislebot_arm_v8.ino, arm_bridge.py, and phone_dashboard.py to the GitHub backup (github.com/AritraD11/Aislebot) now that the deployed versions are confirmed working on the robot.

*End of section. Insert as the next versioned Part of AisleBot_Research_Journal.docx, immediately following the most recent PID-validation entry.*

# Part X — Autonomy Roadmap

Five phases. Each one builds on the previous and can't be skipped. Every current-phase decision must not paint Phase 3 into a corner.

## Phase 1 — Closed-loop motor control

Status: validated in air, ground testing pending.

- PID + feedforward velocity controller per motor on the ESP32, running at 50 Hz.

- Hardware PCNT for encoder decoding.

- Per-motor Kff calibration.

- Anti-windup, derivative filtering, deadband, sticky E-STOP.

Why this matters: every layer above assumes the motors do what they're told. If you command 2.0 rad/s and the wheels deliver 2.0, 1.9, 1.85, 1.68, your odometry is wrong, your SLAM map warps, your path planner sends you into a rack. Closed-loop motor control is the foundation of everything that follows.

## Phase 2 — Odometry and state estimation

Even with perfect PID, mecanum wheels slip. Galati et al. (2022) report 4.56° heading drift over 10 m on industrial concrete and 3.10° on asphalt for open-loop heading. That's 0.79–0.94 m of lateral error. In a 1.2 m aisle with a 0.5 m wide robot, this is catastrophic.

Planned implementation:

- Wheel odometry from the four encoder velocities, integrated through the forward-kinematics equations to produce /odom.

- IMU: BNO055 (preferred — onboard sensor fusion) over I²C to the ESP32, forwarded over serial to the Pi.

- robot_localization E KF node on the Pi fuses /odom with /imu/data, publishes /odometry/filtered.

Expected outcome: heading drift reduced by approximately 88% per Galati's results. Lateral error in a 5 m straight run down to ~0.05 m, well within aisle clearance.

## Phase 3 — Perception and mapping (SLAM)

Status (8 July 2026): **in progress — LiDAR live, first occupancy grid achievable.** See Part XIII for the full bringup narrative. The planned-implementation notes below have been overtaken by the as-built system; they are kept struck-through in spirit for the record and superseded by Part XIII.

The robot needs a map it builds in real time and updates as the environment changes.

As built (supersedes the original plan):

- LiDAR: **YDLIDAR X4 Pro** (single-channel, on `/dev/ydlidar` @ 128000 baud), not the originally-planned RPLiDAR A1/A2. Driver is `ydlidar_ros2_driver` built from the YDLIDAR SDK, not `rplidar_ros`. Confirmed healthy at Sample Rate 5.00K, ~1258 points/scan at ~11.5 Hz (verified 26 June 2026).

- slam_toolbox in online-asynchronous mode, **scan-matching only, no external odometry** (config `slam_nodom.yaml`), consuming `/scan_reliable` — a QoS relay bridges the driver's best-effort `/scan` to a reliable topic (Part XIII §13.4). rf2o laser odometry was trialled and dropped.

- Map persistence: `nav2_map_server map_saver_cli` dumps the occupancy grid on demand.

Expected outcome: an occupancy grid suitable for use as the global costmap input to Phase 4. Nav2 itself remains blocked on Phase 2 — a scan-matched map builds fine without odometry, but robust localisation for navigation needs the fused wheel-odometry + IMU estimate first (Part XIII §13.7).

## Phase 4 — Autonomous navigation

Path planning, local obstacle avoidance, and goal-driven motion.

Planned implementation:

- Nav2 stack with mecanum-compatible local planner.

- DWB (Dynamic Window) local planner to start — proven and well-documented.

- MPPI (Model Predictive Path Integral) once DWB is working — better for smooth motion, which matters for cargo handling.

Expected outcome: send a goal pose on /goal_pose, robot plans a path through the SLAM map, drives there autonomously, avoids dynamic obstacles in its local costmap.

## Phase 5 — Application intelligence (food-delivery cart)

The robot is no longer 'a navigation platform' — it's a cart that recognises a table, carries food to it, opens its cargo arms at the right height, and returns to the kitchen.

Planned implementation:

- AprilTag fiducial markers on tables and the kitchen-side dock for reliable last-metre alignment.

- Behaviour tree on top of Nav2 for the application logic: receive order → navigate to dispatch point → wait for arm load → navigate to target table → dispense → return.

- Cargo-loaded vs cargo-empty Kff profiles loaded at runtime.

- Acoustic announcement and visual indicators for human-friendly operation.

Expected outcome: end-to-end demonstration of an autonomous food-delivery run.

# Part XI — Reference Tables

## 11.1 Robot parameters

| **Parameter**                                | **Symbol** | **Value** | **Unit**                  |
|----------------------------------------------|------------|-----------|---------------------------|
| Outer wheel distance                         | l₁         | 0.403     | m                         |
| Inner wheel distance                         | l₂         | 0.333     | m                         |
| Half track width                             | d          | 0.15769   | m                         |
| Wheel radius                                 | r_w (a)    | 0.0762    | m                         |
| K_outer = l₁ + d                             | K_o        | 0.5607    | m                         |
| K_inner = l₂ + d                             | K_i        | 0.4907    | m                         |
| Encoder CPR (full quadrature)                | CPR        | 46,566    | counts/rev (output shaft) |
| Max wheel angular velocity                   | ω_max      | 6.28      | rad/s (60 RPM)            |
| Conservative wheel-speed clamp               | ω_op       | 3.0       | rad/s                     |
| Conservative linear-velocity clamp (teleop)  | v_op       | 0.15      | m/s                       |
| Conservative angular-velocity clamp (teleop) | ω_z,op     | 0.3       | rad/s                     |
| Chassis mass                                 | m          | 45.54     | kg                        |

## 11.2 PID parameter table

| **Parameter**         | **Value**                 | **Comment**                           |
|-----------------------|---------------------------|---------------------------------------|
| Loop rate             | 50 Hz                     | 20 ms cycle on ESP32 Core 1           |
| Kp                    | 50                        | Proportional                          |
| Ki                    | 30                        | Integral                              |
| Kd                    | 3                         | Derivative (on filtered velocity)     |
| INTEGRAL_MAX          | ±200                      | Anti-windup clamp                     |
| MIN_PWM               | 15                        | Below this, output set to 0           |
| VEL_FILTER_ALPHA      | 0.5                       | EMA on velocity                       |
| D_FILTER_ALPHA        | 0.3                       | EMA on derivative                     |
| Kff FR / FL / RR / RL | 42.1 / 40.2 / 43.7 / 47.9 | Air-calibrated; ground re-cal pending |

## 11.3 Topic communication map (ROS 2)

| **Topic**                | **Message type**           | **Publisher → Subscriber**                                                      |
|--------------------------|----------------------------|---------------------------------------------------------------------------------|
| /joy                     | sensor_msgs/Joy            | joy_node → joy_to_aislebot                                                      |
| /cmd_vel                 | geometry_msgs/Twist        | joy_to_aislebot / keyboard_teleop / phone_dashboard → mecanum_teleop_asymmetric |
| /wheel_speeds            | std_msgs/Float64MultiArray | mecanum_teleop_asymmetric → esp32_bridge / gazebo_bridge                        |
| /wheel_velocities_actual | std_msgs/Float64MultiArray | esp32_bridge → odometry_publisher / phone_dashboard / lcd_display               |
| /motor_telemetry         | std_msgs/Float64MultiArray | esp32_bridge → phone_dashboard                                                  |
| /odom                    | nav_msgs/Odometry          | odometry_publisher → (future: EKF, Nav2)                                        |
| /arm/command             | std_msgs/String            | phone_dashboard → arm_bridge                                                    |
| /arm/status              | std_msgs/String            | arm_bridge → phone_dashboard / lcd_display                                      |

## 11.4 ESP32 serial protocol (full reference)

| **Cmd** | **Format**        | **Behaviour**                                                            | **Reply**                        |
|---------|-------------------|--------------------------------------------------------------------------|----------------------------------|
| V       | \<V,fr,fl,rr,rl\> | Set wheel target velocities in rad/s. Values clamped to MAX_WHEEL_SPEED. | \[OK,V,fr,fl,rr,rl\]             |
| M       | \<M,fr,fl,rr,rl\> | Direct PWM output −255..+255, bypassing PID.                             | \[OK,M,...\]                     |
| T       | \<T,idx,vel\>     | Test single motor (idx ∈ {0,1,2,3}) at given rad/s.                      | \[OK,T,idx,vel\]                 |
| S       | \<S\>             | Emergency stop. Latches estop_active = true.                             | \[OK,ESTOP_LATCHED\]             |
| E       | \<E1\> or \<E0\>  | Enable or disable. E1 clears the E-STOP latch.                           | \[OK,ENABLED\] / \[OK,DISABLED\] |
| P       | \<P\>             | Ping.                                                                    | \[PONG\]                         |
| G       | \<G,Kp,Ki,Kd\>    | Set PID gains live; resets all integrals to 0.                           | \[OK,GAINS,Kp,Ki,Kd\]            |
| F       | \<F,fr,fl,rr,rl\> | Set per-motor feedforward gains live.                                    | \[OK,FF,...\]                    |
| L       | \<L1\> or \<L0\>  | 10 Hz CSV telemetry on serial enable / disable.                          | \[OK,LOG=1\] / \[OK,LOG=0\]      |
| W       | \<W1\> or \<W0\>  | Watchdog enable / disable.                                               | \[OK,WDOG=1\] / \[OK,WDOG=0\]    |

## 11.5 Power distribution quick-view

| **Source**                     | **Output**          | **Powers**                                     |
|--------------------------------|---------------------|------------------------------------------------|
| LiFePO₄ 12.8 V                 | 12.8 V              | Boost & Buck inputs                            |
| Boost (set to 24 V)            | 24 V                | MDD20A drivers → motors                        |
| Buck (set to 5 V)              | 5 V                 | Mega, level shifters V_CCB, LCD                |
| ESP32 USB / on-board regulator | 3.3 V (internal)    | ESP32, level shifters V_CCA                    |
| External 24 V (arm)            | 24 V                | NEMA 34 linear stepper via BH-MSD-6A-W         |
| SSR-50DD                       | Main-bus disconnect | Software-controllable kill switch for main bus |

# Part XII — ESP32 Firmware Deep Dive

Added in v1.2 after a direct verification pass against aislebot_esp32_v2.ino. Everything below comes from reading the firmware source directly, not from memory. Any earlier table or figure that contradicts this section is wrong, and §12.10 catalogues those reconciliations.

## 12.1 Source of truth

| **Item**                  | **Value**                                                              |
|---------------------------|------------------------------------------------------------------------|
| Firmware filename         | aislebot_esp32_v2.ino                                                  |
| Header banner             | AisleBot ESP32 Motor Controller v2.0                                   |
| Hardware target           | Robocraze ESP32-WROOM-32 38-pin Dev Board (CP2102)                     |
| Arduino IDE board setting | ESP32 Dev Module                                                       |
| CPU clock                 | 240 MHz (WiFi/BT)                                                      |
| Flash size                | 4 MB, Default partition                                                |
| Runtime serial baud       | 115200                                                                 |
| Upload baud (flashing)    | 921600                                                                 |
| Required libraries        | WebSockets (Markus Sattler / Links2004), ArduinoJson (Benoit Blanchon) |
| Driver framework          | Arduino-ESP32 core + ESP-IDF PCNT (driver/pcnt.h)                      |

> *Reconciliation: the 115200 vs 921600 distinction has caused at least one bridge-node misconfiguration. 921600 is the flashing speed used by esptool. SERIAL_BAUD in firmware is 115200. Any Pi-side bridge that opens /dev/esp32 at 921600 will not communicate. See §12.10.2.*

## 12.2 Motor driver pin map (right side)

All eight motor control signals (4 × PWM + 4 × DIR) leave the ESP32 on the right side of the Robocraze board. None pass through a level shifter. MDD20A inputs are 3.3 V-tolerant for PWM and DIR.

| **Motor** | **Driver / channel** | **PWM GPIO** | **DIR GPIO** |
|-----------|----------------------|--------------|--------------|
| FR        | MDD20A \#1, CH1      | G4           | G16          |
| FL        | MDD20A \#1, CH2      | G17          | G18          |
| RR        | MDD20A \#2, CH1      | G19          | G21          |
| RL        | MDD20A \#2, CH2      | G22          | G23          |

PWM is generated via ledcAttach at 5 kHz, 8-bit resolution. setMotorOutput() takes a signed PWM value, splits it into magnitude (0..255) and a direction bit, applies MIN_PWM_THRESHOLD = 15 to suppress the deadband buzz, then writes both pins.

## 12.3 Encoder pin map (left side via TXS0108E)

| **Motor** | **Channel A** | **Channel B** | **PCNT Unit** | **Note**                             |
|-----------|---------------|---------------|---------------|--------------------------------------|
| FR        | G36           | G39           | PCNT_UNIT_0   | Labelled SP and SN (input-only pins) |
| FL        | G34           | G35           | PCNT_UNIT_1   | Input-only pins                      |
| RR        | G32           | G33           | PCNT_UNIT_2   | Bidirectional                        |
| RL        | G25           | G26           | PCNT_UNIT_3   | Bidirectional                        |

> *Hardware gotcha: G34, G35, G36, and G39 are input-only. They can't drive outputs. Good for encoder reads; can't be repurposed if the encoder layout ever changes.*

## 12.4 Direction compensation via sign arrays

Right-side motors (FR, RR) are physically mounted facing the opposite way to left-side motors (FL, RL). The firmware handles this with two parallel arrays:

> // FR, FL, RR, RL
>
> const int8_t MOTOR_DIR_SIGN\[4\] = {-1, +1, -1, +1};
>
> const int8_t ENC_DIR_SIGN\[4\] = {-1, +1, -1, +1};

MOTOR_DIR_SIGN is applied in setMotorOutput() so a positive PWM always means 'forward in body frame'. ENC_DIR_SIGN is applied in readEncoderDelta() so positive ticks always mean 'rotating forward in body frame'. The two arrays must match per motor. If they disagree, the PID error signal acquires the wrong sign, the loop becomes positive feedback, and the motor accelerates to saturation in the opposite direction. This is the most common cause of runaway during single-motor bring-up.

> *Commissioning rule: during bring-up, test motor direction with \<T,idx,1.0\>. If a wheel spins the wrong way, flip BOTH the MOTOR_DIR_SIGN and ENC_DIR_SIGN entry for that motor, not just one. Re-test under PID before trusting the change.*

## 12.5 Numerical constants — from firmware

### 12.5.1 Geometry and kinematics

| **Constant** | **Value** | **Notes**                                                    |
|--------------|-----------|--------------------------------------------------------------|
| ROBOT_L1     | 0.403 m   | Outer wheel distance from body centre (FR, RL)               |
| ROBOT_L2     | 0.333 m   | Inner wheel distance from body centre (FL, RR)               |
| ROBOT_D      | 0.15769 m | Half-track width                                             |
| K_OUTER      | 0.56069 m | L1 + D, used for FR and RL in IK                             |
| K_INNER      | 0.49069 m | L2 + D, used for FL and RR in IK                             |
| WHEEL_RADIUS | 0.0762 m  | DekuPro 6" SR Mecanum (152.4 mm OD / 2)                      |
| ENCODER_CPR  | 93132     | RMCS-2086: 500 lines × 4 (full quadrature) × 47 (gear ratio) |

### 12.5.2 Speed envelope

| **Constant**      | **Value**  | **Notes**                          |
|-------------------|------------|------------------------------------|
| MAX_WHEEL_SPEED   | 6.28 rad/s | 60 RPM rated maximum               |
| MAX_LINEAR_SPEED  | 0.48 m/s   | MAX_WHEEL_SPEED × WHEEL_RADIUS     |
| MAX_ANGULAR_SPEED | 1.0 rad/s  | Yaw rate at joystick deflection ±1 |

### 12.5.3 PWM

| **Constant**      | **Value** | **Notes**                                           |
|-------------------|-----------|-----------------------------------------------------|
| PWM_MAX           | 255       | 8-bit duty cycle full scale                         |
| MIN_PWM_THRESHOLD | 15        | Below this, motor hums but does not spin (deadband) |
| PWM_FREQUENCY     | 5000 Hz   | Above audible range                                 |
| PWM_RESOLUTION    | 8 bits    | Matches PWM_MAX                                     |

### 12.5.4 PID and filters

| **Constant**          | **Value**                          | **Notes**                                              |
|-----------------------|------------------------------------|--------------------------------------------------------|
| PID_LOOP_HZ           | 50 Hz                              | PID loop frequency on Core 1                           |
| PID_DT                | 0.02 s                             | = 1 / PID_LOOP_HZ                                      |
| Kp                    | 50.0                               | Live-tunable via \<G,...\>                             |
| Ki                    | 30.0                               | Live-tunable                                           |
| Kd                    | 3.0                                | Viable on ESP32 thanks to hardware PCNT (no ISR noise) |
| Kff\[FR, FL, RR, RL\] | 42.1, 40.2, 43.7, 47.9 PWM/(rad/s) | Per-motor feedforward, calibrated in air May 14        |
| INTEGRAL_MAX          | ±200                               | Anti-windup clamp                                      |
| D_FILTER_ALPHA        | 0.3                                | Derivative EMA (lower = heavier filter)                |
| VEL_FILTER_ALPHA      | 0.5                                | Velocity-measurement EMA                               |

### 12.5.5 Timing and safety

| **Constant**          | **Value** | **Notes**                                  |
|-----------------------|-----------|--------------------------------------------|
| WATCHDOG_TIMEOUT_MS   | 1000 ms   | No command for this long, motors stop      |
| WIFI_CMD_TIMEOUT_MS   | 200 ms    | WiFi joystick goes stale after this        |
| TELEMETRY_INTERVAL_MS | 100 ms    | 10 Hz serial CSV when \<L1\> active        |
| SERIAL_BAUD           | 115200    | Runtime serial speed; not the upload speed |

### 12.5.6 WiFi AP

| **Constant**   | **Value**                          |
|----------------|------------------------------------|
| WIFI_SSID      | AisleBot-Control                   |
| WIFI_PASS      | aislebot123                        |
| WEBSERVER_PORT | 80 (joystick HTML page)            |
| WEBSOCKET_PORT | 81 (joystick data + telemetry)     |
| AP IP address  | 192.168.4.1 (default ESP32 SoftAP) |

## 12.6 Dual-core FreeRTOS task layout

| **Core** | **Responsibility**                                                                                                | **Real-time profile**                                                | **Notes**              |
|----------|-------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|------------------------|
| Core 0   | WiFi SoftAP + WebServer + WebSocketsServer + serial command parser + telemetry broadcaster + watchdog timekeeping | Soft real-time. May stall briefly during WiFi client events.         | Best-effort scheduling |
| Core 1   | PID loop at 50 Hz (pidControlTask). Reads PCNT counters, computes velocity, runs PID+FF, writes PWM and DIR.      | Hard real-time. Uses vTaskDelayUntil; no blocking calls, no delay(). | Dedicated task         |

Inter-core communication is via volatile globals. target_velocity\[\] is the main handoff point. wifi_vx/vy/wz are written from Core 0 and read on Core 1 in the IK block. Source arbitration (Serial vs WiFi) lives on Core 1 and is decided by comparing millis() against last_wifi_cmd_ms with a 200 ms timeout.

## 12.7 PCNT encoder subsystem

Each of the four encoders has a dedicated PCNT unit configured for full quadrature decoding: two PCNT channels per unit, one counting A-edges with B as the direction control, the other counting B-edges with A as the direction control. This recovers all four edges of the AB phase pattern in hardware.

Reading is destructive: pcnt_counter_clear() is called immediately after pcnt_get_counter_value(), so the firmware uses the delta between reads. At 50 Hz with up to ~6.28 rad/s and CPR = 93132, a single 20 ms window sees at most ~1860 counts — well under the 32767 limit, so overflow within one period is impossible during normal operation.

## 12.8 Velocity estimation and PID equation

### 12.8.1 Velocity estimation

> delta = pcnt_read_and_clear() // signed ticks
>
> delta \*= ENC_DIR_SIGN\[i\] // body-frame sign
>
> raw_vel = (delta / ENCODER_CPR) \* 2π / dt // rad/s
>
> actual_vel = α \* raw_vel + (1−α) \* prev_vel // EMA, α = 0.5

### 12.8.2 PID + feedforward output

> ff = Kff\[i\] \* target
>
> p_term = Kp \* e
>
> integral = clamp(integral + e \* dt, −200, +200)
>
> i_term = Ki \* integral
>
> filt_d = 0.3 \* raw_d + 0.7 \* filt_d // EMA
>
> d_term = Kd \* filt_d
>
> total = ff + p_term + i_term + d_term
>
> pwm_out = clamp(total, −255, +255)

## 12.9 Inverse kinematics and command arbitration

### 12.9.1 Asymmetric IK as compiled

> ω_FR = ( vx + vy + wz · K_OUTER ) / R
>
> ω_FL = ( vx − vy − wz · K_INNER ) / R
>
> ω_RR = ( vx − vy + wz · K_INNER ) / R
>
> ω_RL = ( vx + vy − wz · K_OUTER ) / R

where K_OUTER = 0.56069 m, K_INNER = 0.49069 m, R = 0.0762 m

If any \|ω\| would exceed MAX_WHEEL_SPEED = 6.28 rad/s, all four are scaled by the same factor so the commanded direction is preserved.

### 12.9.2 Arbitration logic

- WiFi joystick wins when (millis() − last_wifi_cmd_ms) \< 200 ms.

- Otherwise, the most recent serial command holds.

- When neither has been seen for WATCHDOG_TIMEOUT_MS = 1000 ms, the watchdog zeroes all targets and clears integrals.

- E-STOP latches across both sources. Once \<S\> or the phone E-STOP has fired, motors stay off until explicit \<E1\> or phone 'resume'.

## 12.10 Reconciliations against earlier journal text

### 12.10.1 Table 17 — motor pin assignments

In v1.1, the motor pin table listed encoder pins as D14–D21, which are Arduino Mega digital pin labels from the v3 open-loop era. They don't apply to the ESP32 build. Corrected table:

| **Motor** | **PWM** | **DIR** | **Enc A** | **Enc B** |
|-----------|---------|---------|-----------|-----------|
| FR        | G4      | G16     | G36 (SP)  | G39 (SN)  |
| FL        | G17     | G18     | G34       | G35       |
| RR        | G19     | G21     | G32       | G33       |
| RL        | G22     | G23     | G25       | G26       |

### 12.10.2 Runtime serial baud is 115200, not 921600

Working notes and a few bridge-node defaults had the ESP32 runtime serial at 921600. The firmware constant SERIAL_BAUD = 115200. The 921600 figure is the upload speed used by esptool when flashing. Any Pi-side serial.Serial() that opens /dev/esp32 must use 115200, or the link will appear dead. This includes esp32_bridge.py and any standalone test scripts.

### 12.10.3 Polarity correction is in software, not wiring

The journal previously described the left-side encoder wires as physically swapped (Yellow ↔ Green) to correct sign inversion from opposite-facing motor mounting. That description applies to the v3 Arduino Mega era only. On the current ESP32 build, no wires are swapped. Every encoder is wired the same way: Yellow to Channel A, Green to Channel B. Polarity is corrected entirely by the MOTOR_DIR_SIGN and ENC_DIR_SIGN arrays in firmware (§12.4).

> *Engineering rationale: if a motor is ever remounted, only a single sign in the firmware needs to flip. With physical wire swaps, the same change requires desoldering at the level-shifter end — which has already been a documented failure mode (§7.12).*

## 12.11 Hazardous and reserved pins on this build

| **Category**                  | **Pins**                     | **Why**                                                                                                                      |
|-------------------------------|------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| Strapping pins (used at boot) | G0, G2, G5, G12, G15         | Pulled at boot to determine flash mode. External drivers at power-on prevent normal boot. None used in the motor assignment. |
| Internal SPI flash            | G6, G7, G8, G9, G10, G11     | Connected to on-module flash chip. Cannot be repurposed.                                                                     |
| Input-only                    | G34, G35, G36 (SP), G39 (SN) | Read-only. Used here as encoder inputs.                                                                                      |
| USB-UART (reserved)           | G1 (TXD), G3 (RXD)           | Used by CP2102 USB-serial bridge. Don't connect external signals while USB is in use.                                        |
| Currently unused, safe        | G13, G14, G27                | Available for future expansion (e.g. IMU interrupt, encoder index, LiDAR sync).                                              |

## 12.12 WebSocket protocol (port 81)

### Incoming (phone → ESP32)

| **type** | **Payload**                                             | **Effect**                                                                                               |
|----------|---------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| "joy"    | { "vx": float, "vy": float, "wz": float } in \[−1, +1\] | ESP32 scales by MAX_LINEAR_SPEED / MAX_ANGULAR_SPEED, stores in wifi_vx/vy/wz, updates last_wifi_cmd_ms. |
| "stop"   | (no payload)                                            | estop_active = true, stopAllMotors(), zero wifi velocities. Latched.                                     |
| "gains"  | { "kp": float, "ki": float, "kd": float }               | Sets Kp, Ki, Kd live and zeroes all integrals.                                                           |
| "resume" | (no payload)                                            | Clears the E-STOP latch and re-enables motors.                                                           |

### Outgoing (ESP32 → phone)

Telemetry broadcast roughly every 100 ms. JSON format:

> { "type": "tel", "t": \<millis()\>, "estop": bool, "src": "WIFI"\|"SERIAL",
>
> "m": \[ {"n": "FR", "tgt": float, "act": float, "pwm": int}, ... \] }

## 12.13 Three-speed gear system (WiFi joystick)

| **Mode** | **Multiplier** | **Full-stick linear** | **Use case**                             |
|----------|----------------|-----------------------|------------------------------------------|
| SLOW     | 0.25×          | 0.12 m/s              | Ground testing, narrow-aisle manoeuvring |
| NORMAL   | 0.60×          | 0.29 m/s              | Default exploration                      |
| FAST     | 1.00×          | 0.48 m/s              | Hardware maximum, open floor only        |

## 12.14 Open items as of June 9, 2026

- Confirm every Pi-side bridge opens /dev/esp32 at 115200, not 921600. esp32_bridge.py and any standalone test scripts both qualify.

- Validate that the ENC_DIR_SIGN / MOTOR_DIR_SIGN pair is correct on every motor under load. Wrong sign under friction can present as slow drift or stall rather than runaway.

- Stress-test ROS 2 → ESP32 serial path under sustained PID throughput (still outstanding from §9.4).

- Cytron MDD20A Channel 2 failure (Q4 low-side MOSFET, June 2026) — replacement decision pending. If BTS7960 IBT-2 modules are adopted, the firmware DIR convention may need an extra inversion per motor. Recheck §12.4 after hardware swap.

# Part XIII — Phase 3 Kickoff: LiDAR Integration and SLAM Bringup

Added in v2.0. This part documents the first working perception layer — a YDLIDAR X4 Pro producing a live scan, a slam_toolbox pipeline building an occupancy grid from it, and the two non-obvious problems (device naming and QoS) that stood between "the LiDAR spins" and "the map builds." Verified working on 26 June 2026. In the theory-first convention of this journal: the decisions and the dead ends are recorded, not just the final recipe.

## 13.1 Sensor choice — YDLIDAR X4 Pro, not RPLiDAR

The roadmap (Part X, Phase 3) had planned for an RPLiDAR A1/A2. The unit actually procured and integrated is a **YDLIDAR X4 Pro**. Everything downstream — driver, parameters, udev naming — follows from that part, so the roadmap text has been corrected rather than left aspirational.

| **Parameter** | **Value** |
|---------------|-----------|
| Model | YDLIDAR X4 Pro (single-channel) |
| Device | `/dev/ydlidar` |
| Baud rate | 128000 |
| Sample rate | 5 (healthy: "Sample Rate 5.00K") |
| Scan frequency | ~10 Hz nominal, ~11.5 Hz observed |
| Points per scan | ~1258 when healthy |
| `isSingleChannel` | true |
| `intensity` | false |

These parameters live in `~/ros2_ws/src/ydlidar_ros2_driver/params/ydlidar.yaml` and are mirrored into the repo at `system/ydlidar_params.yaml`. They were read off the hardware, not copied from a forum.

> *Single-channel means the X4 Pro only streams; it ignores device-info and health queries. The log line `Fail to get baseplate device information` is therefore expected and harmless. Running it as two-way (`isSingleChannel: false`) makes it die with `Fail to start the lidar` and health code −2. This is a configuration fact worth not re-discovering.*

## 13.2 The adapter has two USB ports

The X4 Pro adapter board exposes two USB connectors with different jobs: **USB-B is power** (fed from the 5 V buck), **USB-C is data** (to the Pi). Both plugged at once is correct. Because the motor runs off the buck through the power port, the disc spins even with the data cable unplugged — which is a useful sanity check but also a trap, because a spinning disc does not by itself mean the Pi is receiving clean data.

## 13.3 The device-naming problem — identical CP2102 chips

This was the gnarly part, and it is a genuinely new hardware learning that reshaped the udev rules.

The ESP32's USB-UART bridge and the YDLIDAR X4 Pro's data adapter are **both CP2102 chips with the same VID:PID (`10c4:ea60`) and the same factory serial string (`0001`).** Serial number cannot tell them apart. The original udev rule (Part V §5.4) matched the ESP32 purely on `10c4:ea60` — which now matches the LiDAR equally well, a collision that did not exist when the ESP32 was the only CP2102 device on the robot.

The fix is to pin each device by its **physical USB port** (`KERNELS==` in udev) rather than by chip identity:

| **Device** | **Chip** | **Physical port** | **Symlink** |
|------------|----------|-------------------|-------------|
| Arduino Mega | CH340 (`1a86:7523`) | — (unique VID:PID) | `/dev/mega` (ttyUSB0) |
| ESP32 | CP2102 (`10c4:ea60`) | `4-1` | `/dev/esp32` (ttyUSB1) |
| YDLIDAR X4 Pro | CP2102 (`10c4:ea60`) | `2-2` | `/dev/ydlidar` (ttyUSB2) |

> *Operational consequence: the LiDAR and ESP32 cables must stay in their assigned USB sockets. Move one to a different port and its symlink vanishes until it is moved back. The port numbers (`4-1`, `2-2`) were read from `udevadm info` on the live devices, and are baked into `system/99-aislebot.rules`. This is the price of two indistinguishable chips on one hub, and it is cheaper than the alternative (relabelling the chips' EEPROM serials).*

## 13.4 The QoS problem — why a relay node exists

With the LiDAR streaming, the first attempt to feed it into SLAM failed silently. `ros2 topic echo /scan` and `ros2 topic hz /scan` both worked perfectly, yet slam_toolbox sat forever printing "Waiting for laser_scans."

The cause is a QoS mismatch. The `ydlidar_ros2_driver` publishes `/scan` as **best-effort**. slam_toolbox (and rf2o) subscribe as **reliable** by default. Best-effort publisher and reliable subscriber are incompatible endpoints in DDS — they never form a connection. `topic echo`/`hz` work only because those CLI tools negotiate a compatible QoS on the fly; the SLAM node does not.

The fix is a small dedicated node, `scan_relay.py` (vendored at `src/scan_relay/scan_relay.py`): subscribe to `/scan` best-effort, re-publish the identical message on `/scan_reliable` with reliable QoS. Everything downstream reads `/scan_reliable`. It is a plain `python3` script — no colcon build needed.

> *Lesson, generalised: in ROS 2, "the topic is clearly alive" (echo/hz work) is not evidence that your node will receive it. QoS compatibility is a separate gate from topic liveness, and the CLI tools hide the gate by adapting to it. When a node "waits forever" for a topic that `hz` says is publishing, suspect QoS before suspecting the data.*

## 13.5 rf2o dropped — a recorded dead end

Laser odometry via `rf2o_laser_odometry` was trialled as a way to give SLAM a motion prior without wheel odometry. It kept failing on Jazzy even through the QoS relay, and was more trouble than it was worth. **Decision: rf2o is dropped.** The first map is built with slam_toolbox alone, scan-matching only, no external odometry (`slam_nodom.yaml`). The relay still matters, because slam_toolbox hits the identical QoS wall rf2o did.

## 13.6 Bringup sequence

The pipeline is deliberately manual for now — one long-running node per terminal, each confirmed healthy before the next — so a failure is obvious at the stage it occurs. It collapses into one launch file later.

1. **LiDAR:** `ros2 launch ydlidar_ros2_driver ydlidar_launch.py`. Wait for `Lidar has started!` and confirm `Sample Rate: 5.00K`. This launch also publishes the `base_link → laser_frame` static transform, so the TF link is handled here.
2. **QoS relay:** `python3 ~/ros2_ws/src/scan_relay/scan_relay.py`. Verify with `ros2 topic hz /scan_reliable` (~11 Hz).
3. **slam_toolbox:** `ros2 launch slam_toolbox online_async_launch.py slam_params_file:=/home/aritra/ros2_ws/slam_nodom.yaml`.
4. **Save the map:** `ros2 run nav2_map_server map_saver_cli -f ~/aislebot_first_map`.

> *Two traps worth flagging. (a) The `slam_params_file` path must be absolute — a `~` there is not expanded by the launch system, slam silently falls back to its defaults (wrong topic, expects odom), and the map never builds. `slam_nodom.yaml` lives in the workspace root (`~/ros2_ws/`), not inside any package's `config/`, precisely because it is passed by absolute path. (b) A healthy launch reads Sample Rate 5.00K; if it instead reads ~2.59K with a flood of `Checksum error` lines, that is real data corruption — almost always a USB-C not fully seated or the buck sagging and starving the LiDAR motor. Fix the power/seating before building a map on garbage scans.*

## 13.7 Where this sits — and why Nav2 is not next

Done as of 26 June 2026: LiDAR live, TF link up, relay solving QoS, slam config ready, a first occupancy grid you can save.

Not next, and deliberately so: **Nav2 needs trustworthy localisation, which needs real odometry.** Mecanum wheel odometry drifts hard from roller slip (the Galati numbers in Part X, Phase 2), so the path to navigation runs through the ESP32 encoder-odometry bridge plus a BNO055 IMU and EKF fusion — i.e. Phase 2 — before Nav2 with an MPPI controller makes sense. Building a scan-matched map without odometry is fine; navigating on it is not. This keeps Phase 3's deliverable (a map) decoupled from Phase 2's blocker (fused localisation).

## 13.8 Viewing the map headless

The Pi runs CycloneDDS on loopback only (Part V), college WiFi blocks DDS multicast, and a Windows laptop on a different RMW won't discover topics anyway — so RViz-on-laptop cannot see `/scan` or `/map` over the network as-is. The headless-friendly route is **Foxglove Bridge**: a websocket on the Pi that Foxglove Studio on the laptop connects to over plain TCP. Not yet set up; it is the natural next piece once the map builds clean.

## 13.9 Install-time provenance

`install.sh` now builds the YDLidar SDK from source and clones `ydlidar_ros2_driver` (branch `humble`, which builds fine under Jazzy). The origin URLs (`github.com/YDLIDAR/YDLidar-SDK.git` and `github.com/YDLIDAR/ydlidar_ros2_driver.git`) were confirmed against the live Pi checkout, not guessed. The abandoned `ros-jazzy-rplidar-ros` apt line was removed. The driver package is **not** vendored in this repo — it is a third-party dependency cloned fresh at install time; only its `ydlidar.yaml` params and the project's own `scan_relay.py` / `slam_nodom.yaml` are version-controlled here.

# Part XIV — Desktop Dashboard, Self-Hosted Network, and Repository Consolidation

Added in v2.0. Three infrastructure changes that don't touch the control loop but materially change how the robot is operated and how the project is preserved.

## 14.1 Phone dashboard v2.1 → v2.2 — desktop control

The phone dashboard was touchscreen-only. v2.2 adds full desktop operation without removing anything that worked on the phone:

- **Mouse:** the drive joystick, the yaw slider, and every button now respond to mouse click-and-drag, using a `'mouse'` sentinel touch-id so the existing touch code paths are reused unchanged. Document-level `mousemove`/`mouseup` handlers mean a drag that leaves the control's bounds still tracks (normal with a mouse, impossible with touch).
- **Hidden keyboard scheme, not shown in the UI:** `W`/`A`/`S`/`D` drive the joystick, `Q`/`E` yaw (Q = CCW, E = CW), `R` toggles record. Keyboard input yields to an active mouse/touch drag on the same control rather than fighting it, and a window blur clears all held keys so nothing sticks.

The motivation is practical: driving and logging telemetry from the same laptop that is SSH'd into the Pi, with no touchscreen in reach. The firmware, the ROS 2 topics, and the phone experience are all unchanged — this is purely an added input surface on the existing FastAPI dashboard.

## 14.2 Self-hosted Pi network (AisleBot-Pi AP)

Historically the Pi joined college WiFi (eduroam / 10.53.x.x, an address that changed session to session and forced IP-hunting each time). The Pi can instead **host its own network** via NetworkManager shared mode:

| **Setting** | **Value** |
|-------------|-----------|
| SSID | `AisleBot-Pi` |
| Password | `aislebotpi5` |
| Pi address (fixed) | `10.42.0.1` |
| Dashboard | `http://10.42.0.1:8080` |
| SSH | `ssh aritra@10.42.0.1` |

`10.42.0.1` never changes — NetworkManager's shared mode always places the AP host there, so dashboard and SSH targets are stable every session. Phone and PC can both join simultaneously (drive from the phone, watch logs over SSH from the PC).

Two honest caveats recorded for the record: (a) the AP does **not** yet start automatically on boot — autoconnect is off, so after a reboot the Pi returns to eduroam and the AP must be raised by hand (`sudo nmcli con up aislebot-ap`); making it the permanent default means writing it into netplan config, which is the next step. (b) The Pi has one radio, so hosting the AP means no internet; to go online, switch back to eduroam (`sudo nmcli con up eduroam`), which drops the current SSH session by design. ~~The ESP32's own AP (`AisleBot-Control` @ `192.168.4.1`) remains the independent escape hatch for when the Pi itself is down.~~ **No longer true as of firmware v3.0 (4 Aug 2026)** — the ESP32's radio was removed entirely, so this escape hatch does not exist. The PID still lives on the ESP32 and still fails safe on its own (command watchdog stops the motors ~750 ms after the Pi goes quiet), but there is no longer any way to *drive* the robot with the Pi down. See Part XVI §16.6. Full detail in `docs/Network_SelfHosted_AP.md`.

## 14.3 A real config bug fixed in passing — CycloneDDS on Jazzy

The headless CycloneDDS loopback binding in `start_aislebot.sh` and `install.sh` used the deprecated `<NetworkInterfaceAddress>lo</NetworkInterfaceAddress>` form, which **ROS 2 Jazzy silently ignores** — no error, it just doesn't take. Replaced with the modern form:

> `<Interfaces><NetworkInterface name="lo" priority="default" multicast="false"/></Interfaces>`

This is a functional fix, not cosmetic: the intent (bind DDS discovery to loopback on a headless Pi) only actually holds with the new syntax. In practice the system worked anyway because loopback is the default binding when discovery finds no usable multicast interface, but relying on that accident is exactly the kind of silent-no-op this journal exists to flag.

## 14.4 Repository consolidation and rename

The GitHub backup was reorganised into a professional, disaster-recoverable state and renamed from `Aislebot` to **`NarrowAisleBot`** (display name; the ROS 2 package names are unchanged). The consolidation, done as a single reviewed pull request:

- **Documentation** moved into `docs/` as Markdown (this journal, the Master Reference, the LiDAR/SLAM bringup, the network doc, the setup manual), with the original `.docx`/`.pdf` preserved in `docs/originals/` as source of record.
- **LiDAR/SLAM** vendored: `system/ydlidar_params.yaml`, `system/slam_nodom.yaml`, `src/scan_relay/scan_relay.py`, plus the `install.sh` SDK/driver build.
- **Verification discipline:** every code and config file was cross-checked by SHA-256 against the live Pi. Where an uploaded copy disagreed with the Pi, the Pi won. This caught two stale files that would otherwise have been committed as "current": the dashboard (an older v2.1 without the desktop controls) and the full-stack launch file (a variant that had dropped `odom_pub` and `lcd_display`).
- **Housekeeping:** added an MIT `LICENSE` (matching the declaration already in every `package.xml`), a `.gitattributes`, and deleted the deprecated `hardware.launch.py`.
- **Visibility:** the repo was set private. Consequence to remember: the one-command `curl | install.sh` fresh-Pi installer cannot fetch from a private repo anonymously, so a fresh install requires flipping the repo public for the duration of the install, then back.

> *Principle reinforced here, and worth stating as its own rule: the robot's Pi is the single source of truth. The GitHub repo is a backup of the Pi, never the other way round. Any time the two disagree, the Pi is right and the repo is corrected to match — verified by checksum, not by assumption. A backup you have not verified against the source is a hope, not a backup.*

# Part XV — Current Status Snapshot (8 July 2026)

This supersedes the 16 May 2026 snapshot in Part IX. Same purpose: a single honest view of what works, what's in flight, and what's queued.

**Partially superseded by Part XVI (4 August 2026)** — the encoder fault referenced throughout this snapshot is resolved, and the firmware/gains in §15.3 are one generation behind. Read Part XVI first for anything control-related; this snapshot is kept for the LiDAR/SLAM/infrastructure state, which it still describes correctly.

## 15.1 What works

- **Drive:** closed-loop PID + feedforward on the ESP32, validated in air (14 May 2026). All four encoders read correctly through the level shifters.
- **Teleop:** Xbox path (joy → teleop_asym → esp32_bridge), WiFi phone joystick (ESP32 AP), and the phone/desktop dashboard (v2.2, mouse + hidden keyboard) all functional.
- **Arm + UV:** Mega firmware v8 — arm motion plus 3-tube staged UV-C lighting, staircased on-Mega (t=0 / +5s / +10s), non-blocking, ESTOP-latched. Deployed and live (22 June 2026).
- **Perception (new):** YDLIDAR X4 Pro live on `/dev/ydlidar`; slam_toolbox builds a savable occupancy grid via the `scan_relay` QoS bridge, scan-matching only (26 June 2026).
- **Infrastructure:** self-hosted `AisleBot-Pi` AP at a fixed `10.42.0.1`; port-pinned udev naming for the two identical CP2102 devices; systemd autostart of the full drive/arm stack; modern CycloneDDS loopback binding.
- **Backup:** the `NarrowAisleBot` repo is a checksum-verified mirror of the Pi, with full Markdown documentation and an MIT license.

## 15.2 What is in flight / next

- **Ground-truth Kff recalibration** — still the top control task; air values are 4–14% under-calibrated (Part VI §6.11), ground values expected 10–30% higher again.
- **Foxglove Bridge** for headless map/scan viewing (Part XIII §13.8).
- **Phase 2 (the real unlock):** BNO055 IMU + wheel odometry + `robot_localization` EKF. This is the gate for Nav2 — Phase 3's map exists, but navigating on it needs fused localisation first.
- **Fold the manual LiDAR/SLAM bringup into a single launch file** once the pipeline is trusted.

## 15.3 Active firmware and key files (current)

| **Item** | **Current name / location** | **Notes** |
|----------|-----------------------------|-----------|
| ESP32 drive firmware | `aislebot_esp32.ino` (repo root) | v2.0 banner; renamed from `aislebot_esp32_v2.ino`. PCNT PID 50 Hz, Kp=50/Ki=30/Kd=3, per-motor Kff, latching E-STOP. |
| Mega arm firmware | `aislebot_arm.ino` (repo root) | v8: arm + staged UV lighting. Full-travel limits opened; homing/ESTOP unchanged. |
| LiDAR params | `system/ydlidar_params.yaml` | Mirrors `~/ros2_ws/src/ydlidar_ros2_driver/params/ydlidar.yaml`. |
| SLAM config (in use) | `system/slam_nodom.yaml` → `~/ros2_ws/slam_nodom.yaml` | Scan-matching only; absolute-path launch. |
| QoS relay | `src/scan_relay/scan_relay.py` | Plain script; `/scan` → `/scan_reliable`. |
| Full-stack launch | `src/mecanum_robot/launch/aislebot_full.launch.py` | Includes `odom_pub` and `lcd_display`; `/dev/esp32` + `/dev/mega`. |

## 15.4 Consolidated outstanding items (superseding older TODO lists)

- **Hardware (UV):** install the 10 kΩ pull-ups (or opto-rail separation) so the tubes don't all strike while the Mega is unpowered (Part IX, UV §6); confirm the shared LiFePO₄ pack's Ah/BMS rating against combined load; single-ballast burn-in on the modified-sine inverter; add a UV-on warning beacon.
- **Deploy the two pending config fixes to the Pi:** the port-pinned `99-aislebot.rules` and the modern-CycloneDDS `start_aislebot.sh` are corrected in the repo but not yet copied onto the running Pi (the robot runs fine without them today; they matter for a clean rebuild and for adding the LiDAR to boot autostart).
- **Control:** ground-load Kff recalibration; stress-test the ROS 2 → ESP32 serial path under sustained PID throughput on battery.
- **Cytron MDD20A Channel 2 failure** (Q4 low-side MOSFET, June 2026) — replacement decision pending; if BTS7960 IBT-2 modules are adopted, recheck the per-motor DIR convention (§12.4).
- **Autonomy:** procure/mount IMU (Phase 2); make the `AisleBot-Pi` AP the netplan default so it survives reboot; set up Foxglove Bridge.

# Part XVI — 4 August 2026: Feedback Loop Closed — Encoder Fix, Firmware v3.0, New Level Shifter

## 16.1 Encoder fault resolved, firmware recalibrated

The breadboard bench campaign (`Bench_Test_Map.md`) closed out today. All four encoders and all eight channels of the 8-channel BSS138 level shifter came back `HEALTHY` across three AUTO TEST runs and a larger 16-burst manual-drive reconfirmation. The root cause of the whole multi-session encoder saga was a **FR/FL cross-connection** — a wiring swap, not a dead shifter or a dead encoder. The front/rear raw-count ratio at matched PWM landed at 2.0–2.1×, which also independently confirmed the front (GTK08, 186,264 CPR) vs rear (RMCS-2086, 93,132 CPR) encoder split.

That fact fed straight into a firmware defect: `aislebot_esp32.ino` (through v2.0) used a single shared `ENCODER_CPR = 93132` for all four motors. On hardware with GTK08 fronts, that made FR/FL report double their true speed, so the closed loop would settle them at roughly half the commanded velocity — a permanent, silent, speed-dependent yaw bias invisible in any air-test that didn't specifically cross-check front vs rear CPR.

Firmware v3.0 fixes this and recalibrates the controller against the bench data:

- `ENCODER_CPR` is now `float[NUM_MOTORS]` — 186,264 for FR/FL, 93,132 for RR/RL.
- Feedforward is now two-term (`pwm = Kff·ω + Kstat·sgn(ω)`) rather than one slope, fitted across the 4 Aug manual-drive data, the 4 Aug AUTO TEST data, and the 14 May closed-loop back-calculation. `Kff` converged to `{37.3, 38.4, 38.3, 38.0}` — the old 19% per-motor spread (40.2–47.9) turns out to have been an artefact of the faulty-encoder era, not real motor-to-motor variation.
- `Ki`: 30 → 250, derived from the measured plant gain via lambda tuning (λ = 0.15 s). This is the actual fix for the 3.79 s worst-case settling time logged 14 May — at `Ki = 30` the integral moved about 3 PWM/s per 0.1 rad/s of error, an order of magnitude too slow to matter inside a manoeuvre.
- Anti-windup changed from a fixed `±200` clamp (which, at the old `Ki`, permitted a ~6000 PWM integral term and never actually bound) to a per-tick dynamic clamp against the real PWM headroom left after FF+P+D.
- Derivative now acts on measurement, not error, removing the kick every time the Pi steps a setpoint.
- Control loop: 50 Hz → 100 Hz.
- WiFi, the WebSocket server, and the hosted joystick page are removed entirely — the Pi is now the sole command source, so there is no arbitration path left to have a bug in.
- Added: setpoint slew limiting; overspeed / runaway / stall trips (the runaway trip specifically checks saturated+opposing+not-decelerating, so a `MOTOR_DIR_SIGN`/`ENC_DIR_SIGN` mismatch is caught even though it just pins the motor at rated speed rather than exceeding it); `<B>` body-twist passthrough; live `<K>`/`<A>`/`<X>` tuning; `<O>`/`<R>` odometry; `<L2>` extended telemetry.
- Fixed a latent bug inherited from v2.0: `<M>` direct-PWM was silently overwritten by the PID task on its next 10 ms tick, so it never actually held. Unnoticed until open-loop bench calibration needed it. There is now an explicit open-loop mode.

One gain is still an estimate: **`Kp` = 45 assumes a plant time constant τ ≈ 0.18 s that has never been measured on this robot** — every bench run logged so far captured steady-state points only, never a transient. `tools/nab_pid_logger.py --test plant` (new today, see §16.2) is built to close exactly this gap in about 40 seconds on the bench. Full derivation, all source data, and the honest confidence level on each number: `docs/PID_Calibration.md`.

`<V,...>` and the 13-column telemetry line stayed byte-identical to v2.0 throughout, so `esp32_bridge.py` and `aislebot_pid_analysis_v2.py` needed no changes.

## 16.2 Old telemetry recovered and reviewed

Pulled `~/aislebot_logs/run_20260702_183233.csv` off the Pi (`scp aritra@10.42.0.1:~/aislebot_logs/run_20260702_183233.csv .`) and added it to the repo at `data/bench_logs/run_20260702_183233.csv` for reference. This predates today's per-motor-CPR fix, so it was recorded under the old single-CPR firmware.

It is not a structured calibration run — target velocity ramps smoothly and holds varying plateaus, including several in-place rotations (opposite-sign FR/RL and FL/RR targets), consistent with a live phone-joystick drive session rather than a scripted step/staircase test.

**Reading it, under the firmware that was active at the time:**

| Motor | RMS tracking error | PWM saturation |
|---|---|---|
| FR | 0.032 rad/s | 0% |
| FL | 0.032 rad/s | 0% |
| RR | 0.041 rad/s | 0% |
| RL | 0.037 rad/s | 0% |

Against commands up to ~0.95 rad/s, that's 3–6% tracking error, no saturation, and all four motors closely matched — a reasonable showing for the old Kp=50/Ki=30/Kd=3 gains at low-to-moderate speed. One initial mis-read corrected before reporting it: the diagonal-mismatch diagnostic from `aislebot_pid_analysis_v2.py` flagged an alarming 0.60 rad/s RMS on FR−RL. Traced to source — it's an artefact of this log containing rotation commands, where FR and RL are *supposed* to carry opposite-sign targets under the mecanum IK. The diagnostic assumes straight-line motion only and isn't meaningful on a mixed drive log; not a hardware fault.

**Why this file can't be used to validate or tune v3.0:** no isolated steps to fit a step response from, and — see §16.3 — no confirmed-reliable timestamp to anchor it against a known firmware state by date alone. It's kept as a reference point for "the old controller wasn't badly broken," nothing stronger.

A fresh capture on the corrected v3.0 firmware is in progress; the wheels/PID verdict for the *current* controller will be logged here once that data is reviewed.

**Update, same day:** the fresh capture landed — `run_20260804_193703.csv`, wheels still in the air, ESP32 already reflashed with v3.0. 90.75 s, RMS tracking error 2.0–2.4% of peak commanded velocity across all four motors (peak ≈2.9 rad/s), 0% PWM saturation, 50%+ PWM headroom in reserve, zero direction-sign-mismatch samples. The clock was correct for this one (embedded `pi_time_s` matches both the filename and the pasted terminal login banner) — first confirmed-good timestamp of the session, see §16.3 for why that isn't something to assume by default. Same honest caveat as before applies: this is a live drive session, not an isolated-step test, so it confirms the loop is healthy and consistent but still doesn't fit `Kff`/`Ki`/τ for further tuning — that's what the ground `plant`/`staircase`/`steps` runs (§16.3 open items, `tools/nab_pid_logger.py`) are for.

## 16.3 Level shifter hardware — TXS0108E retired

The dual-TXS0108E design (`Master_Reference.md` §4.3–4.4 pre-4-Aug, `LevelShifter_Wiring.md`) is no longer on the robot. It's replaced by a single **8-channel discrete MOSFET (BSS138-style) bidirectional level shifter board** — no IC, no OE pin, per-channel LEDs, `LV+/LV−/HV+/HV−` power rails, `H0–H7`/`L0–L7` signal rails, all four encoders (both channels each) on the one board. This is the board the 4 Aug bench campaign (§16.1) ran all its `HEALTHY` verdicts through.

The switch was already the planned response to the TXS0108E's third failure (`Research_Journal.md` §7.12 covers the first two; the 3 Aug all-four-dead run that `LevelShifter_Wiring.md` was written to diagnose was the third). The discrete-MOSFET board removes the OE pin entirely — floating-or-low OE silently Hi-Z'ing all eight channels was one of the two recurring TXS0108E failure modes, and it structurally can't happen on a board that doesn't have an OE pin. Worth being precise about what actually caused the 3 Aug incident, though: it traced to a FR/FL wiring cross-connection (§16.1), not a defective TXS0108E — so the swap isn't "the old part was proven bad," it's "the more fragile interface got replaced with a simpler one while the root cause was being chased, and it's what's installed now."

`Master_Reference.md` §2.5 and `docs/README.md` are updated with the hardware change; `LevelShifter_Wiring.md` is marked retired but kept, since its wiring *principles* (signal direction, common ground, the GTK08-vs-RMCS colour-code trap) still apply — only the shifter part and its pin names changed. Current wiring is `Bench_Test_Map.md` §"Full 8-channel wiring — all four encoders on one board".

## 16.4 Pi system clock reliability — new open item

While chasing the CSV above, a `sudo nmcli con up eduroam` on the Pi reset the active SSH session — expected, matches the documented behaviour in `Network_SelfHosted_AP.md` §"switching networks always drops the current SSH session." Reconnected via `ssh aritra@aritra-desktop.local` (mDNS) successfully, but `apt` still failed to reach `changelogs.ubuntu.com` — eduroam association without confirmed working internet (link-layer connected, WAN reachability unverified; could be DNS, routing, or a captive-portal step that `nmcli` alone doesn't satisfy).

Cross-checking the recovered CSV's embedded `pi_time_s` (`1782997353.3266` → `2026-07-02 18:32:33 IST`) against its filename (`run_20260702_183233.csv`) shows they agree exactly — but that only proves the filename and the logged timestamp came from the same system clock, not that the clock was showing the true calendar date when the file was written.

**The underlying issue:** a Raspberry Pi 5 has no battery-backed RTC by default. The robot's normal operating mode is the self-hosted AP with no WAN path, so there is no NTP correction available during ordinary use — the clock only gets corrected on a boot that happens to have eduroam (or other internet) access at the time. Any log file's timestamp is only as trustworthy as "was this Pi's clock NTP-synced since its last reboot," which is not currently something the logging pipeline records or checks.

**Open items:**
- Confirm real internet reachability once associated to eduroam, in this order: `ping -c3 <IP literal, e.g. 8.8.8.8>` (raw L3, bypasses DNS) → `ping -c3 google.com` (DNS) → `curl -I https://example.com` (HTTPS/proxy). Narrows whether the gap is DNS, routing, or a portal.
- Once online, force a resync rather than waiting for it: `sudo systemctl restart systemd-timesyncd` then `timedatectl status` to confirm `System clock synchronized: yes`.
- Evaluate a hardware RTC module (DS3231 is the standard cheap choice, I²C, coin-cell backed) so file timestamps stay trustworthy across reboots regardless of WAN state — the right fix for a robot that spends most of its life with no internet by design.

**Resolved (6 Aug 2026):** a DS3231 (HW-084 board) is wired in on the shared I²C bus — VCC to 3.3V (not 5V, to avoid trickle-charging a non-rechargeable coin cell), SDA/SCL piggybacked onto the same lines already used by the LCD (0x27), no conflict since I²C is address-multiplexed. The Pi 5 turned out to register **two** RTC devices: `rtc0` is the SoC's own non-battery-backed clock (resets to a bogus 1970 value every boot — this is what a bare Pi 5 was actually reporting all along) and the DS3231 registered as `rtc1`. `/dev/rtc` symlinks to `rtc0` by default, so simply having the DS3231 present wasn't enough — two systemd oneshot units (`rtc1-hwclock-sync.service`, `rtc1-hwclock-save.service`) now explicitly target `/dev/rtc1` to restore system time from it at boot and save back to it on shutdown, bypassing the wrong default. Confirmed working on a full power-cycle with zero network available: system clock came back correct within seconds of boot. `util-linux-extra` (provides `hwclock`, not installed by default on this image) had to be pulled from `apt` once via the eduroam round-trip — a one-time cost, not a recurring one. Log timestamps are trustworthy from here on regardless of WAN state; the eduroam-just-to-fix-the-clock workflow in this section is no longer needed for routine use.

## 16.5 Where this leaves the feedback loop

As of today, the encoder feedback loop is closed end-to-end on confirmed-good hardware: all four encoders verified `HEALTHY` through all eight channels of the new shifter board (§16.1, §16.3), per-motor CPR corrected in firmware, PID/feedforward recalibrated against real bench data, and the ESP32 reflashed with v3.0 and running (§16.2 update). That's the hardware+firmware side of the two-month encoder hurdle — done.

What's still open before calling the *controller* validated: ground-load recalibration (air-calibrated `Kff`/`Kstat` are expected to rise 10–30% under real chassis weight — `PID_Calibration.md` §7) and the plant-ID bench run for `Kp` (§16.1, τ still unmeasured). Ground testing starts next — first calibration, then wheel odometry accuracy (feeds `odometry_publisher.py`, already in the tree), then SLAM/Nav2 tuning on top of that.

One capability regression to carry forward alongside that: §16.6.

## 16.6 Consequence of removing WiFi: the ESP32 escape hatch is gone

Recorded separately because it is a **safety-relevant capability loss**, not just a code cleanup, and it was not called out when the change was made.

Firmware v3.0 removes the ESP32's WiFi AP, WebSocket server and joystick page (§16.1, item 1). Several documents described that AP (`AisleBot-Control` @ `192.168.4.1`) as the independent escape hatch for a dead Pi — `Network_SelfHosted_AP.md`, `Master_Reference.md` §6.6, Part III §3.7, Part XIV. All of those are now stale and have been corrected.

**What was lost:** the ability to *drive* the robot with the Pi down (crash, SD corruption, kernel panic, USB drop). That was the escape hatch's entire purpose.

**What still holds without the Pi:** the ESP32's own command watchdog stops the motors ~750 ms after commands stop arriving, and the runaway / stall / overspeed trips latch E-STOP autonomously. So a dead Pi now produces a **stopped** robot rather than a drivable one — the safer of the two failure modes, but genuinely less capable. The only manual override that does not depend on the Pi is now the battery disconnect, which must stay physically reachable during ground testing.

Restoring a hardware-independent override (a 2.4 GHz RC receiver on a spare ESP32 input, or a minimal WiFi E-STOP-only endpoint that doesn't reintroduce the arbitration path v3.0 deliberately deleted) is an open item.

## 16.7 6 Aug 2026: Pi-vs-GitHub code drift audit

No persistent git clone exists on the Pi (`~/aislebot` was never created — deployed code lives only under `~/ros2_ws/src`), so "does the Pi actually run what's on GitHub" isn't answerable with `git diff`. Verified instead by sha256-checksumming the live Pi files against the repo, file by file. Found and fixed three real drifts:

- **CycloneDDS syntax.** `~/start_aislebot.sh` on the Pi still used the deprecated `<NetworkInterfaceAddress>lo</NetworkInterfaceAddress>` form, silently ignored on Jazzy (the recurring log warning this produced was previously unexplained). Replaced with the modern `<Interfaces><NetworkInterface name="lo" .../></Interfaces>` form in both the repo (`system/start_aislebot.sh`) and on the Pi.
- **`max_wheel_speed` override.** The Pi's `esp32_bridge.py` was a stale v2.0-era copy with the node default hardcoded at `6.28`; deployed the current v3.1 copy (default `5.20`, per the ground-calibration note in `PID_Calibration.md` §7). `ros2 param get` still showed `6.28` afterward — traced to `aislebot_full.launch.py` hardcoding `'max_wheel_speed': 6.28` as an explicit launch parameter, which always wins over a node's own default. Fixed in the repo (`src/mecanum_robot/launch/aislebot_full.launch.py`) and deployed to the Pi; confirmed via `ros2 param get /esp32_bridge max_wheel_speed` → `5.2`.
- **Dead Xbox-controller wait.** `start_aislebot.sh` had a 10-second polling loop for `/dev/input/js0` that this robot doesn't have (phone dashboard is the only control path — §16.6). Replaced with a single non-blocking check; confirmed via clean-restart timing that nodes now come up well inside what used to be the wait window.

Also confirmed the day's 494-package `apt` upgrade did not regress ROS2 (`ros2 doctor` clean, `aislebot.service` starts clean), and corrected `Network_SelfHosted_AP.md`'s "manual start only" section, which had gone stale — the AP was already found to persist across reboot via a persistent netplan autoconnect-priority entry (5 Aug 2026 finding), not the manual `nmcli con up aislebot-ap` step the doc still described as required. All of the above committed and pushed to `claude/raspi-server-setup-it5gu8`.

## 16.8 6 Aug 2026: First LiDAR ground test — checksum-error saga and a duplicate-node `/map` failure

The first ground test (previous LiDAR work in Part XIII was bench-only) surfaced two separate problems in sequence.

**Problem 1 — data corruption, resolved.** Early runs reproduced the exact failure signature `LiDAR_SLAM_Bringup.md` warns about: `Sample Rate` at ~2.9K instead of the healthy 5.00K, a continuous `Checksum error` flood, and point counts swinging well outside the ~1258-point baseline. Reseating both USB cables (data + power) did not immediately fix it; the fault turned out to be intermittent and resolved itself without a single cause being definitively pinned (marginal connection under vibration is the leading suspect, not confirmed). Validated clean on a genuine ~2-minute multi-direction driving test: `Sample Rate` held at 5.00K throughout with only one checksum error, at startup. This confirms the physically-mounted YDLIDAR X4 Pro produces trustworthy data under real driving conditions, not just on the bench.

**Problem 2 — `/map` never published, root-caused to duplicate nodes.** With clean scan data confirmed, the 3-terminal pipeline (lidar → relay → slam_toolbox) still never produced a `/map` message (`ros2 topic hz /map` returned nothing), despite `/scan_reliable` running healthy — but at ~22.6 Hz, roughly double the ~11 Hz the driver actually publishes at. `ros2 node list` explained why: it reported a duplicate-name warning, showing **two** `/scan_relay` nodes and **two** `/static_tf_pub_laser` nodes. Across several restart attempts over multiple terminal sessions, earlier `scan_relay.py` and `ydlidar_launch` processes had never actually been killed, so each new terminal added a second instance on top rather than replacing the first — two relays both re-publishing the same best-effort `/scan` onto `/scan_reliable`, doubling the rate and feeding slam_toolbox duplicated/interleaved scans it apparently could not use.

A targeted `pkill -f scan_relay.py` / `pkill -f ydlidar_launch` / `pkill -f online_async_launch` cleared the duplicate `/scan_relay` but left `/static_tf_pub_laser` still duplicated and three residual `/launch_ros_*` nodes behind — killing individual stray PIDs on a headless Pi with several nested launch processes wasn't converging quickly enough, so the call was made to reboot the Pi outright rather than keep chasing PIDs. `aislebot.service` and the two RTC systemd units (§16.4) both auto-restart across a reboot with no manual step, so nothing else needed re-doing.

**Status at time of writing:** reboot in progress; the pipeline has not yet been re-verified end-to-end since. Next step on resume: `ros2 node list` to confirm a clean process table (no duplicate names, no stray `/launch_ros_*`), then relaunch the 3 documented terminals one at a time, watching for `Registering sensor: [Custom Described Lidar]` in the slam_toolbox terminal (not just `Activating`) as proof scans are actually being consumed, then `ros2 topic hz /map` before attempting `map_saver_cli` again.

Separately, and not blocking: the LiDAR's current temporary mount puts the battery in its line of sight, restricting field of view. Elevating the mount is deferred until the software/mapping pipeline itself is confirmed working — a pure mounting fix, unrelated to the data-corruption issue above.

## 16.9 6 Aug 2026: First ground-truth `/map` — two root causes, neither the one originally suspected

Resumed from §16.8's reboot. `ros2 node list` came back clean of duplicates as expected, but the pipeline still didn't produce `/map` — and the actual reasons turned out to be more specific than "terminals not properly killed."

**Root cause 1 — an undocumented systemd unit was colliding with every manual bringup attempt.** `ydlidar.service` (`/etc/systemd/system/ydlidar.service`, `ExecStart=/bin/bash /home/aritra/start_lidar.sh`, `enabled`, `Restart=on-failure`) auto-starts the lidar driver + `scan_relay.py` at boot, entirely independent of `aislebot.service`. It is not vendored anywhere in this repo — `install.sh` only ever installs `aislebot.service` — so nobody following `LiDAR_SLAM_Bringup.md` would know it exists. Every manual Terminal 1 + Terminal 2 launch across this session and §16.8 was stacking a second `/ydlidar_ros2_driver_node` and `/static_tf_pub_laser` on top of an already-running systemd-managed pair, fighting over `/dev/ydlidar` and reproducing the exact checksum-error-flood signature `LiDAR_SLAM_Bringup.md` attributes to cable/vibration issues. This also retroactively explains why §16.8's `pkill` attempts "weren't converging" — `Restart=on-failure` would simply respawn what got killed. Fixed for this session with `sudo systemctl stop ydlidar.service && sudo systemctl disable ydlidar.service`, followed by a full reboot to get a verified-clean baseline. `start_lidar.sh`'s own header comment confirms it was deliberate infrastructure (June 2026, keeping lidar independent of drive-stack power-cycles during encoder debugging), just never reconciled with the repo. Left disabled for now rather than folded into the pipeline — properly extending it to include `slam_toolbox` and vendoring it into `system/`+`install.sh` is deferred until there's a documented, tested manual pipeline to build it from.

**Root cause 2 — `odom` never existed in TF at all.** With the systemd collision removed, the lidar (`Sample Rate` 4.90–5.13K, only 1-2 transient checksum errors at connect, clean thereafter) and relay (`/scan_reliable` steady at ~11.35 Hz) both verified healthy. But `slam_toolbox` reached `Activating` and then produced no further output — no `Registering sensor` line, no `/map`, no error. `ros2 run tf2_ros tf2_echo odom base_link` showed *"frame does not exist"*, not staleness. Traced to `odometry_publisher.py`: it only ever calls `sendTransform()` inside its `/wheel_velocities_actual` subscription callback — no timer, no fallback. That topic is only populated by `esp32_bridge` after the ESP32 has been sent `<L1>` (enable telemetry), which is gated by the `telemetry_enabled` parameter — defaulted `False`, and never overridden in `aislebot_full.launch.py`. So `odometry_publisher`'s callback had never fired once since boot, regardless of whether the robot moved. Confirmed by live-unblocking with `ros2 topic pub --once /esp32/command std_msgs/msg/String "data: '<L1>'"` — `odom` appeared immediately and tracked real translation when the robot was driven forward/backward. `slam_toolbox` logged `Registering sensor: [Custom Described Lidar]` right after, and `/map` began publishing at a steady 1.000 Hz.

**Fixed in the repo:** `aislebot_full.launch.py`'s `esp32_bridge` node now sets `'telemetry_enabled': True`, making today's live unblock permanent — once redeployed to the Pi's `~/ros2_ws/src` copy and `aislebot.service` restarted (repo and Pi are not auto-synced, same drift risk as §16.7; the live `<L1>` unblock does not survive a bridge reconnect on its own). `LiDAR_SLAM_Bringup.md` gained a "two silent blockers" section covering both root causes, plus the `Registering sensor` and `ros2 node list | sort | uniq -d` verification steps that actually caught them this session.

**First map saved:** `~/aislebot_first_map.{pgm,yaml}`, 139×198 px @ 0.05 m/pix (~7 m × 9.9 m extent). Pixel histogram: 22371 unknown / 4782 free / 369 occupied — ~81% unknown. A valid proof that the full pipeline works end-to-end, but sparse — the drive that produced it was a short forward/backward validation pass, not a deliberate mapping run. Next session: redeploy the launch-file fix (or keep using the manual `<L1>` command until that's done), then do a longer multi-direction drive with real loop closure for a properly-covered map.

## 16.10 6 Aug 2026 (continued): telemetry deployed to the Pi, a third silent failure mode, second map, and a one-command bringup

Later the same session. The `telemetry_enabled: True` fix was deployed directly on the Pi (`sed` edit to the live `~/ros2_ws/src/mecanum_robot/launch/aislebot_full.launch.py` copy, then `sudo systemctl restart aislebot.service`) and confirmed via `ros2 param get /esp32_bridge telemetry_enabled` → `True`. It survived a subsequent full reboot correctly — the fix itself is solid.

**A third silent failure, distinct from both §16.9 root causes.** Mid-session, `/wheel_velocities_actual` stopped publishing and `odom` reverted to "frame does not exist" — with `esp32_bridge` and `odometry_publisher` both still alive (`ros2 node list`), and drive commands still reaching the ESP32 (the robot could still be driven; wheels only stopped later from the drive-command watchdog after a few idle minutes, not from anything broken). `~/aislebot_boot.log` (not `journalctl` — `start_aislebot.sh` redirects all node output to that file, so `journalctl -u aislebot.service` only ever shows systemd's own start/stop lines, never the node logs) showed a single clean `Connected to ESP32` per boot with no reconnect or error logged, so the Python-level serial connection object never registered a drop. Working theory: the ESP32 itself reset (brownout under load is the leading suspect) fast enough that the Pi-side serial layer never saw a disconnect, so `esp32_bridge` never re-entered `connect_serial()` to resend `<L1>`, while `<V,...>` drive commands kept being accepted normally post-reset. Root cause not fully confirmed. Fix each time was the same manual `ros2 topic pub --once /esp32/command std_msgs/msg/String "data: '<L1>'"` unblock — worked reliably, but the permanent launch-file fix only guarded the boot-time case, and this recurred at least twice more within the same session (once mid-drive, once while testing the new consolidated launch file below), confirming it's a real recurring failure mode, not a one-off.

**Fixed properly, same session:** `esp32_bridge.py` now has a 5-second timer (`resend_telemetry_enable`, only active when `telemetry_enabled` is set) that re-sends `<L1>` on its own whenever connected, instead of only once inside `connect_serial()`. Self-heals within 5s of any silent ESP32-side reset instead of needing a manual unblock. Sending `<L1>` repeatedly is assumed idempotent (it's a mode-enable toggle, not a counter) — not independently verified against the firmware source, worth confirming if telemetry ever behaves oddly after this change.

**Second map:** `~/aislebot_map_2.{pgm,yaml}`, 184×199 px, saved after a `/map` stream that held a clean 1.000 Hz for 183+ continuous seconds. Pixel histogram: 29140 unknown / 6297 free / 1179 occupied (79.6% / 17.2% / 3.2%) — occupied-cell count more than tripled versus the first map (369→1179), meaning meaningfully more wall/obstacle detail resolved, though free-space fraction stayed about the same (still mostly gray outside the driven path). Confirms the pipeline is repeatable across multiple reboot cycles, not a one-off.

**Consolidated bringup:** new `src/mecanum_robot/launch/mapping_full.launch.py` combines all three pieces (lidar driver via `IncludeLaunchDescription` of `ydlidar_ros2_driver`'s own launch file, `scan_relay.py` via `ExecuteProcess` since it isn't an installed package executable, and slam_toolbox via `IncludeLaunchDescription` of `online_async_launch.py` with `slam_params_file` passed through) into one `ros2 launch mecanum_robot mapping_full.launch.py` command. `setup.py` already globs `launch/*.launch.py`, so no other packaging change was needed. Deliberately **on-demand only, no systemd service** — explicit choice, given that an always-on auto-started service is exactly what caused most of this session's debugging (`ydlidar.service`, §16.9). `LiDAR_SLAM_Bringup.md` now leads with this one-command path and keeps the original per-terminal steps as the debugging fallback. Wiring it to an actual phone-dashboard trigger (the longer-term "power on → press button → map and drive" goal) is future work, not done this session. Ran clean once (Sample Rate 5.85K, zero checksum errors, all four processes up together) before the telemetry issue below reappeared and interrupted further testing.

**Open at end of session — the telemetry self-heal did not resolve a post-reboot recurrence, cause not yet isolated.** After the clean reboot in the previous item, `/wheel_velocities_actual` and `odom` did not come up on their own — same "frame does not exist" symptom, but this time NOT clearing after 5+ minutes (dozens of expected 5-second resend cycles), which the fix should have caught. `~/aislebot_boot.log` confirmed a clean `Connected to ESP32` for this boot with no subsequent error logged. Checked the actual firmware (`aislebot_esp32.ino` line 949-950) to rule out `<L1>` being a toggle that repeated resends would fight against — it's a plain `telemetry_mode = cmd[1] - '0'` set, idempotent, not a toggle, so that's not the explanation. Two diagnostics were queued but **not run before the session ended**:
1. `ros2 topic hz /motor_telemetry_raw` — bisects whether *any* bytes are arriving from the ESP32 at all (would point at a hardware/RX-path issue) versus arriving but failing to parse into `/wheel_velocities_actual` (a narrower software bug in `parse_esp32_line`/`_publish_telemetry`).
2. A fresh manual `ros2 topic pub --once /esp32/command std_msgs/msg/String "data: '<L1>'"` retry on this same boot — if that still fixes it like every prior occurrence, the resend timer itself likely isn't actually firing (a bug in the deployed fix, not a hardware regression); if manual `<L1>` *also* fails this time, that's a real escalation.

**Next session: run those two checks first**, before anything else. Current state to resume from: `ydlidar.service` still disabled, `mapping_full.launch.py` deployed and structurally proven, `esp32_bridge.py`'s resend timer deployed but its actual effectiveness unconfirmed pending the above.

## 16.11 Scope for the next session — reliable bringup as a system, dashboard-triggered mapping + recording

Captured at the end of this session, in the user's own framing: hardware is considered solid at this point; what's left is software — ROS2/SLAM bringup reliability and the dashboard/analysis layer on top of it. Goals, in order:

1. **Finish §16.10's open item first.** The telemetry self-heal doesn't yet reliably clear a post-reboot recurrence. Run the two queued diagnostics before anything else: `ros2 topic hz /motor_telemetry_raw` (bytes arriving at all vs. a parsing bug) and a fresh manual `<L1>` retry (resend timer not firing vs. a genuine link regression). Nothing else below is worth building on top of an unreliable bringup.

2. **A "Map" button on the phone/PC dashboard**, replacing the existing `phone_dashboard.py` "RECORD RUN" button (`toggleRecording()` / `record_start` / `record_stop` WebSocket messages, `start_recording()`/`stop_recording()` on the dashboard node, logs to `~/aislebot_logs/run_YYYYMMDD_HHMMSS.csv`). Pressing "Map" should, as one action:
   - Bring up the mapping stack (`mapping_full.launch.py`) — `phone_dashboard.py` doesn't currently launch or manage other ROS2 processes, so this is new: needs a way to start/stop that launch tree from the dashboard node (subprocess management, most likely) rather than a human running it in a terminal.
   - Start telemetry/PID recording automatically at the same time, using the existing `start_recording()` path — **every mapping run recorded by default**, no separate toggle.
   - Stop both together, cleanly, when pressed again or the run ends.
   - Deliberately a placeholder for a future "Autonomous Drive" button once SLAM is trusted enough — same UI slot, different behavior later. Not building autonomy behavior itself yet.

3. **Deep post-run analysis after every recorded run** — PID performance, map quality, and other research-grade metrics. Existing tools to build from: `tools/nab_pid_logger.py`, `aislebot_pid_analysis_v2.py`, `docs/tools/telemetry_analyzer.html`. What "deep analysis" concretely means (which metrics, what output format) isn't defined yet — needs scoping with the user before implementation, not assumed.

**Explicitly out of scope for this work, deferred to a separate future discussion**: full SLAM parameter tuning for autonomy, dynamic modeling, and what's needed for reliable/robust/adaptive/autonomous control. The user wants to discuss this deliberately, not have it bundled into the reliability/dashboard work above — flagged here so the topic isn't lost, not because it's unimportant.

## 16.12 7 Aug 2026: Post-reboot bringup re-verified clean — §16.10's gap did not recur

Resumed from §16.10–§16.11's open item, fresh Pi boot. Ran the two queued diagnostics plus one more to fully bisect the pipeline:

- `ros2 topic hz /motor_telemetry_raw` — steady ~20.4 Hz from the start. Rules out "nothing arriving from the ESP32."
- `ros2 topic hz /wheel_velocities_actual` — steady ~20 Hz, including through a period of active driving (a brief rate/jitter wobble during motion self-corrected, not a drop).
- `ros2 run tf2_ros tf2_echo odom base_link` — tracked real translation and rotation cleanly through a full drive sequence (forward ~1 m, an in-place rotation past 180°, return), no "frame does not exist" beyond the single line `tf2_echo` prints before its very first message ever arrives (normal startup, not a gap).

All three healthy end-to-end. This boot never reproduced §16.10's gap — the `telemetry_enabled: True` launch-file fix (§16.9) held cleanly across this reboot.

**Still open, deliberately deferred rather than resolved:** the `resend_telemetry_enable` 5-second timer (§16.10's self-heal fix) was never actually exercised — nothing broke for it to heal from. A controlled repro (pressing the ESP32's EN/RST button while watching `/wheel_velocities_actual` hz, confirming recovery within ~5-10s with no manual `<L1>`) was proposed and declined for this session in favor of moving on to §16.11's items 2-3. Do this the next time bringup is touched, or immediately if the gap recurs.

**If the gap recurs:** first check is the drift audit, not new code — `sha256sum ~/ros2_ws/src/mecanum_robot/mecanum_robot/esp32_bridge.py` against this repo's copy and `grep -n resend_telemetry_enable` on the deployed file. That exact pattern (fix committed to the repo, Pi's `~/ros2_ws/src` copy left stale) has recurred multiple times on this project (§16.7, §16.9–§16.10) and is the more likely explanation than a new hardware regression.

Bringup accepted as solid enough to build on for today's session goals.

## 16.13 7 Aug 2026: Map button on the dashboard, replacing RECORD RUN

`phone_dashboard.py` v2.3. Replaces the RECORD RUN button (`toggleRecording()` / `record_start` / `record_stop`) with a Map button in the same UI slot — same bottom-bar position, keyboard shortcut moved `R` → `M`. Per §16.11 item 2, one press now does two things as a single action:

- Launches `ros2 launch mecanum_robot mapping_full.launch.py` (lidar + `scan_relay.py` + `slam_toolbox`) as a subprocess, in its own process group (`preexec_fn=os.setsid`) so it can be cleanly stopped as a unit.
- Calls the existing `start_recording()` path unchanged — every mapping run is recorded by default, no separate toggle, exactly as scoped.

Second press (or E-STOP) stops both together: `SIGINT` to the launch tree's process group (mirrors a terminal Ctrl+C, so `ros2 launch` cascades its own shutdown to lidar/relay/slam_toolbox), a 10s wait, then `SIGKILL` to the group if it hasn't exited, followed by `stop_recording()`. E-STOP's handler changed from calling `stop_recording()` to `stop_mapping()`, so hitting E-STOP now also tears down any in-flight mapping run instead of leaving `mapping_full.launch.py` orphaned in the background.

New WebSocket message types `map_start` / `map_stop` replace `record_start` / `record_stop`. `start_recording()` / `stop_recording()` themselves are untouched — reused exactly as §16.11 specified, just no longer independently reachable from the UI.

Deliberately trigger-only: this is the placeholder for a future "Autonomous Drive" button once SLAM is trusted (same UI slot), not autonomy behavior itself. No crash recovery if `mapping_full.launch.py` dies mid-run on its own (`mapping_active` would stay stuck `True` until the next E-STOP or dashboard restart) — accepted as a known gap for today rather than built around, consistent with keeping robustness/autonomy work out of this session's scope.

Verified with a static render of the extracted dashboard HTML in a headless browser (idle "MAP" state and the active "STOP MAP" pulsing state both confirmed visually) — this session has no network path to the Pi, so the actual launch/record behavior end-to-end is unverified against real hardware. That's next-session/on-Pi work: press Map, confirm `mapping_full.launch.py`'s four processes come up and a CSV starts under `~/aislebot_logs/`, press it again mid-run, confirm the launch tree and recording both stop cleanly with no orphaned `ros2 launch` process left behind (`ps aux | grep mapping_full`).

## 16.14 7 Aug 2026: automated post-run analysis report — a Python port of telemetry_analyzer.html, run headless

Before building anything, checked the three tools §16.11 pointed at: `tools/nab_pid_logger.py` (bench-only, but its 13-column CSV format is byte-identical to what `phone_dashboard.py`'s `start_recording()` already writes), `aislebot_pid_analysis_v2.py` (a Google Colab notebook, manual upload each time), and `docs/tools/telemetry_analyzer.html` — which turned out to already be far more built-out than expected: per-motor RMS/settling-time/PWM-saturation metrics, diagonal-mismatch and dead-feedback diagnostics, plain-language pass/warn/fail findings, a Compare tab across runs, and (per the note that prompted checking it first) a Map tab that loads a run's `.pgm`/`.yaml` and computes coverage/occupancy stats with its own findings — plus a combined JSON/CSV export. The analysis logic itself was already solid; the gap was that it's manual and pull-based, with nothing generating it automatically after a run.

Scoped with the user rather than assumed (as §16.11 flagged): keep the existing HTML tool's analysis logic as the reference implementation, and automate the trigger — every mapping run gets a report with no manual drag-and-drop step, matching how recording itself became automatic in §16.13.

**`src/mecanum_robot/mecanum_robot/run_report.py` (new).** A pure-stdlib Python port of `telemetry_analyzer.html`'s metrics/findings/map-stats functions (`computeMetrics`, `detectSettlingTimes`, `buildFindings`, `parsePgm`, `classifyMapPixel`, `computeMapStats`, `buildMapFindings`, `parseSimpleYaml`) — needed because the dashboard runs headless on the Pi with no browser to open the HTML tool in, so the equivalent analysis has to run server-side. No numpy/pandas/PyYAML — deliberately dependency-light for on-Pi automation, mirroring the browser's own from-scratch parsing. Exposes `generate_report(csv_path, pgm_path=None, yaml_path=None) -> dict` for direct import, plus a standalone CLI (`ros2 run mecanum_robot run_report <csv> --map <prefix>`, added to `setup.py`'s console_scripts) for regenerating a report from an old run by hand.

**Verified numerically, not just "looks reasonable."** Extracted the actual JS functions from `telemetry_analyzer.html` into a standalone Node script and ran both implementations against the same inputs: a real bench CSV (`data/bench_logs/run_20260804_193703.csv`, 1816 samples) for the PID path, and a synthetic CSV plus a synthetic `.pgm`/`.yaml` pair (with deliberately borderline pixel values to exercise the nearest-neighbor occupied/free/unknown classification) for both paths together. Diffed every numeric field — exact match on both, including the findings text. This matters because a research-grade tool silently disagreeing with its own browser counterpart would be worse than not having automation at all.

**`phone_dashboard.py`'s `stop_mapping()` extended, sequencing matters here:** it now (1) calls `map_saver_cli` on the still-running `mapping_full.launch.py` process *before* sending it SIGINT — `/map` stops existing the moment slam_toolbox dies, so the map has to be saved while the launch tree is still alive, not after; (2) stops the launch tree and recording as before; (3) generates the report from the just-closed CSV plus the saved `.pgm`/`.yaml` (same filename stem as the CSV, so all three land together in `~/aislebot_logs/`), and logs the health verdict and each finding. Every step degrades gracefully — a `map_saver_cli` failure or timeout logs a warning and the report simply omits the map block instead of blocking or crashing the WebSocket handler; a report-generation failure is caught and logged the same way.

**Not verified end-to-end on hardware** — same caveat as §16.13's Map button, compounded: this session has no path to the Pi, so `stop_mapping()`'s new sequencing (map save while the process group is still alive, then kill, then report) is unverified against a real `mapping_full.launch.py` run. Next session: press Map, drive briefly, press Map again, confirm `~/aislebot_logs/` ends up with matching `run_*.csv`, `run_*.pgm`, `run_*.yaml`, and `run_*_report.json`, and that the report's numbers are sane against what `telemetry_analyzer.html` shows for the same CSV.

## 16.15 7 Aug 2026: Map button + automated report — confirmed end-to-end on hardware

Closes out the "not verified on hardware" caveat both §16.13 and §16.14 ended on. Deployed today's three changed files (`phone_dashboard.py`, `run_report.py`, `setup.py`) to the Pi via `curl` against the raw GitHub URLs for this branch (the Pi briefly went on eduroam and the repo was made public for this — no persistent git clone was set up, same manual-deploy pattern as always), rebuilt with `colcon build --packages-select mecanum_robot`, restarted `aislebot.service`, and verified via `sha256sum` that all three files matched this repo byte-for-byte before trusting the deploy.

**Full round-trip, one press each way, no manual intervention:** pressed Map, drove for ~157s, pressed Map again. Confirmed via live `ros2 node list` that `mapping_full.launch.py`'s subprocess pid matched exactly what the dashboard logged ("Mapping started (pid 3145)" ↔ `/launch_ros_3145` in the node list) — the subprocess tracking isn't just launching something and losing track of it. `~/aislebot_logs/` ended up with all four files sharing one timestamp stem (`run_20260807_174101.{csv,pgm,yaml}` + `_report.json`), confirming the map-save-before-kill ordering from §16.14 actually holds on real hardware — the `.pgm` is 41 KB, not empty, so `map_saver_cli` captured a real map while slam_toolbox was still alive, not after it had already been killed. `ps aux | grep mapping_full` came back empty afterward — no orphaned `ros2 launch` process.

**The auto-generated report's own findings check out against known-good numbers.** 3146 samples, 157.3s, health `ok`, one PID finding (diagonal mismatch — expected for a driven run with turns, not a fault) and one map finding: 81.0% unknown correctly triggered "Sparse coverage" (the 70–90% warn band, not the >90% bad band) — same ballpark as §16.9's first map (81% unknown) and §16.10's second (79.6% unknown), both short drives without deliberate loop closure. No warnings logged about `map_saver_cli` failing or the launch tree needing `SIGKILL` — both hit their clean-path branches.

Bringup (§16.12), the Map button (§16.13), and the automated report (§16.14) are now all confirmed solid on hardware, not just structurally. Today's three-item scope from §16.11 is complete.

## 16.16 7 Aug 2026: consolidated onto `main` — v3.0 ESP32, the Map button, and automated analysis are now the baseline

With §16.12–§16.15 confirmed solid on real hardware — bringup, the Map button, and the automated post-run report all working end-to-end, not just structurally — this branch (`claude/raspi-slam-mapping-bringup-75tf7i`) was merged into `main`. Also cleaned up the branch list: three fully-merged-or-superseded branches (`claude/nab-raspi-ros`, `claude/narrowaislebot-prototype-arch-m9y94t`, `claude/raspi-server-setup-it5gu8`) deleted from GitHub after verifying via git ancestry (not just commit dates) that nothing unique would be lost. `claude/nab-hardware-calibration` was deliberately kept — it has real unmerged ground-calibration work unrelated to this session. `claude/raspi-slam-bringup-mapping-ea3twn` was flagged for deletion too but missed in the cleanup pass; still pending.

Two small repo-organization additions alongside the merge, both scoped to what this session actually made obsolete or repeatedly needed — not a general sweep:

- **`past_iterations/`** (new, repo root) — an explicit archive for superseded tools, kept rather than deleted so an older approach can still be compared against. `aislebot_pid_analysis_v2.py` (the Google Colab notebook requiring a manual upload every run) moved here, superseded by `run_report.py` + `telemetry_analyzer.html`'s automatic, no-browser-needed equivalent (§16.14). A `past_iterations/README.md` explains what replaced what and why, and future replacements should add an entry there instead of deleting the old file outright.

- **`docs/Important_Commands.md`** (new) — a copy-paste command reference for the things done over and over this session: SSH login (AP-mode fixed IP vs. eduroam mDNS hostname), deploying a code change to the Pi (no persistent git clone, so this means `curl` from GitHub's raw URL + `sha256sum` verify + `colcon build` + service restart), downloading run data to a PC (`scp`/`rsync`), where everything lives on the Pi, how to view a map (`telemetry_analyzer.html`, not the raw `.pgm`), and a short list of quick health-check commands. Doesn't replace `Network_SelfHosted_AP.md` or the Research Journal's own detail — it's the fast-reference layer on top of them.

# Part XVII — SLAM, Visualization, and Autonomous Drive

Opened 7 Aug 2026, same day as Part XVI's close. The user's own framing: bringup is concluded and confirmed working — move to reliable mapping/visualization, real SLAM, and proper autonomous drive. Two-week timeline. IR proximity sensors (the 8-pair collision-avoidance layer discussed earlier this session) are explicitly deferred — mapping and SLAM first. Standing requirement for everything from here forward: scientifically sound, reasoned, grounded in real literature — this is PhD work, not a hobby build.

## 17.1 Literature review: SLAM algorithm choice, done before touching any parameters

Per the user's explicit instruction — don't tune anything without grounding the choice in real papers first. Searched and verified via Scite (not assumed from memory; every paper below was retrieved from the actual publication record and checked for retractions/corrections before citing). Full write-up: `docs/SLAM_Theory.md`. Full citation list with DOIs: `research_articles/README.md` (new folder, new convention going forward — any paper that materially informs a decision gets added there, cited by author/year in whichever doc it backs).

**Bottom line: `slam_toolbox` (Macenski & Jambrečić, 2021) — what this robot already runs — is the scientifically justified choice, not just the path of least resistance.** Compared against the real alternatives:
- GMapping/RBPF (Grisetti, Stachniss & Burgard, 2007) carries one map copy per particle — memory/compute scales with particle count × map size, a real cost on a Pi 5 with no GPU (quantified directly in Sugiura & Matsutani's FPGA-acceleration papers, 2021/2022, built specifically because RBPF-SLAM is too slow on embedded hardware otherwise). An empirical comparison on an RPLidar-A1 — same hardware tier as this robot's YDLIDAR X4 Pro — found it noisier and less accurate than scan-matching approaches on this sensor class (Laksono & Kusuma, 2022).
- Hector SLAM (Kohlbrecher et al., 2011) has no pose-graph back-end and no loop closure — drift is minimized going forward, never corrected once accumulated. Its no-odometry philosophy was the right call while this project's odometry was unreliable (§16.9–§16.10), but that's no longer the situation.
- Cartographer (Heß et al., 2016) is more sophisticated (submaps + branch-and-bound global matching) — a reasonable future upgrade if map scale grows well past a single narrow-aisle environment, but more machinery than the current problem needs.

**One concrete, reasoned recommendation for the next session, not just a confirmation of the status quo:** this project currently runs `slam_toolbox` scan-matching-only, deliberately not fusing wheel odometry as a pose prior (`system/slam_nodom.yaml`) — a choice made when the odometry pipeline itself was unreliable. That reasoning doesn't automatically hold anymore: §16.12 and §16.15 confirmed odom-TF holds cleanly across reboots and real driving. A scan matcher with a good motion prior converges faster and more reliably than one with none. **Next session: benchmark `slam_toolbox` with odometry-as-prior enabled against the current no-odometry config**, now that the original reason for avoiding it no longer applies. Full derivation of why in `docs/SLAM_Theory.md` §2.3.

`docs/SLAM_Theory.md` also derives the actual math the algorithm runs, cited throughout: the point-to-line ICP scan-matching metric (Censi, 2008) `slam_toolbox`'s front-end descends from, the pose-graph nonlinear least-squares formulation (Grisetti, Kümmerle & Stachniss, 2010) the back-end solves, and the Bayesian log-odds occupancy-grid update (Moravec & Elfes, 1985) — with an explicit tie back to this project's own tooling: the `.pgm` convention `run_report.py`'s `classify_map_pixel` reads (0/205/254 = occupied/unknown/free) is literally that log-odds value, saturated toward its extremes as evidence accumulates. "81% unknown" in §16.15's map isn't a separate metric from the theory — it's cells that never accumulated enough log-odds evidence to move off zero.

## 17.2 Next session: LiDAR placement trial — three positions, one test procedure, ready to run

The user has three candidate LiDAR mounting positions in mind and wants an empirical trial-and-error comparison, not a guess, before committing to a final mount (extends the §16.8/B.6 deferred "elevate the LiDAR mount" item, now informed by the mechanical analysis done earlier this session — the tall fixed rear stack cannot be practically cleared, so the real comparison is about how much the *battery* occlusion specifically costs each position).

**Three positions to test, same robot, same route each time:**

1. **In front of the battery, current height (not elevated)** — battery blocks part of the LiDAR's line of sight. The baseline/worst case.
2. **On top of the battery** — battery occlusion removed; the fixed rear-stack blind wedge (accepted as static and unavoidable per this session's earlier analysis) remains, which is fine.
3. **In front of the battery, elevated** — battery occlusion avoided by height instead of by repositioning onto it.

**One test motion, run identically for all three positions, so the comparison is fair:**
1. Stationary for the first minute (baseline scan, no motion blur/timing artifacts).
2. Drive forward.
3. Drive backward.
4. One full rotation in place, clockwise.
5. One full rotation in place, counter-clockwise.

Same path, same duration targets, for all three — the only variable being compared is mount position. Use the **Map** button (§16.13) for each run — every run gets recorded and auto-analyzed (§16.14) with no extra steps, so all three runs produce a directly comparable `_report.json` map-quality section (unknown/free/occupied %, findings) plus the `.pgm` for visual comparison in `telemetry_analyzer.html`'s Map tab.

**What decides the winner:** lowest `unknownPct` / highest usable coverage for the same driven path, no new findings-level warnings (e.g. "Sparse coverage") that the other positions don't also have, and — separately from the automated report — an eyeballed check in RViz2 or the Map tab for whether the accepted rear blind wedge is the *only* dead zone, or whether a new one appeared from whatever the position change was near.

## 17.3 Session and branch close-out

This session (branch `claude/raspi-slam-mapping-bringup-75tf7i`) closes here. Everything in it — bringup reliability, the Map button, automated analysis, the `main` consolidation, and this literature review — is merged onto `main` and confirmed working. The next phase (LiDAR placement trial → SLAM implementation → autonomous drive) starts in a **new session on a new branch**, since §17.2's trial needs the user at the robot. Two weeks allotted for a reliable SLAM + AMR result, everything grounded in the literature going forward, IR collision sensors deliberately out of scope until mapping/SLAM is solid.

## 17.4 8 Aug 2026: LiDAR placement trial completed — Position 2 selected

Executed at the robot (new session, branch `claude/lidar-placement-trial-qzqghe`, per §17.3's plan). Three mount positions, each run via the **Map** button (§16.13) so every run got an automated `report.json` + `.pgm` (§16.14) with no manual analysis step. Files were relayed off the Pi by `cat`-ing the JSON directly into chat and uploading the `.csv`/`.pgm`/`.yaml` — this session had no direct SSH/filesystem access to the robot. The `.pgm`s were decoded and rendered as viewable PNGs with a small stdlib-only script (no `numpy`/`PIL` preinstalled in this session's environment; `pillow-heif` was pip-installed separately to view the mount photos, which arrived as `.HEIC`).

**Results:**

| Metric | Position 1 (baseline) | Position 2 (on battery) | Position 3 (elevated) |
|---|---|---|---|
| Description | Front of battery, current height — battery blocks LOS | On top of battery — battery clear, rear-stack wedge remains | Front of battery, elevated on a temporary box |
| `unknownPct` | 85.57% | **85.01%** | 85.70% |
| `freePct` / `occupiedPct` | 12.61% / 1.82% | 13.01% / 1.98% | 12.36% / 1.94% |
| Duration | 275.7 s | 254.6 s | 266.8 s |
| Grid extent | 96.0 m² | 82.9 m² | 95.5 m² |
| Max commanded \|ω\| (FR) | 1.385 rad/s | 2.207 rad/s | 1.385 rad/s (identical to Pos. 1) |
| Findings | Sparse coverage (warn) | Sparse coverage (warn) | Sparse coverage (warn) |

Position 2's run was faster and less controlled than intended (mean commanded velocity ~77× Position 1's, ~8% shorter duration, ~10% less area explored) — self-flagged by the user before analysis. Position 3's run, by contrast, was the cleanest comparison in the trial: its max commanded velocity matches Position 1's exactly and its duration/extent are both close, making it the one genuinely controlled pair.

**That controlled pair is the key finding, and it's a negative result:** Position 3 showed no improvement over baseline (85.70% vs 85.57%, within run-to-run noise) despite eliminating the battery from consideration by height. The mount photos explain why — the LiDAR on its temporary box sat only roughly level with the battery's top edge, not clearly above it, so the occlusion was likely still partially present rather than removed. "Elevate the mount" as a strategy wasn't falsified by this trial; this *specific amount* of elevation was insufficient.

**Decision: Position 2 (on top of the battery) selected**, on two grounds together, not the number alone: it has the best `unknownPct` despite a handicapped run (less time, less area covered — both of which should have hurt the number, not helped it), and — unlike Position 3 — it removes the battery from the LiDAR's line of sight by mechanism (physically off of it) rather than by degree (a few centimeters of clearance that may or may not be enough). A clean redo matched to Positions 1/3's motion profile would tighten the confidence interval but was deferred by the user as non-blocking (logged in B.6).

Mount photos (all three positions, plus the same two floor reference marks visible in every top-down shot, confirming a consistent driven path across runs) cross-check the reported mechanical deltas: Position 2 is **+7.5 cm height, ~20 cm rearward** of Position 1. The height figure matches the battery's own spec label (SuperMexx SMI2830SL, `165×133×75mm`) almost exactly, i.e. "on top of the battery" is literally one battery-height higher, not a rough estimate.

**`aislebot.urdf` updated** to match: `laser_joint`'s origin moved from the pre-trial estimate `(0.35, 0, 0.20)` to `(0.15, 0, 0.275)` — the reported deltas applied to that prior estimate, not an independent measurement. Flagged in the URDF comment for future refinement. Separately, `ydlidar_ros2_driver`'s own launch file publishes this same static transform independently of the URDF (§13.6) — this update fixes what `robot_state_publisher`/RViz/Foxglove read, not necessarily whatever that external package's launch file still hardcodes; carried into B.6 as an open item.

## 17.5 8 Aug 2026: visualization — Foxglove Bridge added; a correction to §2.3's odometry-prior premise

Moving to the phase's stated order (visualization → SLAM → autonomous drive). §13.8 already scoped the right approach and left it undone: RViz running directly on a laptop can't see this robot's topics (DDS multicast doesn't cross college WiFi, and a differently-configured RMW wouldn't discover them anyway), so the headless-friendly route is `foxglove_bridge` — a websocket on the Pi that Foxglove Studio connects to over plain TCP.

**Added:** `ros-jazzy-foxglove-bridge` to `install.sh`'s package list, and a `foxglove_bridge` node to `aislebot_full.launch.py` (port 8765, on by default via a new `use_foxglove` launch arg) — part of the always-on stack, not just mapping runs, so live visualization is available for teleop/drive too. Connection instructions added to `Important_Commands.md` §6. **Not yet verified on hardware** — this session has no direct path to the Pi; next time bringup is touched: deploy the two changed files (`Important_Commands.md` §2's curl pattern), restart `aislebot.service`, and confirm both `ros2 node list | grep foxglove` and an actual Foxglove Studio connection from a laptop.

**A correction to `SLAM_Theory.md` §2.3, found while scoping the follow-up SLAM benchmark it recommends.** §2.3 frames the next step as "benchmark `slam_toolbox` with odometry-as-prior enabled against the current no-odometry config (`slam_nodom.yaml`)" — implying two configs to compare. Checking the actual deployed files shows that's not quite right: `slam_nodom.yaml` already sets `odom_frame: odom`, and `mapping_full.launch.py`'s own header comment states it *requires* `odom→base_link` TF already being published — which comes from `odometry_publisher`, a node in `aislebot_full.launch.py` that runs continuously as part of `aislebot.service`, not something toggled per mapping session. In other words: since §16.9's odom-TF fix, `slam_toolbox` has already had a live, reliable odometry prior available in *every* mapping run, including all three placement-trial runs above — "no-odom" is a filename left over from when the TF genuinely was unreliable (§16.9–§16.10), not a currently-accurate description of what's running.

**Revised experimental design for the actual benchmark:** there's no second YAML to write. The real comparison is *current setup as-is* (already benefiting from the live odom prior, no change needed) against a genuine no-prior control — `odometry_publisher` deliberately stopped before a mapping run, so `slam_toolbox` gets no TF and degrades to true scan-matching-only (the Hector-SLAM-like behavior the filename originally described). That control run is worth doing **after** Foxglove Bridge is confirmed working, since the expected effect (drift/misalignment under no prior) is something to watch directly in a live map view, not just infer from `unknownPct` — a coverage metric that doesn't distinguish "well-aligned but small" from "large but drifting." Queued as the next concrete SLAM-phase task once visualization is confirmed on hardware.

**Confirmed on hardware, same session.** Deployed (`ros-jazzy-foxglove-bridge` installed, updated launch file curled over, rebuilt, `aislebot.service` restarted — needed a network switch to eduroam first, since the AP has no internet uplink for `apt`/`curl`). `ros2 node list` and `ss -tlnp` both confirmed `foxglove_bridge` listening on 8765. Foxglove Studio connected from a laptop via `ws://aritra-desktop.local:8765` and, after swapping out an accidentally-loaded demo layout ("example-002-drone," meant for Foxglove's own sample dataset — wrong `Display frame` and drone-instrument panels, not a real problem) for a blank one, a live **Map** run showed `/map` building in real time (gray/white/black occupancy cells) with the `/slam_toolbox/graph_visualization` pose graph (nodes + edges) rendering alongside it. Visualization item closed — first time this project has watched SLAM build a map live rather than only inspecting the saved result.

## 17.6 8 Aug 2026: autonomy phase scoped — `Navigation_Theory.md`, and four real bugs found in the existing Nav2 config

Opening the autonomous-drive phase. Same discipline as §17.1: literature first, then parameters. Added **`docs/Navigation_Theory.md`** (costmaps/inflation math, global planning, local control, self-occlusion as a *navigation* problem) and six papers to `research_articles/` — Nav2 itself (Macenski et al., 2020), the layered-costmap architecture `nav2_costmap_2d` implements (Lu, Hershberger & Smart, 2014), DWA (Fox, Burgard & Thrun, 1997) plus a paper diagnosing its narrow-aisle-relevant limitations (Li, Liu & Liu, 2017), and the two MPPI papers (Williams et al., 2016, 2018). All verified via Scite, none retracted.

**A question worth recording, because the answer reframes the task.** The user proposed a physical occlusion-calibration experiment: stand opaque sheets around the chassis perimeter (6 cm clearance, ~112 × 48 cm), map that, then remove them — so the recorded black rectangle defines "the chassis," and everything scanned afterwards is by construction beyond it. Good instinct, wrong mechanism, for two separate reasons:

- **The footprint is a declared parameter, not a measured quantity.** `nav2_costmap_2d` takes the robot's outline as a polygon in `base_link` and collision-checks against it directly. Nothing about that is discovered by scanning; the LiDAR cannot measure the robot it is bolted to. The experiment would produce a picture of a rectangle that the config already has to state numerically anyway.
- **Nav2 already publishes exactly the visual the experiment was meant to produce**, on `local_costmap/published_footprint` / `global_costmap/published_footprint` — the true footprint polygon, live, moving with the robot, displayable in Foxglove. Correct by construction, no props, and it updates if the parameter changes.

**What *does* need an experiment is self-occlusion, and the sheets are the wrong tool for it too** — sheets all round block everything, so they cannot separate "occluded by my own hardware" from "occluded by the sheet." The clean discriminator needs no props at all: rotate in place in a static environment and compare scans, because **real features move in the laser frame under rotation and self-occlusion does not**. `Navigation_Theory.md` §4 also records *why* this matters more than it first appears: if the rear stack sits beyond the LiDAR's 0.12 m minimum range it returns a valid hit every scan, which the obstacle layer marks as occupied — a permanent phantom obstacle fixed in the robot frame, inflated by the inflation layer, that the planner reads as "this direction is blocked, always." The fix is masking those sectors as *invalid* (neither marking nor clearing) in `scan_relay.py`, which is already in the scan path.

**Four bugs found in `src/mecanum_navigation/config/nav2_params.yaml`** while grounding the above — none previously exercised, since Nav2 has never been run on this robot:

1. **Footprint smaller than the robot.** Was `0.90 × 0.40 m`; the URDF chassis is `1.0 × 0.50 m`. The planner was being told the robot is 10 cm shorter and 10 cm narrower than it is — a collision bug, not a conservative approximation. Set to `1.12 × 0.62 m` (URDF chassis + the user's 6 cm margin) and flagged prominently as **needing a tape measure before the first autonomous run**. Note the open discrepancy: the user measured 48 cm total width against the 62 cm implied here, most likely chassis-body width (50 cm, what the URDF models) versus wheel-span width (~37.5 cm from the wheel joint origins). Unresolved from here — it needs the physical robot, and the footprint must enclose whichever is widest.
2. **The QoS trap, again, in a new consumer.** Both costmaps' obstacle layers subscribed to `/scan` — published *best-effort* by the ydlidar driver, while the costmap subscribes reliable by default. This is precisely the incompatibility that made `slam_toolbox` hang forever on "Waiting for laser_scans" (§13.4), which cost a full debugging session to root-cause the first time. Repointed both to `/scan_reliable`. Worth noting as a recurrence pattern: the relay exists, is documented, and *still* got missed by a config written for a different consumer.
3. **`allow_unknown: false`** on the planner — would have made the robot essentially unable to plan anywhere while SLAM is still building the map, since those maps run ~85% unknown (§17.4). Set `true`; safety comes from the local costmap and footprint check, not from refusing to enter unmapped space.
4. **`odom_topic: /odometry/filtered`** on `bt_navigator` — the `robot_localization` EKF output, and that node is Phase 2 work that has never run. Repointed to `/wheel_odom`, what `odometry_publisher` actually publishes.

Also corrected `raytrace_max_range`/`obstacle_max_range` (12.0/10.0 → 9.0/8.0): the 12 m figure exceeded the YDLIDAR X4 Pro's own 10 m maximum, inherited from the originally-planned RPLiDAR A1 and never revised. Kept under 10 m deliberately, since the rated range assumes 80% reflectivity and real warehouse surfaces are darker. The same stale 12.0 is still in `system/slam_nodom.yaml`'s `max_laser_range` — left alone for now rather than changed blind, since that file is live on the robot and mid-phase config churn is how §16.7's drift problems started; queued in B.6 instead.

**Controller decision, made on evidence rather than aesthetics:** `SLAM_Theory.md`-era notes and §13.7 both name MPPI as the eventual controller, and it *is* the better fit for genuine omnidirectionality — it samples the continuous $(v_x, v_y, \omega)$ space rather than DWB's coarse `vy_samples` discretization. But Williams et al.'s own experiments run MPPI on a GPU, and this is a Pi 5 with none — the same constraint that ruled out RBPF-SLAM in `SLAM_Theory.md` §5. Nav2's MPPI is CPU-vectorized, so this is a measurement question, not a settled one. **Starting with DWB** (already configured, far lighter, sufficient to prove the autonomy chain end-to-end), instrumenting CPU, and treating MPPI as a measured upgrade — a change confined to one config block, not an architectural commitment.

## 17.7 8 Aug 2026: footprint measured — the URDF chassis box was wrong, the kinematics were not

Resolves §17.6's blocking open item. Tape measurement at the robot: **36 cm wide** (wheel outer to wheel outer, the widest part) **× 100 cm long**. With the 6 cm all-round clearance margin, the Nav2 footprint is **1.12 × 0.48 m**.

**This overturns the caution raised in §17.6, and the correction is worth recording precisely because the reasoning failed in an instructive way.** §17.6 flagged the user's proposed 0.48 m width as potentially unsafe on the grounds that `aislebot.urdf` models the chassis as 0.50 m wide — a footprint narrower than the robot being a collision bug. The measurement shows the URDF was the unreliable source, not the hand measurement. The lesson is not "trust the tape over the model" in general; it's that the model contained two independent width statements and only one of them was checked. The chassis `<box size="1.0 0.50 0.15">` was wrong. The **wheel joint origins** (`±0.15769` m, plus `0.03` m half-wheel-width → `0.375` m outer) agree with the tape to within a centimetre and were right all along. Those joint origins — not the chassis box — are what the inverse kinematics and odometry actually consume (Part XII), so **nothing in the control or odometry path was ever affected by this error**; it was confined to the visual/collision box, which until now nothing on the real robot read.

Corrected:
- `nav2_params.yaml` — both costmaps' footprints to `x = ±0.56, y = ±0.24`; inflation comment updated for the new inscribed radius (0.24 m).
- `aislebot.urdf` — chassis box `0.50 → 0.36` m wide, with the derivation and the wheel-origin cross-check recorded inline. The header comment's "1000mm × 500mm × 200mm" was doubly wrong: the width as above, and the 200 mm height never matched the model's own 150 mm box. Height left at the model's 150 mm rather than guessed.
- Chassis **inertia deliberately left stale** — it was computed for the 0.50 m box. It affects Gazebo simulation dynamics only, nothing on the real robot, and substituting an un-derived replacement would trade a known-stale value for an unknown-wrong one. Flagged for proper recomputation if the simulation is ever used quantitatively.

## 17.8 11 Aug 2026: self-occlusion measured directly — a wide blind sector, not a thin wedge

New session, same branch (`claude/lidar-placement-trial-qzqghe` — §17.3's plan to start a fresh branch for this phase was superseded; the placement-trial branch stayed open and absorbed the whole autonomy-scoping arc through this point). Picking up `Navigation_Theory.md` §4's identified need: which angular sectors does the robot's own rear mast occlude, and by how much.

Method: a single opaque reference block at a known bearing, robot rotated in place, watched live in Foxglove (Fixed/Display frame `base_link`, 0.5 m grid) rather than inferred from `.pgm` coverage stats — the direct approach the visualization phase (§17.5) was built to enable. Two passes were run, documented in `docs/robot_photos/`: an initial pass (`2026-08-11_occlusion_trial_cw/`) and a cleaner re-run with the display properly configured (`2026-08-11_recalibration_cw/`, four pairs of physical-robot-photo + marked-map-screenshot: the block's disappearance heading, its reappearance heading, and the 90°/180°/270°/360° stops in between).

**Result: the blind sector is roughly a third of the full 360° sweep**, not the thin wedge assumed since the LiDAR placement trial (§17.4). This directly explains why all three mount positions in that trial produced maps around ~85% unknown regardless of battery occlusion — roughly a third of every scan was dead on arrival, a bigger effect than which side the battery blocked. Both trials' full rotations closed cleanly (start/end headings matched, both in the map data and in the physical-robot photos independently) — odometry and scan-matching handle in-place rotation correctly; the blind sector is a sensing gap, not a localization one.

**These bearing numbers turned out to need a caveat, discovered while pursuing the mount-offset question in parallel** — see §17.9. Flagged there and in B.6 rather than reopened here, since re-deriving them is now mechanical (repeat the same block-placement method against the corrected `/scan_reliable`).

## 17.9 11 Aug 2026: LiDAR scan found mirrored — diagnosed and fixed in `scan_relay.py`

While running §17.8's trial, a block placed in front of the robot was appearing *behind* it in the map. The live `base_link -> laser_frame` transform was checked and found to be an unset placeholder (`(0, 0, 0.02)`, zero rotation) rather than Position 2's real mount offset — but a translation error cannot swap front and back, so this was a real, separate fault, not an artifact of that known TF gap.

**Measured, not guessed**, with a single block at three bearings, defined empirically by how the robot actually drives (`W` -> `+Y`, `D` -> `+X`, confirmed by a side-by-side video of the robot driving toward a block while its map position closed in step) rather than assumed from the ROS/REP-103 convention that forward is `+X`. That distinction mattered directly: a first derivation assuming REP-103 produced a 180° offset that is 90° away from every one of the three measured points, and was caught before deployment.

| Block truly at | Expected | Reported |
|---|---:|---:|
| Right | 0° | 270° |
| Front | 90° | 180° |
| Left | 180° | 90° |

All three solve `reported = 270° - true`. This is a **reflection**, not a rotation — `reported - true` is not constant across the three (270°, 90°, 270°), while `reported + true` is (270° every time), which is the signature of a fixed mirror line rather than a turn. That distinction decided where the fix could live: `tf2` composes rigid motions (rotations and translations) only, and a reflection inverts handedness — no static transform, at any angle, equals a mirror. The correction has to re-index the scan data itself.

**Fixed in `src/scan_relay/scan_relay.py`** — already the node bridging `/scan` to `/scan_reliable` for QoS reasons (§13.4), now also applying `mirror=True, yaw_offset=270°` via a cached index-remap (built once per scan geometry, reused every message). Verified algebraically against all three measured points plus a fourth untested heading, then re-verified through the actual runtime remapping function rather than the point algebra alone. Deployed; confirmed by the user against a live map immediately afterward.

Full derivation, the ruled-out 180° hypothesis, and the code: `docs/LiDAR_Orientation_Calibration.md`. Photographic evidence: `docs/robot_photos/2026-08-11_orientation_fix/` (block-placement photos, forward-drive confirmation video).

**Open items carried to B.6:** §17.8's blind-sector bearings were measured in the pre-fix, mirrored frame and need re-measuring against corrected `/scan_reliable` before they're used for anything (e.g. a scan mask); the `base_link -> laser_frame` *translation* is a separate, still-open bug from the one fixed here.

## 17.10 11 Aug 2026: the map-drift symptom — real fix landed in odometry, not the LiDAR

Immediately after §17.9's fix, driving the robot forward made the accumulated `/map` shift **sideways** relative to the robot rather than backward, as a correctly-tracked forward move should look. Checked against raw odometry rather than a screenshot — `ros2 run tf2_ros tf2_echo odom base_link`, logged before and after two controlled, single-axis, physically-confirmed moves:

| Move | dX | dY | Reads as |
|---|---:|---:|---|
| Forward only (`W`) | +0.257 m | +0.015 m | 94% of motion in X |
| Strafe right only (`D`) | +0.011 m | −0.287 m | 96% of motion in Y |

That's standard REP-103 (`base_link`'s real `+X` is forward) — the opposite of the `W`/`D` convention §17.9's fix was built on. Re-solving §17.9's original three block measurements with forward correctly assigned to `+X` reproduces the very first, earlier-discarded hypothesis exactly: `yaw_offset=180°`, not 270°.

**That correction to `scan_relay.py` was implemented, verified through the runtime remapping function, and then reverted at the user's explicit instruction** — and the reasoning for the revert is the actual point of this entry, not a footnote. `yaw_offset=270°` already had a *stronger* independent confirmation than the odometry check that seemed to contradict it: a video of the robot physically driving toward a placed block while its position in the map closed in step (`docs/robot_photos/2026-08-11_orientation_fix/forward_drive_confirmation.mp4`), recorded *before* the map-drift symptom was ever noticed. The map-drift and the LiDAR calibration are two observations of the same underlying axis mismatch, but nothing about physics says the LiDAR is the side that has to move — `base_link`'s own axes, as defined by `odometry_publisher.py`, are just as arbitrary a choice as the LiDAR's scan indexing. Two consistent conventions existed; the question was which one had weaker evidence behind it, and that was odometry, not the LiDAR.

**Fix: `odometry_publisher.py` now publishes its orientation rotated by a constant −90° from what it internally computes**, rather than changing `scan_relay.py` at all. The internal kinematics (`vx`/`vy`/`theta` integration, standard REP-103) are untouched and remain correct; only the *published* quaternion and the *published* twist (`linear.x`/`linear.y`) carry the constant offset. Position (`self.x`, `self.y`) is unaffected — relabelling which way a frame's local axes point doesn't move its origin. Verified algebraically at an arbitrary heading (37°, not just the near-zero heading actually measured on hardware) before deploying: a real obstacle directly ahead reads at the LiDAR's validated `+90°` regardless of the robot's true orientation.

**Why a constant rotation of the published orientation, specifically, and not a mid-computation swap of which wheel-formula is called `vx` vs `vy`:** TF's rotation and "which direction a frame's own `+X` points" are the same fact by definition — a rotation of angle θ is exactly what makes local `+X` point in world-direction θ. Relabelling `vx`/`vy` inside the kinematics would also require re-deriving how `theta` accumulates and how position integrates, multiplying the chances of a subtle error for no benefit. One constant offset applied at the point of publication, downstream of otherwise-unchanged correct integration, is the version that's provably right at every heading rather than just the one tested.

**Consequence, handled rather than left as a landmine:** this makes `base_link` non-standard — `+X` is "right," `+Y` is "forward," the reverse of REP-103. Every x/y-labelled parameter in `nav2_params.yaml` (§17.6–§17.7) assumed the standard convention and needed swapping to match: the footprint rectangle (width now on `x`, length on `y`), DWB's velocity limits (`min/max_vel_x` now the strafe limit, `min/max_vel_y` now forward/reverse), and `vx_samples`/`vy_samples` (swapped 5/10 to keep finer sampling on whichever axis is actually forward, not whichever axis is *called* `x`). A prominent AXES note added at the top of the file so this isn't rediscovered by surprise later.

**Left unaddressed, flagged rather than fixed now:** `aislebot.urdf`'s chassis geometry (long axis modelled along `X`) is now inconsistent with the live TF's real meaning. Harmless today — nothing on the real robot publishes `/robot_description` yet (§17.6's B.6 item) — but a real landmine for whenever `robot_state_publisher` is added; the visualized chassis would render rotated 90° from the real robot until this is corrected too.

**The general lesson, distinct from and complementary to §17.9's:** when two independently-measured subsystems disagree about a shared convention, the fix doesn't automatically belong to whichever one was measured second, or whichever one is more convenient to change. It belongs to whichever one has the *weaker* existing confirmation. Here that was odometry's single raw-TF check against the LiDAR's driving-and-watching video, recorded earlier and for an unrelated reason. Revisiting a confirmed-good result under new pressure is sometimes right and sometimes a mistake; the way to tell the difference is comparing the strength of evidence on each side, not just which one is currently in question.

**New B.6 item:** update `aislebot.urdf`'s chassis and footprint geometry to match the new axis convention before `robot_state_publisher` is ever added.

## 17.11 11 Aug 2026: fix confirmed on hardware — session and branch close-out

**Recap, in one place, of what the actual bug was and what fixed it** (the user asked for this spelled out plainly rather than only left spread across §17.9–§17.10): after §17.9's LiDAR mirror fix, driving the robot forward made the accumulated map slide sideways on screen instead of shrinking away behind the robot the way a correctly-tracked forward move should look. The underlying cause was that two subsystems — the LiDAR's scan indexing (`scan_relay.py`) and the wheel odometry's published orientation (`odometry_publisher.py`) — each encoded a *different, self-consistent* answer to "which way does this robot's `+X`/`+Y` actually point," and nothing about physics picks one of two internally-consistent conventions as *the* correct one. The LiDAR side (`yaw_offset=270°`) had already been confirmed by a video of the robot driving toward a placed block with the map tracking correctly, recorded before the drift symptom ever appeared — stronger evidence than odometry's single raw `tf2_echo` check, which is why the fix went into `odometry_publisher.py` (a constant −90° rotation of the *published* orientation and twist only) instead of reopening the LiDAR file. Detail and the measurement tables are in §17.10; this entry is the confirmation and close-out.

**Deployment hit two real infrastructure snags, not fixed by retrying the same thing harder:**
- `curl`-based deploy failed first with `curl: (23) Failure writing output to destination` (the assumed workspace path `~/aislebot_ws` didn't exist — the actual path, found via `find`, is `~/ros2_ws`), then with a TLS handshake error (`OpenSSL: wrong version number`) after switching to eduroam — consistent with the eduroam-reachability risk already flagged in B.6 and never fully resolved this session.
- Rather than keep fighting the network, switched to `scp` run from the user's own Windows PC straight to the Pi (`scp odometry_publisher.py aritra@aritra-desktop.local:~/ros2_ws/...`). This only needs the PC and the Pi to be on the same LAN — which eduroam already was, confirmed by the SSH session being reachable — not any GitHub/WAN path from the Pi at all. Both files copied in under a second; `colcon build --packages-select mecanum_robot mecanum_navigation` picked them up cleanly (2 packages, ~4s, no errors); `sudo systemctl restart aislebot.service` brought the stack back with the odometry node running the new code.

**Confirmed working on hardware:** driving forward with Foxglove's 3D panel set to **Fixed frame = `base_link`, Display frame = `base_link`** (holds the robot stationary at screen-center so the map's own motion is what's visible — the same diagnostic setup that originally exposed the sideways-drift symptom) now shows the map sliding away behind the robot as the robot advances into it, not sideways. Confirmed live by the user: "perfect, absolutely perfect... its moving and going the way I want it to be." Screenshot reviewed showed a clean hallway-shaped occupancy grid (black walls, red `/scan_reliable` points hugging them, grey unknown space) with the robot's TF axes centered — the qualitative signature of correct tracking, not the earlier sideways smear.

**One residual item, explicitly minor and explicitly deferred:** the user noted the map still comes in with a small LiDAR yaw misalignment — "just we will twitch the lidar yaw angle a bit" — distinct from the reflection bug §17.9 fixed (that was a ~constant 90°-scale reflection with a wrong axis assumption; this is a small residual rotational offset on top of an already-correct, already-reflection-fixed scan). Not blocking, not touched this session, explicitly scheduled for later fine-tuning against `scan_relay.py`'s `yaw_offset_deg` — added to B.6 below.

**Foxglove reference, consolidated:** connection steps, why the websocket bridge is used instead of RViz2 (DDS multicast doesn't cross this network; Foxglove's plain-TCP bridge does), and the IP/port to connect to are in `Important_Commands.md` §6 — updated this session to also record the exact 3D-panel frame settings (`Fixed frame` / `Display frame` = `base_link`) used to visually diagnose and then confirm this fix, since that specific setting (rather than the `map` frame default) is what makes odometry drift visible at all.

**Branch close-out:** this branch (`claude/lidar-placement-trial-qzqghe`) covered §17.2 through here — the LiDAR placement trial, Foxglove visualization bringup, the autonomy/Nav2 config literature-and-bugfix pass, the footprint tape-measurement, the self-occlusion measurement, the LiDAR mirror-reflection bug, and this odometry map-drift bug, including one fix that was implemented, found to violate the user's explicit constraint, and cleanly reverted rather than left half-applied. Everything on it is merged onto `main` (verified byte-identical after every push, same discipline as §17.3). Safe to delete. The next phase — actual mapping/SLAM runs and then autonomous drive testing — starts in a new session on a new branch, per the original two-week plan (§17.1).

## 17.12 12 Aug 2026: workspace hygiene, a physical zero-position convention, and the footprint confirmed correct by direct measurement

New session, new branch (`claude/mapping-autonomous-nav-695glw`, the old branch deleted post-merge per §17.11's plan). Explicit session goal from the user: stop calibrating, start actually mapping and driving autonomously — this and the following two sections cover a single continuous session on 12 Aug 2026. Opened by re-reading Part XVII in full and cross-checking `scan_relay.py`/`odometry_publisher.py` against what it documents as confirmed — both matched exactly, no drift between docs and deployed code.

**Pi/workspace cleanup, done before touching the robot, at the user's request.** Audited via `du`/`df`/`journalctl --disk-usage` (58% of 29 G used, 12 G free — healthy, nothing urgent). All pre-existing saved maps — 66 `run_*` files in `~/aislebot_logs/` from the placement/self-occlusion trials plus 4 more loose top-level files (`aislebot_map_2.*`, `aislebot_first_map.*`) the first audit pass missed — predate the §17.9/§17.10 fixes and are in the wrong frame regardless of age, so archived rather than deleted outright: `~/aislebot_logs/archive_pre_fix/` (72 files landed there in the end, ~6 more than the original count — a quick Foxglove-connectivity check earlier in the session turned out to have gone through the dashboard's Map button and produced a few more short trial runs than expected; harmless, all still pre-real-mapping data). Hard-delete deferred until real post-fix map data exists to replace it with. journald vacuumed (`--vacuum-time=7d`, freed 84.1 M), `apt clean` run (449 M reclaimed), three stale `.bak` files from 5 Aug targeted for removal (found already gone by the time the command ran — user had evidently cleared them separately). `~/ros2_ws/maps/` created as a stable, nameable home for the map this phase is actually working toward, replacing the ad-hoc `~/aislebot_logs/run_<timestamp>.*` convention that trial runs used.

**A physical "zero position" convention established, and grounded in the actual mechanism rather than taken on faith.** The user's proposal: a green tape mark on the robot aligned with a matching mark on the floor, used as the fixed start pose for every mapping (and later, navigation) run. Confirmed this is correct for two concrete reasons rather than just "seems tidy": (1) `slam_toolbox` sets a fresh mapping session's `map` frame origin to wherever `base_link` is at the first scan — not tied to raw odometry's own boot-time origin — so a consistent physical start pose gives every map the same real-world origin by construction; (2) `nav2_params.yaml`'s AMCL block hardcodes `initial_pose: {x:0, y:0, z:0, yaw:0}`, which is only correct if the robot starts navigation runs from that same map-origin spot. Verified live in Foxglove (`Fixed`/`Display frame = map`) rather than only asserted: at the start of a fresh mapping run, `base_link`'s TF marker sat visibly at the convergence point of the radiating first-scan rays — i.e. at the map's own local origin, as predicted.

**Footprint/LiDAR-offset geometry resolved by direct measurement — B.6's "chassis-occlusion + danger-cushion validation" item, carried in since §17.9.** Rather than continuing to assume the footprint is symmetric around `base_link`, the user measured directly:

- LiDAR's true center (a marked point on the housing, distinct from the robot's own centre) sits **0.23 m in from the front edge** and **0.12 m in from the side edge**, the latter against the bare chassis *plate* width (0.25 m) — deliberately kept separate from the 0.36 m wheel-outer-to-wheel-outer width the Nav2 footprint uses, a different reference frame for a different purpose.
- `base_link`'s own kinematic origin — the point the wheel math actually pivots the chassis around — was located physically by watching the robot do a pure in-place rotation and marking the one point that stayed fixed while everything else swung around it (the same no-props logic already validated for self-occlusion, §17.8). Measured: **0.5 m from the front edge** (exactly half of the 1.0 m tape-measured length) and **0.125 m from the chassis-plate edge** (exactly half of 0.25 m) — `base_link` sits at the true geometric center of the chassis in both directions, confirmed rather than assumed.

**Consequence: the existing symmetric Nav2 footprint (`±0.56 m` length, `±0.24 m` width, `nav2_params.yaml`) is correct as measured — no config change needed.** The asymmetric wheel kinematics (`l1=0.403` vs `l2=0.333`) turn out not to drag the chassis body's centre off of `base_link`; the wheel geometry cancels out exactly. Derived from the same measurements: the LiDAR sits at **`Y = +0.27 m`** forward of `base_link` (front-edge distance to `base_link`, 0.5 m, minus front-edge distance to the LiDAR, 0.23 m) and **`X ≈ 0`** (within ~0.5 cm of the centerline, noise-level). **Deliberately not written into `aislebot.urdf` this session** — the file still models the whole chassis in the *old* axis convention (chassis `<box>`, all four wheel joints, and `laser_joint` all still assume `+X` = forward), so updating just the LiDAR's number would leave the file internally inconsistent rather than more correct. The real, measured numbers are recorded here so the still-open B.6 item ("swap `aislebot.urdf`'s whole axis convention before `robot_state_publisher` is ever added," §17.10) has real data waiting for it rather than the old, admittedly-rough §17.4 estimate.

## 17.13 12 Aug 2026: first real mapping trials from zero — the traversal pattern, not a code bug, explains the wall gaps

With the zero mark established, ran the first real (not scripted-trial) SLAM mapping sessions. First check: a full in-place rotation from the mark, `Fixed`/`Display frame` cycled between `map` and `base_link` in Foxglove — orientation and axes confirmed correct, matching every prior confirmation this session and last. The resulting map's shape — open sightlines radiating in roughly four directions from the start point — was checked against the physical space rather than assumed correct or wrong from the screenshot alone: the user confirmed the zero mark genuinely sits at a real corridor/aisle junction, so the cross shape is real structure, not an artifact.

**Two map-quality problems found on review, both real and both worth restarting for — not calibration nitpicks.** (1) A wall the user knows is physically solid and continuous showed a visible break in the occupancy grid. (2) Real open space the user drove through was showing up as false-occupied (black) cells. Diagnosed, not just patched over:

- The wall-gap is most likely plain under-coverage — a wall segment seen only briefly, at a shallow angle, from a single vantage point, never accumulating enough log-odds evidence along its full length to solidify. Consistent with every prior trial's "sparse coverage" finding (§17.4 onward).
- The false-occupied-in-open-space symptom raised a sharper, previously-identified hypothesis: `Navigation_Theory.md` §4 flagged, before any real driving ever happened, that the robot's own rear mast would return a valid LiDAR hit every scan if within range — a phantom obstacle fixed to the *robot's* frame, not the room's — and that the fix (masking that sector as invalid in `scan_relay.py`) was measured (§17.8) but never actually implemented. If that mechanism is live, the false black would track wherever the robot itself was standing at the time, not a fixed point in the room — flagged as something to specifically check on the next map, not confirmed either way this session.

**Root cause of both, identified from the user's own description of the drive pattern, not inferred:** every leg was "rotate at zero → drive straight out down one aisle → drive straight back to zero → rotate → repeat," for all four aisles. This is exactly what produces the persistent radiating "flower" map shape seen in every screenshot all session (and, in hindsight, in every earlier trial too) — each aisle was only ever viewed head-on, down its own centerline, at a shallow angle to its own side walls, never from a position close enough or angled enough to solidify them. The hub-and-spoke *topology* isn't the problem (it matches a real junction) — driving dead-center down each spoke instead of hugging its walls is. Corrected guidance given for the next pass: hug one side wall going out, the other coming back (within the established 6 cm cushion), minimal full rotations at the hub between legs.

## 17.14 12 Aug 2026: first Nav2 bringup — three latent bugs found and fixed before ever touching hardware

Prompted by the user asking whether the manual driving could be automated. Investigated the real options (frontier exploration vs. Nav2 with the user clicking goals vs. a blind scripted `cmd_vel` replay) and recommended Nav2-with-manual-goals first: frontier exploration runs on top of Nav2 regardless, so proving Nav2 alone first — with a human choosing every destination and able to abort — avoids debugging two new, never-run systems simultaneously on a 45 kg robot with an unmitigated blind sector (§17.8, still unmasked). User agreed.

**Same discipline as §17.6's original four-bug pass: read the never-yet-run config for latent errors before running it, not after.** Found three:

1. **`navigation.launch.py` started `robot_localization`'s EKF unconditionally**, with `ekf_params.yaml`'s `publish_tf: true` and `world_frame: odom` — a second publisher of the exact `odom→base_link` transform `odometry_publisher` already owns, the one carrying the validated constant −90° rotation from §17.10–§17.11. Two publishers of one transform overwrite each other; this would have intermittently corrupted the axis convention two prior sessions spent confirming on hardware. Also fused an IMU that doesn't exist yet (still unpurchased, B.3). **Fix:** EKF node removed from the launch file, restoration conditions documented inline (needs the real IMU *and* `odometry_publisher`'s `publish_tf` turned off in the same change, so exactly one node owns the transform).
2. **`nav2_params.yaml` had no `velocity_smoother` block.** That node is the last stage of the `cmd_vel` chain (`controller_server → /cmd_vel_nav → velocity_smoother → /cmd_vel`) and starts regardless of whether it's configured. Nav2's stock defaults are differential-drive-shaped and zero out the `y` velocity limits — on this robot, where `+Y` is forward (§17.10), that would have silently capped all forward/reverse motion to zero while the planner and controller both appeared to be working normally, the single least debuggable failure mode available. **Fix:** added, limits matched to the existing DWB config and the same swapped-axis convention.
3. **`bt_navigator`'s `plugin_lib_names` listed 13 hand-picked BT node names.** That parameter *replaces* Nav2's full default list rather than extending it; the default behaviour tree references substantially more nodes than those 13, so `bt_navigator` would have failed to load on the very first goal. **Fix:** key removed so the built-in default list applies.

Also flagged, not fixed — inert on this deployment but worth a real fix before it matters: `joy_to_aislebot.py` publishes `/cmd_vel` on every joy message, including idle-gamepad zeros, at `joy_node`'s 25 Hz autorepeat rate — would fight Nav2 for `/cmd_vel` at 20 Hz if a gamepad were ever plugged in. Currently harmless: `start_aislebot.sh` records that no gamepad is attached on this deployment and the phone dashboard is primary control.

**New file: `src/mecanum_navigation/launch/nav2_slam.launch.py`** — Nav2's navigation-only nodes (`nav2_bringup`'s `navigation_launch.py`: planner, controller, smoother, behaviours, `bt_navigator`, waypoint follower, velocity smoother, lifecycle manager), deliberately *not* `bringup_launch.py`, which also starts `map_server` + AMCL and would fight `slam_toolbox` over `map→odom` — the existing `navigation.launch.py` is reserved for the later, separate "navigate on a finished, saved map" mode. Committed and pushed (`f0df15e`).

**Deployed and built.** All four required Nav2 packages confirmed already installed (`ros2 pkg list`) — no `apt install` needed. Deployed via `curl` straight from GitHub raw URLs run *on the Pi* rather than `scp` from the Windows PC — worth noting because §17.11 flagged eduroam→GitHub HTTPS as unreliable (a TLS handshake failure) and this session's plain `curl` returned a clean `HTTP 200` on the first try. Possibly a transient issue back then rather than a persistent one; not re-investigated further, just noted as a discrepancy rather than quietly assumed resolved. `sha256sum` on both ends confirmed byte-identical transfers for all three files. `colcon build --packages-select mecanum_navigation` succeeded cleanly (2.01 s) on the Pi.

**Session paused here, deliberately, at the user's request — not a natural stopping point in the plan, a real one worth recording as such.** State at pause: the Pi is on `aislebot-ap` (switched from eduroam once the GitHub deploy was done), Foxglove reconnected at `ws://10.42.0.1:8765`, and `ps aux` confirms exactly one `mapping_full.launch.py` + one `slam_toolbox` instance running (no §16.8-style duplicate), started 19:21. **Open and unresolved: whether the robot was physically at the zero mark when that 19:21 session started.** Asked twice, never confirmed before the user ended the session. First thing next session: check this before driving further — if unconfirmed or no, stop that run and restart fresh from the mark, since the entire point of this session's zero-position work is a map whose origin is known and reproducible. No real map has been saved yet; Nav2 has not yet been run on hardware even once. Both remain fully open for the next session.

## 17.15 13 Aug 2026: chassis visualization confirmed on hardware, the blind sector finally measured in the corrected frame, and a real network-flakiness episode

Continuation of the same day, after the pause above — the user confirmed the 19:21 session's zero-mark question directly (robot was at the mark) and drove a full rotation plus a deliberate approach to a real wall, which is what most of this section is built on.

**`robot_state_publisher` confirmed working on real hardware.** Foxglove screenshots showed the actual chassis rectangle, wheel bumps, and LiDAR dot rendering at the robot's position — the URDF axis-convention conversion (§17.12) and the vendor-TF-suppression fix (mapping_full.launch.py launching the driver node directly rather than through `ydlidar_launch.py`) both did what they were meant to. Four `wheel_*` links show a benign Foxglove warning (missing `/joint_states` for their `continuous` joints, since nothing publishes it) — cosmetic only, since all four are non-fixed joints that don't affect the chassis, `base_link`, or `laser_frame`, which are what the footprint and self-occlusion work actually depend on.

**A direct wall-approach gave the first end-to-end scale validation of the whole geometry chain, not just a direction check.** Every prior orientation confirmation (§17.9's block bearings, §17.10's odometry check, §17.11's forward-drive video) tested *which way* things point, never *by how much*. The user drove to a wall and tape-measured a ~7 cm gap between the mecanum roller and the wall; Foxglove's rendered gap read 0.06–0.07 m. Agreement to within a centimetre requires the LiDAR range reading, `scan_relay`'s mirror+270° correction, the measured 0.27 m `laser_joint` offset, the 0.36 m chassis width, and `base_link`'s centred placement to *all* be simultaneously correct — the strongest single validation this project has produced. Documented as the motivating case for adding a **visual-only safety-cushion link** to `aislebot.urdf` (`safety_cushion`, `0.48 × 1.12 m`, no `<collision>` so Gazebo cannot mistake it for a physical object) — the same polygon `nav2_params.yaml` already declares as the Nav2 footprint, verified programmatically equal on both costmaps. Explicitly documented inline as a mirror of that config, not a second source of truth for it.

**The self-occlusion blind sector, re-measured in the corrected frame — resolves the B.6 item open since §17.9.** `tools/scan_bearing.py` run at five headings roughly 90° apart across one full rotation at the zero mark. Cross-checking the five sector tables against each other (not reading any one in isolation) found exactly one bearing block returning a nonzero `<1m` reading in *all five* independent headings, at closely matching percentages each run: **`-135°` to `-45°` true bearing — a 90° wedge centred on directly behind the robot.** Every other "always close" flag in any individual run appeared in exactly one run — real walls the robot happened to face at that heading, correctly not persisting, confirming the discriminator worked as intended. The single nearest point across all five scans clustered independently at `-104°` to `-125°` and `0.12–0.13 m` every time — inside the identified block, at the LiDAR's own minimum range. Refines §17.8's pre-fix estimate ("roughly a third of the sweep," ~120°) down to a measured 90°. Written up in `Navigation_Theory.md` §4 as the confirmation of that section's pre-driving prediction. **The mask was implemented same session** (commit `7e4410c`), added to `scan_relay.py` as new parameters (`mask_enabled`, `mask_min_deg`, `mask_max_deg`, defaulting to `True`/`-135.0`/`-45.0`) that blank the arc's beams to `NaN` in the corrected/published frame rather than zero or `inf` — `NaN` is dropped entirely by `laser_geometry`'s projection, so a masked beam neither marks nor clears, the honest representation of a direction the sensor cannot see; a finite value would falsely mark an obstacle, `inf` would falsely clear through whatever real obstacle sits directly behind the masked arc. The mirror/`yaw_offset_deg` calibration is untouched — verified by reading the diff line by line before saying so.

**LCD display repurposed at the user's explicit request** — drive/arm/lift telemetry replaced with a persistent network-status readout (current IP + `AP:8080`/`NET:22` depending on which network), motivated directly by this session's own repeated difficulty finding the Pi's address after a network switch. **Shipped with a real bug, caught immediately on hardware**: the IP lookup opened a UDP socket toward `8.8.8.8` and read back the local address the OS would use to reach it — a trick that requires a route to exist even if unused, which fails outright on the AisleBot-Pi AP, which deliberately has no upstream route at all. The display showed "NO NETWORK" specifically in the one mode it was built to cover. Fixed by reading the IP directly off `wlan0` via `ip -4 -o addr show` instead of inferring it through a connectivity assumption. Logged as a wrong turn rather than smoothed over, per this project's own documentation discipline — caught fast because the user tested on real hardware immediately rather than assuming the first version was correct.

**A real, if survivable, networking episode — worth recording plainly rather than treated as routine.** `eduroam` gave a TLS handshake failure downloading two files after working cleanly minutes earlier for others — confirming intermittent, not fixed, contrary to a hopeful read earlier in this session. Full `nmcli con up eduroam` reconnect attempts then failed to reach the internet at all. Diagnosed as unrelated to signal — a fresh `nmcli device wifi list` scan later in the session showed `eduroam` at full signal strength, so an earlier partial (`grep`-filtered) scan that appeared to show it missing was a red herring, corrected in-thread rather than left standing. Fell back to `IITB-Wireless` (same physical APs, separate SSID/VLAN, already had a saved profile from earlier Pi setup) — connected, but `ssh aritra@aritra-desktop.local`'s mDNS lookup failed outright, most likely stricter client isolation on that VLAN than `eduroam`'s (plausible, not independently confirmed). Resolved pragmatically rather than by fully diagnosing the network: the two pending files were deferred rather than forced through, and the LCD fix above exists specifically so this doesn't cost as much time next time it happens.

**Session state at this point:** `aislebot.urdf` (safety cushion) and `lcd_display.py` (the fix) are committed and pushed but **not yet deployed to the Pi** — both blocked on the next window with real internet, which the AisleBot-Pi AP by design does not provide. Neither blocks continued mapping or driving; both are additive visualization/convenience features on top of an already-working, already-confirmed stack. **Correction to an error in an earlier draft of this same entry**, caught when the user asked for a consolidated download list and a commit ID in `git log` didn't match anything in this session's visible working memory: this section originally stated `scan_relay.py` was untouched this session. That was wrong — `scan_relay.py` *was* modified (the self-occlusion mask, above, commit `7e4410c`), evidently written earlier in this same session before a context summarization point, which is why the record of writing it didn't carry forward into what produced this entry. Caught by checking `git log` against user-visible claims rather than trusting internal recall, and corrected here rather than left standing, which is the whole reason this discipline exists. The mirror/`yaw_offset_deg` calibration values themselves remain exactly as validated in §17.9 and untouched — confirmed by re-reading the actual diff, not re-asserted from memory.

## 17.16 13 Aug 2026: deploy confirmed on hardware, one unresolved artefact, session closed deliberately for a clean handoff

Continuation of the same day. The three pending files (`aislebot.urdf` with the safety cushion, `scan_relay.py` with the self-occlusion mask, `lcd_display.py`'s fix) deployed cleanly once real internet was available again — all three checksums matched byte-for-byte, `colcon build --packages-select mecanum_robot` succeeded, `sudo systemctl restart aislebot.service` came back with all expected nodes and no duplicates (`ros2 node list`: `arm_bridge`, `esp32_bridge`, `foxglove_bridge`, `joy_node`, `joy_to_aislebot`, `lcd_display`, `odometry_publisher`, `phone_dashboard`, `robot_state_publisher`, `teleop_asym`).

**Both hardware fixes confirmed working, on the actual failure mode each was built for, not just a happy path.** The LCD read `10.42.0.1` / `AP :8080` immediately after restart — confirmed in the exact mode (`aislebot-ap`, no upstream route) that broke the first version. Separately, a physical approach to a real wall/door-frame — photographed for the record — showed the rendered amber safety-cushion boundary and the red `/scan_reliable` points aligning correctly at the wall edge, a second independent confirmation of the geometry chain beyond §17.15's tape-measured gap.

**One artefact found, deliberately left unresolved rather than guessed at.** A cluster of black (occupied) cells appeared in the map circled by the user, positioned close to or under the robot's own rendered footprint at the time — visually resembling either a small real object or a recurrence of the self-occlusion phantom the same-session mask was just built to remove. Diagnosis was narrowed but not completed before the session ended:

- **Ruled out:** a duplicate `scan_relay.py` process (the specific §16.8-class failure mode). `ps aux` showed exactly one instance, started at a time consistent with the fresh post-redeploy mapping session, not a stale pre-redeploy leftover.
- **Not yet done:** the definitive test — driving away from that spot and checking whether the cluster stays fixed in the room (real object) or follows/reappears near the robot's new position (still-phantom, meaning the mask's `-135°`/`-45°` bounds need widening or a second occlusion source exists). Also unanswered: whether a block was physically placed there at all, and the cluster's bearing relative to the robot at the time (near the masked rear arc, or somewhere the mask wouldn't touch).

**Session closed here, deliberately, at the user's explicit request — a new session on this same branch, specifically to start the autonomous-drive phase without carrying forward a growing context history.** Direct motivation: this session's own §17.15 correction, where an earlier commit (`7e4410c`, the self-occlusion mask itself) fell out of working memory across a context-length summarization point and was briefly, incorrectly described as not yet done. Caught and fixed the same session by checking `git log` against what was being claimed rather than trusting recall — but the user's own read of that episode, choosing a clean restart over pushing further into a long conversation, is the more reliable fix and is recorded here as the reasoning, not just the instruction.

**Handoff plan for the new session, so it does not need to re-derive any of this:**
1. **Resolve the block/phantom question first**, before trusting the map for anything else — stop the current mapping run, confirm the robot is at the zero mark, press **Map** fresh. Cleaner than chasing the ambiguity in-place.
2. **First-ever Nav2 hardware launch**: `ros2 launch mecanum_navigation nav2_slam.launch.py` (SLAM mode — no AMCL, not `navigation.launch.py`). Confirm lifecycle nodes report `active` via `ros2 lifecycle list /controller_server`, not just that the process didn't crash.
3. **First autonomous goal**: short and close, given this is genuinely untested on hardware — `1.5 m` forward (`+Y` on this robot) from the zero mark via `ros2 action send_goal /navigate_to_pose ...`. Watch Foxglove throughout: planned path, footprint tracking, local costmap. Hand near the dashboard E-stop, not just watching.
4. **Return-to-zero goal** once the first is reached, and a direct check worth doing rather than assuming: does the robot actually stop back on the physical zero mark, not just wherever the map's `(0,0)` nominally is.

Facts the new session can trust without re-confirming: top speed capped at `0.15 m/s`; the rear-mast mask is active, confirmed non-duplicated, but its correctness at the boundary is exactly the open question above; `robot_state_publisher` and the safety-cushion visual are both live and confirmed on hardware; the zero-position convention (map origin = wherever `base_link` is at a fresh mapping session's first scan) is established and repeatedly verified, not merely assumed.

## 17.17 13 Aug 2026: first Nav2 launch on hardware — two real bringup bugs, one milestone, one still-open discrepancy

The user did not in fact open a new session after §17.16 — continued directly into the first Nav2 hardware launch instead. Logged here rather than retroactively folded into §17.16, since it is materially new work, not a continuation of what that section already described.

**First launch attempt died at `collision_monitor`.** `parameter 'observation_sources' is not initialized` — `nav2_params.yaml` had no `collision_monitor` block at all, and that parameter has no sensible default (Nav2 cannot guess a robot's sensors). `lifecycle_manager` correctly refused to bring up the rest of the stack rather than run degraded. Same bug *class* as the missing `velocity_smoother` block found on this branch's first Nav2 config pass (§17.14) — found and missed together the first time, found individually here. Fixed by adding a full `collision_monitor` block: `action_type: "approach"` (velocity-aware, forward-simulates the footprint along the commanded velocity — deliberately not a static stop polygon at the cushion boundary, which would halt the robot merely for sitting near a wall, including the legitimate 7 cm case measured in §17.15 and ordinary narrow-aisle transit) against `/local_costmap/published_footprint` (the live, authoritative footprint, not a duplicated copy) and `/scan_reliable` (not raw `/scan`, for the same QoS reason as everywhere else in this stack, and specifically so the masked rear arc from §17.15 doesn't make the collision monitor refuse to ever let the robot reverse). This is, incidentally, the "guarded drive" feature requested earlier — native to Nav2, sitting below the planner where it cannot be reasoned around, rather than a hand-written teleop guard.

**Second attempt got past `collision_monitor` and died at `docking_server`**: *"Charging dock plugins not given!"* This robot has no charging dock and will not acquire one. The underlying cause for both failures is the same: this Nav2 build is newer than the one `nav2_params.yaml` was originally written against, and `nav2_bringup`'s `navigation_launch.py` on this build also starts `route_server` and `opennav_docking`, neither of which existed at the time. Configuring dock plugins for a dock that doesn't exist would be pure ceremony, and would leave the identical trap armed for whatever node the next Nav2 release adds to that file. **Fixed by rewriting `nav2_slam.launch.py` to start Nav2's nodes explicitly** rather than including `nav2_bringup`'s launch file — `controller_server`, `smoother_server`, `planner_server`, `behavior_server`, `velocity_smoother`, `collision_monitor`, `bt_navigator`, `waypoint_follower`, and a `lifecycle_manager` whose `node_names` matches exactly that set. `route_server` and `docking_server` are simply not started.

**Third attempt: `Managed nodes are active`.** First successful Nav2 bringup on this robot. Confirmed the `cmd_vel` chain is wired end-to-end and not just configured on paper: `ros2 topic info /cmd_vel --verbose` lists `collision_monitor` as a publisher alongside `joy_to_aislebot` and `phone_dashboard`, and `ros2 topic hz /cmd_vel` during manual WASD adjustment showed an irregular ~7–9 Hz consistent with human input (`std dev 0.21s`, `max 1.1s` gaps) — not the steady ~25 Hz a live idle-gamepad-fighting-Nav2 problem would produce, so that latent issue flagged in §17.14 remains confirmed inert on this deployment, not newly re-verified as fixed.

**The still-open item, and the reason this session stops here rather than sending a goal.** `ros2 run tf2_ros tf2_echo map base_link`, with the robot physically standing at the zero mark, read `[0.285, -0.090, 0.000]` at `-89.5°` yaw — not `[0, 0, 0]`. Root cause: the mapping session running underneath this Nav2 test was never stopped and restarted after the earlier WASD driving (§17.16's block-vs-phantom item was never actually investigated either, for the same reason — it's the same unresolved-origin problem, not two separate ones). The recommended fix — stop mapping, confirm the mark, press Map fresh, relaunch Nav2 — was *attempted* but evidently did not actually take effect: a second `tf2_echo` read `[0.285, -0.063, 0.000]` at `-89.3°` immediately after. The `X` coordinate, `0.285`, is bit-for-bit identical between both readings; only `Y` and yaw drifted slightly, which is the signature of the *same* long-running session's pose estimate settling further under live scan-matching, not a new session with a genuinely reset origin. **The stop/restart sequence needs to be re-attempted and independently verified (a `tf2_echo` reading near `[0,0,0]`) before any goal is sent, and before the block-cluster question from §17.16 can be considered investigated at all** — nothing this session did actually got a clean-origin map to test either question against.

**Session closed here at the user's request**, with the Nav2 stack and mapping session most likely both left running (not confirmed stopped). Next session, in order: confirm process state (`ps aux | grep -E "slam_toolbox|nav2|lifecycle_manager"`), stop and restart mapping fresh from the zero mark, verify with `tf2_echo` before trusting it, then proceed to the block-cluster question and the first autonomous goal — both now blocked on the same single prerequisite.

## 17.18 14 Aug 2026: the zero-mark model was wrong, not the restarts — flagged and handed off before diagnosing further

New day, same branch. `ps aux` showed a genuinely fresh `scan_relay`/`slam_toolbox` pair (new PIDs, exactly one of each) after a careful stop → confirm-at-mark → Map-fresh sequence — solid evidence, unlike §17.17's attempts, that this was a real restart. **`tf2_echo map base_link` still did not read near `[0,0,0]`**: `[0.685, -0.219, 0.000]` at `-90.112°` yaw, rock-steady across seven samples (no drift — a fixed relationship, not noise).

**This overturns the model stated repeatedly since §17.12, not just this one reading.** That model — "`slam_toolbox` zeroes the map's origin to wherever `base_link` is at a fresh session's first scan, so a consistent physical start pose gives every map the same origin" — was asserted from general SLAM/ROS convention, not verified against this project's actual `slam_toolbox` configuration or source. §17.17's non-zero readings were attributed to the restart not actually happening, which was plausible at the time and turned out to be correct for §17.17's specific case. Today's reading, from a session with much stronger evidence of being genuinely fresh, does not fit that explanation, and continuing to assume "must not really be fresh" without evidence would be the same mistake §17.9–§17.10 already taught: prefer the account with weaker evidence to revise, not the one that's inconvenient.

**A concrete, testable hypothesis, not yet confirmed:** the yaw offset lands close to `-90°` on every fresh-session reading across both nights (`-89.5°`, `-89.3°`, `-90.1°`) — the same magnitude as `odometry_publisher.py`'s own deliberate constant `-90°` published-frame rotation (§17.10). If `slam_toolbox`'s `map→odom` initialization sets that transform to identity at session start, rather than actively computing it to cancel out `base_link`'s current (already `-90°`-rotated) published orientation, then `odom→base_link`'s existing `-90°` would pass straight through into `map→base_link` unchanged — explaining the yaw pattern exactly. The varying translation offset (`0.285/-0.09` one night, `0.685/-0.219` the next) would then be whatever `odom`'s own accumulated position happens to be at that moment — itself set once, at whenever `odometry_publisher` last started (a service restart), not reset by a fresh mapping session at all. **Not yet tested**: decomposing `map→odom` and `odom→base_link` separately (`ros2 run tf2_ros tf2_echo map odom` and `... odom base_link`) would show directly which transform actually carries the `-90°`, confirming or ruling this out before acting on it.

**Two separate tracks recorded for the next session, deliberately not conflated:**
1. **Diagnose properly** — the decomposition above, then either a `slam_toolbox` configuration fix or a "reset `odometry_publisher` at the same moment the robot is placed at the mark" procedure, depending what the decomposition shows.
2. **Get a first autonomous drive working today regardless** — goals don't need to trust a `(0,0)` that may not mean what it was assumed to mean. Read the robot's actual current `map→base_link` transform, use its rotation matrix to convert "1.5 m forward in the robot's own frame" into map coordinates directly (the same computation already worked out in §17.17's aborted attempt), and record that starting transform verbatim as the "return" goal rather than assuming it's `(0,0,0)`. Correct regardless of which cause the diagnosis finds, and doesn't block on it.

**Session closed here at the user's explicit request — a new session on this same branch**, to avoid the same kind of context-length memory loss that produced §17.15's correction. Handoff prompt given directly to the user for that purpose.

## 17.19 14 Aug 2026: the zero-mark hypothesis confirmed, a real autonomous-drive bug found and fixed on hardware, the first-ever forward-and-return round trip completed

Same day, new session per the §17.18 handoff. Both tracks from that section's close-out were worked in order: diagnose the origin question, then drive regardless of the outcome.

**Track 1 confirmed exactly as hypothesised.** `ros2 run tf2_ros tf2_echo map odom` read identity (`[0,0,0]` at `0°`); `... odom base_link` read `[0.685, -0.219, 0]` at `-90.111°` — bit-for-bit the same numbers §17.18 saw when it read `map→base_link` directly. `slam_toolbox` sets `map→odom` to identity at session start rather than cancelling `base_link`'s already-rotated published orientation, so `odom→base_link`'s `-90°` (`odometry_publisher.py`'s deliberate rotation, §17.10) and whatever translation `odom` had accumulated since its last restart pass straight through into `map→base_link` unchanged. Confirmed, not just plausible. No code changed for this — `nav_goal.py` (below) works correctly regardless of what map `(0,0)` means, which is why this was never a blocker for track 2.

**`tools/nav_goal.py` (new).** Reads the robot's actual `map→base_link` transform live and rotates a requested body-frame offset ("N metres forward") into map coordinates, printing both a GO goal and a RETURN goal (the robot's current pose, verbatim) to copy before sending anything. This is track 2's design from §17.18, implemented. Also dropped `GoalAlign`/`PathAlign` from `nav2_params.yaml`'s DWB critics in the same pass — both hardcode "forward" as `base_link`'s `+X`, which on this robot is *right* (§17.10), so both would have rewarded travelling sideways and fought to rotate the chassis toward it. `amcl`'s `initial_pose` was also corrected (`yaw: -1.5708`, not `0.0`) though that mode remains unexercised.

**Second latent bt_navigator bug, same class as §17.14/§17.17's, found the same way — by reading a config that had never actually run.** First Nav2 launch attempt on this branch's corrected critics config activated cleanly (`Managed nodes are active`) but the first goal came back `Behavior tree threw exception: Empty Tree. Exiting with failure`. `nav2_params.yaml` set `default_nav_to_pose_bt_xml: ""` on the theory (§17.14) that an empty string falls back to Nav2's built-in default BT file. It does not, on this Nav2 build: `ros2 param get /bt_navigator default_nav_to_pose_bt_xml` on the live node showed the parameter as a real, explicitly-provided empty string, never substituted for the computed default. Checked against this build's own reference config (`/opt/ros/jazzy/share/nav2_bringup/params/nav2_params.yaml`) before changing anything, rather than guessing from memory: `plugin_lib_names` being left unset is correct and matches upstream's own comment ("Built-in plugins are added automatically") — that half of §17.14's fix was right. Only the BT-xml key was wrong. **Fix:** the key removed from the yaml entirely; `nav2_slam.launch.py` now resolves `nav2_bt_navigator`'s real installed share directory at launch time and passes both `default_nav_to_pose_bt_xml` and `default_nav_through_poses_bt_xml` as explicit node parameters, no hardcoded path.

**A DDS participant-exhaustion failure, self-inflicted by the session's own churn.** After the bt_navigator fix, a relaunch died with `Failed to find a free participant index for domain 42` — `planner_server` aborted outright, and even a bare `ros2 param get` hit the same wall moments later. Root cause: an earlier Ctrl-C on a `ros2 launch` in one terminal had stopped the parent process without actually killing its nine children, which sat orphaned holding connection slots for the rest of the session. `ps aux` grepped for the nav2 node names found exactly nine stale PIDs from a prior launch generation; killed cleanly with plain `kill`, confirmed gone, and the next launch came up without incident. Existing infrastructure (`scan_relay`, `slam_toolbox`, `odometry_publisher`) was never affected — Foxglove and the dashboard stayed live throughout, which is what made "pool exhausted" rather than "network broken" the right diagnosis.

**First-ever autonomous goal sent on this robot — and it revealed a real, previously-invisible bug.** With Nav2 finally healthy, a 1.5 m goal computed by `nav_goal.py` was sent. The robot travelled roughly 0.96 m at **88.4° to the commanded direction** — measured directly from the action's own feedback poses, not estimated — and was E-stopped after contacting an obstacle. Root cause, found by inspecting `mecanum_teleop_asymmetric.py` alongside the TF chain: two individually-correct, individually-validated axis conventions meet at `/cmd_vel` and nothing had ever reconciled them. Nav2 reads pose and writes velocity in `base_link`'s TF axes (`+X`=right, `+Y`=forward, §17.10's deliberate rotation); `teleop_asym` — and the dashboard, and the joy node — read `/cmd_vel` as standard REP-103 (`+X`=forward, `+Y`=left). §17.10 rotated odometry's *published* pose and twist and never touched the velocity *input* side; manual driving never noticed because its producers and consumer already agreed with each other. Nav2, wanting forward motion, published `linear.y`, and `teleop_asym` executed a left strafe — and because the error was a constant 90° rotation sitting inside a closed control loop, Nav2's own cross-track corrections came out rotated too, so the drive didn't fail as a single wrong turn, it failed by never converging.

**Fix: `cmd_vel_axis_adapter.py` (new node), not an edit to either existing convention.** Both sides have strong independent hardware validation behind them — the TF/LiDAR side from the mirror calibration and the tape-measured wall gap, the teleop side from every metre this robot has ever been manually driven, E-stop included — so per §17.10's own rule (change the side with weaker evidence, and here neither is weak), this converts between them explicitly at the one place they meet rather than editing a validated file. `collision_monitor` now outputs `/cmd_vel_baselink`; the new node publishes `/cmd_vel` as `(x=in.y, y=-in.x)`, angular.z unchanged, and is placed *after* `collision_monitor` deliberately — that node forward-simulates its footprint polygon along the commanded velocity, and both need to stay in the same (TF) frame for that check to mean anything. DWB and `velocity_smoother` limits were also halved (`0.15→0.08 m/s`, `0.30→0.20 rad/s`) at the user's request; recorded honestly rather than smoothed over that the robot was not exceeding its old limits on the failed run (0.14–0.17 m/s measured, matching the 0.15 cap) — it felt fast because it was travelling the wrong way, not because it was overspeeding. Decel limits deliberately left unchanged, since lowering them would slow the robot's stop, the opposite of the intent.

**Two more goals sent after the fix, both to validate before trusting the change at full scale.** A 0.5 m forward goal and its return, computed fresh by `nav_goal.py` each time. Both `SUCCEEDED`, no E-stop either time. Measured directly from the feedback, the same way the bug itself was measured: the forward leg's direction error was `5.5°` (down from `88.4°`) and the return leg's was `3.7°`, stopping `4.6 cm` short of its exact target — inside the `5 cm` goal tolerance. **First-ever autonomous forward-and-return round trip on this robot**, the session's stated goal from the handoff, completed.

**One incidental discrepancy noted but not chased.** Immediately before the 0.5 m test, with the robot visually confirmed at the physical zero mark, `nav_goal.py` read `y ≈ +0.44 m`, not near zero — despite this being the same mapping session where `map→odom` was confirmed identity earlier the same session. Most likely explanation: `slam_toolbox`'s scan-matching, which continuously corrects `map→odom` as the robot drives (not fixed at identity forever, only observed as such at a session's very first scan), had by this point corrected for real odometry drift from wheel slip during the 88.4°-error crash. Not confirmed by a second decomposition — deliberately not chased tonight, since `nav_goal.py`'s relative-offset design makes the goal correct and safe regardless of what the absolute number means. Left open for a session with room to investigate it properly.

**`collision_monitor`'s recurring `FootprintApproach.max_points` warning, open since the session's own earlier bringups, fully closed.** Checked against `nav2_collision_monitor`'s actual source (`polygon.cpp`) rather than left as a shrug: `max_points` is a deprecated parameter name, superseded by `min_points` (which this config already sets to `6`); the warning is dead backward-compatibility code catching the old name's absence and silently continuing with the real value already in effect. No fix needed, and none of tonight's collision-monitor behaviour was ever affected by it.

**Session paused here at the user's need to step away, not at a natural design boundary** — hardware left as the user described leaving it ("park and disconnect"), not independently confirmed stopped. Next session, in order:
1. Confirm process state before trusting anything (`ps aux`), same discipline as every prior handoff on this branch.
2. Decide whether to chase the odometry/zero-mark discrepancy now that the drive stack itself is trusted, or continue treating it as immaterial to goal safety.
3. A larger-radius test (closer to the original `1.5 m`) now that the axis fix is validated at `0.5 m` twice.
4. Foxglove's built-in "Publish Goal" 3D-panel tool was confirmed workable for future goals — `bt_navigator` already subscribes to `/goal_pose` (`geometry_msgs/PoseStamped`) automatically, verified from Nav2's own source, no config needed — as a friendlier alternative to hand-built `send_goal` commands once the fix above has more hardware runs behind it.

## 17.20 14 Aug 2026: Foxglove click-to-goal wired up, the rotation-doesn't-map mystery traced to its real cause through the user's own controlled experiment, an autonomous scan tool designed but not yet run

Same day, continuation after §17.19's close. Started from theory discussion (SLAM fundamentals, mecanum-specific literature survey — separately valuable but not itself part of this robot's build) before returning to hardware.

**Foxglove click-to-goal set up.** Verified from Nav2's own source (`nav2_bt_navigator`'s `navigate_to_pose.cpp`) that `bt_navigator` subscribes to a hardcoded `goal_pose` topic automatically, no config needed on this project's end. The user's exported 3D-panel settings showed `publish.poseTopic` set to `/move_base_simple/goal` — the old pre-Nav2 topic name, which nothing in this stack listens for. Corrected to `/goal_pose`. One real axis gotcha documented for future use: the drag-arrow sets `base_link`'s yaw directly, and this robot's `+X` is its right side (§17.10), so the arrow points where the robot's right side will face, not its nose — drawing 90° clockwise of the intended heading is required until/unless a dedicated correction node is built.

**A first, wrong hypothesis, caught and corrected before it went anywhere.** When the user reported the built map appearing to vanish at some headings during a 360° spin but not others, the first theory was Foxglove's Fixed Frame being set to `base_link` rather than `map`, making the world appear to rotate with the robot. The user's actual exported panel JSON showed `fixedFrame: "map"` and `followMode: "follow-none"` — both already correct, ruling this out directly rather than by further guessing.

**The real question, and a second wrong hypothesis, also caught.** The user ran a genuinely well-designed controlled experiment: rotate 90° with zero translation (repeated four times, CW and CCW, across the full circle) — no new map area ever appeared. The moment *any* small forward nudge was added, new area appeared immediately, every single time. Four-for-four with the same pattern rules out a coincidental rendering glitch. First explanation offered — that this was `slam_toolbox`'s `minimum_travel_heading` threshold (0.2 rad) simply not yet being crossed — was checked directly against `slam_toolbox`'s actual source (`shouldProcessScan` in `slam_toolbox_common.cpp`) and disproven: that gate rejects a scan only if *both* distance and heading are below threshold, so heading alone crossing ~11.5° should already let a scan through. Corrected in place rather than left standing.

**Real, source-and-config-grounded explanation.** `slam_nodom.yaml`'s own header states the mapping mode runs with "no external odometry, scan-matching only" — every pose update comes purely from matching the new scan against the map, no motion prior at all. Pure rotation with a 360° lidar produces a scan that is nearly identical to the last one, just re-indexed by angle — with no odometry hint to narrow the search, and in a junction where several aisle branches look roughly similar, the matcher has very little unambiguous signal to confidently commit an update. The smallest translation introduces parallax (near objects shift more than far ones) — an unambiguous, strong cue no rotation-only scan provides — and unlocks a confident update immediately. This is not a bug; it is the live, hardware-confirmed version of exactly the gap this session's own literature survey flagged as the field's standard fix for scan-matching weaknesses: IMU/odometry fusion, still on the roadmap and not yet built (Phase 2, B.3).

**`tools/zero_point_scan.py` (new) — designed and written, NOT yet run on hardware.** Automates the procedure the user found by hand: rotate to the next heading via `NavigateToPose`, check whether `/map`'s known-cell count actually grew, and only attempt a small nudge (strafe first, forward as last resort, capped at a few attempts) if it didn't — never a blind nudge every step, matching the user's explicit "only enough movement, self-detected" requirement. Time-boxed (default 150 s), and unconditionally returns to the exact starting pose as the very last action on every exit path, including a time-budget break or Ctrl-C.

**A second latent axis bug found and deliberately not fixed tonight.** Nav2's `Spin`/`BackUp` recovery behaviors were the obvious tool for this script, but `behavior_server` was never given a `cmd_vel` remap in `nav2_slam.launch.py` — its output skips both `collision_monitor` and `cmd_vel_axis_adapter`, publishing straight to `/cmd_vel` in Nav2's own TF-frame convention. `Spin` only ever commands `angular.z`, identical in both conventions, so it's inert. `BackUp` commands a linear velocity and would very likely reproduce tonight's exact 88° miss — untested and unfixed, since nothing has called it yet. `zero_point_scan.py` was deliberately written to use only `NavigateToPose` for every motion, rotation and nudge alike, sidestepping this entirely rather than fixing and freshly testing a second thing in the same session. Real open item for a future session: give `behavior_server` the same remap treatment `controller_server` and `velocity_smoother` already have, if `Spin`/`BackUp` are ever wanted.

**Manual mapping continued by hand in the meantime, and it worked.** A further round of strafe-and-forward/backward nudging (deliberately no rotation this pass) against the same running map produced substantially denser, better-defined coverage — solid black wall boundaries and a much larger contiguous white region than any earlier screenshot this session. Confirms the underlying mechanism understood above: translation is what the current SLAM config actually needs to commit new area, and hand-applying it works exactly as the automated version is designed to.

**Session closed here for the night, not at a natural design boundary — a new session tomorrow, same branch.** Nothing was left running unconfirmed; the usual `ps aux` discipline applies first thing next time regardless.

**Handoff plan for tomorrow:**
1. Confirm process state fresh, same as every prior handoff.
2. **First real test of `zero_point_scan.py`** — small and cautious, not the full run: `python3 zero_point_scan.py --step-deg 90 --max-duration 40`. Hand near the E-stop, same discipline as every new capability this project has ever tested. Only move to the full 360°/2.5-minute run once the small one is watched end-to-end.
3. Once trusted, use it to build one genuinely complete base map from the zero mark, rather than continuing to extend the hand-built one piecemeal.
4. Foxglove click-to-goal is ready to use for future goals — remember the 90°-clockwise arrow correction until a proper adapter node exists for it.
5. `behavior_server`'s missing `cmd_vel` remap remains open, inert only because nothing has called `Spin`/`BackUp` yet — fix before ever relying on either.

## 17.21 15 Aug 2026: two pre-run bugs fixed before ever moving, the zero-point re-zero procedure finally nailed down, `zero_point_scan.py`'s first three hardware runs, and a real 25% odometry error found and fixed — rotation still open

New session per §17.20's handoff, on the same branch. Opened by re-reading §17.12–§17.20 in full per standing discipline, then `ps aux` before touching anything: mapping stack (`ydlidar`, `scan_relay`, `slam_toolbox`) up cleanly since 10:42/10:56 the prior night, no orphans, Nav2 not running. Nothing bad survived overnight.

**Two real bugs found and fixed by reading the never-yet-run config against what `zero_point_scan.py` actually does, before it ever touched hardware — same discipline as every prior latent-bug pass on this branch.**

1. `nav2_params.yaml`'s `progress_checker` was `SimpleProgressChecker`, which measures progress as XY distance only and ignores yaw entirely. `zero_point_scan.py` is built almost entirely from rotate-in-place goals — zero XY distance by construction — so every rotation would have been scored as zero progress regardless of how fast the robot was actually turning, and aborted at the 10 s `movement_time_allowance`. At `max_vel_theta` 0.20 rad/s a 90° turn needs 7.9 s at the cap alone before any slowing near the goal, so the very smoke test the §17.20 handoff recommended (`--step-deg 90 --max-duration 40`) would very likely have failed mid-turn. **Fix:** swapped to `PoseProgressChecker` with `required_movement_angle: 0.25` rad (~14°, deliberately under one 20° scan step so a single step's rotation resets the timer on its own).
2. §17.20 left `behavior_server`'s missing `cmd_vel` remap open on the theory that nothing calls `Spin`/`BackUp` since the script only uses `NavigateToPose`. **That theory was wrong, and this is worth stating plainly rather than smoothing over**: `bt_navigator`'s default behaviour tree runs `Spin` and `BackUp` *automatically* as recovery whenever a `NavigateToPose` goal fails — nothing has to call them directly. Combined with bug 1 (rotations far more likely to fail), the unremapped `behavior_server` was a live, near-certain risk, not an inert one. **Fix:** `behavior_server` remapped to `cmd_vel_nav` in `nav2_slam.launch.py`, same path `controller_server` already takes through `velocity_smoother → collision_monitor → cmd_vel_axis_adapter`. Matches upstream `nav2_bringup`'s own wiring; the explicit-nodes rewrite in §17.17 dropped it by omission. **Confirmed on hardware later this session**: `bt_navigator` did invoke `Spin` and then `BackUp` automatically within the first 90 s of real use (both aborted on `Collision Ahead`, not relevant here — the point is they fired at all, and did so through the correct, monitored path).

Also in `zero_point_scan.py` itself: `map_grew_since()` slept 1.3 s then called `spin_once` a single time, which could service the TF listener instead of the `/map` callback and read a stale cell count — a false "no growth" triggering an unneeded nudge. Changed to spin for the entire settle window (new `--map-settle` arg, default 1.5 s). All committed together, `3cead59`.

**The zero-point re-zero procedure — the actual open question carried since §17.12, finally answered on hardware.** The user asked directly: does pressing **Map** set a new zero point? **No.** `slam_toolbox` sets `map→odom` to identity at a mapping session's *first scan* — it does not plant the map origin under the robot. Map `(0,0)` is wherever *odometry* was zeroed, and odometry only zeroes when `odometry_publisher` starts, i.e. when `aislebot.service` (re)starts. **The whole procedure is: park on the physical mark, then `sudo systemctl restart aislebot.service`.** Confirmed repeatedly on hardware today: `tf2_echo odom base_link` immediately after every such restart read exactly `[0.000, 0.000, 0.000]` at `-90.000°`, to the millimetre, every single time (§17.10's constant −90° twist, so this is the correct reading, not an error).

**A permanent visual zero-point marker, requested by the user and built the same session.** `mapping_full.launch.py` now also starts a `static_transform_publisher` publishing a fixed `map → zero_point` frame at the origin, carrying the *same* −90° twist `base_link` has — so when the robot is standing on the mark, `zero_point`'s and `base_link`'s axis triads coincide exactly, both in Foxglove by eye and numerically: `tf2_echo zero_point base_link` reads `[0,0,0]` at `0.000°` when home, no −90° to mentally correct. This is now the standing "am I home" check, documented in `Important_Commands.md` §8 alongside the restart procedure. Explicit, stated caveat: the marker shows where the map *believes* zero is, which can separate from the physical mark after heavy driving with wheel slip — confirmed itself later this session (below), not just a theoretical caveat.

**`Important_Commands.md` also gained §9**, documenting the CALIBRATE button, the corrected click-to-goal topic, and the `allow_unknown` planner switch for later once a real base map exists. Committed with the marker, `a26f9a0`.

**New: a CALIBRATE button on the phone dashboard (v2.4), and `goal_pose_adapter.py`.** CALIBRATE runs `zero_point_scan.py` as a dashboard-managed subprocess — two-tap arm (one stray tap cannot start a 45 kg robot), a preflight that refuses to start unless mapping is live *and* `bt_navigator` is on the node graph (a sentence on the button instead of a silent multi-second hang), SIGINT-then-drive-home on a second press, SIGKILL-plus-`/navigate_to_pose` cancel-all on E-STOP (killing the script alone leaves Nav2 still executing its last accepted goal), and its stdout tailed back to the phone from `~/aislebot_logs/calib_*.log` so a bad run is diagnosable afterward. `goal_pose_adapter.py` closes §17.20's other open item: it listens on a new `/goal_pose_click` topic and republishes to the real `/goal_pose` with the yaw rotated −90°, so a Foxglove drag arrow means "point the nose here" instead of "point the right side here." Deliberately opt-in on a separate topic rather than intercepting `/goal_pose` directly — a node that silently rotates every goal on the system is the same invisible-transform shape that caused the §17.19 axis bug in the first place. Verified algebraically in all four quadrants before deploying. Committed `df90f75`. **Not yet exercised via the dashboard button or via Foxglove click-to-goal this session** — all hardware testing below used the script by hand, from a terminal.

**First-ever hardware run of `zero_point_scan.py` (`--step-deg 90 --max-duration 40`, then 90): 0 headings completed.** Root cause found from the run's own log plus a new instrument (`tools/map_watch.py`, built mid-session specifically because a Foxglove screenshot cannot distinguish "map is static" from "map grew but under threshold" from "`/map` never arrived," and this run needed to): `slam_nodom.yaml` sets `minimum_travel_distance: 0.2` m (slam_toolbox additionally allows ~10% slack, so the true gate is ≈0.179 m), and the script's nudge default was **0.15 m** — under the gate by construction. Every nudge scan was silently discarded before matching ever happened, and because the script returns to the anchor after each attempt, distance-since-last-processed-scan never had a chance to accumulate past the gate either. Not a behavioural bug, arithmetic: the map could not have grown, not merely didn't. §17.20 checked the *heading* gate and correctly cleared it; nobody had checked the *distance* gate against the nudge size, because the nudge size was invented in that same session against nothing in particular. **Fix:** default raised to 0.25 m, `map_grew_since()` now logs the actual before/after cell counts and the delta (not just a verdict), and a PID lockfile added (`/tmp/zero_point_scan.lock`) so the dashboard button and a hand-run copy can't fight over `/navigate_to_pose` at the same time — a real gap, since the button's own guard only sees its own subprocess. Committed `6184512`.

**Second and third runs, nudge fixed: map growth confirmed working, but two new problems surfaced, one fixed and one still open.**

- **Map growth is real and large.** `pathlog.py` (a second live logger, hand-typed directly on the Pi this session, not yet committed to the repo — flagged below) showed known-cell counts jumping 913→2321→3024→3674→4146 across one run, each jump landing exactly on a nudge, confirming the 0.2 m diagnosis directly rather than just by absence of the old symptom.
- **Rotations frequently stalled and timed out — still unexplained, the main open item for next session.** Multiple `NavigateToPose` rotation-only goals aborted at 20 s with `controller_server`'s `Failed to make progress` or DWB's `No valid trajectories out of 1343!` (`RotateToGoal/Nonrotation command near goal` weighted 0.99 in the rejection), sometimes after visibly reversing direction mid-turn. One run finished 47.3° off its last commanded heading. `pathlog.py` traces show heading swinging 30–49° inside 20 s windows while the robot's *centre* moved under 2 mm — i.e. slewing back and forth in place, which is what the user directly observed and described as "moving in absolute random direction hitting objects." `behavior_server`'s `Spin`/`BackUp` recoveries fired automatically on these failures (confirming the §17.20 theory correction above) and both aborted immediately on `Collision Ahead` even with the robot nowhere near a real obstacle by the user's own account — plausibly a consequence of the odometry error below feeding a wrong perceived position into `collision_monitor`, not independently diagnosed. **Not fixed this session.**
- **A real, dangerous divergence between Nav2's believed pose and physical reality, later explained (mostly).** In one run Nav2's own feedback reported the robot staying within 44 cm of the origin throughout and returning to 4.7 cm of it at the end, with `Reached the goal!` printed — while the user, standing next to the robot, confirmed it was nowhere near the mark and had made contact with objects along the way. Both cannot be true; investigated rather than argued past.

**Root-caused to mecanum lateral (strafe) slip in odometry — a real, tape-measured 24–25% error, confirmed at the wheel level before any code was touched.** Controlled tests, robot re-zeroed at the mark each time: driving 1.00 m forward (W only, no strafe/rotation) read `1.009 m` in the odometry (0.9% error — accurate). Driving 1.00 m sideways (D only) read **1.245–1.248 m**, twice, 3 mm apart — too tight to be floor noise, too large to be scale-factor rounding. **A first hypothesis (an axis-mislabelling bug) was raised and was wrong**, corrected in-conversation: `tf2_echo odom base_link` reports translation in the fixed `odom` frame (whichever direction was "forward" when `odometry_publisher` last started), not in `base_link`'s own instantaneous frame, so which coordinate moves for "forward" vs. "strafe" depends on boot heading and is not itself informative. **The real check, done properly**: echoed `/wheel_velocities_actual` live during an actual D-strafe. Measured `[FR, FL, RR, RL] = [-0.65, +0.65, +0.65, -0.65]` rad/s — algebraically *exactly* what the asymmetric inverse kinematics predict for a pure right strafe (computed `vx` and `wz` both land on precisely `0.0000`). The teleop's forward kinematics, the odometry's reverse kinematics, the ESP32 bridge's channel ordering (checked against `aislebot_esp32.ino`'s own `FR=0,FL=1,RR=2,RL=3` table), and the firmware's per-motor `DIR`/`ENC` sign table were all read and are internally consistent — **nothing is miswired or mis-signed**. The error is physical, not software: mecanum rollers scrub sideways across the floor during a strafe, so the wheels turn further than the chassis actually travels, and the ideal kinemematic model has no way to know that.

**Fix: a `lateral_scale` parameter in `odometry_publisher.py`, applied where `vy` is produced** so the integrated position, the published twist, and everything downstream inherit one correction. Longitudinal left untouched (measured accurate) rather than "fixed" alongside an axis that wasn't broken. **Made a live-read parameter, not cached at startup**, specifically because the very next measurement — a second floor, tested after the user physically rotated the robot to change surface — needed **0.92**, not 0.80: two independent routes to the same number (an uncorrected strafe reading `1.080`/`1.085` m per 1.00 m tape, and a 0.80-corrected strafe reading `0.868` m which back-solves to the same raw `1.085`). Surface dependence is the actual finding here, not a footnote, so `ros2 param set /odometry_publisher lateral_scale <x>` now takes effect immediately with no rebuild and no service restart that would throw away an established zero point. Default set to **0.92**, since that is the floor the physical zero mark actually sits on, not the first (unrelated) test spot. Also measured and *not* fixed: during a 1.00 m pure strafe the chassis visibly drifted 2–3 cm off the tape line (photographed) while odometry reported zero forward-axis change — a small unmodelled cross-coupling, ≈0.6 cm over a 0.25 m nudge, noted rather than modelled. Committed across three commits for a clean history (`0bcf8aa` the fix, `cbb6f69` the live-read refactor, `0beeafe` the 0.92 default), all pushed.

**Known gap at session close: the Pi's on-disk `odometry_publisher.py` is behind the repo.** Only the first, cached-at-startup, 0.80-default version (`0bcf8aa`'s content) was ever hand-patched onto the Pi and rebuilt. The live-read refactor and the 0.92 default (`cbb6f69`, `0beeafe`) exist on the branch but were not yet applied to hardware when the session ended — the natural first deploy step next time. Robot was left parked on the physical zero mark; `lateral_scale` on the Pi is currently `0.80`, not `0.92`, until that catch-up patch runs.

**A second small tool, `tools/map_watch.py`, committed (`6184512`); a third, `tools/pathlog.py`, was not.** Both print one line per second of known-cell count, its delta, and robot pose, built for the same reason: this session's own experience that a Foxglove screenshot shows an end state, not a trajectory, and cannot distinguish "static," "growing under threshold," and "`/map` absent" from each other. `pathlog.py` was hand-typed directly on the Pi via a terminal heredoc mid-session as a faster iteration than redeploying `map_watch.py` over a flaky `eduroam` link, and did the actual diagnostic work quoted above (the 30–49° heading-swing-with-no-translation table, the 44 cm/4.7 cm believed-vs-real contradiction). It only exists on the Pi's filesystem right now, not in git — worth committing next session so it isn't lost to a future redeploy or `aislebot_logs` cleanup.

**Session state at close, stated plainly:** the physical zero-point procedure is solid and hardware-confirmed, repeatedly. The `0.2` m nudge-threshold bug is fixed and hardware-confirmed (real map growth, 913→4146 cells). The lateral-slip odometry bug is fixed on the branch but only half-deployed. **Rotation-in-place reliability is the one fully open, unexplained problem** — DWB near-goal trajectory rejection, `RotateToGoal`'s 0.99-weighted "Nonrotation command near goal" line recurring across failures, is the leading unconfirmed hypothesis, not yet checked against `dwb_core` source the way this project checked `slam_toolbox`'s and `nav2_bt_navigator`'s source earlier on this branch. No full `zero_point_scan.py` run has yet completed cleanly end-to-end; the CALIBRATE button and `goal_pose_adapter`/click-to-goal remain built but unexercised; no point-to-point "real" autonomous drive (this session's and the roadmap's actual stated goal) was attempted, correctly deferred given what was found.

**Handoff plan for next session, in order:**
1. `ps aux` first, standing discipline — multiple `aislebot.service` restarts happened this session; anything left running (particularly a stale Nav2 launch) needs re-verifying, not assumed still valid.
2. **Deploy `odometry_publisher.py`'s pending change** — the Pi is currently on the cached 0.80-default version; the branch has the live-read 0.92-default version. Patch, rebuild, restart at the mark, confirm `ros2 param get /odometry_publisher lateral_scale` reads `0.92` and `tf2_echo odom base_link` reads `[0,0,0]` at `-90°`.
3. **Diagnose the rotation stall in isolation before re-attempting the full scan** — a single `NavigateToPose` rotation-only goal or a standalone `/spin` action call, hand on E-stop, `map_watch.py`/`pathlog.py` running throughout. Check `dwb_core`'s source for the `RotateToGoal`/near-goal-trajectory interaction the way this project has checked other Nav2 internals on this branch, rather than guessing further.
4. Once rotation is understood, re-run `zero_point_scan.py` by hand first (small step count, short duration) with a live logger running and hand on E-stop, before trusting the CALIBRATE button or a longer run.
5. Only after one clean full scan should point-to-point driving — a genuine round trip, or Foxglove click-to-goal via `goal_pose_adapter` (`/goal_pose_click`, unexercised) — be attempted. This remains the actual stated goal of the phase; everything above is the prerequisite chain underneath it, in dependency order.
6. Commit `pathlog.py` to `tools/` so it isn't lost.

## 17.22 15 Aug 2026: the rotation stall traced to source, resolving §17.21's open item

Continuation, same day — the user asked directly why Nav2 was failing rotation goals, which is exactly the open item §17.21 left as "leading hypothesis, not checked against `dwb_core` source." Checked properly this time: fetched `dwb_critics/src/rotate_to_goal.cpp` and `dwb_plugins/one_d_velocity_iterator.hpp` from `ros-navigation/navigation2` (`jazzy` branch) directly, rather than reasoning from the error text alone.

**Confirmed mechanism.** `RotateToGoalCritic::scoreTrajectory` — once the robot is judged to be at the goal position and roughly stopped (both true almost instantly for a rotation-only goal, since commanded position never changes) — enforces `fabs(traj.velocity.x) > 0 || fabs(traj.velocity.y) > 0` throws `"Nonrotation command near goal."`: a zero-tolerance, bit-exact check, not a small-epsilon one. `dwb_plugins`' sampler *does* guarantee an exact `0.0` is injected into each axis's candidate list independently (confirmed in `one_d_velocity_iterator.hpp` — a real safety net, this is not a missing-zero bug), but `FollowPath`'s `vx_samples: 5` × `vy_samples: 10` × `vtheta_samples: 20` builds the full cross-product grid, so only the *one* (x=0, y=0) pair out of 50 survives regardless of samples count — **20 of ~1000 candidates** even reach the rotation check, matching the logged `1343`. The other two critics then killed nearly all of that surviving 2% too (`Oscillation`/`ObstacleFootprint`, ~1% each in the log, not separately investigated this pass). Net: structurally near-zero survivors on every rotation-only goal, not an intermittent fault — explains why this never showed up on driving-somewhere goals (rarely "at goal" long enough for the rule to matter) but hits every step of `zero_point_scan.py`.

**Consequence for next session's fork (§17.21's open decision, analytical-vs-empirical).** This resolves it: `Spin` doesn't route through `dwb_core`'s trajectory sampling or critics at all, so it cannot hit this specific mechanism by construction — switching `zero_point_scan.py`'s rotation steps from `NavigateToPose` to `Spin` is no longer just "try the simpler tool," it's now a source-confirmed fix for a source-confirmed cause. `Spin`'s own single observed failure (`Collision Ahead - Exiting Spin`, during the automatic recovery invocation in §17.21) runs through a separate, not-yet-read code path and remains genuinely open — a different investigation, not resolved by this one.

## 17.23 18-19 Aug 2026: Phase 1 re-opened and partly closed, DWB replaced with MPPI, two real bringup bugs, first hardware validation of the new controller

New session, explicit two-phase plan from the user: confirm SLAM/odometry in isolation (Phase 1) before touching Nav2 again (Phase 2), deliberately reopening §17.21's known gap — the live-read `lateral_scale` fix (`cbb6f69`, `0beeafe`) was committed but never actually deployed; the Pi was still running the cached `0.80` version.

**Phase 1, confirmed as far as it went.** `ps aux` first, standing discipline: base stack up cleanly, no stale Nav2, no orphans. Deployed the pending `odometry_publisher.py`, confirmed live rather than assumed: `ros2 param get /odometry_publisher lateral_scale` read `0.92`, and `tf2_echo odom base_link` immediately after the restart read `[0,0,0]` at `-90.000°`, matching every prior re-zero exactly. `tools/pathlog.py` — hand-typed on the Pi last session, never committed — added to the repo (`157a878`). Re-zero re-confirmed via both readings: `odom→base_link` and `zero_point→base_link` both landed on their expected numbers to the millimetre. The full manual-driving tape-measure test (straight/strafe/diagonal with Nav2 off) was designed and one preliminary out-and-back was logged via `pathlog.py` (closed to 3.4 cm over a ~2.3 m round trip, consistent with the 2.6 cm/1.74 m repeatability noted in `odometry_publisher.py`'s own comments) but the deliberate, tape-measured, stop-at-each-waypoint version was **not completed** — the user redirected to Phase 2 before it finished. Recorded honestly: Phase 1 is not formally closed, and the strict two-phase ordering was not actually followed once redirected.

**The DWB-vs-MPPI decision, made explicitly per the user's request, not a detail.** Chosen: MPPI, `motion_model: Omni`. Reasoning worked from source, not preference, extending §17.22's finding: `nav2_mppi_controller`'s critics are uniformly additive (`data.costs += ...`) with no throw-and-eliminate path anywhere in the optimizer, so "no valid trajectories" — the exact failure class that broke DWB on rotation-only goals — cannot occur by construction. Checked specifically: `goal_angle_critic.cpp` (MPPI's `RotateToGoal` counterpart) is a plain weighted angular distance, never rejecting; `twirling_critic.cpp` returns early inside position goal tolerance, so it does not fight rotation-in-place. Separately, `motion_models.hpp`'s `OmniMotionModel::isHolonomic() -> true` means `vy` is genuinely sampled and blended with `vx`/`wz` in every rollout — the actual mechanism "use the robot's full mecanum freedom" requires, which DWB's fixed sample grid could only ever offer as discrete combinations.

**A real in-place-rotation clearance calculation, worked out collaboratively with the user against the robot's actual measured geometry, not assumed.** Nav2's own padded footprint corner is `0.622 m` from centre (`hypot(0.25, 0.57)`, from the §17.7/§17.12 measurements); a clean in-place spin therefore needs `0.622 + 0.25 (inscribed radius) ≈ 0.87 m` of clearance in every direction. The user's first answer ("~1 m") was ambiguous between radius-from-centre and radius-from-chassis-edge; resolved by iterating the arithmetic together rather than accepting the rounder, more optimistic reading — final measured-from-centre figures: right 4 m, front 2 m, left ~0.75 m (0.5 m edge gap + 0.25 m padded half-width), rear ~1.07 m (0.5 m edge gap + 0.57 m padded half-length). The rear number is what it is specifically *because* the edge-vs-centre distinction was pressed on — a first, centre-only reading of "0.5 m" would have implied the robot's own resting footprint already overlapped an obstacle, which was the tell that the reference point was wrong, not the geometry.

**Two dropped MPPI stock critics, same bug class as §17.14/§17.17/§17.19's — a Nav2 default silently wrong here purely because `base_link` is non-REP-103.** `PathAngleCritic` computes `atan2(dy, dx)`, assuming `+X` is the nose; on this robot `+X` is the right side, so it would reward travelling sideways and rotate the chassis toward it — the same failure `GoalAlign`/`PathAlign` would have caused under DWB (§17.19). `PreferForwardCritic` penalises negative `vx`, meaningless once `vx` means strafe, and encodes a differential-drive constraint (reluctance to reverse) a mecanum base does not have. Both checked against source and dropped rather than reparametrised, since no parameter renames which axis is forward.

**MPPI's speed limits raised only partway back from DWB's post-§17.19 halved caps** (`0.08→0.12` m/s translation, `0.20→0.30` rad/s rotation), deliberately not all the way to the original `0.15`, because Phase 1's tape-measure validation of the corrected odometry was not actually completed this session. `velocity_smoother`'s own limits raised in step for the same reason given in §17.19: it clamps whatever the controller commands, so a limit left behind there does not disagree with the controller, it silently wins.

**Two real, previously-latent Nav2 bugs found at first MPPI bringup, neither caused by the controller switch, both exposed by it.** (1) `bt_navigator.wait_for_service_timeout` was `5` — the unit is milliseconds, not seconds, so every action server was allowed 5 ms to appear on the DDS graph before bringup aborted outright (`"compute_path_to_pose" action server not available after waiting for 0.01s`), despite `planner_server` having connected with its bond ~340 ms earlier in the same log — a coin-flip against discovery latency that had simply not been lost before. Restored to Nav2's own default of `1000`. (2) `inflation_radius` (`0.35` local, `0.45` global) sat below the robot's own padded circumscribed radius (`0.622 m`), which Nav2 flagged directly at bringup as forcing full-polygon collision checks on every query rather than the cheaper potential-field shortcut — costly specifically for MPPI, which runs on the order of 10,000 footprint tests per control cycle at 20 Hz on a Pi 5 also running SLAM. Raised both to `0.65`; verified the change does not narrow any previously-passable corridor, since inflation only makes cells *lethal* within the *inscribed* radius (`0.25 m`) — beyond that it is a decaying cost tail (`93` at `0.45 m`, `34` at `0.65 m`), not a hard wall. Committed together as `ab8da80`.

**First-ever hardware motion under MPPI, both clean.** A `45°` in-place rotation: `SUCCEEDED`, zero recoveries, centre moved only `8.5 mm` during the turn — the direct, hardware-measured counter-example to every DWB rotation failure this branch has logged. A `0.30 m` straight translation: `SUCCEEDED`, heading held to `0.7°`, cross-track drift `1.7 cm`. Map grew `846→1870→2964` cells across the session, each jump landing on a translation, the same §17.20 mechanism observed again. No `Control loop missed its desired rate` at `batch_size 500` across either run — the Pi 5 held 20 Hz with footprint collision-checking on.

**A real, quantified finding from these same two runs: `SimpleGoalChecker`'s `0.05 m`/`0.05 rad` tolerance was being returned as systematic error, not noise.** Both the `0.30 m` and an also-run `0.50 m` translation stopped `4.5-4.6 cm` short of goal — at the tolerance boundary, not near it — and the rotation stopped `2.80°` short against a `2.86°` tolerance. Root cause stated plainly: MPPI is a pure cost-minimiser with no term rewarding "closer than required," so `SimpleGoalChecker` accepting a pose is what actually decides how close the robot gets. Tightened to `0.02 m`/`0.025 rad` (`c6a986e`) — chosen from the same runs' demonstrated capability (`0.7°` heading hold, `1.7 cm` cross-track, `8.5 mm` rotation-centre drift), not aspirationally.

## 17.24 19 Aug 2026: a repeatability-test tool built for the user's APS data, and a real goal-preemption bug found and fixed in both scripts that share the pattern

Same extended session, continued. The user asked for repeated, tape-measured out-and-back trials in all four body-frame directions, for figures to present in an academic progress seminar — `tools/repeatability_test.py` added (`db93cb3`), built from `zero_point_scan.py`'s already-hardware-validated `send_goal_and_wait`/TF/lock-file pieces rather than new logic. Per-direction default distances and a hard `SAFE_MAX` ceiling (refuses without `--force`) set from the §17.23 clearance figures: right/front `1.00 m` (large margin), left/rear `0.35 m` (tight, conservative under their `~0.75 m`/`~1.07 m` ceilings).

**First hardware run (`--side right`) produced motion the user accurately described as "very very random": back, then left, then front, diagonal, then right.** Traced to source via exact log timestamps, not guessed. The outbound goal `(0,0)→(0,-1.00)` was sent at `t0`; the script's `send_goal_and_wait` gave up waiting at its hardcoded `20 s` client-side timeout (`t0+20.0s`) and reported the leg `FAILED`; the user, reading the tape-measurement prompt, took roughly 25 s to respond; the script then sent the RETURN goal at `t0+45.5s` — and `bt_navigator`'s own log shows the goal actually **still executing at that moment**, having reached `(0.10, -0.65)` under its own power: `"Begin navigating from current location (0.10, -0.65) to (0.00, 0.00)"`. `NavigateToPose` keeps exactly one active goal, so the second send **preempted the first mid-drive**, from an intermediate pose neither goal's own logic expected. The first goal, left alone, would have succeeded on its own: `Reached the goal!` fired at `t0+87.4s`, safely, no E-stop. **The randomness was two goals racing on one controller because the client gave up without ever cancelling the goal it gave up on — not a hardware fault, not an MPPI defect.** Separately and honestly recorded: the underlying `87.4 s` completion time for a nominal `1.00 m` strafe is itself unexplained — four `PoseProgressChecker` "Failed to make progress" events at a suspiciously exact `~10.2-10.4 s` cadence (`movement_time_allowance`'s own default), one automatic `Spin` recovery, and repeated `Control loop missed its desired rate` warnings (dropping as low as `5.46 Hz`) coinciding with each costmap-clear-and-replan cycle — plausibly Pi-5 CPU contention during recovery bursts, plausibly a moving-target problem from the global planner re-publishing a shifted path each cycle as the live map grew, not distinguished from each other this session. Left open, explicitly separate from the bug above.

**Fix: `send_goal_and_wait` now explicitly cancels the goal it is giving up on, in both scripts that carry this exact function** — `repeatability_test.py` and, proactively, `zero_point_scan.py`, which has the identical latent flaw and has simply not been running long enough per goal to expose it yet. On a client-side timeout, `goal_handle.cancel_goal_async()` is now called and waited on before the function returns `False`, guaranteeing no goal is ever left alive for a subsequent call to collide with. `repeatability_test.py`'s per-goal timeout also raised from the old `20 s` default to `150 s` (`--goal-timeout`, overridable), directly justified by the `87.4 s` real completion time measured this session — the old default was not merely unlucky, it was structurally too short for any goal near `1 m` under real recovery load.

**Robot state at the point of interruption not independently re-confirmed before this was written up** — the run was Ctrl-C'd, Nav2's own lifecycle shutdown logged a clean deactivation of every node including `velocity_smoother` (which should stop `cmd_vel`), but the robot's final resting position relative to the zero mark is not yet verified against a fresh `ps aux` + TF read. **Explicit next step, ahead of any further motion: confirm hardware state, re-zero at the physical mark, then re-run `repeatability_test.py --side right` with the fix in place**, small first, same discipline as every new capability on this branch — the fixed script has not yet had a single hardware confirmation of its own.

## 17.25 19 Aug 2026: a second, more serious hardware failure — SLAM and the LiDAR pipeline killed outright by CPU starvation mid-recovery, and a first real loop-closure tuning pass

Same extended session, continued. A second `trajectory_viz.py` hardware run — a fresh, structurally different failure from §17.24's goal-preemption bug, not a repeat of it. The user: "i had to press ctrl+C because it collided and it wasnt even moving in a straight line but randomly." Diagnosed from the Nav2 terminal log's own timestamps, not from the symptom description alone.

**Root cause: the LiDAR scan and `slam_toolbox` stopped publishing simultaneously at `t≈254s`, and Nav2 kept commanding motion anyway.** Every `collision_monitor` "Latest source and current... differ" warning from that point on carries the identical frozen timestamp `1787138254.027` while wall-clock time kept advancing underneath it, and `map→odom` froze at `1787138254.140` in the same instant — one shared failure, not two independent ones. It coincided with severe, worsening CPU starvation, also directly measured from the log: the controller loop dropped from its `20 Hz` target to `6.5 Hz`, the planner loop from `5 Hz` to `1.23 Hz`, with repeated `StaticLayer: Resizing costmap` events landing in the same window — the live-growing costmap, MPPI's ~500-trajectory search, and `slam_toolbox`'s scan matching all competing for one Pi 5's CPU, worse than any earlier session because the map itself had grown larger. `bt_navigator` logged `"Robot pose is not available"` while mid-`Spin` recovery at the exact moment of the freeze — Nav2 was driving completely blind during a rotation, which is what the erratic motion and the collision actually were, not a planner defect.

**Separately, the same run's own numbers confirmed a genuine loop-closure failure, not just a performance one.** The recorded HOME pose was `(0.5033, −0.0445)` despite the user confirming the robot was physically parked on the zero mark at start — roughly half a metre of odometry drift that loop closure should have caught and never did. Checked against `slam_nodom.yaml` as it stood at the time: it ran entirely on `slam_toolbox`'s stock defaults for every loop-closure and scan-matcher parameter — nobody had ever set any of them for this robot's actual conditions.

**Fix, not yet hardware-tested: a real loop-closure/scan-matcher tuning block added to `system/slam_nodom.yaml` (`635e4b6`)**, every value justified against a specific measured number from this project's own history rather than copied from a tutorial: `loop_match_minimum_chain_size` `10→5` and `loop_search_maximum_distance` `3.0→5.0` m (a search radius must exceed the drift it's meant to correct, and `0.5` m was measured this run), `loop_match_minimum_response_coarse`/`fine` relaxed `0.35/0.45→0.25/0.35` (107 of 430 beams are permanently masked NaN behind the mast per §17.15 — a quarter of every scan absent means a genuine revisit legitimately scores lower than stock thresholds expect), `correlation_search_space_dimension` `0.5→0.7` m and `distance_variance_penalty`/`angle_variance_penalty` `0.5/1.0→0.7/1.2` (trusting the odometry prior less, since §17.21 already found it over-reports strafe by up to 25% before the `lateral_scale` correction, which is itself an empirical single-floor constant, not a model). `enable_interactive_mode` also turned off — extra live state on a Pi that just ran out of CPU and killed a node outright is a cost with no benefit here.

**Advice given and recorded, not yet acted on this session:** go back to Phase 1's original no-SLAM, no-Nav2, pure-manual-plus-tape-measure test as the cleanest remaining data source; and, longer-term, the CPU contention and the "map recenters every correction" behaviour the user separately flagged (below) are both symptoms of the same architectural choice — live SLAM-while-navigating — and both are addressed by moving to map-once-then-freeze-and-localize instead of trying to tune contention away.

**The user's own mental model, checked and confirmed correct.** Shown a Foxglove screenshot of the map appearing to jump, the user asked directly: should the zero point be fixed no matter what, with the robot moving relative to it and the map only ever growing around it, never recentring — "that is the correct way to think right? I might be wrong." Confirmed: yes, and the `(0.5033, −0.0445)` reading on a robot physically parked on the mark is a real defect by that standard, not a quirk to get used to. Explained in plain terms (REP-105's `odom`-never-jumps-but-drifts vs `map`-jumps-on-correction-but-stays-globally-accurate split) that the recentring itself is `map→odom` being corrected by loop closure working as designed — the defect is that closure wasn't firing at all, not that it exists. Getting fixed-origin, smooth motion, and global accuracy simultaneously needs the map-once-then-freeze workflow, since live correction inherently trades off exactly one of those three.

## 17.26 19 Aug 2026: three tutorial video scripts read against this project's actual architecture, a real missing manual-override safety layer found and fixed, and `navigation.launch.py` rewritten before its first-ever run could hit two already-known bugs

New turn, same branch. The user said "I think I will start from scratch again" and supplied transcripts of three tutorial videos on SLAM Toolbox and Nav2 (Kai Nakamura's overview, and two longer ROS 2-focused walkthroughs). Rather than guess how much of "from scratch" to take literally against branch work that already has real hardware validation behind it (MPPI tuning, costmap inflation math, goal tolerances), asked directly: keep the validated tuning and add what the scripts show is actually missing, or rebuild the SLAM/Nav2 layer from the ground up? User chose the former.

Read the three scripts against the real repo rather than assuming they applied wholesale. Two things checked and found NOT to need work:

- **`base_footprint`** — the scripts' recommended Z=0 projection frame for 2D SLAM. Already exists in `aislebot.urdf`, rigidly offset from `base_link` by exactly `−0.0762` m (the wheel radius) with zero rotation, and already predates this session. Deliberately left every `base_frame`/`robot_base_frame` parameter (`slam_nodom.yaml`, `nav2_params.yaml`'s AMCL/costmap/bt_navigator blocks) on `base_link` rather than switching to match the tutorials: for a ground robot that never moves in Z, the transform between the two is a constant offset with no rotation, so the switch would be pure churn across already-validated files for zero functional difference in the X-Y plane every one of these components actually reasons about.

Two things checked and found to be **real, previously-undiscovered gaps**:

1. **No manual-override arbitration existed at all.** Three independent nodes — `joy_to_aislebot.py`, `phone_dashboard.py`, and the dev-only `keyboard_teleop.py` — all published straight to `/cmd_vel`, and so did `cmd_vel_axis_adapter.py` whenever Nav2 was running. No priority, no timeout, nothing — exactly the "Option 1: Direct Topic Remapping... messy, no explicit priority" anti-pattern the Nav2 script names and rejects in favour of `twist_mux`. This is not hypothetical: it is a direct contributor to why §17.25's SLAM-crash collision was harder to interrupt than it should have been — there was no clean, reliable way to grab the wheels back from a blind, CPU-starved Nav2 mid-drive.

   **Fix (`bd4fb1a`):** all three manual publishers now target `/cmd_vel_manual`; `cmd_vel_axis_adapter`'s Nav2 output (in both `nav2_slam.launch.py` and the rewritten `navigation.launch.py` below) now targets `/cmd_vel_nav_out` instead of `/cmd_vel` directly. A new `twist_mux` node, config in `config/twist_mux.yaml` (manual priority `100`, nav priority `10`, both `0.5` s timeouts), arbitrates the two onto `/cmd_vel` — the one topic `teleop_asym` has always consumed, itself untouched. Runs unconditionally inside `aislebot_full.launch.py`, so manual override exists whether or not Nav2 happens to be up. Not yet hardware-confirmed: `twist_mux` needs installing on the Pi (`ros-<distro>-twist-mux`) before this can even come up.

2. **`navigation.launch.py` — the map-once-then-AMCL "finished map" mode — had never been run, and carried two bugs that its first real run would have hit immediately.** It previously just included stock `nav2_bringup bringup_launch.py`, which chains in `navigation_launch.py` and on this Nav2 build starts `route_server` and `opennav_docking` — neither of which this robot has, and `docking_server`'s refusal to configure is the exact all-or-nothing lifecycle failure `nav2_slam.launch.py` already hit and fixed by going to explicit nodes (§17.17). It also never got the `cmd_vel_axis_adapter`/`collision_monitor` rewiring `nav2_slam.launch.py` needed — a stock bringup writes velocity straight to `/cmd_vel` in `base_link`'s TF axes, the exact 90° misdirection that sent the first-ever autonomous goal `0.956` m sideways (§17.19). Both bugs were latent rather than found on hardware, because the file had simply never been exercised — no saved map has existed to run it against.

   **Fix: rewritten as an explicit-node launch file (`bd4fb1a`), mirroring `nav2_slam.launch.py`'s already-validated node list** — same `controller_server`/`smoother_server`/`planner_server`/`behavior_server`/`velocity_smoother`/`collision_monitor`/`bt_navigator`/`waypoint_follower`/`cmd_vel_axis_adapter`/`goal_pose_adapter` remapping chain, verbatim — with `map_server` and `amcl` substituted for the externally-running `slam_toolbox` as the localization source, both already fully configured in `nav2_params.yaml`'s `amcl:`/`map_server:` blocks (written in an earlier session, annotated "this block has never been run," and correct on inspection — the `yaw: -1.5708` initial pose already accounts for this robot's non-REP-103 axis convention). `map` is now a required launch argument with no default, on the theory that navigating on the wrong map or no map is worse than refusing to launch.

**Nothing in this entry has hardware confirmation.** Both fixes are code-complete and reviewed against the existing, hardware-validated `nav2_slam.launch.py` pattern, but neither `twist_mux` nor `navigation.launch.py` has been run once. The prerequisite chain, in order: install `twist_mux` on the Pi; complete a full SLAM-only mapping drive with §17.25's loop-closure tuning and confirm the return-to-zero-mark error numerically; save that map; stop `slam_toolbox`; only then does `navigation.launch.py` have a map to load.

## 17.27 19 Aug 2026: first hardware confirmation of the §17.25 loop-closure tuning — 50 cm drift down to 2 cm

Same session, continued, directly executing the prerequisite chain §17.26 just laid out. `aislebot.service` restarted on the physical zero mark (odometry and `map`'s origin both zero there by construction), then a controlled single-variable test rather than the full wall-hugging drive: rotate ~90° CW in place, drive straight out to just under 2 m, drive straight back (in reverse, same heading, not a U-turn), then rotate back to the original heading at the mark. `zero_point → base_link` read continuously throughout via `tf2_echo` and Foxglove (Fixed Frame = `zero_point`, Grid layer, `trajectory_viz.py --no-reference --map-frame zero_point` running the whole time — the first real use of both the Foxglove setup and the tool as actually intended).

**Final reading: translation `(-0.011, 0.017)` m — magnitude ≈ 2.0 cm — rotation `-0.17°`.** Direct, dramatic improvement over §17.25's uncorrected `(0.5033, -0.0445)` (≈ 50 cm) measured on the same physical setup before the loop-closure/scan-matcher tuning (`635e4b6`) existed. This is the first time that tuning has touched hardware, and the result is a clean pass against the acceptance test both this project and the user independently arrived at ("drive anywhere, return to the mark, read zero").

**The log itself shows loop closure actually firing, not just a good final number.** Several single-sample step-changes in the continuous `tf2_echo` trace (e.g. `x: 1.977→1.727` at one sample, `1.597→1.407`-ish shortly after) are far larger than the robot's physical speed allows in one control period — these are `map→odom` being corrected by scan-matching recognizing revisited territory, exactly the REP-105 mechanism described to the user earlier this session. The corrections cluster tighter and land the estimate closer to truth as the robot re-approaches the origin, which is the signature of loop closure working as intended rather than noise.

**One thing intentionally left open rather than assumed:** the trace contains two long flat stretches (~35 s around the midpoint, ~50 s at the very end) of bit-identical repeated samples — the same signature §17.25's CPU-starvation freeze produced. Given the run completed cleanly and resumed normal motion immediately after the first stretch, the far more likely explanation is the robot was simply parked/paused there rather than mid-freeze, but this was not independently confirmed against `ps aux`/CPU load at the time, so it is recorded as probable rather than certain.

**Immediate next steps, now unblocked:** the full wall-hugging mapping drive (richer test of loop closure over a longer, revisit-after-exploring path rather than this short controlled out-and-back), then save the map, then the first real run of `navigation.launch.py` + `twist_mux` — both of which reached this session with zero hardware confirmation and now have a working SLAM foundation to build on.

## 17.28 19 Aug 2026: repeated large pose jumps on the very next drive — perceptual aliasing suspected, not yet confirmed against a log

Same session, immediately after §17.27's clean result. A second drive — straight forward only, no rotation commanded — produced four Foxglove screenshots showing the `map` rendering held rock-solid (Fixed Frame = `zero_point`, as intended) while the robot's own displayed pose swung repeatedly through large, inconsistent positions and headings, unlike anything in the clean run minutes earlier. The user asked directly what this is called and flagged, correctly, that no configuration had changed between the two runs.

**Named and distinguished from the benign mechanism §17.27 just demonstrated.** A single clean correction that tightens toward truth (§17.27) is loop closure working. *Repeated, large, seemingly directionless* pose swings while commanding pure forward motion is a different thing: **perceptual aliasing** — the scan matcher finding a spurious, high-confidence-looking match against a *different* previously-seen location because the two look similar in this environment — producing incorrectly-accepted loop closures that snap the pose estimate to the wrong belief, repeatedly. The rendering is not the bug; a held-fixed map with a jumping robot pose is exactly what an unstable `map→odom` correction looks like when watched from a frame that stays put.

**Working hypothesis for why this run and not the last one, despite identical config:** the config was never the variable between the two runs — it was already changed once, by §17.25's tuning, before *either* run happened. Two of those changes specifically lowered the bar for accepting a match as a genuine revisit: `loop_match_minimum_chain_size` (`10→5`) and `loop_match_minimum_response_coarse`/`_fine` (`0.35/0.45→0.25/0.35`). Loosening those was the correct response to §17.25's problem (closures not firing at all), but the same loosening trades missed-closures for false-positive ones — and this robot's own mapped space (a corridor junction with radiating aisles, previously flagged in §17.13/§17.15 as visually self-similar) is exactly the kind of environment where that trade bites. This is a coherent, source-grounded hypothesis, not yet a confirmed diagnosis.

**Deliberately not acted on yet.** Changing loop-closure parameters again without evidence would repeat the exact mistake being diagnosed — tuning by guess rather than by measurement. Recommended immediate action, not yet taken: stop driving until confirmed one way or the other, then capture `slam_toolbox`'s own terminal log (loop-closure candidate/accept/reject messages) correlated by timestamp against the jump events, to see directly whether a bad match is what's firing. `tools/trajectory_viz.py` gained an `epoch_s` column in its CSV output specifically to make that correlation possible (wall-clock, the same clock ROS 2's console logs use — the tool previously only recorded time-since-start, which can't be lined up against a separate log file).

## 17.29 20 Aug 2026: a real `trajectory_viz.py` crash found and fixed, one pose jump captured with full instrumentation, and a decisive finding that this `slam_toolbox` build has no observable loop-closure signal at all

New session, same branch, executing §17.28's plan: capture the SLAM terminal log and the trajectory recorder side by side during a drive, correlate a jump by `epoch_s`, and check whether a bad loop-closure match is what's firing. Walked hands-on-hardware, one command at a time, the user pasting every output rather than any step being assumed to have succeeded.

**A real bug found in `trajectory_viz.py` itself, costing one full run's data.** The first hardware run (`slam_test_01`, an out-and-back drive) hit Ctrl-C and crashed instead of printing a summary: `ValueError: too many values to unpack (expected 4)` in `_leg_stats`'s `for (t, x, y, _) in samples` loop. Root cause: adding the `epoch_s` column (§17.28) made every recorded sample a 5-tuple, but `_leg_stats` — used by both the `--no-reference` summary path and `_print_leg` — was never updated to match. Because the crash happened before the CSV-write step, this run's 827 s / 7117-sample trajectory was lost entirely, not merely unsummarized. Fixed (`8e943fc`): the unpacking now takes `(t, x, y, _yaw, _epoch)`, verified against simulated 5-tuple samples before pushing. A second, unrelated hardware run (`slam_test_02`) confirmed the fix — full summary printed and CSV written cleanly on Ctrl-C.

**`tools/bag_tf_diff.py` added (`d2e0f10`)** — reads any one TF parent/child pair's correction history straight out of a `ros2 bag`, collapsing the 50 Hz republish noise (`transform_publish_period: 0.02` in `slam_nodom.yaml` re-sends the current value regardless of whether it changed) down to only genuine value changes, each with its epoch timestamp. Built because a rosbag running alongside the SLAM log gives a second, quantitative channel independent of both the crashed recorder and the console log — `/tf`, `/scan`, `/scan_reliable`, `/wheel_odom`, `/cmd_vel`, `/pose` recorded (deliberately not `/map`/`/map_metadata`, the heaviest topic, learning directly from §17.25's CPU-starvation crash).

**First redrive (`slam_test_01`) reproduced nothing — and for a structurally sound reason, not a wasted attempt.** Run against `--parent map --child odom`: only 11 distinct corrections in 885 s, every one under 4.2 cm / 2.4°, tracing a smooth out-and-back shape — ordinary healthy correction, nothing resembling §17.28. A separate check against `--parent odom --child base_link` explained an 11-minute stretch of zero correction at the start as the robot genuinely sitting still (matches the "significant latency" the user reported), not a stall. Consistent with the hypothesis floated before driving: this session's map was still nearly empty, and perceptual aliasing needs prior mapped territory to falsely match against, which this run structurally could not provide.

**Second drive, over the same ground a second time, reproduced it — with full data.** `bag_tf_diff.py`'s awk-equivalent scan of the recorder's CSV found exactly one large single-sample step: **25.5 cm / 2.41° at epoch `1787233020.150` (19:07:00.150 IST, t=130.95 s into the recording)** — visually confirmed in a Foxglove screenshot showing the robot's rendered pose sitting off its own recorded path while the map stayed fixed, the same signature named in §17.28. Both the SLAM log (tee'd) and a rosbag (`slam_test_02`) fully cover this timestamp.

**Grepping the log for it came back empty — and traced to a real, decisive architectural finding, not a search failure.** Checked slam_toolbox's actual source rather than assume: the automatic loop-closure candidate evaluation (`COARSE RESPONSE`/`FINE RESPONSE`/`REJECTED!`) fires through a custom `FireLoopClosureCheck` callback in the bundled Karto matching library, not any `RCLCPP_*` logging macro — confirmed against **the exact installed version** (`ros-jazzy-slam-toolbox 2.8.5-1noble.20260614.104642`, checked via `apt-cache policy` after an initial check against the wrong ref, GitHub's `ros2` branch HEAD, gave a materially different and misleading answer). At `2.8.5`, `slam_toolbox_common.cpp` registers **no listener at all** for these events — only `LoopClosureAssistant`, which handles manual/interactive RViz-drag closures, unrelated to the automatic case. `ros2 topic list -t | grep slam_toolbox` on the live node confirms it directly: `/slam_toolbox/loop_closure_event` (the topic a newer slam_toolbox version does publish accepted closures on) **does not exist on this build** — only `feedback`, `graph_visualization`, `scan_visualization`, `transition_event`, `update`. **This build has no observable signal, console or topic, for whether an automatic loop closure was accepted or rejected.** Not a logging-verbosity problem (the launch already runs at `INFO`, and the relevant calls aren't wired to the logger regardless of level) and not fixable by searching harder — confirmed against the actual running node's own topic list, not just the source. A real, useful negative result: any future session on this exact install can skip straight past console-log/topic instrumentation for this question.

**Plan pivoted, not abandoned, before the session closed for the night.** Since the direct "closure accepted: yes/no" signal doesn't exist, the fallback is judging plausibility indirectly — comparing the jump's `map→odom` correction against `odom→base_link` over the same window (physically sensible correction vs. inconsistent snap), using `bag_tf_diff.py` against `slam_test_02`, which already fully covers the jump's timestamp. **Not yet run.** A second, separate jump happened later the same drive, on the return leg, with neither the recorder nor the bag running — only the SLAM log, which we now know can't help pinpoint or diagnose it regardless. That second jump has no analysable data and is not part of the evidence above.

**Also found along the way, not yet acted on:** `phone_dashboard.py`'s Map button (`start_mapping()`) launches `mapping_full.launch.py` with `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` — by design for normal use, but it would have silently discarded the exact log capture this whole session's diagnostic depends on had it been used instead of a manual tee'd terminal. Worth a comment in that method for the next person reading it, not yet added.

## 17.30 21 Aug 2026: the recovery-event anomaly resolved, two independent pure-lateral round trips, and a session-cold-start pattern that reframes the whole investigation

New session, same day, same branch, continuing directly from the forward/back validation and lateral-drift framing recorded in `Next_Session_Kickoff.md`: a hardware-confirmed 0.5m forward-and-return round trip had already converged on ~1.2cm net error from three independent measurements (TF math, tape measure, `trajectory_viz.py`'s own summary), leaving the same round trip's 1-3cm lateral offset as the day's open question. Walked hands-on-hardware exactly as before, one command at a time.

**The stray `number_of_recoveries: 1` from that morning return leg, closed.** Grepping `bt_navigator`'s runtime lines (filtering out startup boilerplate) against the exact epoch window of the return leg found no explicit "recovery" text anywhere — the same silent-subsystem pattern §17.29 already found for loop closures — but a raw, unfiltered dump of every node's output in that window caught the real event directly: at epoch `1787316266.158`, ~10.0s into the leg, `controller_server` logged `Failed to make progress`, aborted `FollowPath`, and `local_costmap` received a `clear entirely` request before the controller retried and finished 6.4s later. This is `nav2_controller::PoseProgressChecker`'s ~10s `movement_time_allowance` firing, not a `behavior_server` Spin/BackUp recovery — a different code path than the one originally suspected, which is why the earlier grep for Spin/BackUp activity came back empty.

**A pure-lateral round-trip test (`nav_goal.py --forward 0.0 --right 0.5`, then its printed return) reproduced the same mechanism live, and explained a genuinely confusing visual artefact.** The first attempt showed 3 separate `Failed to make progress` stalls on the outbound (right) leg, each ~10s apart, each triggering a costmap clear and a fresh replan from wherever the robot then was — and Foxglove's rendered path for that leg showed a visible bend, exactly what chaining 4 distinct straight-ish replanned segments launched from slightly different start poses would produce. Not one curved plan; several straight ones stitched together after repeated stalls.

**Repeating the identical test end-to-end a second time, from a fresh Nav2 bringup, produced a full 4-leg dataset that reframes the investigation.** Both attempts' final resting error landed in the same tight band (1.97-1.99cm) regardless of recovery count — 0, 1, or 3 — which is `SimpleGoalChecker`'s tuned 0.02m tolerance (§17.23) doing exactly what it's configured to do, not a drift signature. The recovery count itself formed a clear pattern across the two independent sessions: 3 → 1 → 1 → 0, worst on the first lateral goal sent after each fresh bringup, best on the following one in the same session. Two candidate explanations, not distinguished by this data: mecanum-roller stiction/backlash being higher on a cold first lateral push (a fundamentally less direct force path than forward rolling, which has never shown this pattern in this project's history) vs. an MPPI/local-costmap warm-up effect. `trajectory_viz.py`'s own summary of the second round trip's whole session gave a net round-trip displacement of 1.63cm — the same tier as the already-validated forward/back benchmark's 1.22cm. **Conclusion: pure lateral motion, tested in isolation, is just as accurate as forward motion.** This reframes the original open question — the 1-3cm side-drift observed after a *forward* move is therefore more likely a side effect of the forward-motion command path itself (an unintended small lateral component in the wheel-speed solution, or a heading-hold correction netting out sideways) than evidence the lateral axis is inherently imprecise. Not yet tested directly.

Session paused with the environment intentionally left as-is (no re-zero, no terminal restart) for a fourth, compound test — forward 1m / back 1m / right 1m / return to the fixed zero mark — requested as a final check before moving on to the next build-order step.

## 17.31 21 Aug 2026 (late): the compound test's fourth leg fails outright, Foxglove click-to-goal finally reached, and the strongest perceptual-aliasing dataset this project has ever captured

Same session continued to its end. Three distinct things happened, and the third is the one that matters.

**The compound four-waypoint test ran, and its fourth leg failed in a way no earlier leg ever has.** Sent as a single `FollowWaypoints` action (four `NavigateToPose` goals chained inside one call, so per-leg behaviour is identical to sending them individually). Leg 1 (forward 1 m) took ~44.6 s with 2 progress-checker stalls; leg 2 (return to start) ~31.9 s, clean, zero stalls; leg 3 (right 1 m) ~61.1 s, 1 stall; **leg 4 (return to the fixed zero mark) ran ≥103 s, logged 5 separate `Failed to make progress` stalls, escalated to a `Spin` recovery that timed out before completing its 1.57 rad (`Exceeded time allowance before reaching the Spin goal`), then to a `BackUp`/`DriveOnHeading` recovery that also timed out — and the captured log ends mid-leg with no `Reached the goal!` line at all.** A `collision_monitor` proximity pair (`Robot to approach for 1.200000 seconds away from collision` → `Robot to continue normal operation`) fired inside the failed `Spin` window. **This is the first time in this project's history that a `behavior_server` recovery behaviour has been observed failing**, as opposed to the `PoseProgressChecker` path §17.30 root-caused. The diagnostic weight is in the comparison, not the failure: **legs 2 and 4 target the same pose.** Leg 2 reached it clean; leg 4 could not. Same goal, same tolerances, same goal checker — so this is not a goal-tolerance problem, it is a problem with the state the stack was in by leg 4. Two non-exclusive candidates, neither confirmed: session-late performance decay (`global_costmap` had grown to 133×201 cells and `planner_server` logged `Planner loop missed its desired rate of 5.0000 Hz. Current loop rate is 1.4277 Hz` — a 3.5× miss, which starves the ~10 s `movement_time_allowance` window), and leg 3's endpoint leaving the robot without clearance to rotate in place (consistent with `Spin` specifically failing alongside a `collision_monitor` approach event).

**Foxglove click-to-goal reached a working state for the first time, and the path there is worth recording because none of it is discoverable.** `goal_pose_adapter` has existed since §17.20 but had never actually been driven from the Foxglove UI. Three separate things had to line up, each of which silently does nothing when wrong: the 3D panel's **Publish** settings section (below Topics and Custom layers, not part of the topic list) has *three independent tools with three independent topic fields* — the one that sends a goal is **"2D pose (geometry_msgs/PoseStamped)"**, not "2D pose estimate" (`/initialpose`) and not "2D point" (`/clicked_point`); its topic field is free text with no dropdown, so `/goal_pose_click` must be typed exactly; and the tool must then be *selected* from the toolbar flyout, since the toolbar defaults to the point tool, which publishes a position-only `PointStamped` that Nav2 ignores entirely. Clicking with the wrong tool armed produces a yellow dot on the map and no motion and no error anywhere — indistinguishable from a broken stack. Recorded here and in `Important_Commands.md` so this costs nobody a session again.

**A full clean restart was performed and verified**, per the §8 re-zero procedure: robot parked on the mark, `aislebot.service` restarted, `tf2_echo odom base_link` confirmed `[0,0,0] @ -90.000°`, `mapping_full.launch.py` brought up clean (LiDAR connected, SLAM activated), `tf2_echo map base_link` also `[0,0,0] @ -90.000°`, then `nav2_slam.launch.py` to `Managed nodes are active` with no errors. A known-good baseline, deliberately left running.

**The finding that matters: a 4,818-sample trajectory recording that is the strongest evidence for §17.28's perceptual-aliasing hypothesis this project has produced.** `trajectory_viz.py --no-reference --map-frame map`, 525.88 s starting 20:36:49 (epoch `1787324283.385`), covering a drive made *before* the restart above. Re-derived independently from the raw CSV rather than taken from the recorder's own summary, and the two agree exactly:

| Quantity | Value |
|---|---|
| Samples / duration | 4818 / 525.88 s (~9.2 Hz) |
| Active motion window | t = 45.6 s → 329.05 s (283.4 s; the remaining 196 s is a stationary tail) |
| Start → end | `(0.0000, 0.0000) @ -90.00°` → `(0.0917, 0.0652) @ -87.51°` |
| Net displacement | **0.1125 m** |
| Total path length | 10.9977 m |
| Single-sample steps > 5 cm | **16**, summing 3.0359 m — **27.6 % of the entire reported path** |
| Single-sample steps > 10 cm | 11, summing 2.6458 m (24.1 %) |
| Largest single step | **0.3109 m in one 0.10 s sample** (t = 316.78 s) |

An 0.31 m step in 0.10 s is an apparent 3.1 m/s. `MAX_LINEAR_SPEED` in `phone_dashboard.py` is 0.15 m/s and the kinematics cap is 0.48 m/s, so this is roughly 6–20× anything the chassis can physically do. **These are pose corrections, not motion.** Four structural properties, none of which ordinary sensor noise produces, and all of which a pose-graph re-solve does:

1. **Every jump carries a simultaneous heading change.** 14 samples exceed 2° in one tick, 7 exceed 5°, one hits 12.80°. A translation-only glitch does not systematically rotate; a rigid-body graph correction necessarily does.
2. **The jump directions are bimodal, not uniform.** Early events head roughly +28° to +93°; late events roughly −38° to −143°. The estimate is being pulled back and forth between two competing alignments — the signature of matching against a *wrong but plausible* prior location, which is precisely what perceptual aliasing means.
3. **Magnitude grows monotonically over the run**, ~0.06–0.10 m early to 0.25–0.31 m late, consistent with accumulating drift being snapped back by progressively larger corrections as more map exists to falsely match against.
4. **Two doublets** — corrections 0.10 s apart at t = 155.02 s and t = 252.96 s. The graph re-solving twice in immediate succession is pose-graph behaviour; noise does not do this.

Inter-event spacing is ~10–32 s, i.e. roughly one correction per ~18 s of driving. **This is the third independent reproduction** (§17.28 observed, §17.29 captured one 25.5 cm event with instrumentation), and the first with enough events to characterise the phenomenon statistically rather than anecdotally.

**⚠ CORRECTED 22 Aug 2026 — the paragraph immediately below is wrong, and §17.32 explains why.** `system/slam_nodom.yaml`'s §17.25 tuning was committed on 19 Aug and **never reached the robot**: `install.sh:228` is the only mechanism that copies it to `~/ros2_ws/slam_nodom.yaml`, and the Pi's copy dated from 26 June. Every drive from 19–21 Aug therefore ran on `slam_toolbox` **stock defaults**, which are *stricter* than §17.25's values, not looser. The observations recorded in this section are sound and reproduced; the attribution below — that §17.25's relaxation caused them — is reasoning about parameters that were never active, and is retracted. What actually caused the jumps remains open. Kept unedited below rather than deleted, because the reasoning was correct given what was known and the failure was one of verification, not logic: **a value in the repo is not a value on the robot.** Verify deployed config with `ros2 param get` against the live node, never by reading a file.

**Read against `system/slam_nodom.yaml`, the mechanism is no longer mysterious.** §17.25 deliberately relaxed exactly the parameters that gate loop-closure acceptance — `loop_match_minimum_response_coarse` `0.35→0.25`, `..._fine` `0.45→0.35`, `loop_match_minimum_chain_size` `10→5`, `loop_search_maximum_distance` `3.0→5.0` — and simultaneously raised `distance_variance_penalty`/`angle_variance_penalty` (`0.5/1.0→0.7/1.2`), which *reduces* how much the odometry prior can veto a scan match. That was the correct call at the time and it worked (§17.27: 50 cm → 2 cm). But it removes the two mechanisms that reject a wrong closure, in an environment §17.13 already characterised as a junction of several similar-looking radiating aisles, with 107 of 430 beams permanently masked (§17.15). The file's own comment block anticipated this outcome in writing: *"If the map ever visibly folds or tears, these two are the first thing to raise back, before anything else in this file."* **This dataset is that condition arriving.** The tuning is not wrong; it is over-relaxed, and the correct response is a middle setting plus the structural change below — not a revert to the stock values that produced 50 cm of uncorrected drift.

**The strategic reframe, which is the most important paragraph in this entry.** The instinct is to treat these jumps as a blocker on autonomous navigation. They are not, because `slam_toolbox` is not what the product navigates on. `Production_Architecture.md` §3.1 already established that named locations require a *saved* map with `map_server` + AMCL, precisely because live SLAM re-anchors its origin every session — and in that architecture `slam_toolbox` is not running at all during the Operate phase. AMCL also corrects `map→odom`, but it is a particle filter localising against a **fixed** map; it never retroactively re-optimises a pose graph, which is the specific mechanism producing these jumps. **So live-SLAM jump behaviour does not need to be made perfect. It needs to be made good enough to build one clean map, once.** That is a dramatically narrower and more achievable goal than "make live-SLAM navigation reliable", and it is the goal the next session should actually pursue. Everything about today's compound-test failure is consistent with this too: chaining four goals through a live-SLAM pose estimate that snaps every ~18 s is asking the progress checker to track a target that keeps moving underneath it.

**One suspected pre-flight bug found by reading, not running, and not yet verified.** `nav2_params.yaml`'s `amcl` block sets `robot_model_type: "omnidirectional"`. On Nav2 Jazzy (this install — `ros-jazzy-slam-toolbox 2.8.5` per §17.29) `robot_model_type` is loaded as a **pluginlib class name**, and the expected value is `"nav2_amcl::OmniMotionModel"`; the bare `differential`/`omnidirectional` strings are the pre-Galactic form. If that is right, AMCL will fail to configure on its first-ever launch. The `amcl` block has never been run once, so this has never had a chance to surface. Flagged rather than changed blind — one command settles it, and it is listed in the next session's pre-flight.

**Also found by reading, and a real trap for the dashboard work:** `src/mecanum_robot/resource/dashboard.html` is installed by `setup.py` as a data file but is **never read by anything**. The page actually served is the `DASHBOARD_HTML` string constant at `phone_dashboard.py:112`, returned by the `@app.get('/')` handler. Editing `dashboard.html` produces no observable change whatsoever. Separately, `phone_dashboard.py`'s WebSocket is **client → server only** by an explicit past decision documented at its own `/calib_status` handler — there is no server → client broadcast path at all, which is the single largest piece of missing plumbing between today's dashboard and the map-rendering product described in `Production_Architecture.md` §6.2.

Full engineering plan for the next session, covering both the SLAM work and the dashboard build: `docs/Dashboard_Map_System.md`, with the session-opening checklist in `docs/Next_Session_Kickoff.md`.

## 17.32 22 Aug 2026: the §17.25 tuning was never deployed, Stage A finally run and decisive, Stage B measured, and the whole workflow moved off the terminal into the dashboard

New session, same branch, executing §17.31's plan. Walked hands-on-hardware exactly as before, one command at a time, the user pasting every output.

**The finding that reframes three journal entries: `system/slam_nodom.yaml`'s loop-closure tuning was committed on 19 Aug and never reached the robot.** The pre-flight audit the user insisted on found the Pi's `~/ros2_ws/slam_nodom.yaml` at **29 lines against the repo's 120** — no `do_loop_closing`, no `loop_match_minimum_chain_size`, no `loop_search_maximum_distance`, no response thresholds, no scan-matcher block, and `enable_interactive_mode: true` where the repo says `false`. Traced to mechanism rather than left as a mystery: `install.sh:228` is the *only* path that copies `system/slam_nodom.yaml` → `~/ros2_ws/slam_nodom.yaml`, `mapping_full.launch.py:62` loads the Pi's copy by absolute path, and that copy's mtime was **26 June 2026** — the last time `install.sh` ran. The tuning commit (`635e4b6`, 19 Aug) went to git and stopped there.

**Two journal entries have to be re-read in that light.** §17.28–§17.31's entire working hypothesis — that §17.25 *over-relaxed* the closure gate and caused false positives — was reasoning about parameters that were never active on the robot; every drive from 19–21 Aug ran `slam_toolbox` **stock defaults**, which are *stricter* than §17.25's values, not looser. And §17.27's headline result ("first hardware confirmation of the tuning — 50 cm → 2 cm") cannot have been caused by the tuning, because the tuning was not there. The obvious alternative — that §17.25's 50 cm reading came from a run whose odometry origin was set at service start rather than at the mark — does **not** fit either: the user confirms directly that the robot was physically parked on the zero mark and returned to it. **What actually produced §17.27's improvement is recorded here as an open question, not resolved.** Inventing a cause would repeat the error this entry exists to correct.

The transferable lesson, and the reason the audit caught it: **a value in the repo is not a value on the robot.** `ros2 param get` against the live node is the check that matters; reading a file is not. Restored the repo copy (verified by sha256 after a first attempt was silently mangled by terminal paste — leading whitespace eaten after every blank line, which dedented `use_scan_matching` to column 0 and would have broken the YAML nesting outright), and confirmed all seven parameters against the running node before driving.

**Stage A ran — the diagnostic §17.29 designed, §17.30 and §17.31 deferred, and `tools/bag_tf_diff.py` was built for and had never once been executed.** A 233.8 s manual drive, recorded to a rosbag, then differenced on both TF pairs:

| Pair | Messages | Distinct value changes | Behaviour |
|---|---|---|---|
| `map→odom` | 11692 | **3** | flat for 168 s, then **39.57 cm / −13.80°** in one step, then **39.00 cm / +13.80°** 12.49 s later, landing back within 0.7 cm of where it started |
| `odom→base_link` | 4676 | 787 | continuous, ~2.3 mm per tick |

The decisive part is not that `map→odom` jumped while `odom→base_link` was *generally* smooth — it is that at the exact epochs of both jumps (`…882.156` and `…894.607`–`.807`), `odom→base_link`'s per-tick delta reads `0.0020`–`0.0024` m, i.e. entirely ordinary. **Wheel odometry did not register anything at the moment the map-frame estimate moved 40 cm.** That is row 1 of the pre-committed decision tree in `Dashboard_Map_System.md` §1: SLAM pose-graph correction, not an upstream odometry or encoder fault. Three sessions of suspicion settled by one measurement, and row 2 (upstream) ruled out rather than merely thought unlikely.

**Stage B deployed and measured.** Exactly three parameters changed, kept in a separate file (`system/slam_nodom_stageB.yaml`) so the §17.27 baseline stays intact and the comparison stays attributable — `loop_search_maximum_distance` 5.0→2.0, `loop_match_minimum_chain_size` 5→8, `max_laser_range` 12.0→10.0 — verified by parsing both files that nothing else differs, and confirmed live on the running node. Two drives followed, each from a verified `[0,0,0] @ -90.000°` re-zero:

| Drive | Path | Final `map→base_link` | Single-sample steps > 10 cm |
|---|---|---|---|
| 1 — strafe out, forward, strafe out, then **reverse the same line back** | — | **(0.342, 0.121)**, 36.3 cm / 5.0° off | 9, spread across the whole run |
| 2 — a closed box, every leg over new ground | 3.4 m / 223 s | **(0.004, 0.050)**, 5.0 cm / 0.75° off | 5, **all within the last 30 s** |

Drive 1 is confounded — retracing the same track re-scans near-identical geometry from near-identical angles, which is not the single-loop case the protocol asks for — and is recorded as a failed run rather than evidence. Drive 2 is the real datapoint. Before Stage B the corrections came roughly every 18 s throughout a run (§17.31); on drive 2 the first **185 seconds had none at all**.

**A structural explanation for where the remaining five sit, offered as probable and not confirmed:** `minimum_travel_distance: 0.2` puts a pose-graph node every 20 cm, and a chain size of 8 requires 8 consecutive nodes — **≈1.6 m of driving before loop closure is eligible to fire at all**. On a 3.4 m drive that eligibility threshold lands in the back half, which is exactly where the jumps are. On that reading the clustering is eligibility, not aliasing.

**Evidence that these are correct closures rather than bad ones:** the saved map came out visibly clean — no fold, no tear, no doubled wall, no forked corridor — and the robot finished 5 cm from truth. A false closure gives neither. The radiating "flower" shape matches §17.13's characterisation of this exact junction, so it is the space, not an artefact.

**Consequence: `Dashboard_Map_System.md` §3's "no single-sample step > 10 cm" acceptance criterion is wrong as written, and is superseded.** It exists to catch bad closures, but it cannot distinguish a bad closure from a legitimate correction of accumulated drift — both trip it identically. The two criteria that actually discriminate are **map integrity** and **return-to-mark accuracy**. Step size is retained as a diagnostic. `loop_match_minimum_response_coarse`/`_fine` were **not** raised to 0.30/0.40: that lever is explicitly gated on the map visibly folding, and it did not.

**Neither of the day's maps is usable, for a reason that is purely about driving geometry.** Both test drives were open-floor boxes, deliberately chosen to remove drive-1's confound. The LiDAR swept a great deal of free space and never sat near a wall long enough to register occupied cells, so the saved grid has free space and unknown space and essentially no wall structure. The real commissioning drive still has to be run: perimeter, 0.5–1.5 m off the walls, one direction, closing at the mark.

**`docs/tools/map_viewer.html` added**, because the map-integrity check could not otherwise be performed. `telemetry_analyzer.html`'s map dropzone only unlocks *after* it loads a valid run, and it wants `phone_dashboard.py`'s 13-column motor-telemetry CSV — not `trajectory_viz.py`'s 6-column pose CSV, and not a bare map. (That pairing turns out to be intentional: the dashboard's own recording *is* the 13-column format.) The new tool takes just the `.pgm` + `.yaml` pair, parses P5/P2 PGM and `map_saver_cli`'s flat YAML entirely client-side, and was verified headless against a synthetic P5 file with a comment line in the header before being used.

**The dashboard became the workflow, at the user's direction — "I am trying to avoid use of terminal as much as possible."** Written this session, all code-complete and **none of it hardware-tested**:

- **Server → client WebSocket broadcast**, the piece §17.31 identified as the largest gap between the dashboard and the map product. ROS callbacks write plain node attributes; a single async task in FastAPI reads them on a timer and pushes — one writer, one reader, no locks, no cross-thread asyncio scheduling from a ROS callback. Pose at 10 Hz; the map at 1 Hz and only when it actually changed. The current map is also pushed directly to each newly-connected client, so a browser reload does not sit blank until the next grid arrives.
- **Live map and pose rendering** in the browser. `/map` subscribed transient-local + reliable (a default subscription on a latched topic silently receives nothing), grid shipped raw and rendered client-side. The three documented traps handled explicitly: int8 data sent as raw bytes so −1 arrives as 255; `OccupancyGrid` row 0 is the *lowest* y while `ImageData` row 0 is the *top*; `info.origin` is the pose of cell (0,0) and is generally not the world origin.
- **The robot drawn as its real 1.12 × 0.48 m footprint rectangle, not a dot** — in a narrow aisle the operator's actual question is "does it fit". Verified numerically before shipping rather than by eye, because `base_link`'s non-REP-103 convention (`+X` = RIGHT, `+Y` = NOSE) has now bitten this project five times: at the mark's −90° heading the 1.12 m long axis lies along map `+X`, the nose direction, and the 0.48 m axis across it.
- **Click-to-goal**, two-tap armed, publishing `/goal_pose_click` — never `/goal_pose`, since `goal_pose_adapter` already owns the −90° conversion and duplicating it in a second place is precisely how §17.19's axis bug happened.
- **A `ZERO` button, and the `/odom/reset` topic that makes it possible.** `odometry_publisher` only ever zeroed `x/y/theta` in `__init__`, so re-zeroing meant `systemctl restart aislebot.service` — which also tears down `phone_dashboard`, the very thing that would be asking. The new topic zeroes the same three numbers in place and refreshes `last_time` (without which the first post-reset sample would integrate the entire idle gap and walk the new origin straight off zero). **The dashboard refuses the request while mapping is active**, which enforces §8's ordering in software: `slam_toolbox` pins `map→odom` to identity at its first scan, so a re-zero underneath a live session moves odom's origin without moving map's.
- **An automatic pose CSV** (`run_<stamp>_pose.csv`) written for the duration of every mapping run, so jump analysis no longer requires launching a separate terminal tool.

**Found by reading, not rebuilt:** `stop_mapping()` has always called `map_saver_cli` — the MAP button is already a complete start-stack / stop-stack-and-save cycle, and no separate save button is needed.

**Where this leaves the session.** Stage A settled, Stage B deployed and partially validated, the terminal-free path built but unexercised, and still no usable map — the one artefact everything downstream depends on. Next session's plan, with the revised acceptance gate and the dashboard-only Stage C procedure, is in `docs/Next_Session_Kickoff.md`.

## 17.33 24 Aug 2026: the Pi audited and cleaned before driving, a second undeployed config caught before it could fire, and 133 MB of never-opened rosbags found outside the data folder

Session opened on the §17.32 plan but the user asked for a full inventory of the Pi first — "what do we have, and what is old or redundant" — before anything was driven. That instinct is what found everything below. Nothing was driven; the robot did not move all session.

**`tools/pi_audit.sh` written and run.** Read-only, one paste, sixteen sections: identity, clock, thermals, disk, network, services, USB/serial, ROS workspace, deployed code with hashes, Pi-side configs, run data, cache sizes, package cruft, running processes, and a section that fetches every deployed source file from GitHub and reports `match` / `DIFFERS` / `MISSING-ON-PI` / `EXTRA`. §17.32 found its undeployed config by auditing one file by hand; this makes the same check mechanical and extends it to all twenty-one.

**Stage B independently confirmed.** `~/ros2_ws/slam_nodom.yaml` hashes to `7ec7904a…0093ba`, byte-identical to the repo's `system/slam_nodom_stageB.yaml`. §17.32's claim verified from a second direction rather than taken on trust.

**The Pi was exactly one commit behind, and the audit could name which one.** `phone_dashboard.py` measured 87,320 B and `odometry_publisher.py` 10,783 B on the robot — not approximately, but *exactly* their sizes at commit `fe2c3be` ("Stage E: dashboard map rendering, live pose, click-to-goal"). The missing commit is `0bea474`, which adds the MAP-owns-the-workflow logic, `/odom/reset` and the pose CSV. So live map rendering and click-to-goal were already deployed on 22 Aug; the ZERO button and the save-on-stop cycle were not. File size as a commit fingerprint turned "the dashboard is out of date" into a precise statement about which 135 lines are absent.

**A second config in the §17.32 class, caught before it ever fired.** `system/ydlidar_params.yaml` — whose own header reads "Confirmed working parameters… read off the hardware, not copied from a forum" — was committed **flat**, with no `ydlidar_ros2_driver_node: / ros__parameters:` nesting. ROS 2 does not partially apply such a file; it binds nothing, and the driver falls back to compiled defaults with the wrong `baudrate`, `lidar_type` and `isSingleChannel` for an X4 Pro, with no error naming the parameter file. `install.sh:220` is the only thing that deploys it, renaming it to `params/ydlidar.yaml` on the way in — and it would have overwritten the working copy. It never fired **only** because `install.sh` has not run since 26 June 2026, while the flat file was committed 13 Aug. A reprovision or a fresh SD card would have hit it.

The difference from §17.32 is worth stating precisely: that was a config that **never reached the robot**. This is a config that **would have reached it and been silently inert**. Same audit method, opposite failure mode, and this one was caught with the robot still working rather than three sessions later.

Traced to source: `docs/LiDAR_SLAM_Bringup.md` listed the values as a prose summary without the wrapper they sit under, and on 13 Aug that listing was transcribed verbatim into a YAML file. The doc is corrected, and the repo file is now byte-identical to the Pi's working copy (sha256 `049fbbe7bff9…`, 561 bytes) rather than merely equivalent — so the audit reports `match` and any future drift is unambiguous.

**The audit script's own first run was wrong in three places**, which is worse than no output, and is recorded because the correction matters more than the tool. `have vcgencmd` was the thermal test, but Ubuntu on the Pi 5 ships vcgencmd without `/dev/vcio`, so it printed an error where a temperature should be. Section 11 reported `params/ydlidar_params.yaml` MISSING when `install.sh` renames on copy and that path was never meant to exist. Worst, the EXTRA scan used `curl -fsI` per file and reported `phone_dashboard.py`, `arm_bridge.py` and `setup.py` as absent from the repo *two lines after the same run matched them byte-for-byte* — HEAD against raw.githubusercontent is not trustworthy under rate limiting, which also explains five interleaved `FETCH-FAILED` lines. Rev 2 reads sysfs first, retries with `--retry-all-errors`, and replaces eleven HEAD requests with one `git/trees?recursive=1` call compared locally, guarded on `truncated=false`.

**133 MB of rosbags found outside the data folder, two of them never opened.** `~/slam_tests/` holds three MCAP bags: `slam_test_01` (94.4 MB, 20 Aug 18:31), `slam_test_02` (27.4 MB, 20 Aug 19:08) and `jump_154512` (11.8 MB, 22 Aug 15:49). The last is Stage A's recording. The two from 20 Aug are §17.29's session and nothing in this journal describes them ever being read — 122 MB of full-rate TF and scan data captured while the jump investigation was running blind. The audit nearly missed them too: it searched for `rosbag2_*` directories and these carry custom names. All three are now copied off the Pi.

**The corpus has never been analysed as a corpus.** `~/aislebot_logs` holds 369 files: 124 telemetry CSVs, 73 auto-generated run reports, 70 map pairs, 32 SLAM logs. Every finding in Part XVII derives from reading exactly one run — §17.27 one run, §17.29 one jump, §17.30 four legs of one session, §17.31 one trajectory, §17.32 one bag and two drives. No entry looks across runs. Three questions are answerable from what already exists, offline, without driving: how much does the same corridor vary across 70 maps of it (which is precisely Stage C's map-integrity criterion); whether §17.30's cold-start recovery pattern, inferred from one session's four goals and explicitly flagged as needing 3+ repeats, holds across 73 reports; and whether per-wheel behaviour has drifted over three weeks. Recorded as a workstream, not started.

**`tools/pi_clean.sh` written and applied.** Dry run by default, every destructive line behind a wrapper that prints rather than executes without `--apply`. Reclaimed **2.0 GB, 58% → 51%** — the estimate said 2.9 GB and was optimistic, chiefly because the old kernel freed 130 MB against a guessed 245 and the per-snap-base figures were placeholders. Actuals: 467.6 MB of journals deleted and journald capped at `SystemMaxUse=100M` so it cannot silently regrow, 5,269 run dirs under `~/.ros/log`, four leaf snaps and four bases removed cleanly, `~/.vscode`, the YDLidar SDK build tree, and `~/ros2_ws/build` down 85 MB → 19 MB as rf2o's artefacts went with it. Workspace dead code (`phone_dashboard.bak.py`, `arm_bridge.bak.py`, `hardware.launch.py`, and `rf2o_laser_odometry`, a dead end recorded in §13.5) was tarballed to `~/aislebot_deadcode_<stamp>.tar.gz` before removal, because there is no git clone on the Pi and deleted means gone. `~/aislebot_logs` and `~/slam_tests` were excluded by construction and both copied to the PC first.

**The Pi now boots to `multi-user.target`.** Not a disk decision — it returns roughly 250 MB of RAM and a core to the ROS stack during every mapping run, and §17.25 is a recorded case of CPU starvation killing SLAM and the LiDAR pipeline outright mid-recovery. Reversible with one command (`sudo systemctl set-default graphical.target`), and `sudo systemctl isolate graphical.target` starts a desktop on demand without rebooting.

**A deploy failure caught by hashing rather than by a mystery.** The first attempt to fetch `phone_dashboard.py` died on `curl: (35) OpenSSL … wrong version number`. Because the procedure hashes before building, this surfaced immediately as the *old* hash (`2c53cc7cb6e1…`) rather than as strange behaviour after a successful-looking build. Root cause of the retry not helping: **`--retry` does not retry TLS handshake errors** — only transient HTTP responses and timeouts — and `--retry-all-errors` is required. Worth remembering for every `curl`-based deploy in `Important_Commands.md` §2.

**State at session end.** `odometry_publisher.py` is verified deployed (`143702e8511f7d8b…`). `phone_dashboard.py` was re-fetched and its correct hash appeared in a scrambled terminal paste, so it is **probable but unverified**. Critically, **`colcon build` and the service restart were never run**, so the robot is still executing the old `install/` tree: the running dashboard remains `fe2c3be`, with no ZERO button and no save-on-stop. The workspace source tree is in a mixed state and the next action is a single guarded command that re-verifies both hashes and only then builds. Nothing was driven, and no map was made.

## 17.34 25 Aug 2026: four latent bugs found and killed, the map-loss chain traced end to end, and the first fully verified robot state

Second hands-on day in a row. No commissioning map was accepted, but the platform underneath one stopped leaking, and for the first time every deployed file on the robot is known to match the repo.

**The best return-to-mark this project has recorded: 1.9 cm, 0.2°.** A ~30 s drive from the zero mark and back read `MAP x 0.018 y -0.006`, `NOSE -90.2°`. Against §17.32's Stage B best of 5.0 cm / 0.75° and the 24 Aug perimeter drive's 28.9 cm / 4.2°. Recorded as an observation, not a claim about repeatability — it is one short drive, and the map it produced was lost to the bug described below before it could be judged.

**A drive-control leak in the map view, found by the user testing an assertion of mine that was wrong.** With the map open and no goal armed, a plain tap or drag on the map drove the robot exactly as the joystick does — reproduced on phone and desktop. I had previously reasoned from the CSS (`.map-view` is `position:absolute; inset:0; z-index:6`) that the map covered the joystick and therefore could not reach it. **z-index governs painting and hit-testing, not event propagation**, and `#mapView` is a *child* of `#joyArea`, so every touch bubbled straight into the joystick's handlers. `mapCanvas`'s `pointerdown` never called `stopPropagation()`. Fixed in four places rather than one: a `mapView` guard in the joystick's own handlers (the layer that cannot be defeated by pointer-vs-touch ordering differences), `stopPropagation()` on the map's pointer handlers, a `touch*` swallow on `#mapView` (because `preventDefault()` on `pointerdown` does **not** suppress the touch events that follow), and a release of any in-flight drag on entering map view. The lesson is not the CSS: it is that a hardware test beat a confident reading of the source.

**The live map's palette was measurably unusable.** Free space `rgb(12,40,64)` against unknown `rgb(16,22,36)` is a WCAG contrast ratio of **1.20:1** — indistinguishable on a phone in daylight, which makes "have I covered this aisle or have I just not looked at it" unanswerable from the one view that exists to answer it. Repalletted on a rule rather than by eye: luminance rises with occupancy probability, and unknown is taken **off-hue** to a neutral slate because it is not a low probability of occupancy, it is the absence of a measurement. Now 3.81:1 free/unknown, 3.79:1 occupied/free, 14.45:1 occupied/unknown. Also hid the arm and lift controls in map mode — on a phone they consumed roughly two thirds of the right panel and 120 px of width for controls with no role in a mapping run.

**`system/ydlidar_params.yaml` was a live landmine and had been since 13 Aug.** Committed **flat**, with no `ydlidar_ros2_driver_node: / ros__parameters:` nesting. ROS 2 does not partially apply such a file — it binds nothing, and the driver falls back to compiled defaults with the wrong `baudrate`, `lidar_type` and `isSingleChannel` for an X4 Pro, with no error naming the parameter file. `install.sh:220` is the only thing that deploys it and would have overwritten the Pi's working copy. It never fired **only** because install.sh has not run since 26 June. The repo file is now byte-identical to the robot's proven copy (`049fbbe7bff9…`, 561 B) and `docs/LiDAR_SLAM_Bringup.md` — whose values-only listing is what got transcribed into the flat file — is corrected. Same class as §17.32, opposite failure mode: that was a config that never reached the robot; this one would have reached it and been silently inert.

**The map-loss chain, traced through four distinct causes.** A 24-minute mapping run was lost to a `systemctl restart`, and the fix took four iterations because each one exposed the next layer:

1. **The shutdown path was dead code.** `stop_mapping()` sat after `uvicorn.run()`, which never returns: `systemctl restart` SIGTERMs the whole control group, uvicorn begins a *graceful* shutdown that waits for open connections, and a connected phone holds a WebSocket open indefinitely — so systemd SIGKILLs it first. Proven from the log, not inferred: between `Mapping stopped` for the previous run at 12:29:35 and the next `Phone Dashboard v2.4` at 12:53:33 there is not one line of the shutdown path.
2. **Owning the signals instead** — drive `uvicorn.Server` directly, stub its signal installer, save first and set `should_exit` second.
3. **The stub targeted a method that no longer exists.** uvicorn 0.46 replaced `install_signal_handlers()` with `capture_signals()`, a context manager. Caught on hardware by a deliberate guard that fell back to `uvicorn.run()` and named the missing attribute in the warning, rather than failing to start the dashboard on a day the robot was in use. Both APIs are now handled.
4. **`map_saver_cli` itself then failed.** It is a separate process that *subscribes* to `/map`, so it only works while `slam_toolbox` is alive to publish — and systemd is killing both at the same instant. The tell was the `_report.json` appearing without a `.pgm`: that file is written by `stop_recording()`, which runs *after* the map save, so `stop_mapping()` had run end to end and only the save had failed.

**The fix removes the dependency rather than working around it.** `_map_callback` already caches every `OccupancyGrid` for the live view, so width, height, resolution, origin and the raw grid are in memory. `_write_map_from_cache()` writes the `.pgm` and `.yaml` directly — no IPC, no subprocess, nothing else in the launch tree required. `map_saver_cli` stays the primary path for a normal STOP MAP; the cache catches it when it fails. Two details handled explicitly because both silently corrupt the output: int8 arrives unsigned so 255 means −1 means unknown, and `OccupancyGrid` row 0 is the *lowest* y while PGM row 0 is the *top*. Verified by round-tripping a synthetic grid through `tools/map_corpus.py` (24 occupied, 60 free, 12 unknown, exact) before it went near the robot.

**Confirmed on hardware.** MAP, ~30 s drive, `systemctl restart` with mapping still live → `run_20260825_151713.pgm`, **27,383 bytes**, the largest map of the day, with `.yaml`, `_report.json` and `_pose.csv` alongside. Its header reads `# CREATOR: phone_dashboard from cached /map`, so the fallback wrote it and `map_saver_cli` did fail exactly as predicted. Note the log line announcing it never reached `aislebot_boot.log` — the dying process's buffered output was lost — so **the artefact is the evidence, not the log**.

**The first fully verified robot state.** All **30** deployed files under `~/ros2_ws/src` hash-match `main` byte-for-byte, including the two that have burned this project: `~/ros2_ws/slam_nodom.yaml` (`7ec7904aa3ab…`, Stage B) and `params/ydlidar.yaml` (`049fbbe7bff9…`). Done by hashing on the Pi and diffing against locally computed repo hashes — no network needed, which mattered because eduroam blocked HTTPS from the Pi for much of the day.

**Repository consolidated.** `main` had not moved since 11 Aug and shared **no common ancestor** with the working branch — different root commits (`6e7c1d8` vs `2effcff`), `git merge-base` returning nothing, because the working branch was created as an orphan. Merged with `--allow-unrelated-histories`, then `claude/nab-hardware-calibration` merged in as well: it held **36 files that existed nowhere else** (the whole PID bench and ground-test corpus, `analyze_bench_log.py`, `sync_bench_logs.ps1`, the hardware photos), contrary to the assumption that it was disposable. `main` went from 145 files to 198. Three files that came out "missing" were each chased down rather than accepted: two bench CSVs relocated into `data/bench_logs/bench/` (byte-identical, verified by hash) and `aislebot_pid_analysis_v2.py` deliberately archived to `past_iterations/` by commit `8c630d5`.

**`tools/map_corpus.py` added** — reads a folder of `run_<stamp>.{pgm,yaml,_report.json}` sets and prints them side by side, ranked by occupied-cell fraction, since AMCL localises against walls and free space contributes nothing to a scan match. Its `wall_m/perim` metric separates "did the drive get round the room" from "how much of the bounding box is unknown", and those two can disagree sharply: `run_20260825_113735` is 81% unknown — which its own auto-report calls "not yet a usable map for navigation" — while carrying ~27 m of wall against a 32.8 m bounding perimeter, a ratio of 0.82. **Which reading is right is still open and needs eyes on the grid, not more arithmetic.**

**Two network failures cost real time and are now documented** (`Important_Commands.md` §1, §2, new §2.1). `aritra-desktop.local` failed to resolve from Windows four consecutive times while the Pi was up and reachable by IP, and the Pi's eduroam lease moved twice in two days — a stale address gives a timeout indistinguishable from the robot being down. And **`curl --retry` does not retry TLS handshake failures**, only transient HTTP responses and timeouts: repeated `curl: (35) OpenSSL … wrong version number` sailed past all five attempts. `--retry-all-errors` is required, and when even that fails, §2.1 documents relaying the file through the PC.

**Where this leaves the session.** The dashboard is trustworthy, the robot's deployed state is verified, and a map now survives anything that kills the stack. Still no *accepted* commissioning map: the integrity check on `113735` and `151713` has not been done, and that remains the gate before Stage D.

## 17.35 26 Aug 2026: the acceptance gate turned into two instruments, and the AMCL bug confirmed from source

A no-hardware session. Nothing was driven, and none of what follows has met the live node — that is stated up front because every tool below is untested against real data and the project's own standard is that a value in the repo is not a value on the robot.

**The gate §17.32 left behind was a human eyeballing a grid, and that was the weakest link in calling mapping reliable.** §17.34 closed with the integrity check on `run_20260825_113735` and `run_20260825_151713` undone and the note that settling it "needs eyes on the grid, not more arithmetic". True of the arithmetic that existed: `map_corpus.py` counts cells and has nothing to say about whether those cells are one wall or two copies of one wall. Different arithmetic can say it.

**`tools/map_integrity.py` — the fold signature, as five numbers.** The detector that carries the verdict is D2, doubled walls, and its argument is worth stating because it is falsifiable. Free cells between two near-parallel walls mean the LiDAR returned through that space, so something stood between them and observed both faces — but the gap is narrower than the robot's own 0.48 m, so that something cannot have been this robot. Two walls whose far faces were both seen across a gap nothing could occupy is the geometry a false closure leaves when it fuses two poses that are not the same pose. The known hole: a genuine narrow gap between shelves, viewed end-on down its length, looks identical. That is precisely why flagged cells are clustered and reported **in map coordinates** rather than only counted — a real end-on gap is one place you can walk to, a fold is a whole wall duplicated. Four supporting measures: D1 wall thickness for the near-miss fold that fattens a wall instead of duplicating it, D3 branch points on the Zhang-Suen-thinned skeleton, D4 wall-orientation histogram mod 90° where a chunk rotated a few degrees shows as a satellite peak, D5 free-space components.

**The thresholds are guesses and the output says so.** They stop being guesses when `--corpus` is run over the 70 archived maps: the same room mapped 70 times gives a distribution, and the tool prints the percentiles that should replace the constants. This is the first thing in the project designed to be *calibrated* by the corpus §17.33 recorded as never analysed, rather than merely to read it.

**Five synthetic rooms with known answers, three of them false positives.** §17.34 round-tripped a synthetic grid through `map_corpus.py` before it went near the robot; same standard here, because a detector never shown a fold it is known to contain has not been tested, only run. A clean rectangle, a planted 0.35 m ghost wall, **two walls 0.30 m apart with UNKNOWN between them**, a real 0.85 m aisle, and a genuinely 3-cell-thick wall. The third case is the one that matters: it is the same geometry as the fold and must not be flagged, and it is not, because the free-space requirement — not the parallelism, not the gap width — is what does the discriminating. `--png` writes the map with flagged cells in red, so the number and the picture can be checked against each other instead of one replacing the other.

**`tools/graph_residuals.py`, and a correction to the MATLAB item that specified it.** `MATLAB_Navigation_Reference.md` Tier 1 #2 proposed computing `edgeResidualErrors` over `/slam_toolbox/graph_visualization`, on the reasoning that "nodes and edges are already on the wire". Reading `publishGraph()` in `loop_closure_assistant.cpp` first — rather than after — showed the topic carries less than that implies: node id → solved `(x, y)`, and edges as two `LINE_LIST` markers whose points are pairs of endpoint **coordinates**. No node orientation (`toMarker()` hardcodes `orientation.w = 1`), no edge node ids, **no edge measurement, no information matrix**. A true SE(2) χ² residual needs the last two. **The item as literally specified is not implementable against this topic**, and `SerializePoseGraph`, which does hold them, writes Karto's own binary serialisation with no Python reader. Same lesson as §17.34's z-index: a confident reading of what something does is not a substitute for reading its source, and here reading it first saved building the wrong thing.

**What replaced it is stronger than what was specified.** The graph is republished every `map_update_interval` — 1.0 s in `slam_nodom_stageB.yaml` — so successive messages can be differenced, and **a node that moves between two publications was moved by the optimiser**. Differencing the *edge sets* over the same two messages names which edge arrived in the update that moved things. A closure appearing in the same update as a 40 cm shift is that shift's cause. **That is the per-closure signal §17.29 concluded did not exist.** §17.29 was right that it does not exist as an *event* — no console line, no topic, no service, verified against source and the live node. It exists as a *difference*. This is Stage A's method, which caught the 39.57 cm `map→odom` jump by differencing TF, at per-node resolution and with the cause attached.

**And the difference can be judged, which a raw jump size cannot.** A legitimate closure cancels drift accumulated since the robot was last at that spot, so `implied drift rate = shift / metres driven since the closed-on node` should land near this project's own measured odometry error — 1.5% over §17.32's 3.4 m box drive, 2.4% forward/back, 3.3% lateral (§17.30). A closure implying 20% corrected drift that never accumulated. The 10% ceiling is three to four times the worst measured rate and is **the single judgement call in the tool**; everything else is measured. This is the direct attack on §17.32's still-open question, and it is the criterion that section explicitly lacked when it recorded that "no single-sample step > 10 cm" cannot tell a good closure from a bad one.

**Topology has to be recovered from geometry, and a mis-match would invent edges.** The line list carries coordinates, so each endpoint is matched back to a node marker by position — exact first, since both are the same doubles from the same message, with a tolerance fallback and an **unresolved count** reported rather than silently dropped. The self-test asserts the round trip on every case.

**`nav2_params.yaml:57` confirmed as a real bug and fixed.** The kickoff's suspicion was right, and it was checked against upstream `nav2_amcl` source on both `jazzy` and `humble` rather than reasoned from version history. `plugins.xml` declares exactly two classes, `nav2_amcl::DifferentialMotionModel` and `nav2_amcl::OmniMotionModel`, with no alias for the bare strings anywhere in the package; `amcl_node.cpp`'s own **default** is the fully-qualified `"nav2_amcl::DifferentialMotionModel"`, which is itself the tell; and it calls `plugin_loader_.createSharedInstance(robot_model_type_)` with no string translation, no legacy-name shim and no try/catch, on the `on_configure` path. `"omnidirectional"` would have thrown out of `on_configure`, AMCL would never have reached ACTIVE, and `lifecycle_manager` would have aborted the **entire** navigation bringup — not just localisation, the same all-or-nothing mode §17.17 hit with `docking_server`. It had never announced itself because the block has never run. The installed package still needs checking on the Pi before the first bringup, and `ros2 param get /amcl robot_model_type` after it: the repo is not the robot.

**The two tools are designed to corroborate each other.** A false closure strains the pose graph at the moment it fires, and puts a doubled wall at the place it strained. `graph_residuals.py --watch` gives the time and the map coordinates; `map_integrity.py --png` gives the location on the saved grid. Either alone is one instrument's opinion; the two agreeing on a location is the first evidence in this project that would not rest on a single reading.

**Where this leaves it.** Both tools self-test clean and neither has seen real data. The integrity check on the two existing maps is now a command rather than a judgement, but the `.pgm` files live on the Windows machine and are not in the repo — running it is the first hardware-side step, and it needs no robot.

## 17.36 26 Aug 2026: the X/Y dispute settled on hardware, three dashboards found to have silently forked, and one canonical file restored

A dashboard-only session, hardware-driven throughout, that started as one axis complaint and ended as a repo hygiene problem.

**The dispute.** Parked at the ZERO mark and pressing W (forward), the phone showed `MAP x` increasing and `MAP y` staying at 0.000 — the user expected the reverse, on the reasonable assumption that "forward" should mean "Y" the way graph paper does. The two are not the same claim. `base_link`'s nose is `+Y` by the project's own documented convention (nav2_params.yaml header, §17.10) — that was never in dispute. What was actually being read on screen is the **map frame**, and the ZERO mark's frame yaw is `-90°`: at that heading the nose vector, rotated into the map frame, points along map `+X`, not map `+Y`. Confirmed by the W-press itself (`x: 0→0.325, y: 0.000`, unchanged) and by a second live test the user read as contradictory — "drove right, held E" — which turned out to be testing the wrong control: `E` is bound to yaw (`kz -= 1`, rotate CW), not the `D` strafe key, so that data point was a rotation test, not a translation test, and its 24 cm shift is better read as the same pose-graph instability already on file (§17.34) than as an axis bug.

**The fix that was actually asked for.** Once the mechanism was clear, the request was direct and unambiguous: relabel the display so it matches ordinary graph convention, not slam_toolbox's own (arbitrary, start-heading-dependent) axis names. `dispX = -raw_y, dispY = raw_x`, applied only at the point each number is printed — HUD, live-pose card, grid labels, axis arrows. Nothing upstream changes: goals, camera-follow and the pose CSV all still consume `robotPose.x/y` raw, exactly as TF and slam_toolbox report it. Verified headless (Playwright, three viewport shapes) against both hardware readings before shipping: the W-press case now prints `x 0.000, y 0.325`.

**Then the deploy came back showing the old, unrelabeled dashboard, and the reason was worse than a bad deploy.** Investigating turned up three independently-diverged copies of this file, none of them the single source of truth the project's own §16.7/§16.9 drift lessons exist to prevent:

1. The git repo's tracked `phone_dashboard.py` — dark theme, carried every fix made in-session (odometry logging, the NOSE bug, the grid-rotation bounding-box bug, the axis relabel above).
2. A light-theme fork obtained from ChatGPT earlier in the session, patched in this session for four real rendering bugs (upright rotated text, a UI badge overlap, a background-clear-after-rotate ghosting bug, missing Y-axis labels) and given the axis relabel — but never actually deployed; it existed only as a file handed to the user, not on the Pi.
3. A **third** fork (`phone_dashboard_fixed_v3.py`, "v2.4"), from a separate ChatGPT thread the user had continued independently, which is what was actually running on the Pi. It had hit the same upright-text problem fork #2 solved with rotation-aware label placement, and "fixed" it by a different route: zeroing `DISPLAY_ROT` entirely. That removes the garbling, but it also removes the reason `DISPLAY_ROT` exists — without it, forward drive visibly moves the robot **sideways** on screen instead of up, the exact bug an earlier commit this project already fixed once (`edf2f2d`, "Rotate the map canvas so forward looks like forward, not sideways"). It also printed raw, unrelabeled `x/y`, so it satisfied neither request.

The one reassuring finding: **the Python `class PhoneDashboard(Node)` — every ROS publisher/subscriber, every TF lookup, arm/E-STOP/UV control, the odometry CSV logger — was byte-for-byte identical across all three files.** Diffed programmatically, not eyeballed. Only the HTML/JS presentation layer had drifted; frames, TF, safety and odometry were never actually in question, which matches the audit note (independently obtained by the user from a fourth, separate tool run) that the underlying ROS architecture is internally coherent and that the HUD relabel is display-only. That audit's specific code-level claims about other files (`odometry_publisher.py`'s exact publish-time rotation, a `cmd_vel_axis_adapter.py`, `scan_relay.py`'s exact mirror formula) were **not** independently verified this session and should not be treated as confirmed until they are.

**Resolution: fork #3's layout is what the user is actually using, so it is now the canonical file.** Took fork #3 (the newer, more complete light-theme UI — scale bar, layers panel, research-mode toggle, on-canvas axis arrows, numeric grid labels) as the base, restored `DISPLAY_ROT = -π/2`, and rebuilt its label-drawing with the same rotation-aware technique already proven in fork #2 (`drawUpright()` for small offsets from a real map point; dedicated `labelXGridline()`/`labelYGridline()` for the grid's margin-anchored numbers, which need the real screen edge computed directly rather than a small local-space nudge — a fixed local anchor like "6 px from the local top" is only actually near the screen edge when there is no rotation, and explodes to the wrong place on any non-square viewport once one is applied). Applied the same `dispX = -raw_y, dispY = raw_x` relabel to this file's HUD, live-pose card, grid labels and the new on-canvas "X+"/"Y+" axis arrows (which needed their world-space tip coordinates swapped, not just their printed numbers). Verified headless across phone (390×844), wide-desktop (1900×950) and tall (950×1900) viewports — matches hardware readings on all three, no exploded or ghosted labels. This file now replaces `src/mecanum_robot/mecanum_robot/phone_dashboard.py` in the repo outright; the two abandoned forks are documented here and nowhere else.

**Branch audit, at the same request.** Cross-referenced every branch against `main` (ahead/behind commit counts, not just PR state — every PR in this repo's history shows `merged: false` even where content plainly landed, because merges here happen by local push rather than GitHub's merge button, so PR state alone is not reliable evidence). Three branches were confirmed fully absorbed into `main` — zero unique commits, safe to delete outright: `claude/mapping-autonomous-nav-695glw`, `claude/nab-hardware-calibration`, `claude/narrowaislebot-mapping-hardware-02rnh2`. A fourth, `claude/aps-report-draft-2nywbq`, carries one real unmerged commit (an 11.5k-word draft Annual Progress Report with 21 figures, never merged to `main`) and was left alone on the user's explicit call. The three deletions themselves were blocked by this session's own permission classifier (`git push --delete`, and no branch-delete tool exists in the GitHub MCP server as an alternate route) — **still pending**, needs either the user's own action on GitHub or an approved retry next session.

**Where this leaves it.** One dashboard file, one place it lives, verified against every hardware reading collected this session. The mapping-reliability instrument chain from §17.35 is unchanged and still untested against real data — Stage D (AMCL) has not been reached, and nothing here touched `slam_nodom.yaml`, TF, or the ROS control stack. The three pending branch deletions and the unverified audit claims (§ above) are the two loose ends to close first.

## 17.37 26 Aug 2026 (continued): the full axis pipeline traced against source, and written down once so it stops being re-derived

Immediately following §17.36, at the user's explicit request to settle the axis question "and stop debating." The pasted external audit's claims about the stack — `cmd_vel_axis_adapter.py`, a REP-103-speaking `mecanum_teleop_asymmetric.py`, a mirror rather than a rotation in `scan_relay.py` — were flagged in §17.36 as *not yet independently verified this session*. They now are: every file the audit named was read directly, not taken on trust.

**Every hop checks out, and the interesting one was checked by re-derivation, not by reading a comment.** `odometry_publisher.py` computes internally in plain REP-103 and publishes the TF orientation rotated by a constant `theta - 90°`, translation unchanged (§17.10's original design). Whether that is actually self-consistent — whether a physical point lands at the same real position in `odom` computed either way — is not something to take on faith from the module's own docstring. Worked the algebra: for a point with internal-frame coordinates `(px_int, py_int)`, the published-frame coordinates are `(-py_int, px_int)` (a +90° rotation of the point, since the published frame is the internal frame rotated -90°). Substituting into both versions of "where does this point land in odom" and requiring them to agree forces `pub_theta = theta_internal - 90°` exactly — which is the line already in the code. Confirmed, not assumed. The twist rotation (`pub_vx=-vy, pub_vy=vx`) checks out the same way.

**`mecanum_teleop_asymmetric.py`'s convention was confirmed by inverting its own kinematics**, not by a comment: its inverse-kinematics formula, expanded algebraically, reduces to exactly odometry's *internal* (pre-rotation) forward-kinematics formula for `vx` and `vy`. So teleop and odometry's internal math agree with each other on REP-103 by construction, independently of what either file says about it.

**`cmd_vel_axis_adapter.py` and `goal_pose_adapter.py` are not leftover cruft — each is the direct, documented fix for a real incident**: the first autonomous goal drove 0.956 m at 88.4° off-heading before an E-STOP (§17.19), diagnosed as exactly the TF-axes-vs-REP-103 mismatch these nodes now bridge. Both are opt-in or placed at one exact point in the chain by deliberate design, specifically reasoned in their own docstrings as avoiding "the kind of invisible transform that produced the axis bug in the first place" — the same principle §17.10 laid down, already self-applied before this session re-verified it.

**`scan_relay.py`'s mirror claim holds**: three bearings measured against how the robot actually drives solve `reported + true = 270°`, not `reported - true = const`, which is the signature of a reflection, and a reflection is not something any TF (rigid motions only) can express — so it has to live in software, in exactly one place, and does.

**Net count: three conversion points in the entire stack** — the cmd_vel adapter, the goal-orientation adapter, and the LiDAR mirror — not the six-plus-layer tangle the external audit's framing implied. Each is justified by an actual physical or mathematical constraint, each is isolated to one node, and `twist_mux` (checked directly against its own config) does zero axis math, confirming the pattern was not silently duplicated anywhere.

**Written down once, so it does not get re-derived a fourth time.** `docs/Axis_Convention.md` is new: the rule stated first, the full hop-by-hop table with file:line citations, and a keypress → TF → dashboard-display quick-reference table for testing it by hand — including the specific trap that already caused one round of false alarm this session (`E` is yaw, not right-strafe; `D` is the strafe-right key). Cross-referenced from `docs/README.md` and the kickoff doc's resume block.

**Where this leaves it.** The axis question is closed with a written, checkable answer, not a verbal one. Nothing in this entry touched code — it is verification and documentation only. The mapping-reliability priority from §17.35 is exactly where §17.36 left it: `tools/map_integrity.py` has still never been run against real data, and that is still the next actual step.

## 17.38 27 Aug 2026: the map frame was rotated after all, and §17.36–§17.37 verified the wrong half of the question

A correction to the two entries immediately above, on evidence they did not have. §17.36 and §17.37 both concluded the axis stack was coherent. They were right about `base_link` and wrong about `map`, and the reason the error survived two consecutive verification passes is the substance of this entry.

**The evidence that reopened it was a video, and it was decisive in a way argument had not been.** The user recorded the physical robot and the map screen side by side: painted `+Y` arrow up toward the marked nose, `+X` right, and then W, S, D, A driven in sequence from the ZERO mark. Read frame by frame off the pose card, `W` took map X from 0.054 to 0.207 with Y pinned at 0.000; `S` brought it back to −0.005; `D` held X at −0.005 while Y went to −0.211; `A` returned it. So the map frame answered `W→+X, S→−X, D→−Y, A→+Y` while the robot's own painted axes said forward was `+Y`. The footprint on the canvas confirmed it independently — drawn wide, long axis and heading arrow along map `+X`, when the robot is 1.12 m along its nose axis and 0.48 m across.

**Where it actually was: `odometry_publisher.py`, and it is a half-applied conversion, not a rotation error.** The node integrates internally in REP-103 and then applies the `+Y`-forward relabel to the published *orientation* (line 221, `theta − π/2`) and the published *twist* (`pub_vx=-vy, pub_vy=vx`) — but published the *translation* as the raw internal `self.x, self.y`. Publishing raw internal translation is what **defines** `odom`'s own axes to be the internal REP-103 ones. So `odom +X` pointed along whatever direction the robot faced when odometry was zeroed, `base_link` carried `+Y`=forward, and the constant −90° yaw was not a design choice at all — it was the seam between two frame definitions. `map` inherited the whole thing because slam_toolbox starts `map→odom` at identity, which the video confirms numerically: the dashboard's `NOSE` read 0.0° through a `+90` display offset, so raw `map→base_link` yaw was exactly −90°.

**Why §17.37's algebra was correct and its conclusion still wrong.** That entry re-derived `pub_theta = theta_internal − 90°` from the requirement that a physical point land at the same real position in `odom` computed either way, and the derivation is sound — the pose of `base_link` *relative to* `odom` is self-consistent. The question it did not ask is what `odom`'s axes then are. Self-consistency between two frames says nothing about whether either one is the frame you wanted. **A verification pass that only checks internal consistency will pass a coherent system that is coherently wrong**, and that is exactly what happened twice.

**Four downstream compensations had grown over the seam, and together they made it invisible.** The dashboard rotated its canvas −90° so forward *looked* like up; the dashboard relabelled every printed number `dispX=-raw_y, dispY=raw_x` so the text *read* right; `goal_pose_adapter` subtracted 90° so a dragged goal aimed the nose; `ZERO_POINT_YAW` was set to −90° so the home marker's triad lined up with `base_link`. Each was locally reasonable, each was documented, each was correct *given* the seam. Anyone auditing any single consumer found it correct. That is the failure mode worth naming: **compensations do not just hide a fault, they actively defend it from discovery**, because every place you check has already been patched.

**The irony in the dashboard forks.** §17.36 spent a session declaring the repo's dashboard canonical and the deployed fork #3 defective, on the grounds that fork #3 had zeroed `DISPLAY_ROT` and printed raw x/y. Diffed properly this session — Python/ROS half byte-for-byte identical at sha `ab7e8245…`, only HTML/JS differing — fork #3 turns out to be the *honest* one. Its own comment block argues for showing "the actual ROS map frame, without an additional canvas rotation" so that labels, pose readout and geometry stay in one frame. It was right, and it is the only reason the fault became visible at all: the canonical file would have re-hidden it. Deploying the repo copy, which §17.36 recommended and this session nearly did, would have cost another two weeks.

**The fix, and why it removes a conversion point rather than adding one.** Rotate the published translation the same way orientation and twist already are: `pub_x = -self.y`, `pub_y = self.x`, and `pub_theta` becomes plain `self.theta` because there is no longer a seam for a constant to bridge. `odom`, `map` and `base_link` now share `+X`=right, `+Y`=forward; a freshly-zeroed robot on the mark reads `[0,0,0] @ 0°` rather than `@ -90°`. All four compensations were deleted in the same commit — the count of conversion points in the stack goes from three to two (the `cmd_vel` adapter and the LiDAR mirror), not four. **Untouched, deliberately:** the internal REP-103 integration, `mecanum_teleop_asymmetric.py`, `cmd_vel_axis_adapter.py` (a different conversion, still needed), `scan_relay.py`'s mirror (a sensor-bearing reflection calibrated in `base_link`, which did not move), the URDF, and nav2's footprint and MPPI limits — all `base_link`-frame and all already correct.

**`tools/verify_axis_chain.py` — the answer stops being prose.** Every previous round of this question ended in a table in a document, and a table does not fail when someone edits the code. This runs the real chain — keypress → `sendDrive()` → teleop inverse kinematics → odometry forward kinematics → integration → published frame — and asserts `W→+Y, S→−Y, D→+X, A→−X`, plus the general invariant that a body displacement `(right, forward)` lands at `Rot(published_yaw)·(right, forward)` at seven arbitrary headings, so that correctness at zero cannot pass as correctness everywhere. It also guards the source text of all five touched files, and asserts the conversions that must *survive* are still present.

**It was mutation-tested, and the first version failed that test.** Reintroducing the exact old bug on purpose initially failed only the source-text guards while the numeric table still passed — because the table was checking the *test's own transcription* of the arithmetic, not the code's. Transcription is the same drift this entry is about. The publish-frame expressions are now parsed out of `odometry_publisher.py` with `ast` and evaluated, so the simulation cannot drift from the module. Re-run with the bug reintroduced, it fails 7 checks and reproduces the video exactly: `W → (+0.400, 0.000)`, `D → (0.000, −0.368)`, yaw −90°. A model that reproduces the observed hardware fault when given the fault is a model worth trusting about the fix.

**Dashboard verified headless** across phone (390×844), desktop (1900×950) and tall (950×1900), same standard as §17.36: HUD correct for six poses on all three, no JS errors, and the footprint now drawn tall with its heading arrow up where the video showed it wide with the arrow right. The grid-label helpers were rebuilt to clip each gridline in real screen space rather than assume a rotation, so they are correct at `DISPLAY_ROT = 0` and stay correct if it is ever set non-zero — the margin-label explosion bug of §17.36 cannot return by that route.

**CONFIRMED ON HARDWARE the same day.** The paragraph above originally ended by saying none of this had run on a robot. It has now, and every prediction held.

*The baseline first, because it is the half that is easy to skip.* Before deploying anything, `tf2_echo odom base_link` on the live node read **`-90.076°`** with the pre-fix file hash-verified in place (`143702e8…`). That is the fault measured on this robot, not inferred from the video or from the simulation — and it could not have been captured after the fix. The `0.076°` is accumulated drift; the `-90` is the constant.

*After deploying (`364c767f…` verified end to end, GitHub → PC → Pi → sha256 on arrival), rebuilding and restarting:* `[0.000, 0.000, 0.000]` at **`0.000°`**, rotation matrix exactly identity where it had been `[-0.001, 1.000; -1.000, -0.001]`. The constant is gone.

*Then the operator table, driven from the dashboard against `/wheel_odom`, with mapping deliberately NOT started* so that slam_toolbox, loop closure and the map frame were all out of the loop and only the changed code was under test:

| Key | Intended axis | Other axis | Cross-coupling |
|---|---|---|---|
| `W` forward | **y +0.1756 m** | x +0.0003 m | 0.2% |
| `D` right | **x +0.1723 m** | y −0.0010 m | 0.6% |
| `S` back | **y −0.1735 m** | x −0.0009 m | 0.5% |
| `A` left | **x −0.1935 m** | y +0.0012 m | 0.6% |

**The cross-axis terms are the second result and were not the thing being tested.** All four are under 1.2 mm on ~180 mm moves. A residual rotation left anywhere in the frame would appear as *systematic* cross-coupling proportional to the move; there is none, which is independent confirmation that the correction is exact rather than approximately right.

*The test was deliberately run on the dashboard that was already deployed* — fork #3, untouched by this session — rather than on the rewritten one. Fork #3 prints raw `x/y` and has `DISPLAY_ROT = 0`, both of which become correct once the frame is fixed, so the axes coming out right on a file this session never edited rules out the display simply agreeing with itself. Its map canvas drew the robot tall with its heading arrow up, where the original video showed it wide with the arrow right. Its one remaining artefact was predicted in advance and observed exactly: `NOSE 89.9°`, the leftover `+90` that existed to make the old `-90°` read as zero.

**Where this leaves it.** The frames are coherent, the claim is executable, and it has been checked against the robot at both ends — the fault measured before, the fix measured after. The cost is that every saved map — both commissioning candidates and the whole 70-map corpus — is frozen in the old frame; they stay geometrically valid, so `map_integrity.py`'s verdicts still mean what they meant, but a re-drive is required before Stage D regardless of what those verdicts say. **All five touched files are now deployed and hash-verified on the robot**, and the last two observable compensations were confirmed gone: the dashboard reads `NOSE 0.0°` where it read `90.0°`, and `tf2_echo map zero_point` reads `0.000°` with an identity rotation where it read `-90.000°`. The rebuilt grid-label helpers were incidentally confirmed on real hardware at a real viewport — `X` labels along the bottom increasing rightward, `Y` up the left increasing upward, robot drawn tall with its heading arrow up. Every one of the four compensations is gone and each was checked individually rather than inferred from the others.

**One deployment note worth keeping, because it cost a round trip.** A `scp` appeared to succeed — `100%`, no error — while the file on the Pi stayed at its old hash. The password had been typed onto the end of the destination path before Enter, so `scp` had faithfully created `mapping_full.launch.py<PASSWORD-REDACTED>` and reported success for it. **`scp` reporting `100%` says a file arrived somewhere, not that it arrived where you meant.** The hash check on arrival is what caught it, and it is the same discipline that caught §17.32's never-deployed config and §17.34's inert parameter file. Two files in the same batch landed correctly, which is precisely why a per-file hash beats a per-batch assumption.

## 17.39 27 Aug 2026: the square drive — the fix demonstrated end to end, and the problem it does not solve, caught on video

The closing run of the §17.38 session, and the first time this project has had a single artefact that shows both what was fixed and what remains. Recorded as a side-by-side video (physical robot left, live map right) plus a full run bundle, both committed: `docs/evidence/axis_frame_fix/` and `data/field_runs/run_20260827_140207_bundle.json`.

**The drive.** From the zero mark, `W → D → S → A` — forward, right, back, left — returning to the mark. **No `Q`/`E`, so no commanded rotation at any point**, which makes it a pure translation test of the frame. 535 s total, of which the square itself occupies 38 s.

**Segmented from wheel odometry, the four legs are each on a single axis:**

| Leg | Δ intended axis | Δ other axis | Δyaw |
|---|---|---|---|
| `W` forward | **+0.2741 m** on `Y` | +0.0001 m | −0.01° |
| `D` right | **+0.3673 m** on `X` | −0.0002 m | −0.06° |
| `S` back | **−0.3118 m** on `Y` | −0.0004 m | −0.04° |
| `A` left | **−0.4065 m** on `X` | +0.0012 m | +0.03° |

Cross-axis coupling peaks at 1.2 mm on a 407 mm leg — 0.3%. Total yaw drift across the whole square: **−0.10°**, confirming from the data alone that nothing rotated. Closure **2.58 cm**. The legs are unequal because the keys were held by hand for different durations; that is manual driving, and it means this run does *not* cleanly measure `lateral_scale` — that needs equal-duration legs and a tape measure, and is still owed.

**One number worth keeping for calibration anyway.** Leg durations give 49.6 mm/s forward and 45.8 mm/s lateral against a commanded 50 mm/s. That ratio, 0.923, is `lateral_scale`'s current value of 0.92 reproducing itself in the data — expected, since odometry applies it, so it is a consistency check rather than an independent measurement. Stated explicitly because it would be easy to mistake for a validation of the constant.

**The problem that remains, and this is the part worth the video.** At 17–18 s the pose card jumps from `X 0.114, Y 0.304` to `X 0.012, Y 0.013` — a **~31 cm discontinuity inside one 10 Hz sample**, while wheel odometry moved 5 mm. The bundle names it: jump event 3, `corr_m 0.327`, at map `(0.14, 0.30)`, verdict "pose graph moved, robot did not". Three such events occur, 0.327 / 0.386 / 0.416 m, all within the first minute, all with odometry stepping normally.

**The corrections imply drift that cannot have accumulated.** Computed from the run's own pose CSV against total odometry path driven at the moment each fired: 0.327 m after 0.447 m driven (**73%**), 0.386 m after 0.869 m (**44%**), 0.416 m after 1.300 m (**32%**). This robot's measured odometry error is **1.5%** over §17.32's 3.4 m box, 2.4% forward/back and 3.3% lateral (§17.30). And these are *conservative lower bounds* — `graph_residuals.py` measures against distance since the closed-on node, which is more recent than the run start, so a smaller denominator pushes every one of them higher. A closure correcting 73% of the distance travelled is not cancelling drift; it is inventing it.

**Two independent instruments therefore disagree about the same 38 seconds, and the disagreement is quantified:** wheel odometry closed the square to **2.58 cm**; SLAM's corrected map pose closed it to **6.2 cm**. Map path 2.47 m against odometry path 1.42 m — the extra 1.05 m is correction applied, and on this run the corrections made the closure **worse, not better**. That is §17.32's open question, unchanged, now with a video of the moment it happens.

**This is the distinction §17.38 was careful to draw, and here it is demonstrated rather than argued.** The axis fix was necessary and is correct; it had nothing to do with loop closure and could not have improved it. A run can have a perfectly coherent frame and an untrustworthy pose graph at the same time, and this one does. Anyone reading §17.38's confirmations as "mapping now works" has the wrong conclusion.

**Map verdict: SUSPECT, for reasons that are the drive's fault rather than the map's.** 9.8 × 6.7 m, 87% unknown, 15.6 m of wall. Two flags: only 38% of wall within 10° of the dominant axis, and 4 disconnected free-space regions. But **D2, doubled walls — the detector that actually carries the fold verdict — is essentially clean**: 4 cells, 0 clusters. This was predicted before the drive: a square with no rotation keeps the LiDAR's permanently blind rear 90° pointed at the *same world direction* for the entire run, so one whole side of the room is never observed. The flags are what that looks like in the metrics. **A non-rotating square is an axis test, not a commissioning drive**, and it was run as one.

**Wheels: nothing to report, which is itself the result.** All four within 0.015–0.016 rad/s RMS error, zero saturation, zero sign mismatches, arc spread ratio 1.00 between busiest and laziest wheel, zero anomalies. The mechanical side did not contribute to anything above.

**A deployment lesson, recorded because it cost a round trip and will recur.** A batch of three `scp`s reported `100%` and exited 0; only two arrived. The third had the password typed onto the end of the destination path before Enter, so `scp` faithfully created `mapping_full.launch.py<PASSWORD-REDACTED>` and reported success for *that*. The subsequent `colcon build` and restart silently used the old file, and the only reason it was caught is that the arrival hash was checked per file. **Two of three landing correctly is exactly why a per-batch assumption fails.** Now in `Important_Commands.md` §3.1, along with the new rule that all Pi↔Windows transfers stage through one folder in both directions.

**Where this leaves the project.** The axis and frame work is closed: deployed, measured at both ends, demonstrated on video, and guarded by `tools/verify_axis_chain.py`, which fails if any part of it is edited back out. Still open and untouched by any of it: loop-closure reliability (now with three fresh events to study), `lateral_scale`'s independent validation, `goal_pose_adapter`'s parameter against a live node, AMCL and Stage D, and — the headline — **there is still no accepted commissioning map.** The next drive is a perimeter run with the nose leading and rotation at the corners, which will also be the first hardware test of the frame at non-zero headings; that invariant is currently verified in simulation at seven headings and on hardware only at yaw ≈ 0.

## 17.40 27 Aug 2026 (evening): the jumps are the front-end scan matcher, not loop closure — two instruments agreeing leg by leg, and the "impossible drift rate" dissolved

The session set out to explain corrections implying 73% / 44% / 32% drift on a robot measuring 1.5% (§17.39). It found that the question was malformed, and that six sessions of loop-closure work (§17.28–§17.32) had been aimed at the wrong half of `slam_toolbox`.

**`graph_residuals.py` met the live node for the first time and immediately paid for itself, though not in the way it was designed to.** Transferred, hash-verified at `54b21d61…` end to end, self-tested clean on the Pi. Its first `--watch` run against a real drive exited with `RCLError: rcl_shutdown already called` — rclpy's own SIGINT handler shuts the context down before `KeyboardInterrupt` reaches the `except`, so the `finally` clause's `rclpy.shutdown()` always raises on `Ctrl-C`, and `log.close()` was sequenced after it and never ran. `Ctrl-C` is the documented way to stop `--watch`, so this fired on every use. Nothing was lost, because the writer flushes per line. The self-test could not have caught it: it returns before `run_live` and never touches rclpy. Fixed (`4ece40c`), redeployed, verified at `9ead3a6f…`, and the clean exit confirmed on the next run. **A tool that self-tests clean is not a tool that works; this one needed the node to find its only bug.**

**The finding, and the reason it is conclusive rather than suggestive: two independent instruments agree leg by leg on the same drive.** A W→S→D→A drive at 0.05 m/s, 153 s, `graph_residuals.py --watch` alongside the dashboard HUD read frame by frame off a screen recording:

| | `W`/`S` leg | `D`/`A` leg |
|---|---|---|
| HUD tracked to | **0.988 m** of a commanded 1 m, and back to 0.017 | jumps at X 0.357, 0.312, −0.313 |
| Corrections | **≤ 6 cm** | **0.336 / 0.302 / 0.240 m** |
| `NOSE` | 0.0° → −0.6° | −0.8° → **−11.8° → −13.4°** |
| Consecutive graph-node spacing | **0.37, 0.36, 0.36, 0.36 m** | **0.02, 0.00, 0.03 m** |
| Chain accumulated | **1.45 m** | **0.05 m** |

Same drive, same speed, comparable ground. Where the matcher tracks, nodes land 36 cm apart and the HUD follows odometry to within 6 cm. Where it fails, node spacing collapses to nothing and the HUD throws a third of a metre. **The graph-node collapse and the HUD jump are the same event observed twice, and they are per-leg co-located** — which is what raises this above the single-instrument arguments of §17.28–§17.31.

**`moved=0` and `max_shift=0.000` for the entire 153 seconds. Not one pose-graph node was ever moved by the optimiser.** A back-end re-solve — loop closure or otherwise — moves nodes. Nothing moved, while three corrections of 0.24–0.34 m occurred. **The corrections are the front end.** (`loops=0` on the same run is *partly* structural and should not be cited as independent evidence: with 8 nodes and `loop_match_minimum_chain_size` 8, an edge of span > 8 cannot exist. `moved=0` carries no such caveat.)

**The mechanism is `correlation_search_space_dimension`, and the corrections are saturating it.** Verified `0.7` against the live node, not read from a file. That permits each new scan to be placed up to ±0.35 m from the odometry prior, a square whose diagonal reaches 0.495 m. An earlier drive at 0.10 m/s threw **seven corrections measuring 0.36, 0.36, 0.37, 0.40, 0.42, 0.45, 0.40 m** — every one between the window's half-width and its diagonal reach. The magnitudes are set by the parameter, not by anything the robot did.

**Which is what dissolves §17.39's headline number.** 73% / 44% / 32% against a measured 1.5% was never a drift rate. An implied-drift-rate assumes the correction *cancels* accumulated drift; these corrections *overrule correct odometry*. A ratio whose numerator is bounded by a search window and whose denominator is distance driven has no reason to stay under 100%. Nothing was violating physics — the yardstick was measuring the wrong quantity. **`graph_residuals.py`'s implied-drift-rate remains the right instrument for a back-end closure and the wrong one for a front-end snap, and it cannot currently tell them apart on its own.**

**The premise behind `0.7` is stale rather than mistaken, which is worth separating.** Its comment justifies the widening on the grounds that "the odometry prior feeding this is itself imperfect", citing §17.21 — *before* `lateral_scale`. That same odometry has since closed a 4 m out-and-back to **4.3 cm (1.1%)** and §17.39's square to 2.58 cm. Between two nodes 0.36 m apart its expected error is about **4 mm**, against a window permitting **350 mm** — roughly 90× the uncertainty of the thing it is allowed to overrule. The configuration instructs `slam_toolbox` to distrust the most accurate instrument on the robot, and hands it 0.7 m in which to find something it prefers, in a space §17.13 characterises as self-similar radiating aisles with a permanent 90° blind sector (§17.15).

**A third recording, reviewed last and the sharpest of the three, tightens the mechanism and retracts a lead.** A 44.6 s `W`/`S` drive at 0.05 m/s (`docs/evidence/frontend_scan_matcher/01_ws_slow_three_resets.mp4`) resets three times, and read at 1 Hz the corrections are **0.340, 0.340, 0.340 m** — identical to the millimetre, against a `correlation_search_space_dimension` half-width of **0.35 m**. Three corrections that do not vary with anything the robot did, landing on the edge of the window the matcher is permitted to search, is the strongest single piece of evidence in this entry that the parameter sets the magnitude.

**It also costs the session its most attractive secondary lead, and that is worth recording as a caution rather than buried.** On the strength of the §17.40 drive alone — `W`/`S` clean, `D`/`A` throwing 0.24–0.34 m — *strafe is the weak axis* looked like a real finding, and a `scan_relay` reflection explanation was already being considered for it. This third recording fails on `W`/`S`, at the same speed, on the same day. **So the failure is intermittent, not axis-locked**, the one-drive asymmetry is a coincidence of sampling rather than a pattern, and a mechanism had very nearly been invented to explain a phenomenon that does not exist. The remaining unconfirmed observation is weaker still: *speed matters*, in that 0.10 m/s produced larger corrections (0.36–0.45 m) than 0.05 m/s (0.24–0.34 m), consistent with the window being reached more readily but not a controlled result. **Neither should be built on, and the strafe lead specifically should not be re-derived from the §17.40 drive in isolation.**

**Deployed state confirmed before any of the above, because a repo value is not a robot value.** All thirteen loop-closure and mapping parameters match Stage B against the live node, `enable_interactive_mode` included — which is what lets `graph_residuals.py` see nodes at all, and which §17.32 once caught at `true`. `src` and `install` hashes agree for all five §17.38 files, ruling out §17.39's stale-build failure mode. `tf2_echo odom base_link` reads `[0.000, 0.000, 0.000] @ 0.000°` with an exact identity rotation: the frame fix is in the running build, not merely in the source tree.

**§17.38's frame convention is now confirmed at metre scale**, where it had only ever been measured on ~180 mm moves. `W` → **+Y 1.002 m** with X pinned at ≤1 mm; `D` → **+X 1.038 m** with Y pinned at ≤2 mm. Leg speeds 0.101 and 0.093 m/s give a ratio of 0.921, `lateral_scale` 0.92 reproducing itself — a consistency check, not an independent measurement, since odometry applies it. **The user drove `W`/`S`/`D`/`A` only; `Q` and `E` were never pressed.** Every `NOSE` excursion above — to −14.2° at 0.10 m/s, −13.4° at 0.05 — is the matcher re-deciding the robot's heading while the robot did not rotate. Odometry's yaw stayed flat throughout.

**One correction to §17.38.** Its claim that "all five touched files are now deployed and hash-verified on the robot" is wrong: four of five. The Pi's `aislebot.urdf` is `31833ce0…`, exactly the pre-§17.38 blob. The §17.38 diff to that file is a single hunk, +12/−2, entirely inside the header comment; with every XML comment stripped, both revisions are byte-identical (7105 chars, same hash), so **the geometry never differed and nothing executed differently**. What is stale is the prose: the header on the robot still asserts the orientation-only −90° rotation that §17.38 removed. Deployment deferred rather than done, because a rebuild would have discarded the clean `[0,0,0]` odometry origin the session was measuring against. Same shape as §17.39's own lesson — there it was two of three, here four of five.

**Stage C, committed and not yet tested on hardware (`2a3e83b`):** `correlation_search_space_dimension` `0.7 → 0.3`. That keeps ±0.15 m, still ~37× the per-node odometry error, and makes a 0.24–0.34 m single-step correction impossible by construction. **Exactly one value changed**, verified by parsing both YAMLs rather than by reading the diff — §17.25 changed six at once and paid for it across three sessions. `distance_variance_penalty` (0.7) and `angle_variance_penalty` (1.2) rest on the same stale §17.21 premise and are the next step, deliberately not this one.

**The prediction, recorded before the test so it can fail.** Re-running the identical drive at the same speed: `D`/`A` corrections drop below 0.15 m and lateral node spacing stops collapsing → the window was the lever. Corrections reappear pinned near 0.15 m → the window only clamped the symptom, the matcher still prefers a wrong alignment, and the variance penalties are the real lever. The `W`/`S` leg degrades → over-constrained, back off to 0.5.

**All three recordings are committed** at `docs/evidence/frontend_scan_matcher/`, with a README carrying the frame-by-frame numbers: `01_ws_slow_three_resets.mp4` (dashboard, the three identical 0.340 m resets), `02_wsda_med_with_odom_terminal.mp4` (dashboard beside `tf2_echo odom base_link`, the 0.10 m/s worst case and the metre-scale frame confirmation), `03_wsda_slow_with_graph_residuals.mp4` (dashboard beside `graph_residuals.py --watch`, the `moved=0` run that carries the conclusion).

**Where this leaves the project.** The commissioning perimeter drive was deliberately *not* run. It was the session's stated goal, and holding it back was the right call: a 20-minute map built on a front end that loses a third of a metre on every strafe would have been a wasted drive and a misleading artefact. §17.28–§17.32's loop-closure conclusions are not refuted — they are **out of scope for these events**, which is a different and more useful statement. Their tuning may still matter for real closures on a long drive; it is simply not what has been producing the jumps.

## 17.41 28 Aug 2026: Stage C tested on hardware — the lateral collapse gone, and the mechanism confirmed a second time by making the corrections scale

The A/B §17.40 wrote down in advance, run against the identical drive with one parameter changed. `correlation_search_space_dimension` `0.7 → 0.3`, deployed to `~/ros2_ws/slam_nodom.yaml` (hash `e90aee53…` verified on arrival) and confirmed **`0.3` on the live node with `ros2 param get` before driving**, never from the file.

**The result, same drive, same 0.05 m/s, same instruments:**

| | baseline (window 0.7) | Stage C (window **0.3**) |
|---|---|---|
| Largest `D`/`A` correction | 0.336 m | **0.158 m** |
| Largest `W`/`S` correction | 0.060 m | **0.032 m** |
| Graph chain accumulated | 1.50 m | **3.07 m** |
| Collapsed node hops | 3 of 7 (`0.02, 0.00, 0.03`) | **none** — 9 hops, all 0.30–0.37 m |
| Forward metre reached | 0.988 m | **1.013 m** |
| Final map error | 0.379 m | **0.008 m** |
| Final `NOSE` | −12.4° | **−1.0°** |
| Pose graph | `moved=0` | `moved=0` |

**The lateral node collapse — the single sharpest symptom in §17.40 — is gone.** Nine consecutive hops between 0.30 and 0.37 m where three of seven had previously dropped to 2 cm or less. The same drive that registered 1.50 m of graph chain now registers 3.07 m, and the run finishes **8 mm from origin against 38 cm**: a 47× improvement in final map error.

**The result that matters more than the pass, because it is the mechanism rather than the outcome.** Largest correction divided by search half-width is **0.96** at a window of 0.7 and **1.05** at a window of 0.3. Change the parameter and the corrections scale with it, landing on the boundary either way. §17.40 inferred the magnitude was set by this parameter from one value; this sets it by a second value on command. **A hypothesis that predicts a number before the test, and then produces it, is worth more than one that explains a number afterwards.**

**But the fix bounds the failure rather than removing it, and that distinction should not be blurred.** Corrections still sit on the window edge, so the matcher still prefers an alignment away from odometry — it simply has less room to act on the preference. §17.40's predicted outcomes were written as three exclusive branches; the truth is branch 1 (the window was the lever) with a substantial component of branch 2 (the preference persists). `distance_variance_penalty` (0.7) and `angle_variance_penalty` (1.2) rest on the same stale §17.21 premise and remain the next lever, unchanged and deliberately untouched.

**An operator observation, honestly volunteered and correct.** The floor is uneven tile and the robot physically wandered during the lateral leg — roughly 6 cm back, then forward about 10 cm, retracing the same path on the return. The data separates the two cleanly. The slow `Y` walk during that leg (0.105 → 0.172 over several seconds) is consistent with real drift, faithfully tracked, and is not error. The two jumps are not physical: `Y −0.016 → +0.113` inside a single 1 Hz sample, with `X` moving **backwards** 0.045 m against the direction of travel and a simultaneous `NOSE` step. At a 0.05 m/s command limit the chassis cannot strafe 12.9 cm sideways in one second, and cannot move backwards while strafing right. **A rigid-body correction and a rough floor look nothing alike once both are on the same time axis**, which is the argument for reading the HUD at 1 Hz rather than by eye.

**A working note worth keeping.** `ros2 node list` is the honest answer to "is mapping running"; the dashboard's MAP button is not. The button restores its state on page load and the map canvas retains the last grid it received, so a page open across a `slam_toolbox` restart reads as actively mapping while nothing is. That cost a confusing five minutes at the start of this session, and `Node not found` from `ros2 param get` was the thing that exposed it.

**Where this leaves it.** The blocker on a commissioning map was a front end losing a third of a metre per strafe. That is now 0.15 m bounded, with the pose returning to within 8 mm of origin over a 3 m path. **The perimeter drive is no longer blocked.** Recorded at `docs/evidence/frontend_scan_matcher/04_wsda_slow_stageC_window_0p3.mp4`.

## 17.42 28 Aug 2026: the first long commissioning drive — 19 loop closures observed, the map FOLDED anyway, and the angular search window found holding the door Stage C closed

The first drive in this project's history long enough for loop closure to be structurally possible: 1047 s, 21.85 m of wheel path, 62 pose-graph nodes, 93 edges, a real hub-and-spoke traverse of the junction. **Nineteen loop closures fired** — the count has been zero in every prior session, because 8 nodes cannot contain an edge of span greater than `loop_match_minimum_chain_size` 8, so `loops=0` was guaranteed rather than observed. §17.28–§17.32's loop-closure question finally has data.

**And the map came back `FOLDED`, unusable for AMCL. There is still no accepted commissioning map.**

**The three numbers that matter, with the robot physically parked back on the zero mark:**

| | position error | heading error |
|---|---|---|
| Truth (on the mark) | 0.000 m | 0.00° |
| **Wheel odometry** | **0.229 m** | **10.53°** |
| **SLAM map pose** | **0.477 m** | **16.18°** |
| the `map→odom` correction itself | 0.271 m | 5.65° |

Odometry's 0.229 m over ~18 m is **1.27%** — dead on its measured 1.1–1.5% spec, on the longest drive it has ever been asked to do. Nothing is wrong with the wheels. **SLAM took that estimate and roughly doubled its error**, 2.09× on position and 1.54× on heading, applying **11.08 m of cumulative correction** across 21.85 m driven. §17.39's result (2.58 cm → 6.2 cm on a 38 s square) reproduced at five times the scale and in the same direction.

**The frame composition is exact and should stop being suspected.** `R(corr)·odom + corr` reproduces the map pose to the fourth decimal. §17.38's work is not implicated in any of this.

**Two instruments appeared to contradict each other, and reconciling them is the finding.** `graph_residuals.py --watch` reported `moved=0, max_shift=0.000` for all 645 s it observed, through all 19 closures. `run_analyzer.py` reported **48 correction events, 48 of 48 with wheel odometry stepping normally** — the Stage A signature, per event. Both are correct: the tool watches pose-graph *node positions* (the back end, which genuinely did nothing), while `map→odom` is also moved by the *front end*, which touches no node. **§17.40's conclusion stands: this is the front end.**

**But the corrections are 4.6× larger than Stage C permits, which is what exposed the real gate.** Largest single correction 0.696 m against a deployed translational search half-width of 0.150 m. That cannot be a translational snap. Checked against pure yaw about the map origin, `2·r·sin(θ/2)`:

| t+s | corr | yaw | r | predicted | ratio |
|---|---|---|---|---|---|
| 68.9 | 0.696 | **−18.40°** | 2.06 m | 0.660 | **0.95** |
| 59.8 | 0.500 | 15.00° | 2.13 m | 0.555 | 1.11 |
| 163.9 | 0.431 | 12.80° | 2.53 m | 0.563 | 1.31 |
| 77.6 | 0.388 | 12.00° | 2.30 m | 0.481 | 1.24 |
| 178.9 | 0.261 | −7.20° | 1.94 m | 0.244 | 0.93 |

**The large corrections are heading snaps whose position error is pure lever arm.** `coarse_search_angle_offset` is stock `0.349 rad = 20°`, never touched by Stage B or Stage C, and the largest correction's **18.40° is 92% of it**. Same saturation signature as §17.40 and §17.41, on the axis nobody had closed. Smaller events fit the model poorly (ratios 0.10–0.49), so translation still contributes at short range — the model explains 3.59 m of 4.80 m total, and is a description of the large events, not all of them.

**This also explains why Stage C looked like a clean win this morning and did not hold here.** The §17.41 A/B stayed within ~1 m of origin, where the lever arm is short and the error is mostly translational — exactly what Stage C bounds. This drive reached 3.5 m out, where the same angular error costs three to four times as much. **A fix validated near the origin was extrapolated to a drive that goes further, and the extrapolation failed** — worth recording as a methodological caution, not just a parameter note.

**Map verdict, and which detector carries it.** `FOLDED`: 10.4 × 10.0 m, 2668 occupied cells, 133.4 m of wall, 63% unknown (against §17.39's 87% — the rotating traverse worked as intended for coverage). **D2 doubled walls is 5.0% of wall cells across 5 clusters**, where §17.39's map had 4 cells and 0 clusters. That is the detector this project has trusted to carry the fold verdict, and this is the first time it has been dirty. D3 forks (16.27/10 m), D4 alignment (0.34), and D5 free-space fragmentation (6 regions) all flag too, but a self-similar radiating junction plausibly produces all three honestly; D2 does not.

**The doubled-wall gaps and the return-to-mark miss agree, independently.** Cluster gaps 0.23, 0.23, 0.38, 0.41, 0.53 m against a 0.477 m terminal miss. Two different instruments — one a spatial artefact in the saved grid, one a physical measurement against a floor mark — reporting the same half-metre.

**Weak but first-of-its-kind evidence for false closure.** `run_analyzer`'s cross-check found **3 corrections within 1.0 m of a doubled wall**. Its own verdict line calls this "a false closure with two independent witnesses." With n=3 and corrections of 0.364 / 0.208 / 0.058 m, this is **suggestive, not conclusive** — but it is the first co-location evidence the project has ever had, and it is exactly the signature §17.28's aliasing hypothesis predicts. The doubled-wall clusters sit *within* individual arms (two pairs 0.29 m and 0.38 m apart in the same arm), not *across* different arms, which argues against "matched the wrong aisle" and for "matched the right aisle at a drifted pose."

**Wheels: one number moved and it is not yet a concern.** All four motors 0.043–0.046 rad/s RMS, zero saturation, zero sign mismatch, no dead feedback. Travel spread **ratio 1.12** (FL 26.32 m, RL 29.46 m) against §17.39's 1.00 — but that run was a non-rotating square and this one rotated at every corner, which loads wheels unequally by construction. Not comparable, and not evidence of a mechanical fault.

**On the operator's question, recorded because the answer is structural.** Asked whether a more detailed per-wheel log existed that could give position from rotation alone, "nearly impossible to mess up." It exists — `run_*.csv`, 20940 samples at 20 Hz, per-motor target/actual/PWM — **and it is already the source of `odom_x/odom_y/odom_yaw`.** `odometry_publisher.py` integrates exactly those four wheel velocities. There is no more precise position further down the stack: the wheel data *is* the estimate, and its 1.27% error is physical slip, not computational. That sharpens rather than weakens the finding — the most trustworthy instrument on the robot said 0.229 m, and SLAM chose to disagree with it by 0.271 m.

**Where this leaves it.** Stage C is not wrong and should not be reverted; it closed the translational door and the §17.41 measurements stand. What it did not close is the angular one. `coarse_search_angle_offset` 20° and `angle_variance_penalty` 1.2 are both untouched and both rest on the same stale §17.21 premise as the parameters already corrected. The next step is Stage D on the angular gate, with one caveat that must be respected: `minimum_travel_heading` is 0.2 rad (11.5°), so the angular search cannot be cut below the inter-node heading change without risking loss of track during corner rotations — a real risk that Stage C's translational cut did not carry.

## 17.43 28 Aug 2026 (evening): the strategic review — a full-stack audit, the Stage D config written, and the architectural mistake nobody had named

A no-hardware session. The operator was off-site and asked for the whole repository and every prior session to be reviewed at once: where the project stands, how it becomes fully autonomous, what to do this week, and what to study for the 30 September review. Four documents were written as one package (`docs/Where_We_Stand.md`, `docs/Autonomy_Endgame.md`, `docs/APS_Study_Guide.md`, `docs/Vision_Indian_Market.md`) and are indexed at the top of `docs/README.md`. What follows is what the audit *found*, not a summary of what it produced.

**The architectural mistake, named for the first time.** Every navigation attempt in this project's history has been made *inside a live SLAM session*. `Production_Architecture.md` §3.1 already recorded, in August, that a saved map plus AMCL is the target — but it was filed as an eventual product decision, and in the meantime every autonomous drive kept being run against a map frame that was actively moving. On 28 Aug that frame moved **11.08 m across 21.85 m driven**. A goal is captured as a fixed coordinate in a frame that then slides underneath it while the robot drives. **That is the real explanation for the operator's "where I clicked and where the goal deployed are different" — and it is not a dashboard bug.** The click→world transform was verified exact to 1e-6 at device pixel ratios 1, 2 and 3 in headless Chromium; the arithmetic is right and the *frame the answer is expressed in* is what moves. Recorded here because it is the second time in this project a correct rendering path has been suspected for a fault living in the transform tree, and the §17.38 rule applies again: **never fix an axis or placement complaint in the dashboard.**

The consequence is a re-ordering of the roadmap. Fixing the front end is still required — but for **map quality**, not for navigation to work. Navigation needs a *fixed* frame, which means the critical path is: close the angular gate → get one accepted commissioning map → save it → switch to `map_server` + AMCL. Commissioning quality is a mapping problem; operating quality is a localisation problem; the project has been trying to solve the second by tuning the first.

**Stage D is written and committed, one parameter, hash `0e88d60c…`.** `coarse_search_angle_offset` **stock 0.349 rad (20°) → 0.175 (10°)** in `system/slam_nodom_stageB.yaml`, verified by parsing both YAMLs rather than reading the diff: 35 parameters before, 36 after, exactly one difference. Not deployed.

**§17.42's caveat on this parameter was re-examined and is judged conservative, with the reasoning written down so it can be wrong in public.** The caveat was that the angular search must not fall below `minimum_travel_heading` (0.2 rad = 11.46°). But the search is centred on the **odometry-propagated prior**, which has already rotated by the inter-node heading change before matching begins. What the window must cover is the *error* in that prior, not the rotation itself. Measured: odometry accumulated 10.53° over ~18 m = 0.58°/m, so across a 0.36 m node hop the prior's heading error is about **0.2°**. A 10° window is still ~50× that. **The risk is real but bounded and it has a distinguishing signature**: if the prior is ever worse than 10° — a wheel slipping through a corner rotation — the matcher loses track rather than snapping, and that failure looks *different* (map tears or pose freezes at a corner, instead of the pose jumping mid-leg). Pre-committed response: if corner rotations lose track, go to **0.25 (14.3°)**, above `minimum_travel_heading` — not back to 0.349.

**A second, unadvertised property of the last two stages, found while writing the theory up.** Candidate poses evaluated per scan scale as `(dim/res)² × (2·offset/angle_res)`. At the original 0.7 m / ±20° that is ~103 000 candidates; at Stage C + D's 0.3 m / ±10° it is ~9 900. **Roughly a 10× reduction in front-end search cost.** On a Pi already running its control loop at 7.5–13.7 Hz against a 20 Hz request, the accuracy fix is simultaneously a compute fix. Neither §17.41 nor §17.42 noticed this.

**A discrepancy found by auditing the kinematics, resolved, and deliberately not acted on.** Journal §2.5 and `odometry_publisher.py` give different yaw estimators. Both are unbiased — verified to 1.67e-16 over 20 000 random twists — and they are two *weightings of the same two measurements*. Rows 1 and 4 of the inverse-kinematics matrix (FR, RL) share the translational term `(u+v)`; rows 2 and 3 (FL, RR) share `(u−v)`. So each diagonal pair measures yaw independently on its own lever arm:

```
ω̂_outer = r(ω_FR − ω_RL) / (2·K_outer)      ω̂_inner = r(ω_RR − ω_FL) / (2·K_inner)
```

`odometry_publisher` publishes their **mean**; §2.5 publishes their **K-weighted mean** (note `l₁+l₂+2d = K_outer+K_inner = 1.05138` exactly). And — the result worth keeping —

> **the slip residual `s = ω_FR + 1.142656·ω_FL − 1.142656·ω_RR − ω_RL` is exactly `(2·K_outer/r)` times the *difference* of those same two estimates.**

Sum and difference of one pair of numbers: the yaw signal and its own error bar come from the same measurement, and this only exists as a non-degenerate pair *because* l₁ ≠ l₂. This is also a cleaner derivation of `wheel_forensics.py`'s residual than the Gram-Schmidt construction used when it was built — it is the null space of **Jᵀ**, obtainable in three lines of elimination. (The original error in that derivation is worth keeping too: the first attempt used null(**J**), which is a different subspace, and produced a residual of 1.72 on clean twists.)

Under equal per-wheel noise, minimum-variance weights go as K², i.e. (0.5663, 0.4337). Equal weighting therefore carries **+0.89%** yaw-rate noise standard deviation and §2.5's carries **+0.22%**. **Verdict: change nothing.** A 0.89% noise penalty cannot produce 10.53° of drift over 18 m; that drift is physical slip. Recorded as theory, explicitly rejected as an engineering priority — the distinction is the point.

**What the audit says is actually blocking, ranked.** (1) No accepted commissioning map — everything in `Production_Architecture.md` rests on one saved grid that does not exist. (2) The angular gate. (3) Pi CPU saturation, which degrades planner, controller and `collision_monitor` alike and reads as navigation bugs. (4) **AMCL has never executed once**, and `nav2_params.yaml`'s `robot_model_type: "omnidirectional"` is the pre-Galactic bare-string form where Jazzy expects `nav2_amcl::OmniMotionModel` — a plugin load failure aborts the whole `lifecycle_manager` bringup, exactly as in §17.17. That check is scheduled four days before the demo deliberately, not on demo day. (5) `xy_goal_tolerance: 0.02` is smaller than the estimate's own jitter.

**One thing the audit banked rather than found.** Rung C of the fallback ladder — tap a point during a live mapping session, robot plans and drives there — **already worked on 27 Aug**, twice, 25.9 s and 21.0 s. Whatever happens this week there is a working autonomous navigation demo in hand, which is what makes it reasonable to spend the week going for the saved-map version instead of protecting the one that exists.


## 17.44 29 Aug 2026: G1 and G2 passed, rotation in place found to map nothing, and three sessions of tuning spent against a degenerate test

Day 1 of `Autonomy_Endgame.md`'s week, and the first hands-on day since the strategic review. Six mapping sessions were driven. Two gates passed, one long-standing assumption about how to drive a commissioning map was destroyed, and the session's last three experiments turned out to have been run against a test geometry that cannot be tuned. Evidence in `docs/evidence/rotation_deadzone/`.

**G1 passed — the deployment debt is cleared and verified against the live node.** All four pending files transferred Windows → Pi and hashed individually on arrival: `slam_nodom.yaml` `0e88d60c…`, `phone_dashboard.py` `5b30a91d…`, `wheel_forensics.py` `27858ce4…`, `aislebot.urdf` `ea6619ff…`. Before deployment the live node read `coarse_search_angle_offset = 0.349` — stock 20°, confirming by measurement what `Where_We_Stand.md` §6 had on the operator's report. `colcon build` clean, `wheel_forensics.py --selftest` 6/6, and after a fresh MAP the live node read **`0.175` and `0.3`**. The angular gate is closed on hardware for the first time in this project. Four analysis tools already on the Pi (`graph_residuals.py`, `run_bundle.py`, `map_integrity.py`, `run_analyzer.py`) hash-matched the repo exactly; only `wheel_forensics.py` was genuinely absent.

**Odometry re-verified before anything was believed, and it is the best instrument on the robot.** A 30 s nudge with `tf2_echo odom base_link` running: forward → **+Y** (0.011 → 0.378 m), cross-axis X held **0.000–0.001 m** across a 0.378 m out-and-back, yaw ≤0.041°, and the return closed to **1 mm**. Every subsequent finding rests on odometry being trustworthy, and it earned that repeatedly through the day — wheel closures of 0.074 m over 18.1 m (0.41%), then 0.019, 0.013 and 0.008 m on the short runs.

**G2 passed on the 621 s commissioning drive (`run_20260829_144619`).** Maximum correction **0.2018 m** against a <0.30 m gate; largest heading step **4.57°** against <10°. On 28 Aug the same measures were 0.696 m and −18.40°. Cumulative correction per metre driven fell from 0.507 to **0.163 m/m**, a 3.1× reduction. The discriminating detail is that 4.57° is **46% of the new 10.03° window**, where 18.40° was **92% of the old 20° one** — if `0.175` were merely clamping the symptom the corrections would have pinned to the new boundary, and they did not. §17.42's angular-saturation hypothesis is confirmed and the lever is real. **Caveat recorded honestly:** G2 specifies a repeat of the 1047 s traverse and this was 621 s / 18.14 m against 21.85 m, so it passes the stated numbers on a smaller test than the gate asks for. The map still came back **FOLDED** — D2 doubled 1.9% against a <1.0% gate, though down from 5.0% — and return-to-mark 0.257 m against <0.15 m. **G4 remains unmet; there is still no accepted commissioning map.**

**The finding of the day: `slam_toolbox` adds no pose-graph node and no map cell while the robot rotates in place.** It surfaced as an anomaly in the opening of the commissioning drive, where `graph_residuals.py` sat frozen at `n=7, e=7, driven=1.89 m` for **72 seconds** while the dashboard pose card swept ~250° of accumulated rotation at a steady 5.7°/s. `minimum_travel_heading` was 0.2 rad (11.46°) and should have fired ~21 times. The initial hypothesis — that `/scan_reliable` had stalled — was **killed by measurement**: the topic publishes at **11.4 Hz**, std dev 0.005 s, over ~170 windows, and the node log's only hits are `foxglove_bridge` channel churn tracking MAP start/stop. A deliberate test then reproduced it cleanly: **two full turns in place, 714° over 642 s, produced 43 occupied cells = 2.1 m of wall and zero corrections.** Ten and a half minutes of sweeping a room for two metres of wall.

**`minimum_travel_heading` was falsified as the gate, by direct test.** Set to **0.05** on the live node and verified there, a full 360° in place produced **`n=1, e=0` for 166 seconds** — the first scan of the session accepted and not one more — and 45 cells against a 43 baseline. The threshold is not what blocks rotation. A mechanism is proposed but **not verified against source and must not be cited as fact**: `slam_toolbox`'s own `shouldProcessScan()` gate runs ahead of Karto's `HasMovedEnough()` and tests only squared *distance*, with no heading term, so a pure rotation never reaches the threshold that `minimum_travel_heading` governs. It predicts every observation made, which is why it is written down, and it is a hypothesis until somebody reads the installed source.

**The consequence is that the commissioning drive procedure has been wrong since §17.39.** "Perimeter, nose leading, rotating at every corner so the LiDAR sweeps every wall" was adopted specifically to solve the rear-blind 90° cone. **Those corner rotations contribute nothing** — no scans, no nodes, no cells. This is a better explanation for maps returning 63–87% unknown than anything previously considered, and it means **G4 was never reachable by that method.** The rear cone is still blind and the problem it causes is still real; the remedy has to change from stop-and-spin to turning while rolling.

**Turning *while translating* works, and the size of the effect is the cleanest number of the day.** Holding `W`+`E` together — the dashboard accumulates held keys in a `Set` (`phone_dashboard.py:975–999`), so forward and yaw combine into an arc — produced `n` climbing 1 → 18 with nodes every 0.09–0.15 m:

| run | duration | body path | nodes | occupied cells | wall |
|---|---|---|---|---|---|
| pure rotation, 714° | 642 s | 0.09 m | **1** | 43 | 2.1 m |
| **W+E arc** | 111 s | 3.20 m | **18** | **1545** | **77.2 m** |
| perimeter drive | 621 s | 18.14 m | 48 | 1761 | 88.1 m |

**88% of the perimeter drive's wall coverage in 18% of its time and 18% of its distance.**

**The sharpest result, and the one that reframes the front-end problem: one correction per node, every node.** The Stage E arc recorded **18 nodes and 17 corrections**, with correction timestamps spaced **3.65 s** — the same cadence as node additions in the watcher, and confirmed independently in video by sampling the drawn trail region, whose frame-to-frame change alternates between ~480 (smooth drawing) and 700–2800 (a leap) on a ~3.7 s period. This is not occasional false closure. **The matcher disagrees with wheel odometry by 0.15–0.37 m on every single scan it accepts.**

**The operator's "why is the trajectory spiky and not a circle" has a numeric answer, and it is the correct question.** The trail is drawn in the `map` frame, `map→base_link = map→odom ∘ odom→base_link`; odometry traced a smooth 3.20 m circle and `map→odom` jumped underneath it 17 times. **SLAM path 5.63 m against a wheel path of 3.20 m — the 2.43 m difference is the spikes**, and it agrees with the 2.86 m cumulative correction. The follow-up question — whether the display should be made to draw a clean circle instead — was **declined**, and the reasoning belongs in the record: smoothing the trail would have deleted the only signal that revealed the per-node disagreement. This is standing rule #5 and §17.38 is the precedent, where four separate −90° display compensations hid a real frame fault for two weeks. **The display is correct; the robot is wrong.**

**Three parameter sets, one invariant, and Stage E's answer is no.** The same tight arc was driven three times:

| | arc 1 | arc 2 | arc 3 (Stage E) |
|---|---|---|---|
| `minimum_travel_heading` | 0.2 | 0.1 | 0.1 |
| `angle_variance_penalty` | 1.2 | 1.2 | **0.6** |
| max correction | 0.367 m | 0.229 m | 0.366 m |
| max heading step | 10.42° | 5.71° | 10.23° |
| **cumulative correction** | **2.80 m** | **2.85 m** | **2.86 m** |
| return to mark | 0.292 m | 0.282 m | 0.276 m |
| wheel closure | 0.019 m | 0.013 m | 0.008 m |

Halving `minimum_travel_heading` halved the largest heading step exactly as predicted and pulled the maximum correction back under the G2 threshold — and changed the total not at all. Lowering `angle_variance_penalty` then undid that gain and left the total where it was. **Cumulative correction is invariant to within 2% across every parameter set tried.** The tuning moves the distribution of the error and never the amount, which is the signature of something the search parameters do not reach.

**The reason, proposed here as a hypothesis and as a methodological warning: the circle is a degenerate geometry for scan matching, and three experiments were spent on it.** The robot circles inside a ~1 m disc at the centre of a ~10 m space, matching against walls several metres out. At 5 m range **1° of heading error is indistinguishable from 8.7 cm of translation**; rotation and translation stop being separable, and the matcher resolves the ambiguity in favour of heading — which odometry pins down well — dumping the residual into position. It predicts the measured signature exactly: **heading right to ~4°, position 27.6 cm out, wheels closing to 0.008 m.** It also explains why no search or penalty parameter moved the total, because conditioning is not a search problem. Against this, the perimeter drive — real translation, walls at 0.5–1.5 m — gives **1.0 corrections/m and a 0.202 m maximum**, where the circle gives **5.3/m and 0.367 m**. **The perimeter drive was the good case all along, and the day's last three tests optimised against a bad proxy for it.** §17.41's lesson recurs in a new costume: a fix validated on one geometry does not transfer to another, and this time the failure was choosing the benchmark rather than extrapolating from it.

**Two `run_analyzer.py` false positives, both firing on every arc drive, both wrong.** First, *"one wheel did much less work than another — slip, or a mechanical problem"*, on ratios of 37–56:1. It is geometry: left wheels 6.29/6.73 m against right 0.37/0.12 m gives a mean of 3.4 m ≈ the 3.2 m body path, a yaw of 6.25/(K_o+K_i = 1.05) = 5.95 rad = **341°**, and a radius of **0.54 m** — while `K_o` is **0.56069 m**, so the instantaneous centre of rotation landed on the right-hand wheels and they sat at the pivot. All four motors read 0.024–0.035 rms with 0% saturation and 0% sign error in every run. The heuristic assumes near-straight driving. Second, *"a false closure with two independent witnesses"*: all seven flagged corrections referenced the **same** 4-cell doubled wall — one wall counted seven times — and on a 1 m circle the whole trajectory sits inside the 1.0 m coincidence radius, so the test has no discriminating power at that geometry. Both need guards; neither was patched today, deliberately, because changing an instrument mid-campaign destroys the baseline it is being compared against.

**A blind spot quantified for the first time, and correctly not chased.** After 714° of rotation in place the robot was tape-measured **3 cm right, 2 cm back = 3.6 cm** from the mark while odometry and SLAM both reported 0.001 m. Encoders cannot see slip, so odometry's blindness is expected; SLAM's is not. But the magnitude is ~0.45 cm per 90° of turn, at most ~14% of the terminal error on an eight-corner drive. **Real, measured, small, filed.**

**One measurement error made and corrected in the same session, recorded so it is not repeated.** Map coverage during the two-rotation run was initially judged to be *growing*, from a dark-pixel count over the dashboard's map region — a metric that counted trail lines and UI chrome as occupancy. The saved grid, 43 cells, is the truth and it overrode the estimate. **Do not derive map coverage from a screenshot.**

**Where this leaves the critical path.** The angular gate is closed and G2 is passed. The blocker is no longer a search parameter — it is that every commissioning drive so far has been driven with a procedure that discards its own corner observations, and that the last three diagnostic runs measured a geometry the matcher cannot resolve. The next drive is a perimeter traverse hugging the walls at 0.5–1.5 m with **rounded corners taken while rolling**, on the unmodified G2 configuration, with no parameter changes carried over from the circle work.

**A hardware addition proposed at the end of the day and declined, with the reasoning recorded so it is not re-opened casually.** The operator asked whether a USB webcam — or two, angled to approximate the LiDAR's coverage — mounted below the LiDAR on the same axis would help. **No, and the first objection is decisive: `slam_toolbox` is 2D laser SLAM and has no camera input.** Frames from a webcam would reach nothing in the stack. Consuming them for SLAM means replacing `slam_toolbox` with a visual or visual-inertial system, which is a re-architecture seven days before the demo, aimed at a fault whose cause was identified today and whose remedy costs nothing. Three supporting objections: the Pi's control loop already runs **7.5–13.7 Hz against 20 requested**, so two camera streams would worsen a measured blocker; two UVC devices on one Pi bus routinely fail to negotiate simultaneously at usable resolution; and matching a 360°-minus-90° laser field would need four cameras or fisheyes, none of which reach the matcher. The rear blind cone is real but is **not** what was blocking the map — the corner rotations were, and that is fixed by driving differently. **Same reasoning as the 22 Aug IMU decision**: do not add a sensor that does not address the measured fault. Revisit only if visual SLAM becomes a deliberate direction after the demo; an onboard POV camera for report footage is worth doing then.

**Session closed with the next measurement chosen rather than the next parameter.** `scan_quality.py` — self-tested, and the one instrument in this project that has **never met real data** — measures exactly the quantity the degenerate-geometry hypothesis predicts: geometric conditioning as `λ_min/λ_max` over surface normals, with the bearing of the weak direction, thresholds `< 0.15` poor and `< 0.35` marginal. Its own header, written before that hypothesis existed, names the failure mode: *"Two parallel walls put every normal on one axis, so the scan slides freely along the other and the matcher has nothing to stop it."* The plan for the next session is to capture it at two positions — on the zero mark in the open, and parked within ~0.7 m of a wall — and compare. **Predicted before the test: poor in the open middle, better near the wall.** If it holds, the hypothesis becomes measured, and it also answers the operator's practical question of which parts of the lab the robot can localise in at all.

## 17.45 31 Aug 2026: `scan_quality.py` meets real data at last — the position prediction fails in both directions, and an unpredicted instability shows up instead

Monday's S0, before any driving. Two positions, on the deployed G2 configuration, MAP already running from the prior session (health check confirmed nothing pending deployment — same hashes and live params as 29 Aug's close-out).

**A measurement mistake made and caught before being treated as data.** The first "near wall" capture was run without moving the robot — it was the zero mark measured twice. Caught because the two readings were suspiciously close (conditioning 0.739 vs 0.721, weak axis 99.8° vs 100.0°, valid_pct 47.4% both), which in hindsight is itself a useful fact: **the tool reproduces closely on a genuinely unchanged position**, so the numbers below aren't sampling noise. The robot was then actually relocated — dashboard confirms `X −0.022, Y 0.703, NOSE −0.3°`, ~0.7 m off the mark — and re-captured.

| | mark (open, n=2 captures) | ~0.7 m from a wall |
|---|---|---|
| conditioning | 0.739 / 0.721 | **0.537** |
| weak axis | 99.8° / 100.0° | 90.5° |
| valid rays | 47.4% | 52.8% |
| range p50 / <1 m | 1.6 m / 12.2% | 1.0 m / 53.3% |
| stationary noise (median / p90 / max) | 7.5 / 22.8 / 79.9 mm, 6.8 / 24.5 / 47.9 mm | **2.1 / 13.0 / 25.9 mm** |
| flicker | 74.8% / 78.0% | **57.0%** |
| verdict | UNSTABLE (noise + flicker) | UNSTABLE (flicker only — noise now under the 15 mm gate) |

**The pre-registered prediction — "poor in the open middle, better near the wall" — is falsified in both halves, not confirmed. `MEASURED`, retracted as stated.** The open mark came back well-conditioned (0.739, comfortably above the 0.35 marginal line), and near the wall came back *worse* (0.537) — still above marginal, so neither position is flagged POORLY CONSTRAINED by the tool's own criteria, but the direction of the effect is the opposite of what was predicted. A candidate reason, **hypothesis only**: sitting 0.7 m from one wall lets that single nearby surface dominate the point count, so its one normal direction outweighs the more varied bearings visible from the middle — the same aliasing mechanism the tool targets, just triggered by proximity rather than distance. Untested against a third position.

**What the test actually found instead was not on the original question.** Stationary stability — the discriminator the tool's own docstring calls out as measuring "the matcher is fed a moving target" — comes back **UNSTABLE at both positions**, driven by two things: a majority of rays flicker valid/invalid scan-to-scan while the robot is completely still (74.8–78.0% in the open, 57.0% near the wall), and among the rays that stay valid every scan, per-ray range noise exceeds the tool's 15 mm gate in the open (p90 22.8–24.5 mm, max up to 79.9 mm) though it clears the gate near the wall (p90 13.0 mm). **`MEASURED`, new to this project** — this is the first time this instrument has seen real data, and it was not what the degenerate-geometry hypothesis was about at all.

**Checked before trusting it: is this the pipeline, or the sensor?** `scan_relay.py`'s angle correction is a **static index permutation**, built once per scan-geometry key and cached — the same remap applied to every message, no per-scan randomness — and its self-occlusion mask writes `NaN`, which `scan_quality.py`'s own `valid_mask()` correctly excludes from the flicker accounting (confirmed against source: the masked ~90° arc shows up correctly as the `largest_gap_deg` ≈ 90–96° sanity check in every capture, not as flicker). That rules out the one piece of software between the raw driver and this measurement as the source of the instability. **Reasoned, not fully verified** — `ydlidar_params.yaml`'s `abnormal_check_count: 4` is an internal SDK filter with no visible source here, so the driver's own de-noise pass is not eliminated as a contributor.

**Stability improving near the wall on both measures (noise and flicker) while conditioning gets worse there is not a contradiction — they are different axes of the same instrument, and the data disagreed with the prediction on one and not the other.** Stronger, closer, more consistent returns near a wall plausibly explain the cleaner stability numbers; the same proximity plausibly explains the worse conditioning, by the single-surface-domination mechanism above. Both halves are **hypothesis**, not settled.

**One repeatable detail across all three captures, not yet leaned on:** the weak axis bearing sits at 90–100° in the sensor frame at every position tried, including two different physical locations. With `NOSE` near 0° at capture, the sensor frame is close to the map frame, so this could be a real, position-independent feature of the room's shape (an elongated space with one dominant wall-normal direction) rather than a property of where the robot happened to be standing. **`HYPOTHESIS`, n=2 positions — not enough to separate "room shape" from "coincidence."**

**Not used as evidence, per standing rule #10:** the dashboard's live map view during this test showed scattered, salt-and-pepper occupied cells rather than clean wall lines — visually consistent with a matcher accumulating flickering per-ray returns, but a screenshot is not the saved grid and is not cited as a finding here.

**Where this leaves S0.** The instrument works and has now met real data twice, cleanly. It did not confirm the hypothesis it was built to test — position alone does not make the room's centre poorly conditioned — but it surfaced a second, independently plausible contributor to the front-end problem (`Where_We_Stand.md` §2 layer 6) that nothing had measured before: the raw scan is not standing still even when the robot is. Whether that instability actually lines up in time with real correction events is the next question, and it is untested — the S0 captures were taken with the robot stationary and idle, not against a live drive's correction log.

## 17.46 31 Aug 2026: `run_analyzer.py`'s two false positives fixed, deployed, and confirmed against the exact runs that exposed them

Kickoff §6 items 1 and 2, done idle with no driving. Both were self-tested against hand-built inputs reproducing the real 29 Aug numbers, then deployed (hash `74387d55…`, matched Windows to Pi) and re-run against `run_20260829_155447` and `run_20260829_164017` — the same two files whose *before* output (captured first, on the still-deployed old script) is what motivated the fix in the first place. `MEASURED`, real-data attribution, not just a self-test claim.

**Guard 1 — turn-rate context for the wheel-spread alarm.** Added `turn_context()`: curvature = integrated odometry yaw / path driven, its reciprocal the implied turn radius. Before: both runs' 56.08:1 and 39.59:1 wheel-travel ratios printed *"one wheel did much less work than another — slip, or a mechanical problem."* After: both now read *"expected for a tight turn: curvature 1.97 rad/m implies a 0.51 m radius... not flagged as slip"* — recovering the same ~0.5 m radius §17.44 derived by hand from the wheel-travel geometry, this time straight from odometry on every run rather than a one-off calculation. A synthetic wide-corner case (90°/18 m) confirmed the guard does not suppress unconditionally — a genuine non-tight 40:1 spread still prints "investigate."

**Guard 2 — distinct-cluster and extent guards on the doubled-wall co-location check.** Before: `run_20260829_164017` printed *"7 correction(s) happened within 1.0 m of a doubled wall — two instruments pointing at the same place, which is the strongest false-closure evidence available here"* — all seven referencing the same 4-cell/0.31 m-gap cluster, exactly the §17.44 finding this was built to catch. After: the check is **suppressed outright** on both real runs, because `trajectory_extent_m()` (bounding-box diagonal of the whole map-frame path) measured **0.66 m and 0.67 m** — both under the 1.0 m coincidence radius — so the note now reads *"co-location check suppressed: the trajectory's own extent... is no bigger than the coincidence radius, so every point on it is trivially 'near' every doubled wall."* This is a stronger outcome than the synthetic self-test alone showed (which exercised the distinct-cluster count on a larger fabricated trajectory): on the actual data, the simpler extent guard fires first and removes the false claim entirely, which is itself direct confirmation of §17.44's own explanation for why the check produced "seven witnesses" out of one wall.

**What did not change, correctly.** Both runs still verdict `MAP FOLDED` and `NOT USABLE for AMCL — redo the drive`. The fix removed two false alarms; it did not, and should not, touch the real finding underneath them. Neither run was a candidate for G4 regardless — both are the circle-geometry diagnostics §17.44 explicitly says were spent on a degenerate test, not commissioning drives.

## 17.47 31 Aug 2026 (evening): two recon legs on one configuration, a 6.8× spread between them, and the first return-to-mark inside the G4 gate

The commissioning drive was **not** driven today. What was driven instead were two ~165 s reconnaissance legs, and they turned out to matter more than the errand they were sent on. Evidence and both videos in `docs/evidence/monday_recon/`.

**Why recon at all.** The drive plan needed usable floor dimensions, and the room turns out to be **cross-shaped** — variable width, no single length × width to tape-measure. The operator's alternative was better than the request: a camera fixed to the mast looking straight down, with the floor's **62 × 62 cm tiles** (tape-measured) as an embedded metric ruler, so distance comes from counting tile-line crossings rather than from commanded speed × elapsed time, which assumes no slip. One leg out to the obstacle in `+Y`, one in `+X`, each returning to the mark. The zero mark, axes and NOSE direction are recorded on a photographed floor plan: **NOSE points toward the Entrance, and that is `+Y`.**

**The result nobody was looking for.** Same deployed configuration, same afternoon, same operator, same driving style — mixed straight / wall-hugging / turn-while-rolling / strafing, no stop-and-spin anywhere — and the two legs came back **6.8× apart on return-to-mark**:

| | front leg (`155316`, +Y) | right leg (`191509`, +X) | G4 gate |
|---|---|---|---|
| wheel path | 9.61 m | 8.00 m | — |
| **return to mark** | **0.577 m** | **0.085 m** | < 0.15 m |
| wheel closure | 0.028 m | 0.019 m | — |
| max correction | **0.678 m** | 0.280 m | (G2: < 0.30 m) |
| net correction | 0.576 m | 0.072 m | — |
| cumulative ÷ wheel path | 0.562 m/m | 0.305 m/m | — |
| corrections | 21 | 13 | — |
| D2 doubled | 5.1% | 5.2% | < 1.0% |
| unknown | 73.8% | 79.4% | < 50% |
| verdict | FOLDED | FOLDED | not FOLDED |

**The right leg returned to the mark at 0.085 m — the first drive in this project's history to land inside G4's return gate.** ✅ **measured.** Its largest correction also sits under the G2 threshold. The annotated maps show why: on the right leg the SLAM path and the wheel path run nearly on top of each other; on the front leg they separate into a loop.

**The front leg is the worst front-end performance recorded since the Stage D fix.** 0.678 m maximum correction against a G2 gate of 0.30 m, and **0.562 m of cumulative correction per metre driven — worse than the 0.507 m/m pre-fix baseline Stage D was built to cure**, on the configuration that passed G2 four days earlier. G2 passing once on one geometry is not a property of the robot; it was a property of that drive.

**What must not be concluded from this.** ⛔ Not "`+X` is good, `+Y` is bad." That is precisely the shape of **"strafe is the weak axis," retracted 29 Aug** when a third recording failed on the `W`/`S` leg at the same speed on the same day. This is n=1 per direction, on two physically different routes. Three explanations remain live and this data cannot separate them: **geometry** (the front leg threads a narrow furniture-flanked aisle traversed twice in opposite directions minutes apart, which would extend §17.44's degenerate-geometry hypothesis from tight turns to narrow aisles — 🔷 hypothesis); **direction/axis** (the retracted shape); and **intermittency** (✅ already measured to exist on 29 Aug, and on its own sufficient to produce a 6.8× spread). **The separating test is cheap and is the first thing owed tomorrow: drive each leg a second time.** If each reproduces its own number it is route/geometry and route planning can help; if either flips it is intermittency, and no route plan rescues G4.

**A procedural fault that nearly contaminated the analysis.** The front leg's MAP session had been running since before S0, so its saved pose log spans **2246 s** of which only the first ~166 s contain motion. Analysed untrimmed, `duration_s` and every correction-step percentile are meaningless. Caught because the log duration and the video duration disagreed by 13×. **Trim to the moving window before reading any run.** The idle tail did pay for itself once: across ~2080 s parked, the pose graph produced **zero** corrections — consistent with §17.44, and it establishes that S0's measured scan instability does **not** leak into corrections while the robot is stationary.

**A third `run_analyzer`-family false positive, found and deliberately not patched.** `run_report.py`'s *"Diagonal mismatch is visible"* fired at FR−RL 1.214 / FL−RR 1.070 rad/s against a fixed 0.3 threshold. Read from source, it is `RMS(FR_actual − RL_actual)` and `RMS(FL_actual − RR_actual)` — and on a mecanum chassis those diagonal pairs are exactly what carries strafe and yaw, so a drive that deliberately strafed and turned makes them large by construction. Against it: all four motors 0.076–0.082 rad/s tracking error, 0% saturation, 0% sign mismatch, travel ratio 1.11. The threshold appears to date from a straight-line open-loop stutter investigation. **Scheduled, not patched** — standing rule #9 forbids changing an instrument mid-campaign without re-baselining, and the campaign is live.

**Where this leaves the week.** Three of Monday's four items are done (§2 health check, §4 S0, §6 items 1–2, all logged above). **The fourth — the commissioning drive itself, the only one that moves G4 — was not driven.** G4 has four sub-criteria; exactly one of them has now been met once, and the three map-quality ones (not FOLDED, D2 < 1.0%, unknown < 50%) have never been met in this project's history. Four working days remain before the 5 Sep demo, and Phase 2 (AMCL, point-and-go) has still never executed and is gated on a map that does not exist.

## 17.48 1 Sep 2026: the repeat test resolves in favour of intermittency, and the project splits onto a second branch

Tuesday's session, short. One drive — §17.47's repeat test, front leg re-driven — plus a strategic decision at the end. Evidence in `docs/evidence/tuesday_repeat/`.

**The repeat test's own prediction, written down before driving:** reproduce near 0.577 m/0.678 m (route geometry) or move toward the right leg's 0.085 m/0.280 m (intermittency). **Neither happened.** `run_20260901_112335` — same aisle, same style, same deployed config — returned **0.209 m** with a max correction of **0.857 m**, the single worst correction recorded in this project's history, exceeding even the pre-Stage-D baseline.

| | Front (31 Aug) | Front (repeat, 1 Sep) | Right (31 Aug) |
|---|---|---|---|
| Return to mark | 0.577 m | 0.209 m | 0.085 m |
| Max correction | 0.678 m | **0.857 m** | 0.280 m |
| Cumulative ÷ path | 0.562 m/m | 0.484 m/m | 0.305 m/m |

**A third distinct number on the identical route is the cleanest evidence this project has produced that the spread is intermittency, not geometry.** A stable route/geometry story predicts reproduction; this instead shows the SLAM front end varying run to run on the *same* aisle, better on some measures and record-worse on another. ✅ **measured.**

**`graph_residuals.py --watch`, run alongside, again confirms the back end is not the fault.** 9 loop closures fired over the 230 s drive; `moved=0`, `max_shift=0.000 m`, every closure at 0.0% implied drift, start to finish. The map's internal consistency is fine. The estimate the operator actually sees — `map→odom` — is where all of tonight's variance lives, same conclusion as §17.40 and §17.42, now on a fourth independent drive.

**The actual S1 commissioning drive was set up and not executed.** Robot re-zeroed, MAP restarted, the wide-outer-wall-perimeter instructions given — and the session ended there. G4 was not attempted today beyond the repeat test. It remains at exactly one of four sub-criteria ever met, once, on 31 Aug.

**The strategic decision, made explicitly rather than by default.** Rather than continuing to spend the remaining time-box exclusively chasing G4, the project now runs on **two branches in parallel**: this branch continues SLAM reliability work as issues surface, while a new branch and session begin building **autonomous drive-to-goal with real-time obstacle detection and avoidance** — MPPI + local costmap + `collision_monitor`, all of which `Where_We_Stand.md`'s fallback table (§8) already establishes work **without needing an accepted map**. The hard requirement carried into that branch: **a detected obstacle must stop the robot regardless of an active goal, using the already-configured cushioning/inflation value** — the safety chain takes priority over goal-seeking, not the reverse. This is not G4 declared solved or abandoned; it is Nav work no longer waiting on it, per the reasoning `Next_Session_Kickoff.md` §11 wrote down in advance for exactly this situation.

## 17.49 1 Sep 2026 (evening): the tape measure closes the loop — the front end is a navigation problem, proved twice from opposite ends

The first session on the autonomy branch. No commissioning drive, no G4 attempt, and by a distance the most conclusive day this project has had about what is actually wrong — because for the first time the evidence came from **outside the software**.

**The headline, and it is not a hypothesis.** Two runs, two tape measurements, and a chain verified to four decimals in both:

| | 18:48 — Nav2 drove | 19:38 — operator drove |
|---|---|---|
| odom path | 4.27 m | 4.58 m |
| **odom closure** | 10.4 cm | **0.3 cm** |
| **map closure** | ~0 cm | 6.0 cm |
| **tape** | **9 cm right of the mark** | **on the mark** |
| net `map→odom` | 0.114 m | 0.064 m |
| peak `map→odom` | 13.0 cm | **20.3 cm** |

**The two runs measure the same error from opposite ends, and that is what makes them decisive.** Nav2 closes its loop on the map pose, so it physically drives the robot until the corrupted estimate reads zero — the map closes and the error lands *on the floor*. Drive the same route by hand and the robot is physically correct, so odometry closes and the error stays *in the estimate*. Either way it is 6–20 cm and it is the front end's. ✅ **MEASURED**, and independent of every instrument in this repo.

**Wheel odometry agreed with the tape to about a centimetre on both runs**, and on the hand-driven one closed **4.582 m to 3.1 mm — 0.07%**, the best closure recorded in this project. §17.44's W+E circle closed to 3.3 mm over ~3 m; this is consistent and better. Layer 5 of `Where_We_Stand.md` stands.

**The arithmetic, on the 18:48 run.** `map = R(corr_yaw)·odom + corr_t`, with `corr = (−0.1142, +0.0011, −2.66°)` and `odom = (0.1041, 0.0161)`, gives `(−0.0095, +0.0124)`. The dashboard displayed **`−0.009, 0.012`**. Nothing on screen was wrong — the screen only ever held the estimate.

**99% of the net correction was in a single axis** (dX −0.1142, dY +0.0011), with every one of the nine events showing 1.7–4.7 mm of odometry motion while the map moved 6–71 mm. The obvious explanation was tested and **rejected**: `corr_x` against `−odom_y·sin(corr_yaw)` correlates **−0.352** — wrong sign, an order of magnitude too small — so it is not a yaw error seen at a lever arm. But `corr_x` against `corr_yaw` correlates **+0.889**: position and heading walk off together at a fixed ratio, roughly 4.3 cm per degree.

**A metric that should not have been trusted, and was.** The net correction is an accident of where a route happens to end. On the hand-driven run the net was 0.064 m while the **peak was 20.3 cm** and **57% of the run sat past 5 cm**. Reporting "net 0.064 vs baseline 0.114, better" was wrong and is corrected here: peak and time-over-threshold are the honest measures. Across all three runs of the day the over-5 cm fraction is **56% / 59% / 57%** — invariant across two controllers, three routes and both `use_scan_barycenter` settings.

### The dashboard was lying in six places, two of them about safety

An audit of `phone_dashboard.py`, not another drive, and it found more than the reported symptom.

**Every dragged goal heading has been 90° wrong.** The drag handler wrote a bare `Math.atan2(dy, dx)` — an angle measured from **+X** — into `goalDrag.yaw`, the same field `pointerdown` initialises from `robotPose.yaw`, which is measured from **+Y**. Two conventions, one variable: tap without dragging and the heading was right; drag more than 5 cm and it went out orthogonal. And `drawGoalMarker` drew its arrow from +X while `drawRobot` drew the nose from +Y — same canvas, same frame, 90° apart — so **the picture agreed with the wrong number and it looked correct**. The comment on the send line still claimed `goal_pose_adapter` applied a compensating −90°, which stopped being true at §17.38 and is why nobody looked at that line. The whole awkward shape of `run_20260901_132022` — a lateral strafe followed by a de-rotating climb — traces to this one expression.

Fixed structurally rather than numerically: `vecToYaw`/`yawToVec` are exact inverses, and the drag handler and *both* renderers now route through them, so they cannot drift apart again. `goal_pose_adapter` stays at `yaw_offset_deg: 0.0` — a display-side offset is what hid the last frame fault for two weeks.

**The E-STOP did not survive a reconnect.** `ws.onopen` sent `arm/ENABLE` unconditionally, so a Wi-Fi blip re-armed an E-STOPped robot with nobody touching anything, while the button still read `CLEAR / TAP TO RESUME`. Now the latch re-asserts the stop instead, on the reasoning that a drive stack which restarted during the outage has lost its own latch.

**`send()` failed silently.** `if (wsOk) ws.send(...)` with no return value: a GOAL or an E-STOP tapped with the socket down vanished and the UI reported success. It now reports delivery, checks `readyState`, and says `NOT CONNECTED`; the 20 Hz drive loop passes a quiet flag so a dead socket cannot spam the hint line.

Also: click-to-goal landed right of the pointer whenever the cached `cssW` went stale (live `getBoundingClientRect()` on the pointer path, cached `cssW` in `s2w()`, marker landing at `sx·(r.width/cssW)`); the POSE pill stayed green on a dead socket; and `resource/dashboard.html`, a decoy the docs have called dead since §17.34, is deleted.

**Why the existing test never caught any of it.** `dashboard_goal_roundtrip.py` has passed since 28 Aug — *"exact to 1e-6 at device pixel ratios 1, 2 and 3"*. It measured **position** and never touched **heading**. The test was right and its coverage was the bug. Extended to 19 checks across a second phase, and **every new guard was verified by reverting its fix and watching it fail** — with the old `send()` restored, the hint reads `GOAL SENT → 2.00, 0.00` while nothing reaches the wire.

**The fix that actually mattered was not a bug fix.** The pose card now shows `ODOM` and a `DRIFT` figure, red past 5 cm, built from transforms the pose logger was already looking up on the same tick. On the 19:38 run it read **0.203 m in red, live, mid-drive**, where the old card would have shown a clean return to the mark. That is §17.38's lesson made structural: *the dashboard that showed the raw truth rather than a patched version is what found the bug.*

### A frame-by-frame verification, because the screen was under suspicion

The 18:48 recording was read against its own pose log. Seven pose-card samples matched the CSV to **under 0.5 mm**. Measured in pixels rather than by eye: gridlines at **76.00 px per 0.5 m over eleven consecutive intervals with zero variance**; the footprint drawn **1.125 m long against the URDF's 1.120**; the trail top at **2.023 m against the log's 2.016**. Every one inside the width of the stroke used to draw it. **The rendering is dimensionally exact, and the 9 cm is simply not in the recording** — it is the gap between the estimate and the room, and the screen contains only the estimate.

### Two parameter changes, one of them confirmed on hardware the same evening

`progress_checker.required_movement_radius` **0.30 → 0.10**. A 0.30 m bar over 10 s is a floor of **0.030 m/s**, against a measured autonomous cruise of **0.027–0.037 m/s** — the bar sat *inside* the speed distribution, so goals aborted while the robot was driving perfectly well. Audited both ways before changing it: the 31 Aug false positive had moved 0.288 m (short by 12 mm) and dies at 0.10; G3's three genuine stalls moved 0.075 / 0.053 / 0.048 m and all still fire. `movement_time_allowance` deliberately stays at 10 s — it is the timer that will detect a `collision_monitor` halt. **Result on hardware at 19:58: two goals, zero aborts**, where every prior Nav2 run aborted once per goal. ✅ **MEASURED.**

`amcl initial_pose` yaw **−1.5708 → 0.0**. The −90° was reasoned in §17.18 as *"base_link +X is the robot's RIGHT, so a robot facing along map +X has yaw −90"* — correct while the map frame still used REP-103 axes. §17.38 rotated it; `Axis_Convention.md` now states a freshly-zeroed robot on the mark reads `[0,0,0] @ 0°`. Left as it was, AMCL would seed its particle filter 90° off the truth on the very first frame. **The fifth stale §17.38 compensation**, and it survived because AMCL has never once been run.

### Stage F: registered, run wrong, and left open on purpose

`use_scan_barycenter: true → false`, with `docs/StageF_Ablation.md` written **before** the drive. The reasoning: §17.44 found cumulative correction invariant to 2% across three parameter sets, and every one of those changes how the matcher **searches**; this changes **what it registers**, seeding from the centroid of a cloud §17.45 measured at 48.8% valid and 86% flickering while parked.

It is **unscored**, and deliberately so. The one run on it was hand-driven rather than Nav2-driven, so the registered protocol was not followed; by the letter of the thresholds the net of 0.064 m falls in the gap between CONFIRMED (<0.06) and REFUTED (0.091–0.137) — **AMBIGUOUS**. The over-5 cm fraction and the peak both point at refutation, but both are metrics chosen *after* seeing the data, and scoring on a post-hoc metric is exactly what pre-registration exists to prevent. `ros2 param get /slam_toolbox use_scan_barycenter` returned **False** on the live node afterwards, and the file predates the run's MAP session, so Stage F **was** active — the run is valid, the protocol was not.

⛔ **The took-effect check registered with it is RETRACTED.** It claimed baseline corrections arrive every **0.175 ± 0.006 m** and should widen toward 0.200 m. That 0.175 came from differencing `hypot(odom_x, odom_y)` — displacement *from the origin* — on an out-and-back route, where the quantity shrinks on the return leg. Measured along the path instead: baseline **0.441 m (sd 0.192)**, Stage F run **0.391 m (sd 0.147)**, indistinguishable at every threshold from 0.5 mm to 5 mm. Withdrawn rather than quietly restated. Caught before the ablation was scored, so nothing downstream rests on it.

### Three self-inflicted failures, recorded because the process is the asset

**A build that reported success destroyed two nodes.** The deploy step said `colcon build --packages-select mecanum_robot mecanum_navigation --symlink-install`. `mecanum_navigation` had only ever been built *without* symlink-install; colcon does not reconcile the two, so the switch left the package's installed dist metadata unusable — while the build printed `Summary: 2 packages finished`. Both its Python nodes then died at launch with `PackageNotFoundError`: `goal_pose_adapter`, so `/goal_pose_click` was never republished to `/goal_pose` and `bt_navigator` never saw a goal; and `cmd_vel_axis_adapter`, so `collision_monitor`'s `/cmd_vel_baselink` never became `/cmd_vel_nav_out`. **That is the whole of "goals weren't working even though Nav2 was active"**, and it is why the 19:38 run had to be hand-driven. Fixed by `rm -rf build/ install/` and a clean rebuild.

The verification step that should have caught it checked the params file and the served dashboard — both correct — and **never launched Nav2**. `Important_Commands.md` §3.2 now requires a clean when switching build modes, and requires step 5 to *launch* what it deployed rather than inspect it.

**A wrong expectation, stated confidently.** The operator was told the DRIFT card would read ≈0.000 m on a parked robot with no MAP session. With no `slam_toolbox` there is no `map` frame at all, so the card correctly reads `NO POSE`. Corrected in the moment, but it is the same class of error as the 0.175 m above: a claim asserted from reasoning without checking the one condition that made it false.

**`main` was 27 commits stale, and it cost something real.** An external stack audit was written against `main` on 1 Sep and was four sessions out of date as a result — it never saw the invariance result, the scan-stability measurement, or the intermittency finding, and recommended as "the most important missing measurement" an experiment (parked LiDAR stability) that §17.45 had already run and which had already returned that document's own Case B. Merged via PR #9; `main` is current at `5cace67`.

### The structural finding: AMCL could not have worked

Found from a node list taken for an unrelated reason. `mapping_full.launch.py` bundled four things — the ydlidar driver, `scan_relay`, `zero_point_tf` and `slam_toolbox` — started and stopped as one unit by the dashboard's MAP button. And `navigation.launch.py`, the AMCL path, starts **no scan source at all** (`grep -c 'ydlidar|scan_relay'` → 0) while its own header forbids running alongside `mapping_full`.

**So the only thing that could bring up the LiDAR was the one thing AMCL forbids.** AMCL would have launched, activated, and sat there with no `/scan` forever — reading as an AMCL fault when it was a launch-topology fault. This is precisely what `Where_We_Stand.md` §8 item 5 asked to be discovered *"on a Tuesday, not on demo day"*, and it was found with no drive, no map and no hardware.

Split into `sensors.launch.py` (lidar + relay + zero_point), included by `mapping_full.launch.py` and by `navigation.launch.py` behind `with_sensors` (default true). MAP's behaviour is unchanged and checked rather than assumed: all three node declarations byte-identical modulo `zero_point`'s new condition, `ZERO_POINT_YAW` carried across, all three launch arguments still resolving. Second benefit: `scan_quality.py` can now characterise the LiDAR without starting a mapping session, which is how every scan capture to date has had to be taken.

### Where this leaves the project

`Where_We_Stand.md` gained a companion, `Stack_Assessment_2026-09-01.md`, rating every layer against measured numbers. The uncomfortable structure it names: **everything below the LiDAR rates 9–10, everything from the LiDAR up rates 1–3**, and the cliff is at one component. It also reads two existing findings against each other for the first time — §17.44's invariance (cumulative correction 2.80 / 2.85 / 2.86 m across three *search*-parameter sets) and §17.45's scan instability (86% of rays flickering while parked). Together they say the matcher is handed a **different point cloud every scan**, and no search parameter can fix a moving objective function. That is consistent with everything measured since, including today's 56/59/57%.

The YDLIDAR X4 Pro is a **triangulation** scanner rated at **<2% of range**: 32 mm at the 1.6 m median, 200 mm at 10 m. §17.45's measured p90 of 22.8 mm is *within spec*. **The sensor is performing to specification and the specification is not good enough for what is being asked of it** — a conclusion that points at hardware, and the honest reason to close the remaining software levers is to justify that rather than guess at it.

**Not attempted today:** G4, the obstacle-avoidance test that is this branch's actual purpose, and AMCL's first bringup. All three are now unblocked in a way they were not this morning.

## 17.50 3 Sep 2026: the first input-side change in the project's history, and the scan made visible

**Every SLAM change to date has been downstream of the scan.** Five sessions of search tuning, three parameter sets, and §17.44's verdict: cumulative `map→odom` correction of 2.80 / 2.85 / 2.86 m, invariant to within 2%. Then §17.45 measured the input for the first time and found 74.8–78% of rays flipping valid/invalid between consecutive scans **with the robot stationary**, 47.4% valid. Read together those two facts say the matcher is not searching badly; it is handed a different point cloud every sweep. This session is the first time anything upstream of the matcher has been touched.

**Six values, and the reasoning for the two that matter.** `frequency` 10.0 → 6.0 buys **+67% angular density** (5000/f: 500 → 833 points per revolution) at the cost of 8 mm more motion skew per sweep, against corrections of 150–370 mm. `max_laser_range` 10.0 → 5.0 removes the rays whose individual error is the same order as the fault being chased: this is a **triangulation** scanner, so error grows with the square of range (~32 mm at 1.6 m, ~100 mm at 5 m, ~200 mm at 10 m), and the measured **median scan range in this lab is 1.6 m** — the cut discards a small tail here and would discard most of the cloud in an open aisle. `range_max` 12.0 → 10.0 closes an Appendix B item open since §17.6. Nav2 gets `xy_goal_tolerance` 0.02 → 0.05 and `batch_size` 500 → 300, the latter being the response `nav2_params.yaml`'s own comment named if the control loop missed its rate, which it has, at 7.5–13.7 Hz against 20.

**The headline is `use_scan_matching: false`, and it is not a retreat.** Over the same 21.85 m drive, wheel odometry alone closed 0.229 m (1.27%, dead on its own spec) while odometry plus the SLAM front end closed 0.706 m. The expensive estimator is three times worse than the cheap one. Turning the sequential matcher off means the pose comes from the wheels and the scan is stamped down there — selecting the better of two measured estimators, not abandoning SLAM. Projected on a ~10 m perimeter, odometry alone gives ~0.13 m, **inside G4's 0.15 m return gate**, which five sessions of matcher tuning never reached. Loop closure runs on a separate matcher and should survive; that is filed as HYPOTHESIS, and `verify_live_config.sh` reads the installed source rather than recalling it.

**Two parameters at once, against the one-at-a-time rule, with the argument written down.** With matching off, none of the matcher's search parameters are active, so there is no search for the range cut to confound. `max_laser_range` changes *what* is drawn into the grid; `use_scan_matching` changes *where*. Separable in analysis, so one drive yields two independent results. The penalties, the search windows, the loop-closure thresholds and the map resolution are all deliberately frozen, each with a stated reason — including `angle_variance_penalty`, which rests on a premise now known false but whose lever Stage E measured going the wrong way (1.2 → 0.6 took max correction 0.229 → 0.366 m). A lever measured as unreliable is not one to pull while other things move.

**`range_max` and `max_laser_range` are deliberately NOT the same number, and the distinction is worth recording.** The first is what the sensor can do; the second is what one consumer chooses to trust. Capping the driver at 5 m would push that decision onto the costmaps, `collision_monitor` and `scan_quality.py` simultaneously, and would destroy the evidence needed to prove the cut helped. Keeping the driver honest at 10 m means the SLAM cap returns to 10.0 in one line for a clean A/B on the same route. Cap policy at the consumer; never edit the spec sheet to record a decision.

**The scan is now visible while driving, with its own statistics.** The dashboard gained a live LiDAR layer: `/scan_reliable` decimated to ~240 beams, broadcast at 5 Hz over the WebSocket path that already carries pose and map, drawn as red dots welded to the live footprint rather than to a pose cached with the scan. Returns beyond `max_laser_range` draw faint grey instead of being hidden, so the cost of the 5 m cut is on screen rather than taken on trust. The masked rear wedge travels as JSON `null`, never 0.0 — a finite value there would paint a phantom obstacle ring at the robot's own origin. The HUD carries **VALID** and **CHURN**. ⚠ **Corrected same day, see §17.52:** this was first written as "the two numbers §17.45 could only recover offline", which is wrong. `scan_quality.py`'s `flicker_pct` is a *windowed cumulative* metric over rays-ever-valid; the HUD's churn is a *per-sweep* rate over live beams. Different denominators, different windows, not comparable. A stale scan stops drawing after 1.5 s, because §17.25 had `/scan` and `slam_toolbox` freeze together while Nav2 kept driving and the last good sweep sat on screen looking authoritative.

**`tools/tests/dashboard_scan_geometry.py`, 25 checks, and it found a bug in itself on the first run.** The overlay is exactly the hazard §17.49 described: `base_link` is not REP-103 here (+X right, +Y nose), the corrected scan frame measures bearing 0 along +X, and the laser sits 0.27 m forward — get any one of those wrong and the dots still form a plausible room outline, just rotated, and nobody can tell by eye. So the test does not check that dots appear; it checks that `drawScan()` agrees with `yawToVec()`/`drawRobot()`, the renderers already validated against hardware, for beams whose answer is known by construction. It agreed to 2.2e-16 at five headings. The one failure on the first run was the test's own URDF regex latching onto a comment 260 lines above the actual `<joint>` element and reporting a convincing 0.27 m disagreement that did not exist — recorded because a test that fails loudly on its own bug is working correctly.

**`tools/verify_live_config.sh`, which is §17.32 turned into a script.** It asks the live nodes for all six values, measures the actual scan rate and beam count, and exits non-zero rather than clearing a drive on a mismatch. Two things it settles that no file can: whether the hardware honoured `frequency: 6.0` at all (`support_motor_dtr` is false, so the driver may not command the motor and the request can be silently ignored — if it reports ~10 Hz, every prediction resting on 833 points is void); and which of this repo's two contradictory beam-count figures is right, since `Stack_Assessment` §3A computes 5000/f = 833 while `README.md` states ~1258 pts/scan at ~11.5 Hz, implying ~14.5 kHz rather than 5. Both cannot be true.

**A recommendation overruled, recorded so it is settled by measurement rather than re-argued.** 7.0 Hz was recommended over 6.0: it is the X4 Pro's datasheet nominal, and 6 Hz sits nearer the bottom of the motor's range where speed ripple becomes angular error distributed differently every revolution — the same class of fault this change exists to reduce. That is reasoning, not a measurement on this unit, and the operator chose the extra 17% density. The deviation reading in `verify_live_config.sh` decides it, and the fallback to 7.0 is one line.

**Predictions registered before the drive** in `docs/StageG_Deploy.md` §3, including the one expected to go the wrong way: unknown% should **rise** from 82.9% against a G4 gate of 50%, because a shorter ray paints less free space. Three G4 criteria should improve and one should degrade. And the falsifier is stated plainly: **if the map still folds with scan matching off, the front end was never the cause**, and five sessions of suspicion pointed the wrong way. That would be the largest finding this project has produced, and it is written down in advance so it cannot be quietly reinterpreted afterwards.


## 17.51 3 Sep 2026 (afternoon): Stage G deployed, and the density half of it was dead on arrival

**The deploy itself was clean.** All six files hashed correct on arrival, both `colcon` packages built in 4.5 s, and `verify_live_config.sh` ran for the first time ever. Then it failed five checks, and three of those failures were the script's own bug.

**The script bug, first, because it is the more embarrassing one.** `ros2 param get` prints Python-style booleans — `True`, `False`, capitalised. The verifier compared them against lowercase literals (`"false"`, `"true"`) with a plain bash `=`, so `use_scan_matching`, `use_scan_barycenter` and `do_loop_closing` were all reported FAIL while being **correctly deployed**. A verification tool that fails correct configuration is worse than no tool, because the next instinct is to "fix" a config that was never broken. Fixed by lower-casing both sides before comparison, and the incident is recorded in the script's own comment so the fix is not silently re-applied by someone who does not know why it is there. The remaining lesson is the general one: **a tool written to check a claim needs its own claim checked**, and this one was written and shipped without ever being run against a live node.

**The real finding, and it kills a third of this stage: `frequency:` does nothing on this unit.** Measured `/scan` rate **11.35 Hz against 6.0 requested**. `support_motor_dtr: false` means the driver never commands the LiDAR's motor at all, so the head free-runs at its own native speed and the parameter is not wired to anything. Deviation was **~8 ms on an ~88 ms period, under 10%** — so the rate is *stable*, just not *commanded*. Neither the operator's 6.0 nor the 7.0 recommended alongside it could ever have taken effect. **The +67% density gain was never available.** The `support_motor_dtr` risk was written down as a HYPOTHESIS in the config comment *before* the deploy, which is the right instinct applied at the wrong time: it should have been settled by a ten-second `ros2 topic hz /scan` **before** a specific rate was argued over at length, not registered as a caveat underneath the argument.

**The same measurement settled a contradiction that had been sitting in the repo unresolved.** `Stack_Assessment` §3A computes points/rev as `5000/f`; `README.md` claimed ~1258 pts/scan at ~11.5 Hz, which implies a ~14.5 kHz sample rate against a configured 5 kHz. Both could not be true. Measured: **430 beams at 11.35 Hz**, against `5000/11.35 = 441` — **2.5% error**. The formula is confirmed at the rate that is really running; `sample_rate: 5` means 5 kHz and always did; the README figure was stale and is corrected. Worth noting the shape of this: the beam-count check was written expecting 833 and *failed* — and the failure is what produced the answer, because the number it measured fitted the model at the real rate rather than the requested one. The check has since been rewritten to compare against the **measured** rate rather than the requested one, so it tests the formula rather than the deployment.

**The verifier now separates hardware ceilings from deployment errors.** A stable-but-uncommanded scan rate is not something a re-deploy can fix, so blocking the drive on it would be wrong; it is now a **WARN** that reports the real rate, names what it invalidates, and explicitly says not to re-deploy chasing it. Only genuine config mismatches still exit non-zero. `support_motor_dtr: true` is the one route to a commanded rate and is deliberately **not** taken here — this unit's motor start/stop behaviour is unknown and it belongs in its own single-variable test, not bolted onto a stage that is already changing two things.

**What survives, and it is most of it.** The density lever is dead. The other four values are unaffected and all verified deployed on the live nodes: `max_laser_range: 5.0`, `use_scan_matching: false`, `xy_goal_tolerance: 0.05`, `batch_size: 300`. **None of them depend on beam density**, so the drive is worth doing exactly as planned and the headline test — whether the map stops folding once the sequential matcher is out of the loop — is untouched by any of this. `Mapper.h` was also read directly on the Pi and confirms `m_pLoopScanMatcher` and `m_pSequentialScanMatcher` are separate objects, which upgrades "loop closure should survive matching off" from HYPOTHESIS toward MEASURED, pending the drive actually showing a closure fire.


## 17.52 3 Sep 2026: the live scan HUD shipped with the wrong name on it, and 76% vs 17% was never a comparison

**Stage G verified clean on the second attempt: 15 passed, 0 failed, 1 warned.** Nav2 happened to be running this time, so `batch_size: 300` and both goal tolerances were confirmed against live nodes too. The one warning is the known scan-rate ceiling (measured 11.451 Hz across three runs now — 11.348, 11.419, 11.451, spread 0.9%, deviation *improving* each time). The verifier's boolean-case bug is fixed and the three correctly-deployed values it had been failing now read PASS.

**Then the dashboard showed VALID 50% and FLICKER 17%, against §17.45's 74.8-78%, and the obvious reading was a 4.5x improvement. It is not, and the error was mine.** `tools/scan_quality.py` computes `flicker_pct = (ever_valid − always_valid) / ever_valid` over a **whole capture window**: of the rays that returned anything at all during the capture, what fraction were not *perfectly* consistent across every scan in it. A ray that drops out once in two hundred sweeps counts fully as flickering. The dashboard computed something entirely different — beams whose valid/invalid state changed since the **immediately previous sweep**, divided by **all** beams. A windowed cumulative metric is mechanically far larger than a per-pair instantaneous one, and the two share a denominator only by coincidence. **76% and 17% are not the same quantity, so the difference between them is not an improvement in anything.**

**Two things were wrong at once, which is why it was convincing.** The metric definition was wrong, and the denominator included the ~107-beam rear wedge that `scan_relay.py` masks to NaN by design (§17.15) — beams that are structurally blind and can never be valid, so counting them deflates every percentage that includes them. `VALID 215 of 430 = 50%` is arithmetically true and operationally misleading; against the 323 beams that *could* return it is **66.6%**, which is a materially different picture of the same sensor.

**Fixed by separating three states rather than two.** MASKED (NaN, structurally blind, `scan_relay`'s doing), NO-RETURN (a real beam that got nothing back — range, reflectivity, incidence angle; this is sensor performance) and VALID. Churn now counts only non-masked beams, VALID reports against live beams, and the masked count is displayed rather than silently folded into a denominator. Measured churn over live beams is **~23%/sweep**, not 17%.

**Renamed FLICKER → CHURN on the HUD, deliberately and permanently.** Keeping the word would have guaranteed the same misreading by someone else later, including by this project's own author six weeks from now. `scan_quality.py` owns "flicker" and means a specific windowed thing by it; the live number is a per-sweep churn rate and now says so, with a HUD line stating outright that the two are different metrics. `dashboard_scan_geometry.py` gained assertions that the publisher emits no field named `flicker` and that churn excludes masked beams — so the conflation cannot silently return.

**§17.50 is corrected in place and the Stage G prediction is withdrawn, not quietly adjusted.** That entry claimed the HUD showed "the two numbers §17.45 could only recover offline from a recording", which is false for flicker. `StageG_Deploy.md` §3.1 predicted "CHURN, parked: 60-80%" by quoting §17.45's windowed figure against a per-sweep metric — **the prediction was never testable as written**, so it is marked WITHDRAWN rather than scored. A prediction that cannot fail is worth nothing, and one that compares two different quantities is worse than none because it manufactures a result.

**What is still genuinely unknown, and the cheap test that settles it.** Whether the scan input actually improved is *not answered by this session*. The honest way to find out costs sixty seconds: run `scan_quality.py` on the parked robot now and compare its `flicker_pct` against §17.45's 74.8-78% — same tool, same metric, same question, different day. Until that is run, **no claim about scan stability having improved is supported**, and the Stage G drive should be read as testing `use_scan_matching: false` and `max_laser_range: 5.0` only.

**The pattern worth naming, because it is the third instance.** §17.38 was a wrong frame that survived two weeks because nobody wrote down which category a claim was in. §17.44 was three sessions spent tuning parameters that were never deployed. This is the same shape a third time: an instrument was built, its output was compared against a historical number, and nobody checked that the two numbers measured the same thing before drawing a conclusion from the difference. **The instrument was right; the comparison was invented.** The check that catches this class costs one grep of the tool being compared against, and it was not done until the result looked too good.


## 17.53 3 Sep 2026: the first scan measurement since Stage G, and three of its four numbers are not comparable to anything

**347 scans, 30 s, robot parked, `/scan_reliable`, saved to `data/scan_captures/stageG_20260903_154323.json`.** Verdict `UNSTABLE`. Four headline numbers came back and only one of them can be read against §17.45 without further work.

**COMPARABLE, AND UNCHANGED: valid 47.0% against §17.45's 47.4%.** This is a per-scan median, not a windowed statistic, so the comparison is exact. **The fraction of usable rays did not move.** Whatever Stage G did, it did not change how much of each sweep returns.

**NOT COMPARABLE: flicker 84.8% against §17.45's 74.8-78%.** This looks like a regression and is not evidence of one. `flicker_pct = (ever_valid − always_valid) / ever_valid`, and `always_valid` requires a ray to be valid in *every* scan of the window — a set that can only shrink as the window grows. The metric therefore rises monotonically with capture length, and §17.45 **does not record the length it used**. `tools/scan_window_sweep.py` was written to settle this class of question permanently: it replays a saved capture at every window length. Its selftest makes the point better than argument can — on one synthetic capture with a single ray dropping out once in a hundred scans, flicker reads **1.0% at a 2-scan window and 50.0% at 100**, from identical data. Two captures of different lengths are not comparable, full stop.

**NOT COMPARABLE, AND CONFOUNDED IN A SECOND WAY: per-ray noise median 5.8 mm, p90 11.9 mm, max 32.6 mm, against §17.45's p90 22.8 mm and max 79.9 mm.** This looks like a halving and may well be one, but the statistic is computed only over rays valid in *every* scan — **42 of 277** here. A longer window selects a smaller, more stable subset, biasing the noise figure *down*. The apparent improvement and the window length are confounded and cannot be separated from this capture alone.

**THE STAGE G DECISION THIS VALIDATES OUTRIGHT: 94.7% of returns fall within 5 m** (81.8% within 3 m, p50 1.6 m, p90 4.2 m). `max_laser_range: 10.0 → 5.0` therefore discards about **5% of returns** in this room. The prediction from the 1.6 m median was that the cut would be nearly free here and expensive in an open aisle; the first direct measurement puts a number on the first half of that.

**AND THE ONE IT KILLS: `range_max: 12.0 → 10.0` removed nothing.** `discarded 0.0% beyond max_laser_range 10.0 m` — there is nothing out there to discard. That change was defended as a correctness fix rather than a tuning choice, which it is and remains, but it was also floated as the prime suspect for any flicker improvement. **It cannot have caused one.** Recorded because a hypothesis that had not yet been tested is easier to retract than one that has been repeated.

**GENUINELY NEW, AND THE MOST USEFUL NUMBER OF THE DAY: geometric conditioning 0.659, weak axis ~95° in the sensor frame, range 0.469–0.879 across the run.** Conditioning is `λ_min / λ_max` of `Σ n·nᵀ` over surface normals: 1 means the scan pins the pose in both axes, 0 means it slides freely along one. Bearing 95° in this robot's sensor convention (0° = +X = right, +90° = +Y = nose) is **essentially the nose axis**, so at the zero mark the geometry constrains sideways motion well and **forward/backward poorly**. That is textbook corridor degeneracy, measured rather than inferred, on the exact spot every commissioning drive starts from. It is also a mechanism the scan-matching work has been circling since §17.13 without ever putting a number on it.

**`largest gap 95.7°`** confirms the rear mast wedge is masked as designed (§17.15) and is slightly wider than the nominal 90°.

**One instrument defect found and fixed conservatively.** `scan_quality.py` hardcoded `SLAM_MAX_RANGE = 10.0`, now stale against Stage G's deployed 5.0, so its "discarded" figure describes a configuration that is no longer running. Fixed by adding `--slam-max-range` rather than editing the constant: the **default output stays byte-comparable with §17.45 and every run before it**, per §17.46's rule that changing an instrument mid-campaign destroys the baseline it is measured against. The deployed reality is one flag away.

**CLOSED, same session, by `scan_window_sweep.py`.** `scan_quality.py`'s default is `--seconds 10.0`, which at the measured 11.45 Hz is **114.5 scans**. The sweep gives 76.6% at 100 scans and 79.5% at 150, so the 10 s equivalent interpolates to **77.4%** — against §17.45's two captures at the same mark, **74.8% and 78.0%**. Today sits *inside* that spread, 0.6 pp from the upper one, while §17.45's own two captures differ by 3.2 pp. **The scan input is unchanged. Not better, not worse, identical within the instrument's demonstrated reproducibility.** Stage G's input-side levers did nothing to scan stability, which is unsurprising given the one that could have (`frequency`) turned out inert and the other (`range_max` 12→10) removed nothing. This is not a disappointment: it *strengthens* the case for the drive, because it confirms the matcher is still being handed the same moving target no search parameter has ever been able to compensate for.

**The dashboard CHURN metric cross-validates against the offline tool.** Flicker at a 2-scan window is 22.3% mean (9.2–35.3% spread) over `ever`=277; converted to churn's `live`=323 denominator that is 19.1% mean, 7.9–30.3% spread. The HUD reads 17%/sweep. Two independently written instruments, different denominators, agreeing — which is the check that says the live number means what it claims.

**Two numbers moved more than the instrument's own noise, and are recorded as open.** `conditioning` 0.659 against 0.739/0.721, and `weak axis` 95.0° against 99.8°/100.0°. §17.45 established the tool reproduces to 0.018 in conditioning and 0.2° in bearing on a genuinely unchanged position, so gaps of 0.062 and 4.8° are **3.4× and 24×** that. Something about the scene or the placement is different — furniture moved, a door open, or the robot not physically on the mark despite a zeroed odometry readout. **Not chased today, not ignored either.** It matters because conditioning is the number that says whether the geometry can pin a pose at all, and a drifting weak-axis bearing would change which leg of a drive is degenerate.

**What this session still did not establish.** Whether per-ray noise improved. p90 11.9 mm against §17.45's 22.8–24.5 mm is computed over rays valid in *every* scan — 42 of 277 at 347 scans — and a longer window keeps only the most stable rays, biasing it down. `scan_window_sweep.py` now reports noise per window alongside flicker, so this closes from the capture already saved rather than needing another drive. From here on, record `--seconds` with every `scan_quality.py` figure and no future comparison has this problem at all. **Stage G's drive still tests exactly what it was built to test — `use_scan_matching: false` and `max_laser_range: 5.0` — and none of that rests on the scan having got better.**


## 17.54 3 Sep 2026 (16:24): the corrections stopped, exactly and completely — `run_20260903_162401`

**`map→odom` did not move once. Not by 1 mm, across 2225 pose samples and 222 seconds of driving.**

```
corr_x    min / max :  +0.000000 / +0.000000
corr_y    min / max :  +0.000000 / +0.000000
corr_yaw  min / max :  +0.0000   / +0.0000
correction events   :  0
```

The registered prediction was "corrections ≈ 0, the 0.175 m metronome stops". The measured answer is zero to six decimal places. Against the baseline this replaces — §17.49's Nav2 run: **9 corrections at 0.175 m ± 6 mm spacing, magnitudes 26–163 mm**; §17.42's commissioning drive: **48 correction events**, cumulative 2.80–2.86 m invariant across three parameter sets — this is not an improvement in degree. `use_scan_matching: false` removes the mechanism, and the mechanism was the entire observed fault.

**What was actually driven, reconstructed from the pose CSV rather than from the operator's description.** Total rotation **−723.8° = 2.01 full turns**. Fitted circle centre **(+0.496, −0.004)**, radius **0.502 m with a 6 mm standard deviation** across both laps. Path length 6.42 m against 6.28 m predicted for two circles of r = 0.5 m. The odometry traced two half-metre circles and held the radius to six millimetres — the estimator is not the weak link anywhere in this stack.

**Heading closure −3.85° after 723.8° of rotation = 0.53%.** For context, §17.42 measured 10.53° of drift over 18 m of mixed driving. Rotation is tracked well.

**The estimate is optimistic against the floor, and by exactly the amount encoders cannot see.** Estimate closure **1.84 cm**; the operator's tape measure read approximately **−4, −3 cm and nose −3°** (units to be confirmed). Heading agrees closely (−3.85° estimate against −3° measured). Position does not: ~5 cm on the floor against 1.84 cm believed, a **~3 cm gap over 6.42 m = 0.47%**. That is mecanum roller slip, structurally invisible to wheel encoders, and it is the specific error an optical-flow ground sensor would catch. Well inside the 1.27% odometry spec; recorded because the *direction* matters — the robot always believes it did better than it did.

**What this run does NOT establish, stated plainly so the result is not over-read.** It was **two tight circles at the mark, not a perimeter drive**. G4 is untouched: the map grades 75.4% unknown over a 10.15 × 9.95 m extent observed from essentially one position, which is a coverage figure, not a quality one, and is not comparable to the 82.9% from a full drive. §17.44 also established the tight circle as a *degenerate* geometry for scan matching, so this is close to the easiest case for the front end to have been switched out of. **The decisive claim is narrow and safe: the correction mechanism is gone. Whether the resulting map is geometrically true over a real route is the next run's question.**

**A useful incidental confirmation:** the map extent of 10.15 × 9.95 m is almost exactly 2 × the deployed `max_laser_range: 5.0`, seen from one spot. The range cut is live and behaving.

**Loop closure remains untested, and the reason is procedural.** `graph_residuals.py --watch` reported no message on `/slam_toolbox/graph_visualization` in 15 s — because it was started while the robot was parked and before any pose-graph nodes existed. The topic publishes only once the graph has content. **Start it after pressing MAP, not before.** The "does closure survive `use_scan_matching: false`" question is still HYPOTHESIS, supported only by the source read confirming `m_pLoopScanMatcher` and `m_pSequentialScanMatcher` are separate objects.

**Two instrument notes, neither a hardware fault.** `run_report.py` flagged *"Diagonal mismatch is visible"* (FR-RL 1.091 against FL-RR 0.956). It is the circle geometry: FL and RL carried the drive (|target| 0.730 and 0.781 rad/s) while FR and RR sat at the pivot (0.044 and 0.014), because the instantaneous centre of rotation landed on the right-side wheels at r = 0.502 m against `K_OUTER` = 0.5607 m. **This is precisely the false positive §17.46 built a turn-context guard for in `run_analyzer.py`, and `run_report.py` never received that guard.** Separately, the report's `RR actualRows 1244` is a count of *non-zero* samples, not missing telemetry — all four motors reported all 4534 rows, verified against the raw CSV. No encoder problem.

**The video could not be analysed and was not guessed at.** The only ffmpeg available in the analysis environment is Playwright's encoder-only build with no MP4 demuxer and no H.264 decoder. The pose CSV answered every question the video would have, more precisely.


## 17.55 3 Sep 2026: the video says the robot did not turn, and the odometry says it turned 3.85 degrees

**Photogrammetry on the run video, against `run_20260903_162401`'s own endpoint.** The recording is the mastcam side-by-side (robot left, dashboard right). Sampled at the frame where the HUD reads `X −0.016 · Y 0.008 · NOSE −3.8° · DRIFT 0.000 · JUMPS 0`, and compared against the frame at `NOSE −0.3°` seconds after the run began.

| measurement | rotation | translation |
|---|---|---|
| odometry (HUD, pose CSV) | **−3.85°** | 1.84 cm |
| floor L-brackets (world-static) | **−0.03°** | ~0.3 cm |
| floor grout orientation (world-static) | **+0.00°** | — |

**The method was validated before its result was believed, and the first attempt failed, which is why it is trustworthy now.** The first pass measured the robot's own wheels against the frame and returned "no rotation" — then a validation frame where the HUD read −28.3° also returned ~0°, which is impossible. Looking at that frame explained it: **the camera is mounted on the robot's own mast.** The robot sits still in frame while the floor and the background chairs swing around it. Measuring the robot against a robot-mounted camera measures nothing. Redone with the floor as the reference, the same validation frame gives **grout −27.07° against the HUD's −28.0°, agreeing to within 1°.** The instrument detects real rotation; at the endpoint it detects none.

**Noise floor and discrimination.** Centroid repeatability is ~1 px over a 325 px bracket baseline = **0.18°**. A genuine −3.5° would have swung the brackets roughly **13 px**; the measured motion was **2.4 px**. The result is not near the noise floor.

**What this means, and it is not a small thing.** The −3.85° is **phantom yaw in the estimator, not physical rotation of the robot.** Over 723.8° of commanded rotation that is 0.48% — and it is the same 0.53% figure §17.54 computed from the CSV and attributed to physical drift. **The robot is mechanically more repeatable than its own estimate claims.**

This bears directly on a load-bearing assumption. §17.42 measured 10.53° of heading drift over 18 m and this project has treated that as physical slip. **Physical slip cannot be fixed by better estimation; estimator drift can.** If some fraction of that 10.53° is also phantom, the wheel odometry is a better instrument than its numbers suggest, and a gyro recovers the difference directly rather than merely bounding it. That converts the BNO055 from a general recommendation into one with a measurement behind it.

**Grade 🟡 SINGLE, deliberately.** One run, one endpoint pair, on a tight-circle drive. The rotation figure is the strong half (validated against a known 28°, confirmed by two independent world-static features). The translation figure is weaker: a mast camera at an oblique angle is sensitive to small pitch and roll of the mast, so ~0.3 cm is indicative rather than exact. **Needs replication on a route that is not two circles before anything is built on it.**

**An unresolved discrepancy, recorded rather than smoothed over.** The operator reported roughly **−4, −3 cm and nose −3°** at the end of the run. The −3° matches the dashboard's NOSE reading exactly, which raises the possibility those numbers were read off the dashboard rather than measured against the brackets with a tape. If they were a genuine tape measurement, this section's analysis is wrong somewhere and that needs finding. **The tape-measured ground truth at the mark, which Appendix B.7 has wanted for a week, still has not been captured.**

**Method note for reuse.** `ffmpeg` frame extraction plus a threshold centroid on the floor brackets, and a gradient-orientation histogram on the grout lines, is enough to measure return-to-mark to a few millimetres and a fraction of a degree from an ordinary phone video — no fiducials, no calibration. It is a cheaper and more precise ground truth than a tape measure for rotation, and it works retrospectively on footage already recorded. The one thing it requires is knowing where the camera is mounted.


## 17.56 3 Sep 2026 (17:43): the perimeter drive — zero corrections again, and the phantom yaw replicates

**`run_20260903_174352`. 482 s, 12.04 m, one full turn (−364.5°), out to 3.66 m from the mark and back.** A structurally different route from §17.54's two circles, on the same Stage G config, verified live before the drive (12 pass, 0 fail, 1 warn).

**`map→odom` was zero again. Exactly.**

```
corr_x / corr_y / corr_yaw   min = max = 0.000000   over 4769 samples
correction events            0
```

Two runs now, 698 s and 18.5 m of combined driving, on routes with completely different geometry: **not one correction.** §17.54's result was not an artefact of the tight-circle geometry §17.44 flagged as degenerate. `use_scan_matching: false` removes the mechanism, and the mechanism was the whole observed fault.

**Odometry closure 9.9 cm over 12.04 m = 0.83% of path**, against the 1.27% spec. Heading closure −4.49°.

### The phantom yaw replicates, and the method now has two validations

Photogrammetry on the run video, using tile-grout orientation as a world-static reference (the operator's own zero criterion is *"chassis edge parallel to the tile line"*, so this measures exactly what they align by):

| | odometry | physical | validation |
|---|---|---|---|
| §17.55, two circles, 723.8° rot | −3.85° | −0.03° / −0.01° | HUD −28.0° vs grout −27.07° |
| **§17.56, 12 m out-and-back, 364.5° rot** | **−4.49°** | **+0.00°** | **HUD −19.4° vs grout −18.50°** |

Both runs: the robot physically returned to its starting heading; the estimator did not. **Upgraded from 🟡 SINGLE to ✅ MEASURED** — reproduced on a different route, different rotation profile, different video, with the method independently validated in each.

Phantom yaw rate: **0.60°/m** on run 1, **0.37°/m** on run 2. §17.42 measured 10.53° over 18 m = **0.58°/m** and attributed it to physical slip. Those are the same order. **A large fraction of this project's assumed heading drift may be estimator error rather than physical slip** — which matters because slip cannot be fixed by better estimation and estimator error can. This is now the strongest measured argument for the IMU on the hardware list.

### Two instrument failures, both caught by validation, both recorded

The method failed twice before it worked, and the failures are more instructive than the result.

**First failure (§17.55):** measured the robot's own wheels against the video frame, got "no rotation", then a validation frame at a known −28.3° also returned ~0°. Cause: **the camera is on the robot's own mast.** The robot sits still in frame while the world moves around it. Measuring the robot against a robot-mounted camera measures nothing.

**Second failure (this run):** the grout-orientation window returned 90.2° at start, middle *and* end — suspiciously identical. Cause: **this video has a different panel split from the previous one**, and the measurement window extended into the dashboard's own border, a fixed UI edge that never rotates. It was measuring the screenshot, not the floor. Re-run on a floor-only window (x 85–755, clear of both the cabinet at left and the panel edge at right), the validation passed at 0.90°.

**Both were caught only because a validation frame with a known answer was checked before the result was believed.** Neither would have been visible in the output. A measurement that cannot fail its own check is not a measurement.

### What is NOT established, stated plainly

**Translation was not reliably measured and no number is claimed.** Phase correlation on the floor gave a weak peak (0.034) and the tile-pitch autocorrelation found no usable period, so there is no trustworthy scale. The brackets and wheels sit at different distances from an uncalibrated oblique camera, so their pixel scales differ and cannot be reconciled without calibration. **The video replaces the tape measure for heading and does not replace it for position.** The tape-measured ground truth Appendix B.7 has wanted for a week is still needed, and now specifically for position only.

**G4 is still not scored.** `map_integrity.py` was not run and the `.pgm` was not transferred. From `run_report.py`: 76.7% unknown over a 9.65 × 11.7 m extent, 2.76% occupied. Unknown is *worse* than §17.54's 75.4% and far outside the <50% gate — consistent with the prediction that the 5 m cut would cost coverage, but neither figure is a controlled comparison.

**And the route was not actually a perimeter.** The pose trace spans X −0.42…+0.51 m against Y −0.68…+3.64 m: an out-and-back along a single corridor arm, not a loop around the room. The map's cross shape is what the LiDAR *saw* from that corridor, not where the robot *drove*. A genuine perimeter, closing a loop, is still outstanding and is what G4 needs.

### Loop closure: the graph never published, twice

`graph_residuals.py --watch` reported no message on `/slam_toolbox/graph_visualization` in 15 s — the second time, and this time with mapping unambiguously running and 8 minutes of driving behind it. The earlier explanation (started while parked, before nodes existed) does not cover this run.

`enable_interactive_mode: false` is the obvious suspect but is contradicted by §17.42, which ran `graph_residuals` successfully through 19 closures with that same setting. **The live hypothesis is therefore that `use_scan_matching: false` suppresses pose-graph construction entirely** — in which case slam_toolbox is operating as a pure scan-stamper, loop closure cannot fire because there is no graph, and the `do_loop_closing: true` in the config is inert. That would be a real and important limitation of the current configuration, not a tooling problem. **HYPOTHESIS, unverified.** Settled cheaply by `ros2 topic info /slam_toolbox/graph_visualization` during a live mapping session: a publisher count of zero, or a topic that does not exist, decides it.


Every supporting document, organised by category. Update this as new artefacts are produced.

> *Repository note (v2.0): the project's own authored documents now live as Markdown under `docs/` in the `NarrowAisleBot` GitHub repo, with the original `.docx`/`.pdf` in `docs/originals/`. The catalogue below predates that consolidation and lists documents by their original working titles; several are now the `docs/*.md` files. The repo is the current home of record.*

## A.1 Foundational papers

- An Omnidirectional Asymmetric Mobile Robot for Narrow-Aisle Spaces — defines the asymmetric kinematic basis used by AisleBot.

- Galati et al. — Adaptive Heading Correction — empirical heading-drift characterisation on mecanum platforms; motivates Phase 2 IMU fusion.

- Modeling and Adaptive Control of an Omnidirectional Mobile Robot — adaptive-control reference for future work.

- Fuzzy Adaptive PID Control of Mecanum-Wheeled Mobile Robot — alternative tuning strategy worth comparing to fixed-gain PID once baseline is solid.

- Advanced Omnidirectional Mobility System for Human-Friendly Industrial Warehouse Operations — context for the food-cart deployment.

- Robotized and Automated Warehouse Systems — broader warehouse-robotics literature review.

- Mecanum Roll Geometry / Wheel Roller Design — wheel-mechanics reference for the 45° roller assumption.

## A.2 Datasheets and component documents

- Motor datasheet — Rhino RMCS-2086 (operating voltage, RPM, gear ratio, encoder CPR).

- Motor driver — Cytron MDD20A pinout and PWM/DIR truth table.

- Arduino Mega Grove Shield v1.2 reference.

- RobotizedandAutomatedWarehouseSystems.pdf — for warehouse context.

## A.3 Internal project documents

- Aislebot_Complete_System_Architecture_v2.docx — Jan 2026 system architecture overview (open-loop era).

- Aislebot_v3_OpenLoop_Manual.docx — March 2026 setup and deployment manual for the open-loop v3 system.

- AisleBot_PID_Control_Theory.md / .docx — theory reference covering P, I, D, anti-windup, derivative filtering, and feedforward.

- AisleBot_Autonomy_Roadmap.md — the five-phase autonomy roadmap referenced in Part X.

- AisleBot_Robotics_Masterclass.md — long-form educational reference covering Linux, Python, C++, ROS 2, PID, SLAM, EKF.

- AisleBot_ESP32_Complete_Manual_v2.docx + ESP32 wiring guide — ESP32 firmware and wiring reference.

- AisleBot_Complete_Setup_From_Zero.md — fresh-Pi setup procedure (April 2026).

- AisleBot_Dev_Operations_Guide.md — day-to-day operations playbook.

- AisleBot_UV_Arm_System_v1.docx — UV-arm subsystem reference.

- aislebot_motor_analysis.txt — open-loop motor characterisation report (the PWM-120 data set).

- Important_Commands.md — copy-paste cheat sheet for login, code deploy, data download, and quick health checks (new, added 7 Aug 2026, §16.16).

- SLAM_Theory.md — SLAM algorithm choice and underlying math (scan matching, pose-graph optimization, occupancy grids), grounded in `research_articles/` (new, added 7 Aug 2026, §17.1).

- Navigation_Theory.md — costmap inflation math, layered costmaps, global/local planning, self-occlusion as a navigation problem (new, added 8 Aug 2026, §17.6).

- LiDAR_Orientation_Calibration.md — the LiDAR scan-mirror bug: how it was found, the block-placement measurement method, the reflection-vs-rotation derivation, and the `scan_relay.py` fix (new, added 11 Aug 2026, §17.9).

- robot_photos/ — dated, captioned photographic record of the physical robot, cross-referenced from the journal entries they support (new convention, added 11 Aug 2026, §17.4/§17.8/§17.9).

## A.4 ROS 2 source files (Pi)

- esp32_bridge.py — ESP32 serial-protocol node.

- mecanum_teleop_asymmetric.py — asymmetric inverse-kinematics node.

- odometry_publisher.py — forward-kinematics odometry.

- arm_bridge.py — UV-arm bridge to Mega.

- phone_dashboard.py — FastAPI/uvicorn dashboard.

- lcd_display.py — 16×2 status LCD driver.

- joy_to_aislebot.py — Xbox controller mapper.

- keyboard_teleop.py — keyboard fallback.

- gazebo_bridge.py — Gazebo simulation bridge.

- aislebot_full.launch.py (active) — primary launch file.

- ~~hardware_launch.py (deprecated)~~ — deleted in v2.0, as flagged.

- scan_relay.py (new, v2.0) — QoS bridge, best-effort `/scan` → reliable `/scan_reliable` (src/scan_relay/).

- mapping_full.launch.py (new, 6 Aug 2026) — one-command lidar + relay + slam_toolbox bringup, on demand only (§16.10).

- run_report.py (new, 7 Aug 2026) — automated post-run PID + map analysis, a Python port of `docs/tools/telemetry_analyzer.html`'s metrics/findings logic (§16.14).

- setup.py — console_scripts entries.

## A.5 Firmware (ESP32 / Mega)

- aislebot_esp32.ino — active ESP32 firmware (renamed from aislebot_esp32_v2.ino in v2.0; v2.0 banner, content unchanged).

- aislebot_arm.ino — active Mega firmware, v8 (arm + staged UV-C lighting). Supersedes aislebot_arm_v7.ino.

## A.6 LiDAR / SLAM configs (new, v2.0)

- system/ydlidar_params.yaml — confirmed YDLIDAR X4 Pro driver parameters.

- system/slam_nodom.yaml — the working slam_toolbox config (scan-matching only); deployed at ~/ros2_ws/slam_nodom.yaml.

- ydlidar_ros2_driver — third-party, cloned by install.sh (branch humble), not vendored.

## A.7 Research articles (new, v2.4, 7 Aug 2026)

Living bibliography backing SLAM/AMR decisions from Part XVII onward — full list with DOIs and per-paper relevance notes in `research_articles/README.md`, source of truth; this is a pointer, not a duplicate.

- Macenski & Jambrečić (2021) — SLAM Toolbox — the algorithm this robot runs.
- Grisetti, Stachniss & Burgard (2007) — GMapping/RBPF — the particle-filter alternative.
- Kohlbrecher, von Stryk, Meyer & Klingauf (2011) — Hector SLAM — the no-odometry alternative.
- Heß, Kohler, Rapp & Andor (2016) — Cartographer — the submap/branch-and-bound alternative.
- Konolige, Grisetti & Kümmerle (2010) — Sparse Pose Adjustment — Karto's back-end, `slam_toolbox`'s lineage.
- Censi (2008) — point-to-line ICP (PLICP) — the scan-matching metric.
- Grisetti, Kümmerle & Stachniss (2010) — graph-based SLAM tutorial — the pose-graph optimization math.
- Moravec & Elfes (1985) — occupancy grid mapping — the Bayesian log-odds update.
- Laksono & Kusuma (2022) — Hector SLAM vs. GMapping on an RPLidar-A1 — empirical comparison on similar hardware.
- Sugiura & Matsutani (2021, 2022) — FPGA acceleration for 2D LiDAR SLAM — quantifies embedded-hardware compute constraints.

# Appendix B — Open Questions and TODOs

## B.1 Immediate (current debugging cycle)

- Reproduce and characterise the motor-stopping / vibration / non-compliance symptoms in isolation via the serial monitor. Identify whether the trigger is a specific manoeuvre, a specific motor, a specific commanded magnitude, or a serial-protocol edge case.

- Confirm whether the active controller for this debug iteration is the ESP32 firmware or whether a transition back to the Mega is intentional.

- Stress-test the ROS 2 → ESP32 serial path with full PID throughput and motors under battery-powered load.

## B.2 Near-term

- Ground-load Kff recalibration — first complete in-place rotation on the ground, capture telemetry, back-calculate Kff per motor, update firmware.

- Phone dashboard — add ENABLE button for the arm subsystem.

- Update start_aislebot.sh wait condition to /dev/esp32 (not ttyUSB0).

- UV arm — measure and codify travel limits in firmware as soft stops.

- Delete deprecated hardware_launch.py to remove ambiguity.

## B.3 Phase 2 preparation

- Procure IMU: choose between BNO055 (recommended), MPU6050 (budget), and ICM-20948.

- Decide mounting location — close to the geometric centre to minimise tangential acceleration mixing into yaw rate.

- Decide host: ESP32 reads IMU over I²C and forwards over serial, vs Pi reads IMU directly.

## B.4 Phase 3 preparation

- Procure LiDAR: RPLiDAR A1 or A2.

- Mounting: high enough to clear cargo, low enough to detect aisle obstacles at the relevant height.

## B.5 Open methodological questions

- Should per-motor Kff be a single scalar, or a 2-D table over (target velocity × load)? Linear extrapolation of single-point air calibration to load conditions is unverified.

- How do we instrument the cargo arm's effect on chassis dynamics? Does opening the arms while strafing create a torque the wheel PID can't see?

- Long-term: revisit fuzzy-adaptive PID and MPC alternatives once the baseline fixed-gain PID is at full performance. Decision criterion: does the baseline produce visible imperfections in cargo-handling motion? If yes, advance; if no, the simpler controller wins.

## B.6 Infrastructure (added 4 August 2026)

- Verify eduroam actually reaches the internet from the Pi, not just link-layer association (Part XVI §16.3) — `ping` by IP, then by name, then HTTPS, to localise the gap.
- ~~Evaluate a hardware RTC (DS3231 or similar) so log-file timestamps are trustworthy across reboots without depending on an NTP-capable boot (Part XVI §16.3).~~ **Resolved 6 Aug 2026** — DS3231 wired and verified across a network-less power-cycle (§16.4).
- Run `tools/nab_pid_logger.py --test plant` — the last unmeasured quantity in the v3.0 controller (plant time constant τ, which `Kp` currently only estimates) closes with this one bench run.
- Re-verify the LiDAR/SLAM pipeline post-reboot and confirm `/map` publishes with no duplicate nodes present, then save the first ground-truth occupancy map (§16.8).
- ~~Elevate the LiDAR mount to clear the battery from its line of sight — deferred until the mapping pipeline itself is confirmed working (§16.8).~~ **Resolved 8 Aug 2026** — three-position placement trial run and compared; Position 2 (on top of the battery) selected (§17.4).
- Optional: redo Position 2's placement-trial run with a motion profile matched to Positions 1/3 (~270s, mostly-stationary-then-scripted) — the run that decided the mount was shorter and faster than the other two, so the winning margin isn't from a fully controlled comparison (§17.4). Not blocking, since the decision also rests on Position 2 being the only position that removes the battery from the LiDAR's line of sight by mechanism rather than by degree.
- ~~Confirm whether `ydlidar_ros2_driver`'s own `base_link→laser_frame` static transform matches `aislebot.urdf`'s updated offset, or still carries a stale default.~~ **Confirmed 11 Aug 2026** — it's the stale placeholder, `(0, 0, 0.02)` with zero rotation, not Position 2's real mount. **Still open**: the translation itself hasn't been corrected. Separate bug from §17.9's angular fix — that one corrected the scan's angle convention, not the mount's position in TF (§17.9).
- Re-run `tools/scan_bearing.py` against `/scan_reliable` now that both the tool and the mirror fix exist — a numeric double-check of the §17.9 fix, cheap now that it's just running a script rather than a full block-placement trial (§17.9).
- ~~**Re-measure the self-occlusion blind-sector bearings** from `docs/robot_photos/2026-08-11_recalibration_cw/` — that trial ran before the §17.9 mirror fix, so its specific degree values are in the wrong frame. The qualitative finding (~1/3 of the sweep blocked) stands; re-run the same block-placement method against corrected `/scan_reliable` before writing any scan mask from these numbers (§17.8–§17.9).~~ **Resolved 13 Aug 2026** — `scan_bearing.py` run at five headings, cross-checked against each other rather than read individually: `-135°` to `-45°` true bearing (a 90° wedge centred directly behind the robot) is present in all five, everything else in exactly one. Refines the ~120° pre-fix estimate to a measured 90° (§17.15, `Navigation_Theory.md` §4). ~~Still open: actually writing the mask into `scan_relay.py`~~ — **also done same session** (commit `7e4410c`, found on review to have been missed by this document's own §17.15 entry — see the correction logged there).
- ~~Deploy `aislebot.urdf` (safety-cushion visual) and `lcd_display.py` (network-status fix) to the Pi — both committed and pushed, neither yet deployed, both blocked on a window with real internet (the AisleBot-Pi AP has none by design). Neither blocks continued mapping/driving (§17.15).~~ **Resolved 13 Aug 2026** — all three pending files (those two plus `scan_relay.py`'s mask) deployed and confirmed working on hardware (§17.16).
- **Resolve whether the black cell cluster seen near the robot's own footprint is a real object or renewed self-occlusion.** Duplicate-process cause already ruled out (`ps aux` showed exactly one `scan_relay.py`, correctly timed to the post-redeploy session). Still needed: drive away and check whether it stays fixed in the room (real) or follows the robot (mask boundary needs widening, or a second occlusion source exists) — deliberately left for the next session rather than guessed at (§17.16). **First priority next session, before trusting the map for anything else, including the Nav2 test below.**
- ~~First-ever Nav2 hardware launch, not yet attempted.~~ **Reached 13 Aug 2026** — `Managed nodes are active`, `cmd_vel` chain confirmed wired through `collision_monitor` to the wheels (§17.17). Two real bugs found and fixed on the way (`collision_monitor` needing a full config block Nav2 cannot default; `route_server`/`docking_server` being started by `nav2_bringup` on this Nav2 build with no use on this robot, fixed by starting nodes explicitly in `nav2_slam.launch.py` rather than including the bringup file). **No goal sent yet** — blocked on the item below.
- ~~Confirm the mapping session's map origin actually resets to the zero mark before trusting it for anything.~~ **Superseded 14 Aug 2026** — a genuinely fresh session (confirmed via clean `ps aux`, not just a restart attempt) *still* read `[0.685, -0.219]` at `-90.1°`, not `[0,0,0]`. Not a restart-verification problem after all; the "fresh session zeroes at the mark" model itself needs revisiting (§17.18).
- **Diagnose why `map→base_link` doesn't zero at a fresh session's start, before trusting the map's `(0,0)` as "the zero mark" ever again.** Hypothesis, untested: `slam_toolbox`'s `map→odom` initializes to identity rather than cancelling `base_link`'s current published pose, letting `odometry_publisher`'s own constant `-90°` (§17.10) pass straight through — consistent with the yaw landing near `-90°` on every fresh-session reading across two separate nights, and with the varying translation being `odom`'s own accumulated position at whatever moment it was last started, not something a new mapping session resets. **First test**: decompose `tf2_echo map odom` and `tf2_echo odom base_link` separately — whichever one carries the `-90°` settles which transform is actually responsible (§17.18).
- **Not blocking the first autonomous goal.** Compute goals from the robot's actual measured `map→base_link` transform (rotation matrix applied to "N metres forward in the robot's own frame"), not from an assumed `(0,0,0)` — correct regardless of which cause the diagnosis above finds (§17.18).
- `lcd_display.py`'s first version shipped with a real bug (IP lookup failed specifically on the AisleBot-Pi AP, the one mode it was built for) — fixed same session, but flagging the general lesson: a fix motivated by this project's own network flakiness should be tested against the actual failure mode it's meant to survive, not just the happy path, before calling it done (§17.15).
- ~~Chassis-occlusion + danger-cushion validation (does the footprint rectangle track the corrected scan correctly, does the 6 cm margin behave as intended) — scoped for the next session's dedicated mapping/SLAM branch, not this one (§17.9).~~ **Resolved 12 Aug 2026** — `base_link`'s kinematic origin located by watching the robot's in-place rotation pivot and tape-measured: exactly the geometric center of the chassis in both length and width. `nav2_params.yaml`'s existing symmetric footprint confirmed correct as-is, no change needed (§17.12).
- ~~**Measure the robot's true overall length and width with a tape measure** and set `nav2_params.yaml`'s footprint (both costmaps) accordingly.~~ **Resolved 8 Aug 2026** — 36 × 100 cm measured, footprint set to 1.12 × 0.48 m, URDF chassis box corrected (§17.7).
- Recompute `aislebot.urdf`'s chassis inertia tensor — still the value derived for the pre-correction 0.50 m box. Gazebo-simulation-only impact, nothing on the real robot; do it if the sim is ever used quantitatively (§17.7).
- `system/slam_nodom.yaml` still has `max_laser_range: 12.0`, above the YDLIDAR X4 Pro's actual 10 m maximum (inherited from the originally-planned RPLiDAR A1). Deliberately not changed blind while the file is live on the robot; fold into the next intentional deploy (§17.6).
- Add `robot_state_publisher` + the URDF to `aislebot_full.launch.py` so `/robot_description` exists on the real robot (currently only in the Gazebo sim launch) — needed for Foxglove to draw the actual chassis rather than a bare TF axis (§17.6).
- Update `aislebot.urdf`'s chassis and footprint geometry to match `base_link`'s new non-standard axis convention (`+X`=right, `+Y`=forward per §17.10's odometry fix) before `robot_state_publisher` is ever added — the box is currently modelled long along `X`, which is now the wrong axis (§17.10).
- Fine-tune a small residual LiDAR yaw misalignment noticed after §17.10's fix was confirmed working — distinct from §17.9's reflection bug (that one was fixed and stays fixed), this is a minor rotational offset on top of an already-correct scan. Non-blocking; adjust `scan_relay.py`'s `yaw_offset_deg` by the small residual amount once it's been measured, not guessed (§17.11).
- **Resolve whether the 12 Aug session's 19:21 mapping run started from the physical zero mark.** Asked of the user twice, never confirmed before the session ended (§17.14). First thing next session: check before driving further; if unconfirmed or no, stop that run and restart from the mark rather than build on an uncertain origin.
- LiDAR-to-`base_link` offset now measured (`Y = +0.27 m` forward, `X ≈ 0`, §17.12) but deliberately not written into `aislebot.urdf` — folds into the existing item below once that file's whole axis convention is swapped, not before.
- Update `aislebot.urdf`'s chassis and footprint geometry to match `base_link`'s new non-standard axis convention (`+X`=right, `+Y`=forward per §17.10's odometry fix) before `robot_state_publisher` is ever added — the box is currently modelled long along `X`, which is now the wrong axis (§17.10). Real measurements for the chassis box and the LiDAR joint are now in hand (§17.12) — this is now a mechanical swap, not a re-measurement.
- Investigate whether the wall-gaps seen in the first real mapping trial are pure under-coverage or partly the still-unimplemented self-occlusion phantom-obstacle mechanism (`Navigation_Theory.md` §4) — check whether false-occupied cells track the robot's own position at the time rather than a fixed point in the room (§17.13). Only resolvable with more real mapping data, not from this session's trial alone.
- Fix `joy_to_aislebot.py` publishing `/cmd_vel` on idle-gamepad zeros before ever running a joystick and Nav2 together — currently inert (no gamepad attached on this deployment) but would fight Nav2 for `/cmd_vel` at 25 Hz vs. 20 Hz if one were plugged in (§17.14). A `twist_mux` or a `use_joystick:=false` guard when launching Nav2 would both work.
- Re-verify whether eduroam→GitHub HTTPS is actually still unreliable from the Pi — §17.11 recorded a TLS handshake failure, but a plain `curl` to raw.githubusercontent.com returned a clean `HTTP 200` on the first try this session (§17.14). Not chased further; worth a deliberate re-test before continuing to route all deploys through `scp` from the Windows PC on the assumption that curl doesn't work.
- Save the first real, post-fix ground-truth map and run the first-ever Nav2 autonomous drive on hardware — both still fully open going into the next session (§17.14); `nav2_slam.launch.py` is written, deployed, and built, but has never actually been launched.
- **Test whether a pure-forward move itself introduces a small unintended lateral component** — the candidate explanation (§17.30) for the original 1-3cm side-drift observed after a forward-and-return round trip, now that pure lateral motion tested in isolation has been shown just as accurate as forward motion. Not yet tested directly.
- Confirm whether the recovery-count cold-start pattern found in §17.30 (worst on the first lateral goal of a fresh Nav2 bringup, better on the next one in the same session) is mecanum-roller stiction/backlash or an MPPI/costmap warm-up effect — low priority, since final positional accuracy is unaffected either way; would need 3+ repeats in one fresh session to see whether the recovery count keeps dropping and plateaus.
- **Split `map→base_link` into `map→odom` and `odom→base_link` across a jump event** — the decisive diagnostic §17.29 designed and never ran, now backed by §17.31's 16-event dataset. `tools/bag_tf_diff.py` was built for exactly this and has never been run once. Pre-committed decision tree in `docs/Dashboard_Map_System.md` §1. **First task of the next session; nothing in `slam_nodom.yaml` should be tuned before it.**
- **Verify `nav2_params.yaml`'s `amcl.robot_model_type: "omnidirectional"` against the installed Nav2's plugin names** (§17.31). On Jazzy this parameter is loaded as a pluginlib class name and the expected value is `"nav2_amcl::OmniMotionModel"`; the bare string is the pre-Galactic form. The whole `amcl` block has never run once, so this has never had a chance to surface — and a plugin that fails to load aborts the entire `lifecycle_manager` bringup, the same all-or-nothing failure §17.17 hit. Check `grep -rn "OmniMotionModel" /opt/ros/jazzy/share/nav2_amcl/*.xml` before the first `navigation.launch.py` run.
- **`src/mecanum_robot/resource/dashboard.html` is dead code** (§17.31): installed by `setup.py` as a data file, read by nothing. The page actually served is the `DASHBOARD_HTML` string constant at `phone_dashboard.py:112`. Either delete the file or make `index()` read it — but not as a drive-by change during the dashboard map work, since silently swapping the served page mid-build would confuse every subsequent test.
- **`phone_dashboard.py`'s WebSocket has no server→client path** (§17.31) — `ws_clients` is tracked but never broadcast to, by an explicit past decision documented in the `/calib_status` handler. This is the single largest piece of missing plumbing between today's dashboard and the map-rendering product; design in `docs/Dashboard_Map_System.md` §E.1.
- `phone_dashboard.py`'s `start_mapping()` launches `mapping_full.launch.py` with `stdout=DEVNULL`, discarding the SLAM console. Fine for casual driving, but it means a dashboard-launched mapping run cannot be diagnosed after the fact — launch mapping from a terminal (teed to a file) for any run that is being investigated.

## B.7 Opened by the 28 Aug strategic audit (§17.43)

- **There is still no accepted commissioning map.** Every downstream item — `map_server`, AMCL, named locations, stable coordinates, point-and-go — is blocked on one saved grid that does not exist. Acceptance criteria fixed at: `map_integrity.py` verdict not `FOLDED`, **D2 doubled walls < 1.0%**, unknown < 50%, physical return-to-mark < 0.15 m.
- **Stage D committed, not deployed** — `coarse_search_angle_offset` 0.349 → 0.175, hash `0e88d60c…`. Pre-committed fallback if corner rotations lose track: **0.25**, not back to 0.349.
- **Stage E, still untouched and resting on the same stale §17.21 premise as everything already corrected**: `angle_variance_penalty` 1.2 → 0.6, then `distance_variance_penalty` 0.7 → 0.4. The premise ("wheel odometry over-reports strafe by 25%") predates `lateral_scale` and is false; the config currently instructs the matcher to distrust its best input.
- **CPU headroom has never been worked deliberately.** Control loop 7.5–13.7 Hz against 20 Hz requested; planner 1.25 Hz against 5. Ranked levers, one at a time: MPPI `batch_size` 1000 → 400; `map_update_interval` 1.0 → 2.0; global costmap `update_frequency` → 1.0 and `publish_frequency` → 0.5. Note that Stage C + D independently cut front-end search cost ~10× (§17.43).
- **`xy_goal_tolerance: 0.02`** is smaller than the pose jitter of the estimate itself, so the controller cannot converge. Raise to ~0.12 before any accuracy claim is made about goal-reaching.
- **The location library does not exist.** Designed in `Production_Architecture.md` §3.3; no code written. Two endpoints (`/save_location`, `/goto_location`) and a JSON file tied to a map name, with a UI warning when the loaded map does not match.
- **A tape-measured, photographed ground truth for the zero mark has never been recorded.** Costs thirty seconds on the next drive and cannot be recovered afterwards. Do it on the next commissioning attempt.
- **Not a code item, but the highest-value cheap action available**: add up the actual invoices for the robot already built, to get a real BOM cost (`Vision_Indian_Market.md` §9). One evening, and a report containing a measured BOM is far more credible than one containing a projection.

# Revision Log

| **Date**     | **Version** | **Summary**                                                                                                                                                                                                                                                                                                                                                                                |
|--------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 16 May 2026  | v1.0        | Initial release. Covers project from inception through the 14 May 2026 PID validation run. Catalogues hardware, software, the v3 open-loop era, the migration to ESP32, the PID + FF design, all known debugging episodes (Parts VI–VII), 11 principles, current status, autonomy roadmap, appendices.                                                                                     |
| 09 June 2026 | v1.2        | Firmware audit pass against aislebot_esp32_v2.ino. Table 17 corrected (was Mega-era D-pin numbers; now ESP32 GPIO map). Added Part XII (ESP32 Firmware Deep Dive). Three explicit reconciliations: D14-D21 vs ESP32 GPIOs, 921600 vs 115200 baud, physical wire swap vs software sign arrays. Note: v1.1 was an interim file with no content delta from v1.0 (file-name renumbering only). |
| 22 June 2026 | v1.3        | Added the UV-C tube lighting subsystem section (embedded in Part IX): hardware inventory from bench photos, the continuously-powered-inverter / 240 V-side staged-relay architecture, the cross-inverter safety rule, the aislebot_arm_v7 → v8 firmware changes (staged `<U1>`/`<U0>`/`<U?>`), the arm_bridge.py / phone_dashboard.py integration, the 22 June deployment, and the open items (floating-pin strike on unpowered Mega, pack BMS rating, burn-in, warning beacon). (Logged retroactively.) |
| 08 July 2026 | v2.0        | Major update — Phase 3 opened. Added Part XIII (LiDAR + SLAM bringup: YDLIDAR X4 Pro, the identical-CP2102 udev port-pinning, the best-effort/reliable QoS relay, rf2o dropped, the scan-matching-only slam_nodom pipeline, verified 26 June). Added Part XIV (dashboard v2.2 desktop mouse+keyboard, self-hosted AisleBot-Pi AP, CycloneDDS Jazzy syntax fix, repository consolidation + rename to NarrowAisleBot, MIT license, checksum-verified-against-Pi discipline). Added Part XV (current status snapshot, superseding Part IX). Updated Part X Phase 3 from planned-RPLiDAR to as-built YDLIDAR. Updated Appendix A firmware/file names (esp32_v2→esp32, arm_v7→arm v8, +scan_relay, +A.6 LiDAR configs). |
| 04 Aug 2026  | v2.1        | Added Part XVI: the encoder-fault bench resolution (FR/FL cross-connection, not the shifter — full detail in `Bench_Test_Map.md`), the resulting per-motor-CPR firmware bug and its fix, and the full v3.0 PID/feedforward recalibration (two-term FF, Ki 30→250, dynamic anti-windup, 100 Hz loop, WiFi removed — derivation in `docs/PID_Calibration.md`). Logged the recovery and review of two bench CSVs: `run_20260702_183233.csv` (old firmware, pre-fix; 3–6% RMS tracking error) and, same day, `run_20260804_193703.csv` (post-flash confirmation on v3.0, wheels in air; 2.0–2.4% RMS error, 0% saturation, zero direction-sign faults). Documented the TXS0108E → single 8-channel discrete-MOSFET level shifter hardware swap and updated `Master_Reference.md` §2.5/§4.3–4.4 and `LevelShifter_Wiring.md` (now marked retired) accordingly. Logged a new open item: the Pi has no battery-backed RTC and its clock reliability during no-WAN operation is now flagged rather than assumed — one of the two CSVs above had a correct timestamp, the other didn't, which is exactly the failure mode this flags. Added B.6 (infrastructure TODOs). Declared the encoder feedback loop closed on the hardware+firmware side (§16.5); ground calibration is next. Brought Part III's hardware inventory up to date (dual-encoder split with the GTK08 fronts, the discrete-MOSFET level shifter, ESP32 at 100 Hz with no radio) and documented the CPR-normalisation mechanism in `PID_Calibration.md` §1. Recorded §16.6: removing WiFi also removed the ESP32 escape hatch, a safety-relevant capability loss that several docs still described as live — all corrected. Noted Part XV as partially superseded for control-related content. |
| 06 Aug 2026  | v2.2        | Resolved the RTC open item from v2.1: DS3231 wired on the shared I²C bus, the two-RTC-device (`rtc0` SoC vs `rtc1` DS3231) discovery, and two custom systemd units targeting `/dev/rtc1` explicitly — verified across a full network-less power-cycle (§16.4 update). Added §16.7: a Pi-vs-GitHub code drift audit (no persistent git clone on the Pi, verified via sha256 instead of `git diff`) that found and fixed a deprecated CycloneDDS syntax, a `max_wheel_speed` launch-file override masking the corrected node default, and a dead Xbox-controller wait loop; also corrected `Network_SelfHosted_AP.md`'s stale "manual AP start" section. Added §16.8: the first real LiDAR ground test — a data-corruption episode matching the documented checksum-error failure mode (resolved, validated clean under a 2-minute drive test), followed by a separate `/map`-never-publishes failure root-caused to duplicate `/scan_relay` and `/static_tf_pub_laser` nodes left over from un-killed prior terminal sessions; resolved via a full Pi reboot rather than continued targeted process cleanup, re-verification pending. Updated B.6 to mark the RTC item resolved and add the pending post-reboot LiDAR/SLAM re-verification and the deferred LiDAR-elevation mounting fix. |
| 07 Aug 2026  | v2.3        | Reliable mapping as a system, not a manually-babysat pipeline (§16.9–§16.16). Root-caused and fixed the first ground-truth `/map` blockers: the undocumented `ydlidar.service` collision and `odom` never existing in TF because `esp32_bridge`'s `telemetry_enabled` defaulted off (§16.9); a third silent failure where the ESP32 could reset without the Pi's serial layer noticing, fixed with a periodic `<L1>` resend self-heal (§16.10); consolidated the 3-terminal LiDAR/SLAM bringup into one on-demand `mapping_full.launch.py`. Re-verified all of it post-reboot clean (§16.12). Added a **Map** button to `phone_dashboard.py` (v2.3), replacing RECORD RUN — one press launches the mapping stack and starts telemetry/PID recording together as a single action, no separate toggle (§16.13). Added `run_report.py`, a pure-stdlib Python port of `telemetry_analyzer.html`'s metrics/findings logic, so every mapping run gets an automated PID+map analysis report the moment it stops — numerically cross-checked against the browser tool's own JS, exact match (§16.14). Confirmed the entire chain end-to-end on real hardware in one clean run: Map button → subprocess-managed launch tree → map saved while slam_toolbox was still alive → clean teardown → auto-generated report, zero manual steps (§16.15). Merged onto `main` as the new baseline, archived the superseded `aislebot_pid_analysis_v2.py` to `past_iterations/`, added `docs/Important_Commands.md`, and cleaned up merged/superseded branches (§16.16). |
| 07 Aug 2026  | v2.4        | Opened Part XVII — SLAM, visualization, and autonomous drive, two-week timeline, everything grounded in literature going forward (§17). Literature-reviewed the SLAM algorithm choice via Scite before touching any parameters: confirmed `slam_toolbox` (Macenski & Jambrečić, 2021) is the scientifically justified pick against GMapping/RBPF, Hector SLAM, and Cartographer, not just the incumbent; surfaced one concrete reasoned recommendation for next session — re-evaluate the scan-matching-only (no odometry prior) config now that odom-TF is confirmed reliable, since that config's original justification (unreliable odometry) no longer holds (§17.1). Added `docs/SLAM_Theory.md`, deriving the actual math (point-to-line ICP scan matching, pose-graph nonlinear least-squares optimization, Bayesian log-odds occupancy grids) with an explicit tie back to this project's own `run_report.py`/`telemetry_analyzer.html` map classification. Added `research_articles/`, a living, DOI-cited bibliography (new Appendix A.7) — ten papers, all verified via Scite, none retracted. Documented the next session's ready-to-execute LiDAR placement trial: three candidate mount positions × one standardized test motion (§17.2). Session and branch close out at §17.3 — the next phase begins in a new session on a new branch. |

| 08 Aug 2026  | v2.5        | Closed out the LiDAR placement trial from §17.2 (§17.4): three mount positions run and compared via the Map button's automated reports. Position 3 (elevated) was the cleanest controlled comparison and showed no improvement over baseline — the temporary-box elevation was insufficient to clear the battery's occlusion. Position 2 (on top of the battery) had the best `unknownPct` despite a less-controlled run, and was selected on that plus being the only position that removes the battery from the LiDAR's line of sight by mechanism rather than degree. `aislebot.urdf`'s `laser_joint` origin updated to match the reported mount deltas (+7.5 cm height, ~20 cm rearward). B.6 updated: the elevation item resolved, two new open items added (optional clean Position 2 redo; confirming `ydlidar_ros2_driver`'s own static transform matches the URDF update). |

| 08 Aug 2026  | v2.6        | Completed the visualization phase (§17.5): added `foxglove_bridge` to `install.sh` and `aislebot_full.launch.py` (port 8765, always-on), with connection steps in `Important_Commands.md` §6, then deployed and confirmed on hardware the same session — `/map` and the `slam_toolbox` pose graph observed building live in Foxglove Studio during a Map run. Found and corrected a premise in `SLAM_Theory.md` §2.3 while scoping the follow-up: `slam_nodom.yaml`'s `odom_frame: odom` plus `odometry_publisher` running continuously via `aislebot.service` means every mapping run since §16.9's odom-TF fix has already had a live odometry prior, despite the filename — there's no second "with-odom" config to write. Revised the actual benchmark to a genuine no-prior control run (`odometry_publisher` stopped) vs. current-as-is, now that live visualization makes drift directly observable rather than only inferred from `unknownPct`. |

| 08 Aug 2026  | v2.7        | Opened the autonomy phase (§17.6), literature before parameters as in §17.1. Added `docs/Navigation_Theory.md` (costmap inflation math and the inscribed/circumscribed-radius semantics, layered costmaps, A\* global planning and why `allow_unknown` decides whether exploration is possible, DWA's velocity-space search and its local-minima limitation, MPPI's importance-weighted alternative and its GPU caveat, and self-occlusion as a navigation failure rather than a mapping annoyance) plus six papers to `research_articles/`. Established that the proposed physical occlusion-calibration experiment isn't needed for its stated purpose — the footprint is a declared polygon, not a measurable quantity, and Nav2 already publishes the exact live footprint visual on `published_footprint`; the experiment that *is* needed (self-occlusion sector identification) works by in-place rotation with no props, since self-occlusion is invariant in the laser frame under rotation. Found and fixed four latent bugs in the never-yet-run `nav2_params.yaml`: a footprint 10 cm smaller than the robot in both axes, both costmaps subscribing to best-effort `/scan` instead of `/scan_reliable` (a recurrence of §13.4's QoS trap in a new consumer), `allow_unknown: false` (unusable against ~85%-unknown SLAM maps), and `odom_topic` pointed at a never-run EKF. Chose DWB over MPPI to start, on the Pi-5-has-no-GPU constraint, with MPPI as a measured upgrade. Four new B.6 items, including a blocking tape-measure of the true footprint. |

| 08 Aug 2026  | v2.8        | Footprint tape-measured (§17.7), resolving §17.6's blocking item: 36 × 100 cm, giving a Nav2 footprint of 1.12 × 0.48 m. Found the URDF's chassis `<box>` (0.50 m wide) was the wrong number, not the hand measurement — the URDF's own wheel-joint origins (0.375 m outer) agreed with the tape and were unaffected, since inverse kinematics and odometry consume those, not the visual/collision box. Corrected `nav2_params.yaml`'s footprint (both costmaps) and `aislebot.urdf`'s chassis width; left the chassis inertia tensor deliberately stale (Gazebo-only impact) rather than substitute an un-derived guess. |
| 11 Aug 2026  | v2.9        | Self-occlusion measured directly by block-placement trial rather than inferred from map coverage stats (§17.8) — found a blind sector roughly a third of the full sweep, explaining the placement trial's stubborn ~85%-unknown maps better than battery occlusion alone. While running that trial, found and fixed a LiDAR scan mirror bug (§17.9): a block in front was appearing behind, measured against three bearings defined by how the robot actually drives (not the REP-103 textbook convention, which a first attempt wrongly assumed and which was caught before deployment). All three measurements solved one relationship — a reflection, not a rotation, provably outside what any `tf2` static transform could correct — fixed by re-indexing the scan in `scan_relay.py` (`mirror=True, yaw_offset=270°`), verified against the runtime remapping function, deployed, and confirmed live: "now it maps perfectly." Added `docs/LiDAR_Orientation_Calibration.md` (full derivation and code) and `docs/robot_photos/2026-08-11_recalibration_cw/` + `2026-08-11_orientation_fix/` (photographic evidence, captioned). B.6 updated: the live TF's stale placeholder translation confirmed still-open and separate from this fix; §17.8's blind-sector bearings flagged as needing re-measurement in the corrected frame; chassis-occlusion/danger-cushion validation scoped forward to the next session's dedicated branch. |

| 11 Aug 2026  | v2.10       | Diagnosed and fixed the map-drift-while-driving-forward symptom that appeared right after §17.9's fix (§17.10). Raw `tf2_echo odom base_link` measurements across controlled single-axis moves showed standard REP-103 (`+X`=forward), contradicting the `W`/`D` convention §17.9's LiDAR fix relied on; re-solving §17.9's block data with forward on `+X` reproduces the earlier-discarded `yaw_offset=180°` hypothesis exactly. Implemented that change in `scan_relay.py`, then reverted it at the user's explicit instruction: the LiDAR's `270°` value had stronger independent confirmation (a driving-toward-a-block video predating the drift symptom) than odometry's single raw-TF check, so the fix belonged on the weaker-evidence side instead. Landed as a constant −90° rotation of `odometry_publisher.py`'s *published* orientation and twist only, leaving its internal REP-103 kinematics/position integration untouched — verified algebraically at an arbitrary heading, not just the one tested. Updated `nav2_params.yaml` to match the resulting non-standard `base_link` (footprint, DWB velocity-limit roles, and `vx_samples`/`vy_samples` all swapped; AXES warning note added). New B.6 item: `aislebot.urdf`'s chassis geometry still assumes the old convention and needs correcting before `robot_state_publisher` is added. |

| 11 Aug 2026  | v2.11       | Confirmed §17.10's odometry fix live on hardware and closed out the branch (§17.11). Deployed via `scp` straight from the user's Windows PC to the Pi (`~/ros2_ws`, the actual workspace path — an earlier assumed path and a `curl`/eduroam TLS failure were both dead ends, consistent with B.6's long-flagged eduroam-reachability risk) after a `colcon build` and service restart. With Foxglove's 3D panel set to Fixed/Display frame = `base_link`, forward driving now shows the map correctly sliding away behind the robot instead of sideways — user-confirmed "perfect, absolutely perfect." Noted one small residual LiDAR yaw misalignment, distinct from §17.9's already-fixed reflection bug, deferred to next session as a new B.6 item. Updated `Important_Commands.md` §6 with the specific Foxglove frame settings used to diagnose and confirm this fix. Branch `claude/lidar-placement-trial-qzqghe` closes here, fully merged onto `main`; next session opens a new branch for actual mapping/SLAM and autonomous-drive runs. |
| 12 Aug 2026  | v2.12       | New branch `claude/mapping-autonomous-nav-695glw` (§17.12–§17.14), the actual mapping/SLAM/autonomy session §17.11 deferred to. Pi workspace audited and cleaned (old pre-fix maps archived, journald/apt cache trimmed, `~/ros2_ws/maps/` created). Physical "zero position" convention established and confirmed live in Foxglove — grounded in `slam_toolbox` setting a fresh session's map origin to wherever `base_link` is at the first scan. Footprint/LiDAR-offset geometry resolved by direct measurement rather than assumption: `base_link`'s kinematic origin located by watching the robot's rotation pivot, found to sit at the true geometric center of the chassis — confirming the existing symmetric Nav2 footprint is correct as-is, and giving a real (not estimated) LiDAR-to-`base_link` offset for whenever `aislebot.urdf`'s axis convention is swapped. First real mapping trials from the zero mark found two real map-quality issues (a wall showing a false gap, real open space showing false-occupied); root-caused to the driving pattern itself — out-and-back down each aisle's centerline, never close enough to either wall — rather than a code bug, with corrected driving guidance given. Separately, found and fixed three latent bugs in the never-yet-run Nav2 stack before first hardware bringup (a duplicate `odom→base_link` publisher via an unwanted EKF node, a missing `velocity_smoother` block that would have silently zeroed all forward/reverse motion on this robot's swapped-axis convention, and a `bt_navigator` config that would have failed to load its behaviour tree on the first goal); added `nav2_slam.launch.py` for driving autonomously while `slam_toolbox` maps. Deployed and built on the Pi; incidentally found eduroam→GitHub `curl` working cleanly this session, contradicting §17.11's TLS failure. Session paused at the user's request with two things explicitly still open: whether the running mapping session actually started from the zero mark (asked twice, never confirmed), and the first-ever Nav2 autonomous drive, not yet attempted. |
| 13 Aug 2026  | v2.13       | Same branch, continuation (§17.15–§17.16). `aislebot.urdf` converted to the robot's real axis convention throughout (chassis box, all four wheel joints, `laser_joint`) with the LiDAR's measured offset (`Y=+0.27 m`, `X≈0`) finally landed, resolving the landmine §17.10 had flagged and deferred. `robot_state_publisher` wired into `aislebot_full.launch.py`, with the vendor `ydlidar_launch.py`'s stale placeholder TF suppressed by launching the driver node directly — confirmed rendering the real chassis on hardware. A direct wall approach gave the first end-to-end scale/offset validation of the whole geometry chain (not just direction): ~7 cm by tape against 0.06–0.07 m in Foxglove. Added a visual-only safety-cushion link matched exactly to the Nav2 footprint polygon. The self-occlusion blind sector was finally re-measured in the corrected frame (five headings, cross-checked against each other): a 90° wedge, `-135°` to `-45°` true bearing, refining §17.8's ~120° pre-fix estimate — and masked in `scan_relay.py` the same session, without touching the mirror/`yaw_offset_deg` calibration. That masking commit briefly fell out of working memory across a context-summarization point and was incorrectly described as not-yet-done in a first draft of §17.15; caught by checking `git log` against what was being claimed, corrected in place rather than left standing. `lcd_display.py` repurposed to a persistent network-status readout at the user's request, shipped with a real bug (IP lookup failed specifically in AP mode, the one case it existed to cover), caught on hardware and fixed same session. A real `eduroam`/`IITB-Wireless` connectivity episode cost real time; resolved pragmatically rather than fully diagnosed. All three pending files confirmed deployed and working on hardware by session's end. One artefact — a black cell cluster near the robot's own footprint, real object or renewed self-occlusion — found and deliberately left unresolved. Session closed at the user's explicit request for a clean-context handoff to a new session on the same branch, with an explicit resolve-then-launch-Nav2 plan recorded for it. |
| 13 Aug 2026  | v2.14       | Same branch, continued directly rather than in a new session (§17.17). First-ever Nav2 hardware launch: two real bringup bugs found and fixed in sequence — `collision_monitor` had no config block and `observation_sources` has no sensible default, aborting the whole bringup; then `nav2_bringup`'s `navigation_launch.py` on this (newer-than-expected) Nav2 build also starts `route_server` and `opennav_docking`, and `docking_server` refused to configure with no charging dock on this robot. Fixed by adding a full `collision_monitor` block (velocity-aware `approach` polygon against the live footprint and the masked, reliable scan — incidentally the "guarded drive" feature requested earlier, native to Nav2) and by rewriting `nav2_slam.launch.py` to start Nav2's eight needed nodes explicitly rather than including the bringup file. Third attempt reached `Managed nodes are active` — the milestone this whole phase has been building toward — with the `cmd_vel` chain confirmed wired end-to-end through `collision_monitor` to the wheels. No goal was sent: `tf2_echo map base_link` at the physical zero mark read `[0.285, -0.090]` at `-89.5°`, not `[0,0,0]`, and an attempted mapping restart to fix it did not visibly take effect (a second reading shared the identical `X` value, the signature of the same session settling rather than a new one). Session closed with this as the explicit single blocking item for next time, ahead of both the block-cluster question and the first autonomous goal. |
| 14 Aug 2026  | v2.15       | New day, same branch (§17.18). A genuinely fresh mapping session — confirmed via clean `ps aux`, not just attempted — still read `map→base_link` as `[0.685, -0.219]` at `-90.1°`, not `[0,0,0]`. This overturns the model stated since §17.12 ("a fresh session zeroes the map origin to the physical start pose"), not just §17.17's specific readings: that model was asserted from general SLAM convention and never verified against this project's actual `slam_toolbox` behaviour, and the yaw landing near `-90°` on every fresh-session reading across two nights — the same magnitude as `odometry_publisher.py`'s own deliberate constant `-90°` (§17.10) — is a concrete, testable, not-yet-confirmed hypothesis that `map→odom` initializes to identity rather than cancelling `base_link`'s already-rotated published pose. Two tracks recorded, deliberately not conflated: diagnosing the real cause (decompose `map→odom` and `odom→base_link` separately) versus getting a first autonomous drive working today regardless, by computing goals from the robot's actual measured transform rather than an assumed `(0,0,0)` — correct either way, not blocked on the diagnosis. Session closed at the user's request for a clean-context handoff, same reasoning as §17.16. |
| 14 Aug 2026  | v2.16       | Same day, new session (§17.19) — both §17.18 tracks resolved. The `map→odom` identity hypothesis confirmed exactly by direct decomposition. `tools/nav_goal.py` added, computing goals from the robot's live measured transform rather than an assumed origin. A second `bt_navigator` config bug found the same way as §17.14/§17.17's (`default_nav_to_pose_bt_xml: ""` doesn't trigger Nav2's built-in fallback on this build; fixed by resolving the real path in the launch file, verified against this build's own reference config rather than guessed) and a self-inflicted DDS participant-exhaustion failure from orphaned processes, found and killed via `ps aux`. **First-ever autonomous goal sent on this robot** revealed a real bug: the robot drove 88.4° off the commanded direction and was E-stopped near an obstacle, root-caused to `/cmd_vel` never having been reconciled between Nav2's TF-axis convention and `teleop_asym`'s REP-103 convention (§17.10 rotated odometry's output but never the velocity input). Fixed with a new `cmd_vel_axis_adapter` node converting explicitly between the two — both conventions independently hardware-validated, so neither was edited — placed after `collision_monitor` so its footprint-polygon safety check stays in a consistent frame; drive speeds also halved at the user's request. Two validation goals after the fix (0.5 m forward, then return) both `SUCCEEDED` with single-digit-degree direction error, no E-stop needed — **the first-ever autonomous forward-and-return round trip on this robot**, this phase's stated goal. `collision_monitor`'s long-open `max_points` warning fully closed (confirmed harmless/deprecated from Nav2's own source). Session paused mid-flow at the user's need to step away, not a design boundary; hardware state not independently confirmed at pause. |
| 14 Aug 2026  | v2.17       | Same day, continued session (§17.20). Foxglove click-to-goal wired up (`/goal_pose` topic corrected from the stale `/move_base_simple/goal`), with the 90°-clockwise arrow-drag correction documented. Two wrong hypotheses chased and corrected in place for why the built map appeared to vanish at some headings during a hand-driven 360° spin: Foxglove's Fixed Frame (ruled out — the user's own exported panel JSON showed `map`/`follow-none`, both already correct) and `slam_toolbox`'s `minimum_travel_heading` threshold (ruled out — checked directly against `shouldProcessScan` in `slam_toolbox`'s own source, which would have let a rotation-only scan through). Real cause, grounded in `slam_nodom.yaml`'s own "no external odometry, scan-matching only" design: pure rotation with a 360° lidar and no motion prior gives the matcher little unambiguous signal to confidently commit an update; any translation introduces parallax and unlocks it immediately — confirmed by the user's own four-times-repeated controlled experiment, and a live demonstration of exactly the IMU-fusion gap this session's literature survey flagged as the field's standard fix. `tools/zero_point_scan.py` added: automates the hand-found procedure (rotate, check whether `/map` actually grew, only nudge if it didn't, always return to the exact start pose) — designed, written, pushed, but **not yet run on hardware**. A second latent axis-convention bug found and deliberately left unfixed: `behavior_server`'s `Spin`/`BackUp` recovery behaviors were never given the `cmd_vel` remap `controller_server` and `velocity_smoother` already have, so `BackUp` would likely repeat the exact 88° miss fixed earlier the same day; the new script sidesteps this entirely by using only `NavigateToPose`. Manual mapping continued by hand in parallel (strafe/forward-backward, deliberately no rotation) and produced substantially denser, better-defined coverage than any earlier map this session — direct confirmation the underlying mechanism is understood correctly. Session closed for the night, not at a design boundary; next session opens on the same branch with the small-first `zero_point_scan.py` test as the explicit first step. |

| 18-19 Aug 2026 | v2.18 | Phase 1 reopened, partly closed (§17.23): the pending `odometry_publisher.py` live-read `lateral_scale` fix actually deployed and confirmed (`0.92`, not the stale cached `0.80`), `tools/pathlog.py` committed, re-zero re-confirmed on both `odom→base_link` and `zero_point→base_link`. Full tape-measured manual-drive validation designed but not completed — the user redirected to Phase 2 before it finished, recorded honestly rather than smoothed over. DWB replaced with MPPI (`motion_model: Omni`), the explicit, source-grounded decision extending §17.22: every MPPI critic is additive with no reject path, so DWB's rotation failure class cannot occur by construction. Two stock MPPI critics dropped for assuming REP-103 axes this robot doesn't have (`PathAngleCritic`, `PreferForwardCritic`), same bug class as three earlier sessions' fixes. In-place-rotation clearance worked out collaboratively against real measured geometry (right 4 m, front 2 m, left ~0.75 m, rear ~1.07 m from centre), catching an edge-vs-centre reference-point ambiguity in the user's own estimate before it became a wrong safety margin. Two real, previously-latent Nav2 bugs found at first MPPI bringup: `wait_for_service_timeout` set to `5` (milliseconds, not seconds — aborted bringup against a server that was already up), and `inflation_radius` below the robot's own padded circumscribed radius (forcing full-polygon collision checks on every one of MPPI's ~10,000-per-cycle footprint tests). First-ever hardware motion under MPPI: a 45° in-place rotation (8.5 mm centre drift, zero recoveries) and a 0.30 m translation (0.7° heading hold), both clean — direct counter-examples to every DWB rotation failure this branch has logged. `SimpleGoalChecker`'s tolerance found to be returned as systematic ~4.5 cm/2.8° error rather than noise (MPPI has no reward for landing closer than required) and tightened to `0.02 m`/`0.025 rad` from the same runs' demonstrated capability. |
| 19 Aug 2026 | v2.19 | `tools/repeatability_test.py` added for the user's APS presentation data (§17.24): repeated, tape-measured out-and-back trials per direction, distances and a hard safety ceiling set from v2.18's clearance figures. First hardware run produced motion the user accurately called "very very random" — traced via exact log timestamps to a real bug, not a hardware fault: `send_goal_and_wait`'s client-side timeout (20 s) fired while the goal was still genuinely executing server-side (it succeeded on its own 87.4 s in, safely), and the next goal sent afterward preempted the still-running first one mid-drive, from an unexpected intermediate pose — two goals racing on one controller. Fixed by making `send_goal_and_wait` explicitly cancel any goal it gives up on, in both this script and, proactively, `zero_point_scan.py`, which carries the identical latent flaw. Per-goal timeout raised 20 s → 150 s, directly justified by the measured 87.4 s completion time. Separately and honestly left open: why that particular 1.00 m strafe took 87 s at all (repeated progress-checker failures at a suspiciously exact ~10.2 s cadence, one automatic Spin recovery, and control-loop-rate drops coinciding with each recovery's costmap replan) — plausible Pi-5 CPU contention or a moving-target replanning effect, not distinguished this session. Explicit next step: confirm hardware state, re-zero, re-run the fixed script small first — it has not yet had a single hardware confirmation of its own. |

| 19 Aug 2026 | v2.20 | A second, structurally different hardware failure (§17.25): the LiDAR scan and `slam_toolbox` stopped publishing simultaneously mid-run under severe CPU starvation (controller loop 20→6.5 Hz, planner 5→1.23 Hz), with `bt_navigator` driving a `Spin` recovery blind (`"Robot pose is not available"`) — the actual cause of the erratic motion and collision the user reported. Same run also confirmed a real loop-closure failure independent of the crash: `(0.5033, −0.0445)` recorded as home despite the robot being parked on the physical mark. `system/slam_nodom.yaml` given its first-ever loop-closure/scan-matcher tuning block, every value justified against a specific measured number from this project's history (masked-beam fraction, prior odometry error, measured drift) rather than copied from a default. Not yet hardware-tested. Separately, the user's "fixed zero point, map only grows around it, never recentres" mental model was checked and confirmed correct — the observed recentring is `map→odom` correcting via loop closure, working as designed; the defect was that closure wasn't firing, not that correction exists at all. |
| 19 Aug 2026 | v2.21 | Three tutorial scripts (SLAM Toolbox + Nav2) read against the real repo, at the user's explicit request to restart with them in hand — scoped down via a direct question to "add the missing pieces, keep the validated tuning" rather than a ground-up rebuild (§17.26). `base_footprint` checked and found already present and correctly modelled in `aislebot.urdf`; deliberately not switched to as `base_frame` anywhere, since it differs from `base_link` only by a constant Z offset with no rotation and doing so would be pure churn against validated config for a ground robot. Two real gaps found and fixed: (1) three manual-control publishers and Nav2's `cmd_vel_axis_adapter` all wrote straight to `/cmd_vel` with zero arbitration — a direct contributor to why the v2.20 SLAM-crash collision was hard to interrupt — fixed with `twist_mux` (manual priority 100 over nav priority 10, `config/twist_mux.yaml`), manual publishers moved to `/cmd_vel_manual`, Nav2's fully-adapted output moved to `/cmd_vel_nav_out`; (2) `navigation.launch.py` (map-once-then-AMCL mode) had never been run and would have hit both the `docking_server` all-or-nothing lifecycle failure §17.17 already found once, and the 90°-axis-convention bug §17.19 already found once, on its first real use — rewritten as an explicit-node launch file mirroring `nav2_slam.launch.py`'s validated pattern, with `map_server`+`amcl` (already fully configured, never exercised) replacing the external `slam_toolbox` as the localization source. Neither fix has hardware confirmation yet. |

| 19 Aug 2026 | v2.22 | First hardware confirmation of the §17.25 loop-closure tuning (§17.27): a controlled rotate-90°-drive-straight-return test on the physical zero mark read back `(-0.011, 0.017)` m / `-0.17°` — ≈2 cm, down from the pre-tuning `≈50 cm` measured on the same setup. The continuous trace shows loop closure visibly firing (large single-sample corrections that shrink and tighten as the robot re-approaches the origin), not just a good final number. First real use of the Foxglove Fixed-Frame=`zero_point` + Grid + `trajectory_viz.py --map-frame zero_point` setup as intended. Two long flat stretches in the trace noted as probably-just-parked rather than a repeat of §17.25's CPU freeze, not independently confirmed. |

| 19 Aug 2026 | v2.23 | The very next drive after §17.27's clean result produced repeated large pose jumps while commanding pure forward motion — perceptual aliasing suspected (§17.28): today's loop-closure tuning deliberately loosened match-acceptance thresholds to fix §17.25's no-closures-at-all problem, and the same loosening plausibly lets the matcher accept spurious matches in this map's self-similar corridor-junction geometry. Not confirmed against a log yet — deliberately not re-tuned on a guess. `trajectory_viz.py` gained an `epoch_s` CSV column (wall-clock) so a future run's plotted trajectory can be correlated directly against `slam_toolbox`'s own terminal output at the moment of a jump. |
| 20 Aug 2026 | v2.24 | Executed §17.28's plan on hardware (§17.29): a real `trajectory_viz.py` crash found and fixed (`8e943fc`, epoch_s made samples 5-tuples but `_leg_stats` still unpacked 4 — cost one full run's CSV before the fix), `tools/bag_tf_diff.py` added (`d2e0f10`) to pull a TF pair's correction history straight out of a rosbag. First redrive reproduced nothing (map still too empty for aliasing to bite); second drive over the same ground a second time reproduced a real jump with full data — 25.5 cm / 2.41° at epoch `1787233020.150`, both SLAM log and rosbag covering it. Grepping the log for it came back empty for a decisive reason, not a search failure: checked against the exact installed `slam_toolbox` (`2.8.5`), confirmed no listener is registered anywhere for automatic loop-closure accept/reject events — no console output, no topic, nothing observable, verified against both source and the live node's own topic list. Plan pivoted to comparing `map→odom` against `odom→base_link` at the jump instead, via `bag_tf_diff.py` against the bag that already covers it — not yet run when the session closed for the night. A second, unrecorded jump happened later the same drive with nothing running to capture it. |
| 21 Aug 2026 | v2.25 | Forward/backward round-trip accuracy validated on hardware (~1.2cm net error, three independent measurements), then the day's actual focus — lateral drift — investigated in depth (§17.30). The stray `number_of_recoveries: 1` anomaly from the forward/back test's return leg root-caused directly: `nav2_controller::PoseProgressChecker`'s ~10s `movement_time_allowance` firing (`Failed to make progress` → costmap clear → replan), not a `behavior_server` Spin/BackUp event, explaining why the earlier targeted grep found nothing. Two independent pure-lateral round trips (`nav_goal.py --forward 0.0 --right 0.5`, out and back) gave a 4-leg dataset: final resting error landed in a tight 1.97-1.99cm band regardless of recovery count (0, 1, or 3) — `SimpleGoalChecker`'s tuned 0.02m tolerance, not drift — while recovery count itself formed a clear cold-start pattern (3→1→1→0, worst on the first lateral goal after each fresh Nav2 bringup) that also explains an earlier-observed bent path in Foxglove as several stitched-together replans, not one curved plan. `trajectory_viz.py`'s net round-trip figure for the second attempt (1.63cm) matched the forward/back benchmark's tier, establishing pure lateral motion as just as accurate as forward motion in isolation — reframing the original 1-3cm side-drift as more likely a side effect of the forward-motion command path itself, not a lateral-axis limitation. Two new B.6 items recorded for this. Session continued directly (no re-zero) into a fourth, compound test. |
| 21 Aug 2026 | v2.26 | Same day, later session (§17.31). The compound four-waypoint test's fourth leg failed outright — 5 progress-checker stalls, a timed-out `Spin` and a timed-out `BackUp` (the first behaviour-server recovery failures in this project's history), never reaching its goal; legs 2 and 4 targeted the same pose and leg 2 was clean, which rules out goal tolerance. Foxglove click-to-goal reached a working state for the first time and its three silent-failure steps documented in `Important_Commands.md`. A full clean restart verified against the §8 re-zero procedure. **The finding that matters:** a 4,818-sample trajectory recording, re-derived independently from the raw CSV, showing 16 single-sample steps >5cm totalling 27.6% of the entire reported path length, the largest 31.1cm in 0.10s (~3.1 m/s apparent, 6-20x physically possible) — the third independent reproduction of §17.28's suspected perceptual aliasing and the first with enough events to characterise it: every jump yaw-coupled, directions bimodal rather than uniform, magnitude growing monotonically, two 0.1s doublets — all pose-graph signatures, none of them noise signatures. Traced to §17.25's deliberate relaxation of exactly the parameters that reject a bad closure, in an environment `slam_nodom.yaml`'s own comment block had predicted this outcome for in writing. **Strategic reframe recorded:** live SLAM is not what the product navigates on (AMCL on a saved map is), so it needs to be good enough to build one clean map once, not to navigate reliably — a far narrower and more achievable target. Two suspected bugs found by reading rather than running: `amcl.robot_model_type` likely needs Jazzy's pluginlib class name, and `resource/dashboard.html` is dead code the served page never reads. Full build plan written to `docs/Dashboard_Map_System.md`; `Next_Session_Kickoff.md` rewritten around it. |

| 24 Aug 2026 | v2.27 | Pre-drive audit session (§17.33); the robot never moved. `tools/pi_audit.sh` written and run — a read-only 16-section Pi inventory whose last section diffs every deployed source file against GitHub, generalising the one-file hand audit that found §17.32's undeployed config. Stage B's `slam_nodom.yaml` independently re-confirmed by sha256. The Pi identified as *exactly* one commit behind by file size as a fingerprint: `phone_dashboard.py` at 87,320 B and `odometry_publisher.py` at 10,783 B are precisely commit `fe2c3be`, so live map rendering and click-to-goal were already deployed and `0bea474`'s ZERO button, MAP-owns-the-workflow and pose CSV were not. **A second §17.32-class defect caught before it fired:** `system/ydlidar_params.yaml` was committed flat with no `ros__parameters` nesting, which binds nothing in ROS 2 and would have dropped the X4 Pro to compiled defaults — `install.sh:220` would have overwritten the working copy, and it survived only because install.sh has not run since 26 June. Fixed byte-identical to the Pi's proven file; `LiDAR_SLAM_Bringup.md`, whose values-only listing seeded the error, corrected too. The audit script's own rev 1 was wrong in three places (vcgencmd thermal test, a renamed-on-copy path reported MISSING, and per-file HEAD requests reporting files as absent that the same run had matched) — rev 2 fixes all three. 133 MB of MCAP rosbags found in `~/slam_tests`, outside the data folder and missed by a `rosbag2_*` search; two of the three have never been opened. Recorded that no finding in Part XVII has ever come from more than a single run, while 70 maps, 73 run reports and 124 telemetry CSVs sit unanalysed as a corpus. `tools/pi_clean.sh` applied: 2.0 GB reclaimed (58% → 51%), journald capped, desktop moved to `multi-user.target` for the CPU headroom §17.25 showed mattering. Deploy left mid-flight: odometry verified, dashboard probable-but-unverified, and neither built nor restarted. |

| 25 Aug 2026 | v2.28 | Second hands-on day (§17.34). Four latent bugs found and killed. **A drive-control leak in the map view** — touching the live map drove the robot, on phone and desktop — traced to `#mapView` being a *child* of `#joyArea`: z-index governs painting, not event propagation, so every touch bubbled into the joystick. Found by the user testing an assertion made from reading the CSS, which was wrong. **The map palette measured at 1.20:1** free-vs-unknown contrast, i.e. indistinguishable; repalletted to 3.81:1 on a stated rule (luminance rises with occupancy, unknown taken off-hue as absence-of-measurement rather than low-probability). **`system/ydlidar_params.yaml` was a live landmine since 13 Aug** — committed flat with no `ros__parameters` nesting, which binds nothing in ROS 2 and would have dropped the X4 Pro to compiled defaults the next time install.sh ran. **The map-loss-on-restart chain traced through four causes**: the shutdown path was dead code after `uvicorn.run()` (which never returns, because a connected phone's WebSocket blocks graceful shutdown until systemd SIGKILLs it); owning the signals directly; uvicorn 0.46 having renamed `install_signal_handlers` to `capture_signals`; and finally `map_saver_cli` failing because it subscribes to `/map` while `slam_toolbox` is being killed alongside it. Fixed by writing the `.pgm`/`.yaml` from the grid the dashboard already caches for its live view — no IPC, no subprocess, no dependency on anything else still running. **Confirmed on hardware**: a restart mid-mapping produced `run_20260825_151713.pgm`, 27,383 B, header stamped `# CREATOR: phone_dashboard from cached /map`. Best return-to-mark ever recorded: **1.9 cm / 0.2°**. **All 30 deployed files hash-verified against main** — the first fully known robot state in this project. `main` consolidated: it shared no common ancestor with the working branch (orphan root) and had not moved since 11 Aug; merged with `--allow-unrelated-histories` plus `nab-hardware-calibration`, which held 36 files existing nowhere else. Added `tools/map_corpus.py` for cross-run comparison. Two network failure modes documented after costing real time: Windows mDNS being unreliable, and `curl --retry` not retrying TLS handshake failures. |

| 26 Aug 2026 | v2.29 | No-hardware session (§17.35); nothing driven, nothing yet run against the live node. **The map-acceptance gate turned from a judgement into two instruments.** `tools/map_integrity.py` measures the fold signature §17.32's gate describes in words: its headline detector flags two near-parallel walls with **free** space between them across a gap narrower than the robot's own 0.48 m — free cells mean the LiDAR returned through that space, so something saw both faces across a gap nothing could occupy, which is what a closure produces when it fuses two poses that are not the same pose. Flagged cells are clustered and reported in map coordinates because the known hole in that argument, a real gap between shelves seen end-on, is one place you can walk to while a fold is a whole wall duplicated. Four supporting measures (thickness, skeleton branch points, orientation histogram, free-space components), thresholds explicitly provisional, and `--corpus` prints the percentiles that should replace them — the first thing here designed to be *calibrated* by the 70-map archive §17.33 recorded as unanalysed. Self-tested on five synthetic rooms including three false positives, of which "two walls 0.30 m apart with UNKNOWN between" is the one that proves the free-space requirement is what discriminates. **`tools/graph_residuals.py` built, and the MATLAB item that specified it corrected.** Reading `publishGraph()` before writing showed `/slam_toolbox/graph_visualization` carries node positions and edge endpoint *coordinates* only — no orientation, no node ids, no edge measurement, no information matrix — so `edgeResidualErrors` as literally specified is **not implementable** against it. What replaced it is stronger: the graph is republished every second, a node that moves between two publications was moved by the optimiser, and differencing the edge sets over the same two messages names which closure caused the shift. **That is the per-closure signal §17.29 concluded did not exist** — not as an event, as a difference — and it yields a judgeable number, implied drift rate = shift / metres driven, against this project's own measured 1.5–3.3%. **`nav2_params.yaml:57` confirmed from upstream source and fixed**: `plugins.xml` exports only `nav2_amcl::OmniMotionModel`, `amcl_node.cpp` defaults to the fully-qualified name and passes the string straight to `createSharedInstance` with no shim and no try/catch on the `on_configure` path, so `"omnidirectional"` would have aborted the whole `lifecycle_manager` bringup, not just localisation. |

| 29 Aug 2026 | v2.30 | First hands-on day of the endgame week (§17.44). **G1 passed** — all four pending files deployed, hashed per file on arrival, and the live node confirmed at `coarse_search_angle_offset 0.175` / `correlation_search_space_dimension 0.3`; before deployment it read stock `0.349`, confirming the debt by measurement rather than report. **G2 passed** on a 621 s commissioning drive: max correction **0.2018 m** (<0.30) and max heading step **4.57°** (<10°), against 0.696 m / −18.40° on 28 Aug, with cumulative correction per metre down 3.1×. The discriminator is that 4.57° is 46% of the new 10.03° window where 18.40° was 92% of the old 20° one — the corrections did not re-pin to the new boundary, so the gate is a real lever and not a clamp. **The day's finding: `slam_toolbox` adds no pose-graph node and no map cell while the robot rotates in place.** Three runs; a deliberate test produced **714° of rotation over 642 s for 43 occupied cells = 2.1 m of wall and zero corrections**. `/scan_reliable` was measured publishing at 11.4 Hz throughout, killing the stalled-scan hypothesis. `minimum_travel_heading` was falsified as the gate by direct test — set to 0.05 and verified live, a full 360° gave `n=1, e=0` for 166 s. **Every stop-and-spin corner driven since §17.39 contributed nothing**, which is a better explanation for maps returning 63–87% unknown than anything previously considered, and means G4 was never reachable by that procedure. Turning *while translating* works: a 111 s `W`+`E` arc produced **18 nodes and 1545 cells = 77.2 m of wall**, 88% of the perimeter drive's coverage in 18% of its time. **Sharpest result: 18 nodes, 17 corrections — one jump per node**, at a 3.65 s cadence confirmed independently in video, so the matcher disagrees with odometry by 0.15–0.37 m on every scan it accepts. **Three parameter sets left cumulative correction at 2.80 / 2.85 / 2.86 m** — invariant to within 2% — so the tuning moves the distribution of the error and never the amount; Stage E (`angle_variance_penalty` 1.2 → 0.6) is answered **no**. Proposed as hypothesis: the tight circle is a **degenerate geometry** — at 5 m range 1° of heading is indistinguishable from 8.7 cm of translation — which predicts the measured signature (heading right to ~4°, position 27.6 cm out, wheels closing to 0.008 m) and explains why no search parameter moved the total. **The perimeter drive was the good case all along and three diagnostics were spent on a bad proxy for it.** Two `run_analyzer.py` false positives identified and left unpatched deliberately (changing an instrument mid-campaign destroys its baseline): the wheel-spread alarm fires on arcs where the ICR sits on the inner wheels (radius 0.54 m vs `K_o` 0.56069 m), and the correction/doubled-wall co-location counted one wall seven times inside a coincidence radius larger than the whole trajectory. Evidence in `docs/evidence/rotation_deadzone/`. |

| 1 Sep 2026 | v2.31 | First session on the autonomy branch (§17.49). **The tape measure closed the loop, twice, from opposite ends.** Nav2 drove 4.27 m and finished **9 cm right of the mark** with the map reading zero; the operator hand-drove 4.58 m, finished **on** the mark, and the map read 6.0 cm out. Nav2 closes its loop on the map pose, so a corrupted estimate becomes *physical* error; drive by hand and the error stays in the estimate. Wheel odometry agreed with the tape to ~1 cm both times and closed **4.582 m to 3.1 mm (0.07%)**, the best in this project's history. The displayed pose was reconstructed from `map = R(corr_yaw)·odom + corr_t` to **four decimals**, so nothing on screen was wrong — the screen only ever held the estimate. Peak `map→odom` **20.3 cm**, and **56/59/57%** of all three runs sat past 5 cm, invariant across two controllers, three routes and both `use_scan_barycenter` settings. **Six dashboard defects found by audit, two about safety.** Every dragged goal heading had been 90° wrong — a bare `atan2(dy,dx)` (from +X) written into the field `robotPose.yaw` initialises (from +Y), while `drawGoalMarker` drew from +X and `drawRobot` from +Y, so the picture agreed with the wrong number; fixed structurally via `vecToYaw`/`yawToVec` as exact inverses shared by both renderers and the command path, with `goal_pose_adapter` left at 0.0. **E-STOP did not survive a reconnect** (`ws.onopen` re-armed unconditionally while the button read TAP TO RESUME), and **`send()` failed silently**, reporting success for commands that never left. The existing headless test had passed since 28 Aug because it measured *position* and never *heading* — extended to 19 checks, each new guard verified by reverting its fix and watching it fail. **The fix that mattered was not a bug fix:** the pose card now shows `ODOM` and a `DRIFT` figure, red past 5 cm, and read **0.203 m live mid-drive** where the old card showed a clean return. `required_movement_radius` **0.30 → 0.10** — the 0.30 m/10 s bar was a 0.030 m/s floor against a measured 0.027–0.037 m/s cruise, so goals aborted while driving normally; audited both ways, and **two goals, zero aborts** on hardware the same evening where every prior run aborted once per goal. `amcl initial_pose` yaw **−1.5708 → 0.0**, the fifth stale §17.38 compensation, uncaught because AMCL has never run. **Stage F registered before the drive and left unscored** — the run was hand-driven so the protocol was not followed, and its took-effect check was **retracted** when the 0.175 m baseline behind it proved to be an artefact of measuring displacement-from-origin instead of path length. **Three self-inflicted failures recorded:** a `colcon build` that printed *2 packages finished* while destroying `mecanum_navigation`'s dist metadata, killing `goal_pose_adapter` and `cmd_vel_axis_adapter` — the whole of "goals weren't working" and why one run had to be hand-driven; a confidently-wrong expectation about the DRIFT card on a parked robot; and `main` 27 commits stale, which caused an external audit to be written four sessions out of date. **Structural finding: AMCL could not have worked** — `mapping_full.launch.py` was the only launcher of the LiDAR and `navigation.launch.py` forbids running alongside it, so AMCL would have activated with no `/scan` forever. Split into `sensors.launch.py`, MAP's behaviour verified unchanged node-by-node. `main` merged current at `5cace67` via PR #9. |

Future revisions append rows here. When in doubt about whether something deserves an entry, err toward writing it — the value of this document is the path travelled.
