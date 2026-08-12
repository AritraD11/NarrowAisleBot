"""
AisleBot Navigation Launch
============================
Starts Nav2 stack for autonomous navigation on a pre-built, saved map
(map_server + AMCL localization).

⚠ This is the FINISHED-MAP mode. Do NOT run it while slam_toolbox is
  mapping — AMCL and slam_toolbox both publish map->odom and will fight
  over the pose estimate (see nav2_params.yaml's AMCL warning). To drive
  autonomously *while* mapping, use nav2_slam.launch.py instead.

Usage:
  ros2 launch mecanum_navigation navigation.launch.py map:=/path/to/map.yaml
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_dir = get_package_share_directory('mecanum_navigation')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    nav2_params = os.path.join(nav_dir, 'config', 'nav2_params.yaml')

    # ── robot_localization EKF: REMOVED, deliberately ────────────────
    # This launch file used to start ekf_node unconditionally. Two
    # separate reasons it must not, both found before this file was ever
    # run for the first time:
    #
    #   1. DUPLICATE odom->base_link TF. ekf_params.yaml sets
    #      publish_tf: true with world_frame: odom, so the EKF publishes
    #      odom->base_link — the exact transform odometry_publisher
    #      already publishes (publish_tf: True in aislebot_full.launch.py).
    #      Two publishers of one transform overwrite each other, and the
    #      one being overwritten carries the validated constant -90 deg
    #      published-frame rotation that makes base_link's axes agree with
    #      the LiDAR (§17.10-§17.11). Starting the EKF would have
    #      intermittently corrupted the axis convention this project spent
    #      two sessions confirming on hardware.
    #
    #   2. It fuses an IMU that does not exist. ekf_params.yaml's
    #      imu0: imu/data refers to a BNO055 that is still unpurchased
    #      Phase 2 work (Appendix B.3).
    #
    # bt_navigator already reads /wheel_odom directly (§17.6), so nothing
    # in the navigation path wanted the EKF's output anyway. Restore this
    # node only when the IMU exists AND odometry_publisher's publish_tf is
    # turned off in the same change, so exactly one node owns that TF.

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value='',
                              description='Path to map YAML file'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        # === Nav2 Bringup ===
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
            ),
            launch_arguments={
                'map': LaunchConfiguration('map'),
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'params_file': nav2_params,
                'autostart': 'true',
            }.items()
        ),
    ])
