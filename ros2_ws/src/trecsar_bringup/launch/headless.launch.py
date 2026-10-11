"""Full mission stack without Gazebo or Nav2 (fake robot follows the terrain grid).

Used by CI as an end-to-end integration test, and handy on laptops without a GPU:

    ros2 launch trecsar_bringup headless.launch.py scenario:=hazmat_industrial seed:=5 speed:=8.0
    ros2 topic echo --once /trecsar/report
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

SPAWN = {"forest_winter": (27.0, 15.0), "tunnel": (6.0, 198.0), "hazmat_industrial": (12.5, 232.5)}


def _setup(context):
    scenario = LaunchConfiguration("scenario").perform(context)
    seed = int(LaunchConfiguration("seed").perform(context))
    planner = LaunchConfiguration("planner").perform(context)
    speed = float(LaunchConfiguration("speed").perform(context))
    sx, sy = SPAWN[scenario]
    mission_cfg = os.path.join(get_package_share_directory("trecsar_mission"), "config", "mission.yaml")
    common = {"scenario": scenario, "spawn_x": sx, "spawn_y": sy, "use_sim_time": False}
    seeded = dict(common, casualty_seed=seed)
    return [
        Node(
            package="trecsar_mission",
            executable="fake_robot",
            output="screen",
            parameters=[dict(common, speed_mps=speed)],
        ),
        Node(package="trecsar_mission", executable="link_sim", parameters=[mission_cfg, common]),
        Node(package="trecsar_mission", executable="sim_detector", output="screen", parameters=[mission_cfg, seeded]),
        Node(package="trecsar_mission", executable="aerial_spotter", parameters=[mission_cfg, seeded]),
        Node(
            package="trecsar_mission",
            executable="mission_manager",
            output="screen",
            parameters=[mission_cfg, dict(common, planner=planner)],
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("scenario", default_value="hazmat_industrial"),
            DeclareLaunchArgument("seed", default_value="5"),
            DeclareLaunchArgument("planner", default_value="trecsar"),
            DeclareLaunchArgument("speed", default_value="8.0", description="robot speed in m/s (2.22 = real TREC)"),
            OpaqueFunction(function=_setup),
        ]
    )
