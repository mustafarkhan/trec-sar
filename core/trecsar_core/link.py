"""Radio link model: log-distance path loss plus terrain obstruction loss.

margin_db = EIRP + G_rx - PL(d) - sum(obstruction along the straight line) - sensitivity

Defaults approximate a 2.4 GHz mesh radio (FSPL at 1 m ~ 40 dB) at the European
power limit: `ptx_dbm` is the radiated power (EIRP, 20 dBm = 100 mW under
ETSI EN 300 328) and `antenna_gain_db` is the receive antenna. Propagation numbers
are placeholders: replace with a site survey or a calibrated model (e.g. ITU-R
P.833 for vegetation, measured tunnel loss) before drawing operational conclusions.

`RadioProfile` describes a second, narrowband link in the European 868 MHz
short-range-device band, with the power and duty-cycle limits of ERC
Recommendation 70-03 / ETSI EN 300 220. See docs/EU_RADIO.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .terrain import Terrain


@dataclass(frozen=True)
class RadioProfile:
    """A regulated radio: what the rules allow and what the modem can do."""

    key: str
    title: str
    freq_mhz: float
    eirp_dbm: float  # radiated power; e.r.p. limits are converted with +2.15 dB
    rx_gain_dbi: float
    sensitivity_dbm: float
    bitrate_bps: float
    duty_cycle: float  # legal fraction of time on air (1.0 = no limit)
    threshold_db: float  # fade margin required above sensitivity
    rf_scale: float  # obstruction loss relative to the 2.4 GHz terrain numbers
    rule: str

    @property
    def pl_1m_db(self) -> float:
        """Free-space path loss at 1 m."""
        return 20.0 * np.log10(self.freq_mhz) - 27.55

    @property
    def throughput_bps(self) -> float:
        """Long-run data rate once the duty-cycle limit is respected."""
        return self.bitrate_bps * self.duty_cycle

    def airtime_s(self, payload_bytes: float) -> float:
        """Wall-clock time to deliver a payload under the duty-cycle limit."""
        return payload_bytes * 8.0 / self.throughput_bps


_ERP = 2.15  # dB between e.r.p. (dipole reference) and e.i.r.p.

# LoRa SF7 / 125 kHz: 5.47 kbit/s, -123 dBm (Semtech SX1276 class modems).
# rf_scale 0.75: vegetation loss scales roughly with f^0.284 (Weissberger), (868/2440)^0.284 = 0.75.
PROFILES: dict[str, RadioProfile] = {
    p.key: p
    for p in (
        RadioProfile(
            "eu868_500mw",
            "868 MHz LoRa, 500 mW e.r.p., 10 % duty cycle",
            869.525,
            10 * np.log10(500.0) + _ERP,
            2.0,
            -123.0,
            5470.0,
            0.10,
            6.0,
            0.75,
            "ERC/REC 70-03 Annex 1 band h1.7 (869.4-869.65 MHz), ETSI EN 300 220",
        ),
        RadioProfile(
            "eu868_25mw",
            "868 MHz LoRa, 25 mW e.r.p., 1 % duty cycle",
            868.3,
            10 * np.log10(25.0) + _ERP,
            2.0,
            -123.0,
            5470.0,
            0.01,
            6.0,
            0.75,
            "ERC/REC 70-03 Annex 1 band h1.5 (868.0-868.6 MHz), ETSI EN 300 220",
        ),
    )
}


def report_link(terrain: Terrain, profile: RadioProfile, exponent: float, rf_scale: float | None = None) -> LinkModel:
    """LinkModel for a narrowband profile on this terrain (same path-loss exponent as the site's main radio)."""
    scale = profile.rf_scale if rf_scale is None else rf_scale
    return LinkModel(
        terrain,
        ptx_dbm=profile.eirp_dbm,
        antenna_gain_db=profile.rx_gain_dbi,
        sensitivity_dbm=profile.sensitivity_dbm,
        pl_1m_db=float(profile.pl_1m_db),
        exponent=exponent,
        threshold_db=profile.threshold_db,
        rf_map=terrain.rf_db_per_m * scale,
    )


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
        rf_map: np.ndarray | None = None,
    ):
        """`rf_map` overrides the terrain's per-cell attenuation (calibrated or "true" radio)."""
        self.t = terrain
        self.rf = terrain.rf_db_per_m if rf_map is None else np.asarray(rf_map, float)
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

    def variant(self, exponent: float | None = None, rf_map: np.ndarray | None = None) -> LinkModel:
        """Same radio and threshold, different propagation (used for calibration / ground truth)."""
        m = LinkModel.__new__(LinkModel)
        m.__dict__.update(self.__dict__)
        m.n = self.n if exponent is None else float(exponent)
        m.rf = self.rf if rf_map is None else np.asarray(rf_map, float)
        m._cache = {}
        return m

    # -- single link -----------------------------------------------------------
    def margin(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        res = self.t.resolution
        d_cells = float(np.hypot(b[0] - a[0], b[1] - a[1]))
        d = max(d_cells * res, 1.0)
        k = max(int(np.ceil(d_cells * 2)), 1)
        ts = (np.arange(k) + 0.5) / k
        rr = np.clip(np.round(a[0] + ts * (b[0] - a[0])).astype(int), 0, self.t.shape[0] - 1)
        cc = np.clip(np.round(a[1] + ts * (b[1] - a[1])).astype(int), 0, self.t.shape[1] - 1)
        obstruction = float(self.rf[rr, cc].sum() * (d / k))
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
        rf = self.rf[rr, cc]  # (k, n_cells)
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
