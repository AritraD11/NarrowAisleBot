# robot_kit

Everything NarrowAisleBot runs on its Raspberry Pi, rebuilt so it fits a different robot. Motors, encoders, microcontroller, motor driver, LiDAR and drive type (differential, skid steer, mecanum, omni) are things you describe in one file, `robot_config.yaml`, not things baked into the code.

The manual is `manual/Robot_Setup_Manual.pdf`. Read chapter 1 first; it says what has been tested and what hasn't.

## Fresh Raspberry Pi 5, Ubuntu 24.04

```bash
cd ~/robot_kit
nano robot_config.yaml          # your hardware (manual chapter 3)
python3 generate.py --check     # must print no CONFIG ERROR
./setup/install_all.sh          # 30 to 45 minutes; log in ~/robot_kit_install.log
```

Log out and back in, flash `firmware/robot_mcu` (manual chapter 7), then:

```bash
rk-start        # base stack: bridge, kinematics, odometry, twist_mux, dashboard
rk-check        # live health check
```

and open `http://<pi-address>:8080` on a phone.

## Calibrate the motor controllers

```bash
rk-stop
./tools/encoder_logger.py --test plant        # wheels in the air
./tools/encoder_logger.py --test staircase
./tools/encoder_logger.py --test steps
```

No hardware yet? `make -C tools/firmware_sim && tools/firmware_sim/sim --pty` runs the real firmware against simulated motors on a pseudo-terminal, and the logger works against it unchanged (manual 9.2).

## Layout

| Path | |
|---|---|
| `robot_config.yaml` | the one file you edit |
| `generate.py` | writes the URDF, ROS params, Nav2 and SLAM configs, udev rule, firmware header |
| `examples/` | a 4WD skid steer on an Arduino Mega; NarrowAisleBot itself |
| `setup/` | install scripts, USB device lister, health check, the systemd start script |
| `firmware/robot_mcu/` | the microcontroller sketch (ESP32, AVR, RP2040, Teensy) |
| `ros2/robot_base/` | ROS 2 package: mcu_bridge, base_controller, wheel_odometry, scan_filter, telemetry_logger, dashboard, launch files |
| `tools/` | encoder logger, log analyser, firmware simulator |
| `tests/` | `./run_tests.sh` runs all of them |
| `manual/` | the manual source (`manual.md`), its figures, and `build_manual.py` (needs pandoc and Node playwright) |

Axes are REP-103 everywhere: +x forward, +y left. Manual section 2.3 explains why that is not negotiable.
