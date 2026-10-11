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

## What TREC-SAR adds

1. **Relay placement driven by the probability map**, not by signal strength alone. Relays are dropped at the last
   well-connected point on the way to an area that is both likely and out of coverage.
2. **Planned link-loss windows** ("store and forward") as an explicit planning option with a time budget, so the
   failsafe protects the robot from *unplanned* loss without stopping deliberate excursions.
3. **Time-to-report as the outcome metric**, with an ablation that separates the two ideas above.
4. **An open, reproducible civilian benchmark**: three operational scenarios, four policies, held-out seeds,
   confidence intervals, and a 3D world generated from the same terrain.

Communication-aware planning is an active research area in multi-robot exploration; TREC-SAR does not claim to be
the first to consider radio in planning. The contribution is the specific SAR combination and the open benchmark.

## Key finding from the ablation

Most of the success gain over link-unaware policies comes from **planning the link loss**. Probability-driven relay
placement then delivers the same success with about half the relays (forest) or about 90 % fewer (tunnel), at the
cost of more time without live video. That trade-off is the honest headline.

## Assumptions that would change the answer

- Radio: 2.4 GHz-like budget (20 dBm, 4 dB gain, −90 dBm sensitivity). Sub-GHz mesh radios reach much further in
  forest, which would shrink the advantage of link-aware planning.
- Failsafe policy for baselines: 30–45 s, then return to coverage. A more permissive failsafe narrows the gap
  between baselines and the planned-link-loss policies.
- Perfect localisation and a known map in the 2D simulator.
