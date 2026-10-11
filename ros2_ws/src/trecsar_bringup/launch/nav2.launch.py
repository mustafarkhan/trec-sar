"""Minimal Nav2 for TREC-SAR: planner, controller, behaviours and BT navigator only.

The stock nav2_bringup/navigation_launch.py lifecycle-manages servers that change
between Jazzy point releases (route, docking, collision monitor) and refuse to
start without their own parameters. This launch starts exactly the servers
configured in config/nav2_params.yaml, so it behaves the same on every release.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

NODES = [
    ("nav2_controller", "controller_server", [("cmd_vel", "/cmd_vel")]),
    ("nav2_planner", "planner_server", []),
    ("nav2_behaviors", "behavior_server", [("cmd_vel", "/cmd_vel")]),
    ("nav2_bt_navigator", "bt_navigator", []),
]


def generate_launch_description():
    params = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    default_params = os.path.join(get_package_share_directory("trecsar_bringup"), "config", "nav2_params.yaml")
    nodes = [
        Node(
            package=pkg,
            executable=exe,
            name=exe,
            output="screen",
            parameters=[params, {"use_sim_time": use_sim_time}],
            remappings=remap,
        )
        for pkg, exe, remap in NODES
    ]
    manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time, "autostart": True, "node_names": [n[1] for n in NODES]}],
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument("params_file", default_value=default_params),
            DeclareLaunchArgument("use_sim_time", default_value="true"),
            *nodes,
            manager,
        ]
    )
