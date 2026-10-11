"""Image-based person detector (optional; needs `pip install ultralytics`).

Runs a YOLO model on the RGB or thermal camera. A detection is localised
roughly: robot position + `assumed_range_m` along the robot heading. That is
deliberately crude — a real system would use the lidar or stereo depth for the
range — and is documented as a limitation.

    ros2 run trecsar_mission yolo_detector --ros-args -p model:=best.pt -p image_topic:=/thermal/image
"""
from __future__ import annotations

import math

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from rclpy.node import Node
from sensor_msgs.msg import Image


def image_to_numpy(msg: Image) -> np.ndarray:
    """sensor_msgs/Image -> HxWx3 uint8 without cv_bridge."""
    h, w = msg.height, msg.width
    if msg.encoding in ("rgb8", "bgr8"):
        arr = np.frombuffer(msg.data, np.uint8).reshape(h, w, 3)
        return arr[..., ::-1].copy() if msg.encoding == "bgr8" else arr.copy()
    if msg.encoding in ("mono16", "16UC1"):        # thermal L16: stretch to 8 bit
        a = np.frombuffer(msg.data, np.uint16).reshape(h, w).astype(np.float32)
        lo, hi = np.percentile(a, 1), np.percentile(a, 99)
        g = np.clip((a - lo) / max(hi - lo, 1.0) * 255, 0, 255).astype(np.uint8)
        return np.repeat(g[..., None], 3, axis=2)
    if msg.encoding in ("mono8", "8UC1"):
        g = np.frombuffer(msg.data, np.uint8).reshape(h, w)
        return np.repeat(g[..., None], 3, axis=2)
    raise ValueError(f"unsupported encoding {msg.encoding}")


class YoloDetector(Node):
    def __init__(self):
        super().__init__("trecsar_yolo_detector")
        self.declare_parameter("model", "yolo11n.pt")
        self.declare_parameter("image_topic", "/camera/image")
        self.declare_parameter("confidence", 0.45)
        self.declare_parameter("person_class", 0)
        self.declare_parameter("assumed_range_m", 8.0)
        try:
            from ultralytics import YOLO
        except ImportError as e:
            raise SystemExit("ultralytics not installed: pip install ultralytics") from e
        self.model = YOLO(self.get_parameter("model").value)
        self.pose = None
        self.pub = self.create_publisher(PointStamped, "/trecsar/detection", 10)
        self.create_subscription(PoseStamped, "/trecsar/ground_truth_pose", lambda m: setattr(self, "pose", m), 10)
        self.create_subscription(Image, self.get_parameter("image_topic").value, self.on_image, 2)

    def on_image(self, msg: Image):
        if self.pose is None:
            return
        res = self.model.predict(image_to_numpy(msg), conf=self.get_parameter("confidence").value, verbose=False)[0]
        cls = int(self.get_parameter("person_class").value)
        if not any(int(c) == cls for c in res.boxes.cls.tolist()):
            return
        q = self.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        rng = self.get_parameter("assumed_range_m").value
        out = PointStamped()
        out.header.frame_id = "world"
        out.header.stamp = msg.header.stamp
        out.point.x = self.pose.pose.position.x + rng * math.cos(yaw)
        out.point.y = self.pose.pose.position.y + rng * math.sin(yaw)
        self.pub.publish(out)


def main():
    rclpy.init()
    n = YoloDetector()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    n.destroy_node()
    rclpy.try_shutdown()
