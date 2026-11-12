# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- CI `hygiene` job: `scripts/check_repo_hygiene.py` checks commit authorship, rejects co-author or session
  trailers and personal-notes files; gitleaks scans the full history for secrets. The same checks run as
  pre-commit and commit-msg hooks.
- Videos and README GIF re-rendered: new scenes for online radio calibration (a replay in the radio-mismatch forest
  and the 200-mission comparison) and for the Gazebo + Nav2 mission from CI (`results/sim3d/hazmat_ci_run.json`).
  `make_videos.py --which gif` regenerates the README GIF.
- `trecsar_core.bench.variant_world()` builds the world for any benchmark variant, including radio and
  last-known-point mismatches.

### Changed
- **Benchmark now holds out terrains as well as casualty seeds.** `trecsar bench` runs 25 casualties on each of 8
  freshly generated terrains per scenario; `--reference` runs the tuning terrain (terrain 0), whose results move to
  `results/reference_terrain/`. Summaries show the per-terrain range next to the confidence interval.
- **Headline corrected.** On held-out terrains the probability-driven policies reach the same forest success
  (73–74 %); TREC-SAR's benefit is the relay saving (half in the forest and chemical site, about 70 % fewer in the
  tunnel) and robustness with one relay or a wrong radio model. The earlier "about 40 % to 60 %" forest gain was
  specific to the tuning terrain. README, research notes and failure modes are rewritten accordingly.
- CI: least-privilege token permissions, cancelled superseded PR runs, gitleaks download verified by checksum.
- Licence section states that Ultralytics YOLO11 and the bundled detector weights are AGPL-3.0, not MIT.
- Replays draw the coverage the radios really achieve and count failsafe trips in the status line.
- TREC is described in academic and industrial terms (Government of Pakistan, NUST College of E&ME).

### Fixed
- Custom sites: overriding one field of a terrain class in `site.yaml` (for example only `rf_db_per_m`) silently
  made the whole class impassable. Missing fields now keep the base class's values; unknown keys are rejected.
- README example output listed four planners; `trecsar compare` prints five.
- Wrong venue for Malmirchegini & Mostofi in the calibration module's docstring.
- 3D run distance in the README and v0.2.0 notes: the robot drove more than 450 m (lower bound from the
  once-a-minute ground-truth track), not about 330 m.

## [0.2.0] — 2026-10-12

### Added
- **Online radio calibration** (`trecsar_core.calibrate.RadioCalibrator`): Bayesian linear regression of path-loss
  exponent and per-terrain attenuation from signal-strength readings, used by the new `trecsar_cal` planner in
  simulation and by `MissionCore` on the live robot.
- Benchmark variant *Forest, radio 1.8× worse than planned*; the simulator separates the radio's true propagation
  from the planner's model (`Scenario.radio_truth`).
- Full 3D mission in CI (`sim3d.yml`): Gazebo Harmonic + Nav2 + mission nodes; passes only when the casualty
  report reaches the command post. Ground-truth localisation node for CI; slam_toolbox remains available.
- Thermal person detector trained and evaluated in CI on HIT-UAV (`perception.yml`): held-out test mAP@0.5 0.90,
  precision 0.88, recall 0.88; weights in `perception/weights/`.
- Tests: calibration, Gazebo world checks (visual-only geometry below the lidar), robot model.

### Fixed
- Gas plume in the Gazebo world was a 2 m translucent volume that the GPU lidar saw as a wall; now a ground decal.
- Lidar moved to the top of the mast (it was seeing the robot's own relay bay).
- Skid-steer traction (centre wheels carry traction), Nav2 controller tuning, route segmentation for long goals,
  link-recovery retries, a taboo list for goals Nav2 could not reach.
- When the radio model is wrong, link recovery falls back to the nearest radio node instead of failing.

## [0.1.0] — 2026-10-11

### Added
- `trecsar_core`: terrain model, Bayesian probability map, radio link model with relay networks, sensor model,
  four search planners (lawnmower, probability-greedy, greedy + planned link loss, TREC-SAR), mission
  simulator, event-driven mission logic for live robots, mission replay recording.
- Three built-in scenarios: winter boreal forest, tunnel after a rock fall, industrial chemical release.
- Custom sites from a PNG map plus a YAML legend (`--site`), with a campus example.
- `trecsar` command-line tool: `scenarios`, `run`, `compare`, `bench`.
- Held-out benchmark: 4,000 missions, 95 % Wilson intervals, ablation study.
- ROS 2 Jazzy packages: URDF of the TREC-heritage UGV, Gazebo Harmonic worlds generated from the scenarios,
  mission manager, radio-link simulator with operator-video gating, drone stub, model-based and YOLO detectors,
  headless fake robot, SLAM + Nav2 bringup.
- Perception pipeline: VOC→YOLO converter and Colab notebook for thermal person detection on HIT-UAV.
- CI: ruff, tests on Python 3.10–3.13 with coverage, CLI smoke tests, ROS 2 build and an end-to-end headless
  mission test.
- Videos and figures rendered from recorded simulation runs, and a command-line walkthrough video whose terminal
  output is captured from real commands at render time (`scripts/make_cli_video.py`).
