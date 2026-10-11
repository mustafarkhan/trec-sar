"""Procedurally generated operational scenarios.

All numeric parameters are engineering placeholders chosen to be plausible in
order of magnitude. They are NOT calibrated field data. Each one is exposed so it
can be replaced with measured values (e.g. ISRID lost-person statistics, site
radio surveys) — see docs/RESEARCH.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import gaussian_filter

from .terrain import Terrain


@dataclass
class LostPersonProfile:
    """Distance-from-LKP model (log-normal) plus terrain affinity."""
    category: str
    median_distance_m: float
    sigma_log: float = 0.6          # spread of log-distance
    p_in_area: float = 0.95         # probability mass inside the modelled area (rest = ROW)


@dataclass
class MissionConfig:
    time_limit_s: float
    relays: int
    robot_speed_mps: float = 2.22         # 8 km/h — the TREC spec sheet top speed
    battery_wh: float = 600.0
    cold_derate: float = 1.0              # usable battery fraction (Li-ion in sub-zero)
    idle_w: float = 60.0
    move_w_per_mps: float = 90.0          # extra draw per m/s, scaled by terrain cost
    sense_radius_m: float = 30.0
    detect_pmax: float = 0.85             # per-glimpse POD at zero range, open ground
    detect_r0_m: float = 18.0             # e-folding range of detection probability
    canopy_occlusion: float = 0.7         # how strongly canopy reduces POD
    link_threshold_db: float = 10.0       # minimum margin for usable video + telemetry
    link_buffer_db: float = 4.0
    failsafe_s: float = 45.0              # link-loss time before return-to-last-good-link
    relay_drop_s: float = 15.0            # time to stop and deploy one relay
    aerial_cue_time_s: float | None = None  # when a drone cue arrives (None = no drone)
    aerial_cue_sigma_m: float = 40.0
    aerial_false_cue_rate: float = 0.15
    radio: dict = field(default_factory=dict)  # overrides for LinkModel


@dataclass
class Scenario:
    key: str
    title: str
    terrain: Terrain
    person: LostPersonProfile
    mission: MissionConfig
    narrative: str
    truth_lkp_offset: tuple[int, int] = (0, 0)  # for prior-mismatch stress tests


def _noise(rng, shape, sigma):
    n = gaussian_filter(rng.standard_normal(shape), sigma)
    n -= n.min()
    return n / (n.max() + 1e-12)


def _ellipse(shape, center, radii, angle=0.0):
    r, c = np.indices(shape)
    dy, dx = r - center[0], c - center[1]
    ca, sa = np.cos(angle), np.sin(angle)
    u = (dx * ca + dy * sa) / radii[1]
    v = (-dx * sa + dy * ca) / radii[0]
    return u * u + v * v <= 1.0


def _draw_path(mask, pts, width=1):
    """Rasterise a polyline of (row, col) points into mask."""
    for (r0, c0), (r1, c1) in zip(pts[:-1], pts[1:]):
        n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
        rr = np.linspace(r0, r1, n).round().astype(int)
        cc = np.linspace(c0, c1, n).round().astype(int)
        for r, c in zip(rr, cc):
            mask[max(r - width + 1, 0): r + width, max(c - width + 1, 0): c + width] = True
    return mask


# --------------------------------------------------------------------------------
# 1. Boreal forest, winter — elderly person with memory loss walked away from home
# --------------------------------------------------------------------------------
def forest_winter(seed: int = 0, relays: int = 3) -> Scenario:
    rng = np.random.default_rng(seed)
    N, res = 100, 6.0
    shape = (N, N)
    cost = np.full(shape, 1.6)
    rf = np.full(shape, 0.05)
    canopy = np.full(shape, 0.5)
    aff = np.ones(shape)
    labels = {}

    dense = _noise(rng, shape, 6) > 0.62
    cost[dense], rf[dense], canopy[dense], aff[dense] = 2.6, 0.12, 0.85, 0.8
    labels["dense spruce"] = dense

    bog = _noise(rng, shape, 8) < 0.18
    cost[bog], rf[bog], canopy[bog], aff[bog] = 3.0, 0.01, 0.1, 0.5
    labels["bog (suo)"] = bog

    lake = _ellipse(shape, (35, 68), (13, 20), angle=0.4)
    cost[lake], rf[lake], canopy[lake], aff[lake] = np.inf, 0.0, 0.0, 0.0
    labels["lake (no-go: ice not trusted)"] = lake

    ridge = _draw_path(np.zeros(shape, bool), [(78, 30), (60, 45), (55, 62), (64, 90)], width=2)
    ridge &= ~lake
    gaps = np.zeros(shape, bool)
    gaps[56:60, 50:54] = True
    gaps[60:66, 80:84] = True
    cliff = ridge & ~gaps
    cost[cliff], rf[cliff], canopy[cliff], aff[cliff] = np.inf, 2.5, 0.0, 0.0
    cost[ridge & gaps], rf[ridge & gaps] = 4.0, 0.8
    labels["granite ridge"] = ridge

    trail = _draw_path(np.zeros(shape, bool),
                       [(96, 6), (85, 20), (70, 28), (58, 52), (45, 50), (28, 40), (12, 30)], width=1)
    trail |= _draw_path(np.zeros(shape, bool), [(58, 52), (62, 82), (52, 96)], width=1)
    trail &= ~lake & ~cliff
    cost[trail], rf[trail], canopy[trail], aff[trail] = 1.0, 0.03, 0.2, 2.5
    labels["trail"] = trail

    road = np.zeros(shape, bool)
    road[95:, :] = True
    cost[road], rf[road], canopy[road], aff[road] = 1.0, 0.0, 0.0, 0.3
    labels["road"] = road

    t = Terrain("forest_winter", res, cost, rf, canopy, aff, base=(97, 4), lkp=(86, 18), labels=labels)
    t.validate()
    return Scenario(
        key="forest_winter",
        title="Boreal forest, winter night — missing elderly person",
        terrain=t,
        person=LostPersonProfile("dementia / wandering", median_distance_m=260.0, sigma_log=0.65),
        mission=MissionConfig(time_limit_s=90 * 60, relays=relays, cold_derate=0.75,
                              aerial_cue_time_s=240.0, aerial_cue_sigma_m=45.0),
        narrative=("An 81-year-old walked out of a rural home at dusk, -12 °C. Last seen on the "
                   "forest trail. Rescue service drone scouts from above; dense spruce hides "
                   "people from the air, so the UGV searches under canopy and carries a "
                   "thermal blanket and two-way audio."),
    )


# --------------------------------------------------------------------------------
# 2. Underground — worker missing in a mine / utility tunnel after a rock fall
# --------------------------------------------------------------------------------
def tunnel(seed: int = 0, relays: int = 4) -> Scenario:
    rng = np.random.default_rng(seed)
    N, res = 100, 4.0
    shape = (N, N)
    cost = np.full(shape, np.inf)
    rf = np.full(shape, 6.0)          # rock: effectively opaque
    canopy = np.zeros(shape)
    aff = np.zeros(shape)
    labels = {}

    corr = np.zeros(shape, bool)
    _draw_path(corr, [(50, 0), (50, 92)], width=2)                     # main adit
    for c in (18, 40, 62, 84):                                         # cross-cuts
        top, bot = int(rng.integers(8, 22)), int(rng.integers(78, 92))
        _draw_path(corr, [(top, c), (bot, c)], width=1)
    for r, c0, c1 in ((20, 40, 62), (80, 18, 40), (30, 62, 84), (70, 62, 84), (12, 84, 96)):
        _draw_path(corr, [(r, c0), (r, c1)], width=1)
    for _ in range(6):                                                 # dead-end drifts
        r0 = int(rng.integers(10, 90)); c0 = int(rng.choice([18, 40, 62, 84]))
        c1 = int(np.clip(c0 + rng.integers(-14, 15), 2, 97))
        _draw_path(corr, [(r0, c0), (r0, c1)], width=1)
    cost[corr], rf[corr], aff[corr] = 1.3, 0.02, 1.0
    labels["tunnels"] = corr

    fall = np.zeros(shape, bool)
    fall[44:56, 66:69] = True
    fall &= corr
    cost[fall] = 3.5                                                    # rubble: slow but passable
    aff[fall] = 1.5
    labels["rock-fall rubble"] = fall

    work_face = (20, 84) if corr[20, 84] else tuple(np.argwhere(corr)[-1])
    t = Terrain("tunnel", res, cost, rf, canopy, aff, base=(50, 1), lkp=work_face, labels=labels)
    t.validate()
    return Scenario(
        key="tunnel",
        title="Underground tunnel network — missing worker after rock fall",
        terrain=t,
        person=LostPersonProfile("trapped / sheltering worker", median_distance_m=130.0, sigma_log=0.85),
        mission=MissionConfig(time_limit_s=60 * 60, relays=relays, sense_radius_m=24.0,
                              detect_r0_m=14.0, aerial_cue_time_s=None, failsafe_s=30.0),
        narrative=("A maintenance worker's last radio check-in came from the north-east work face "
                   "before a rock fall. No GPS, no radio beyond the first bend. Humans cannot "
                   "enter until the roof is assessed. The UGV must lay relays as it goes."),
    )


# --------------------------------------------------------------------------------
# 3. Industrial site — chemical release, casualty inside the hot zone
# --------------------------------------------------------------------------------
def hazmat_industrial(seed: int = 0, relays: int = 2) -> Scenario:
    rng = np.random.default_rng(seed)
    N, res = 90, 5.0
    shape = (N, N)
    cost = np.full(shape, 1.0)
    rf = np.zeros(shape)
    canopy = np.zeros(shape)
    aff = np.ones(shape)
    labels = {}

    bld = np.zeros(shape, bool)
    for _ in range(14):
        r, c = int(rng.integers(5, 80)), int(rng.integers(15, 82))
        h, w = int(rng.integers(5, 12)), int(rng.integers(5, 14))
        bld[r:r + h, c:c + w] = True
    bld[:, :12] = False        # keep the access road and cordon clear
    bld[40:46, :] = False      # central roadway
    cost[bld], rf[bld], aff[bld] = np.inf, 1.4, 0.0
    labels["buildings / tanks"] = bld

    racks = _noise(rng, shape, 3) > 0.8
    racks &= ~bld
    cost[racks], rf[racks], canopy[racks] = 2.0, 0.3, 0.4
    labels["pipe racks"] = racks

    source = (30, 62)
    for dr in range(0, 6):
        for dc in range(0, 6):
            p = (source[0] + dr, source[1] + dc)
            if np.isfinite(cost[p]):
                source = p
                break
        else:
            continue
        break
    plume = _ellipse(shape, (source[0] + 12, source[1] - 8), (14, 26), angle=-0.5) & ~bld
    cost[plume] = np.where(np.isfinite(cost[plume]), np.maximum(cost[plume], 1.3), np.inf)
    aff[plume] *= 1.6
    labels["gas plume (no humans)"] = plume

    t = Terrain("hazmat_industrial", res, cost, rf, canopy, aff, base=(43, 2), lkp=source, labels=labels)
    t.validate()
    return Scenario(
        key="hazmat_industrial",
        title="Chemical release at an industrial site — casualty in the hot zone",
        terrain=t,
        person=LostPersonProfile("incapacitated worker", median_distance_m=55.0, sigma_log=0.7),
        mission=MissionConfig(time_limit_s=45 * 60, relays=relays, aerial_cue_time_s=90.0,
                              aerial_cue_sigma_m=25.0, failsafe_s=30.0),
        narrative=("A valve failure releases ammonia. One worker near the leak does not answer. "
                   "Firefighters hold the cordon; the drone sees the open yard but not between "
                   "tanks. Steel structures shadow the radio link."),
    )


SCENARIOS = {
    "forest_winter": forest_winter,
    "tunnel": tunnel,
    "hazmat_industrial": hazmat_industrial,
}


def build(key: str, seed: int = 0, **kw) -> Scenario:
    return SCENARIOS[key](seed=seed, **kw)
