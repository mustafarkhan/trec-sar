# Scenarios and concept of operations

Each scenario is a story an emergency-service officer would recognise, the timeline the robot follows, and the
things that go wrong. The narratives are fictional; the structure follows common incident-command practice.

---

## 1. Boreal forest, winter night — missing elderly person

**Situation.** 18:40, −12 °C. An 81-year-old with memory loss has walked out of a rural home at dusk. Relatives last
saw him on the forest trail. The rescue service sets up a command post on the road (■ on the maps). Volunteers
will arrive in about an hour; hypothermia risk is high.

**Assets.** One drone with a thermal camera. One TREC-SAR UGV with a thermal/RGB mast, a thermal blanket and two-way
audio in the payload bay, and three relay nodes.

| Time | What happens |
|---|---|
| T+0 | UGV leaves the command post. Probability map built from the last known point and the trail network. |
| T+4 min | Drone sends a cue: something warm near the bog edge. Under dense spruce the drone often sees nothing. |
| T+5–20 min | UGV searches trail-side forest inside radio coverage first; first relay goes down where the trail enters the forest only if the map says the area beyond is worth it. |
| — | Beyond the granite ridge, radio stops. TREC-SAR authorises a bounded search window instead of spending its last relay. |
| T+x | Person detected. UGV stops, plays a voice message, drops the blanket (future payload), drives back into coverage and pushes video + position to the command post. |

**What goes wrong:** a frozen lake that looks like open ground (TREC-SAR treats ice as no-go by policy); battery
capacity loss in the cold (25 % derate in the model); drone false alarms (15 % rate in the model).

---

## 2. Tunnel network after a rock fall — missing worker

**Situation.** A maintenance worker's last radio check-in came from the north-east work face shortly before a rock
fall. The roof is unassessed: nobody goes in. There is no GPS and radio dies at the first bend.

**Assets.** TREC-SAR UGV with four relay nodes. No drone.

| Time | What happens |
|---|---|
| T+0 | UGV enters through the portal. Probability concentrated around the work face but spread along all drifts (people flee a rock fall in any direction). |
| T+2–6 min | At each junction the planner decides: drop a relay here, or run a short planned link-loss window into a dead-end drift and come back. |
| — | The rubble zone is slow but passable; the robot crosses it, a person would not. |
| T+x | Detection → back to the last junction with coverage → report. |

**What goes wrong:** relays used up early on the main adit (the reactive "drop when signal drops" habit does this);
dust blinding the camera (not modelled); collapsed side drifts (not modelled).

---

## 3. Industrial chemical release — casualty in the hot zone

**Situation.** A valve fails and releases ammonia. One worker near the leak does not answer the radio. Firefighters
hold the cordon upwind; entering the plume needs full chemical protection and time.

**Assets.** Drone over the open yard, TREC-SAR UGV with two relays.

| Time | What happens |
|---|---|
| T+0 | UGV leaves the cordon. Probability concentrated around the leak and downwind. |
| T+1.5 min | Drone cue from the open yard; between tanks the drone sees little. |
| T+3–8 min | UGV searches between tanks and pipe racks; steel shadows the link, so goals behind structures are checked against coverage. |
| T+x | Report pushed; firefighters enter with a known location instead of searching in protective suits. |

**What goes wrong:** gas sensor mapping is not modelled (future payload); wind shifts moving the plume (not
modelled); robot decontamination after the mission is a real operational cost.

---

## Variants used in the experiments

- **Forest, only one relay.** Tests graceful degradation when hardware is scarce.
- **Forest, wrong last-known point.** The person is sampled around a point about 95 m from where the planner thinks
  the LKP is. Tests robustness to bad witness information.
