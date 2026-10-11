"""Event-driven mission logic for a live robot (used by the ROS 2 mission manager).

`sim.py` is the fast batch evaluator; `MissionCore` is the same decision logic
reshaped for a robot that reports its pose, link margin and detections as they
happen. It never imports ROS, so it is unit-tested here and wrapped by a thin
rclpy node in ros2_ws/src/trecsar_mission.

Outputs are *commands* the wrapper executes:
    ("goto", cell)         send a navigation goal (flat index)
    ("drop_relay", cell)   deploy a relay node here
    ("report", cell)       push the detection + snapshot to the command post
    ("state", name)        state changed (for logging / UI)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .belief import Belief
from .planner import PLANNERS, PlanContext
from .sim import World


@dataclass
class MissionCore:
    world: World
    planner_name: str = "trecsar"
    state: str = "SEARCH"
    nodes: list = field(default_factory=list)
    relays_left: int = 0
    pos: int = -1
    margin_db: float = 99.0
    _plan_goal: int | None = None
    _relay_at: int | None = None
    _authorized_out: float = 0.0
    _out_since: float | None = None
    _detected_at: int | None = None
    _taboo: list = field(default_factory=list)

    def __post_init__(self):
        t = self.world.sc.terrain
        self.t = t
        self.m = self.world.sc.mission
        self.planner = PLANNERS[self.planner_name](t, self.world.oracle, self.world.link)
        self.belief = Belief(self.world.prior, 1.0 - self.world.prior.sum())
        self.nodes = [t.base]
        self.relays_left = self.m.relays
        self.coverage = self.world.link.coverage(self.nodes)

    # ---- inputs -------------------------------------------------------------------
    def on_pose(self, cell: int) -> None:
        if cell != self.pos:
            self.pos = cell
            idx, pod = self.world.detector.glimpse(self.t.rc(cell))
            if self.state in ("SEARCH", "LINK_RECOVERY"):
                self.belief.update_negative_sparse(idx, pod)

    def on_link(self, margin_db: float, now: float) -> list:
        self.margin_db = margin_db
        cmds = []
        if margin_db >= self.m.link_threshold_db:
            self._out_since = None
            self._authorized_out = 0.0
            if self.state == "LINK_RECOVERY":
                cmds += self._set("SEARCH")
                self._plan_goal = None
            if self.state == "REPORT":
                cmds += [("report", self._detected_at)] + self._set("DONE")
        else:
            self._out_since = now if self._out_since is None else self._out_since
            if self.state == "SEARCH" and now - self._out_since > max(self.m.failsafe_s, self._authorized_out):
                if self._plan_goal is not None:
                    self._taboo.append((self._plan_goal, now + 600.0))
                cmds += self._set("LINK_RECOVERY") + self._goto_nearest_covered()
        return cmds

    def on_detection(self, casualty_cell: int) -> list:
        if self.state in ("DONE", "REPORT"):
            return []
        self._detected_at = casualty_cell
        if self.margin_db >= self.m.link_threshold_db:
            return [("report", casualty_cell)] + self._set("DONE")
        return self._set("REPORT") + self._goto_nearest_covered()

    def on_aerial_cue(self, rc: tuple[int, int]) -> None:
        sig = self.m.aerial_cue_sigma_m / self.t.resolution
        self.belief.update_cue(rc, sig, reliability=0.6)
        self._plan_goal = None  # force a replan

    def on_relay_deployed(self, cell: int) -> None:
        self.nodes.append(self.t.rc(cell))
        self.relays_left -= 1
        self.coverage = self.world.link.coverage(self.nodes)
        self._relay_at = None
        self._plan_goal = None

    # ---- decision tick ------------------------------------------------------------
    def tick(self, now: float, goal_reached: bool) -> list:
        if self.state != "SEARCH" or self.pos < 0:
            return []
        cmds = []
        if self._relay_at is not None and self.pos == self._relay_at and self.relays_left > 0:
            return [("drop_relay", self.pos)]
        if self._plan_goal is None or goal_reached:
            self._taboo = [(g, e) for g, e in self._taboo if e > now]
            blocked = None
            if self._taboo:
                rr, cc = np.indices(self.t.shape)
                blocked = np.zeros(self.t.n_cells, bool)
                for g, _ in self._taboo:
                    gr, gc = self.t.rc(g)
                    blocked |= (((rr - gr) ** 2 + (cc - gc) ** 2) <= 25).ravel()
            ctx = PlanContext(
                self.pos,
                self.belief.p,
                self.world.detector.value_map(self.belief.p),
                self.coverage,
                self.relays_left,
                self.m.link_threshold_db,
                self.m.link_buffer_db,
                blocked,
                self.m.robot_speed_mps,
                self.m.failsafe_s,
                tuple(self.nodes),
            )
            plan = self.planner.plan(ctx)
            if plan is None:
                return self._set("RTH") + [("goto", self.t.idx(self.t.base))]
            self._plan_goal = plan.goal
            self._relay_at = plan.relay_at
            self._authorized_out = max(self._authorized_out, plan.authorized_out_s)
            cmds.append(("goto", plan.relay_at if plan.relay_at is not None else plan.goal))
        return cmds

    def after_relay_continue(self) -> list:
        """Called by the wrapper once a relay is down: continue to the original goal."""
        return [("goto", self._plan_goal)] if self._plan_goal is not None else []

    # ---- helpers ------------------------------------------------------------------
    def _set(self, s: str) -> list:
        if s == self.state:
            return []
        self.state = s
        return [("state", s)]

    def _goto_nearest_covered(self) -> list:
        d, _ = self.world.oracle.from_cell(self.pos)
        ok = (self.coverage.ravel() >= self.m.link_threshold_db + 1.0) & np.isfinite(d)
        if not ok.any():
            return [("goto", self.t.idx(self.t.base))]
        return [("goto", int(np.argmin(np.where(ok, d, np.inf))))]
