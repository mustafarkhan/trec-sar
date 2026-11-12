# Research basis and positioning

TREC-SAR stands on established work. This page says what is borrowed, what is new, and what is assumed.

## Borrowed foundations

| Idea | Source | Used for |
|---|---|---|
| Optimal search, probability of detection, Bayesian updating after unsuccessful search | B. O. Koopman, *Search and Screening* (1946/1980); L. D. Stone, *Theory of Optimal Search* (1975) | Probability map and negative-information updates |
| Operational Bayesian SAR planning | Kratzke, Stone & Frost, "Search and Rescue Optimal Planning System" (SAROPS), FUSION 2010 | "Probability of success" framing; rest-of-world mass |
| Lost-person behaviour by category | R. J. Koester, *Lost Person Behavior* (dbS Productions, 2008); International Search & Rescue Incident Database (ISRID) | Distance-from-LKP prior (parameters here are placeholders) |
| Robots dropping communication relays | Teams in the DARPA Subterranean Challenge (2018–2021) | Reactive "breadcrumb" baseline |
| Disaster robotics practice | R. R. Murphy, *Disaster Robotics* (MIT Press, 2014) | Operator-in-the-loop framing, what fails in the field |
| Aerial person detection for SAR | Božić-Štulić et al., HERIDAL, *IJCV* 2019; Pyrrö, Naseri & Jung, "Rethinking Drone-Based Search and Rescue with Aerial Person Detection", arXiv:2111.09406 (Aalto University / Accenture) | Drone detector and SAR-specific evaluation |
| Thermal drone dataset | Suo et al., "HIT-UAV", *Scientific Data* 10:227 (2023) | Training the aerial person detector |
| Vegetation radio attenuation | ITU-R Recommendation P.833 | Order of magnitude of forest attenuation |
| Predicting the channel from robot-collected samples | M. Malmirchegini & Y. Mostofi, "On the spatial predictability of communication channels", *IEEE Trans. Wireless Communications* 11(3), 2012; J. Fink & V. Kumar, "Online methods for radio signal mapping with mobile robots", ICRA 2010 | Online calibration of path loss and per-terrain attenuation |
| Bayesian linear regression | C. M. Bishop, *Pattern Recognition and Machine Learning* (2006), §3.3 | Closed-form posterior over radio parameters, prior = planning model |

## What TREC-SAR adds

1. **Relay placement driven by the probability map**, not by signal strength alone. Relays are dropped at the last
   well-connected point on the way to an area that is both likely and out of coverage.
2. **Planned link-loss windows** ("store and forward") as an explicit planning option with a time budget, so the
   failsafe protects the robot from *unplanned* loss without stopping deliberate excursions.
3. **Time-to-report as the outcome metric**, with an ablation that separates the two ideas above.
4. **Online radio calibration feeding the search planner**: signal-strength readings update the path-loss exponent
   and per-terrain attenuation during the mission, and relay placement and link-loss windows use the updated model.
   Under a radio 1.8× worse than planned this cuts failsafe trips 3.7× and median time-to-report from 47 to 36 min
   (held-out terrains).
5. **An open, reproducible civilian benchmark**: three operational scenarios plus stress variants (fewer relays,
   wrong last-known point, wrong radio model), five policies, held-out terrains and casualty seeds, confidence
   intervals, and a 3D Gazebo world generated from the reference terrain in which the full mission is run in CI.

Communication-aware planning is an active research area in multi-robot exploration; TREC-SAR does not claim to be
the first to consider radio in planning. The contribution is the specific SAR combination and the open benchmark.

## Key findings from the ablation (held-out terrains)

- With three relays and a correct radio model, all probability-driven policies reach the same forest success
  (73–74 %). **Probability-driven relay placement then delivers that success with half the relays** (forest,
  chemical site) **or about 70 % fewer** (tunnel), at the cost of more time without live video.
- **Planning the link loss** separates the policies only when the reactive habit fails: one relay (62 % against
  73–74 %) or a radio worse than planned (60 % against 68–70 %).
- An uncalibrated TREC-SAR under a wrong radio model is the worst probability-driven policy on time; calibration
  repairs it.

Up to version 0.2 this page reported a larger effect ("most of the success gain comes from planning the link
loss", about 40 % to 60 %). That was measured on the single terrain used for tuning, where the reactive baseline
happens to do badly. It did not generalise to freshly generated terrains and has been withdrawn; the old numbers
are in `results/reference_terrain/`.

## Assumptions that would change the answer

- Radio: 2.4 GHz budget at the European limit (20 dBm e.i.r.p., 4 dBi receive gain, −90 dBm sensitivity). A
  sub-GHz link reaches much further in forest. This is now tested rather than assumed: with a legal 868 MHz
  telemetry and report link every policy is supervised over most of the forest and needs few relays, while the
  tunnel result is unchanged. See `docs/EU_RADIO.md`.
- Failsafe policy for baselines: 30–45 s, then return to coverage. A more permissive failsafe narrows the gap
  between baselines and the planned-link-loss policies.
- Perfect localisation and a known map in the 2D simulator.
