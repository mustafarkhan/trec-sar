# Concept

## The problem

Rescue robots are judged on whether they *find* people. Operationally, what matters is whether a human at the
command post **knows** — sees the video, gets the location, can send a team. In a boreal forest, a mine, or between
steel tanks, the radio link drops long before the robot's batteries do. A robot that finds a casualty while out of
range has found nobody yet.

So the planning question is not "where is the person most likely to be?" but:

> Where should the robot look next, given what it believes, **and** what the radio network can carry back?

## System

```
  Drone (aerial spotter)          UGV (LUOTSI)                         Command post
  thermal person detector  ──cue──▶ probability map (Bayesian)  ──video/report──▶ operator
                                    planner: goal + relay + link window
                                    Nav2 / SLAM, thermal + RGB mast
                                    relay-node dropper (payload bay)
                                          │
                                   mesh relays ◀── dropped where they pay off
```

## Decision loop

Every replan (on reaching a goal, after a relay drop, after a drone cue, or every 12 moves):

1. **Value map.** Convolve the probability map with the sensor footprint: expected probability of detection from
   each cell, discounted by canopy.
2. **Candidates.** Take the top-40 reachable cells; score each = value ÷ (path length + 60 m).
3. **Radio check** for each candidate, in order of score:
   - inside current coverage → keep the score;
   - relay option: drop at the last cell on the path with margin ≥ threshold + buffer; full score if that relay
     covers the goal, otherwise a "chain" score (the relay extends the network towards it);
   - bounded excursion: the out-of-link part of the outbound path must fit 40 % of the failsafe time;
   - store-and-forward: commit to an authorised link-loss window (2.5 × outbound out-of-link time + 60 s), search
     autonomously, keep the evidence, come back to report.
4. **Choose** the best option. If nothing feasible, search the best covered area; last resort is plain greedy
   behaviour protected by the failsafe.

## Mission state machine

`SEARCH → RELAY_DROP → SEARCH`, `SEARCH → LINK_RECOVERY → SEARCH` (failsafe after 30–45 s of *unplanned* link
loss: drive to the nearest covered cell), `SEARCH → REPORT → DONE` (on detection: get into coverage and push the
report), `SEARCH → RTH` (battery reserve: energy home × 1.3, with a cold-weather derate in winter).

The failsafe is the direct descendant of TREC's blinking-LED connection indicator. The difference is that LUOTSI
plans *around* it instead of being surprised by it.

## Models (all replaceable)

| Model | Form | Where to calibrate |
|---|---|---|
| Lost-person location | log-normal distance from LKP × terrain affinity | ISRID / Koester category statistics |
| Detection | `pmax · exp(−(r/r0)²) · (1 − 0.7·canopy)`, zero without line of sight | field trials with the actual thermal camera |
| Radio | log-distance path loss (n = 2.2) + per-metre terrain attenuation | site survey; ITU-R P.833 for vegetation |
| Mobility / energy | terrain cost multiplier; idle + speed-proportional draw | robot logs |

## Why three scenarios

- **Forest, winter night.** Long distances, canopy that blinds the drone, radio absorbed by wet spruce. The scenario
  where link planning matters most.
- **Tunnel after a rock fall.** No GPS, radio stops at the first bend, humans not allowed in. Relays or planned
  link loss are the only way to search.
- **Industrial chemical release.** Short distances, open yard with steel structures that shadow the link. A control
  case: probability-driven search already works well.
