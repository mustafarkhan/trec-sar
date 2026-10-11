"""TREC-SAR mission manager: wraps trecsar_core.MissionCore for a live robot.

Inputs
  /trecsar/ground_truth_pose  geometry_msgs/PoseStamped  robot pose, world frame (sim shortcut)
  /link/margin_db            std_msgs/Float32           radio link margin to the network
  /trecsar/detection          geometry_msgs/PointStamped person detected (world frame)
  /aerial/cue                geometry_msgs/PointStamped drone "possible person here"
Outputs
  navigate_to_pose           nav2_msgs/action/NavigateToPose (map frame = world - spawn)
  /relay/deploy              geometry_msgs/PointStamped     drop a relay here
  /trecsar/state              std_msgs/String
  /trecsar/report             std_msgs/String (JSON)         casualty report for the command post
  /trecsar/belief, /trecsar/coverage  nav_msgs/OccupancyGrid  for RViz
"""

from __future__ import annotations

import json

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PointStamped, PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import OccupancyGrid
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Float32, String

from trecsar_core.mission import MissionCore  # noqa: E402  (path set up by common)

from .common import get_world, grid_msg


class MissionManager(Node):
    def __init__(self):
        super().__init__("trecsar_mission_manager")
        self.declare_parameter("scenario", "forest_winter")
        self.declare_parameter("planner", "trecsar")
        self.declare_parameter("spawn_x", 27.0)
        self.declare_parameter("spawn_y", 15.0)
        self.declare_parameter("tick_hz", 1.0)
        self.declare_parameter("segment_m", 60.0)  # route handed to Nav2 in segments of this length
        scenario = self.get_parameter("scenario").value
        self.world = get_world(scenario)
        self.t = self.world.sc.terrain
        self.core = MissionCore(self.world, self.get_parameter("planner").value)
        self.spawn = (self.get_parameter("spawn_x").value, self.get_parameter("spawn_y").value)

        self.nav = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.goal_handle = None
        self.goal_reached = True
        self.dropping_until = None
        self.route: list[int] = []  # remaining waypoints (cells); last one is the mission goal
        self.segment_failures = 0
        self.segment_m = float(self.get_parameter("segment_m").value)
        # stuck detection: TREC-style escape (reverse + turn) when Nav2 recoveries cannot move the robot
        self.declare_parameter("stuck_after_s", 40.0)
        self.stuck_after = float(self.get_parameter("stuck_after_s").value)
        self.xy = None
        self.last_move = (None, 0.0)  # (xy, time)
        self.escape_until = None
        self.escape_count = 0
        self.pub_cmd = self.create_publisher(Twist, "/cmd_vel", 10)

        self.pub_state = self.create_publisher(String, "/trecsar/state", 10)
        self.pub_report = self.create_publisher(String, "/trecsar/report", 10)
        self.pub_relay = self.create_publisher(PointStamped, "/relay/deploy", 10)
        self.pub_belief = self.create_publisher(OccupancyGrid, "/trecsar/belief", 1)
        self.pub_cov = self.create_publisher(OccupancyGrid, "/trecsar/coverage", 1)

        self.create_subscription(PoseStamped, "/trecsar/ground_truth_pose", self.on_pose, 10)
        self.create_subscription(Float32, "/link/margin_db", self.on_link, 10)
        self.create_subscription(PointStamped, "/trecsar/detection", self.on_detection, 10)
        self.create_subscription(PointStamped, "/aerial/cue", self.on_cue, 10)
        self.create_timer(1.0 / self.get_parameter("tick_hz").value, self.tick)
        self.create_timer(2.0, self.publish_maps)
        self.get_logger().info(f"TREC-SAR mission manager up: {self.world.sc.title}, planner={self.core.planner_name}")

    # ---- helpers ------------------------------------------------------------------
    def now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def execute(self, cmds):
        for cmd, arg in cmds:
            if cmd == "goto":
                self.send_goal(arg)
            elif cmd == "drop_relay":
                self.cancel_goal()
                x, y = self.t.cell_to_xy(self.t.rc(arg))
                p = PointStamped()
                p.header.frame_id = "world"
                p.header.stamp = self.get_clock().now().to_msg()
                p.point.x, p.point.y = x, y
                self.pub_relay.publish(p)
                self.dropping_until = (self.now() + self.world.sc.mission.relay_drop_s, arg)
                self.get_logger().info(f"deploying relay at {x:.1f}, {y:.1f}")
            elif cmd == "report":
                x, y = self.t.cell_to_xy(self.t.rc(arg))
                rep = {
                    "type": "casualty_report",
                    "x_m": round(x, 1),
                    "y_m": round(y, 1),
                    "time_s": round(self.now(), 1),
                    "relays_used": self.world.sc.mission.relays - self.core.relays_left,
                }
                self.pub_report.publish(String(data=json.dumps(rep)))
                self.cancel_goal()
                self.get_logger().warn(f"CASUALTY REPORTED: {rep}")
            elif cmd == "state":
                self.pub_state.publish(String(data=arg))
                self.get_logger().info(f"state -> {arg}")

    def send_goal(self, cell: int):
        """Plan a terrain route to `cell` and hand it to Nav2 one segment at a time.

        The mission planner knows the whole site; Nav2 only knows what the lidar has
        seen. Feeding Nav2 waypoints ~segment_m apart along the terrain route keeps
        every goal inside Nav2's rolling costmap while the mission planner owns the
        long-range decision.
        """
        if not self.nav.wait_for_server(timeout_sec=0.5):
            self.get_logger().warn("Nav2 not ready yet")
            self.goal_reached = True
            return
        self.cancel_goal()  # one goal at a time
        start = self.core.pos if self.core.pos >= 0 else self.t.idx(self.t.base)
        _, pred = self.world.oracle.from_cell(start)
        path = self.world.oracle.path(pred, start, cell) or [start, cell]
        step = max(1, int(self.segment_m / self.t.resolution))
        self.route = path[step::step]
        if not self.route or self.route[-1] != cell:
            self.route.append(cell)
        self.segment_failures = 0
        self.goal_reached = False
        gx, gy = self.t.cell_to_xy(self.t.rc(cell))
        self.get_logger().info(f"goal ({gx:.0f}, {gy:.0f}) via {len(self.route)} segment(s)")
        self._send_next_segment()

    def _send_next_segment(self):
        if not self.route:
            self.goal_reached = True
            return
        x, y = self.t.cell_to_xy(self.t.rc(self.route[0]))
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x - self.spawn[0]
        goal.pose.pose.position.y = y - self.spawn[1]
        goal.pose.pose.orientation.w = 1.0
        fut = self.nav.send_goal_async(goal)
        fut.add_done_callback(self._accepted)

    def _accepted(self, fut):
        handle = fut.result()
        if not handle.accepted:
            self.route = []
            self.goal_reached = True
            return
        self.goal_handle = handle

        def done(f, h=handle):
            if self.goal_handle is not h:  # ignore results of preempted / cancelled goals
                return
            ok = f.result().status == GoalStatus.STATUS_SUCCEEDED
            final = self.route[-1] if self.route else None
            if not ok:
                self.get_logger().info(f"segment failed (status {f.result().status}); re-routing")
            if ok and self.route:
                self.route.pop(0)
                if self.route:
                    self._send_next_segment()
                    return
            elif not ok and final is not None and self.segment_failures < 3:
                # re-route from where the robot actually is, not from the stale plan
                self.segment_failures += 1
                failures = self.segment_failures
                self.send_goal(final)
                self.segment_failures = failures
                return
            self.route = []
            self.goal_reached = True

        handle.get_result_async().add_done_callback(done)

    def cancel_goal(self):
        self.route = []
        if self.goal_handle is not None:
            self.goal_handle.cancel_goal_async()
            self.goal_handle = None

    # ---- callbacks ----------------------------------------------------------------
    def on_pose(self, msg: PoseStamped):
        x, y = msg.pose.position.x, msg.pose.position.y
        self.xy = (x, y)
        ref, _t = self.last_move
        if ref is None or (x - ref[0]) ** 2 + (y - ref[1]) ** 2 > 0.5**2:
            self.last_move = ((x, y), self.now())
        r, c = self.t.xy_to_cell(x, y)
        self.core.on_pose(self.t.idx((r, c)))

    def _escape_step(self) -> bool:
        """Drive an escape manoeuvre if wedged. Returns True while it is in progress."""
        now = self.now()
        if self.escape_until is not None:
            start, end = self.escape_until
            tw = Twist()
            if now < start + 3.0:
                tw.linear.x = -0.4  # back away from the obstacle
            elif now < end:
                tw.angular.z = 1.0 if self.escape_count % 2 else -1.0  # then turn away
            else:
                self.escape_until = None
                self.pub_cmd.publish(Twist())
                self.last_move = (self.xy, now)
                self.goal_reached = True  # let the mission core issue a fresh goal
                return False
            self.pub_cmd.publish(tw)
            return True
        ref, t0 = self.last_move
        active = self.core.state in ("SEARCH", "LINK_RECOVERY", "REPORT", "RTH")
        if active and ref is not None and now - t0 > self.stuck_after:
            self.escape_count += 1
            self.get_logger().warn(f"no progress for {now - t0:.0f} s: escape manoeuvre #{self.escape_count}")
            self.cancel_goal()
            self.escape_until = (now, now + 5.0)
            return True
        return False

    def on_link(self, msg: Float32):
        self.execute(self.core.on_link(float(msg.data), self.now()))

    def on_detection(self, msg: PointStamped):
        cell = self.t.idx(self.t.xy_to_cell(msg.point.x, msg.point.y))
        self.execute(self.core.on_detection(cell))

    def on_cue(self, msg: PointStamped):
        self.core.on_aerial_cue(self.t.xy_to_cell(msg.point.x, msg.point.y))
        self.get_logger().info("aerial cue fused into the probability map")

    def tick(self):
        if self.dropping_until is None and self._escape_step():
            return
        if self.dropping_until is not None:
            until, cell = self.dropping_until
            if self.now() < until:
                return
            self.dropping_until = None
            self.core.on_relay_deployed(cell)
            self.execute(self.core.after_relay_continue())
            return
        self.execute(self.core.tick(self.now(), self.goal_reached))

    def publish_maps(self):
        origin = (-self.spawn[0], -self.spawn[1])
        p = self.core.belief.p
        self.pub_belief.publish(grid_msg(self, p / max(p.max(), 1e-12), self.t, "map", origin))
        cov = (self.core.coverage >= self.world.sc.mission.link_threshold_db).astype(float)
        self.pub_cov.publish(grid_msg(self, cov, self.t, "map", origin))


def main():
    rclpy.init()
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
