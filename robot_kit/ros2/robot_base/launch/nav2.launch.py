#!/usr/bin/env python3
"""
nav2.launch.py - Nav2 while slam_toolbox maps: send a goal, the robot drives
there, and the map keeps growing on the way.

    ros2 launch robot_base nav2.launch.py

Order: base.launch.py, then mapping.launch.py (wait ~30 s for /map), then this.

Nodes are started explicitly instead of including nav2_bringup. Recent
nav2_bringup also starts route_server and docking_server; docking_server
refuses to configure without dock plugins, and because lifecycle_manager
brings nodes up all-or-nothing, one node nobody needed aborted the whole
bringup on NarrowAisleBot. Start what you use.

The command chain, every autonomous command takes this path:
    controller_server / behavior_server -> /cmd_vel_nav
      -> velocity_smoother -> /cmd_vel_smoothed
        -> collision_monitor -> /cmd_vel_nav_out
          -> twist_mux (priority 10, manual wins) -> /cmd_vel -> base_controller
behavior_server is remapped too, so recovery Spin and BackUp pass the
smoother and the collision monitor like everything else. (Left on its
default, it publishes straight to /cmd_vel and bypasses both.)

The behaviour tree XML paths are resolved here and passed in, because an
empty string in the YAML does not fall back to the default on this Nav2
build ("Empty Tree", first goal on NarrowAisleBot).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

LIFECYCLE = ["controller_server", "smoother_server", "planner_server", "behavior_server",
             "velocity_smoother", "collision_monitor", "bt_navigator", "waypoint_follower"]


def generate_launch_description():
    share = get_package_share_directory("robot_base")
    params = os.path.join(share, "config", "nav2_params.yaml")
    bt = os.path.join(get_package_share_directory("nav2_bt_navigator"), "behavior_trees")
    common = [params, {"use_sim_time": False}]
    to_smoother = [("cmd_vel", "cmd_vel_nav")]
    return LaunchDescription([
        Node(package="nav2_controller", executable="controller_server", name="controller_server",
             output="screen", parameters=common, remappings=to_smoother),
        Node(package="nav2_smoother", executable="smoother_server", name="smoother_server",
             output="screen", parameters=common),
        Node(package="nav2_planner", executable="planner_server", name="planner_server",
             output="screen", parameters=common),
        Node(package="nav2_behaviors", executable="behavior_server", name="behavior_server",
             output="screen", parameters=common, remappings=to_smoother),
        Node(package="nav2_velocity_smoother", executable="velocity_smoother",
             name="velocity_smoother", output="screen", parameters=common, remappings=to_smoother),
        Node(package="nav2_collision_monitor", executable="collision_monitor",
             name="collision_monitor", output="screen", parameters=common),
        Node(package="nav2_bt_navigator", executable="bt_navigator", name="bt_navigator",
             output="screen", parameters=common + [{
                 "default_nav_to_pose_bt_xml": os.path.join(
                     bt, "navigate_to_pose_w_replanning_and_recovery.xml"),
                 "default_nav_through_poses_bt_xml": os.path.join(
                     bt, "navigate_through_poses_w_replanning_and_recovery.xml")}]),
        Node(package="nav2_waypoint_follower", executable="waypoint_follower",
             name="waypoint_follower", output="screen", parameters=common),
        Node(package="nav2_lifecycle_manager", executable="lifecycle_manager",
             name="lifecycle_manager_navigation", output="screen",
             parameters=[{"use_sim_time": False, "autostart": True, "node_names": LIFECYCLE}]),
    ])
