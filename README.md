# NarrowAisleBot

Asymmetric Mecanum Omnidirectional Robot for Narrow-Aisle Warehouse Navigation
**Aritra Das (25D0074) | IIT Bombay, Dept. of Biosciences & Bioengineering | Prof. Ambarish Kunwar**

A Raspberry Pi 5 / ROS 2 Jazzy robot whose defining feature is a non-collinear, **asymmetric** mecanum wheelbase — the outer wheels (FR, RL) sit farther from centre than the inner wheels (FL, RR), roughly halving chassis width so it fits aisles a conventional mecanum platform can't. Real-time motor control runs on an ESP32 (hardware-PCNT PID at 50 Hz); planning, teleop, and SLAM run on the Pi.

---

## Project status (see `docs/Research_Journal.md` for the full narrative)

| Phase | Status |
|---|---|
| 1 — Closed-loop PID motor control | Done — air-test validated, ground recalibration in progress |
| 2 — Odometry + IMU state estimation | Not started (IMU not yet procured) |
| 3 — LiDAR SLAM | In progress — YDLIDAR X4 Pro live, manual bringup produces a first occupancy grid (see `docs/LiDAR_SLAM_Bringup.md`) |
| 4 — Nav2 autonomous path planning | Not started — blocked on Phase 2 (needs real odometry) |
| 5 — Warehouse/food-cart intelligence | Not started |

---

## Fresh Pi — one command

```bash
bash <(curl -sSL https://raw.githubusercontent.com/AritraD11/NarrowAisleBot/main/install.sh)
```

Installs ROS2 Jazzy, Nav2, SLAM, the YDLIDAR SDK + ROS2 driver, all Python packages, builds the workspace, and configures udev, systemd, and `.bashrc`. Takes ~25–30 minutes on a fresh Pi 5.

> **Repo is private.** `raw.githubusercontent.com` can't serve private-repo content anonymously, so this one-liner (and any plain `git clone`) only works while the repo is temporarily switched to public. Workflow: [make it public](https://github.com/AritraD11/NarrowAisleBot/settings) → run the install → set it back to private. There's no token embedded in the command above on purpose — don't paste a Personal Access Token into a URL you might screenshot or paste into chat.

---

## Documentation

The full write-up lives in [`docs/`](docs/) — start at [`docs/README.md`](docs/README.md) for an index. Highlights:

- [`docs/Research_Journal.md`](docs/Research_Journal.md) — the living project journal. **Keep this updated as the project progresses; it's the primary record.**
- [`docs/Master_Reference.md`](docs/Master_Reference.md) — hardware/wiring/firmware deep reference.
- [`docs/LiDAR_SLAM_Bringup.md`](docs/LiDAR_SLAM_Bringup.md) — YDLIDAR X4 Pro + slam_toolbox bringup.
- [`docs/Network_SelfHosted_AP.md`](docs/Network_SelfHosted_AP.md) — the Pi's self-hosted WiFi AP setup.
- [`docs/originals/`](docs/originals/) — the source-of-record `.docx`/`.pdf` files the Markdown above was converted from.
- [`docs/tools/`](docs/tools/) — standalone interactive HTML tools (telemetry analyzer, mecanum physics guide) — download and double-click to open, no server needed.

---

## Repo structure

