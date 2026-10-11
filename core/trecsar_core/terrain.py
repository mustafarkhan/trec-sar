"""Grid terrain model shared by the planner, link model, detector and simulator.

Every layer is a 2D numpy array of shape (rows, cols). One cell = `resolution`
metres. Coordinates are (row, col); flat indices are row * cols + col.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Terrain:
    name: str
    resolution: float                 # metres per cell
    cost: np.ndarray                  # traversal multiplier (>=1); np.inf = impassable
    rf_db_per_m: np.ndarray           # extra radio attenuation per metre inside this cell
    canopy: np.ndarray                # 0..1 occlusion for camera/thermal detection
    affinity: np.ndarray              # lost-person location weight (0 = never there)
    base: tuple[int, int]             # incident command post / radio base station
    lkp: tuple[int, int]              # last known point of the missing person
    labels: dict[str, np.ndarray] = field(default_factory=dict)  # named masks for plots/docs

    @property
    def shape(self) -> tuple[int, int]:
        return self.cost.shape

    @property
    def n_cells(self) -> int:
        return int(self.cost.size)

    @property
    def passable(self) -> np.ndarray:
        return np.isfinite(self.cost)

    def idx(self, rc: tuple[int, int]) -> int:
        return int(rc[0] * self.shape[1] + rc[1])

    def rc(self, idx: int) -> tuple[int, int]:
        return divmod(int(idx), self.shape[1])

    # Grid <-> world frame used by Gazebo/ROS: x east, y north, origin at the
    # south-west corner, cell centres at half-resolution offsets.
    def cell_to_xy(self, rc: tuple[int, int]) -> tuple[float, float]:
        r, c = rc
        return (c + 0.5) * self.resolution, (self.shape[0] - 1 - r + 0.5) * self.resolution

    def xy_to_cell(self, x: float, y: float) -> tuple[int, int]:
        c = int(np.clip(np.floor(x / self.resolution), 0, self.shape[1] - 1))
        r = int(np.clip(self.shape[0] - 1 - np.floor(y / self.resolution), 0, self.shape[0] - 1))
        return r, c

    def validate(self) -> None:
        shp = self.cost.shape
        for name in ("rf_db_per_m", "canopy", "affinity"):
            arr = getattr(self, name)
            if arr.shape != shp:
                raise ValueError(f"layer {name} has shape {arr.shape}, expected {shp}")
        if not np.all((self.canopy >= 0) & (self.canopy <= 1)):
            raise ValueError("canopy must be within 0..1")
        if np.any(self.rf_db_per_m < 0) or np.any(self.affinity < 0):
            raise ValueError("rf attenuation and affinity must be non-negative")
        finite = self.cost[np.isfinite(self.cost)]
        if finite.size and finite.min() < 1.0:
            raise ValueError("traversal cost multipliers must be >= 1")
        for name, p in (("base", self.base), ("lkp", self.lkp)):
            if not self.passable[p]:
                raise ValueError(f"{name} {p} is not on passable ground")
