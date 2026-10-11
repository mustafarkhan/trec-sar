"""Ground-truth localisation (simulation only): publishes map -> odom from the true pose.

Lets the mission and navigation stack be tested independently of SLAM quality.
In a wide, feature-poor yard lidar SLAM can drift by tens of metres, which tests
the SLAM configuration rather than the search logic. Use localization:=slam
for the realistic setup.

map frame = world frame shifted so the robot starts at the origin (same as SLAM).
"""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from tf2_ros import TransformBroadcaster


def _yaw(q) -> float:
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class GroundTruthLocalizer(Node):
    def __init__(self):
        super().__init__("trecsar_gt_localizer")
        self.declare_parameter("spawn_x", 27.0)
        self.declare_parameter("spawn_y", 15.0)
        self.spawn = (self.get_parameter("spawn_x").value, self.get_parameter("spawn_y").value)
        self.truth = None
        self.odom = None
        self.tf = TransformBroadcaster(self)
        self.create_subscription(PoseStamped, "/trecsar/ground_truth_pose", self.on_truth, 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_timer(0.05, self.publish)

    def on_truth(self, msg: PoseStamped):
        p = msg.pose
        self.truth = (p.position.x - self.spawn[0], p.position.y - self.spawn[1], _yaw(p.orientation))

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose
        self.odom = (p.position.x, p.position.y, _yaw(p.orientation), msg.header.stamp)

    def publish(self):
        if self.truth is None or self.odom is None:
            return
        mx, my, myaw = self.truth  # base in map
        ox, oy, oyaw, stamp = self.odom  # base in odom
        # map->odom = map->base * (odom->base)^-1
        yaw = myaw - oyaw
        c, s = math.cos(yaw), math.sin(yaw)
        tx = mx - (c * ox - s * oy)
        ty = my - (s * ox + c * oy)
        t = TransformStamped()
        t.header.stamp = stamp
        t.header.frame_id = "map"
        t.child_frame_id = "odom"
        t.transform.translation.x, t.transform.translation.y = tx, ty
        t.transform.rotation.z, t.transform.rotation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        self.tf.sendTransform(t)


def main():
    rclpy.init()
    n = GroundTruthLocalizer()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.try_shutdown()
