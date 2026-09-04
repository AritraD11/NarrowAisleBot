#!/usr/bin/env python3
"""
mapping_full.launch.py — the LiDAR chain plus slam_toolbox, in one command.

Replaces the 3-terminal manual bringup documented in
docs/LiDAR_SLAM_Bringup.md (lidar -> relay -> slam_toolbox), now that the
pipeline itself is proven (Research_Journal.md Part XVI §16.8-16.9).

    sensors.launch.py       lidar + scan_relay + zero_point marker
    online_async_launch.py  slam_toolbox: mapping, params from slam_nodom.yaml

The sensor chain moved OUT of this file on 1 Sep 2026 (§17.49) and into
sensors.launch.py. Behaviour here is unchanged — same nodes, same
parameters, same order — but the LiDAR is no longer welded to SLAM. Until
that split, the only way to start the scanner was to start a mapping
session, which made the AMCL path in
mecanum_navigation/launch/navigation.launch.py physically impossible to run:
it forbids running alongside this file, and nothing else brought up a /scan.

Deliberately NOT merged into aislebot_full.launch.py / aislebot.service and
NOT auto-started at boot — start_lidar.sh's original design note still
applies (mapping shouldn't restart when the drive stack does, and doesn't
need to run continuously). Started on demand, in practice by the phone
dashboard's MAP button (phone_dashboard.py's start_mapping()).

⚠ MAP FIRST, THEN NAV. If nav2_slam.launch.py is launched before this file,
  its global_costmap has no /map and logs `Received map message is
  malformed. Rejecting.` once a second until one arrives — measured at 29
  consecutive seconds on 1 Sep (§17.49). NavFn cannot plan during that
  window.

Requires odom->base_link TF already being published, which comes from
odometry_publisher in aislebot.service (needs esp32_bridge's
telemetry_enabled parameter, on by default as of this fix) — if that's
missing this will sit at "Activating" with no error; see
docs/LiDAR_SLAM_Bringup.md's "silent blockers" section.

Usage:
    ros2 launch mecanum_robot mapping_full.launch.py
    ros2 launch mecanum_robot mapping_full.launch.py map_name:=my_map
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    ydlidar_share = get_package_share_directory('ydlidar_ros2_driver')
    robot_share = get_package_share_directory('mecanum_robot')

    # Re-declared here, not just inherited, so `ros2 launch ... -s` still
    # documents them on this file and existing invocations keep working
    # verbatim. They are forwarded to sensors.launch.py below.
    args = [
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.expanduser('~/ros2_ws/slam_nodom.yaml'),
        ),
        DeclareLaunchArgument(
            'scan_relay_path',
            default_value=os.path.expanduser('~/ros2_ws/src/scan_relay/scan_relay.py'),
        ),
        DeclareLaunchArgument(
            'ydlidar_params_file',
            default_value=os.path.join(ydlidar_share, 'params', 'ydlidar.yaml'),
            description="The driver's own params file — same default its "
                        "ydlidar_launch.py uses.",
        ),
    ]

    # The LiDAR chain. See sensors.launch.py for the driver/TF reasoning that
    # used to live in this file — in particular why the vendor's
    # ydlidar_launch.py is deliberately not used.
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(robot_share, 'launch', 'sensors.launch.py')
        ),
        launch_arguments={
            'scan_relay_path': LaunchConfiguration('scan_relay_path'),
            'ydlidar_params_file': LaunchConfiguration('ydlidar_params_file'),
            'zero_point': 'true',
        }.items(),
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('slam_toolbox'),
                'launch', 'online_async_launch.py',
            )
        ),
        launch_arguments={
            'slam_params_file': LaunchConfiguration('slam_params_file'),
        }.items(),
    )

    return LaunchDescription([
        *args,
        sensors,
        slam,
    ])
