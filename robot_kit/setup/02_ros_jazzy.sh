#!/bin/bash
# 02_ros_jazzy.sh - ROS 2 Jazzy and every ROS package the kit uses.
#   ROS_PKG=desktop ./02_ros_jazzy.sh    for RViz on the Pi itself (bigger, slower)
source "$(dirname "$0")/common.sh"
ROS_PKG="${ROS_PKG:-ros-base}"

step "2. ROS 2 Jazzy ($ROS_PKG)"
if [ ! -f /etc/apt/sources.list.d/ros2.sources ] && [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
    run sudo add-apt-repository -y universe
    # The current official method: the ros2-apt-source package installs the
    # repository and its signing key, and keeps the key up to date.
    VER=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
          | grep -F '"tag_name"' | awk -F'"' '{print $4}')
    [ -n "$VER" ] || die "could not read the ros-apt-source version from GitHub"
    run curl -L -o /tmp/ros2-apt-source.deb \
        "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${VER}/ros2-apt-source_${VER}.noble_all.deb"
    run sudo dpkg -i /tmp/ros2-apt-source.deb
    ok "ROS 2 apt repository ($VER)"
fi
run sudo apt-get update
echo "  installing ros-jazzy-$ROS_PKG and add-ons: the slow part, 10 to 25 minutes"
run sudo apt-get install -y "ros-jazzy-$ROS_PKG" \
    ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
    ros-jazzy-twist-mux ros-jazzy-robot-state-publisher ros-jazzy-xacro \
    ros-jazzy-tf2-tools ros-jazzy-teleop-twist-keyboard ros-jazzy-foxglove-bridge \
    ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-robot-localization \
    python3-colcon-common-extensions python3-rosdep
ok "ROS 2 Jazzy and add-ons"
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    run sudo rosdep init
fi
run rosdep update
ok "rosdep"
