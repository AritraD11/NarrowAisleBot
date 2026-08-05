# MiniAisleBot — Wokwi kinematics simulation

A no-hardware way to see the **asymmetric mecanum inverse kinematics** run on a
real ESP32 core, at [wokwi.com](https://wokwi.com). It runs the exact same IK
equations as `firmware/narrowaislebot_mini_esp32.ino`.

## What it does

| On screen | Meaning |
|---|---|
| 3 slide potentiometers | `vx` (forward), `vy` (right strafe), `wz` (CCW yaw). **Centre = 0.** |
| 4 LEDs (FR / FL / RR / RL) | brightness ∝ `|wheel speed|`, driven by real `ledc` PWM |
| Serial Monitor @ 115200 | the 4 signed wheel speeds, each wheel's direction, and a forward-kinematics round-trip (`FK` should reconstruct your pot inputs) |

Because the two outer wheels use `K_outer = 0.225` and the two inner wheels use
`K_inner = 0.195`, a **pure yaw command spins the outer LEDs (FR, RL) brighter
than the inner LEDs (FL, RR)** — that asymmetry is the whole point of the robot,
made visible.

## How to run

1. Go to [wokwi.com](https://wokwi.com) → **New Project** → **ESP32**.
2. Replace `sketch.ino` with `mini_sim.ino` from this folder.
3. Open the `diagram.json` tab and paste this folder's `diagram.json`.
4. Press **▶**. Open the Serial Monitor. Drag the pots.

## Things to try

- **Pure forward:** only `vx` up → all four LEDs equal, all `fwd`.
- **Pure strafe right:** only `vy` up → `FR,RL` fwd / `FL,RR` rev (the mecanum "X").
- **Pure yaw:** only `wz` → outer LEDs brighter than inner — the asymmetry.
- Watch the `FK …` columns track your commands: that's the odometry equation the
  Pi will use to estimate motion from the wheels.

## What this does *not* simulate

Wokwi has no geared DC motor with a quadrature encoder, so this models the
**command math and pin logic**, not the closed PID loop or motor dynamics. For
the analog H-bridge / power side use [falstad.com/circuit](https://www.falstad.com/circuit/).
The real closed-loop PID lives in the firmware and is tuned on the bench.
