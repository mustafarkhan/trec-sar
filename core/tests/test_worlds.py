"""Gazebo world checks that do not need Gazebo.

gpu_lidar ray-casts against *visual* geometry, so a visual with no collision
(decoration such as the gas plume) must stay below the lidar scan plane or
Nav2 sees a wall the robot could physically drive through.
"""

import re
from pathlib import Path

import pytest

WORLDS = Path(__file__).resolve().parents[2] / "ros2_ws" / "src" / "trecsar_gazebo" / "worlds"
LIDAR_MIN_HEIGHT = 0.9  # scan plane is ~1.1 m above ground (mast top); keep decorations well below

VISUAL = re.compile(
    r"<visual name='(\w+)_v'><pose>[\d.\-]+ [\d.\-]+ ([\d.\-]+) .*?<box><size>[\d.]+ [\d.]+ ([\d.]+)</size>"
)


@pytest.mark.parametrize("world", sorted(p.name for p in WORLDS.glob("*.sdf")))
def test_visual_only_geometry_is_below_the_lidar(world):
    sdf = (WORLDS / world).read_text()
    collisions = set(re.findall(r"<collision name='(\w+)_c'>", sdf))
    for name, z, sz in VISUAL.findall(sdf):
        if name in collisions:
            continue
        top = float(z) + float(sz) / 2
        assert top < LIDAR_MIN_HEIGHT, f"{world}: visual-only '{name}' reaches {top:.2f} m, the lidar will see it"
