# Using LUOTSI for your CV, LinkedIn and interviews

Everything here is framed as a **project**, not a company. Replace anything in [brackets] before posting, and only
claim what you have run yourself.

## GitHub

- **Repository name:** `luotsi`
- **Description:** Link-aware search planning for rescue ground robots — Bayesian search, radio-relay placement and
  planned link loss. ROS 2 Jazzy, Gazebo, Nav2, YOLO.
- **Topics:** `search-and-rescue` `ros2` `gazebo` `nav2` `ugv` `bayesian-search` `robotics` `drones` `yolo`
  `thermal-imaging` `simulation`
- Pin it on your profile. Put `results/success_and_relays.png` at the top of the README (already there).

## CV — Projects section

**LUOTSI — Link-aware search planner for rescue ground robots** · Open source · [Month 2026]
*Python, NumPy/SciPy, ROS 2 Jazzy, Gazebo Harmonic, Nav2, slam_toolbox, YOLO11, Docker, GitHub Actions*

- Designed a search planner for a tracked rescue UGV that jointly chooses search goals, radio-relay placement and
  time-bounded link-loss windows from a Bayesian probability map; evaluated on time-to-report to the command post.
- Built a reproducible benchmark (3 civilian scenarios: winter forest, tunnel, chemical release; 4 policies;
  4,000 held-out Monte Carlo missions with 95 % confidence intervals and an ablation study).
- Raised simulated forest-search success from 36–42 % (link-unaware baselines) to 60 %, matching the best policy
  while using about half the relay nodes (about 90 % fewer in tunnels); documented where the method does not help.
- Implemented the ROS 2 stack (mission manager, radio-link simulator with operator-video gating, drone-cue stub,
  detectors), a URDF model of the TREC-heritage UGV, and Gazebo worlds generated from the planner's terrain.
- Applied QA practice: 29+ unit and behaviour tests, CI, FMEA-style failure-mode analysis, held-out evaluation.

**TREC — Tele-operated tracked reconfigurable UGV** · NUST College of E&ME, Department of Mechatronics · [year]
- [Your exact role — e.g. "Control and integration of the NI cRIO-9012 drive and payload interfaces"] on an 80 kg
  tracked UGV with swappable payloads, video feedback and a link-loss failsafe.
- Prototype progressed to field trials with an army unit.

> For European civilian employers keep the TREC line to engineering facts. Leave out weapon payload testing,
> named units and operational locations. For defence employers (Milrem, Patria, Saab) you can say more in the
> interview, but check what you are allowed to share.

## LinkedIn — headline addition

`… | Rescue robotics: link-aware search for UGV–drone teams (ROS 2, Nav2)`

## LinkedIn — post series (one per day)

**Day 1 — the origin story**
> Years ago, as an engineer in the Pakistan Army's EME corps, I worked on TREC: a tracked, reconfigurable ground
> robot. Its link-loss warning was a blinking green LED on the operator's screen.
>
> This week I'm rebuilding the idea for civilian search and rescue in Europe, fully open source, with one question
> at the centre: a robot that finds a missing person while out of radio range hasn't helped anyone yet.
> How should it search so the command post actually gets the video?
> Building in public — repo link in comments. #robotics #searchandrescue #ROS2

**Day 2 — the problem, with a picture** (attach `results/map_forest_winter.png`)
> Two robots, same forest, same missing person. The left one keeps losing the radio link and gets pulled back by its
> failsafe. The right one plans where to drop relays — and when to accept a short, planned link loss. One of them
> reported the casualty at 53 minutes. The other didn't.

**Day 3 — the method in plain words**
> The robot keeps a probability map of where the person could be. Every look that finds nothing lowers the
> probability there. For each place worth searching it asks: is it inside radio coverage? If not, would one relay
> fix that, or can I go, search and come back before the failsafe fires?

**Day 4 — results, including the uncomfortable part** (attach `results/success_and_relays.png`)
> 4,000 simulated missions. Link-aware planning took forest success from about 40 % to 60 %. My ablation then showed
> something humbling: most of that gain comes from planning the link loss, not from clever relay placement. What
> relay placement buys is efficiency: the same success with half the relays. Reporting the ablation is the point.

**Day 5 — the 3D stack** (attach a short Gazebo/RViz screen recording)
> Same terrain, now in Gazebo with ROS 2, SLAM and Nav2. The operator video panel goes black when the link drops,
> exactly the experience TREC's operators had.

**Day 6 — failure modes**
> What would break this in the real world? Thin ice. Batteries at −20 °C. A witness who is wrong about the last
> known point. I wrote them all down in an FMEA table. Simulation is a starting point, not evidence.

**Day 7 — open invitation**
> LUOTSI is open source (Apache-2.0). If you work in rescue services, rescue robotics, or radio for difficult
> environments in Finland or the Nordics, I'd value 20 minutes of your criticism.

*Before posting the TREC photos: they show identifiable officers and weapon payloads. Crop to the robot, or describe
it instead of showing the poster.*

## Interview talking points

1. **Why time-to-report, not time-to-detect** — the operational outcome is a human knowing.
2. **The ablation story** — I tested my own idea against a simpler variant and reported that the simpler variant
   carries most of the gain. That is how I'd work on a product too.
3. **Held-out seeds and confidence intervals** — tuned on 100–159, evaluated on 1000–1199.
4. **What I'd do with hardware** — radio site survey, thermal detection tests under spruce, battery logs in cold;
   replace each placeholder model with measured data.
5. **TREC → LUOTSI** — same hull spec, but the link failsafe went from a warning LED to a planning constraint.
