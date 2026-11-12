"""European radio profiles and the two-link (video + narrowband report) mission logic."""

import numpy as np
import pytest

from trecsar_core import World, build, run
from trecsar_core.link import PROFILES, LinkModel
from trecsar_core.mission import MissionCore


def _world(key, radio, **mission):
    sc = build(key)
    sc.mission.report_radio = radio
    for k, v in mission.items():
        setattr(sc.mission, k, v)
    return World(sc)


def test_profiles_respect_the_european_limits():
    hi, lo = PROFILES["eu868_500mw"], PROFILES["eu868_25mw"]
    # ERC/REC 70-03 Annex 1: h1.7 500 mW e.r.p. at <= 10 %, h1.5 25 mW e.r.p. at <= 1 %
    assert 869.4 <= hi.freq_mhz <= 869.65 and hi.duty_cycle <= 0.10
    assert 10 ** ((hi.eirp_dbm - 2.15) / 10) == pytest.approx(500, rel=1e-3)
    assert 868.0 <= lo.freq_mhz <= 868.6 and lo.duty_cycle <= 0.01
    assert 10 ** ((lo.eirp_dbm - 2.15) / 10) == pytest.approx(25, rel=1e-3)
    # the default video link radiates the 2.4 GHz limit of EN 300 328: 20 dBm e.i.r.p.
    t = build("hazmat_industrial").terrain
    assert LinkModel(t).budget == pytest.approx(20.0 + 4.0 + 90.0)


def test_duty_cycle_sets_the_report_time():
    hi, lo = PROFILES["eu868_500mw"], PROFILES["eu868_25mw"]
    assert hi.airtime_s(4000) == pytest.approx(4000 * 8 / 547.0)  # about a minute
    assert lo.airtime_s(4000) == pytest.approx(10 * hi.airtime_s(4000))  # ten times less airtime allowed
    assert hi.airtime_s(60) < 1.0  # a position-only alert is almost instant


def test_free_space_loss_is_lower_at_868_mhz():
    assert PROFILES["eu868_500mw"].pl_1m_db == pytest.approx(31.2, abs=0.1)


def test_unknown_report_radio_is_a_clear_error():
    with pytest.raises(KeyError, match="unknown report radio"):
        _world("forest_winter", "cb_radio")


def test_narrowband_link_reaches_further_than_video_in_forest_but_not_through_rock():
    w = _world("forest_winter", "eu868_500mw")
    video = w.link.coverage([w.sc.terrain.base]) >= w.link.threshold
    nb = w.link_report.coverage([w.sc.terrain.base]) >= w.link_report.threshold
    passable = w.sc.terrain.passable
    assert nb[passable].mean() > 0.8 and video[passable].mean() < 0.3
    tw = _world("tunnel", "eu868_500mw")
    t = tw.sc.terrain
    v = (tw.link.coverage([t.base]) >= tw.link.threshold)[t.passable].mean()
    n = (tw.link_report.coverage([t.base]) >= tw.link_report.threshold)[t.passable].mean()
    assert n <= v + 0.05  # underground the sub-GHz link buys almost nothing


def test_without_a_report_radio_nothing_changes():
    w = World(build("tunnel"))
    assert w.link_report is None
    r = run(w, "trecsar", 1003)
    assert r.report_channel in ("video", "") and r.unsupervised_s == pytest.approx(r.out_of_link_s)
    if r.success:
        assert r.time_alert_s == r.time_report_s


def test_two_link_mission_supervises_the_forest_and_reports_position_first():
    w = _world("forest_winter", "eu868_500mw")
    rs = [run(w, "greedy_bayes", s) for s in range(1000, 1012)]
    assert sum(r.failsafe_events for r in rs) == 0  # telemetry keeps the robot supervised
    assert all(r.unsupervised_s <= r.out_of_link_s for r in rs)
    done = [r for r in rs if r.success]
    assert done and all(r.time_alert_s <= r.time_report_s for r in done)
    assert {r.report_channel for r in done} <= {"video", "narrowband"}


def test_slow_duty_cycle_makes_the_robot_drive_back_to_video():
    # same missions, same radio range; only the legal airtime differs
    fast = _world("forest_winter", "eu868_500mw")
    slow = _world("forest_winter", "eu868_500mw", report_payload_bytes=400_000)  # would take hours on air
    seeds = range(1000, 1030)
    nb_fast = sum(run(fast, "greedy_bayes", s).report_channel == "narrowband" for s in seeds)
    nb_slow = sum(run(slow, "greedy_bayes", s).report_channel == "narrowband" for s in seeds)
    assert nb_fast > 0 and nb_slow == 0


def test_live_mission_core_sends_the_report_over_narrowband_after_its_airtime():
    w = _world("forest_winter", "eu868_500mw")
    core = MissionCore(w)
    t = w.sc.terrain
    core.on_pose(t.idx(t.base))
    thr_v, thr_nb = w.sc.mission.link_threshold_db, w.link_report.threshold
    airtime = w.report_profile.airtime_s(w.sc.mission.report_payload_bytes)
    # no video, narrowband up: detection starts the transfer and the robot holds
    core.on_link(thr_v - 20, 100.0, thr_nb + 5)
    assert core.supervised and not core.video_ok
    cmds = core.on_detection(t.idx(t.lkp), 100.0)
    assert ("hold", None) in cmds and core.state == "REPORT"
    assert core.on_link(thr_v - 20, 100.0 + airtime / 2, thr_nb + 5) == []
    cmds = core.on_link(thr_v - 20, 100.0 + airtime + 1, thr_nb + 5)
    assert ("report", t.idx(t.lkp)) in cmds and core.state == "DONE" and core.report_channel == "narrowband"


def test_live_mission_core_restarts_an_interrupted_narrowband_transfer():
    w = _world("forest_winter", "eu868_500mw")
    core = MissionCore(w)
    t = w.sc.terrain
    core.on_pose(t.idx(t.base))
    thr_v, thr_nb = w.sc.mission.link_threshold_db, w.link_report.threshold
    airtime = w.report_profile.airtime_s(w.sc.mission.report_payload_bytes)
    core.on_link(thr_v - 20, 0.0, thr_nb + 5)
    core.on_detection(t.idx(t.lkp), 0.0)
    core.on_link(thr_v - 20, airtime / 2, thr_nb - 5)  # link drops mid-transfer
    assert core.on_link(thr_v - 20, airtime + 1, thr_nb + 5) == [("hold", None)]  # starts again
    assert core.state == "REPORT"
    assert core.on_link(thr_v + 5, airtime + 2, thr_nb + 5)[0][0] == "report"  # video arrives: immediate
    assert core.report_channel == "video"


def test_supervision_map_matches_between_simulator_and_live_core():
    w = _world("hazmat_industrial", "eu868_25mw")
    core = MissionCore(w)
    thr = w.sc.mission.link_threshold_db
    video = w.link.coverage(core.nodes)
    nb = w.link_report.coverage(core.nodes) - w.link_report.threshold + thr
    assert np.allclose(core.coverage, np.maximum(video, nb))
