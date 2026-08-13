#!/usr/bin/env python3
"""
nav2_slam.launch.py — Nav2 autonomous navigation WHILE slam_toolbox is mapping.

This is the "drive autonomously in a space you haven't mapped yet" mode:
you send the robot a goal, Nav2 plans and drives to it, and slam_toolbox
keeps building the map from the scans collected on the way.

WHY THIS STARTS NODES EXPLICITLY INSTEAD OF INCLUDING nav2_bringup
    The first version included nav2_bringup's navigation_launch.py. On this
    Nav2 build that also starts route_server and opennav_docking — neither
    of which existed in the Nav2 generation nav2_params.yaml was written
    against, and neither of which this robot has any use for. docking_server
    then refused to configure ("Charging dock plugins not given!"), and
    because lifecycle_manager brings nodes up as an all-or-nothing set, ONE
    unconfigurable node it never needed aborted the entire bringup
    (Research_Journal.md §17.17).

    Configuring a full charging-dock stack for a robot with no charging dock
    would be pure ceremony, and would leave the same trap set for whatever
    node the next Nav2 release adds. Starting exactly the nodes this robot
    uses is both smaller and more honest about what is actually running.

    Deliberately NOT started, and why:
      route_server     — route-graph planning from a GeoJSON file. No graph
                         exists; the default behaviour tree never calls it.
      docking_server   — autonomous charging-dock approach. No dock exists.

WHAT THIS STARTS
    controller_server   DWB local planner + local costmap
    planner_server      NavFn/A* global planner + global costmap
    smoother_server     path smoothing
    behavior_server     spin / backup / wait recoveries
    bt_navigator        the behaviour tree that sequences all of the above
    waypoint_follower   multi-goal sequencing
    velocity_smoother   acceleration limiting
    collision_monitor   the hard safety layer, last before the wheels
    lifecycle_manager   brings the above up in order

HOW THIS DIFFERS FROM navigation.launch.py
    navigation.launch.py starts map_server + AMCL — the "navigate on a
    previously-saved, finished map" mode. AMCL and slam_toolbox BOTH publish
    map->odom, so running that file while mapping corrupts the pose estimate
    (nav2_params.yaml's own AMCL warning). This file has no localization at
    all: it comes from the already-running slam_toolbox.

PREREQUISITES — all three must already be up, in this order:
    1. aislebot.service          (odometry_publisher -> odom->base_link TF,
                                  teleop_asym -> consumes /cmd_vel)
    2. mapping_full.launch.py    (LiDAR + scan_relay + slam_toolbox ->
                                  /scan_reliable, /map, map->odom TF)
    3. This file.

    Nav2's costmaps need /map and the TF tree to exist, or they sit inactive
    waiting for a transform that never arrives.

Usage:
    ros2 launch mecanum_navigation nav2_slam.launch.py

Then send a goal from Foxglove (or `ros2 action send_goal /navigate_to_pose
...`) and the robot drives there on its own.

AXES: base_link on this robot is NOT REP-103 (+X=right, +Y=forward,
Research_Journal.md §17.10). Every x/y-labelled velocity and footprint
parameter lives in nav2_params.yaml and is already swapped to match — see
the AXES note at the top of that file before touching any of them.

cmd_vel CHAIN, wired by the remappings below:
    controller_server -> /cmd_vel_nav
      -> velocity_smoother -> /cmd_vel_smoothed
        -> collision_monitor -> /cmd_vel
/cmd_vel is what teleop_asym already consumes, so Nav2 slots into the
existing, validated drive path as just another publisher — the wheel
kinematics and the ESP32 bridge are untouched by any of this. Note that
collision_monitor is wired by PARAMETERS (cmd_vel_in_topic /
cmd_vel_out_topic in nav2_params.yaml), not by remapping, which is how
that node expects to be configured.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


# Order matters: lifecycle_manager configures and activates these in
# sequence, and later nodes assume earlier ones are already up.
LIFECYCLE_NODES = [
    'controller_server',
    'smoother_server',
    'planner_server',
    'behavior_server',
    'velocity_smoother',
    'collision_monitor',
    'bt_navigator',
    'waypoint_follower',
]


def generate_launch_description():
    nav_dir = get_package_share_directory('mecanum_navigation')
    default_params = os.path.join(nav_dir, 'config', 'nav2_params.yaml')

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')

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

    common = [params_file, {'use_sim_time': use_sim_time}]

    nodes = [
        Node(
            package='nav2_controller', executable='controller_server',
            name='controller_server', output='screen', parameters=common,
            # DWB publishes cmd_vel; hand it to the smoother rather than
            # straight to the wheels, so nothing reaches the base without
            # passing the smoother and then the collision monitor.
            remappings=[('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_smoother', executable='smoother_server',
            name='smoother_server', output='screen', parameters=common,
        ),
        Node(
            package='nav2_planner', executable='planner_server',
            name='planner_server', output='screen', parameters=common,
        ),
        Node(
            package='nav2_behaviors', executable='behavior_server',
            name='behavior_server', output='screen', parameters=common,
        ),
        Node(
            package='nav2_velocity_smoother', executable='velocity_smoother',
            name='velocity_smoother', output='screen', parameters=common,
            # Input side only. Its output stays on the default
            # cmd_vel_smoothed, which collision_monitor reads by parameter.
            remappings=[('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_collision_monitor', executable='collision_monitor',
            name='collision_monitor', output='screen', parameters=common,
            # No remappings: cmd_vel_in_topic / cmd_vel_out_topic are set in
            # nav2_params.yaml, which is how this node is meant to be wired.
        ),
        Node(
            package='nav2_bt_navigator', executable='bt_navigator',
            name='bt_navigator', output='screen', parameters=common,
        ),
        Node(
            package='nav2_waypoint_follower', executable='waypoint_follower',
            name='waypoint_follower', output='screen', parameters=common,
        ),
        Node(
            package='nav2_lifecycle_manager', executable='lifecycle_manager',
            name='lifecycle_manager_navigation', output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': autostart,
                'node_names': LIFECYCLE_NODES,
            }],
        ),
    ]

    return LaunchDescription([*args, *nodes])
