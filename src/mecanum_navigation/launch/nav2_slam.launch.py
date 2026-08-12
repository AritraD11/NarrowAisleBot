#!/usr/bin/env python3
"""
nav2_slam.launch.py — Nav2 autonomous navigation WHILE slam_toolbox is mapping.

This is the "drive autonomously in a space you haven't mapped yet" mode:
you send the robot a goal, Nav2 plans and drives to it, and slam_toolbox
keeps building the map from the scans collected on the way.

HOW THIS DIFFERS FROM navigation.launch.py
    navigation.launch.py runs nav2_bringup's bringup_launch.py with a
    `map:=` argument, which starts map_server + AMCL — the "navigate on a
    previously-saved, finished map" mode. AMCL and slam_toolbox BOTH
    publish map->odom, so running that file while mapping corrupts the
    pose estimate (nav2_params.yaml's own AMCL warning). This file starts
    the navigation half only: planner, controller, behaviors, BT navigator,
    costmaps. Localization comes from the already-running slam_toolbox.

PREREQUISITES — all three must already be up:
    1. aislebot.service          (odometry_publisher -> odom->base_link TF,
                                  teleop_asym -> consumes /cmd_vel)
    2. mapping_full.launch.py    (LiDAR + scan_relay + slam_toolbox ->
                                  /scan_reliable, /map, map->odom TF)
    3. This file.

    Order matters: Nav2's costmaps need /map and the TF tree to exist, or
    they sit inactive waiting for a transform that never arrives.

Usage:
    ros2 launch mecanum_navigation nav2_slam.launch.py

Then send a goal from Foxglove (or `ros2 action send_goal
/navigate_to_pose ...`) and the robot drives there on its own.

AXES: base_link on this robot is NOT REP-103 (+X=right, +Y=forward,
Research_Journal.md §17.10). Every x/y-labelled velocity and footprint
parameter lives in nav2_params.yaml and is already swapped to match —
see the AXES note at the top of that file before touching any of them.

cmd_vel CHAIN (nav2_bringup's own remapping, Jazzy):
    controller_server -> /cmd_vel_nav -> velocity_smoother -> /cmd_vel
/cmd_vel is what teleop_asym already consumes, so Nav2 slots into the
existing, validated drive path as just another publisher — the wheel
kinematics and the ESP32 bridge are untouched by any of this.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    nav_dir = get_package_share_directory('mecanum_navigation')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    default_params = os.path.join(nav_dir, 'config', 'nav2_params.yaml')

    args = [
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Nav2 parameters (footprint/velocity axes already '
                        'swapped for this robot — see the file header)',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='false on the real robot; true only under Gazebo',
        ),
        DeclareLaunchArgument(
            'autostart',
            default_value='true',
            description='Auto-transition the lifecycle nodes to active',
        ),
    ]

    # nav2_bringup's navigation_launch.py = planner, controller, smoother,
    # behaviors, bt_navigator, waypoint_follower, velocity_smoother, and
    # their lifecycle manager. Deliberately NOT bringup_launch.py, which
    # would also start map_server + AMCL (see the header).
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'params_file': LaunchConfiguration('params_file'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
        }.items(),
    )

    return LaunchDescription([*args, nav2])
