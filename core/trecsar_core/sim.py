"""Mission simulator: one robot, one missing person, one radio network.

Mission states (same names as the ROS 2 mission manager):

    SEARCH         follow the planner's path, look every step, update belief
    RELAY_DROP     stop and deploy a relay node (planned or reactive)
    LINK_RECOVERY  link lost for longer than failsafe_s -> drive to nearest covered cell
    REPORT         person detected -> make sure the operator gets the video
    RTH            battery reserve reached -> return to base
    DONE / FAILED

The key outcome is *time to report*: a detection only helps the casualty once a
human at the command post has seen it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .belief import Belief, prior_map
from .detector import Detector
from .link import LinkModel
from .planner import PLANNERS, PathOracle, PlanContext
from .scenarios import Scenario


@dataclass
class RunResult:
    planner: str
    scenario: str
    seed: int
    success: bool
    time_detect_s: float | None
    time_report_s: float | None
    out_of_link_s: float
    relays_used: int
    distance_m: float
    failsafe_events: int
    end_state: str
    trajectory: list[int] = field(default_factory=list)
    relays: list[int] = field(default_factory=list)
    casualty: int = -1
    events: list[tuple[float, str]] = field(default_factory=list)


class World:
    """Static, expensive-to-build pieces shared across Monte Carlo runs."""

    def __init__(self, sc: Scenario):
        self.sc = sc
        t = sc.terrain
        m = sc.mission
        self.oracle = PathOracle(t)
        self.link = LinkModel(t, threshold_db=m.link_threshold_db, **m.radio)
        self.detector = Detector(t, m.sense_radius_m, m.detect_pmax, m.detect_r0_m, m.canopy_occlusion)
        self.prior = prior_map(t, sc.person)
        lkp_truth = (t.lkp[0] + sc.truth_lkp_offset[0], t.lkp[1] + sc.truth_lkp_offset[1])
        self.truth_prior = prior_map(t, sc.person, lkp=lkp_truth) if sc.truth_lkp_offset != (0, 0) else self.prior
        d_base, _ = self.oracle.from_cell(t.idx(t.base))
        self.dist_to_base = d_base.copy()


def sample_casualty(world: World, rng: np.random.Generator) -> int:
    p = world.truth_prior.ravel()
    return int(rng.choice(p.size, p=p / p.sum()))


def run(world: World, planner_name: str, seed: int, record: bool = False) -> RunResult:
    sc, t, m = world.sc, world.sc.terrain, world.sc.mission
    rng = np.random.default_rng(seed)
    casualty = sample_casualty(world, rng)
    det_rng = np.random.default_rng(seed + 10_000)   # same detection luck across planners
    cue_rng = np.random.default_rng(seed + 20_000)

    planner = PLANNERS[planner_name](t, world.oracle, world.link)
    belief = Belief(world.prior, 1.0 - world.prior.sum())

    pos = t.idx(t.base)
    nodes = [t.base]
    coverage = world.link.coverage(nodes)
    relays_left = m.relays
    time = 0.0
    energy = m.battery_wh * m.cold_derate * 3600.0           # joules
    state = "SEARCH"
    path: list[int] = []
    planned_relay: int | None = None
    steps_since_plan = 0
    out_since: float | None = None
    out_total = 0.0
    failsafe_events = 0
    distance = 0.0
    t_detect = t_report = None
    events: list[tuple[float, str]] = []
    traj = [pos] if record else []
    relay_cells: list[int] = []
    cue_done = m.aerial_cue_time_s is None
    reactive_last_drop_d = -1e9
    prev_margin = None
    current_goal = None
    authorized_out = 0.0                      # planned link-loss window from the planner
    taboo: list[tuple[int, float]] = []      # (goal, expiry time) after a failsafe
    rr_all, cc_all = np.indices(t.shape)

    def taboo_disk(g, radius_cells=5):
        gr, gc = t.rc(g)
        return (((rr_all - gr) ** 2 + (cc_all - gc) ** 2) <= radius_cells ** 2).ravel()

    def log(msg):
        if record:
            events.append((round(float(time), 1), msg))

    def drop_relay(cell):
        nonlocal relays_left, coverage, time
        nodes.append(t.rc(cell))
        relay_cells.append(cell)
        relays_left -= 1
        coverage = world.link.coverage(nodes)
        time += m.relay_drop_s
        log(f"relay {m.relays - relays_left} deployed at {t.rc(cell)}")
        

    def nearest_covered():
        d, pred = world.oracle.from_cell(pos)
        ok = (coverage.ravel() >= m.link_threshold_db + 1.0) & np.isfinite(d)
        if not ok.any():
            return []
        g = int(np.argmin(np.where(ok, d, np.inf)))
        return world.oracle.path(pred, pos, g)

    # initial look from the start position
    idx, pod = world.detector.glimpse(t.rc(pos))
    belief.update_negative_sparse(idx, pod)

    while time < m.time_limit_s:
        # ---- aerial spotter cue -------------------------------------------------
        if not cue_done and time >= m.aerial_cue_time_s:
            cue_done = True
            if planner.uses_belief:
                cr, cc = t.rc(casualty)
                p_see = 0.8 * (1.0 - 0.9 * t.canopy[cr, cc])
                sig = m.aerial_cue_sigma_m / t.resolution
                if cue_rng.random() < p_see:
                    rc = (int(np.clip(cr + cue_rng.normal(0, sig), 0, t.shape[0] - 1)),
                          int(np.clip(cc + cue_rng.normal(0, sig), 0, t.shape[1] - 1)))
                    belief.update_cue(rc, sig, reliability=0.6)
                    log(f"aerial cue near {rc}")
                elif cue_rng.random() < m.aerial_false_cue_rate:
                    rc = t.rc(int(cue_rng.choice(t.n_cells, p=world.prior.ravel() / world.prior.sum())))
                    belief.update_cue(rc, sig, reliability=0.6)
                    log(f"aerial cue (false alarm) near {rc}")
                else:
                    log("drone saw nothing (canopy)")
                path = []

        # ---- decide -------------------------------------------------------------
        connected = coverage.ravel()[pos] >= m.link_threshold_db
        if state in ("SEARCH",):
            # battery reserve check (energy to drive home + 30 %)
            home_j = world.dist_to_base[pos] / m.robot_speed_mps * (m.idle_w + m.move_w_per_mps * m.robot_speed_mps * 1.5)
            if energy < 1.3 * home_j:
                state = "RTH"
                d, pred = world.oracle.from_cell(pos)
                path = world.oracle.path(pred, pos, t.idx(t.base))
                log("battery reserve -> RTH")
            elif not path or (planner.uses_belief and steps_since_plan >= 12 and planned_relay is None):
                blocked = None
                if taboo:
                    taboo[:] = [(g, exp) for g, exp in taboo if exp > time]
                    if taboo:
                        blocked = np.zeros(t.n_cells, bool)
                        for g, _ in taboo:
                            blocked |= taboo_disk(g)
                ctx = PlanContext(pos, belief.p, world.detector.value_map(belief.p), coverage,
                                  relays_left, m.link_threshold_db, m.link_buffer_db, blocked,
                                  m.robot_speed_mps, m.failsafe_s, tuple(nodes))
                plan = planner.plan(ctx)
                steps_since_plan = 0
                if plan is None or len(plan.path) < 2:
                    state = "RTH"
                    d, pred = world.oracle.from_cell(pos)
                    path = world.oracle.path(pred, pos, t.idx(t.base))
                    log("search plan exhausted -> RTH")
                else:
                    path = plan.path
                    current_goal = plan.goal
                    planned_relay = plan.relay_at
                    if plan.authorized_out_s > 0:
                        authorized_out = max(authorized_out, plan.authorized_out_s)
                        log(f"store-and-forward excursion authorised ({plan.authorized_out_s:.0f} s)")
                    if planned_relay is not None:
                        log(f"plan: goal {t.rc(plan.goal)} with relay at {t.rc(planned_relay)}")

        if state == "REPORT":
            if connected:
                t_report = time
                state = "DONE"
                log("video received at command post — casualty reported")
                break
            if not path:
                path = nearest_covered()
                if not path:
                    state = "FAILED"
                    break

        if state == "LINK_RECOVERY" and connected:
            state = "SEARCH"
            path = []
            out_since = None
            log("link restored")

        if state == "RTH" and pos == t.idx(t.base):
            state = "FAILED" if t_report is None else "DONE"
            break

        # ---- move one cell ------------------------------------------------------
        if path and path[0] == pos:
            path = path[1:]
        if not path:
            if state in ("RTH", "LINK_RECOVERY"):
                state = "FAILED"
                break
            continue
        nxt = path.pop(0)
        steps_since_plan += 1
        prev_pos, prev_margin = pos, coverage.ravel()[pos]
        d_step = world.oracle.g[pos, nxt]
        if d_step == 0:     # not adjacent (should not happen) — replan
            path = []
            continue
        dt = d_step / m.robot_speed_mps
        tc = 0.5 * (t.cost.ravel()[pos] + t.cost.ravel()[nxt])
        energy -= dt * (m.idle_w + m.move_w_per_mps * m.robot_speed_mps * tc)
        time += dt
        distance += float(np.hypot(*np.subtract(t.rc(pos), t.rc(nxt)))) * t.resolution
        pos = nxt
        if record:
            traj.append(pos)
        if energy <= 0:
            state = "FAILED"
            log("battery depleted")
            break

        # ---- relays -------------------------------------------------------------
        if planned_relay is not None and pos == planned_relay and relays_left > 0:
            drop_relay(pos)
            planned_relay = None
            path = []                       # replan with the extended coverage
        elif planner.reactive_breadcrumbs and relays_left > 0 and state == "SEARCH":
            # SubT-style breadcrumb: signal fell through the warning band -> drop at the
            # last cell that was still well connected (robot backs up one cell).
            mg = coverage.ravel()[pos]
            band = m.link_threshold_db + m.link_buffer_db
            if mg < band and prev_margin is not None and prev_margin >= m.link_threshold_db \
                    and distance - reactive_last_drop_d > 60.0:
                drop_relay(prev_pos if mg < m.link_threshold_db else pos)
                reactive_last_drop_d = distance

        # ---- link bookkeeping ---------------------------------------------------
        connected = coverage.ravel()[pos] >= m.link_threshold_db
        if not connected:
            out_total += dt
            out_since = time if out_since is None else out_since
            if state == "SEARCH" and time - out_since > max(m.failsafe_s, authorized_out):
                state = "LINK_RECOVERY"
                failsafe_events += 1
                if current_goal is not None:
                    taboo.append((current_goal, time + 600.0))
                planned_relay = None
                path = nearest_covered()
                log("link lost > failsafe -> return to last good link")
        else:
            out_since = None
            authorized_out = 0.0

        # ---- sense --------------------------------------------------------------
        if state in ("SEARCH", "LINK_RECOVERY", "RTH") and t_detect is None:
            idx, pod = world.detector.glimpse(t.rc(pos))
            hit = np.nonzero(idx == casualty)[0]
            if hit.size and det_rng.random() < pod[hit[0]]:
                t_detect = time
                state = "REPORT"
                path = []
                log(f"PERSON DETECTED at {t.rc(casualty)} (robot at {t.rc(pos)})")
            else:
                belief.update_negative_sparse(idx, pod)

    if state not in ("DONE", "FAILED"):
        state = "TIMEOUT"
    return RunResult(planner_name, sc.key, seed, t_report is not None, t_detect, t_report,
                     out_total, m.relays - relays_left, distance, failsafe_events, state,
                     traj, relay_cells, casualty, events)
