"""Held-out Monte Carlo benchmark of search policies.

Used by `trecsar bench` and scripts/run_experiments.py. Planner weights were tuned
on one terrain per scenario (terrain seed 0, casualty seeds 100-159). The benchmark
therefore holds out both: it runs on freshly generated terrains (seeds 1-8) with
casualty seeds 1000+. `--reference` runs the tuning terrain instead, which is the
terrain used for the maps, replays and Gazebo worlds.
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
REFERENCE_TERRAIN = 0  # the terrain the planner weights were tuned on
HELD_OUT_TERRAINS = (1, 2, 3, 4, 5, 6, 7, 8)


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
        "urban_collapse": ("Urban block after an earthquake", dict(key="urban_collapse")),
        "road_tunnel": ("Twin-bore road tunnel fire (1 km)", dict(key="road_tunnel")),
        # European two-link radio: 2.4 GHz video plus a duty-cycle-limited 868 MHz telemetry/report link
        "forest_eu868_500mw": (
            "Forest + 868 MHz report link (500 mW, 10 % duty cycle)",
            dict(key="forest_winter", report="eu868_500mw"),
        ),
        "forest_eu868_25mw": (
            "Forest + 868 MHz report link (25 mW, 1 % duty cycle)",
            dict(key="forest_winter", report="eu868_25mw"),
        ),
        "urban_eu868_500mw": (
            "Urban earthquake + 868 MHz report link (500 mW, 10 % duty cycle)",
            dict(key="urban_collapse", report="eu868_500mw"),
        ),
        "tunnel_eu868_500mw": (
            "Tunnel + 868 MHz report link (500 mW, 10 % duty cycle)",
            dict(key="tunnel", report="eu868_500mw"),
        ),
    }


_WORLDS: dict = {}


def variant_world(vkey: str, terrain: int = REFERENCE_TERRAIN) -> World:
    """World for a benchmark variant key on one generated terrain (cached), including the variant's
    radio and last-known-point mismatches."""
    if (vkey, terrain) not in _WORLDS:
        if len(_WORLDS) >= 12:  # each world holds path and radio caches; keep memory bounded
            _WORLDS.pop(next(iter(_WORLDS)))
        spec = variants()[vkey][1]
        kw = {"relays": spec["relays"]} if "relays" in spec else {}
        sc = build(spec["key"], seed=terrain, **kw)
        if "offset" in spec:
            sc.truth_lkp_offset = spec["offset"]
        if "radio" in spec:
            sc.radio_truth = spec["radio"]
        if "report" in spec:
            sc.mission.report_radio = spec["report"]
        _WORLDS[(vkey, terrain)] = World(sc)
    return _WORLDS[(vkey, terrain)]


def _job(args):
    vkey, terrain, planner, seed = args
    w = variant_world(vkey, terrain)
    r = run(w, planner, seed)
    return dict(
        variant=vkey,
        terrain=terrain,
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
        report_channel=r.report_channel,
        time_alert_s=r.time_alert_s,
        unsupervised_s=round(r.unsupervised_s, 1),
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
            ta = np.array([r["time_alert_s"] if r["time_alert_s"] is not None else tl for r in rs], float)
            per_terrain = [
                np.mean([r["success"] for r in rs if r["terrain"] == k]) for k in sorted({r["terrain"] for r in rs})
            ]
            out.append(
                dict(
                    variant=vkey,
                    title=vtitle,
                    planner=p,
                    n=n,
                    success=k / n,
                    ci_lo=lo,
                    ci_hi=hi,
                    terrains=len(per_terrain),
                    terrain_lo=float(min(per_terrain)),
                    terrain_hi=float(max(per_terrain)),
                    median_min=float(np.median(t)) / 60,
                    alert_median_min=float(np.median(ta)) / 60,
                    mean_min=float(t.mean()) / 60,
                    out_of_link_s=float(np.mean([r["out_of_link_s"] for r in rs])),
                    failsafe=float(np.mean([r["failsafe_events"] for r in rs])),
                    relays=float(np.mean([r["relays_used"] for r in rs])),
                    two_link="report" in variants()[vkey][1],
                    narrowband=float(np.mean([r["report_channel"] == "narrowband" for r in rs])),
                    unsupervised_s=float(np.mean([r["unsupervised_s"] for r in rs])),
                    limit_min=tl / 60,
                )
            )
    return out


def write_summary(summary, path, n, seconds, terrains=(REFERENCE_TERRAIN,)):
    held_out = REFERENCE_TERRAIN not in terrains
    multi = len(terrains) > 1
    lines = [
        "# Results — held-out Monte Carlo" if held_out else "# Results — reference (tuning) terrain",
        "",
        f"{n} runs per planner per scenario (casualty seeds {EVAL_SEED0}–{EVAL_SEED0 + n - 1}"
        + (f", spread evenly over generated terrains {', '.join(str(k) for k in terrains)}" if multi else "")
        + "), same terrain, casualty location and detection luck for every planner in a given run. "
        "Planner weights were tuned on terrain 0 with casualty seeds 100–159 only"
        + (
            ", so both the terrains and the casualties here are held out. "
            if held_out
            else "; this table is that same terrain (the one shown in the maps, replays and Gazebo worlds), "
            "so only the casualties are held out. Results on freshly generated terrains are in `results/summary.md`. "
        )
        + f"Runtime {seconds:.0f} s.",
        "",
        "*Success* = a human at the command post received the detection before the time limit (with an image "
        "they can confirm: live video, or a thumbnail sent over the narrowband link). "
        "*Time* counts failures as the full time limit (so medians are conservative). 95 % Wilson "
        "intervals in brackets"
        + (
            "; they treat runs as independent and ignore that runs share terrains, so read them together with "
            "the *per-terrain range* column (lowest and highest success on a single terrain)."
            if multi
            else "."
        ),
        "",
    ]
    for vkey, (vtitle, _) in variants().items():
        rows = [s for s in summary if s["variant"] == vkey]
        if not rows:
            continue
        two = rows[0]["two_link"]
        lines += [
            f"## {vtitle}",
            "",
            "| Policy | Success |"
            + (" Per-terrain range |" if multi else "")
            + (" Median time to position alert |" if two else "")
            + " Median time | Mean time | "
            + (
                "Time without live video | Time unsupervised | Reports sent over 868 MHz |"
                if two
                else "Time out of link |"
            )
            + " Failsafe trips | Relays used |",
            "|---|---|---|---|---|---|---|" + ("---|" if multi else "") + ("---|---|---|" if two else ""),
        ]
        for s in rows:
            lines.append(
                f"| {LABELS[s['planner']]} | {s['success']:.0%} [{s['ci_lo']:.0%}–{s['ci_hi']:.0%}] | "
                + (f"{s['terrain_lo']:.0%}–{s['terrain_hi']:.0%} | " if multi else "")
                + (f"{s['alert_median_min']:.1f} min | " if two else "")
                + f"{s['median_min']:.1f} min | {s['mean_min']:.1f} min | {s['out_of_link_s']:.0f} s | "
                + (f"{s['unsupervised_s']:.0f} s | {s['narrowband']:.0%} | " if two else "")
                + f"{s['failsafe']:.1f} | {s['relays']:.1f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines))


def run_benchmark(
    runs: int = 200,
    workers: int = 2,
    out: Path | str = "results",
    variant_keys: list[str] | None = None,
    terrains: tuple[int, ...] = HELD_OUT_TERRAINS,
) -> list[dict]:
    """Run every planner on every variant; write results.csv and summary.md into `out`.

    `runs` missions per planner per variant are spread evenly over `terrains` (generated-terrain
    seeds); run i uses casualty seed EVAL_SEED0 + i on terrain terrains[i * len(terrains) // runs].
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    keys = variant_keys or list(variants())
    terrains = tuple(terrains)[: max(1, runs)]
    # ordered by terrain so each worker builds a world once and reuses it
    jobs = [
        (v, terrains[s * len(terrains) // runs], p, EVAL_SEED0 + s) for v in keys for s in range(runs) for p in PLANNERS
    ]
    t0 = time.time()
    if workers > 1:
        with Pool(workers) as pool:
            rows = pool.map(_job, jobs, chunksize=5 * len(PLANNERS))
    else:
        rows = [_job(j) for j in jobs]
    secs = time.time() - t0
    with open(out / "results.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    summary = summarise(rows)
    write_summary(summary, out / "summary.md", runs, secs, terrains)
    return summary
