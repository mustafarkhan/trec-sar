# Contributing to TREC-SAR

Thank you for helping. Rescue robotics benefits from people who have run real searches, built radios, or
operated robots in bad conditions — field experience is as welcome as code.

## Ways to help

- **Field data.** Lost-person statistics, radio measurements in forests or tunnels, thermal detection ranges.
  Replacing a placeholder model with measured data is the most valuable contribution.
- **New sites.** Add a map under `examples/sites/` (see `examples/sites/campus`).
- **Planners.** Implement a policy in `core/trecsar_core/planner.py` and add it to the benchmark.
- **ROS 2 / hardware.** Tuning Nav2 for real tracked platforms, real detectors, real relay hardware.

## Development setup

```bash
git clone https://github.com/mustafarkhan/trec-sar.git && cd trec-sar
python3 -m venv .venv && source .venv/bin/activate
pip install -e "core[dev]"
pre-commit install          # ruff, secret scan and commit-message checks on every commit
pytest -q core/tests
```

## Rules of the road

1. **Tests with every change.** New behaviour needs a test in `core/tests/`. CI runs on Python 3.10–3.13 plus a
   ROS 2 Jazzy build and an end-to-end headless mission.
2. **Results stay honest.** If a change affects planner behaviour, re-run `trecsar bench --runs 200` and update
   `results/` and the README tables in the same pull request. Tune only on seeds 100–159; report on 1000+.
3. **Say what is assumed.** New models document their parameters and where to calibrate them
   (see `docs/RESEARCH.md`).
4. **Civilian scope.** This project is for search and rescue. Weapon or targeting features will not be accepted.
5. `ruff check .` and `ruff format .` must pass.
6. **Plain commits.** No co-author or session trailers, no links to chat sessions, and no personal working notes
   (`private/`, `notes/`, `*.private.*` are ignored and rejected). CI checks this with
   `scripts/check_repo_hygiene.py` and scans the full history for secrets with gitleaks.

## Commit and PR style

Short imperative commit subjects ("Add tunnel relay test"). One topic per pull request. Describe what changed,
why, and how you tested it.
