#!/usr/bin/env python3
"""
aislebot_full.launch.py — bring up the entire AisleBot stack.

Nodes started:
    joy_node               (USB gamepad → /joy)
    joy_to_aislebot        (/joy → /cmd_vel, /arm/cmd_vel, /arm/command)
    teleop_asym            (/cmd_vel → /wheel_speeds)              [from existing pkg]
    esp32_bridge           (/wheel_speeds → ESP32 serial)          [from existing pkg]
    arm_bridge             (arm topics → Arduino Mega serial)
    phone_dashboard        (HTTP + WebSocket → ROS2 publishers)

Usage:
    ros2 launch mecanum_robot aislebot_full.launch.py
    ros2 launch mecanum_robot aislebot_full.launch.py use_phone:=false
    ros2 launch mecanum_robot aislebot_full.launch.py \\
        esp32_port:=/dev/ttyUSB0  arm_port:=/dev/ttyACM0

Find your ports first:
    ls -l /dev/serial/by-id/
    udevadm info /dev/ttyUSB0 | grep MODEL
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node


def generate_launch_description():

    args = [
        DeclareLaunchArgument('esp32_port',  default_value='/dev/ttyUSB0',
                              description='Serial port for ESP32 drive controller'),
        DeclareLaunchArgument('esp32_baud',  default_value='921600'),
        DeclareLaunchArgument('arm_port',    default_value='/dev/ttyACM0',
                              description='Serial port for Arduino Mega arm controller'),
        DeclareLaunchArgument('arm_baud',    default_value='115200'),
        DeclareLaunchArgument('use_joystick', default_value='true',
                              description='Start joy_node + joy_to_aislebot'),
        DeclareLaunchArgument('use_phone',    default_value='true',
                              description='Start phone_dashboard HTTP/WS server'),
        DeclareLaunchArgument('http_port',    default_value='8080'),
        DeclareLaunchArgument('max_linear',   default_value='0.15'),
        DeclareLaunchArgument('max_angular',  default_value='0.30'),
    ]

    use_joy   = LaunchConfiguration('use_joystick')
    use_phone = LaunchConfiguration('use_phone')

    banner = LogInfo(msg=[
        '\n══════════════════════════════════════════════════════════════════\n',
        '  AisleBot Unified Stack\n',
        '  ESP32 (drive): ', LaunchConfiguration('esp32_port'),
        ' @ ', LaunchConfiguration('esp32_baud'), ' baud\n',
        '  Mega  (arm)  : ', LaunchConfiguration('arm_port'),
        ' @ ', LaunchConfiguration('arm_baud'), ' baud\n',
        '  USB joystick : ', use_joy, '\n',
        '  Phone server : ', use_phone,
        '  (port ', LaunchConfiguration('http_port'), ')\n',
        '══════════════════════════════════════════════════════════════════\n',
    ])

    # ────────── INPUT NODES ───────────────────────────────────────
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

    # ────────── DRIVE PIPELINE ────────────────────────────────────
    teleop = Node(
        package='mecanum_robot', executable='teleop_asym',
        name='teleop_asym',
        output='screen',
    )

    esp32_bridge = Node(
        package='mecanum_robot', executable='esp32_bridge',
        name='esp32_bridge',
        parameters=[{
            'serial_port': LaunchConfiguration('esp32_port'),
            'baud_rate':   LaunchConfiguration('esp32_baud'),
        }],
        output='screen',
    )

    # ────────── ARM PIPELINE ──────────────────────────────────────
    arm_bridge = Node(
        package='mecanum_robot', executable='arm_bridge',
        name='arm_bridge',
        parameters=[{
            'serial_port': LaunchConfiguration('arm_port'),
            'baud_rate':   LaunchConfiguration('arm_baud'),
            # Auto-disable bench joystick once Pi takes over.
            # Auto-enable is OFF by default — explicit ENABLE keeps you safer.
            'disable_joystick_on_connect': True,
            'auto_enable_on_connect': False,
        }],
        output='screen',
    )

    return LaunchDescription([
        *args,
        banner,
        joy_node, joy_translator, phone,
        teleop, esp32_bridge,
        arm_bridge,
    ])
