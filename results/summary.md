# Results — held-out Monte Carlo

200 runs per planner per scenario (casualty seeds 1000–1199, spread evenly over generated terrains 1, 2, 3, 4, 5, 6, 7, 8), same terrain, casualty location and detection luck for every planner in a given run. Planner weights were tuned on terrain 0 with casualty seeds 100–159 only, so both the terrains and the casualties here are held out. Runtime 557 s.

*Success* = a human at the command post received the detection before the time limit. *Time* counts failures as the full time limit (so medians are conservative). 95 % Wilson intervals in brackets; they treat runs as independent and ignore that runs share terrains, so read them together with the *per-terrain range* column (lowest and highest success on a single terrain).

## Forest, winter (3 relays)

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 25% [20%–31%] | 20%–44% | 90.0 min | 75.0 min | 1199 s | 11.6 | 2.8 |
| Probability-greedy + reactive relays | 74% [68%–80%] | 56%–92% | 30.9 min | 40.0 min | 77 s | 0.7 | 2.4 |
| Probability-greedy + planned link loss (ablation) | 73% [66%–79%] | 48%–92% | 30.9 min | 40.5 min | 77 s | 0.1 | 2.4 |
| TREC-SAR (link-aware, planned relays) | 74% [68%–80%] | 48%–92% | 30.4 min | 39.8 min | 385 s | 0.6 | 1.2 |
| TREC-SAR + online radio calibration | 74% [68%–80%] | 48%–96% | 30.0 min | 39.7 min | 412 s | 0.7 | 1.2 |

## Forest, only 1 relay

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 22% [16%–28%] | 8%–36% | 90.0 min | 76.8 min | 2613 s | 25.9 | 1.0 |
| Probability-greedy + reactive relays | 62% [55%–68%] | 44%–80% | 33.6 min | 46.0 min | 702 s | 7.0 | 1.0 |
| Probability-greedy + planned link loss (ablation) | 74% [68%–80%] | 52%–92% | 29.4 min | 39.9 min | 448 s | 0.3 | 1.0 |
| TREC-SAR (link-aware, planned relays) | 73% [66%–79%] | 48%–92% | 27.8 min | 39.9 min | 586 s | 1.2 | 0.6 |
| TREC-SAR + online radio calibration | 74% [68%–80%] | 52%–92% | 29.3 min | 39.3 min | 604 s | 1.0 | 0.6 |

## Forest, wrong last-known point (~95 m)

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 27% [21%–34%] | 20%–32% | 90.0 min | 73.1 min | 1156 s | 11.2 | 2.8 |
| Probability-greedy + reactive relays | 68% [62%–75%] | 44%–84% | 32.3 min | 43.8 min | 80 s | 0.7 | 2.4 |
| Probability-greedy + planned link loss (ablation) | 68% [62%–75%] | 40%–84% | 32.3 min | 43.9 min | 76 s | 0.0 | 2.4 |
| TREC-SAR (link-aware, planned relays) | 67% [60%–73%] | 44%–84% | 33.5 min | 44.1 min | 403 s | 0.7 | 1.4 |
| TREC-SAR + online radio calibration | 67% [60%–73%] | 44%–80% | 33.0 min | 43.8 min | 441 s | 0.9 | 1.3 |

## Forest, radio 1.8x worse than planned (wet snow on spruce)

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 22% [16%–28%] | 8%–36% | 90.0 min | 77.2 min | 2300 s | 22.7 | 2.8 |
| Probability-greedy + reactive relays | 60% [53%–67%] | 40%–80% | 35.6 min | 47.6 min | 634 s | 6.3 | 2.6 |
| Probability-greedy + planned link loss (ablation) | 70% [64%–76%] | 52%–92% | 30.1 min | 41.9 min | 482 s | 2.9 | 2.6 |
| TREC-SAR (link-aware, planned relays) | 62% [55%–68%] | 52%–76% | 46.5 min | 49.2 min | 1921 s | 10.6 | 1.6 |
| TREC-SAR + online radio calibration | 68% [61%–74%] | 48%–80% | 35.8 min | 43.4 min | 1332 s | 2.9 | 1.1 |

## Tunnel after rock fall

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 68% [61%–74%] | 56%–80% | 29.2 min | 32.3 min | 442 s | 7.7 | 3.2 |
| Probability-greedy + reactive relays | 86% [80%–90%] | 76%–100% | 5.8 min | 14.7 min | 137 s | 2.2 | 2.6 |
| Probability-greedy + planned link loss (ablation) | 88% [83%–92%] | 76%–100% | 5.8 min | 13.6 min | 87 s | 0.0 | 2.6 |
| TREC-SAR (link-aware, planned relays) | 92% [87%–95%] | 84%–100% | 5.1 min | 12.2 min | 345 s | 0.4 | 0.8 |
| TREC-SAR + online radio calibration | 92% [87%–95%] | 84%–100% | 5.1 min | 12.2 min | 345 s | 0.4 | 0.8 |

## Industrial chemical release

| Policy | Success | Per-terrain range | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 97% [94%–99%] | 92%–100% | 20.1 min | 20.5 min | 110 s | 1.9 | 1.8 |
| Probability-greedy + reactive relays | 98% [95%–99%] | 92%–100% | 3.8 min | 7.3 min | 23 s | 0.3 | 1.2 |
| Probability-greedy + planned link loss (ablation) | 98% [94%–99%] | 92%–100% | 3.8 min | 7.4 min | 22 s | 0.0 | 1.2 |
| TREC-SAR (link-aware, planned relays) | 98% [94%–99%] | 92%–100% | 3.7 min | 7.2 min | 72 s | 0.1 | 0.6 |
| TREC-SAR + online radio calibration | 98% [94%–99%] | 92%–100% | 3.7 min | 7.2 min | 71 s | 0.1 | 0.6 |
