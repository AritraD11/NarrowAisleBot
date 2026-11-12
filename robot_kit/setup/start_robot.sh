#!/bin/bash
# start_robot.sh - what robot.service runs. Waits for the microcontroller,
# then starts base.launch.py. Output goes to ~/robot_boot.log.
KIT="$(cd "$(dirname "$0")/.." && pwd)"
exec >> "$HOME/robot_boot.log" 2>&1
echo; echo "==== robot start $(date)"
source "$KIT/setup/generated/robot.env"
source /opt/ros/jazzy/setup.bash
source "$ROBOT_WS/install/setup.bash"
export ROS_DOMAIN_ID="$ROBOT_DOMAIN_ID"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
# Loopback-only DDS: every node is on this Pi, and without a LAN cable
# CycloneDDS otherwise fails to pick an interface on a headless boot.
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo" priority="default" multicast="false"/></Interfaces></General></Domain></CycloneDDS>'
for i in $(seq 1 30); do
    [ -e "/dev/$MCU_DEVICE" ] && break
    echo "  waiting for /dev/$MCU_DEVICE ($i/30)"
    sleep 1
done
if [ ! -e "/dev/$MCU_DEVICE" ]; then
    echo "[ERROR] /dev/$MCU_DEVICE never appeared. Cable? udev rule? (setup/list_usb_serial.py)"
    exit 1        # systemd retries in 10 s
fi
echo "  /dev/$MCU_DEVICE present, launching"
exec ros2 launch robot_base base.launch.py
