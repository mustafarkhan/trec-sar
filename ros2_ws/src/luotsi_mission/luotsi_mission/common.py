"""Helpers shared by the LUOTSI ROS 2 nodes."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

try:
    import luotsi_core  # noqa: F401  (pip install -e core/)
except ImportError:      # fall back to the source checkout layout: <repo>/ros2_ws/src/luotsi_mission/...
    for parent in Path(__file__).resolve().parents:
        cand = parent / "core"
        if (cand / "luotsi_core").is_dir():
            sys.path.insert(0, str(cand))
            break

from luotsi_core import World, build  # noqa: E402

_WORLDS: dict[str, World] = {}


def get_world(scenario: str) -> World:
    if scenario not in _WORLDS:
        _WORLDS[scenario] = World(build(scenario))
    return _WORLDS[scenario]


def grid_msg(node, values: np.ndarray, terrain, frame: str, origin_xy: tuple[float, float]):
    """Pack a 0..1 float grid into nav_msgs/OccupancyGrid (row 0 = north, as in luotsi_core)."""
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
    # OccupancyGrid row 0 is the SOUTH edge -> flip luotsi rows
    v = np.clip(np.flipud(values), 0, 1)
    msg.data = (v * 100).astype(np.int8).ravel().tolist()
    return msg
