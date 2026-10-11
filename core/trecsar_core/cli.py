"""Command-line interface: `trecsar --help`.

trecsar scenarios
trecsar run --scenario forest_winter --planner trecsar --seed 1002 --plot mission.png
trecsar compare --scenario tunnel --seed 1003 --plot compare.png
trecsar run --site examples/sites/campus/site.yaml
trecsar bench --runs 200 --out results
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .planner import PLANNERS
from .scenarios import SCENARIOS, build
from .sim import World, run


def _world(a) -> World:
    key = a.site or a.scenario
    kw = {"relays": a.relays} if a.relays is not None else {}
    return World(build(key, **kw))


def _summary(r) -> dict:
    return {
        "planner": r.planner,
        "scenario": r.scenario,
        "seed": r.seed,
        "success": r.success,
        "time_detect_min": None if r.time_detect_s is None else round(r.time_detect_s / 60, 2),
        "time_report_min": None if r.time_report_s is None else round(r.time_report_s / 60, 2),
        "out_of_link_min": round(r.out_of_link_s / 60, 2),
        "relays_used": r.relays_used,
        "distance_m": round(r.distance_m),
        "failsafe_events": r.failsafe_events,
        "end_state": r.end_state,
    }


def _print_run(r, events: bool):
    s = _summary(r)
    verdict = f"REPORTED at {s['time_report_min']} min" if r.success else f"NOT REPORTED ({r.end_state})"
    print(
        f"{s['planner']:>13}  {verdict:<26} relays {s['relays_used']}  "
        f"out-of-link {s['out_of_link_min']} min  distance {s['distance_m']} m  failsafe {s['failsafe_events']}"
    )
    if events:
        for t, msg in r.events:
            print(f"{'':>15}{t / 60:7.2f} min  {msg}")


def cmd_scenarios(a):
    for k, f in SCENARIOS.items():
        sc = f()
        t = sc.terrain
        print(
            f"{k:<18} {sc.title}\n{'':<18} {t.shape[0]}x{t.shape[1]} cells @ {t.resolution:g} m, "
            f"{sc.mission.relays} relays, {sc.mission.time_limit_s / 60:.0f} min limit"
        )
    print("\nCustom sites: --site path/to/site.yaml (see examples/sites/campus)")


def cmd_run(a):
    w = _world(a)
    r = run(w, a.planner, a.seed, record=bool(a.plot) or a.events)
    if a.json:
        print(json.dumps(_summary(r), indent=2))
    else:
        print(f"{w.sc.title}  ·  seed {a.seed}")
        _print_run(r, a.events)
    if a.plot:
        from .plot import plot_runs

        print("plot:", plot_runs(w, [r], a.plot))
    return 0


def cmd_compare(a):
    w = _world(a)
    names = a.planners.split(",") if a.planners else list(PLANNERS)
    rs = [run(w, p, a.seed, record=bool(a.plot)) for p in names]
    if a.json:
        print(json.dumps([_summary(r) for r in rs], indent=2))
    else:
        print(f"{w.sc.title}  ·  seed {a.seed}")
        for r in rs:
            _print_run(r, False)
    if a.plot:
        from .plot import plot_runs

        print("plot:", plot_runs(w, rs, a.plot))
    return 0


def cmd_bench(a):
    from .bench import run_benchmark

    run_benchmark(a.runs, a.workers, a.out, a.variants.split(",") if a.variants else None)
    print((Path(a.out) / "summary.md").read_text())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="trecsar", description="Link-aware search planning for rescue ground robots")
    ap.add_argument("--version", action="version", version=f"trecsar {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scenarios", help="list built-in scenarios").set_defaults(fn=cmd_scenarios)

    def common(p):
        p.add_argument("--scenario", default="forest_winter", choices=list(SCENARIOS))
        p.add_argument("--site", help="custom site YAML (overrides --scenario)")
        p.add_argument("--seed", type=int, default=1002)
        p.add_argument("--relays", type=int, help="override the number of relay nodes")
        p.add_argument("--plot", help="write a PNG map of the mission(s)")
        p.add_argument("--json", action="store_true", help="machine-readable output")

    p = sub.add_parser("run", help="simulate one mission")
    common(p)
    p.add_argument("--planner", default="trecsar", choices=list(PLANNERS))
    p.add_argument("--events", action="store_true", help="print the mission event log")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("compare", help="run several planners on the same mission")
    common(p)
    p.add_argument("--planners", help="comma-separated subset (default: all)")
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("bench", help="held-out Monte Carlo benchmark")
    p.add_argument("--runs", type=int, default=200)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--out", default="results")
    p.add_argument("--variants", help="comma-separated subset of benchmark variants")
    p.set_defaults(fn=cmd_bench)

    a = ap.parse_args(argv)
    try:
        return a.fn(a) or 0
    except (KeyError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
