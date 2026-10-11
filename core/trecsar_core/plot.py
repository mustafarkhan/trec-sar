"""Static mission plots (needs matplotlib: pip install 'trecsar-core[viz]')."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .sim import RunResult, World

COLOR = {
    "trecsar_cal": "#7b4fd6",
    "trecsar": "#2a78d6",
    "greedy_sf": "#eb6834",
    "greedy_bayes": "#1baf7a",
    "lawnmower": "#eda100",
}
NAME = {
    "trecsar": "TREC-SAR",
    "trecsar_cal": "TREC-SAR + radio calibration",
    "greedy_sf": "Greedy + planned link loss",
    "greedy_bayes": "Greedy + reactive relays",
    "lawnmower": "Lawnmower + reactive relays",
}
SURFACE, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"

_SHADE = {
    "dense spruce": (0.78, 0.86, 0.78),
    "dense_forest": (0.78, 0.86, 0.78),
    "forest": (0.86, 0.92, 0.85),
    "bog (suo)": (0.86, 0.84, 0.74),
    "bog": (0.86, 0.84, 0.74),
    "trail": (0.97, 0.94, 0.86),
    "road": (0.86, 0.86, 0.86),
    "tunnels": (0.96, 0.95, 0.92),
    "corridor": (0.96, 0.95, 0.92),
    "rock-fall rubble": (0.80, 0.74, 0.68),
    "rubble": (0.80, 0.74, 0.68),
    "pipe racks": (0.86, 0.86, 0.90),
    "gas plume (no humans)": (0.98, 0.88, 0.84),
    "water": (0.70, 0.80, 0.90),
    "lake (no-go: ice not trusted)": (0.70, 0.80, 0.90),
}


def terrain_rgb(t) -> np.ndarray:
    img = np.ones(t.shape + (3,)) * np.array([0.93, 0.95, 0.91])
    for name, mask in t.labels.items():
        if name in _SHADE:
            img[mask] = _SHADE[name]
    water = np.zeros(t.shape, bool)
    for name in ("water", "lake (no-go: ice not trusted)"):
        if name in t.labels:
            water |= t.labels[name]
    img[~t.passable & ~water] = (0.45, 0.47, 0.50)
    return img


def plot_runs(world: World, results: list[RunResult], path: str | Path, title: str | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    t = world.sc.terrain
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(5.6 * n, 6.0), facecolor=SURFACE, squeeze=False)
    for ax, r in zip(axes[0], results):
        ax.set_facecolor(SURFACE)
        ax.imshow(terrain_rgb(t), interpolation="nearest")
        prior = world.prior / world.prior.max()
        ax.imshow(np.ma.masked_less(prior, 0.3), cmap=ListedColormap(["#7d4fd6"]), alpha=0.22, interpolation="nearest")
        nodes = [t.base] + [t.rc(c) for c in r.relays]
        cov = world.link.coverage(nodes) >= world.sc.mission.link_threshold_db
        ax.contour(cov, levels=[0.5], colors=[INK2], linewidths=1.0, linestyles="--")
        if r.trajectory:
            tr = np.array([t.rc(c) for c in r.trajectory])
            ax.plot(tr[:, 1], tr[:, 0], color=COLOR.get(r.planner, INK), lw=1.8)
        for rr, cc in nodes[1:]:
            ax.plot(cc, rr, "^", ms=10, color=INK, mec=SURFACE, mew=1.5)
        ax.plot(t.base[1], t.base[0], "s", ms=10, color=INK, mec=SURFACE)
        cr, cc = t.rc(r.casualty)
        ax.plot(cc, cr, "X", ms=12, color="#e34948", mec=SURFACE, mew=1.5)
        status = f"reported at {r.time_report_s / 60:.1f} min" if r.success else f"not reported ({r.end_state.lower()})"
        ax.set_title(
            f"{NAME.get(r.planner, r.planner)} — {status}\nrelays {r.relays_used}, "
            f"out of link {r.out_of_link_s / 60:.1f} min",
            fontsize=10,
            color=INK,
        )
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(
        title or f"{world.sc.title} (seed {results[0].seed})",
        x=0.01,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color=INK,
    )
    legend = (
        "Grey = impassable · purple = highest initial probability · dashed = final radio coverage · "
        "▲ relay · ■ command post · X casualty"
    )
    if n == 1:
        legend = legend.replace(" · dashed", "\ndashed")
    fig.text(0.01, 0.01, legend, fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.06 if n == 1 else 0.03, 1, 0.94))
    path = Path(path)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
