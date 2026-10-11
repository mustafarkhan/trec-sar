"""Unit and behaviour tests for the TREC-SAR core. Run: pytest -q core/tests"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trecsar_core import SCENARIOS, Belief, Detector, LinkModel, World, build, prior_map, run  # noqa: E402
from trecsar_core.planner import PLANNERS, PathOracle, PlanContext  # noqa: E402

KEYS = list(SCENARIOS)


@pytest.fixture(scope="module")
def worlds():
    return {k: World(build(k)) for k in KEYS}


# --- terrain & prior ---------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_scenario_layers_valid(key):
    sc = build(key)
    sc.terrain.validate()
    assert sc.terrain.passable.mean() > 0.05


@pytest.mark.parametrize("key", KEYS)
def test_prior_mass_and_support(key):
    sc = build(key)
    p = prior_map(sc.terrain, sc.person)
    assert p.sum() == pytest.approx(sc.person.p_in_area)
    assert np.all(p[~sc.terrain.passable] == 0)
    assert np.all(p >= 0)


# --- belief ------------------------------------------------------------------------
def test_negative_search_conserves_probability_and_lowers_searched_cells():
    sc = build("forest_winter")
    b = Belief.from_scenario(sc.terrain, sc.person)
    before = b.p.copy()
    det = Detector(sc.terrain, 30, 0.85, 18, 0.7)
    idx, pod = det.glimpse(sc.terrain.lkp)
    pos = b.update_negative_sparse(idx, pod)
    assert 0 < pos < 1
    assert b.total == pytest.approx(1.0)
    flat_b, flat_a = before.ravel(), b.p.ravel()
    assert np.all(flat_a[idx[pod > 0.5]] < flat_b[idx[pod > 0.5]])


def test_dense_and_sparse_updates_agree():
    sc = build("hazmat_industrial")
    det = Detector(sc.terrain, 30, 0.85, 18, 0.7)
    idx, pod = det.glimpse(sc.terrain.lkp)
    a = Belief.from_scenario(sc.terrain, sc.person)
    b = Belief.from_scenario(sc.terrain, sc.person)
    dense = np.zeros(sc.terrain.n_cells)
    dense[idx] = pod
    a.update_negative(dense.reshape(sc.terrain.shape))
    b.update_negative_sparse(idx, pod)
    assert np.allclose(a.p, b.p) and a.p_row == pytest.approx(b.p_row)


def test_aerial_cue_pulls_mass_towards_cue():
    sc = build("forest_winter")
    b = Belief.from_scenario(sc.terrain, sc.person)
    cue = (40, 30)
    near = lambda p: p[35:46, 25:36].sum()  # noqa: E731
    before = near(b.p)
    b.update_cue(cue, sigma_cells=5, reliability=0.6)
    assert near(b.p) > before
    assert b.total == pytest.approx(1.0)


# --- radio -------------------------------------------------------------------------
def test_link_margin_falls_with_distance_in_open_ground():
    sc = build("hazmat_industrial")
    lm = LinkModel(sc.terrain)
    a = sc.terrain.base
    near, far = lm.margin(a, (a[0], a[1] + 4)), lm.margin(a, (a[0], a[1] + 40))
    assert near > far


def test_rock_blocks_radio_in_tunnel_and_relay_extends_coverage():
    sc = build("tunnel")
    lm = LinkModel(sc.terrain)
    base = sc.terrain.base
    cov0 = lm.coverage([base])
    assert cov0[sc.terrain.lkp] < lm.threshold          # work face is out of reach
    relay = (50, 40)                                     # junction on the main adit
    assert lm.margin(base, relay) >= lm.threshold
    cov1 = lm.coverage([base, relay])
    assert np.all(cov1 >= cov0 - 1e-9)
    assert (cov1 >= lm.threshold).sum() > (cov0 >= lm.threshold).sum()


def test_vectorised_margin_map_matches_single_link():
    sc = build("forest_winter")
    lm = LinkModel(sc.terrain, samples=256)
    mm = lm.margin_map(sc.terrain.base)
    for dst in [(90, 10), (60, 40), (20, 80)]:
        assert mm[dst] == pytest.approx(lm.margin(sc.terrain.base, dst), abs=3.0)


# --- detector ----------------------------------------------------------------------
def test_detector_cannot_see_through_rock():
    sc = build("tunnel")
    det = Detector(sc.terrain, 24, 0.85, 14, 0.7)
    idx, pod = det.glimpse((50, 20))
    assert np.all(sc.terrain.passable.ravel()[idx[pod > 0]])
    assert np.all((pod >= 0) & (pod <= 1))
    r, c = np.divmod(idx, sc.terrain.shape[1])
    assert not np.any((r == 44) & (c == 20) & ~sc.terrain.passable[44, 20])


# --- planners ----------------------------------------------------------------------
@pytest.mark.parametrize("name", list(PLANNERS))
def test_planners_return_valid_paths(worlds, name):
    w = worlds["forest_winter"]
    t = w.sc.terrain
    planner = PLANNERS[name](t, w.oracle, w.link)
    cov = w.link.coverage([t.base])
    ctx = PlanContext(t.idx(t.base), w.prior, w.detector.value_map(w.prior), cov, 3, 10.0, 4.0,
                      nodes=(t.base,))
    plan = planner.plan(ctx)
    assert plan is not None and plan.path[0] == ctx.pos and plan.path[-1] == plan.goal
    for a, b in zip(plan.path[:-1], plan.path[1:]):
        assert w.oracle.g[a, b] > 0                       # adjacent and passable
    if plan.relay_at is not None:
        assert plan.relay_at in plan.path


# --- whole mission -----------------------------------------------------------------
@pytest.mark.parametrize("key", KEYS)
def test_runs_are_deterministic(worlds, key):
    a = run(worlds[key], "trecsar", 7)
    b = run(worlds[key], "trecsar", 7)
    assert (a.success, a.time_report_s, a.relays_used) == (b.success, b.time_report_s, b.relays_used)


@pytest.mark.parametrize("name", list(PLANNERS))
def test_report_only_happens_inside_radio_coverage(worlds, name):
    w = worlds["forest_winter"]
    t = w.sc.terrain
    for seed in range(6):
        r = run(w, name, seed, record=True)
        assert r.relays_used <= w.sc.mission.relays
        if r.success:
            assert r.time_report_s >= r.time_detect_s
            nodes = [t.base] + [t.rc(c) for c in r.relays]
            cov = w.link.coverage(nodes)
            assert cov.ravel()[r.trajectory[-1]] >= w.sc.mission.link_threshold_db


def test_same_seed_gives_same_casualty_for_every_planner(worlds):
    w = worlds["hazmat_industrial"]
    cas = {run(w, n, 3).casualty for n in PLANNERS}
    assert len(cas) == 1


def test_grid_world_round_trip():
    t = build("forest_winter").terrain
    for rc in [(0, 0), (99, 99), t.base, t.lkp, (37, 81)]:
        assert t.xy_to_cell(*t.cell_to_xy(rc)) == rc
