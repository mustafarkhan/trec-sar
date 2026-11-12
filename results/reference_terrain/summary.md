# Results — reference (tuning) terrain

200 runs per planner per scenario (casualty seeds 1000–1199), same terrain, casualty location and detection luck for every planner in a given run. Planner weights were tuned on terrain 0 with casualty seeds 100–159 only; this table is that same terrain (the one shown in the maps, replays and Gazebo worlds), so only the casualties are held out. Results on freshly generated terrains are in `results/summary.md`. Runtime 896 s.

*Success* = a human at the command post received the detection before the time limit (with an image they can confirm: live video, or a thumbnail sent over the narrowband link). *Time* counts failures as the full time limit (so medians are conservative). 95 % Wilson intervals in brackets.

## Forest, winter (3 relays)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 36% [29%–42%] | 90.0 min | 69.9 min | 1434 s | 12.9 | 2.7 |
| Probability-greedy + reactive relays | 42% [35%–48%] | 90.0 min | 57.8 min | 1305 s | 12.8 | 2.4 |
| Probability-greedy + planned link loss (ablation) | 63% [56%–69%] | 36.1 min | 46.0 min | 452 s | 0.1 | 2.4 |
| TREC-SAR (link-aware, planned relays) | 60% [53%–67%] | 37.5 min | 47.5 min | 767 s | 1.6 | 1.2 |
| TREC-SAR + online radio calibration | 64% [57%–70%] | 36.1 min | 45.5 min | 576 s | 0.9 | 1.6 |

## Forest, only 1 relay

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 23% [18%–29%] | 90.0 min | 75.5 min | 2999 s | 29.1 | 0.9 |
| Probability-greedy + reactive relays | 50% [44%–57%] | 59.5 min | 53.7 min | 977 s | 8.9 | 1.0 |
| Probability-greedy + planned link loss (ablation) | 62% [55%–68%] | 37.9 min | 46.4 min | 721 s | 0.3 | 1.0 |
| TREC-SAR (link-aware, planned relays) | 61% [54%–67%] | 38.2 min | 47.4 min | 867 s | 1.9 | 0.7 |
| TREC-SAR + online radio calibration | 62% [56%–69%] | 38.2 min | 46.7 min | 852 s | 1.9 | 0.7 |

## Forest, wrong last-known point (~95 m)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 32% [26%–39%] | 90.0 min | 73.1 min | 1497 s | 13.5 | 2.9 |
| Probability-greedy + reactive relays | 39% [33%–46%] | 90.0 min | 60.4 min | 1321 s | 13.0 | 2.5 |
| Probability-greedy + planned link loss (ablation) | 60% [54%–67%] | 36.1 min | 48.2 min | 446 s | 0.1 | 2.5 |
| TREC-SAR (link-aware, planned relays) | 56% [49%–62%] | 46.6 min | 52.2 min | 839 s | 1.8 | 1.3 |
| TREC-SAR + online radio calibration | 58% [51%–65%] | 43.2 min | 50.8 min | 605 s | 1.0 | 1.8 |

## Forest, radio 1.8x worse than planned (wet snow on spruce)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 22% [17%–29%] | 90.0 min | 76.2 min | 2732 s | 27.7 | 2.8 |
| Probability-greedy + reactive relays | 39% [33%–46%] | 90.0 min | 59.6 min | 1217 s | 9.8 | 2.7 |
| Probability-greedy + planned link loss (ablation) | 61% [54%–67%] | 41.3 min | 48.7 min | 887 s | 2.7 | 2.7 |
| TREC-SAR (link-aware, planned relays) | 57% [51%–64%] | 54.1 min | 52.1 min | 1885 s | 9.6 | 2.0 |
| TREC-SAR + online radio calibration | 62% [55%–68%] | 37.1 min | 47.7 min | 1538 s | 2.8 | 0.7 |

