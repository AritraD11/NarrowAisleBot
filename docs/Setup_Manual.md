> Converted from `AisleBot_Setup_Manual.docx`. Original preserved at `docs/originals/AisleBot_Setup_Manual.docx`. Much of the fresh-Pi setup procedure this describes is now automated by `install.sh` at the repo root — treat this as narrative/historical reference, and `install.sh` + the root `README.md` as the authoritative current procedure.

**AisleBot**

Complete Setup & Deployment Manual

*Asymmetric Mecanum Omnidirectional Robot for Narrow-Aisle Warehouse Navigation*

**Aritra Das \| Roll No. 25D0074**

Department of Biosciences and Bioengineering

Indian Institute of Technology Bombay

Supervisor: Prof. Ambarish Kunwar

**GitHub Repository**

https://github.com/AritraD11/Aislebot

**1. Fresh Pi — One-Click Install**

On a brand-new Raspberry Pi 5 with Ubuntu 24.04 LTS installed, open a terminal and run this single command:

|                                                                                         |
|-----------------------------------------------------------------------------------------|
| **ONE-CLICK INSTALL COMMAND**                                                           |
| bash \<(curl -sSL https://raw.githubusercontent.com/AritraD11/Aislebot/main/install.sh) |

This command downloads and runs the install script directly from GitHub. It will:

- Install ROS2 Jazzy Desktop (~15 min)

- Install Nav2, SLAM Toolbox, robot_localization, RPLiDAR, joy, rviz2

- Install Python packages: fastapi, uvicorn, pyserial, RPLCD, pandas, numpy, openpyxl

- Clone the AisleBot GitHub repository

- Build the ROS2 workspace with colcon

- Install udev rules (/dev/esp32 and /dev/mega)

- Install and configure the systemd autostart service

- Set up .bashrc with ROS2 environment and aliases

|                                                                                                                        |
|------------------------------------------------------------------------------------------------------------------------|
| **⚠ NOTE:** Total time: approximately 20-30 minutes on a fresh Pi 5. Keep the Pi connected to the internet throughout. |

**2. Prerequisites**

**2.1 Hardware Required**

| **Component**          | **Detail**                                        |
|------------------------|---------------------------------------------------|
| **Raspberry Pi 5**     | 4GB or 8GB RAM recommended                        |
| **MicroSD Card**       | 32GB minimum, 64GB recommended (Class 10 / A2)    |
| **Power Supply**       | USB-C 5V 5A (official Pi 5 supply recommended)    |
| **Internet**           | Required during install — college WiFi or hotspot |
| **Monitor + Keyboard** | Only needed for initial Ubuntu setup and install  |

**2.2 Software Prerequisites**

Before running the install command, the Pi must have:

1.  Ubuntu 24.04 LTS (Noble) installed on the SD card

2.  Internet connection active

3.  A user account (default username: aritra)

|                                                                                                    |
|----------------------------------------------------------------------------------------------------|
| **⚠ NOTE:** Do NOT install ROS2 manually before running the script. The script handles everything. |

**2.3 Ubuntu 24.04 Flash Instructions**

On your Windows laptop:

4.  Download Raspberry Pi Imager from raspberrypi.com/software

5.  Insert SD card into laptop

6.  Open Imager → Choose OS → Other general-purpose OS → Ubuntu → Ubuntu 24.04 LTS (64-bit)

7.  Choose Storage → your SD card

8.  Click the gear icon → set hostname: aritra-desktop, username: aritra, enable SSH

9.  Write → insert SD into Pi → boot

**3. What the Install Script Does (Step by Step)**

The script runs 7 steps with progress output. Here is what each step does:

**Step 1 — System update & base tools**

Updates apt, installs git, curl, python3-pip, build-essential, i2c-tools, zip.

**Step 2 — ROS2 Jazzy (~15 minutes)**

Adds the ROS2 apt repository, installs ros-jazzy-desktop, colcon, and all required add-on packages including Nav2, SLAM Toolbox, joy, RPLiDAR, CycloneDDS, and rviz2.

**Step 3 — Python packages**

Installs exact versions matching the working Pi:

- fastapi 0.136.1 — phone dashboard web server

- uvicorn 0.46.0 — ASGI server for FastAPI

- pyserial 3.5 — serial communication with ESP32 and Mega

- RPLCD 1.4.0 — 16x2 I2C LCD display driver

- pandas 3.0.0 — telemetry data analysis

- numpy + openpyxl — data processing and Excel export

**Step 4 — Clone AisleBot repo**

Clones https://github.com/AritraD11/Aislebot into /tmp, then copies the src/ packages into ~/ros2_ws/src/.

**Step 5 — Build ROS2 workspace**

Runs colcon build --symlink-install in ~/ros2_ws. All 9 nodes are compiled and installed.

**Step 6 — System configuration**

- Installs /etc/udev/rules.d/99-aislebot.rules — gives ESP32 and Mega persistent device names

- Installs ~/start_aislebot.sh — the launch script called by systemd

- Installs /etc/systemd/system/aislebot.service — autostart on boot (optional)

- Adds user to dialout group (serial port access)

- Adds user to i2c group (LCD access)

**Step 7 — Shell environment**

Adds to ~/.bashrc:

- source /opt/ros/jazzy/setup.bash

- source ~/ros2_ws/install/setup.bash

- export ROS_DOMAIN_ID=42

- export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

- CycloneDDS loopback URI (required for headless Pi with no LAN)

- Aliases: ab, ab-build, ab-log, ab-status, ab-start, ab-stop, ab-ports

**4. After Install — First Boot Steps**

**4.1 Plug in hardware (order matters)**

|                                                                                                                                                                                                                  |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **⚠ NOTE:** Always plug ESP32 (CP2102) FIRST, then Arduino Mega (CH340). The udev rules assign /dev/esp32 and /dev/mega based on USB vendor IDs, so order does not strictly matter — but this is the safe habit. |

Verify devices are detected:

> ls /dev/esp32 /dev/mega
>
> \# Expected output:
>
> \# /dev/esp32 /dev/mega

**4.2 Flash firmware (from Windows laptop)**

| **Component**      | **Detail**                                            |
|--------------------|-------------------------------------------------------|
| **ESP32 firmware** | aislebot_esp32_v2.ino → ESP32-WROOM-32 @ 921600 baud  |
| **Arm firmware**   | aislebot_arm_v7.ino → Arduino Mega 2560 @ 115200 baud |
| **Arduino IDE**    | Tools → Board → ESP32 Dev Module (CPU: 240 MHz)       |
| **Partition**      | Default 4MB with spiffs                               |

**4.3 Open a new terminal**

After install, open a new terminal (or run source ~/.bashrc) so the ROS2 environment is loaded.

**4.4 Launch the robot**

> ab
>
> \# Same as:
>
> \# ros2 launch mecanum_robot aislebot_full.launch.py

Expected startup sequence:

10. ESP32 bridge connects on /dev/esp32

11. Arduino arm bridge connects on /dev/mega — responds PONG, enables arm

12. LCD shows AISLEBOT READY + IP address

13. Phone dashboard ready at http://\<PI_IP\>:8080

14. Xbox controller detected (if plugged in)

**4.5 Open phone dashboard**

On your phone, connect to the same WiFi network as the Pi, then open:

> http://10.53.6.122:8080
>
> \# Find your Pi's IP with:
>
> hostname -I

**5. Hardware Reference**

**5.1 Full hardware stack**

| **Component**        | **Detail**                                                |
|----------------------|-----------------------------------------------------------|
| **Compute**          | Raspberry Pi 5, Ubuntu 24.04.4 LTS, ROS2 Jazzy            |
| **Drive controller** | ESP32-WROOM-32 38-pin CP2102 → /dev/esp32 @ 921600 baud   |
| **Arm controller**   | Arduino Mega 2560 CH340 → /dev/mega @ 115200 baud         |
| **Motors**           | Rhino RMCS-2086 (24V, 60 RPM, 1:47 gear, 93132 CPR)       |
| **Motor drivers**    | 2× Cytron MDD20A                                          |
| **Wheels**           | DekuPro 6-inch SR Mecanum (radius = 0.0762 m)             |
| **Power**            | SM12830SL LiFePO4 battery + SSR-50DD solid state relay    |
| **UV arm**           | 2× NEMA23 (TB6600) + NEMA34 linear actuator (BH-MSD-6A-W) |
| **LCD**              | 16×2 I2C (PCF8574 at 0x27, SDA/SCL)                       |
| **LiDAR**            | RPLiDAR A1 (planned)                                      |
| **IMU**              | BNO055 (planned)                                          |
| **Level shifter**    | 2× TXS0108E (5V→3.3V for encoder signals)                 |

**5.2 Robot geometry (asymmetric)**

| **Component**                 | **Detail**                                |
|-------------------------------|-------------------------------------------|
| **Outer wheel pair (FR, RL)** | l1 = 0.403 m from centre                  |
| **Inner wheel pair (FL, RR)** | l2 = 0.333 m from centre                  |
| **Half-track width**          | d = 0.15769 m                             |
| **K_outer = l1 + d**          | 0.5607 m (used in IK for FR and RL)       |
| **K_inner = l2 + d**          | 0.4907 m (used in IK for FL and RR)       |
| **Wheel radius**              | 0.0762 m (DekuPro 6-inch: 152.4mm OD / 2) |

|                                                                                                                                                                                                    |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **⚠ NOTE:** K_outer and K_inner MUST be identical in: ESP32 firmware, mecanum_teleop_asymmetric.py, odometry_publisher.py, and nav2_params.yaml. Any mismatch causes drift and incorrect odometry. |

**6. ROS2 Node Architecture**

**6.1 All 8 nodes**

| **Component**       | **Detail**                                                                         |
|---------------------|------------------------------------------------------------------------------------|
| **esp32_bridge**    | Serial ↔ ROS2 bridge for ESP32. Sends wheel velocity commands, receives telemetry. |
| **teleop_asym**     | Converts /cmd_vel Twist → /wheel_speeds using asymmetric mecanum IK.               |
| **odom_pub**        | Reads encoder feedback → publishes /odom (odometry/filtered).                      |
| **arm_bridge**      | Serial ↔ ROS2 bridge for Arduino Mega arm controller.                              |
| **joy_to_aislebot** | Converts /joy (Xbox) → /cmd_vel and /arm/command.                                  |
| **phone_dashboard** | FastAPI + WebSocket HTTP server on port 8080. Phone control interface.             |
| **lcd_display**     | Writes status to 16×2 I2C LCD at address 0x27.                                     |
| **joy_node**        | ROS2 joy package — reads USB Xbox controller → /joy topic.                         |

**6.2 Topic map**

| **Component**        | **Detail**                                                             |
|----------------------|------------------------------------------------------------------------|
| **/joy**             | sensor_msgs/Joy — Xbox controller raw input                            |
| **/cmd_vel**         | geometry_msgs/Twist — drive commands (vx, vy, wz)                      |
| **/wheel_speeds**    | std_msgs/Float64MultiArray — \[FR, FL, RR, RL\] rad/s                  |
| **/arm/command**     | std_msgs/String — arm commands (LIFT, LOWER, OPEN, CLOSE, ESTOP)       |
| **/odom**            | nav_msgs/Odometry — wheel encoder odometry                             |
| **/motor_telemetry** | std_msgs/Float64MultiArray — \[FR_t, FR_a, FR_pwm, FL_t...\] 12 values |
| **/esp32/command**   | std_msgs/String — raw commands to ESP32 (\<L1\>, \<S\>, \<E1\>, etc.)  |

**6.3 Useful aliases (added to .bashrc by install script)**

| **Component** | **Detail**                                         |
|---------------|----------------------------------------------------|
| **ab**        | ros2 launch mecanum_robot aislebot_full.launch.py  |
| **ab-build**  | colcon build --symlink-install in ~/ros2_ws        |
| **ab-log**    | tail -f ~/aislebot_boot.log                        |
| **ab-status** | sudo systemctl status aislebot                     |
| **ab-start**  | sudo systemctl start aislebot                      |
| **ab-stop**   | sudo systemctl stop aislebot                       |
| **ab-ports**  | ls /dev/esp32 /dev/mega (check hardware connected) |

**7. Keeping the GitHub Repo Up to Date**

After any code change on the Pi, sync it to GitHub so the install script always restores the latest version:

> cd ~/aislebot
>
> \# Copy changed files from workspace to repo folder
>
> cp ~/ros2_ws/src/mecanum_robot/mecanum_robot/\*.py src/mecanum_robot/mecanum_robot/
>
> cp ~/ros2_ws/src/mecanum_robot/launch/\*.py src/mecanum_robot/launch/
>
> \# Commit and push
>
> git add -A
>
> git commit -m "update: describe what changed"
>
> git push

|                                                                                                                                                     |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **⚠ NOTE:** If you also changed system files (start_aislebot.sh, aislebot.service, udev rules), copy those to ~/aislebot/system/ before committing. |

**8. Troubleshooting**

**8.1 Service fails at boot**

Check the boot log:

> cat ~/aislebot_boot.log

Common cause: ESP32 not plugged in. The service waits 30 seconds for /dev/esp32 then exits. Plug in ESP32 and run:

> sudo systemctl start aislebot

**8.2 /dev/esp32 or /dev/mega not found**

> lsusb \# check USB devices are detected
>
> ls /dev/ttyUSB\* \# fallback device names
>
> sudo udevadm control --reload-rules && sudo udevadm trigger

**8.3 LCD errors (Remote I/O error)**

LCD is physically disconnected from the robot. The node logs warnings but continues running — this is not a fatal error.

**8.4 Phone dashboard not loading**

> \# Check dashboard is running
>
> ros2 node list \| grep phone
>
> \# Get Pi IP
>
> hostname -I
>
> \# Make sure phone is on same WiFi as Pi

**8.5 colcon build fails**

> cd ~/ros2_ws
>
> source /opt/ros/jazzy/setup.bash
>
> colcon build --symlink-install 2\>&1 \| grep -i error

**8.6 CycloneDDS warning in logs**

The warning 'NetworkInterfaceAddress: deprecated element' is harmless. It appears in all nodes but does not affect functionality. The loopback config works correctly.

**9. PID Tuning Reference**

**9.1 Current PID gains (ESP32 firmware)**

| **Component**      | **Detail**                    |
|--------------------|-------------------------------|
| **Kp**             | 50.0 — proportional gain      |
| **Ki**             | 30.0 — integral gain          |
| **Kd**             | 3.0 — derivative gain         |
| **Loop rate**      | 50 Hz (every 20 ms) on Core 1 |
| **Feedforward FR** | 42.1 PWM per (rad/s)          |
| **Feedforward FL** | 40.2 PWM per (rad/s)          |
| **Feedforward RR** | 43.7 PWM per (rad/s)          |
| **Feedforward RL** | 47.9 PWM per (rad/s)          |

**9.2 Live gain tuning via serial**

Connect ESP32 to laptop via USB (921600 baud), open Serial Monitor:

> \<G,50,30,3\> \# set Kp=50 Ki=30 Kd=3
>
> \<F,42.1,40.2,43.7,47.9\> \# set feedforward gains
>
> \<L1\> \# enable telemetry CSV output
>
> \<L0\> \# disable telemetry
>
> \<V,2.0,2.0,2.0,2.0\> \# spin all wheels at 2 rad/s
>
> \<S\> \# E-STOP (latches)
>
> \<E1\> \# clear E-STOP and re-enable
>
> \<?\> \# live state of all motors

**9.3 Telemetry CSV format**

When \<L1\> is active, ESP32 outputs CSV at 10 Hz:

> timestamp_ms, FR_target, FR_actual, FR_pwm, FL_target, FL_actual, FL_pwm, RR_target, RR_actual, RR_pwm, RL_target, RL_actual, RL_pwm

The Pi's phone_dashboard saves this to ~/aislebot_logs/run_YYYYMMDD_HHMMSS.csv when Record Run is pressed.

**9.4 Known motor performance (air test baseline)**

| **Component**          | **Detail**                                              |
|------------------------|---------------------------------------------------------|
| **FL (Front Left)**    | 2.983 rad/s, CV 0.33% — fastest, most consistent        |
| **FR (Front Right)**   | 2.853 rad/s — solid                                     |
| **RR (Rear Right)**    | 2.743 rad/s — slightly weaker                           |
| **RL (Rear Left)**     | 2.507 rad/s, CV 4.57% — slowest, most erratic           |
| **FR↔RL diagonal gap** | 11-13% — primary source of stutter. PID addresses this. |

**10. Quick Reference Card**

|                                                                                         |
|-----------------------------------------------------------------------------------------|
| **FRESH PI RESTORE — ONE COMMAND**                                                      |
| bash \<(curl -sSL https://raw.githubusercontent.com/AritraD11/Aislebot/main/install.sh) |

|                                                          |
|----------------------------------------------------------|
| **DAILY LAUNCH**                                         |
| ab                                                       |
| \# or: ros2 launch mecanum_robot aislebot_full.launch.py |

|                                      |
|--------------------------------------|
| **CHECK HARDWARE**                   |
| ab-ports \# /dev/esp32 and /dev/mega |
| ab-log \# live boot log              |
| ab-status \# systemd service status  |

|                                                                                     |
|-------------------------------------------------------------------------------------|
| **UPDATE GITHUB AFTER CODE CHANGE**                                                 |
| cd ~/aislebot                                                                       |
| cp ~/ros2_ws/src/mecanum_robot/mecanum_robot/\*.py src/mecanum_robot/mecanum_robot/ |
| git add -A && git commit -m 'update' && git push                                    |

|                                       |
|---------------------------------------|
| **GITHUB REPO**                       |
| https://github.com/AritraD11/Aislebot |

*AisleBot — IIT Bombay — Aritra Das (25D0074)*
