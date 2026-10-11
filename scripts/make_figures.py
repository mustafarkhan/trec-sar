#!/usr/bin/env python3
"""Figures for the README: success rates, time-to-report curves, relays, scenario maps.

    python3 scripts/make_figures.py          # needs results/results.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "scripts"))

from trecsar_core import World, build, run  # noqa: E402
from run_experiments import PLANNERS, variants  # noqa: E402

OUT = ROOT / "results"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLOR = {"trecsar": "#2a78d6", "greedy_sf": "#eb6834", "greedy_bayes": "#1baf7a", "lawnmower": "#eda100"}
SHORT = {"trecsar": "TREC-SAR", "greedy_sf": "Greedy + planned link loss",
         "greedy_bayes": "Greedy + reactive relays", "lawnmower": "Lawnmower + reactive relays"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans",
})


def load():
    with open(OUT / "results.csv") as f:
        return list(csv.DictReader(f))


def success_and_relays(rows):
    vs = variants()
    fig, axes = plt.subplots(2, len(vs), figsize=(17, 6.4), sharey="row")
    order = list(reversed(PLANNERS))     # TREC-SAR on top
    for j, (vkey, (vtitle, _)) in enumerate(vs.items()):
        for i, metric in enumerate(("success", "relays_used")):
            ax = axes[i, j]
            vals = []
            for p in order:
                rs = [r for r in rows if r["variant"] == vkey and r["planner"] == p]
                vals.append(np.mean([float(r[metric]) for r in rs]))
            y = np.arange(len(order))
            ax.barh(y, vals, height=0.62, color=[COLOR[p] for p in order], edgecolor=SURFACE, linewidth=2)
            for yy, v in zip(y, vals):
                ax.text(v + (0.02 if metric == "success" else 0.06), yy,
                        f"{v:.0%}" if metric == "success" else f"{v:.1f}", va="center", fontsize=9, color=INK)
            ax.set_yticks(y, [SHORT[p] for p in order])
            ax.grid(axis="x", color=GRID, linewidth=0.8)
            ax.set_axisbelow(True)
            if metric == "success":
                ax.set_xlim(0, 1.18)
                ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
                ax.set_title(vtitle, fontsize=10)
            else:
                ax.set_xlim(0, 3.6)
        axes[0, 0].set_ylabel("Casualty reported\nwithin time limit", fontsize=9)
        axes[1, 0].set_ylabel("Relays used\n(mean per mission)", fontsize=9)
    fig.suptitle("Success and relay use — 200 held-out runs per bar", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "success_and_relays.png", dpi=150)
    plt.close(fig)


def time_curves(rows):
    keys = ["forest_winter", "forest_1relay", "tunnel", "hazmat_industrial"]
    vs = variants()
    fig, axes = plt.subplots(1, len(keys), figsize=(17, 4.2))
    for ax, vkey in zip(axes, keys):
        for p in PLANNERS:
            rs = [r for r in rows if r["variant"] == vkey and r["planner"] == p]
            tl = float(rs[0]["time_limit_s"]) / 60
            t = np.sort([float(r["time_report_s"]) / 60 for r in rs if r["success"] == "1"])
            xs = np.concatenate([[0], t, [tl]])
            ys = np.concatenate([[0], np.arange(1, len(t) + 1) / len(rs), [len(t) / len(rs)]])
            ax.step(xs, ys, where="post", color=COLOR[p], linewidth=2.2 if p == "trecsar" else 1.6, label=SHORT[p])
        ax.set_title(vs[vkey][0], fontsize=10)
        ax.set_xlabel("Minutes since robot launch")
        ax.set_ylim(0, 1.02)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.grid(color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Casualties reported so far")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=4, frameon=False, fontsize=9)
    fig.suptitle("How fast the command post gets the casualty on video", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(OUT / "time_to_report.png", dpi=150)
    plt.close(fig)


def terrain_rgb(t):
    """Muted terrain basemap: lighter = easier ground."""
    img = np.ones(t.shape + (3,)) * np.array([0.93, 0.95, 0.91])
    shade = {"dense spruce": (0.78, 0.86, 0.78), "bog (suo)": (0.86, 0.84, 0.74), "trail": (0.97, 0.94, 0.86),
             "road": (0.86, 0.86, 0.86), "tunnels": (0.96, 0.95, 0.92), "rock-fall rubble": (0.80, 0.74, 0.68),
             "pipe racks": (0.86, 0.86, 0.90), "gas plume (no humans)": (0.98, 0.88, 0.84)}
    for name, mask in t.labels.items():
        if name in shade:
            img[mask] = shade[name]
    img[~t.passable] = (0.45, 0.47, 0.50)
    if "lake (no-go: ice not trusted)" in t.labels:
        img[t.labels["lake (no-go: ice not trusted)"]] = (0.70, 0.80, 0.90)
    return img


def scenario_map(key, seed):
    w = World(build(key))
    t = w.sc.terrain
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2))
    for ax, p in zip(axes, ["greedy_bayes", "trecsar"]):
        r = run(w, p, seed, record=True)
        ax.imshow(terrain_rgb(t), interpolation="nearest")
        prior = w.prior / w.prior.max()
        ax.imshow(np.ma.masked_less(prior, 0.3), cmap=ListedColormap(["#7d4fd6"]), alpha=0.22,
                  interpolation="nearest")
        nodes = [t.base] + [t.rc(c) for c in r.relays]
        cov = w.link.coverage(nodes)
        ax.contour(cov >= w.sc.mission.link_threshold_db, levels=[0.5], colors=[INK2], linewidths=1.0,
                   linestyles="--")
        tr = np.array([t.rc(c) for c in r.trajectory])
        ax.plot(tr[:, 1], tr[:, 0], color=COLOR[p], linewidth=1.8)
        for (rr, cc) in nodes[1:]:
            ax.plot(cc, rr, marker="^", markersize=10, color=INK, markeredgecolor=SURFACE, markeredgewidth=1.5)
        ax.plot(t.base[1], t.base[0], marker="s", markersize=10, color=INK, markeredgecolor=SURFACE)
        ax.annotate("command post", (t.base[1], t.base[0]), xytext=(6, -8), textcoords="offset points",
                    fontsize=8, color=INK)
        cr, cc_ = t.rc(r.casualty)
        ax.plot(cc_, cr, marker="X", markersize=12, color="#e34948", markeredgecolor=SURFACE, markeredgewidth=1.5)
        status = f"reported at {r.time_report_s / 60:.1f} min" if r.success else f"not reported ({r.end_state.lower()})"
        ax.set_title(f"{SHORT[p]} — {status}\nrelays {r.relays_used}, out of link {r.out_of_link_s / 60:.1f} min",
                     fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"{w.sc.title} (seed {seed})", x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, 0.015, "Grey = impassable · purple tint = highest initial probability · dashed = live radio coverage "
             "(final) · ▲ relay · ■ command post · ✕ casualty", fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(OUT / f"map_{key}.png", dpi=130)
    plt.close(fig)


def pick_seed(key, lo=1000, hi=1200):
    """First held-out seed where TREC-SAR reports and the link-unaware greedy policy does not."""
    w = World(build(key))
    for s in range(lo, hi):
        a, b = run(w, "trecsar", s), run(w, "greedy_bayes", s)
        if a.success and not b.success:
            return s
    for s in range(lo, hi):
        a, b = run(w, "trecsar", s), run(w, "greedy_bayes", s)
        if a.success and b.success and a.time_report_s < b.time_report_s:
            return s
    return lo


def main():
    rows = load()
    success_and_relays(rows)
    time_curves(rows)
    for key in ["forest_winter", "tunnel", "hazmat_industrial"]:
        s = pick_seed(key)
        scenario_map(key, s)
        print(key, "map seed", s)
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