## Tunnel after rock fall

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 90% [85%–93%] | 5.9 min | 17.9 min | 226 s | 3.7 | 2.8 |
| Probability-greedy + reactive relays | 94% [90%–97%] | 5.9 min | 11.0 min | 135 s | 2.2 | 2.8 |
| Probability-greedy + planned link loss (ablation) | 98% [96%–99%] | 5.9 min | 9.4 min | 64 s | 0.1 | 2.8 |
| TREC-SAR (link-aware, planned relays) | 98% [96%–99%] | 6.5 min | 9.2 min | 334 s | 0.5 | 0.2 |
| TREC-SAR + online radio calibration | 98% [96%–99%] | 6.5 min | 9.2 min | 334 s | 0.5 | 0.2 |

## Industrial chemical release

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 88% [83%–92%] | 21.5 min | 23.6 min | 210 s | 3.3 | 2.0 |
| Probability-greedy + reactive relays | 96% [93%–98%] | 3.8 min | 7.7 min | 89 s | 1.2 | 1.2 |
| Probability-greedy + planned link loss (ablation) | 98% [96%–99%] | 3.8 min | 7.0 min | 58 s | 0.0 | 1.2 |
| TREC-SAR (link-aware, planned relays) | 98% [96%–99%] | 3.9 min | 7.0 min | 80 s | 0.7 | 0.9 |
| TREC-SAR + online radio calibration | 98% [96%–99%] | 3.8 min | 7.0 min | 85 s | 0.6 | 0.9 |

## Urban block after an earthquake

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 51% [44%–58%] | 38.9 min | 39.0 min | 1264 s | 19.0 | 3.0 |
| Probability-greedy + reactive relays | 99% [96%–100%] | 2.5 min | 3.8 min | 10 s | 0.2 | 1.6 |
| Probability-greedy + planned link loss (ablation) | 100% [98%–100%] | 2.5 min | 3.7 min | 7 s | 0.0 | 1.6 |
| TREC-SAR (link-aware, planned relays) | 100% [98%–100%] | 2.7 min | 3.6 min | 34 s | 0.0 | 1.2 |
| TREC-SAR + online radio calibration | 100% [98%–100%] | 2.7 min | 3.6 min | 36 s | 0.0 | 1.2 |

## Twin-bore road tunnel fire (1 km)

| Policy | Success | Median time | Mean time | Time out of link | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 96% [92%–98%] | 11.6 min | 19.0 min | 127 s | 2.4 | 3.2 |
| Probability-greedy + reactive relays | 99% [96%–100%] | 6.3 min | 8.8 min | 26 s | 0.5 | 2.2 |
| Probability-greedy + planned link loss (ablation) | 99% [96%–100%] | 6.3 min | 8.9 min | 25 s | 0.0 | 2.3 |
| TREC-SAR (link-aware, planned relays) | 99% [96%–100%] | 6.3 min | 9.0 min | 193 s | 0.0 | 1.0 |
| TREC-SAR + online radio calibration | 99% [96%–100%] | 6.3 min | 9.0 min | 193 s | 0.0 | 1.0 |

## Forest + 868 MHz report link (500 mW, 10 % duty cycle)

| Policy | Success | Median time to position alert | Median time | Mean time | Time without live video | Time unsupervised | Reports sent over 868 MHz | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 42% [35%–49%] | 90.0 min | 90.0 min | 66.1 min | 2710 s | 0 s | 24% | 0.0 | 0.9 |
| Probability-greedy + reactive relays | 62% [55%–68%] | 35.4 min | 36.3 min | 46.7 min | 1153 s | 0 s | 16% | 0.0 | 1.3 |
| Probability-greedy + planned link loss (ablation) | 62% [55%–68%] | 35.4 min | 36.3 min | 46.7 min | 1153 s | 0 s | 16% | 0.0 | 1.3 |
| TREC-SAR (link-aware, planned relays) | 62% [55%–68%] | 37.4 min | 37.9 min | 46.9 min | 1209 s | 13 s | 16% | 0.1 | 0.6 |
| TREC-SAR + online radio calibration | 62% [55%–68%] | 37.4 min | 37.9 min | 46.9 min | 1209 s | 13 s | 16% | 0.1 | 0.6 |

