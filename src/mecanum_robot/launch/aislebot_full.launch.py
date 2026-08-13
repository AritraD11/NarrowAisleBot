#!/usr/bin/env python3
"""
aislebot_full.launch.py — bring up the entire AisleBot stack.

Nodes started:
    joy_node               (USB gamepad → /joy)
    joy_to_aislebot        (/joy → /cmd_vel, /arm/cmd_vel, /arm/command)
    teleop_asym            (/cmd_vel → /wheel_speeds)
    esp32_bridge           (/wheel_speeds → ESP32 serial)   /dev/esp32 CP2102
    odom_pub               (encoder feedback → /odom)
    arm_bridge             (arm topics → Arduino Mega)      /dev/mega  CH340
    phone_dashboard        (HTTP + WebSocket → ROS2 publishers)
    lcd_display            (16x2 I2C LCD status at 0x27)
    foxglove_bridge        (websocket :8765 → live RViz-equivalent view,
                             Research_Journal.md §13.8/§17.5 — Foxglove Studio
                             on a laptop connects here; RViz-on-laptop can't,
                             since DDS multicast doesn't cross this network)

Usage:
    ros2 launch mecanum_robot aislebot_full.launch.py
    ros2 launch mecanum_robot aislebot_full.launch.py use_phone:=false
    ros2 launch mecanum_robot aislebot_full.launch.py use_joystick:=false
    ros2 launch mecanum_robot aislebot_full.launch.py use_foxglove:=false
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node


def generate_launch_description():

    urdf_path = os.path.join(
        get_package_share_directory('mecanum_robot'), 'urdf', 'aislebot.urdf')
    with open(urdf_path, 'r') as f:
        robot_description = f.read()

    args = [
        DeclareLaunchArgument('esp32_port',   default_value='/dev/esp32',
                              description='ESP32 drive controller (CP2102)'),
        DeclareLaunchArgument('esp32_baud',   default_value='921600'),
        DeclareLaunchArgument('arm_port',     default_value='/dev/mega',
                              description='Arduino Mega arm controller (CH340)'),
        DeclareLaunchArgument('arm_baud',     default_value='115200'),
        DeclareLaunchArgument('use_joystick', default_value='true',
                              description='Start joy_node + joy_to_aislebot'),
        DeclareLaunchArgument('use_phone',    default_value='true',
                              description='Start phone_dashboard HTTP/WS server'),
        DeclareLaunchArgument('http_port',    default_value='8080'),
        DeclareLaunchArgument('max_linear',   default_value='0.15'),
        DeclareLaunchArgument('max_angular',  default_value='0.30'),
        DeclareLaunchArgument('use_foxglove', default_value='true',
                              description='Start foxglove_bridge for live visualization'),
        DeclareLaunchArgument('foxglove_port', default_value='8765'),
    ]

    use_joy      = LaunchConfiguration('use_joystick')
    use_phone    = LaunchConfiguration('use_phone')
    use_foxglove = LaunchConfiguration('use_foxglove')

    banner = LogInfo(msg=[
        '\n══════════════════════════════════════════════════════════\n',
        '  AisleBot Full Stack\n',
        '  ESP32  (drive): ', LaunchConfiguration('esp32_port'),
        ' @ ', LaunchConfiguration('esp32_baud'), ' baud\n',
        '  Mega   (arm)  : ', LaunchConfiguration('arm_port'),
        ' @ ', LaunchConfiguration('arm_baud'), ' baud\n',
        '  Joystick : ', use_joy, '\n',
        '  Phone    : ', use_phone,
        ' (port ', LaunchConfiguration('http_port'), ')\n',
        '══════════════════════════════════════════════════════════\n',
    ])

    # ── INPUT ────────────────────────────────────────────────────
    joy_node = Node(
        package='joy', executable='joy_node', name='joy_node',
        parameters=[{'device_id': 0, 'deadzone': 0.05, 'autorepeat_rate': 25.0}],
        condition=IfCondition(use_joy),
        output='screen',
    )

    joy_translator = Node(
        package='mecanum_robot', executable='joy_to_aislebot',
        name='joy_to_aislebot',
        parameters=[{
            'max_linear':  LaunchConfiguration('max_linear'),
            'max_angular': LaunchConfiguration('max_angular'),
        }],
        condition=IfCondition(use_joy),
        output='screen',
    )

    phone = Node(
        package='mecanum_robot', executable='phone_dashboard',
        name='phone_dashboard',
        parameters=[{
            'http_port':   LaunchConfiguration('http_port'),
            'max_linear':  LaunchConfiguration('max_linear'),
            'max_angular': LaunchConfiguration('max_angular'),
        }],
        condition=IfCondition(use_phone),
        output='screen',
    )

    # ── DRIVE PIPELINE ───────────────────────────────────────────
    teleop = Node(
        package='mecanum_robot', executable='teleop_asym',
        name='teleop_asym',
        parameters=[{
            'wheel_radius': 0.0762,
            'l1':           0.403,
            'l2':           0.333,
            'd':            0.15769,
            'max_linear':   LaunchConfiguration('max_linear'),
            'max_angular':  LaunchConfiguration('max_angular'),
        }],
        output='screen',
    )

    esp32_bridge = Node(
        package='mecanum_robot', executable='esp32_bridge',
        name='esp32_bridge',
        parameters=[{
            'serial_port':       LaunchConfiguration('esp32_port'),
            'baud_rate':         921600,
            'max_wheel_speed':   5.20,
            # Without this, the ESP32 is never sent <L1>, so
            # /wheel_velocities_actual never gets a message and
            # odometry_publisher's odom->base_link TF (publish_tf
            # above) never fires — slam_toolbox then sits at
            # "Activating" forever with no error (docs/LiDAR_SLAM_Bringup.md).
            'telemetry_enabled': True,
        }],
        output='screen',
    )

    odom_pub = Node(
        package='mecanum_robot', executable='odom_pub',
        name='odometry_publisher',
        parameters=[{
            'wheel_radius': 0.0762,
            'l1':           0.403,
            'l2':           0.333,
            'd':            0.15769,
            'publish_tf':   True,
        }],
        output='screen',
    )

    # ── ARM PIPELINE ─────────────────────────────────────────────
    arm_bridge = Node(
        package='mecanum_robot', executable='arm_bridge',
        name='arm_bridge',
        parameters=[{
            'serial_port':                 LaunchConfiguration('arm_port'),
            'baud_rate':                   115200,
            'disable_joystick_on_connect': True,
            'auto_enable_on_connect':      True,
        }],
        output='screen',
    )

    # ── STATUS ───────────────────────────────────────────────────
    lcd = Node(
        package='mecanum_robot', executable='lcd_display',
        name='lcd_display',
        output='screen',
    )

    # ── VISUALIZATION ────────────────────────────────────────────
    # DDS multicast doesn't cross this network (Research_Journal.md §13.8),
    # so RViz running on a laptop can't discover this robot's topics
    # directly. foxglove_bridge exposes them over a plain TCP websocket
    # instead, which Foxglove Studio connects to from anywhere on the LAN.
    foxglove = Node(
        package='foxglove_bridge', executable='foxglove_bridge',
        name='foxglove_bridge',
        parameters=[{'port': LaunchConfiguration('foxglove_port')}],
        condition=IfCondition(use_foxglove),
        output='screen',
    )

    # ── ROBOT MODEL ──────────────────────────────────────────────
    # Publishes /robot_description and the URDF's fixed-joint TFs, so
    # Foxglove draws the actual 36 x 100 cm chassis, four wheels and LiDAR
    # instead of a bare set of axes — the robot is a body, not a point, and
    # the 6 cm cushion only means something against a body.
    #
    # This OWNS base_link -> laser_frame. The vendor ydlidar_launch.py used
    # to publish a competing hardcoded (0, 0, 0.02) placeholder for the same
    # transform; mapping_full.launch.py now starts the driver node directly
    # and leaves that publisher out, so there is exactly one source and it
    # carries the measured mount (§17.12).
    #
    # URDF is read at launch-time into a parameter rather than passed as a
    # path: robot_state_publisher wants the XML itself, and reading it here
    # fails loudly at launch if the file is missing rather than leaving the
    # node up with an empty description.
    robot_state_pub = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen',
    )

    return LaunchDescription([
        *args,
        banner,
        joy_node, joy_translator, phone,
        teleop, esp32_bridge, odom_pub,
        arm_bridge,
        lcd,
        foxglove,
        robot_state_pub,
    ])
