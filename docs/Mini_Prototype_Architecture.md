# NarrowAisleBot — Mini Prototype Architecture

**A small-scale, ESP32-driven replica of the NarrowAisleBot (NAB) for SLAM, PID, and autonomous-navigation research**

Aritra Das (25D0074) · IIT Bombay, Dept. of Biosciences & Bioengineering · Prof. Ambarish Kunwar

> **Why this exists.** The full-size NAB's separate optical encoders stopped working reliably. Rather than fight the encoder-mounting problem again, this prototype uses **four geared DC motors with the encoder built into the motor** (Pro-Range PG36M555-19.2K + ME-37). It keeps the *defining* NAB feature — the **asymmetric mecanum wheelbase** — at roughly one-third scale, and reuses the exact **Raspberry Pi 5** and **YDLIDAR X4 Pro** from the NAB so the SLAM/Nav2 stack carries straight over. Goal: a bench-and-lab platform to develop **closed-loop PID**, **odometry + IMU fusion**, and **LiDAR-SLAM autonomous navigation** for an *asymmetric* base.

---

## 0. The short answers (you asked these directly)

| Question | Answer |
|---|---|
| **Same Raspberry Pi for both robots?** | **Yes — ideal.** The ROS 2 kinematics node is already parameterized (`l1, l2, d, r, max_*`). The prototype is just a **robot profile** (a params YAML + launch), not a code fork. Your SLAM config carries over unchanged. Physically you move the one Pi between robots (the NAB is down anyway), or clone the microSD if you want both alive. |
| **Same ESP32 for both?** | **Use a *dedicated* ESP32 for the prototype (~₹400 / \$5).** Same firmware codebase, different constants selected by one `#define`. Reusing the NAB's ESP32 works (its encoders are dead), but a second one means you never reflash/rewire on a swap and both robots stay intact. |
| **Same LiDAR?** | **Yes — reuse the YDLIDAR X4 Pro.** Your `slam_nodom.yaml` is already tuned to its scan characteristics, so Phase 3 params transfer directly. Its 0.12–12 m range is more than enough for a small robot in tight spaces. |
| **Motor driver?** | **2× SmartElex 13D** (the Robu board you linked) — dual-channel, 6.5–30 V, **13 A continuous / 30 A peak**, PWM+DIR, **3.3 V logic accepted**. It's a drop-in for the Cytron MDD10A I first named — *same* PWM+DIR interface, more headroom → **zero firmware changes**. Two boards = 4 motors. See §12. |
| **Wheel diameter?** | **80–100 mm is ideal for SLAM.** The **152 mm EasyMech set you already own will work** (just set `WHEEL_RADIUS = 0.0762`), but 152 mm + bush rollers coarsen odometry and raise the CG. Buy **100 mm (bearing rollers)** only if you want the cleaner build. Full reasoning in §12. |
| **IMU?** | **BNO055** — the sensor the NAB always planned for. On-board fusion → calibrated absolute yaw straight into `robot_localization`. I2C, 3.3 V, ~12 mA. |
| **Rated power?** | ~90 W continuous design point (motors light-load + Pi), >150 W transient. Battery **3S Li-ion ~5 Ah (55 Wh)**. The **PDB-XT60** you linked is great for *distribution* + the light 5 V loads, but its 5 V BEC is only **2 A** — **the Pi 5 still needs its own dedicated 5 V / ≥5 A buck.** See §12. |

---

## 1. What changes from the NAB, and what doesn't

