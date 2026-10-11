"""Full TREC-SAR demo: Gazebo world + UGV + SLAM + Nav2 + mission stack (+ RViz).

    ros2 launch trecsar_bringup bringup.launch.py scenario:=forest_winter planner:=trecsar
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# must match trecsar_gazebo/launch/sim.launch.py and the generated worlds
SPAWN = {"forest_winter": (27.0, 15.0), "tunnel": (6.0, 198.0), "hazmat_industrial": (12.5, 232.5)}
SEED = {"forest_winter": 1002, "tunnel": 1003, "hazmat_industrial": 1022}


def _setup(context):
    scenario = LaunchConfiguration("scenario").perform(context)
    planner = LaunchConfiguration("planner").perform(context)
    sx, sy = SPAWN[scenario]
    bringup = get_package_share_directory("trecsar_bringup")
    gz = get_package_share_directory("trecsar_gazebo")
    mission_cfg = os.path.join(get_package_share_directory("trecsar_mission"), "config", "mission.yaml")
    common = {"scenario": scenario, "spawn_x": sx, "spawn_y": sy, "use_sim_time": True}
    seeded = dict(common, casualty_seed=SEED[scenario])

    sim = IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(gz, "launch", "sim.launch.py")),
                                   launch_arguments={"scenario": scenario}.items())
    slam = Node(package="slam_toolbox", executable="async_slam_toolbox_node", name="slam_toolbox", output="screen",
                parameters=[os.path.join(bringup, "config", "slam_params.yaml")])
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory("nav2_bringup"), "launch",
                                                   "navigation_launch.py")),
        launch_arguments={"use_sim_time": "true",
                          "params_file": os.path.join(bringup, "config", "nav2_params.yaml")}.items())
    mission = [
        Node(package="trecsar_mission", executable="link_sim", parameters=[mission_cfg, common]),
        Node(package="trecsar_mission", executable="sim_detector", parameters=[mission_cfg, seeded]),
        Node(package="trecsar_mission", executable="aerial_spotter", parameters=[mission_cfg, seeded]),
        Node(package="trecsar_mission", executable="mission_manager", output="screen",
             parameters=[mission_cfg, dict(common, planner=planner)]),
    ]
    rviz = Node(package="rviz2", executable="rviz2", condition=IfCondition(LaunchConfiguration("rviz")),
                arguments=["-d", os.path.join(get_package_share_directory("trecsar_description"), "rviz", "trecsar.rviz")],
                parameters=[{"use_sim_time": True}])
    # give Gazebo + SLAM time to come up before Nav2 and the mission start
    return [sim, TimerAction(period=5.0, actions=[slam]), TimerAction(period=10.0, actions=[nav2, rviz]),
            TimerAction(period=20.0, actions=mission)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="forest_winter"),
        DeclareLaunchArgument("planner", default_value="trecsar"),
        DeclareLaunchArgument("rviz", default_value="true"),
        OpaqueFunction(function=_setup),
    ])
