"""Bayesian probability-of-area (POA) map, in the tradition of search theory
(Koopman, Stone) and operational tools such as SAROPS.

The map holds P(person in cell). Mass outside the modelled area is kept as
`p_row` ("rest of world") so that unsuccessful search correctly shifts belief
both between cells and out of the area.
"""

from __future__ import annotations

import numpy as np

from .scenarios import LostPersonProfile
from .terrain import Terrain


def prior_map(t: Terrain, person: LostPersonProfile, lkp: tuple[int, int] | None = None) -> np.ndarray:
    """Log-normal distance-from-LKP ring weighted by terrain affinity.

    Euclidean distance is used (people do not travel optimal paths). The ring
    density is divided by circumference so that the *distance* distribution — not
    the per-cell density — is log-normal.
    """
    lkp = lkp or t.lkp
    r, c = np.indices(t.shape)
    d = np.hypot(r - lkp[0], c - lkp[1]) * t.resolution
    d = np.maximum(d, t.resolution / 2)
    mu = np.log(person.median_distance_m)
    s = person.sigma_log
    pdf_d = np.exp(-((np.log(d) - mu) ** 2) / (2 * s * s)) / (d * s * np.sqrt(2 * np.pi))
    w = pdf_d / (2 * np.pi * d) * t.affinity * t.passable
    w = np.nan_to_num(w)
    total = w.sum()
    if total <= 0:
        raise ValueError("prior is empty — check affinity / passable layers")
    return w / total * person.p_in_area


class Belief:
    def __init__(self, prior: np.ndarray, p_row: float):
        self.p = prior.astype(float).copy()
        self.p_row = float(p_row)

    @classmethod
    def from_scenario(cls, t: Terrain, person: LostPersonProfile) -> Belief:
        prior = prior_map(t, person)
        return cls(prior, 1.0 - prior.sum())

    @property
    def total(self) -> float:
        return float(self.p.sum() + self.p_row)

    def update_negative(self, pod: np.ndarray) -> float:
        """Searched with per-cell probability of detection `pod`, found nothing.

        Returns the probability of success (POS) that this glimpse had.
        """
        pos = float((self.p * pod).sum())
        self.p *= 1.0 - pod
        norm = self.p.sum() + self.p_row
        self.p /= norm
        self.p_row /= norm
        return pos

    def update_negative_sparse(self, flat_idx: np.ndarray, pod: np.ndarray) -> float:
        """Same as update_negative but only for the cells a glimpse covered."""
        flat = self.p.reshape(-1)
        old = flat[flat_idx]
        pos = float((old * pod).sum())
        flat[flat_idx] = old * (1.0 - pod)
        norm = flat.sum() + self.p_row
        self.p /= norm
        self.p_row /= norm
        return pos

    def update_cue(self, cue_rc: tuple[int, int], sigma_cells: float, reliability: float) -> None:
        """Fuse a noisy 'possible person here' cue from the aerial spotter.

        Likelihood = reliability * Gaussian(cue | person cell) + (1 - reliability),
        i.e. the cue is either a true (noisy) detection or uninformative clutter.
        """
        r, c = np.indices(self.p.shape)
        g = np.exp(-((r - cue_rc[0]) ** 2 + (c - cue_rc[1]) ** 2) / (2 * sigma_cells**2))
        g /= g.max()
        like_in = reliability * g + (1 - reliability)
        like_row = 1 - reliability
        self.p *= like_in
        self.p_row *= like_row
        norm = self.p.sum() + self.p_row
        self.p /= norm
        self.p_row /= norm
