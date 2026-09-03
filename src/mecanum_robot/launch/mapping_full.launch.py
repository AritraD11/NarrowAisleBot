#!/usr/bin/env python3
"""
mapping_full.launch.py — bring up the LiDAR + SLAM mapping stack in one command.

Replaces the 3-terminal manual bringup documented in
docs/LiDAR_SLAM_Bringup.md (lidar -> relay -> slam_toolbox), now that the
pipeline itself is proven (Research_Journal.md Part XVI §16.8-16.9).

Included/started:
    ydlidar_launch.py      (ydlidar_ros2_driver: driver + base_link->laser_frame TF)
    scan_relay.py           (/scan best-effort -> /scan_reliable reliable)
    static_transform_publisher (map->zero_point, the visible home marker)
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
from launch_ros.actions import LifecycleNode, Node


# base_link's published yaw at a freshly-zeroed odometry, in radians.
# NOT an arbitrary choice, and it CHANGED on 27 Aug 2026 (§17.38).
#
# It used to be -90 deg. odometry_publisher.py rotated its published
# orientation but not its published translation, which gave odom REP-103's
# axes while base_link had +X=right/+Y=nose, so a robot standing on the
# zero mark read [0,0,0] @ -90 deg (confirmed 15 Aug via tf2_echo). The
# marker carried the same -90 deg so its triad would coincide with
# base_link's instead of sitting 90 deg away from it.
#
# That seam is gone: odom, map and base_link now all use +X=right,
# +Y=forward, so a freshly-zeroed robot on the mark reads [0,0,0] @ 0 deg
# and the marker needs no rotation to line up with it. Verify on hardware
# with `ros2 run tf2_ros tf2_echo odom base_link` before trusting a map.
ZERO_POINT_YAW = 0.0


def generate_launch_description():

    ydlidar_share = get_package_share_directory('ydlidar_ros2_driver')

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

    # ── LiDAR driver, started DIRECTLY rather than via the vendor's
    #    ydlidar_launch.py ────────────────────────────────────────────────
    # That launch file bundles two things: this driver node, and a
    # static_transform_publisher hardcoding base_link -> laser_frame as
    # (0, 0, 0.02) with zero rotation — a placeholder that is not this
    # robot's real mount, confirmed live in §17.9 and never corrected. It
    # takes no argument to disable it, so the only way to stop publishing a
    # wrong transform is to not run that file.
    #
    # The real mount is now measured and lives in aislebot.urdf's laser_joint
    # (0, 0.27, 0.275 — §17.12), published by robot_state_publisher from
    # aislebot_full.launch.py. Exactly one publisher owns this transform, and
    # it is the one carrying the measured value.
    #
    # The node declaration below is copied verbatim from the vendor launch
    # file (LifecycleNode, same name/namespace/params) so the driver behaves
    # identically — only its TF companion is dropped.
    lidar = LifecycleNode(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        emulate_tty=True,
        parameters=[LaunchConfiguration('ydlidar_params_file')],
        namespace='/',
    )

    # scan_relay.py is a plain script, not an installed package executable
    # (see src/scan_relay/scan_relay.py) - run directly rather than as a Node.
    relay = ExecuteProcess(
        cmd=['python3', LaunchConfiguration('scan_relay_path')],
        output='screen',
    )

    # ── The permanent zero-point marker ──────────────────────────────────
    # A fixed frame at the map's origin, so "am I home?" is a thing you can
    # SEE in Foxglove rather than a thing you have to eyeball against a mark
    # on the floor that the robot's own chassis is standing on top of.
    #
    # Why this lands on the physical mark at all: slam_toolbox sets map->odom
    # to identity at a mapping session's first scan — it does NOT plant the
    # map origin under the robot (§17.18/§17.19, two sessions spent proving
    # this the hard way). So map (0,0) is wherever ODOMETRY was zeroed, and
    # odometry zeroes only when odometry_publisher starts. Restarting
    # aislebot.service with the robot parked on the mark is therefore the
    # entire re-zero procedure, and this marker is only meaningful when that
    # procedure was followed — see docs/Important_Commands.md §8.
    #
    # Deliberately a child of map, not odom: map is the corrected frame the
    # occupancy grid itself is anchored to, so this marker stays put on the
    # map as the robot drives. Parented to odom it would drift along with
    # every centimetre of wheel slip, which is the opposite of a landmark.
    zero_point = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='zero_point_tf',
        output='screen',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', str(ZERO_POINT_YAW),
            '--frame-id', 'map', '--child-frame-id', 'zero_point',
        ],
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
        zero_point,
        slam,
    ])
