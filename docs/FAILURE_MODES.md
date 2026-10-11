# Failure modes and limitations

Written in an FMEA style: what can fail, what happens, how TREC-SAR handles it, and what is still open.
Severity: H = could cost the casualty, M = delays the mission, L = nuisance.

| # | Failure | Effect | Current handling | Open |
|---|---|---|---|---|
| 1 | Link lost unexpectedly | Operator blind, robot may wander | Failsafe after 30–45 s → drive to nearest covered cell; goal blocked for 10 min | Real radios fade gradually; model is binary at the threshold (H) |
| 2 | Person found while out of link | Report delayed | REPORT state drives back into coverage before anything else | Robot could also drop a relay at the casualty (future) (M) |
| 3 | Relays used up early | Deep areas unreachable with live video | Planner discounts relay use; store-and-forward fallback | Relay pick-up/reuse not modelled (M) |
| 4 | Wrong last-known point | Search starts in the wrong place | Bayesian updates move belief; tested at ~95 m offset (success 56–60 %) | Larger errors untested; no re-planning from new witness info (H) |
| 5 | Drone false cue | Robot pulled to the wrong place | Cue fused with 0.6 reliability, not treated as truth | Reliability not learned from data (M) |
| 6 | Missed detection in canopy | Casualty passed by | Canopy term lowers POD and the map keeps residual probability | Real thermal performance under spruce unknown (H) |
| 7 | Battery loss in cold | Robot stranded | 25 % derate, return-to-home reserve × 1.3 | No battery heating model (M) |
| 8 | Terrain misclassified (thin ice, bog) | Robot stuck or lost | Lake = no-go by policy; bog high cost | No traversability learning (H) |
| 9 | Localisation drift (no GPS in tunnel) | Map and relays misplaced | 3D demo uses SLAM; 2D sim assumes perfect pose | Ground-truth pose shortcut in 3D (H) |
| 10 | Detector confusion (animals, warm rocks) | False report | Report needs operator confirmation on video | Not modelled in Monte Carlo (L) |

## Simulation-to-reality gaps (stated plainly)

- **All numbers are simulation.** No hardware test has been done.
- **Parameters are placeholders**, chosen for the right order of magnitude: lost-person distances, radio budget and
  attenuation, detection range, energy use.
- **One terrain per scenario.** Results vary with the map; the experiment fixes the map and varies casualty
  location and detection luck.
- **Weights were tuned** on seeds 100–159 and evaluated on seeds 1000–1199. Tuning was light (a handful of
  settings), and the ablation was run with the same care so the comparison is fair.
- **3D stack:** the ROS 2 packages are written against Jazzy + Gazebo Harmonic APIs and syntax-checked, and the
  mission logic they wrap is unit-tested, but the full launch has not been run end to end in this repository's CI.
  Expect to tune Nav2 and the bridge on first run (see RUNNING.md).

## Ethics and dual use

TREC-SAR is designed for civilian search and rescue. The original TREC platform carried mine-detection
payloads; none of that is part of this project. Public material should not include operational details of
earlier trials or identifiable personnel photos.
