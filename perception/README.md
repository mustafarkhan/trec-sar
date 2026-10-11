# Perception — person detection on open datasets

## Measured result

YOLO11n fine-tuned on HIT-UAV (person class), 25 epochs on a GitHub Actions CPU runner (220 min), evaluated once on
the **held-out test split** (579 images never used for training or model selection):

| Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|
| 0.88 | 0.88 | **0.90** | 0.47 |

Reproduce: `EPOCHS=25 python3 perception/train_ci.py` (or the `perception` workflow). Raw numbers:
[`results/perception/metrics.json`](../results/perception/metrics.json). Weights:
[`weights/hituav_person_yolo11n.pt`](weights/hituav_person_yolo11n.pt) (5.5 MB, trained on HIT-UAV — check the
dataset's terms before commercial use).

![Detections on held-out thermal test images](../results/perception/predictions.png)

People in these frames are often only a few pixels across. mAP50-95 is much lower than mAP50 because box edges on
such small targets are imprecise; for a search cue, finding the person matters more than a tight box.

Two detectors, two viewpoints:

| Where | Job in TREC-SAR | Training data | Status |
|---|---|---|---|
| **Drone (aerial spotter)** | Send a "possible person here" cue that the UGV fuses into its probability map | HIT-UAV thermal (person class), optionally HERIDAL RGB | **Trained and tested: mAP50 0.90 on the test split** (see above); Colab notebook for GPU retraining |
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
3. Save `test_metrics.json` to `results/perception/metrics.json` and quote those numbers — and only those.

`voc_to_yolo.py` also works for HERIDAL (`--classes human,person`); check the class name in its XML files first.

## Honest limitations

- Aerial datasets do not cover the UGV's ground-level viewpoint, winter forests, or people under dense spruce.
- HIT-UAV scenes are mostly urban and campus areas; expect a domain gap in a Finnish forest.
- The YOLO node localises a detection crudely (robot pose + an assumed range along the heading); fusing lidar range is listed as future work.
