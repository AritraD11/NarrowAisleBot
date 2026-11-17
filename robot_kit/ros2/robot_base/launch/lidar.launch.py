#!/usr/bin/env python3
"""
lidar.launch.py - the LiDAR driver plus scan_filter. Nothing else.

    ros2 launch robot_base lidar.launch.py

Which driver runs comes from config/kit.yaml (generate.py writes it from
robot_config.yaml lidar.model). The driver's own launch file is NOT used:
vendor launch files (YDLIDAR's, for one) also publish a hard-coded
base_link -> laser_frame transform, which then fights the URDF's measured
one. Here the URDF is the only source of that transform.

EXACTLY ONE driver may own the serial port. Before launching by hand:
    ros2 node list | grep -i -e lidar -e rplidar      # must be empty
"""
import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import LogInfo
from launch_ros.actions import LifecycleNode, Node


def generate_launch_description():
    share = get_package_share_directory("robot_base")
    kit = yaml.safe_load(open(os.path.join(share, "config", "kit.yaml")))["lidar"]
    lidar_params = os.path.join(share, "config", "lidar.yaml")
    robot_params = os.path.join(share, "config", "robot.yaml")
    model = kit.get("model", "none")

    actions = []
    if model == "ydlidar":
        # Lifecycle node with namespace "/", exactly as the vendor launch file
        # declares it (NarrowAisleBot runs it this way on Jazzy).
        actions.append(LifecycleNode(
            package="ydlidar_ros2_driver", executable="ydlidar_ros2_driver_node",
            name="ydlidar_ros2_driver_node", namespace="/", output="screen",
            emulate_tty=True, parameters=[lidar_params]))
    elif model == "rplidar":
        actions.append(Node(package="rplidar_ros", executable="rplidar_node",
                            name="rplidar_node", output="screen", parameters=[lidar_params]))
    elif model == "custom":
        params = [kit["params_file"]] if kit.get("params_file") else []
        actions.append(Node(package=kit["package"], executable=kit["executable"],
                            output="screen", parameters=params,
                            remappings=[("scan", "/scan")]))
    else:
        actions.append(LogInfo(msg="lidar.model is 'none': no driver started"))

    actions.append(Node(package="robot_base", executable="scan_filter", name="scan_filter",
                        parameters=[robot_params], output="screen"))
    return LaunchDescription(actions)
