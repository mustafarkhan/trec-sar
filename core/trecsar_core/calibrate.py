"""Online radio-model calibration from the link measurements the robot already gets.

Every radio reports received signal strength. Each reading is one equation of the
link model

    margin = budget - PL(1 m) - 10 n log10(d) - sum_k a_k * L_k

where L_k is how many metres of terrain class k the straight line from the node
to the robot crosses and a_k is that class's attenuation in dB/m. The unknowns
(n, a_1 .. a_K) enter linearly, so a Bayesian linear regression with the site's
prior radio parameters as the prior mean gives a closed-form posterior after
every reading. Nothing is learned from scratch: with few readings the model stays
at the prior, and it moves only as far as the measurements justify.

The planner then predicts coverage — and decides where relays go and how long a
planned link-loss window lasts — from the calibrated model instead of the
placeholder numbers. Background: log-distance path loss with per-class
obstruction loss (ITU-R P.833 for vegetation), and online channel estimation from
robot-collected samples (Malmirchegini & Mostofi, IJRR 2012; Fink & Kumar, ICRA
2010). See docs/RESEARCH.md.
"""

from __future__ import annotations

import numpy as np

from .link import LinkModel


class RadioCalibrator:
    def __init__(
        self,
        prior: LinkModel,
        noise_db: float = 4.0,
        exponent_sd: float = 0.4,
        rel_sd: float = 0.7,
        min_sd_db_per_m: float = 0.02,
        sensitivity_floor_db: float = 0.0,
    ):
        self.prior = prior
        rf = np.round(prior.rf, 4)
        self.values, inv = np.unique(rf, return_inverse=True)
        self.cls = inv.reshape(rf.shape)
        self.K = len(self.values)
        self.noise = noise_db
        self.floor = sensitivity_floor_db
        x0 = np.concatenate([[prior.n], self.values])
        sd = np.concatenate([[exponent_sd], np.maximum(rel_sd * self.values, min_sd_db_per_m)])
        self.x0 = x0
        self.P = np.diag(1.0 / sd**2)  # posterior precision (information form)
        self.b = self.P @ x0
        self.n_obs = 0
        self._mean = x0.copy()

    # -- features --------------------------------------------------------------
    def features(self, a: tuple[int, int], b: tuple[int, int]) -> np.ndarray:
        """Row of the design matrix for a link a -> b (same sampling as LinkModel.margin)."""
        t = self.prior.t
        d_cells = float(np.hypot(b[0] - a[0], b[1] - a[1]))
        d = max(d_cells * t.resolution, 1.0)
        k = max(int(np.ceil(d_cells * 2)), 1)
        ts = (np.arange(k) + 0.5) / k
        rr = np.clip(np.round(a[0] + ts * (b[0] - a[0])).astype(int), 0, t.shape[0] - 1)
        cc = np.clip(np.round(a[1] + ts * (b[1] - a[1])).astype(int), 0, t.shape[1] - 1)
        lengths = np.bincount(self.cls[rr, cc], minlength=self.K) * (d / k)
        return np.concatenate([[-10.0 * np.log10(d)], -lengths])

    def _offset(self) -> float:
        return self.prior.budget - self.prior.pl_1m

    # -- update ----------------------------------------------------------------
    def observe(self, node: tuple[int, int], robot: tuple[int, int], margin_db: float) -> bool:
        """Add one signal-strength reading. Readings below the receiver floor carry no value."""
        if margin_db <= self.floor:
            return False
        a = self.features(node, robot)
        y = margin_db - self._offset()
        w = 1.0 / self.noise**2
        self.P += w * np.outer(a, a)
        self.b += w * a * y
        self.n_obs += 1
        self._mean = None
        return True

    @property
    def mean(self) -> np.ndarray:
        if self._mean is None:
            self._mean = np.linalg.solve(self.P, self.b)
        return self._mean

    @property
    def sd(self) -> np.ndarray:
        return np.sqrt(np.diag(np.linalg.inv(self.P)))

    def estimate(self) -> tuple[float, dict[float, float]]:
        """(path-loss exponent, {prior dB/m -> calibrated dB/m}) clipped to physical ranges."""
        m = self.mean
        n = float(np.clip(m[0], 1.6, 4.5))
        att = np.maximum(m[1:], 0.0)
        return n, dict(zip(self.values.tolist(), att.tolist()))

    def model(self) -> LinkModel:
        n, _ = self.estimate()
        att = np.maximum(self.mean[1:], 0.0)
        return self.prior.variant(exponent=n, rf_map=att[self.cls])

    def predict(self, node: tuple[int, int], robot: tuple[int, int]) -> tuple[float, float]:
        """Predicted margin and its standard deviation (model uncertainty, without shadowing)."""
        a = self.features(node, robot)
        mu = float(a @ self.mean) + self._offset()
        var = float(a @ np.linalg.solve(self.P, a))
        return mu, float(np.sqrt(max(var, 0.0)))
