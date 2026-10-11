"""Model your own site from a map image.

Draw (or export from GIS) a PNG where each pixel is one grid cell and each colour
is a terrain class, then describe it in a small YAML file:

```yaml
name: campus
title: University campus at night - missing student
map: campus.png            # relative to this YAML file; row 0 = top of the image (north)
resolution_m: 5            # metres per pixel
legend:                    # colour -> terrain class (see CLASSES below or define your own)
  "#ffffff": open
  "#808080": road
  "#1f5f1f": forest
  "#2060c0": water
  "#000000": building
base: [78, 3]              # command post, [row, col]
lkp: [40, 40]              # last known point, [row, col]
person: {category: student, median_distance_m: 150, sigma_log: 0.7}
mission: {time_limit_min: 45, relays: 2, aerial_cue_time_s: 120}
classes:                   # optional: add or override classes
  hedge: {cost: 3.0, rf_db_per_m: 0.2, canopy: 0.6, affinity: 0.5}
```

Then: `trecsar run --site path/to/site.yaml` or `build_site("path/to/site.yaml")`.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .scenarios import LostPersonProfile, MissionConfig, Scenario
from .terrain import Terrain

INF = float("inf")

# cost: traversal multiplier (inf = impassable) · rf_db_per_m: radio loss inside the cell
# canopy: 0..1 occlusion for cameras · affinity: relative chance a lost person is there
CLASSES: dict[str, dict] = {
    "open": dict(cost=1.0, rf_db_per_m=0.00, canopy=0.0, affinity=1.0),
    "road": dict(cost=1.0, rf_db_per_m=0.00, canopy=0.0, affinity=0.4),
    "trail": dict(cost=1.0, rf_db_per_m=0.03, canopy=0.2, affinity=2.5),
    "forest": dict(cost=1.6, rf_db_per_m=0.05, canopy=0.5, affinity=1.0),
    "dense_forest": dict(cost=2.6, rf_db_per_m=0.12, canopy=0.85, affinity=0.8),
    "bog": dict(cost=3.0, rf_db_per_m=0.01, canopy=0.1, affinity=0.5),
    "rubble": dict(cost=3.5, rf_db_per_m=0.30, canopy=0.3, affinity=1.5),
    "corridor": dict(cost=1.3, rf_db_per_m=0.02, canopy=0.0, affinity=1.0),
    "water": dict(cost=INF, rf_db_per_m=0.00, canopy=0.0, affinity=0.0),
    "building": dict(cost=INF, rf_db_per_m=1.40, canopy=0.0, affinity=0.0),
    "rock": dict(cost=INF, rf_db_per_m=6.00, canopy=0.0, affinity=0.0),
    "cliff": dict(cost=INF, rf_db_per_m=2.50, canopy=0.0, affinity=0.0),
}


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    if len(h) != 6:
        raise ValueError(f"colour '{h}' must be #rrggbb")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def terrain_from_image(
    img: np.ndarray,
    legend: dict[str, str],
    classes: dict[str, dict],
    resolution_m: float,
    base: tuple[int, int],
    lkp: tuple[int, int],
    name: str = "site",
    tolerance: int = 40,
) -> Terrain:
    """Classify every pixel to the nearest legend colour (within `tolerance` per channel)."""
    if img.ndim == 2:
        img = np.repeat(img[..., None], 3, axis=2)
    rgb = img[..., :3].astype(int)
    keys = list(legend)
    cols = np.array([_hex_to_rgb(k) for k in keys])  # (K, 3)
    dist = np.abs(rgb[:, :, None, :] - cols[None, None, :, :]).max(axis=3)  # (H, W, K)
    nearest = dist.argmin(axis=2)
    if (dist.min(axis=2) > tolerance).any():
        r, c = np.argwhere(dist.min(axis=2) > tolerance)[0]
        raise ValueError(
            f"pixel ({r},{c}) colour {tuple(rgb[r, c])} matches no legend entry "
            f"(tolerance {tolerance}); add it to the legend"
        )
    shape = rgb.shape[:2]
    layers = {k: np.zeros(shape) for k in ("cost", "rf_db_per_m", "canopy", "affinity")}
    labels = {}
    for i, key in enumerate(keys):
        cname = legend[key]
        if cname not in classes:
            raise ValueError(f"legend class '{cname}' is not defined; known: {sorted(classes)}")
        mask = nearest == i
        for layer in layers:
            layers[layer][mask] = classes[cname][layer]
        labels[cname] = labels.get(cname, np.zeros(shape, bool)) | mask
    t = Terrain(
        name,
        float(resolution_m),
        layers["cost"],
        layers["rf_db_per_m"],
        layers["canopy"],
        layers["affinity"],
        base=tuple(base),
        lkp=tuple(lkp),
        labels=labels,
    )
    t.validate()
    return t


def build_site(path: str | Path) -> Scenario:
    """Build a Scenario from a site YAML file (see module docstring)."""
    import yaml
    from PIL import Image

    path = Path(path)
    cfg = yaml.safe_load(path.read_text())
    for req in ("map", "resolution_m", "legend", "base", "lkp"):
        if req not in cfg:
            raise ValueError(f"{path}: missing required key '{req}'")
    classes = dict(CLASSES)
    for k, v in (cfg.get("classes") or {}).items():
        spec = dict(v)
        if spec.get("cost") in ("inf", "impassable", None):
            spec["cost"] = INF
        classes[k] = {**CLASSES.get(k, CLASSES["open"]), **spec}
    img = np.asarray(Image.open(path.parent / cfg["map"]).convert("RGB"))
    name = cfg.get("name", path.stem)
    t = terrain_from_image(
        img, cfg["legend"], classes, cfg["resolution_m"], cfg["base"], cfg["lkp"], name, int(cfg.get("tolerance", 40))
    )
    p = cfg.get("person") or {}
    person = LostPersonProfile(
        p.get("category", "unknown"),
        float(p.get("median_distance_m", 200)),
        float(p.get("sigma_log", 0.7)),
        float(p.get("p_in_area", 0.95)),
    )
    m = dict(cfg.get("mission") or {})
    if "time_limit_min" in m:
        m["time_limit_s"] = float(m.pop("time_limit_min")) * 60
    m.setdefault("time_limit_s", 3600.0)
    m.setdefault("relays", 3)
    if "radio" in cfg:
        m["radio"] = cfg["radio"]
    mission = MissionConfig(**m)
    return Scenario(
        key=name,
        title=cfg.get("title", name),
        terrain=t,
        person=person,
        mission=mission,
        narrative=cfg.get("narrative", ""),
    )
