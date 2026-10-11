"""Inspect the UGV model alone: ros2 launch trecsar_description view.launch.py"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory("trecsar_description")
    desc = ParameterValue(Command(["xacro ", os.path.join(share, "urdf", "trecsar.urdf.xacro")]), value_type=str)
    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": desc}],
            ),
            Node(package="joint_state_publisher", executable="joint_state_publisher"),
            Node(package="rviz2", executable="rviz2", arguments=["-d", os.path.join(share, "rviz", "trecsar.rviz")]),
        ]
    )
