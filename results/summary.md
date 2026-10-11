# Results — held-out Monte Carlo

200 runs per planner per scenario (seeds 1000–1199), same casualty location and detection luck for every planner in a given seed. Planner weights were tuned on seeds 100–159 only. Runtime 195 s.

*Success* = a human at the command post received the detection before the time limit. *Time* counts failures as the full time limit (so medians are conservative). 95 % Wilson intervals in brackets.

## Forest, winter (3 relays)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 36% [29%–42%] | 90.0 min | 69.9 min | 1434 s | 12.9 | 2.7 |
| Probability-greedy + reactive relays | 42% [35%–48%] | 90.0 min | 57.8 min | 1305 s | 12.8 | 2.4 |
| Probability-greedy + planned link loss (ablation) | 63% [56%–69%] | 36.1 min | 46.0 min | 452 s | 0.1 | 2.4 |
| TREC-SAR (link-aware, planned relays) | 60% [53%–67%] | 37.5 min | 47.5 min | 767 s | 1.6 | 1.2 |

## Forest, only 1 relay

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 23% [18%–29%] | 90.0 min | 75.5 min | 2999 s | 29.1 | 0.9 |
| Probability-greedy + reactive relays | 50% [44%–57%] | 59.5 min | 53.7 min | 977 s | 8.9 | 1.0 |
| Probability-greedy + planned link loss (ablation) | 62% [55%–68%] | 37.9 min | 46.4 min | 721 s | 0.3 | 1.0 |
| TREC-SAR (link-aware, planned relays) | 61% [54%–67%] | 38.2 min | 47.4 min | 867 s | 1.9 | 0.7 |

## Forest, wrong last-known point (~95 m)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 32% [26%–39%] | 90.0 min | 73.1 min | 1497 s | 13.5 | 2.9 |
| Probability-greedy + reactive relays | 39% [33%–46%] | 90.0 min | 60.4 min | 1321 s | 13.0 | 2.5 |
| Probability-greedy + planned link loss (ablation) | 60% [54%–67%] | 36.1 min | 48.2 min | 446 s | 0.1 | 2.5 |
| TREC-SAR (link-aware, planned relays) | 56% [49%–62%] | 46.6 min | 52.2 min | 839 s | 1.8 | 1.3 |

## Tunnel after rock fall

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 90% [85%–93%] | 5.9 min | 17.9 min | 226 s | 3.7 | 2.8 |
| Probability-greedy + reactive relays | 94% [90%–97%] | 5.9 min | 11.0 min | 135 s | 2.2 | 2.8 |
| Probability-greedy + planned link loss (ablation) | 98% [96%–99%] | 5.9 min | 9.4 min | 64 s | 0.1 | 2.8 |
| TREC-SAR (link-aware, planned relays) | 98% [96%–99%] | 6.5 min | 9.2 min | 334 s | 0.5 | 0.2 |

## Industrial chemical release

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 88% [83%–92%] | 21.5 min | 23.6 min | 210 s | 3.3 | 2.0 |
| Probability-greedy + reactive relays | 96% [93%–98%] | 3.8 min | 7.7 min | 89 s | 1.2 | 1.2 |
| Probability-greedy + planned link loss (ablation) | 98% [96%–99%] | 3.8 min | 7.0 min | 58 s | 0.0 | 1.2 |
| TREC-SAR (link-aware, planned relays) | 98% [96%–99%] | 3.9 min | 7.0 min | 80 s | 0.7 | 0.9 |
