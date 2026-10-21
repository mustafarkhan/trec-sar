"""Held-out Monte Carlo benchmark of search policies.

Used by `trecsar bench` and scripts/run_experiments.py. Planner weights were tuned
on seeds 100-159; evaluation uses seeds 1000+ so reported numbers are held out.
"""

from __future__ import annotations

import csv
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from .scenarios import build
from .sim import World, run

PLANNERS = ["lawnmower", "greedy_bayes", "greedy_sf", "trecsar", "trecsar_cal"]
LABELS = {
    "lawnmower": "Lawnmower sweep + reactive relays",
    "greedy_bayes": "Probability-greedy + reactive relays",
    "greedy_sf": "Probability-greedy + planned link loss (ablation)",
    "trecsar": "TREC-SAR (link-aware, planned relays)",
    "trecsar_cal": "TREC-SAR + online radio calibration",
}
EVAL_SEED0 = 1000


def variants():
    return {
        "forest_winter": ("Forest, winter (3 relays)", dict(key="forest_winter")),
        "forest_1relay": ("Forest, only 1 relay", dict(key="forest_winter", relays=1)),
        "forest_wrong_lkp": ("Forest, wrong last-known point (~95 m)", dict(key="forest_winter", offset=(-12, 10))),
        "forest_radio_worse": (
            "Forest, radio 1.8x worse than planned (wet snow on spruce)",
            dict(key="forest_winter", radio={"rf_scale": 1.8, "exponent": 2.4}),
        ),
        "tunnel": ("Tunnel after rock fall", dict(key="tunnel")),
        "hazmat_industrial": ("Industrial chemical release", dict(key="hazmat_industrial")),
    }


_WORLDS: dict = {}


def variant_world(vkey: str) -> World:
    """World for a benchmark variant key (cached), including its radio and last-known-point mismatches."""
    if vkey not in _WORLDS:
        spec = variants()[vkey][1]
        kw = {"relays": spec["relays"]} if "relays" in spec else {}
        sc = build(spec["key"], **kw)
        if "offset" in spec:
            sc.truth_lkp_offset = spec["offset"]
        if "radio" in spec:
            sc.radio_truth = spec["radio"]
        _WORLDS[vkey] = World(sc)
    return _WORLDS[vkey]


def _job(args):
    vkey, planner, seed = args
    w = variant_world(vkey)
    r = run(w, planner, seed)
    return dict(
        variant=vkey,
        planner=planner,
        seed=seed,
        success=int(r.success),
        time_detect_s=r.time_detect_s,
        time_report_s=r.time_report_s,
        out_of_link_s=round(r.out_of_link_s, 1),
        relays_used=r.relays_used,
        distance_m=round(r.distance_m, 1),
        failsafe_events=r.failsafe_events,
        end_state=r.end_state,
        time_limit_s=w.sc.mission.time_limit_s,
    )


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def summarise(rows):
    out = []
    for vkey, (vtitle, _) in variants().items():
        for p in PLANNERS:
            rs = [r for r in rows if r["variant"] == vkey and r["planner"] == p]
            if not rs:
                continue
            n = len(rs)
            k = sum(r["success"] for r in rs)
            lo, hi = wilson(k, n)
            tl = rs[0]["time_limit_s"]
            t = np.array([r["time_report_s"] if r["success"] else tl for r in rs], float)
            out.append(
                dict(
                    variant=vkey,
                    title=vtitle,
                    planner=p,
                    n=n,
                    success=k / n,
                    ci_lo=lo,
                    ci_hi=hi,
                    median_min=float(np.median(t)) / 60,
                    mean_min=float(t.mean()) / 60,
                    out_of_link_s=float(np.mean([r["out_of_link_s"] for r in rs])),
                    failsafe=float(np.mean([r["failsafe_events"] for r in rs])),
                    relays=float(np.mean([r["relays_used"] for r in rs])),
                    limit_min=tl / 60,
                )
            )
    return out


def write_summary(summary, path, n, seconds):
    lines = [
        "# Results — held-out Monte Carlo",
        "",
        f"{n} runs per planner per scenario (seeds {EVAL_SEED0}–{EVAL_SEED0 + n - 1}), same casualty "
        "location and detection luck for every planner in a given seed. Planner weights were tuned on "
        f"seeds 100–159 only. Runtime {seconds:.0f} s.",
        "",
        "*Success* = a human at the command post received the detection before the time limit. "
        "*Time* counts failures as the full time limit (so medians are conservative). 95 % Wilson "
        "intervals in brackets.",
        "",
    ]
    for vkey, (vtitle, _) in variants().items():
        rows = [s for s in summary if s["variant"] == vkey]
        if not rows:
            continue
        lines += [
            f"## {vtitle}",
            "",
            "| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |",
            "|---|---|---|---|---|---|---|",
        ]
        for s in rows:
            lines.append(
                f"| {LABELS[s['planner']]} | {s['success']:.0%} [{s['ci_lo']:.0%}–{s['ci_hi']:.0%}] | "
                f"{s['median_min']:.1f} min | {s['mean_min']:.1f} min | {s['out_of_link_s']:.0f} s | "
                f"{s['failsafe']:.1f} | {s['relays']:.1f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def run_benchmark(
    runs: int = 200, workers: int = 2, out: Path | str = "results", variant_keys: list[str] | None = None
) -> list[dict]:
    """Run every planner on every variant; write results.csv and summary.md into `out`."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    keys = variant_keys or list(variants())
    jobs = [(v, p, EVAL_SEED0 + s) for v in keys for p in PLANNERS for s in range(runs)]
    t0 = time.time()
    if workers > 1:
        with Pool(workers) as pool:
            rows = pool.map(_job, jobs, chunksize=8)
    else:
        rows = [_job(j) for j in jobs]
    secs = time.time() - t0
    with open(out / "results.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    summary = summarise(rows)
    write_summary(summary, out / "summary.md", runs, secs)
    return summary
