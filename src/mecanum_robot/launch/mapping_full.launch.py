#!/usr/bin/env python3
"""
mapping_full.launch.py — bring up the LiDAR + SLAM mapping stack in one command.

Replaces the 3-terminal manual bringup documented in
docs/LiDAR_SLAM_Bringup.md (lidar -> relay -> slam_toolbox), now that the
pipeline itself is proven (Research_Journal.md Part XVI §16.8-16.9).

Included/started:
    ydlidar_launch.py      (ydlidar_ros2_driver: driver + base_link->laser_frame TF)
    scan_relay.py           (/scan best-effort -> /scan_reliable reliable)
    online_async_launch.py  (slam_toolbox: mapping, params from slam_nodom.yaml)

Deliberately NOT merged into aislebot_full.launch.py / aislebot.service and
NOT auto-started at boot — start_lidar.sh's original design note still
applies (mapping shouldn't restart when the drive stack does, and doesn't
need to run continuously). This is meant to be launched on demand, e.g. from
a future phone-dashboard trigger.

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
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():

    args = [
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.expanduser('~/ros2_ws/slam_nodom.yaml'),
        ),
        DeclareLaunchArgument(
            'scan_relay_path',
            default_value=os.path.expanduser('~/ros2_ws/src/scan_relay/scan_relay.py'),
        ),
    ]

    lidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ydlidar_ros2_driver'),
                'launch', 'ydlidar_launch.py',
            )
        ),
    )

    # scan_relay.py is a plain script, not an installed package executable
    # (see src/scan_relay/scan_relay.py) - run directly rather than as a Node.
    relay = ExecuteProcess(
        cmd=['python3', LaunchConfiguration('scan_relay_path')],
        output='screen',
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
        lidar,
        relay,
        slam,
    ])
