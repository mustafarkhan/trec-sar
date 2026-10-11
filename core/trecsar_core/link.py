"""Radio link model: log-distance path loss plus terrain obstruction loss.

margin_db = Ptx + G - PL(d) - sum(obstruction along the straight line) - sensitivity

Defaults approximate a 2.4 GHz mesh radio (FSPL at 1 m ~ 40 dB). They are
placeholders: replace with a site survey or a calibrated model (e.g. ITU-R P.833
for vegetation, measured tunnel loss) before drawing operational conclusions.
"""

from __future__ import annotations

import numpy as np

from .terrain import Terrain


class LinkModel:
    def __init__(
        self,
        terrain: Terrain,
        ptx_dbm: float = 20.0,
        antenna_gain_db: float = 4.0,
        sensitivity_dbm: float = -90.0,
        pl_1m_db: float = 40.0,
        exponent: float = 2.2,
        samples: int = 64,
        threshold_db: float = 10.0,
    ):
        self.t = terrain
        self.budget = ptx_dbm + antenna_gain_db - sensitivity_dbm
        self.pl_1m = pl_1m_db
        self.n = exponent
        self.samples = samples
        self.threshold = threshold_db
        self._cache: dict[int, np.ndarray] = {}
        rows, cols = terrain.shape
        rr, cc = np.indices((rows, cols))
        self._rr = rr.ravel().astype(float)
        self._cc = cc.ravel().astype(float)
        self._rf_flat = terrain.rf_db_per_m.ravel()

    # -- single link -----------------------------------------------------------
    def margin(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        res = self.t.resolution
        d_cells = float(np.hypot(b[0] - a[0], b[1] - a[1]))
        d = max(d_cells * res, 1.0)
        k = max(int(np.ceil(d_cells * 2)), 1)
        ts = (np.arange(k) + 0.5) / k
        rr = np.clip(np.round(a[0] + ts * (b[0] - a[0])).astype(int), 0, self.t.shape[0] - 1)
        cc = np.clip(np.round(a[1] + ts * (b[1] - a[1])).astype(int), 0, self.t.shape[1] - 1)
        obstruction = float(self.t.rf_db_per_m[rr, cc].sum() * (d / k))
        return self.budget - (self.pl_1m + 10 * self.n * np.log10(d)) - obstruction

    # -- one transmitter to every cell (cached; nodes never move once placed) ----
    def margin_map(self, src: tuple[int, int]) -> np.ndarray:
        key = self.t.idx(src)
        if key in self._cache:
            return self._cache[key]
        res = self.t.resolution
        dr = self._rr - src[0]
        dc = self._cc - src[1]
        d_cells = np.hypot(dr, dc)
        d = np.maximum(d_cells * res, 1.0)
        k = self.samples
        ts = ((np.arange(k) + 0.5) / k)[:, None]
        rr = np.clip(np.round(src[0] + ts * dr[None, :]).astype(int), 0, self.t.shape[0] - 1)
        cc = np.clip(np.round(src[1] + ts * dc[None, :]).astype(int), 0, self.t.shape[1] - 1)
        rf = self.t.rf_db_per_m[rr, cc]  # (k, n_cells)
        obstruction = rf.sum(axis=0) * (d / k)
        m = self.budget - (self.pl_1m + 10 * self.n * np.log10(d)) - obstruction
        m = m.reshape(self.t.shape)
        self._cache[key] = m
        return m

    # -- network of base + relays ------------------------------------------------
    def connected_nodes(self, nodes: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Nodes reachable from nodes[0] (the base) through hops above threshold."""
        if not nodes:
            return []
        reached = [nodes[0]]
        frontier = [nodes[0]]
        rest = list(nodes[1:])
        while frontier:
            cur = frontier.pop()
            mm = self.margin_map(cur)
            still = []
            for n in rest:
                if mm[n] >= self.threshold:
                    reached.append(n)
                    frontier.append(n)
                else:
                    still.append(n)
            rest = still
        return reached

    def coverage(self, nodes: list[tuple[int, int]]) -> np.ndarray:
        """Best link margin to the network at every cell."""
        conn = self.connected_nodes(nodes)
        return np.max(np.stack([self.margin_map(n) for n in conn]), axis=0)
