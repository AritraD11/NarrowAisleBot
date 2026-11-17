#!/bin/bash
# 03_lidar_driver.sh - the driver for lidar.model in robot_config.yaml.
source "$(dirname "$0")/common.sh"
load_env
step "3. LiDAR driver: $LIDAR_MODEL"
case "$LIDAR_MODEL" in
  ydlidar)
    if [ ! -d "$HOME/YDLidar-SDK" ]; then
        run git clone https://github.com/YDLIDAR/YDLidar-SDK.git "$HOME/YDLidar-SDK"
    fi
    mkdir -p "$HOME/YDLidar-SDK/build"
    ( cd "$HOME/YDLidar-SDK/build" && cmake .. >> "$LOG" 2>&1 && make -j"$(nproc)" >> "$LOG" 2>&1 \
      && sudo make install >> "$LOG" 2>&1 ) || die "YDLidar-SDK build failed (see $LOG)"
    ok "YDLidar-SDK built and installed"
    mkdir -p "$ROBOT_WS/src"
    if [ ! -d "$ROBOT_WS/src/ydlidar_ros2_driver" ]; then
        # The humble branch builds on Jazzy (NarrowAisleBot runs it).
        run git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git \
            "$ROBOT_WS/src/ydlidar_ros2_driver"
    fi
    ok "ydlidar_ros2_driver in $ROBOT_WS/src (built by 04_workspace.sh)"
    ;;
  rplidar)
    run sudo apt-get install -y ros-jazzy-rplidar-ros
    ok "rplidar_ros from apt"
    ;;
  none|custom)
    ok "nothing to install for '$LIDAR_MODEL'. For custom, put your driver in $ROBOT_WS/src."
    ;;
  *) die "unknown LIDAR_MODEL '$LIDAR_MODEL'" ;;
esac
