"""Drive MissionCore with a toy kinematic loop to check the live-robot logic end to end."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trecsar_core import World, build  # noqa: E402
from trecsar_core.mission import MissionCore  # noqa: E402
from trecsar_core.sim import sample_casualty  # noqa: E402


def drive(key, seed, max_steps=4000):
    w = World(build(key))
    t = w.sc.terrain
    core = MissionCore(w)
    casualty = sample_casualty(w, np.random.default_rng(seed))
    rng = np.random.default_rng(seed + 1)
    pos, now, path, log = t.idx(t.base), 0.0, [], []
    core.on_pose(pos)

    def execute(cmds):
        nonlocal path
        for c in cmds:
            log.append(c)
            if c[0] == "goto":
                _, pred = w.oracle.from_cell(pos)
                path = w.oracle.path(pred, pos, c[1])[1:]
            elif c[0] == "drop_relay":
                core.on_relay_deployed(c[1])
                execute(core.after_relay_continue())

    for _ in range(max_steps):
        execute(core.tick(now, goal_reached=not path))
        if core.state in ("DONE",):
            break
        if path:
            nxt = path.pop(0)
            now += w.oracle.g[pos, nxt] / w.sc.mission.robot_speed_mps
            pos = nxt
        else:
            now += 1.0
        core.on_pose(pos)
        idx, pod = w.detector.glimpse(t.rc(pos))
        hit = np.nonzero(idx == casualty)[0]
        if hit.size and rng.random() < pod[hit[0]]:
            execute(core.on_detection(casualty))
        cov = w.link.coverage(core.nodes)
        execute(core.on_link(float(cov.ravel()[pos]), now))
        if core.state == "DONE":
            break
    return core, log, w, pos


@pytest.mark.parametrize("key,seed", [("hazmat_industrial", 1), ("tunnel", 2), ("forest_winter", 4)])
def test_live_mission_reaches_report(key, seed):
    core, log, w, pos = drive(key, seed)
    assert core.state == "DONE", log[-5:]
    assert ("report", log[[c[0] for c in log].index("report")][1]) in log
    cov = w.link.coverage(core.nodes)
    assert cov.ravel()[pos] >= w.sc.mission.link_threshold_db
