"""Aerial spotter STUB.

Stands in for a drone running a thermal person detector (see perception/). It
sends one noisy "possible person here" cue at `cue_time_s`, with the same
canopy-dependent hit / false-alarm model as the 2D simulator. Replace with a
PX4 SITL drone + the trained detector for full air-ground teaming.
"""

from __future__ import annotations

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped
from rclpy.node import Node

from trecsar_core.sim import sample_casualty  # noqa: E402

from .common import get_world


class AerialSpotter(Node):
    def __init__(self):
        super().__init__("trecsar_aerial_spotter")
        self.declare_parameter("scenario", "forest_winter")
        self.declare_parameter("casualty_seed", 1002)
        self.declare_parameter("cue_time_s", -1.0)  # <0: use the scenario default
        w = get_world(self.get_parameter("scenario").value)
        self.w, self.t = w, w.sc.terrain
        seed = int(self.get_parameter("casualty_seed").value)
        self.casualty = self.t.rc(sample_casualty(w, np.random.default_rng(seed)))
        self.rng = np.random.default_rng(seed + 20_000)
        ct = float(self.get_parameter("cue_time_s").value)
        self.cue_time = ct if ct >= 0 else w.sc.mission.aerial_cue_time_s
        self.pub = self.create_publisher(PointStamped, "/aerial/cue", 10)
        self.start = None
        self.done = self.cue_time is None
        self.create_timer(1.0, self.step)
        if self.done:
            self.get_logger().info("no drone in this scenario (underground)")

    def step(self):
        if self.done:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        self.start = now if self.start is None else self.start
        if now - self.start < self.cue_time:
            return
        self.done = True
        m = self.w.sc.mission
        cr, cc = self.casualty
        sig = m.aerial_cue_sigma_m / self.t.resolution
        if self.rng.random() < 0.8 * (1.0 - 0.9 * self.t.canopy[cr, cc]):
            rc = (
                int(np.clip(cr + self.rng.normal(0, sig), 0, self.t.shape[0] - 1)),
                int(np.clip(cc + self.rng.normal(0, sig), 0, self.t.shape[1] - 1)),
            )
        elif self.rng.random() < m.aerial_false_cue_rate:
            p = self.w.prior.ravel()
            rc = self.t.rc(int(self.rng.choice(p.size, p=p / p.sum())))
        else:
            self.get_logger().info("drone saw nothing (canopy)")
            return
        x, y = self.t.cell_to_xy(rc)
        msg = PointStamped()
        msg.header.frame_id = "world"
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.point.x, msg.point.y = x, y
        self.pub.publish(msg)
        self.get_logger().info(f"aerial cue sent at {x:.0f}, {y:.0f}")


def main():
    rclpy.init()
    n = AerialSpotter()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.try_shutdown()
