# Failure modes and limitations

Written in an FMEA style: what can fail, what happens, how TREC-SAR handles it, and what is still open.
Severity: H = could cost the casualty, M = delays the mission, L = nuisance.

| # | Failure | Effect | Current handling | Open |
|---|---|---|---|---|
| 1 | Link lost unexpectedly | Operator blind, robot may wander | Failsafe after 30–45 s → drive to nearest covered cell; goal blocked for 10 min | Real radios fade gradually; model is binary at the threshold (H) |
| 2 | Person found while out of link | Report delayed | REPORT state drives back into coverage before anything else | Robot could also drop a relay at the casualty (future) (M) |
| 3 | Relays used up early | Deep areas unreachable with live video | Planner discounts relay use; store-and-forward fallback | Relay pick-up/reuse not modelled (M) |
| 4 | Wrong last-known point | Search starts in the wrong place | Bayesian updates move belief; tested at ~95 m offset (success 67–68 %) | Larger errors untested; no re-planning from new witness info (H) |
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
- **Terrain matters more than policy.** The benchmark runs on eight generated terrains per scenario; on single
  terrains the same policy's success ranges from 48 % to 92 % in the forest. All terrains of a scenario still share
  its fixed features (ridge, lake, trail, command post), so this is variation within one kind of site.
- **Tuning-terrain bias (found in the November 2026 audit).** Weights were tuned on terrain 0 with casualty seeds
  100–159, and results were first reported on that same terrain. There the reactive baseline does badly, which
  made link-aware planning look like a 40 % → 60 % gain. On held-out terrains the success rates are equal and the
  benefit is the relay saving. The benchmark now holds out terrains as well as casualty seeds.
- **Confidence intervals** treat runs as independent although 25 runs share each terrain, so they are too narrow
  for claims about new terrains; the summary shows the per-terrain range next to them.
- **3D stack:** CI runs the full mission in Gazebo Harmonic with Nav2 and requires a delivered casualty report.
  That run uses ground-truth localisation; with `localization:=slam`, slam_toolbox can drift in the wide,
  feature-poor yard, and that mode is not gated in CI. Gazebo's lidar sees *visual* geometry, so decorative
  volumes (the plume) must stay below the scan plane; a test enforces this.
- **Radio calibration** learns only what the robot can hear: classes the robot never has a link through (for
  example behind the granite ridge) stay at the prior value. Readings are treated as independent, which ignores
  spatially correlated shadowing, so the model can be overconfident.

- **New scenarios (0.3)** are procedural like the others. The earthquake block has no voids, aftershocks or dust;
  the road tunnel has no heat model and assumes the robot can pass between stopped vehicles. The planner was not
  retuned for them, which is a fair test of transfer but also means their numbers could improve or get worse with
  site-specific tuning.
- **Two-link missions** assume relay nodes repeat both bands and treat narrowband telemetry as adequate
  supervision; see `docs/EU_RADIO.md` for the list of what the airtime model leaves out.

## Ethics and dual use

TREC-SAR is designed for civilian search and rescue. The original TREC platform carried mine-detection
payloads; none of that is part of this project. Public material should not include operational details of
earlier trials or identifiable personnel photos.
