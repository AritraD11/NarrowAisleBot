#!/bin/bash
# install_all.sh - a fresh Pi 5 (Ubuntu 24.04) to a working robot stack.
#
#   cd ~/robot_kit
#   nano robot_config.yaml          # your hardware, FIRST
#   python3 generate.py             # must print no CONFIG ERROR
#   ./setup/install_all.sh
#
# Runs steps 01 to 05, and 06 (Wi-Fi AP) last because it can drop your
# connection. Each step is safe to re-run. Full log: ~/robot_kit_install.log
set -e
D="$(cd "$(dirname "$0")" && pwd)"
python3 "$D/../generate.py" --check
"$D/01_base_system.sh"
"$D/02_ros_jazzy.sh"
"$D/03_lidar_driver.sh"
"$D/04_workspace.sh"
"$D/05_system.sh"
echo
echo "Steps 1-5 done. Log out and back in (serial permissions), then:"
echo "    rk-start        # or: sudo reboot, if autostart is on"
echo "    rk-check        # health check"
echo "Wi-Fi access point (optional, can disconnect you):  $D/06_wifi_ap.sh"
