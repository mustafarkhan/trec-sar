"""Online radio calibration."""

import numpy as np

from trecsar_core import World, build
from trecsar_core.calibrate import RadioCalibrator
from trecsar_core.sim import run


def _readings(truth, nodes, cells, rng, noise=2.0):
    for n in nodes:
        mm = truth.margin_map(n)
        for rc in cells:
            yield n, rc, float(mm[rc]) + rng.normal(0, noise)


def test_no_readings_means_prior_model():
    w = World(build("forest_winter"))
    cal = RadioCalibrator(w.link)
    n, att = cal.estimate()
    assert n == w.link.n
    assert all(abs(k - v) < 1e-9 for k, v in att.items())


def test_recovers_worse_than_planned_propagation():
    sc = build("forest_winter")
    sc.radio_truth = {"rf_scale": 1.8, "exponent": 2.4}
    w = World(sc)
    cal = RadioCalibrator(w.link)
    rng = np.random.default_rng(0)
    passable = np.argwhere(sc.terrain.passable)
    cells = [tuple(c) for c in passable[rng.choice(len(passable), 400, replace=False)]]
    for n, rc, y in _readings(w.link_truth, [sc.terrain.base], cells, rng):
        cal.observe(n, rc, y)
    n_est, att = cal.estimate()
    assert abs(n_est - 2.4) < 0.15
    assert abs(att[0.12] - 0.12 * 1.8) < 0.04  # dense spruce, the class most links cross
    # predictions now match the real radio far better than the prior did, wherever the radio
    # can be heard at all (links buried behind the ridge give no readings and do not matter)
    test = [c for c in cells if w.link_truth.margin(sc.terrain.base, c) > 0]
    assert len(test) > 50
    prior_err = [abs(w.link.margin(sc.terrain.base, c) - w.link_truth.margin(sc.terrain.base, c)) for c in test]
    cal_err = [abs(cal.predict(sc.terrain.base, c)[0] - w.link_truth.margin(sc.terrain.base, c)) for c in test]
    assert np.mean(cal_err) < 0.3 * np.mean(prior_err)


def test_readings_below_sensitivity_are_ignored():
    w = World(build("tunnel"))
    cal = RadioCalibrator(w.link)
    assert not cal.observe(w.sc.terrain.base, (5, 5), -3.0)
    assert cal.n_obs == 0


def test_uncertainty_shrinks_with_data():
    w = World(build("forest_winter"))
    cal = RadioCalibrator(w.link)
    t = w.sc.terrain
    far = (40, 60)
    _, sd0 = cal.predict(t.base, far)
    rng = np.random.default_rng(1)
    for n, rc, y in _readings(w.link, [t.base], [(r, c) for r in range(50, 95, 5) for c in range(5, 90, 10)], rng):
        cal.observe(n, rc, y)
    _, sd1 = cal.predict(t.base, far)
    assert sd1 < 0.5 * sd0


def test_calibrated_planner_runs_and_exact_radio_leaves_other_planners_unchanged():
    w = World(build("tunnel"))
    r = run(w, "trecsar_cal", 1003)
    assert r.end_state in ("DONE", "FAILED", "TIMEOUT")
    # with an exact planning model the truth/plan split must not change behaviour
    assert w.link_truth is w.link
