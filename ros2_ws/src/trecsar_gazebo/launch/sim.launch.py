"""Start Gazebo Harmonic with a TREC-SAR scenario world and spawn the UGV at the command post.

    ros2 launch trecsar_gazebo sim.launch.py scenario:=forest_winter
"""
import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# Spawn poses = command post cell centre (from trecsar_core Terrain.cell_to_xy), metres.
SPAWN = {
    "forest_winter": (27.0, 15.0, 0.0),
    "tunnel": (6.0, 198.0, 0.0),
    "hazmat_industrial": (12.5, 232.5, 0.0),
}


def _setup(context):
    scenario = LaunchConfiguration("scenario").perform(context)
    gz_share = get_package_share_directory("trecsar_gazebo")
    desc_share = get_package_share_directory("trecsar_description")
    world = os.path.join(gz_share, "worlds", f"{scenario}.sdf")
    x, y, yaw = SPAWN[scenario]

    # bridge config needs the world name for the joint_state topic
    with open(os.path.join(gz_share, "config", "bridge.yaml")) as f:
        bridge_cfg = f.read().replace("WORLD_NAME", scenario)
    bridge_file = os.path.join(tempfile.gettempdir(), f"trecsar_bridge_{scenario}.yaml")
    with open(bridge_file, "w") as f:
        f.write(bridge_cfg)

    robot_description = ParameterValue(
        Command(["xacro ", os.path.join(desc_share, "urdf", "trecsar.urdf.xacro")]), value_type=str)

    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": f"-r {world}"}.items())

    return [
        gz,
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": robot_description, "use_sim_time": True}]),
        Node(package="ros_gz_sim", executable="create", output="screen",
             arguments=["-name", "trecsar", "-topic", "robot_description",
                        "-x", str(x), "-y", str(y), "-z", "0.3", "-Y", str(yaw)]),
        Node(package="ros_gz_bridge", executable="parameter_bridge", output="screen",
             parameters=[{"config_file": bridge_file, "use_sim_time": True}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="forest_winter",
                              description="forest_winter | tunnel | hazmat_industrial"),
        OpaqueFunction(function=_setup),
    ])
