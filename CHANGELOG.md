# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

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
- Videos and figures rendered from recorded simulation runs.
