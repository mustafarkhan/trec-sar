#!/usr/bin/env python3
"""Held-out Monte Carlo benchmark. Same as `trecsar bench`.

python3 scripts/run_experiments.py --runs 200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from trecsar_core.bench import PLANNERS, run_benchmark, variants  # noqa: E402,F401  (re-exported for make_figures)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    a = ap.parse_args()
    run_benchmark(a.runs, a.workers, a.out)
    print((a.out / "summary.md").read_text())


if __name__ == "__main__":
    main()
