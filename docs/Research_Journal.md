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
| ESP32-WROOM-32    | 38-pin module, CP2102 USB-UART, 240 MHz, 4 MB flash | Real-time PID + feedforward velocity controller at 50 Hz, encoder counting via PCNT, WiFi AP for joystick teleoperation |
| Arduino Mega 2560 | ATmega2560, 16 MHz                                  | UV-arm stepper controller (separate subsystem)                                                                          |

The dual-microcontroller split is deliberate. The ESP32 has the throughput and hardware peripherals needed for four-channel quadrature encoder counting at the ~93,000 pulses/second the drive motors produce under load. The Mega cannot service that interrupt rate while also handling stepper drivers, so responsibilities are partitioned by physical capability rather than by software architecture.

## 3.2 Drive motors

| **Specification**                  | **Value**                                |
|------------------------------------|------------------------------------------|
| Model                              | Rhino RMCS-2086                          |
| Operating voltage                  | 24 V DC                                  |
| No-load speed                      | 60 RPM (≈ 6.28 rad/s)                    |
| Gear ratio                         | 1 : 47                                   |
| Encoder type                       | Quadrature (A / B channels), built-in    |
| Encoder CPR (full quadrature)      | 93,132 counts per output revolution      |
| Encoder pulses at max load (all 4) | ≈ 93 k pulses / second across the system |

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

The ESP32 operates at 3.3 V logic; the motor encoders output 5 V signals. Two TXS0108E bidirectional level-shifter boards translate between the two voltage domains, one handling the front axle and the other the rear.

| **Shifter** | **Side A (ESP32 3.3 V)** | **Side B (encoder 5 V)**   | **Channels in use**      |
|-------------|--------------------------|----------------------------|--------------------------|
| U1 (front)  | From ESP32 GPIO          | To FR encoder + FL encoder | FR (A1, A2), FL (A3, A4) |
| U2 (rear)   | From ESP32 GPIO          | To RR encoder + RL encoder | RR (A1, A2), RL (A3, A4) |

Power is daisy-chained: ESP32 3V3 → U1 V_CCA → U2 V_CCA, and Buck 5 V → U1 V_CCB → U2 V_CCB. Output Enable (OE) is tied to V_CCA on both boards. This daisy-chain has been the source of two debugging episodes — a broken wire on U2 ch1/2 took down RR; a later break on U2 ch3/4 took down RL. See Part VII for details.

## 3.7 User-interface and status hardware

| **Component**             | **Specification**                                                                                   | **Role**                                                |
|---------------------------|-----------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| 16×2 character LCD        | I²C interface via PCF8574 backpack, address 0x27                                                    | On-robot status display: mode, wheel directions, errors |
| Xbox 360 controller       | Dual analog sticks + buttons over USB                                                               | Primary teleoperation input                             |
| WiFi-based phone joystick | Hosted by ESP32 AP (SSID AisleBot-Control, password aislebot123) at HTTP port 80, WebSocket port 81 | Secondary teleoperation when Pi is unavailable          |

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
| ESP32 WiFi (AP mode)   | SSID AisleBot-Control, password aislebot123 | WiFi joystick fallback; HTTP :80, WebSocket :81                       |
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

Two honest caveats recorded for the record: (a) the AP does **not** yet start automatically on boot — autoconnect is off, so after a reboot the Pi returns to eduroam and the AP must be raised by hand (`sudo nmcli con up aislebot-ap`); making it the permanent default means writing it into netplan config, which is the next step. (b) The Pi has one radio, so hosting the AP means no internet; to go online, switch back to eduroam (`sudo nmcli con up eduroam`), which drops the current SSH session by design. The ESP32's own AP (`AisleBot-Control` @ `192.168.4.1`) remains the independent escape hatch for when the Pi itself is down — the PID lives on the ESP32, so the robot can still be driven or stopped with the Pi gone. Full detail in `docs/Network_SelfHosted_AP.md`.

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

# Appendix A — Document Catalogue

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

- setup.py — console_scripts entries.

## A.5 Firmware (ESP32 / Mega)

- aislebot_esp32.ino — active ESP32 firmware (renamed from aislebot_esp32_v2.ino in v2.0; v2.0 banner, content unchanged).

- aislebot_arm.ino — active Mega firmware, v8 (arm + staged UV-C lighting). Supersedes aislebot_arm_v7.ino.

## A.6 LiDAR / SLAM configs (new, v2.0)

- system/ydlidar_params.yaml — confirmed YDLIDAR X4 Pro driver parameters.

- system/slam_nodom.yaml — the working slam_toolbox config (scan-matching only); deployed at ~/ros2_ws/slam_nodom.yaml.

- ydlidar_ros2_driver — third-party, cloned by install.sh (branch humble), not vendored.

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

# Revision Log

| **Date**     | **Version** | **Summary**                                                                                                                                                                                                                                                                                                                                                                                |
|--------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 16 May 2026  | v1.0        | Initial release. Covers project from inception through the 14 May 2026 PID validation run. Catalogues hardware, software, the v3 open-loop era, the migration to ESP32, the PID + FF design, all known debugging episodes (Parts VI–VII), 11 principles, current status, autonomy roadmap, appendices.                                                                                     |
| 09 June 2026 | v1.2        | Firmware audit pass against aislebot_esp32_v2.ino. Table 17 corrected (was Mega-era D-pin numbers; now ESP32 GPIO map). Added Part XII (ESP32 Firmware Deep Dive). Three explicit reconciliations: D14-D21 vs ESP32 GPIOs, 921600 vs 115200 baud, physical wire swap vs software sign arrays. Note: v1.1 was an interim file with no content delta from v1.0 (file-name renumbering only). |
| 22 June 2026 | v1.3        | Added the UV-C tube lighting subsystem section (embedded in Part IX): hardware inventory from bench photos, the continuously-powered-inverter / 240 V-side staged-relay architecture, the cross-inverter safety rule, the aislebot_arm_v7 → v8 firmware changes (staged `<U1>`/`<U0>`/`<U?>`), the arm_bridge.py / phone_dashboard.py integration, the 22 June deployment, and the open items (floating-pin strike on unpowered Mega, pack BMS rating, burn-in, warning beacon). (Logged retroactively.) |
| 08 July 2026 | v2.0        | Major update — Phase 3 opened. Added Part XIII (LiDAR + SLAM bringup: YDLIDAR X4 Pro, the identical-CP2102 udev port-pinning, the best-effort/reliable QoS relay, rf2o dropped, the scan-matching-only slam_nodom pipeline, verified 26 June). Added Part XIV (dashboard v2.2 desktop mouse+keyboard, self-hosted AisleBot-Pi AP, CycloneDDS Jazzy syntax fix, repository consolidation + rename to NarrowAisleBot, MIT license, checksum-verified-against-Pi discipline). Added Part XV (current status snapshot, superseding Part IX). Updated Part X Phase 3 from planned-RPLiDAR to as-built YDLIDAR. Updated Appendix A firmware/file names (esp32_v2→esp32, arm_v7→arm v8, +scan_relay, +A.6 LiDAR configs). |

Future revisions append rows here. When in doubt about whether something deserves an entry, err toward writing it — the value of this document is the path travelled.
