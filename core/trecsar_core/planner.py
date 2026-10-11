"""Search planners.

Three policies are compared:

* ``LawnmowerPlanner``  — systematic coverage sweep (classic SAR practice) with
  reactive relay "breadcrumbs" dropped when the link gets weak.
* ``GreedyBayesPlanner`` — goes where expected probability-of-detection per metre
  is highest (probability-driven search), same reactive breadcrumbs.
* ``TrecSarPlanner``     — the contribution of this project: chooses the next
  search goal and *where to place a relay* jointly, scoring each candidate by
  expected detection per metre **subject to the operator still receiving video
  when the person is found**. Relays are placed proactively at the last
  well-connected point on the path to a high-value but out-of-link area.

Reactive breadcrumb dropping is the approach popularised by DARPA SubT teams;
TREC-SAR's difference is that relay placement is driven by the probability map,
not by signal strength alone.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .terrain import Terrain

_NEI = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def build_graph(t: Terrain) -> csr_matrix:
    """8-connected grid graph; edge weight = metres x mean terrain cost."""
    rows, cols = t.shape
    idx = np.arange(rows * cols).reshape(rows, cols)
    src, dst, w = [], [], []
    for dr, dc in _NEI:
        r0, r1 = max(0, -dr), rows - max(0, dr)
        c0, c1 = max(0, -dc), cols - max(0, dc)
        a = idx[r0:r1, c0:c1]
        b = idx[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
        ca = t.cost[r0:r1, c0:c1]
        cb = t.cost[r0 + dr:r1 + dr, c0 + dc:c1 + dc]
        ok = np.isfinite(ca) & np.isfinite(cb)
        if dr and dc:   # no corner cutting past impassable cells
            ok &= np.isfinite(t.cost[r0 + dr:r1 + dr, c0:c1]) & np.isfinite(t.cost[r0:r1, c0 + dc:c1 + dc])
        step = np.hypot(dr, dc) * t.resolution
        src.append(a[ok]); dst.append(b[ok]); w.append(step * 0.5 * (ca[ok] + cb[ok]))
    n = rows * cols
    return csr_matrix((np.concatenate(w), (np.concatenate(src), np.concatenate(dst))), shape=(n, n))


class PathOracle:
    """Shortest paths on the terrain graph (cached per source cell)."""

    def __init__(self, t: Terrain):
        self.t = t
        self.g = build_graph(t)
        self._cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def from_cell(self, src_idx: int) -> tuple[np.ndarray, np.ndarray]:
        if src_idx not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            d, pred = dijkstra(self.g, indices=src_idx, return_predecessors=True)
            self._cache[src_idx] = (d, pred)
        return self._cache[src_idx]

    @staticmethod
    def path(pred: np.ndarray, src_idx: int, dst_idx: int) -> list[int]:
        out = [dst_idx]
        cur = dst_idx
        while cur != src_idx:
            cur = int(pred[cur])
            if cur < 0:
                return []
            out.append(cur)
        out.reverse()
        return out


@dataclass
class Plan:
    goal: int
    path: list[int]               # flat indices, path[0] == current cell
    relay_at: int | None = None   # flat index on the path where a relay is to be dropped
    note: str = ""
    authorized_out_s: float = 0.0  # planned link-loss window (store-and-forward excursion)


@dataclass
class PlanContext:
    pos: int
    belief_p: np.ndarray
    value: np.ndarray             # detector.value_map(belief)
    coverage: np.ndarray          # link margin map of the connected network
    relays_left: int
    link_threshold: float
    link_buffer: float
    blocked: np.ndarray | None = None     # flat bool mask of goals to avoid (recent failsafe)
    speed_mps: float = 2.22
    failsafe_s: float = 45.0
    nodes: tuple = ()                     # deployed radio nodes (base first)


class BasePlanner:
    name = "base"
    reactive_breadcrumbs = True
    uses_belief = True

    def __init__(self, t: Terrain, oracle: PathOracle, link=None):
        self.t = t
        self.oracle = oracle
        self.link = link

    def plan(self, ctx: PlanContext) -> Plan | None:
        raise NotImplementedError


class LawnmowerPlanner(BasePlanner):
    """Boustrophedon sweep of a lattice around the LKP, snapped to passable ground."""
    name = "lawnmower"
    uses_belief = False

    def __init__(self, t, oracle, link=None, spacing_m: float = 40.0, radius_m: float = 420.0):
        super().__init__(t, oracle, link)
        s = max(1, int(round(spacing_m / t.resolution)))
        R = int(round(radius_m / t.resolution))
        lr, lc = t.lkp
        rows, cols = t.shape
        pas = t.passable
        wps = []
        r_vals = list(range(max(0, lr - R), min(rows, lr + R + 1), s))
        for i, r in enumerate(r_vals):
            c_vals = list(range(max(0, lc - R), min(cols, lc + R + 1), s))
            if i % 2:
                c_vals.reverse()
            for c in c_vals:
                snapped = self._snap(pas, r, c, s // 2 + 1)
                if snapped is not None and (not wps or wps[-1] != snapped):
                    wps.append(snapped)
        # dedupe while keeping order
        seen, self.waypoints = set(), []
        for w in wps:
            if w not in seen:
                seen.add(w)
                self.waypoints.append(w)
        self.k = 0

    @staticmethod
    def _snap(pas, r, c, rad):
        rows, cols = pas.shape
        if pas[r, c]:
            return r * cols + c
        best, bd = None, 1e9
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols and pas[rr, cc]:
                    d = dr * dr + dc * dc
                    if d < bd:
                        best, bd = rr * cols + cc, d
        return best

    def plan(self, ctx):
        d, pred = self.oracle.from_cell(ctx.pos)
        while self.k < len(self.waypoints):
            g = self.waypoints[self.k]
            self.k += 1
            if np.isfinite(d[g]) and g != ctx.pos:
                return Plan(g, self.oracle.path(pred, ctx.pos, g), note="sweep")
        return None


class GreedyBayesPlanner(BasePlanner):
    name = "greedy_bayes"
    n_candidates = 40
    travel_offset_m = 60.0

    def _candidates(self, ctx, d):
        v = np.where(np.isfinite(d.reshape(self.t.shape)), ctx.value, 0.0).ravel()
        v[ctx.pos] = 0.0
        if ctx.blocked is not None:
            v[ctx.blocked] = 0.0
        k = min(self.n_candidates, v.size - 1)
        cand = np.argpartition(-v, k)[:k]
        cand = cand[v[cand] > 0]
        return cand, v

    def plan(self, ctx):
        d, pred = self.oracle.from_cell(ctx.pos)
        cand, v = self._candidates(ctx, d)
        if cand.size == 0:
            return None
        score = v[cand] / (d[cand] + self.travel_offset_m)
        g = int(cand[np.argmax(score)])
        return Plan(g, self.oracle.path(pred, ctx.pos, g), note="max POD/m")


class TrecSarPlanner(GreedyBayesPlanner):
    name = "trecsar"
    reactive_breadcrumbs = False
    relay_cost = 1.0              # weight of plans that consume a relay (tuned on seeds 100-159)
    chain_cost = 0.8              # a relay that only extends the chain (goal still not covered)
    out_of_link_penalty = 1.0     # bounded excursion: allowed only if it fits the failsafe budget
    excursion_budget = 0.4        # fraction of failsafe_s the outbound leg may spend out of link
    store_forward_penalty = 1.0   # commit to a planned link-loss window instead of a relay
    store_forward_always = True
    min_relay_spacing_m = 30.0

    def _out_of_link_time(self, path, cov, thr, speed):
        cost = self.t.cost.ravel()
        out = [c for c in path if cov[c] < thr]
        return len(out) * self.t.resolution * float(np.mean(cost[out]) if out else 0) / speed

    def _far_from_nodes(self, cell, nodes):
        r, c = self.t.rc(cell)
        return all(np.hypot(r - a, c - b) * self.t.resolution >= self.min_relay_spacing_m for a, b in nodes)

    def plan(self, ctx):
        d, pred = self.oracle.from_cell(ctx.pos)
        cand, v = self._candidates(ctx, d)
        if cand.size == 0:
            return None
        cov = ctx.coverage.ravel()
        thr = ctx.link_threshold
        nodes = ctx.nodes
        best = None
        for g in cand[np.argsort(-v[cand] / (d[cand] + self.travel_offset_m))]:
            g = int(g)
            base = v[g] / (d[g] + self.travel_offset_m)
            if best is not None and base <= best[0]:
                break                   # sorted: nothing below can beat the incumbent
            if cov[g] >= thr:
                best = (base, Plan(g, self.oracle.path(pred, ctx.pos, g), note="in-link"))
                continue
            path = self.oracle.path(pred, ctx.pos, g)
            if not path:
                continue
            options = []
            # (a) bounded excursion: short enough to come back before the failsafe fires
            if self._out_of_link_time(path, cov, thr, ctx.speed_mps) <= self.excursion_budget * ctx.failsafe_s:
                options.append((base * self.out_of_link_penalty, Plan(g, path, note="bounded excursion")))
            # (b) proactive relay at the last well-connected cell on the way
            if ctx.relays_left > 0:
                good = [i for i, c in enumerate(path) if cov[c] >= thr + ctx.link_buffer]
                if good and self._far_from_nodes(path[good[-1]], nodes):
                    drop = path[good[-1]]
                    if self.link.margin(self.t.rc(drop), self.t.rc(g)) >= thr:
                        options.append((base * self.relay_cost, Plan(g, path, relay_at=drop, note="planned relay")))
                    else:
                        options.append((base * self.chain_cost, Plan(g, path, relay_at=drop, note="relay chain")))
            # (c) store-and-forward: out of relays, so plan the link loss explicitly —
            #     search autonomously, keep the evidence, come back to report.
            if self.store_forward_always or (ctx.relays_left == 0 and not options):
                t_out = self._out_of_link_time(path, cov, thr, ctx.speed_mps)
                options.append((base * self.store_forward_penalty,
                                Plan(g, path, note="store-and-forward", authorized_out_s=2.5 * t_out + 60.0)))
            for s, p in options:
                if best is None or s > best[0]:
                    best = (s, p)
        if best is not None:
            return best[1]
        # Nothing feasible among the top candidates: search the best covered area instead.
        v_in = np.where(cov >= thr, v, 0.0)
        v_in[ctx.pos] = 0.0
        if v_in.max() > 0:
            score = np.where(np.isfinite(d), v_in / (d + self.travel_offset_m), 0.0)
            g = int(np.argmax(score))
            return Plan(g, self.oracle.path(pred, ctx.pos, g), note="best covered area")
        # Last resort: behave like the greedy planner and let the failsafe protect us.
        return super().plan(ctx)


class GreedyStoreForwardPlanner(GreedyBayesPlanner):
    """Ablation: greedy goal choice + planned link-loss windows, but reactive relays.

    Separates how much of TREC-SAR's gain comes from *planning the link loss* versus
    from *placing relays where the probability is*.
    """
    name = "greedy_sf"

    def plan(self, ctx):
        p = super().plan(ctx)
        if p is None:
            return None
        cov = ctx.coverage.ravel()
        out = [c for c in p.path if cov[c] < ctx.link_threshold]
        if out:
            t_out = len(out) * self.t.resolution * float(np.mean(self.t.cost.ravel()[out])) / ctx.speed_mps
            p.authorized_out_s = 2.5 * t_out + 60.0
            p.note = "greedy + store-and-forward"
        return p


PLANNERS = {p.name: p for p in (LawnmowerPlanner, GreedyBayesPlanner, GreedyStoreForwardPlanner, TrecSarPlanner)}
