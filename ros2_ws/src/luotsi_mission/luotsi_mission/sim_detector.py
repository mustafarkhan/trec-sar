"""Model-based detector (default in simulation).

Uses the analytic POD model (range, canopy, line of sight) against the known
casualty location. Deterministic per seed, so 3D runs can be compared with the
2D Monte Carlo. Switch to yolo_detector for image-based detection.
"""
from __future__ import annotations

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.node import Node

from .common import get_world

from luotsi_core.sim import sample_casualty  # noqa: E402


class SimDetector(Node):
    def __init__(self):
        super().__init__("luotsi_sim_detector")
        self.declare_parameter("scenario", "forest_winter")
        self.declare_parameter("casualty_seed", 1002)
        w = get_world(self.get_parameter("scenario").value)
        self.w, self.t = w, w.sc.terrain
        seed = int(self.get_parameter("casualty_seed").value)
        self.casualty = sample_casualty(w, np.random.default_rng(seed))
        self.rng = np.random.default_rng(seed + 10_000)
        self.last = None
        self.found = False
        self.pub = self.create_publisher(PointStamped, "/luotsi/detection", 10)
        self.create_subscription(PoseStamped, "/luotsi/ground_truth_pose", self.on_pose, 10)

    def on_pose(self, msg: PoseStamped):
        rc = self.t.xy_to_cell(msg.pose.position.x, msg.pose.position.y)
        if rc == self.last or self.found:
            return
        self.last = rc
        idx, pod = self.w.detector.glimpse(rc)
        hit = np.nonzero(idx == self.casualty)[0]
        if hit.size and self.rng.random() < pod[hit[0]]:
            self.found = True
            x, y = self.t.cell_to_xy(self.t.rc(self.casualty))
            out = PointStamped()
            out.header.frame_id = "world"
            out.header.stamp = self.get_clock().now().to_msg()
            out.point.x, out.point.y = x, y
            self.pub.publish(out)
            self.get_logger().warn(f"person detected at {x:.1f}, {y:.1f}")


def main():
    rclpy.init()
    n = SimDetector()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.try_shutdown()