```
aislebot/
│
├── install.sh                          ← one-click installer
├── README.md
├── aislebot_esp32.ino                  ← ESP32 drive firmware
├── aislebot_arm.ino                    ← Mega arm + UV-lighting firmware
├── aislebot_pid_analysis_v2.py         ← offline PID telemetry analysis
│
├── docs/                               ← full documentation (see docs/README.md)
│   ├── Research_Journal.md
│   ├── Master_Reference.md
│   ├── LiDAR_SLAM_Bringup.md
│   ├── Network_SelfHosted_AP.md
│   ├── Setup_Manual.md
│   └── originals/                      ← source .docx / .pdf files
│
├── system/                             ← system config, mirrors what's live on the Pi
│   ├── 99-aislebot.rules               ← /etc/udev/rules.d/  — port-pinned esp32/ydlidar/mega
│   ├── aislebot.service                ← /etc/systemd/system/
│   ├── start_aislebot.sh               ← ~/start_aislebot.sh
│   ├── ydlidar_params.yaml             ← confirmed YDLIDAR X4 Pro driver params
│   └── slam_nodom.yaml                 ← ~/ros2_ws/slam_nodom.yaml — the SLAM config actually in use
│
└── src/                                ← ROS2 workspace src/, as run on the Pi
    ├── scan_relay/
    │   └── scan_relay.py               ← plain script, no build — best-effort/scan → reliable/scan_reliable
    │
    ├── mecanum_robot/
    │   ├── package.xml
    │   ├── setup.py
    │   ├── mecanum_robot/
    │   │   ├── esp32_bridge.py
    │   │   ├── arm_bridge.py
    │   │   ├── phone_dashboard.py
    │   │   ├── mecanum_teleop_asymmetric.py
    │   │   ├── odometry_publisher.py
    │   │   ├── lcd_display.py
    │   │   ├── joy_to_aislebot.py
    │   │   ├── keyboard_teleop.py
    │   │   └── gazebo_bridge.py
    │   ├── urdf/aislebot.urdf
    │   ├── worlds/warehouse.world
    │   └── launch/
    │       ├── aislebot_full.launch.py ← primary launch file
    │       └── simulation.launch.py
    │
    └── mecanum_navigation/
        ├── package.xml
        ├── setup.py
        ├── launch/
        │   ├── slam.launch.py
        │   └── navigation.launch.py
        └── config/
            ├── ekf_params.yaml
            ├── nav2_params.yaml        ← Phase 4, forward-looking
            └── slam_params.yaml        ← Phase 4/EKF-fusion config; current bringup instead uses
                                           slam_nodom.yaml, which lives on the Pi (not yet vendored here)
```

The `ydlidar_ros2_driver` package itself is **not** vendored in this repo — `install.sh` clones it fresh from the public YDLIDAR org repo (branch `humble`) alongside the YDLidar-SDK, since it's a third-party dependency, not project code.

---

## Keeping this repo in sync

This repo is meant to be a complete, disaster-proof mirror of the project — code, firmware, docs, and hardware notes. When you change something on the Pi:

```bash
cd ~/aislebot   # your clone of this repo
cp ~/ros2_ws/src/mecanum_robot/mecanum_robot/*.py src/mecanum_robot/mecanum_robot/
cp ~/ros2_ws/src/mecanum_robot/launch/*.py        src/mecanum_robot/launch/
cp ~/ros2_ws/src/scan_relay/scan_relay.py         src/scan_relay/scan_relay.py
git add -A
git commit -m "update: <what you changed>"
git push
```

And whenever you make a real design decision, fix a bug, or hit a milestone — append it to `docs/Research_Journal.md`. That document is only as useful as it is current.

---

## Hardware

| Component | Detail |
|---|---|
| Compute | Raspberry Pi 5, Ubuntu 24.04 LTS, ROS2 Jazzy |
| Drive controller | ESP32-WROOM-32 → `/dev/esp32` @ 921600 baud |
| Arm controller | Arduino Mega 2560 → `/dev/mega` @ 115200 baud |
| LiDAR | YDLIDAR X4 Pro → `/dev/ydlidar` @ 128000 baud (single-channel, ~1258 pts/scan @ ~11.5 Hz) |
| Motors | Rhino RMCS-2086 (24V, 60 RPM, 1:47, 93132 CPR) |
| Drivers | 2× Cytron MDD20A |
| Wheels | DekuPro 6-inch SR Mecanum (radius 0.0762 m) |
| Geometry | K_outer = 0.5607 m (FR, RL) · K_inner = 0.4907 m (FL, RR) |
| Arm | 2× NEMA23 (TB6600) + NEMA34 linear (BH-MSD-6A-W) + 3-tube staged UV lighting (v8 firmware) |
| Sensors | YDLIDAR X4 Pro (live) · BNO055 IMU (planned, Phase 2) · 16×2 I2C LCD |

Full pin-level detail: `docs/Master_Reference.md`. LiDAR-specific hardware notes (USB port pinning, cabling): `docs/LiDAR_SLAM_Bringup.md`.

## Firmware

Committed at the repo root (not stored separately):

| File | Target | Baud |
|---|---|---|
| `aislebot_esp32.ino` | ESP32-WROOM-32 | 921600 |
| `aislebot_arm.ino` | Arduino Mega 2560 (arm + UV lighting, v8) | 115200 |

---

## License

Released under the [MIT License](LICENSE) © 2026 Aritra Das.

## Acknowledgements

Developed at the Indian Institute of Technology Bombay, Department of Biosciences and Bioengineering, under the supervision of Prof. Ambarish Kunwar. The asymmetric wheelbase kinematics build on *An Omnidirectional Asymmetric Mobile Robot for Narrow-Aisle Spaces* (see `docs/Research_Journal.md`, Appendix A, for the full reference list).
