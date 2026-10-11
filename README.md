# TREC-SAR — from a fielded tracked UGV to civilian search and rescue

[![ci](https://github.com/mustafarkhan/trec-sar/actions/workflows/ci.yml/badge.svg)](https://github.com/mustafarkhan/trec-sar/actions/workflows/ci.yml)
[![3D mission (Gazebo + Nav2)](https://github.com/mustafarkhan/trec-sar/actions/workflows/sim3d.yml/badge.svg)](https://github.com/mustafarkhan/trec-sar/actions/workflows/sim3d.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy-22314E)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

This repository continues **TREC**, a tele-operated tracked ground robot I worked on as a Project Engineer with the
Government of Pakistan (developed at NUST College of E&ME), and rebuilds its ideas for civilian search and
rescue with modern open-source robotics.

![Mission replay: link-unaware search vs TREC-SAR in the winter forest](media/trec-sar_replay.gif)

**Videos:** [command-line walkthrough (1 min)](media/trec-sar_cli_demo.mp4) · **project walkthrough (2 min):** [`media/trec-sar_github.mp4`](media/trec-sar_github.mp4) — the original project, how the
planner decides, three scenario replays, results, ablation and limits. Every map frame is a recorded simulation run.

## Part 1 — TREC: the original project

**TREC (Tele-operated, Tracked, Reconfigurable UGV)** · Department of Mechatronics, College of Electrical &
Mechanical Engineering, National University of Sciences and Technology (NUST), Pakistan.

| | |
|---|---|
| Platform | Track-wheeled, differential-drive mobile robot; turns about its own centre; high-power drive motors for steep inclines |
| Control | NI cRIO-9012 real-time controller interpreting commands from a laptop control unit; video over IP |
| Specification | 84 × 42 × 20 cm, 80 kg, 8 km/h, two cameras, 30 m night vision |
| Reconfigurable payloads | Manipulator arm with camera, mine-detection payload |
| Operator console | Live video, connection failsafe indicator, continuous battery monitoring with low-battery alarm |

**Milestones**
- Demonstrated to senior government stakeholders.
- Prototype with manipulator handed over for field trials and testing.

<p>
  <img src="docs/media/trec_robot.jpg" alt="TREC tracked UGV with manipulator" height="170">
  <img src="docs/media/trec_mine_detector.jpg" alt="TREC with land-mine detector payload" height="170">
</p>

## Part 2 — TREC-SAR: the civilian successor (independent project, 2026)

TREC-SAR is my independent, open-source redesign of TREC for search and rescue in Europe. It is **not** a government
project. All results below are from simulation.

It answers one operational question:

> **Where should the robot search next — and how does it make sure the command post actually sees the casualty when it finds them?**

A detection is worth nothing until a human at the command post receives it. In forests, tunnels and industrial
sites the radio link is the bottleneck. TREC-SAR plans the search **and** the radio network together: where to look,
where to drop relay nodes, and when to accept a planned, time-bounded link loss.

### What changed from TREC

| TREC (original) | TREC-SAR (civilian) |
|---|---|
| Open-loop tele-operation over Wi-Fi | Probability-driven autonomous search, Nav2 + SLAM |
| Link loss shown by a failsafe indicator | Link margin is a first-class planning constraint |
| Reconfigurable payloads (arm, mine detector) | Payload bay carries a thermal mast and a relay-node dropper |
| Single operator, single robot | Drone cue + UGV + command post |
| 84 × 42 × 20 cm, 80 kg, 8 km/h | Same hull, mass and top speed in the simulation model |

### Simulation benchmark

![Success and relay use](results/success_and_relays.png)

200 held-out simulated missions per policy per scenario (seeds never used for tuning), same casualty location and
detection luck for every policy. Success = casualty reported to the command post within the time limit.

| Scenario | Lawnmower + reactive relays | Greedy + reactive relays | Greedy + planned link loss *(ablation)* | **TREC-SAR** | **TREC-SAR + radio calibration** | Relays used (ablation → TREC-SAR → +calibration) |
|---|---|---|---|---|---|---|
| Boreal forest, winter, 3 relays | 36 % | 42 % | 63 % | **60 %** | **64 %** | 2.4 → **1.2** → 1.6 |
| Forest, only 1 relay | 23 % | 50 % | 62 % | **61 %** | **62 %** | 1.0 → **0.7** → 0.7 |
| Forest, wrong last-known point (~95 m) | 32 % | 39 % | 60 % | **56 %** | **58 %** | 2.5 → **1.3** → 1.8 |
| Forest, radio 1.8× worse than planned | 22 % | 39 % | 61 % | **57 %** | **62 %** | 2.7 → 2.0 → **0.7** |
| Tunnel after rock fall | 90 % | 94 % | 98 % | **98 %** | **98 %** | 2.8 → **0.2** → 0.2 |
| Industrial chemical release | 88 % | 96 % | 98 % | **98 %** | **98 %** | 1.2 → **0.9** → 0.9 |

Full tables with 95 % confidence intervals: [`results/summary.md`](results/summary.md).

**What the numbers say — honestly:**

1. **Link-awareness is the big win.** Robots that are thrown back by a link-loss failsafe and keep re-trying the
   same out-of-range area waste the mission. Planning the link loss explicitly — search autonomously for a bounded
   time, then come back into coverage to report — lifts forest success from about 40 % to about 60 %.
2. **TREC-SAR matches the best policy's success with far fewer relays** (about half in the forest, about 90 % fewer
   in the tunnel), because it places relays only where the probability map says they pay off.
3. **The price is less live video.** In the tunnel TREC-SAR spends about 5.6 min out of link per mission versus about
   1 min for the relay-hungry ablation. Whether that trade is acceptable is an operator decision, and the weights
   are exposed so it can be tuned.
4. **Where it does not help:** in the open industrial site all probability-driven policies perform the same, and
   with a wrong last-known point TREC-SAR is slightly behind the ablation (confidence intervals overlap).

![Time to report](results/time_to_report.png)

### Online radio calibration (new in 0.2)

Every planner above trusts a radio model whose numbers are guesses. On a real site they will be wrong — wet snow
on spruce, a steel structure, a different antenna. TREC-SAR 0.2 **learns the site's radio while it searches**: every
signal-strength reading the robot already receives is one equation of the link model, and a closed-form Bayesian
regression (prior = the planning numbers) updates the path-loss exponent and the attenuation of every terrain class
([`core/trecsar_core/calibrate.py`](core/trecsar_core/calibrate.py)). Coverage predictions, relay placement and
link-loss windows then use the calibrated model. Readings below receiver sensitivity are ignored, so the model only
moves where the radio can actually be heard.

Stress test: the real radio is 1.8× more attenuating than planned (path-loss exponent 2.4 instead of 2.2). In
simulation the estimate converges to 0.20 dB/m for dense spruce (true 0.216) and an exponent of 2.45 (true 2.4).
Over 200 held-out missions:

| Forest, radio 1.8× worse than planned | Success | Median time to report | Failsafe trips | Relays used |
|---|---|---|---|---|
| Greedy + planned link loss *(ablation)* | 61 % | 41 min | 2.7 | 2.7 |
| TREC-SAR with the planning model | 57 % | 54 min | 9.6 | 2.0 |
| **TREC-SAR + online radio calibration** | **62 %** | **37 min** | **2.8** | **0.7** |

Calibration does not change the success rate within the confidence intervals. What it fixes is behaviour: the
uncalibrated robot keeps planning into coverage that does not exist and trips the link-loss failsafe 3.4× as often.
The calibrated robot reports 17 min sooner at the median and uses a quarter of the relays the ablation needs. The
same logic runs on the live robot: `MissionCore` calibrates from `/link/margin_db` with `planner:=trecsar_cal`.

### Thermal person detector (measured)

A YOLO11n detector fine-tuned on the open **HIT-UAV** drone thermal dataset (Suo et al., *Scientific Data* 2023),
person class only, trained and evaluated unattended in GitHub Actions on CPU
([`perception.yml`](.github/workflows/perception.yml), [`perception/train_ci.py`](perception/train_ci.py)).
Numbers are on the **held-out test split (579 images)**, never seen in training:

| Precision | Recall | mAP@0.5 | mAP@0.5:0.95 | Training |
|---|---|---|---|---|
| 0.88 | 0.88 | **0.90** | 0.47 | 25 epochs, 220 min on a CI CPU |

![Detections on held-out thermal test images](results/perception/predictions.png)

The weights ([`perception/weights/hituav_person_yolo11n.pt`](perception/weights/)) plug into the ROS 2
`yolo_detector` node. HIT-UAV is aerial imagery, so this is the drone half of the team; a ground-level thermal
dataset would be needed before trusting it on the UGV camera.

## Quick start

Requires Python 3.10+. Works on Linux, macOS and Windows.

```bash
git clone https://github.com/mustafarkhan/trec-sar.git && cd trec-sar
pip install -e "core[viz]"

trecsar scenarios                                           # list built-in scenarios
trecsar run --scenario forest_winter --seed 1002 --events   # one mission, with its event log
trecsar compare --scenario tunnel --seed 1003 --plot compare.png   # all planners, same mission
trecsar bench --runs 200                                    # the full held-out benchmark (~3 min)
```

Example output:

```
Underground tunnel network — missing worker after rock fall  ·  seed 1003
    lawnmower  NOT REPORTED (FAILED)      relays 4  out-of-link 16.67 min  distance 5775 m  failsafe 17
 greedy_bayes  NOT REPORTED (TIMEOUT)     relays 4  out-of-link 28.63 min  distance 6005 m  failsafe 28
    greedy_sf  REPORTED at 13.25 min      relays 4  out-of-link 1.56 min  distance 1255 m  failsafe 0
      trecsar  REPORTED at 13.2 min       relays 0  out-of-link 8.67 min  distance 1332 m  failsafe 1
```

Every command accepts `--json` for scripting. Python API:

```python
from trecsar_core import World, build, run

world = World(build("hazmat_industrial"))
result = run(world, "trecsar", seed=5, record=True)
print(result.success, result.time_report_s, result.relays_used, result.events[:3])
```

### Model your own site

Paint a map (one pixel = one grid cell, one colour per terrain type), describe it in a few lines of YAML, and
every planner, the benchmark and the plots work on it:

```bash
trecsar compare --site examples/sites/campus/site.yaml --seed 2 --plot campus.png
```

Built-in terrain classes: `open, road, trail, forest, dense_forest, bog, rubble, corridor, water, building, rock,
cliff`; you can add your own with cost, radio loss, canopy and lost-person affinity. See
[`examples/sites/campus/site.yaml`](examples/sites/campus/site.yaml) and [`core/trecsar_core/site.py`](core/trecsar_core/site.py).

### ROS 2

**Headless (no GPU, no Gazebo)** — the full mission stack with a stand-in robot, the same test CI runs on every push:

```bash
cd ros2_ws && colcon build --symlink-install && source install/setup.bash
ros2 launch trecsar_bringup headless.launch.py scenario:=hazmat_industrial seed:=5
ros2 topic echo --once /trecsar/report          # casualty report JSON
```

**3D mission (Gazebo Harmonic + Nav2)** — tested in CI ([`sim3d.yml`](.github/workflows/sim3d.yml)): the
TREC-sized robot drives the industrial site in Gazebo, Nav2 follows the mission planner's route, and the run passes
only if the casualty report reaches the command post. Latest run: about 330 m driven, drone cue fused, one relay
deployed, one link-loss recovery, **casualty reported at 410 s with 1 relay**. CI uses ground-truth localisation;
`localization:=slam` runs slam_toolbox instead. Ubuntu 24.04 + ROS 2 Jazzy, or the Docker image; see
[`docs/RUNNING.md`](docs/RUNNING.md):

```bash
ros2 launch trecsar_bringup bringup.launch.py scenario:=forest_winter planner:=trecsar
```

## Engineering quality

| | |
|---|---|
| Tests | 56 unit, behaviour, calibration, world and CLI tests on Python 3.10–3.13, with coverage |
| ROS 2 | All four packages built in CI on ROS 2 Jazzy; end-to-end headless mission must deliver a casualty report |
| 3D | Gazebo Harmonic + Nav2 mission in CI must find the casualty and deliver the report |
| Perception | Thermal person detector trained and evaluated in CI on HIT-UAV (held-out test mAP@0.5 0.90) |
| Reproducibility | Fixed seeds; tuning seeds (100–159) separate from evaluation seeds (1000–1199); Gazebo worlds regenerated and diffed in CI |
| Code style | `ruff` lint + format, pre-commit hooks |
| Failure analysis | FMEA-style table of failure modes and limitations in [`docs/FAILURE_MODES.md`](docs/FAILURE_MODES.md) |

## What is in the repository

```
core/            trecsar_core: terrain, probability map, radio model, sensor model, planners, mission simulator,
                 live-robot mission logic, custom sites, CLI, benchmark, plotting       (pure Python, tested)
examples/sites/  custom site example (campus park)
scripts/         make_figures.py, make_videos.py (mission replays → MP4), run_experiments.py
results/         summary.md, results.csv, figures
media/           LinkedIn and GitHub videos, README GIF
ros2_ws/src/     trecsar_description  URDF/xacro of the tracked UGV (TREC dimensions)
                 trecsar_gazebo       Gazebo Harmonic worlds generated from the same scenarios
                 trecsar_mission      ROS 2 nodes: mission manager, radio-link simulator, drone stub, detectors,
                                      headless fake robot
                 trecsar_bringup      launch files: 3D (SLAM + Nav2 + RViz) and headless
perception/      HIT-UAV thermal person detector: CI training script, Colab notebook, trained weights
docs/            concept, scenarios (CONOPS), research basis, failure modes, running guide
docker/          ROS 2 Jazzy + Gazebo container
```

## How it works (one paragraph)

The probability map starts from a lost-person distance model around the last known point, weighted by terrain
(people follow trails; nobody is inside a lake). Every camera glimpse that finds nothing lowers the probability
where the robot looked (Bayesian search theory); a drone cue raises it near the cue. For each candidate search goal,
TREC-SAR computes expected detection per metre of travel and then checks the radio: is the goal inside coverage? If
not, can a relay dropped at the last well-connected point on the way cover it? If not, can the robot reach it and
return before the link-loss failsafe — or should it commit to an explicitly authorised link-loss window? The best
scoring option wins; the mission state machine handles relay drops, failsafe returns, reporting and battery reserve.
Details: [`docs/CONCEPT.md`](docs/CONCEPT.md).

## Is this new?

Parts of it are well established, and the repository says so: Bayesian search theory (Koopman, Stone; the US Coast
Guard's SAROPS), lost-person behaviour statistics (Koester), and relay "breadcrumbs" dropped by robots in the DARPA
Subterranean Challenge. What TREC-SAR adds is the **combination**: relay placement and link-loss windows chosen from
the *probability of finding the person*, with the radio model **calibrated online during the search** (methods
from robot channel-estimation research), evaluated on time-to-report rather than time-to-detect, packaged as an
open, reproducible benchmark for civilian SAR (forest, tunnel and hazmat). I have not found this exact combination
in open source, but I make no claim that nobody has done it. See [`docs/RESEARCH.md`](docs/RESEARCH.md).

## Limitations

All results are simulation. Radio, detection and lost-person parameters are plausible placeholders, not field
calibration (online calibration narrows the radio gap but starts from those placeholders). The ROS 2 stack runs end
to end in CI both headless and in Gazebo + Nav2; the CI 3D run uses ground-truth localisation, and nothing has been
tested on hardware. TREC-SAR is not certified
for operational use. Full list:
[`docs/FAILURE_MODES.md`](docs/FAILURE_MODES.md).

## Contributing and citing

Field data, new sites and planners are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md). If you use TREC-SAR in
research, please cite it via [`CITATION.cff`](CITATION.cff) (GitHub shows a "Cite this repository" button).

## License

MIT. Datasets keep their own licences.
