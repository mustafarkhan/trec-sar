"""Helpers shared by the TREC-SAR ROS 2 nodes."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

try:
    import trecsar_core  # noqa: F401  (pip install -e core/)
except ImportError:  # fall back to the source checkout layout: <repo>/ros2_ws/src/trecsar_mission/...
    for parent in Path(__file__).resolve().parents:
        cand = parent / "core"
        if (cand / "trecsar_core").is_dir():
            sys.path.insert(0, str(cand))
            break

from trecsar_core import World, build  # noqa: E402

_WORLDS: dict[tuple[str, str], World] = {}


def get_world(scenario: str, report_radio: str = "") -> World:
    """Scenario world; `report_radio` adds a narrowband telemetry/report link (a trecsar_core.link.PROFILES key)."""
    if (scenario, report_radio) not in _WORLDS:
        sc = build(scenario)
        if report_radio:
            sc.mission.report_radio = report_radio
        _WORLDS[(scenario, report_radio)] = World(sc)
    return _WORLDS[(scenario, report_radio)]


def grid_msg(node, values: np.ndarray, terrain, frame: str, origin_xy: tuple[float, float]):
    """Pack a 0..1 float grid into nav_msgs/OccupancyGrid (row 0 = north, as in trecsar_core)."""
    from nav_msgs.msg import OccupancyGrid

    msg = OccupancyGrid()
    msg.header.frame_id = frame
    msg.header.stamp = node.get_clock().now().to_msg()
    rows, cols = terrain.shape
    msg.info.resolution = float(terrain.resolution)
    msg.info.width = cols
    msg.info.height = rows
    msg.info.origin.position.x = float(origin_xy[0])
    msg.info.origin.position.y = float(origin_xy[1])
    msg.info.origin.orientation.w = 1.0
    # OccupancyGrid row 0 is the SOUTH edge -> flip trecsar rows
    v = np.clip(np.flipud(values), 0, 1)
    msg.data = (v * 100).astype(np.int8).ravel().tolist()
    return msg
