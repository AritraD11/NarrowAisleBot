#!/usr/bin/env python3
"""
base.launch.py - everything that runs whenever the robot is on.

    ros2 launch robot_base base.launch.py
    ros2 launch robot_base base.launch.py use_dashboard:=false use_foxglove:=true

Starts:
    robot_state_publisher   URDF -> /robot_description and the fixed TFs
                            (base_link -> laser_frame, wheels, chassis)
    mcu_bridge              /wheel_cmd -> serial; serial -> /wheel_states
    base_controller         /cmd_vel -> /wheel_cmd
    wheel_odometry          /wheel_states -> /odom, TF odom -> base_link
    twist_mux               /cmd_vel_manual (priority 100) and
                            /cmd_vel_nav_out (priority 10) -> /cmd_vel
    dashboard               phone UI on http://<pi>:8080        (use_dashboard)
    foxglove_bridge         ws://<pi>:8765 for Foxglove Studio   (use_foxglove)

The LiDAR, SLAM and Nav2 are NOT started here. They start on demand
(lidar.launch.py, mapping.launch.py, nav2.launch.py), usually from the
dashboard, so that restarting a map never restarts the motor stack.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("robot_base")
    params = os.path.join(share, "config", "robot.yaml")
    with open(os.path.join(share, "urdf", "robot.urdf")) as fh:
        urdf = fh.read()

    args = [
        DeclareLaunchArgument("params_file", default_value=params),
        DeclareLaunchArgument("use_dashboard", default_value="true"),
        DeclareLaunchArgument("use_foxglove", default_value="false"),
        DeclareLaunchArgument("foxglove_port", default_value="8765"),
    ]
    p = LaunchConfiguration("params_file")

    return LaunchDescription(args + [
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": urdf}], output="screen"),
        Node(package="robot_base", executable="mcu_bridge", name="mcu_bridge",
             parameters=[p], output="screen"),
        Node(package="robot_base", executable="base_controller", name="base_controller",
             parameters=[p], output="screen"),
        Node(package="robot_base", executable="wheel_odometry", name="wheel_odometry",
             parameters=[p], output="screen"),
        Node(package="twist_mux", executable="twist_mux", name="twist_mux",
             parameters=[os.path.join(share, "config", "twist_mux.yaml")],
             remappings=[("cmd_vel_out", "cmd_vel")], output="screen"),
        Node(package="robot_base", executable="dashboard", name="dashboard",
             parameters=[p], output="screen",
             condition=IfCondition(LaunchConfiguration("use_dashboard"))),
        Node(package="foxglove_bridge", executable="foxglove_bridge", name="foxglove_bridge",
             parameters=[{"port": LaunchConfiguration("foxglove_port")}], output="screen",
             condition=IfCondition(LaunchConfiguration("use_foxglove"))),
    ])
