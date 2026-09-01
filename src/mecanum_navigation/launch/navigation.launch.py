#!/usr/bin/env python3
"""
navigation.launch.py — Nav2 autonomous navigation on a pre-built, SAVED map
(map_server + AMCL localization, slam_toolbox NOT running).

This is the "map once, then freeze and localize" mode: drive the map with
mapping_full.launch.py, confirm loop closure back at the physical zero
mark, save it (slam_toolbox's Save Map service), then load that saved
.yaml/.pgm pair here. AMCL — a particle filter, not a live scan-matching
SLAM — places the robot inside that FIXED map. Nothing rewrites the map
after this point, which is the whole point of this mode: no more of the
map->odom recentering that live SLAM-while-navigating does every time it
corrects itself (expected behaviour there, but not what you want once
you've already trusted a map enough to navigate on it).

⚠ Do NOT run this at the same time as mapping_full.launch.py. AMCL and
  slam_toolbox both publish map->odom; running both corrupts the pose
  estimate (nav2_params.yaml's own AMCL warning, and the tutorial script
  this file follows says the same thing).

REWRITTEN from a bare `nav2_bringup bringup_launch.py` include to this
explicit-node form for the exact same reason nav2_slam.launch.py was
(§17.17): bringup_launch.py chains together localization_launch.py AND
navigation_launch.py, and the latter starts route_server and
opennav_docking on this Nav2 build — neither exists for this robot, and
docking_server's unconfigurable state aborts the whole all-or-nothing
lifecycle bringup. This file was NEVER RUN before that rewrite, so it
would have hit that exact failure the first time someone tried it.

It ALSO would have been missing the cmd_vel_axis_adapter / twist_mux /
collision_monitor rewiring nav2_slam.launch.py already has — a stock
bringup publishes velocity straight to /cmd_vel in base_link's TF axes
(+X=right, +Y=forward on this robot), which is exactly the 90°
misdirection that sent the first-ever autonomous goal 0.956 m sideways
(§17.19). Both gaps are closed below by reusing nav2_slam.launch.py's
node list verbatim, just swapping the localization source.

WHAT THIS STARTS
    map_server           loads the saved map, publishes /map (latched)
    amcl                 particle-filter localization against that map
    controller_server     MPPI local planner + local costmap
    planner_server        NavFn/A* global planner + global costmap
    smoother_server        path smoothing
    behavior_server        spin / backup / wait recoveries
    bt_navigator            the behaviour tree that sequences all of the above
    waypoint_follower       multi-goal sequencing
    velocity_smoother      acceleration limiting
    collision_monitor      the hard safety layer, last before the wheels
    cmd_vel_axis_adapter   TF axes -> wheel-kinematics axes (see below)
    goal_pose_adapter      Foxglove click-to-goal fix (inert unless armed)
    lifecycle_manager      brings the above up in order

PREREQUISITES — all must already be up, in this order:
    1. aislebot.service   (odometry_publisher -> odom->base_link TF,
                           twist_mux -> /cmd_vel, teleop_asym -> wheels)
    2. A saved map. mapping_full.launch.py, drive it, confirm loop closure
       at the zero mark, then use slam_toolbox's Save Map RViz/Foxglove
       panel (or its save_map service) to write <name>.yaml + <name>.pgm.
    3. slam_toolbox from step 2 STOPPED. Two nodes publishing map->odom
       at once corrupts the pose estimate.
    4. This file, with map:=/path/to/<name>.yaml.

Usage:
    ros2 launch mecanum_navigation navigation.launch.py \
        map:=/home/aritra/ros2_ws/maps/<name>.yaml

Then send a goal from Foxglove, same as nav2_slam.launch.py.

AXES: base_link on this robot is NOT REP-103 (+X=right, +Y=forward,
Research_Journal.md §17.10). Every x/y-labelled velocity and footprint
parameter lives in nav2_params.yaml and is already swapped to match — see
the AXES note at the top of that file before touching any of them.

cmd_vel CHAIN, wired by the remappings below (identical to nav2_slam.launch.py):
    controller_server -> /cmd_vel_nav ─┐
    behavior_server   -> /cmd_vel_nav ─┤   (Spin / BackUp / Wait recoveries)
                                       ↓
      -> velocity_smoother -> /cmd_vel_smoothed
        -> collision_monitor -> /cmd_vel_baselink      (base_link TF axes)
          -> cmd_vel_axis_adapter -> /cmd_vel_nav_out  (wheel-kinematics axes)
            -> twist_mux -> /cmd_vel                   (arbitrated against manual,
                                                          aislebot.service)
twist_mux (always running as part of aislebot.service) is what actually
publishes /cmd_vel, the topic teleop_asym consumes — so a human on the
joystick or phone dashboard can always take over from AMCL/Nav2 mid-drive,
the same safety property nav2_slam.launch.py has.

robot_localization EKF: deliberately not started, same two reasons as the
old navigation.launch.py and nav2_slam.launch.py — it would duplicate
odometry_publisher's odom->base_link TF (and its validated -90° axis
rotation), and it fuses an IMU (BNO055) that is still unpurchased Phase 2
work. Restore only when both are addressed together.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode, Node


# Order matters: lifecycle_manager configures and activates these in
# sequence. map_server and amcl come first — planner/controller/behavior
# all need a valid /map and a localized pose before they have anything
# useful to plan against.
LIFECYCLE_NODES = [
    'map_server',
    'amcl',
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

    # Same reasoning as nav2_slam.launch.py: bt_navigator's default BT xml
    # paths are resolved here, not left to nav2_params.yaml's fallback,
    # which this Nav2 build does not actually apply (§17.19).
    bt_nav_dir = get_package_share_directory('nav2_bt_navigator')
    default_nav_to_pose_bt = os.path.join(
        bt_nav_dir, 'behavior_trees',
        'navigate_to_pose_w_replanning_and_recovery.xml')
    default_nav_through_poses_bt = os.path.join(
        bt_nav_dir, 'behavior_trees',
        'navigate_through_poses_w_replanning_and_recovery.xml')

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    map_yaml = LaunchConfiguration('map')

    args = [
        DeclareLaunchArgument(
            'map',
            description='Path to the saved map YAML file (required — no '
                        'default, since navigating on the wrong map, or no '
                        'map, is worse than failing to launch)',
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=default_params,
            description='Nav2 parameters (footprint/velocity axes already '
                        'swapped for this robot, AMCL block included — see '
                        'the file header)',
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
        DeclareLaunchArgument(
            'with_sensors',
            default_value='true',
            description='Start the LiDAR chain (sensors.launch.py). TRUE is '
                        'correct for this file: AMCL cannot run alongside '
                        'mapping_full.launch.py, which was the only other '
                        'thing that started the scanner (§17.49). Set false '
                        'ONLY if you have already started sensors.launch.py '
                        'by hand — two ydlidar drivers on one serial port is '
                        'not a soft failure.',
        ),
    ]

    common = [params_file, {'use_sim_time': use_sim_time}]

    # ── THE LIDAR CHAIN — the thing this file could not previously have ──
    # Before §17.49 the only launcher of the scanner was
    # mapping_full.launch.py, which also starts slam_toolbox, which this
    # file's own header forbids running alongside. AMCL would therefore
    # activate with no /scan and never localise, which reads as an AMCL
    # fault and is not one. Started first so /scan and the TF chain are up
    # before the lifecycle manager activates amcl.
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('mecanum_robot'),
                'launch', 'sensors.launch.py',
            )
        ),
        condition=IfCondition(LaunchConfiguration('with_sensors')),
        launch_arguments={'zero_point': 'true'}.items(),
    )

    nodes = [
        LifecycleNode(
            package='nav2_map_server', executable='map_server',
            name='map_server', namespace='', output='screen',
            parameters=common + [{'yaml_filename': map_yaml}],
        ),
        LifecycleNode(
            package='nav2_amcl', executable='amcl',
            name='amcl', namespace='', output='screen',
            parameters=common,
        ),
        Node(
            package='nav2_controller', executable='controller_server',
            name='controller_server', output='screen', parameters=common,
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
            # Same reasoning as nav2_slam.launch.py's behavior_server: without
            # this remap, Spin/BackUp recoveries reach the wheels unmonitored
            # (skipping collision_monitor) and in the wrong axis convention.
            remappings=[('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_velocity_smoother', executable='velocity_smoother',
            name='velocity_smoother', output='screen', parameters=common,
            remappings=[('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_collision_monitor', executable='collision_monitor',
            name='collision_monitor', output='screen', parameters=common,
            # cmd_vel_in_topic / cmd_vel_out_topic set in nav2_params.yaml.
        ),
        Node(
            package='nav2_bt_navigator', executable='bt_navigator',
            name='bt_navigator', output='screen',
            parameters=common + [{
                'default_nav_to_pose_bt_xml': default_nav_to_pose_bt,
                'default_nav_through_poses_bt_xml': default_nav_through_poses_bt,
            }],
        ),
        Node(
            package='nav2_waypoint_follower', executable='waypoint_follower',
            name='waypoint_follower', output='screen', parameters=common,
        ),
        # Plain rclpy node, not a lifecycle node — must already be
        # translating before collision_monitor is ever activated. Output
        # goes to cmd_vel_nav_out, not cmd_vel: twist_mux (aislebot.service)
        # is what publishes the final /cmd_vel, so a human can override this.
        Node(
            package='mecanum_navigation', executable='cmd_vel_axis_adapter',
            name='cmd_vel_axis_adapter', output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'output_topic': 'cmd_vel_nav_out',
            }],
        ),
        # Inert unless Foxglove's 3D panel is deliberately pointed at
        # /goal_pose_click instead of /goal_pose — see nav2_slam.launch.py.
        Node(
            package='mecanum_navigation', executable='goal_pose_adapter',
            name='goal_pose_adapter', output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
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

    return LaunchDescription([*args, sensors, *nodes])