| Layer | NAB (full size) | Mini prototype | Same? |
|---|---|---|---|
| Compute / planning | Raspberry Pi 5, ROS 2 Jazzy | **Same Pi 5** (robot profile switch) | ✅ reuse |
| SLAM sensor | YDLIDAR X4 Pro | **Same X4 Pro** | ✅ reuse |
| Real-time controller | ESP32-WROOM-32, PCNT PID @ 50 Hz | ESP32-WROOM-32, PCNT PID | ⚠️ dedicated unit, same code |
| Motors | 4× Rhino RMCS-2086, 24 V, 60 RPM, 93 132 CPR | 4× **PG36M555-19.2K**, 12 V, 262 RPM, **537.6 CPR** | 🔴 new |
| Drivers | 2× Cytron MDD20A (20 A) | 2× **Cytron MDD10A** (10 A) | 🔴 new (same family) |
| Wheels | DekuPro 6″ mecanum (r = 76.2 mm) | **80 mm mecanum** (r = 40 mm) | 🔴 new |
| Encoder interface | 5 V optical → TXS0108E level shifter | Hall @ 3.3 V → **direct, no shifter** | 🔴 simpler |
| Battery | 12.8 V LiFePO₄ 30 Ah + 24 V boost | 3S Li-ion ~5 Ah (no boost needed) | 🔴 new |
| IMU | BNO055 (planned) | **BNO055** | ✅ same plan |
| Kinematics | Asymmetric mecanum IK | **Same equations, new constants** | ✅ same math |

The **control architecture, firmware structure, ROS 2 graph, and kinematic form are identical.** Only the physical constants (geometry, wheel radius, CPR, feedforward, voltage) change. That is exactly what makes this a faithful small-scale replica rather than a different robot.

---

## 2. Motor analysis — Pro-Range PG36M555-19.2K + ME-37

| Parameter | Value | Notes |
|---|---|---|
| Motor family | 555-size brushed DC + PG36 planetary gearbox | 36 mm gearbox |
| Rated voltage | **12 V DC** | |
| Rated output speed | **262 RPM** = 27.44 rad/s | at 12 V |
| Rated torque | **45 N·cm = 0.45 N·m** | per motor |
| Gear ratio | **19.2 : 1** | base motor ≈ 262 × 19.2 ≈ 5030 RPM |
| Encoder | **ME-37, 7 PPR** (per channel, motor shaft), quadrature Hall A/B | magnetic |
| **Output CPR (full quadrature)** | **7 × 4 × 19.2 = 537.6 counts / wheel-rev** | what the ESP32 PCNT reads |
| Output CPR (2× / CHANGE mode) | 268.8 | legacy comparison only |
| No-load current (est.) | ~0.35 A | *confirm on datasheet* |
| Load current @ rated (est.) | ~1.5 A | *confirm* |
| Stall current @ 12 V (est.) | ~5.5 A | drives the driver sizing; *confirm* |
| Shaft | ~6 mm D-shaft (typical PG36) | match wheel hub to yours |

### 2.1 The one thing to watch: encoder resolution

The NAB's optical encoders gave **93 132 CPR**. These built-in Hall encoders give **537.6 CPR** — about **173× coarser**. That matters for *velocity estimation*, not position:

- Velocity quantization at a **50 Hz** loop (dt = 20 ms): one count = `(1/537.6)/0.02 = 0.093 rev/s = 0.584 rad/s`.
- At cruise (wheel ≈ 10 rad/s → 1.59 rev/s): **≈ 17 counts / 20 ms window** → clean.
- At crawl (wheel ≈ 2 rad/s → 0.32 rev/s): **≈ 3.4 counts / 20 ms** → coarse/jittery.

**Mitigations (in priority order):**
1. **Keep ESP32 PCNT full-quadrature** — it counts all 28 edges/motor-rev for free. Still the right tool.
2. **Lean on feedforward.** These motors are well-behaved; `Kff` supplies ~90 % of the PWM, the PID only trims. Coarse feedback hurts less when you're not relying on it.
3. **Heavier velocity smoothing:** set `VEL_FILTER_ALPHA = 0.3` (vs 0.5 on the NAB).
4. **Small/zero Kd.** A coarse encoder makes the derivative term noisy — start `Kd = 0.3` (or 0) and add only if needed.
5. **If low-speed velocity is still jittery, drop the PID loop to 25 Hz** (dt = 40 ms) — doubles counts/window at the cost of slower correction. The NAB's 50 Hz assumed a fine encoder; here 25–50 Hz is the honest range.

This is the single most important "what's different" for the firmware. Everything else is a constant swap.

---

## 3. Chassis geometry (scaled, asymmetry preserved)

The scientific point of the NAB is `l₁ ≠ l₂` (outer pair farther forward/back than inner pair), which narrows the track. The prototype keeps that ~20 % asymmetry at ~⅓ scale.

