"""Sensor model: probability of detection (POD) for a thermal + RGB camera mast.

POD(range, cell) = pmax * exp(-(range / r0)^2) * (1 - occlusion * canopy[cell])
and zero when the line of sight crosses impassable ground (rock, walls, tanks).

In the 3D simulator this is replaced by a real detector (YOLO) on rendered
images; this analytic model is what the planner uses to reason about where to
look, and what the 2D Monte Carlo uses as ground truth.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve

from .terrain import Terrain


class Detector:
    def __init__(self, t: Terrain, sense_radius_m: float, pmax: float, r0_m: float, occlusion: float):
        self.t = t
        self.pmax = pmax
        self.occlusion = occlusion
        R = int(np.ceil(sense_radius_m / t.resolution))
        dr, dc = np.mgrid[-R:R + 1, -R:R + 1]
        dist = np.hypot(dr, dc)
        keep = dist <= R
        self.dr, self.dc = dr[keep], dc[keep]
        d_m = dist[keep] * t.resolution
        self.base_pod = pmax * np.exp(-(d_m / r0_m) ** 2)
        # line-of-sight sample offsets for every footprint cell, padded to equal length
        L = 2 * R + 1
        ts = (np.arange(1, L) / L)[None, :]
        self.los_r = np.round(self.dr[:, None] * ts).astype(int)
        self.los_c = np.round(self.dc[:, None] * ts).astype(int)
        # convolution kernel for planning (no line-of-sight term)
        k = np.zeros((2 * R + 1, 2 * R + 1))
        k[self.dr + R, self.dc + R] = self.base_pod
        self.kernel = k
        self._vis = (1.0 - occlusion * t.canopy)

    def glimpse(self, pos: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
        """Return (flat cell indices, POD) for one look from `pos`."""
        rows, cols = self.t.shape
        r = pos[0] + self.dr
        c = pos[1] + self.dc
        inb = (r >= 0) & (r < rows) & (c >= 0) & (c < cols)
        lr = np.clip(pos[0] + self.los_r, 0, rows - 1)
        lc = np.clip(pos[1] + self.los_c, 0, cols - 1)
        clear = self.t.passable[lr, lc].all(axis=1)
        ok = inb & clear
        r, c = r[ok], c[ok]
        pod = self.base_pod[ok] * self._vis[r, c] * self.t.passable[r, c]
        return r * cols + c, pod

    def value_map(self, p: np.ndarray) -> np.ndarray:
        """Expected probability detected by one glimpse from each cell (planning heuristic)."""
        return convolve(p * self._vis, self.kernel, mode="constant", cval=0.0)
