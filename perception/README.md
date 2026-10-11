# Perception — person detection on open datasets

Two detectors, two viewpoints:

| Where | Job in TREC-SAR | Training data | Status |
|---|---|---|---|
| **Drone (aerial spotter)** | Send a "possible person here" cue that the UGV fuses into its probability map | HIT-UAV thermal (person class), optionally HERIDAL RGB | Notebook ready: `train_sar_yolo.ipynb` (free Colab T4) |
| **UGV camera mast** | Confirm the person at close range before reporting | COCO-pretrained `yolo11n.pt` (person = class 0) | Used as-is by `ros2 run trecsar_mission yolo_detector` |

The 2D Monte Carlo and the default 3D demo use an **analytic detection model** (range, canopy and line of sight)
instead of images, so experiments are reproducible. The image detectors are what you would run on real hardware.

## Datasets (all free for research — check each licence before redistributing)

| Dataset | What | Why it fits | Reference |
|---|---|---|---|
| **HIT-UAV** | 2,898 drone thermal images; Person, Car, Bicycle, OtherVehicle, DontCare; VOC + COCO annotations | Night/thermal person detection from the air | Suo et al., *Scientific Data* 10:227 (2023); Zenodo DOI 10.5281/zenodo.7633134 |
| **HERIDAL** | 1,647 annotated high-resolution aerial RGB images of people in wilderness SAR scenes | Real search-and-rescue imagery, tiny people in vegetation | Božić-Štulić et al., *IJCV* (2019) |
| **AIR (Aalto/Accenture)** | Detector + SAR-specific evaluation on HERIDAL | Strong baseline and evaluation method to compare against; Aalto University link | Pyrrö, Naseri, Jung, arXiv:2111.09406 (2021); github.com/Accenture/AIR |

## Steps

1. Open `train_sar_yolo.ipynb` in Google Colab, select a T4 GPU, run all cells.
2. The notebook downloads HIT-UAV, converts it with `voc_to_yolo.py` (person only, empty frames kept as
   negatives), trains `yolo11n`, and evaluates on the **test** split at two confidence thresholds.
3. Save `test_metrics.json` to `results/perception_metrics.json` and quote those numbers — and only those.

`voc_to_yolo.py` also works for HERIDAL (`--classes human,person`); check the class name in its XML files first.

## Honest limitations

- Aerial datasets do not cover the UGV's ground-level viewpoint, winter forests, or people under dense spruce.
- HIT-UAV scenes are mostly urban and campus areas; expect a domain gap in a Finnish forest.
- The YOLO node localises a detection crudely (robot pose + an assumed range along the heading); fusing lidar range is listed as future work.