| Parameter | Symbol | NAB | **Prototype** | Applies to |
|---|---|---|---|---|
| Outer longitudinal dist. | l₁ | 0.403 m | **0.150 m** | FR, RL |
| Inner longitudinal dist. | l₂ | 0.333 m | **0.120 m** | FL, RR |
| Asymmetry offset | l₁ − l₂ | 70 mm (17 %) | **30 mm (20 %)** | — |
| Half-track width | d | 0.15769 m | **0.075 m** (150 mm track) | all wheels |
| Wheel radius | r (a) | 0.0762 m | **0.040 m** (80 mm) | all wheels |
| **K_outer = l₁ + d** | — | 0.5607 m | **0.225 m** | FR, RL |
| **K_inner = l₂ + d** | — | 0.4907 m | **0.195 m** | FL, RR |
| Deck footprint | — | 1000 × 250 mm | **≈ 360 × 180 mm** (≈ 400 × 200 mm incl. wheels) | — |
| Est. total mass | m | 45.54 kg | **≈ 3.5 kg** | — |

```
              FRONT
   FL (inner)        FR (outer)
   l₂ = 120 mm       l₁ = 150 mm
        ┌───────────────────┐
        │                   │
        │      DECK         │   ≈360 mm
        │   Pi5 · Lidar     │
        │   ESP32 · IMU     │
        └───────────────────┘
   RL (outer)        RR (inner)
   l₁ = 150 mm       l₂ = 120 mm
              REAR
   |←—— 150 mm track (2d) ——→|
```

> **Design trade-off (honest note):** I widened `d` slightly relative to a pure 0.37× scale (which would give d ≈ 58 mm). A 150 mm track is more stable and gives more rotational authority at bench scale, at the cost of a little "narrowness." Since the prototype's job is to *develop the control and SLAM stack for an asymmetric base* — not to physically fit a real warehouse aisle — stability wins. The asymmetry that matters scientifically (`l₁ ≠ l₂`) is fully preserved. If you'd rather maximize narrowness, set d = 0.058 m and K_outer/K_inner recompute automatically.

---

## 4. Kinematics (identical form to the NAB)

Body velocities: **vx** = forward (+), **vy** = right strafe (+), **wz** = CCW yaw (+). Wheel order **[FR, FL, RR, RL]**.

### Inverse kinematics (body → wheels)
```
ω_FR = (1/r) · ( vx + vy + K_outer · wz )     ← outer
ω_FL = (1/r) · ( vx − vy − K_inner · wz )     ← inner
ω_RR = (1/r) · ( vx − vy + K_inner · wz )     ← inner
ω_RL = (1/r) · ( vx + vy − K_outer · wz )     ← outer

r = 0.040   K_outer = 0.225   K_inner = 0.195
```

### Forward kinematics (wheels → body, for odometry)
```
vx = (r/4) · ( ω_FR + ω_FL + ω_RR + ω_RL )
vy = (r/4) · ( ω_FR − ω_FL − ω_RR + ω_RL )
wz = ( r / (2·(l₁+l₂+2d)) ) · ( ω_FR − ω_FL + ω_RR − ω_RL )

l₁+l₂+2d = 0.150 + 0.120 + 0.150 = 0.420   →   wz = (r/0.84)·(…)
```

### Limits
| Quantity | Value | Basis |
|---|---|---|
| ω_max (hardware) | 27.44 rad/s | 262 RPM |
| MAX_WHEEL_SPEED (firmware clamp) | **22 rad/s** | ~80 % of hardware, leaves PID headroom |
| MAX_LINEAR (SLAM cruise) | **0.45 m/s** | = ~11 rad/s wheel |
| MAX_ANGULAR | **2.0 rad/s** | outer wheel ≈ 11.25 rad/s at wz = 2 |

Direction/sign conventions are identical to the NAB — reuse the same `MOTOR_DIR_SIGN[]` / `ENC_DIR_SIGN[]` calibration procedure at commissioning (they **must** match per motor or the PID sees positive feedback → runaway).

---

## 5. Electronics — bill of materials

