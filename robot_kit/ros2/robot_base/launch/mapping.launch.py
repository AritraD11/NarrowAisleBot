#!/usr/bin/env python3
"""
mapping.launch.py - LiDAR + scan_filter + slam_toolbox (online async).

    ros2 launch robot_base mapping.launch.py

Needs base.launch.py already running: slam_toolbox takes the robot's motion
from TF odom -> base_link, which wheel_odometry publishes only while
telemetry flows. Without it slam_toolbox sits at "Activating" and prints
nothing at all (NarrowAisleBot lost an afternoon to that silence). Check:
    ros2 run tf2_ros tf2_echo odom base_link

The params file path is absolute on purpose. A "~" in slam_params_file
fails silently and slam_toolbox runs on its defaults.

Start mapping BEFORE Nav2, never after: Nav2's global costmap rejects the
missing /map once a second until one arrives.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    share = get_package_share_directory("robot_base")
    slam_share = get_package_share_directory("slam_toolbox")
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(share, "launch", "lidar.launch.py"))),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(slam_share, "launch", "online_async_launch.py")),
            launch_arguments={"slam_params_file": os.path.join(share, "config", "slam_toolbox.yaml"),
                              "use_sim_time": "false"}.items()),
    ])
