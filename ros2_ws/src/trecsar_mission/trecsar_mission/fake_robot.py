"""Headless stand-in for Gazebo + Nav2, used for integration tests and quick demos.

Provides the `navigate_to_pose` action (same interface as Nav2) and publishes the
robot's ground-truth pose. Goals are followed along the shortest grid path of the
scenario terrain at `speed_mps`, so the whole mission stack (mission manager,
radio-link simulator, detector, drone stub) runs exactly as it would with Gazebo,
without a GPU or a physics engine.

    ros2 launch trecsar_bringup headless.launch.py scenario:=hazmat_industrial
"""

from __future__ import annotations

import threading
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from .common import get_world


class FakeRobot(Node):
    def __init__(self):
        super().__init__("trecsar_fake_robot")
        self.declare_parameter("scenario", "forest_winter")
        self.declare_parameter("spawn_x", 27.0)
        self.declare_parameter("spawn_y", 15.0)
        self.declare_parameter("speed_mps", 2.22)
        self.world = get_world(self.get_parameter("scenario").value)
        self.t = self.world.sc.terrain
        self.spawn = (self.get_parameter("spawn_x").value, self.get_parameter("spawn_y").value)
        self.speed = float(self.get_parameter("speed_mps").value)
        self.cell = self.t.idx(self.t.base)
        self.lock = threading.Lock()
        self.active = None  # newest goal wins (Nav2 preemption semantics)
        cb = ReentrantCallbackGroup()
        self.pub = self.create_publisher(PoseStamped, "/trecsar/ground_truth_pose", 10)
        self.create_timer(0.05, self.publish_pose, callback_group=cb)
        self.server = ActionServer(
            self,
            NavigateToPose,
            "navigate_to_pose",
            execute_callback=self.execute,
            goal_callback=lambda _g: GoalResponse.ACCEPT,
            cancel_callback=lambda _g: CancelResponse.ACCEPT,
            callback_group=cb,
        )
        self.get_logger().info(f"fake robot ready in '{self.world.sc.key}' at {self.speed:.1f} m/s")

    def publish_pose(self):
        with self.lock:
            x, y = self.t.cell_to_xy(self.t.rc(self.cell))
        msg = PoseStamped()
        msg.header.frame_id = "world"
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x, msg.pose.position.y = x, y
        msg.pose.orientation.w = 1.0
        self.pub.publish(msg)

    def execute(self, goal_handle):
        self.active = goal_handle
        p = goal_handle.request.pose.pose.position
        goal = self.t.idx(self.t.xy_to_cell(p.x + self.spawn[0], p.y + self.spawn[1]))
        with self.lock:
            start = self.cell
        _, pred = self.world.oracle.from_cell(start)
        path = self.world.oracle.path(pred, start, goal)
        for nxt in path[1:]:
            if self.active is not goal_handle:  # preempted by a newer goal
                goal_handle.abort()
                return NavigateToPose.Result()
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return NavigateToPose.Result()
            with self.lock:
                step = self.world.oracle.g[self.cell, nxt]
            time.sleep(float(step) / self.speed)
            with self.lock:
                self.cell = nxt
        goal_handle.succeed()
        return NavigateToPose.Result()


def main():
    rclpy.init()
    node = FakeRobot()
    ex = MultiThreadedExecutor(num_threads=4)
    ex.add_node(node)
    try:
        ex.spin()
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()