| # | Component | Model | Qty | Rail | Notes |
|---|---|---|---|---|---|
| 1 | Compute | **Raspberry Pi 5, 8 GB** (from NAB) | 1 | 5 V / 5 A | Ubuntu 24.04, ROS 2 Jazzy |
| 2 | Real-time MCU | **ESP32-WROOM-32** (38-pin) | 1 | 5 V (VIN) / 3.3 V | dedicated to prototype |
| 3 | Motors | **Pro-Range PG36M555-19.2K + ME-37** | 4 | 12 V | 262 RPM, 0.45 N·m, 537.6 CPR |
| 4 | Motor drivers | **SmartElex 13D** (dual 13 A) — or Cytron MDD10A | 2 | 12 V | PWM+DIR, 3.3 V logic, 30 A peak |
| 5 | Wheels | **100 mm mecanum** (buy) **or 152 mm EasyMech** (own) | 4 | — | 2× LH + 2× RH; see §12 |
| 6 | LiDAR | **YDLIDAR X4 Pro** (from NAB) | 1 | 5 V / 0.4 A | `/dev/ydlidar` @ 128000 |
| 7 | IMU | **BNO055** breakout | 1 | 3.3 V / 12 mA | I2C, on-board fusion |
| 8 | Battery | **3S Li-ion ~5 Ah** (or 4S LiFePO₄ ~4 Ah) | 1 | — | ≥20 A BMS; XT60 lead |
| 9 | Power distribution | **Matek PDB-XT60** (yours) | 1 | batt / 5 V | XT60 in → 2 drivers; 5 V/2 A BEC → ESP32+Lidar+IMU |
| 10 | **Pi 5 regulator** | **dedicated 5 V / ≥5 A buck** | 1 | 12 V→5 V | Pi 5 **only** — PDB's 2 A BEC is too weak |
| 11 | Main switch / E-stop | Rocker/SSR + **15–20 A blade fuse** | 1 | 12 V | latching E-stop mirrors NAB |
| 12 | (Optional) level shifter | TXS0108E | 0–1 | — | only if you power encoders at 5 V |

**Not needed vs the NAB:** the 24 V boost converter (motors are natively 12 V), and — if you power the Hall encoders at 3.3 V — the level shifters. **Note the two 5 V sources:** the PDB's 5 V BEC feeds only the light loads (ESP32 + Lidar + IMU ≈ 0.7 A); the Pi 5 gets its *own* buck (§6, §12).

---

## 6. Power architecture

```
Battery 3S Li-ion (11.1 V) ── XT60 ──► PDB-XT60
  [inline 15–20 A fuse + main switch on the battery lead]
        │
        ├─ PDB ESC pads (25 A×4) ─► SmartElex 13D #1 (VMOT) ─► FR, FL motors
        │                        └► SmartElex 13D #2 (VMOT) ─► RR, RL motors
        │
        ├─ PDB 5 V BEC (2 A) ─┬─► YDLIDAR X4 Pro       (~0.40 A)
        │                     ├─► ESP32 VIN            (~0.25 A) ─3.3 V─┬─► BNO055 (I2C)
        │                     │                                        └─► 4× ME-37 enc A/B
        │                     └─ (≈0.7 A total — well within 2 A)
        │
        └─ PDB VBAT pad ─► DEDICATED 5 V / ≥5 A BUCK ─► Raspberry Pi 5  (ONLY)
                           (the PDB's 2 A BEC cannot feed a Pi 5)
COMMON GROUND: the PDB already ties battery−, both driver grounds and the BEC
ground together — land the Pi-buck ground and the ESP32/encoder grounds on that
same PDB ground plane. (The PDB's 12 V linear BEC, 500 mA, is unused here.)
```

### 6.1 Power budget

| Load | Voltage | Typical current | Typical power | Peak note |
|---|---|---|---|---|
| 4× motors (light load) | 12 V | ~6 A (4×1.5) | ~72 W | stall surge ~22 A / >150 W (rare, all four) |
| Raspberry Pi 5 | 5 V | ~3 A typ (5 A max) | ~15–25 W | throttles if under-fed |
| YDLIDAR X4 Pro | 5 V | ~0.4 A | ~2 W | |
| ESP32 (WiFi AP) | 5 V | ~0.25 A | ~1.3 W | |
| BNO055 | 3.3 V | ~0.012 A | ~0.04 W | |
| **Continuous design point** | — | — | **~90 W** | size battery + fuse for transients |

