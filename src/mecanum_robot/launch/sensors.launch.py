#!/usr/bin/env python3
"""
sensors.launch.py — the LiDAR chain, on its own, with no estimator attached.

WHY THIS FILE EXISTS (§17.49). Until 1 Sep 2026 the only thing that started
the LiDAR was mapping_full.launch.py, which also starts slam_toolbox. And
navigation.launch.py — the AMCL path — carries this warning in its own
header:

    ⚠ Do NOT run this at the same time as mapping_full.launch.py. AMCL and
      slam_toolbox both publish map->odom; running both corrupts the pose
      estimate.

So the only thing that could bring up the scanner was the one thing AMCL
forbids running. AMCL would have launched, activated, and sat there with no
/scan forever — looking like an AMCL fault when it was a launch-topology
fault. Nothing had caught it because AMCL has never once been run.

Splitting the sensor chain out fixes that, and buys a second thing: a
scan_quality.py capture no longer requires starting a mapping session, so
the LiDAR can be characterised without also creating a map nobody wanted.

    ydlidar_ros2_driver_node   the scanner
    scan_relay.py              /scan best-effort -> /scan_reliable reliable,
                               plus the calibrated mirror and the rear-mast
                               self-occlusion mask (§17.9, §17.15)
    zero_point_tf              map -> zero_point, the visible home marker

⚠ EXACTLY ONE OF THESE MAY RUN AT A TIME. Two ydlidar drivers on one serial
  port is not a soft failure. Before launching this directly, check:

      ros2 node list | grep ydlidar        # must come back EMPTY

Usage:
    ros2 launch mecanum_robot sensors.launch.py                  # everything
    ros2 launch mecanum_robot sensors.launch.py zero_point:=false

`zero_point:=false` drops the marker, which is only meaningful once some
node is publishing a `map` frame. For a bare scan-quality capture with
neither slam_toolbox nor AMCL running there is no `map`, so the marker is a
static transform into a frame that does not exist — harmless, but noise.

Included by mapping_full.launch.py and by navigation.launch.py. Prefer
launching one of those; this file is the shared part, not usually the entry
point.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
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
            'scan_relay_path',
            default_value=os.path.expanduser('~/ros2_ws/src/scan_relay/scan_relay.py'),
        ),
        DeclareLaunchArgument(
            'ydlidar_params_file',
            default_value=os.path.join(ydlidar_share, 'params', 'ydlidar.yaml'),
            description="The driver's own params file — same default its "
                        "ydlidar_launch.py uses.",
        ),
        DeclareLaunchArgument(
            'zero_point',
            default_value='true',
            description='Publish the map->zero_point home marker. Set false '
                        'for a bare scan capture with no map frame in play.',
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
    # ⚠ Under AMCL the origin means something DIFFERENT: it is wherever the
    #   saved map's own origin sits, which is wherever odometry happened to
    #   be zeroed on the drive that BUILT the map. Same marker, same frame,
    #   different provenance — do not read it as "the mark" without knowing
    #   which map is loaded.
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
        condition=IfCondition(LaunchConfiguration('zero_point')),
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', str(ZERO_POINT_YAW),
            '--frame-id', 'map', '--child-frame-id', 'zero_point',
        ],
    )

    return LaunchDescription([
        *args,
        lidar,
        relay,
        zero_point,
    ])
