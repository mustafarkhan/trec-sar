#!/usr/bin/env python3
"""Generate a Gazebo (Harmonic) SDF world from a TREC-SAR scenario.

The same terrain the planner reasons about becomes the 3D world, so the 2D
Monte Carlo and the 3D demo describe one place.

    python3 terrain_to_sdf.py forest_winter --seed 1002 -o ../worlds/forest_winter.sdf

Needs trecsar_core importable (pip install -e core/ from the repo root).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    from trecsar_core import World, build
    from trecsar_core.sim import sample_casualty
except ImportError:  # running from a source checkout without pip install
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "core"))
    from trecsar_core import World, build
    from trecsar_core.sim import sample_casualty

STYLE = {
    "forest_winter": dict(ground=(0.93, 0.94, 0.96), wall_h=2.5, wall_rgb=(0.42, 0.42, 0.44)),
    "tunnel": dict(ground=(0.35, 0.33, 0.30), wall_h=3.5, wall_rgb=(0.30, 0.28, 0.26)),
    "hazmat_industrial": dict(ground=(0.55, 0.55, 0.55), wall_h=7.0, wall_rgb=(0.62, 0.64, 0.68)),
}


def _box(name, x, y, z, sx, sy, sz, rgb, collide=True, alpha=1.0):
    col = (
        (
            f"<collision name='{name}_c'><pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>"
            f"<geometry><box><size>{sx:.2f} {sy:.2f} {sz:.2f}</size></box></geometry></collision>"
        )
        if collide
        else ""
    )
    r, g, b = rgb
    return (
        col + f"<visual name='{name}_v'><pose>{x:.2f} {y:.2f} {z:.2f} 0 0 0</pose>"
        f"<geometry><box><size>{sx:.2f} {sy:.2f} {sz:.2f}</size></box></geometry>"
        f"<material><ambient>{r} {g} {b} {alpha}</ambient><diffuse>{r} {g} {b} {alpha}</diffuse></material></visual>"
    )


def _cyl(name, x, y, radius, h, rgb):
    r, g, b = rgb
    return (
        f"<collision name='{name}_c'><pose>{x:.2f} {y:.2f} {h / 2:.2f} 0 0 0</pose>"
        f"<geometry><cylinder><radius>{radius}</radius><length>{h}</length></cylinder></geometry></collision>"
        f"<visual name='{name}_v'><pose>{x:.2f} {y:.2f} {h / 2:.2f} 0 0 0</pose>"
        f"<geometry><cylinder><radius>{radius}</radius><length>{h}</length></cylinder></geometry>"
        f"<material><ambient>{r} {g} {b} 1</ambient><diffuse>{r} {g} {b} 1</diffuse></material></visual>"
    )


def runs_of(mask_row):
    """(start, end_exclusive) column runs of True in a 1-D mask."""
    out, c, n = [], 0, len(mask_row)
    while c < n:
        if mask_row[c]:
            s = c
            while c < n and mask_row[c]:
                c += 1
            out.append((s, c))
        c += 1
    return out


def generate(key: str, seed: int, tree_seed: int = 0) -> str:
    w = World(build(key))
    t = w.sc.terrain
    st = STYLE[key]
    res = t.resolution
    rows, cols = t.shape
    size_x, size_y = cols * res, rows * res
    rng = np.random.default_rng(tree_seed)

    imp = ~t.passable
    # only cells bordering passable ground need geometry (keeps the tunnel world light)
    border = np.zeros_like(imp)
    pas = t.passable
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
        border |= np.roll(np.roll(pas, dr, 0), dc, 1)
    walls = imp & border
    lake = t.labels.get("lake (no-go: ice not trusted)", np.zeros_like(imp))
    walls_solid = walls & ~lake

    parts = []
    k = 0
    for r in range(rows):
        for c0, c1 in runs_of(walls_solid[r]):
            x0, y = t.cell_to_xy((r, c0))
            x1, _ = t.cell_to_xy((r, c1 - 1))
            parts.append(
                _box(f"w{k}", (x0 + x1) / 2, y, st["wall_h"] / 2, (c1 - c0) * res, res, st["wall_h"], st["wall_rgb"])
            )
            k += 1
        for c0, c1 in runs_of(lake[r]):
            x0, y = t.cell_to_xy((r, c0))
            x1, _ = t.cell_to_xy((r, c1 - 1))
            parts.append(_box(f"l{k}", (x0 + x1) / 2, y, 0.15, (c1 - c0) * res, res, 0.3, (0.55, 0.70, 0.85)))
            k += 1
    obstacles = "".join(parts)

    trees = ""
    if key == "forest_winter":
        tparts = []
        dense = t.labels["dense spruce"] & pas
        open_forest = pas & ~dense & ~t.labels["trail"] & ~t.labels["road"] & ~t.labels["bog (suo)"]
        for i, (mask, p) in enumerate(((dense, 0.35), (open_forest, 0.08))):
            for r, c in np.argwhere(mask):
                if rng.random() < p:
                    x, y = t.cell_to_xy((r, c))
                    x += rng.uniform(-res / 3, res / 3)
                    y += rng.uniform(-res / 3, res / 3)
                    tparts.append(_cyl(f"t{i}_{r}_{c}", x, y, 0.22, float(rng.uniform(8, 16)), (0.20, 0.30, 0.20)))
        trees = f"<model name='trees'><static>true</static><link name='l'>{''.join(tparts)}</link></model>"

    plume = ""
    # The plume is painted on the ground, 2 cm thick: Gazebo's gpu_lidar ray-casts against
    # visuals, so a translucent 2 m volume (the earlier version) looked like a solid wall to
    # the lidar and Nav2 refused to drive into the plume area.
    if "gas plume (no humans)" in t.labels:
        pm = t.labels["gas plume (no humans)"]
        pp = []
        for r in range(rows):
            for c0, c1 in runs_of(pm[r]):
                x0, y = t.cell_to_xy((r, c0))
                x1, _ = t.cell_to_xy((r, c1 - 1))
                pp.append(
                    _box(
                        f"p{r}_{c0}",
                        (x0 + x1) / 2,
                        y,
                        0.01,
                        (c1 - c0) * res,
                        res,
                        0.02,
                        (0.95, 0.85, 0.3),
                        collide=False,
                        alpha=0.6,
                    )
                )
        plume = f"<model name='gas_plume'><static>true</static><link name='l'>{''.join(pp)}</link></model>"

    cas = sample_casualty(w, np.random.default_rng(seed))
    cx, cy = t.cell_to_xy(t.rc(cas))
    bx, by = t.cell_to_xy(t.base)
    gr, gg, gb = st["ground"]
    return f"""<?xml version="1.0"?>