**Runtime:** 3S 5 Ah ≈ 55 Wh → ~30–40 min mixed driving. 4S LiFePO₄ 4 Ah ≈ 51 Wh similar, with a flatter 12.8 V rail (closest to the NAB philosophy and to the motors' 12 V rating).

### 6.2 Rules carried over from the NAB (learned the hard way)
- **One common ground.** Missing any ground link → phantom motor behaviour (NAB Master Ref §3.2).
- **Don't power the ESP32 from the Pi's USB during motor runs** if you see jitter — Pi SMPS noise + PWM ground transients. Power ESP32 from the 5 V buck (VIN), keep the Pi↔ESP32 USB for data only (cut VBUS if needed).
- **Latching E-stop.** The NAB's 50 ms auto-clear E-stop was a genuine safety bug — this firmware keeps `<S>` latched until `<E1>`.

---

## 7. ESP32 pin map (unchanged from the NAB firmware)

Because we keep the two-driver layout, the **pin map is identical** — flash the same firmware, only constants differ.

### 7.1 Motor outputs → MDD10A (right side of board, 3.3 V logic direct)
| Motor | PWM | DIR | Driver |
|---|---|---|---|
| FR | G4 | G16 | Driver 1 Ch1 |
| FL | G17 | G18 | Driver 1 Ch2 |
| RR | G19 | G21 | Driver 2 Ch1 |
| RL | G22 | G23 | Driver 2 Ch2 |

### 7.2 Encoder inputs (Hall, 3.3 V — **no level shifter**)
| Motor | Enc A | Enc B | PCNT unit | Dir sign |
|---|---|---|---|---|
| FR | G36 (SP) | G39 (SN) | PCNT_UNIT_0 | −1 |
| FL | G34 | G35 | PCNT_UNIT_1 | +1 |
| RR | G32 | G33 | PCNT_UNIT_2 | −1 |
| RL | G25 | G26 | PCNT_UNIT_3 | +1 |

> **Change vs NAB:** the NAB's optical encoders were 5 V and needed a TXS0108E. The ME-37 Hall encoders are powered at **3.3 V** here, so their A/B outputs are already 3.3 V — wire them **straight to the ESP32 input-only pins**. If your specific ME-37 sample needs 5 V or you see missed counts over longer wires, fall back to the NAB approach: power the encoder at 5 V and put one TXS0108E in the A/B path.

### 7.3 IMU + spares
| Signal | GPIO | Use |
|---|---|---|
| I2C SDA | G14 | BNO055 (and optional LCD) — `Wire.begin(14, 13)` |
| I2C SCL | G13 | BNO055 |
| Spare | G27 | buzzer / status LED |

**IMU placement:** mount the BNO055 on the ESP32 I2C bus so the ESP32 can run an optional **heading-hold** inner loop, and forward yaw/quaternion to the Pi over the existing serial link (add an `<IMU,…>` telemetry line) for `robot_localization` EKF. Simpler alternative: hang the BNO055 off the **Pi's** I2C and let a stock ROS driver publish `/imu/data` — choose this if you only want it for SLAM/EKF and not for on-board control.

---

## 8. Software — the "same Pi" story

The NAB's `mecanum_teleop_asymmetric.py` already declares every geometry value as a ROS parameter. So the prototype needs **no code changes** — just a profile:

`ros2/mini_robot.yaml`
```yaml
mecanum_teleop_asymmetric:
  ros__parameters:
    wheel_radius: 0.040
    l1: 0.150
    l2: 0.120
    d:  0.075
    max_linear: 0.45
    max_angular: 2.0
    max_wheel_speed: 22.0
    input_source: cmd_vel
```

Launch the same stack with `--params-file ros2/mini_robot.yaml`. SLAM (`slam_nodom.yaml`), Nav2, the EKF, and the YDLIDAR driver are **unchanged** — the only robot-specific things are the geometry params above and the URDF frame offsets (LiDAR at ~0.12 m above deck, IMU at deck centre). Keep one Pi image; select the robot with a launch arg.

---

## 9. What's right, and what to watch

### ✅ Right / good decisions
- **Reusing the Pi 5 and X4 Pro** — the biggest time-saver; the entire SLAM/Nav2 investment transfers. The parameterized kinematics node makes it clean.
- **Built-in Hall encoders** — sidesteps the exact failure that stopped the NAB (separate encoder mounting/alignment).
- **12 V native motors** — no 24 V boost converter, simpler and lighter power train.
- **2× MDD10A** — same architecture and pin map as the NAB; generous 10 A headroom over ~5.5 A stall.
- **Keeping the asymmetric IK** — the prototype stays scientifically faithful to the NAB's novelty.
- **80 mm wheels** — a sane 1.1 m/s ceiling with plenty of wheel torque (0.45 N·m / 0.04 m ≈ 11 N per wheel).

### ⚠️ Watch / potential pitfalls
- **Coarse encoder (537.6 CPR)** — the headline caveat. Low-speed velocity is quantized; mitigate with feedforward, `VEL_FILTER_ALPHA = 0.3`, small `Kd`, and (if needed) a 25 Hz loop. See §2.1.
- **Feedforward must be re-measured.** NAB `Kff ≈ 40–48` was for 24 V/60 RPM motors. Here the wheel spins ~4× faster per volt, so expect **`Kff ≈ 8–12` PWM per rad/s** — start ~9.5 and recalibrate per motor in air, then on the ground.
- **Pi 5 power is real.** It can draw 5 A at 5 V; an undersized buck → brown-outs and CPU throttling mid-SLAM. Use ≥6 A and short, thick 5 V wiring.
- **Encoder logic voltage.** Confirm your ME-37 sample is happy at 3.3 V. If it wants 5 V, you're back to a level shifter (§7.2).
- **Mecanum handedness.** You need **2 left-handed + 2 right-handed** wheels, mounted so the rollers form an "X" from above. A wrong-handed wheel breaks strafing.
- **Battery sag.** 3S Li-ion at 11.1 V nominal runs the motors ~8 % slower than a true 12 V; 4S LiFePO₄ (12.8 V) is flatter and closer to spec if top speed matters.

### 🔴 Don't
- Don't reuse the **24 V boost converter** — these motors are 12 V.
- Don't drive these with a **TB6612FNG** (1.2 A continuous) — it can't survive stall.
- Don't let `MOTOR_DIR_SIGN` and `ENC_DIR_SIGN` disagree per motor (runaway).
- Don't skip the **fuse** and **latching E-stop**.

---

## 10. Build & bring-up order

1. **Mechanical:** cut the ~360 × 180 mm deck; mount 4 motors at the asymmetric positions (§3); fit LH/RH mecanum wheels correctly.
2. **Power:** battery → fuse → switch → 12 V motor rail + 5 V/6 A buck. Verify 5.0–5.1 V at the Pi under load *before* connecting the Pi.
3. **Wiring:** ESP32 ↔ 2× MDD10A (PWM+DIR per §7.1); encoders 3.3 V direct (§7.2); **one common ground**.
4. **Firmware:** flash `firmware/narrowaislebot_mini_esp32.ino` (prototype profile). Serial `<I>` should print r = 0.040, K_outer = 0.225, K_inner = 0.195, CPR = 537.6.
5. **Encoder check** (battery off): spin each wheel forward by hand → positive velocity. Flip `ENC_DIR_SIGN` if not.
6. **Motor check** (battery on, one at a time): `<T,0,3.0>` … `<T,3,3.0>` → each wheel forward. Flip `MOTOR_DIR_SIGN` if not.
7. **Deadband + feedforward calibration:** step PWM to find start-of-motion per motor; set `MIN_PWM_THRESHOLD`; measure `Kff` per motor.
8. **PID tune:** `<V,5,5,5,5>` → converge in <0.5 s. Start `Kp 25 / Ki 15 / Kd 0.3`.
9. **IMU:** bring up BNO055, confirm calibrated yaw.
10. **Pi:** launch with `ros2/mini_robot.yaml`; verify `/wheel_speeds`, then bring up the X4 Pro and SLAM with your existing config.

---

## 11. Simulate it first

- **`sim/wokwi/`** — a Wokwi project (paste into [wokwi.com](https://wokwi.com)) that runs the **asymmetric IK live**: three pots = vx / vy / wz, four "motor" LEDs show |ω| as brightness with direction LEDs, and the serial monitor prints the 4 wheel speeds plus a forward-kinematics round-trip. Verifies the math and pin logic before you touch hardware.
- **`docs/tools/mini_prototype_architecture.html`** — a standalone interactive architecture explorer (block diagram, BOM, live kinematics calculator, power budget, pin map). Double-click to open; no server needed.
- For the analog H-bridge / power side, [falstad.com/circuit](https://www.falstad.com/circuit/) is the better sandbox; Wokwi is for the ESP32 firmware logic.

---

---

## 12. Parts on hand — component decisions

Decisions on the specific parts you already have or linked, checked against their datasheets.

### 12.1 Motor driver — SmartElex 13D Dual Channel ✅ *better than my first pick*

From the manual you linked ([robu / SmartElex 13D](https://robu-prod-media.s3.ap-south-1.amazonaws.com/uploads/2018/01/FInal-manual-PDF.pdf)):

| Spec | Value | Why it matters here |
|---|---|---|
| Channels | **2 (dual)** | 2 boards = 4 motors — same two-driver layout as the NAB |
| Motor voltage | **6.5–30 V** | 12 V motors sit comfortably in range |
| Continuous current | **13 A** (no heatsink) | vs ~5.5 A motor stall → big headroom (more than the MDD10A's 10 A) |
| Peak current | **30 A / 10 s**, current-limited at 30 A | survives stall transients |
| Interface | **PWM + DIR** (also single-pin 50 %-duty mode) | *identical* to the firmware's `setMotorOutput()` — no code change |
| Logic level | **3.3 V and 5 V** (VIOH 3–5.5 V) | ESP32's 3.3 V drives it directly, no level shifter |
| PWM frequency | up to **20 kHz** | keep the firmware's 5 kHz, or raise to ~18 kHz for silence |
| Protection | thermal shutdown + under-voltage lockout | nice safety margin |

**Verdict: use it — it's a drop-in upgrade.** The SmartElex 13D is functionally the same class as the Cytron MDD10A/MDD13A (sign-magnitude PWM+DIR, wide-Vin, 3.3 V-tolerant), with *more* current headroom. Wire **Board 1 → FR, FL** and **Board 2 → RR, RL** exactly as in the §7 pin map. Tie each board's **logic GND to ESP32 GND** (common-ground rule). The firmware needs **no changes** — it already speaks PWM+DIR. Get **2 boards**.

### 12.2 Wheels — 152 mm EasyMech (own) vs 100 mm (buy)

Your [EasyMech 152 mm aluminium mecanum set](https://robu.in) is the **same 6-inch size as the full-size NAB** (r = 0.0762 m). It will physically work — but for a *SLAM* prototype it's not the best choice, for concrete reasons tied to your coarse encoder:

| | **80 mm** | **100 mm** *(recommended buy)* | **152 mm** *(you own)* |
|---|---|---|---|
| radius r | 0.040 m | 0.050 m | **0.0762 m** |
| hardware v_max | 1.10 m/s | 1.37 m/s | **2.08 m/s** |
| **odometry: distance / encoder count** | 0.47 mm | 0.58 mm | **0.89 mm** |
| **velocity quant / count @ 50 Hz** | 0.023 m/s | 0.029 m/s | **0.045 m/s** |
| traction force / wheel (0.45 N·m) | 11.3 N | 9.0 N | **5.9 N** |
| rollers | bearing | bearing | **bush** |

**Why size matters here:** the encoder is *already* coarse (537.6 CPR, §2.1). Bigger wheels **multiply** the metres-per-count, so 152 mm gives ~**2× coarser odometry and velocity resolution** than 80 mm — the two coarse effects stack, and odometry quality is exactly what Phase 2/3 (EKF + SLAM) depend on. **Bush rollers** also rumble/vibrate more than bearing rollers, adding noise to both odometry and the IMU. And a 152 mm wheel on a 360 mm deck is oversized — higher CG, front/rear wheels close together.

**Recommendation:**
- **If budget/time is tight → use the 152 mm you have.** Nothing in the firmware or geometry changes except `WHEEL_RADIUS = 0.0762` and a hard software speed cap (set `MAX_LINEAR = 0.40` m/s → wheel ≈ 5.3 rad/s, plenty for SLAM). Get the platform moving, validate PID + SLAM, and only upgrade if odometry noise bothers you.
- **If you want the clean build → buy 100 mm bearing-roller mecanum wheels.** Better proportions on this deck, ~1.5× finer odometry than 152 mm, smoother rollers. This is the one place I'd spend money on this robot.
- Either way you need **2 left-handed + 2 right-handed** wheels (rollers forming an "X" from above) and a hub coupler matching your PG36 output shaft (≈6 mm D — verify yours).

> **You do NOT strictly need to buy 100 mm.** The 152 mm works. It's a "good enough vs. ideal" call, and for a SLAM-focused robot the ideal leans smaller.

**If you keep the 152 mm**, the profile becomes: `wheel_radius: 0.0762`, `max_linear: 0.40`, `max_wheel_speed: 10.0` in `ros2/mini_robot.yaml`, and `ROBOT_PROFILE` in the firmware gets `WHEEL_RADIUS = 0.0762f` (geometry `l1/l2/d` are axle positions — unchanged by wheel size).

### 12.3 Power — PDB-XT60 is **not enough on its own** for the Pi 5

From the [Matek PDB-XT60 manual](https://robu-prod-media.s3.ap-south-1.amazonaws.com/uploads/2018/02/pdb-xt60_manual_en.pdf):

| PDB output | Rating | Use in this robot |
|---|---|---|
| Input (XT60) | 3S–4S, **9–18 V** | 3S Li-ion (11.1 V) fits |
| ESC pads | **25 A×4 / 15 A×6** continuous | ✅ distribute battery to the 2 SmartElex drivers |
| **5 V BEC** | DC/DC buck, **2 A cont (2.5 A/10 s)** | ✅ ESP32 + Lidar + IMU (~0.7 A) — but **✗ NOT the Pi 5** |
| 12 V BEC | **linear, 500 mA** (and only ~10 V on 3S: "Vbatt − 1 V") | ✗ unused — too weak, and not 12 V on 3S |

**The Pi 5 needs up to 5 A at 5 V (27 W).** The PDB's 5 V BEC delivers **2 A**. If you run the Pi from it, it will brown-out and CPU-throttle mid-SLAM — the classic "why did my map glitch" failure. So:

**→ Yes, you need a separate 12 V→5 V converter — a dedicated 5 V / ≥5 A buck for the Raspberry Pi 5.** Good options: Pololu D36V50F5 (5 V/5 A), a quality 5 V/5–6 A UBEC, or any Pi-5-rated 5 V/5 A supply module.

**But the PDB is still worth using** — it does two useful jobs:
1. **Distribution:** XT60 battery in → its high-current ESC pads cleanly feed both motor drivers (25 A×4 ≫ your ~6 A nominal / ~22 A worst-case stall), and it consolidates grounds.
2. **Sensor 5 V:** its 2 A BEC comfortably powers the light 5 V loads — **ESP32 (0.25 A) + YDLIDAR X4 Pro (0.4 A) + BNO055** ≈ 0.7 A.

So the final power stack is **PDB (distribution + sensor 5 V) + one dedicated 5 V/≥5 A buck (Pi 5 only)** — see the diagram in §6. Keep the battery on **3S** (the PDB accepts up to 4S, but 4S = 14.8–16.8 V would over-volt the 12 V motors; and the drivers/PDB are happiest at 3S for this build).

---

*NarrowAisleBot Mini Prototype Architecture — IIT Bombay BSBE — Aritra Das (25D0074). Companion to `docs/Master_Reference.md`. Current estimates for motor current and Kff are marked — confirm against the PG36M555 datasheet and in-air calibration.*
