"""Radio-link simulator for the 3D demo.

Computes the link margin from the robot to the base + deployed relays with the
same LinkModel the planner uses, and *gates the operator video*: camera frames
reach /operator/camera only while the link is up. That makes link loss visible
in RViz exactly as an operator would experience it.
"""

from __future__ import annotations

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32
from visualization_msgs.msg import Marker, MarkerArray

from .common import get_world


class LinkSim(Node):
    def __init__(self):
        super().__init__("trecsar_link_sim")
        self.declare_parameter("scenario", "forest_winter")
        self.declare_parameter("spawn_x", 27.0)
        self.declare_parameter("spawn_y", 15.0)
        self.world = get_world(self.get_parameter("scenario").value)
        self.t = self.world.sc.terrain
        self.spawn = (self.get_parameter("spawn_x").value, self.get_parameter("spawn_y").value)
        self.nodes = [self.t.base]
        self.cov = self.world.link.coverage(self.nodes)
        self.cell = self.t.base
        self.thr = self.world.sc.mission.link_threshold_db

        self.pub_margin = self.create_publisher(Float32, "/link/margin_db", 10)
        self.pub_conn = self.create_publisher(Bool, "/link/connected", 10)
        self.pub_video = self.create_publisher(Image, "/operator/camera", 5)
        self.pub_markers = self.create_publisher(MarkerArray, "/trecsar/relays", 1)
        self.create_subscription(PoseStamped, "/trecsar/ground_truth_pose", self.on_pose, 10)
        self.create_subscription(PointStamped, "/relay/deploy", self.on_relay, 10)
        self.create_subscription(Image, "/camera/image", self.on_image, 5)
        self.create_timer(0.2, self.publish)

    def margin(self) -> float:
        return float(self.cov[self.cell])

    def on_pose(self, msg: PoseStamped):
        self.cell = self.t.xy_to_cell(msg.pose.position.x, msg.pose.position.y)

    def on_relay(self, msg: PointStamped):
        rc = self.t.xy_to_cell(msg.point.x, msg.point.y)
        self.nodes.append(rc)
        self.cov = self.world.link.coverage(self.nodes)
        self.get_logger().info(f"relay {len(self.nodes) - 1} online at cell {rc}")

    def on_image(self, msg: Image):
        if self.margin() >= self.thr:
            self.pub_video.publish(msg)

    def publish(self):
        m = self.margin()
        self.pub_margin.publish(Float32(data=m))
        self.pub_conn.publish(Bool(data=m >= self.thr))
        arr = MarkerArray()
        for i, rc in enumerate(self.nodes):
            x, y = self.t.cell_to_xy(rc)
            mk = Marker()
            mk.header.frame_id = "map"
            mk.header.stamp = self.get_clock().now().to_msg()
            mk.ns, mk.id, mk.type, mk.action = "radio_nodes", i, Marker.CYLINDER, Marker.ADD
            mk.pose.position.x, mk.pose.position.y, mk.pose.position.z = x - self.spawn[0], y - self.spawn[1], 0.5
            mk.pose.orientation.w = 1.0
            mk.scale.x = mk.scale.y = 0.6
            mk.scale.z = 1.0
            mk.color.a = 1.0
            mk.color.r, mk.color.g, mk.color.b = (0.9, 0.2, 0.1) if i == 0 else (0.95, 0.55, 0.1)
            arr.markers.append(mk)
        self.pub_markers.publish(arr)


def main():
    rclpy.init()
    n = LinkSim()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.try_shutdown()