<!-- Generated by terrain_to_sdf.py from scenario '{key}', casualty seed {seed}. Do not edit by hand. -->
<sdf version="1.9">
  <world name="{key}">
    <physics name="default" type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <scene><ambient>0.5 0.5 0.55 1</ambient><background>0.75 0.8 0.88 1</background><shadows>false</shadows></scene>
    <light type="directional" name="sun"><cast_shadows>false</cast_shadows><pose>0 0 100 0 0 0</pose>
      <diffuse>0.9 0.9 0.9 1</diffuse><specular>0.1 0.1 0.1 1</specular><direction>-0.4 0.3 -0.9</direction></light>
    <model name="ground"><static>true</static><pose>{size_x / 2:.1f} {size_y / 2:.1f} 0 0 0 0</pose><link name="l">
      <collision name="c"><geometry><plane><normal>0 0 1</normal><size>{size_x:.0f} {size_y:.0f}</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>{size_x:.0f} {size_y:.0f}</size></plane></geometry>
        <material><ambient>{gr} {gg} {gb} 1</ambient><diffuse>{gr} {gg} {gb} 1</diffuse></material></visual></link></model>
    <model name="obstacles"><static>true</static><link name="l">{obstacles}</link></model>
    {trees}
    {plume}
    <model name="command_post"><static>true</static><pose>{bx - 3:.2f} {by:.2f} 0 0 0 0</pose><link name="l">
      {_box("cp", 0, 0, 1.2, 2.4, 2.0, 2.4, (0.8, 0.2, 0.15))}</link></model>
    <model name="casualty"><static>true</static><pose>{cx:.2f} {cy:.2f} 0.18 0 1.5708 0.6</pose><link name="body">
      <collision name="c"><geometry><cylinder><radius>0.18</radius><length>1.7</length></cylinder></geometry></collision>
      <visual name="v"><geometry><cylinder><radius>0.18</radius><length>1.7</length></cylinder></geometry>
        <material><ambient>0.85 0.35 0.1 1</ambient><diffuse>0.85 0.35 0.1 1</diffuse></material>
        <plugin filename="gz-sim-thermal-system" name="gz::sim::systems::Thermal"><temperature>306.0</temperature></plugin>
      </visual></link></model>
  </world>
</sdf>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=list(STYLE))
    ap.add_argument("--seed", type=int, default=1002, help="casualty placement seed (same as the 2D simulator)")
    ap.add_argument("-o", "--out", type=Path)
    a = ap.parse_args()
    sdf = generate(a.scenario, a.seed)
    out = a.out or Path(__file__).resolve().parents[1] / "worlds" / f"{a.scenario}.sdf"
    out.write_text(sdf)
    print(f"wrote {out} ({len(sdf) / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