## Forest + 868 MHz report link (25 mW, 1 % duty cycle)

| Policy | Success | Median time to position alert | Median time | Mean time | Time without live video | Time unsupervised | Reports sent over 868 MHz | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 42% [35%–49%] | 90.0 min | 90.0 min | 66.4 min | 2743 s | 0 s | 0% | 0.0 | 0.9 |
| Probability-greedy + reactive relays | 62% [55%–68%] | 35.5 min | 37.1 min | 46.9 min | 1170 s | 0 s | 0% | 0.0 | 1.3 |
| Probability-greedy + planned link loss (ablation) | 62% [55%–68%] | 35.5 min | 37.1 min | 46.9 min | 1170 s | 0 s | 0% | 0.0 | 1.3 |
| TREC-SAR (link-aware, planned relays) | 64% [57%–70%] | 36.3 min | 38.0 min | 46.2 min | 1213 s | 18 s | 0% | 0.1 | 0.7 |
| TREC-SAR + online radio calibration | 64% [57%–70%] | 36.3 min | 38.0 min | 46.2 min | 1213 s | 18 s | 0% | 0.1 | 0.7 |

## Urban earthquake + 868 MHz report link (500 mW, 10 % duty cycle)

| Policy | Success | Median time to position alert | Median time | Mean time | Time without live video | Time unsupervised | Reports sent over 868 MHz | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 78% [72%–83%] | 29.8 min | 30.4 min | 32.0 min | 1376 s | 299 s | 1% | 4.9 | 3.0 |
| Probability-greedy + reactive relays | 100% [98%–100%] | 2.4 min | 3.1 min | 3.9 min | 169 s | 1 s | 2% | 0.0 | 0.6 |
| Probability-greedy + planned link loss (ablation) | 100% [98%–100%] | 2.4 min | 3.1 min | 3.9 min | 171 s | 2 s | 2% | 0.0 | 0.6 |
| TREC-SAR (link-aware, planned relays) | 100% [98%–100%] | 2.4 min | 3.1 min | 3.9 min | 177 s | 26 s | 1% | 0.0 | 0.3 |
| TREC-SAR + online radio calibration | 100% [98%–100%] | 2.4 min | 3.1 min | 3.9 min | 177 s | 26 s | 1% | 0.0 | 0.3 |

## Tunnel + 868 MHz report link (500 mW, 10 % duty cycle)

| Policy | Success | Median time to position alert | Median time | Mean time | Time without live video | Time unsupervised | Reports sent over 868 MHz | Failsafe trips | Relays used |
|---|---|---|---|---|---|---|---|---|---|
| Lawnmower sweep + reactive relays | 90% [85%–93%] | 5.9 min | 5.9 min | 17.9 min | 226 s | 226 s | 0% | 3.7 | 2.8 |
| Probability-greedy + reactive relays | 94% [90%–97%] | 5.9 min | 5.9 min | 11.0 min | 135 s | 135 s | 0% | 2.2 | 2.8 |
| Probability-greedy + planned link loss (ablation) | 98% [96%–99%] | 5.9 min | 5.9 min | 9.4 min | 64 s | 64 s | 0% | 0.1 | 2.8 |
| TREC-SAR (link-aware, planned relays) | 97% [94%–99%] | 6.5 min | 6.5 min | 9.8 min | 326 s | 326 s | 0% | 0.7 | 0.3 |
| TREC-SAR + online radio calibration | 97% [94%–99%] | 6.5 min | 6.5 min | 9.8 min | 326 s | 326 s | 0% | 0.7 | 0.3 |
