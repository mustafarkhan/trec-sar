# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

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
