#!/usr/bin/env python3
"""Download HIT-UAV, build a person-only YOLO dataset, train YOLO11n, evaluate on the test split.

Runs unattended (GitHub Actions, CPU) and writes:
  results/perception/metrics.json      test-split precision / recall / mAP at two confidence levels
  results/perception/predictions.png   detections on held-out test images
  perception/weights/hituav_person_yolo11n.pt

    EPOCHS=25 python3 perception/train_ci.py
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("WORK", "/tmp/hituav"))
OUT = ROOT / "results" / "perception"
RECORD = "7633134"  # Zenodo record of HIT-UAV (Suo et al., Scientific Data 2023)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def download() -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    rec = requests.get(f"https://zenodo.org/api/records/{RECORD}", timeout=60).json()
    files = rec.get("files", [])
    log("record files: " + ", ".join(f"{f['key']} ({f.get('size', 0) / 1e6:.0f} MB)" for f in files))
    zips = [f for f in files if f["key"].lower().endswith(".zip")]
    if not zips:
        raise SystemExit("no zip in the Zenodo record")
    f = max(zips, key=lambda x: x.get("size", 0))
    dest = WORK / Path(f["key"]).name
    if not dest.exists():
        url = f["links"].get("self") or f["links"].get("download")
        log(f"downloading {f['key']} from {url}")
        with requests.get(url, stream=True, timeout=1800) as r, open(dest, "wb") as fh:
            r.raise_for_status()
            for chunk in r.iter_content(1 << 22):
                fh.write(chunk)
    ex = WORK / "extracted"
    if not ex.exists():
        zipfile.ZipFile(dest).extractall(ex)
    return ex


def find_voc(ex: Path) -> tuple[Path, Path, Path | None]:
    anns = sorted(ex.rglob("Annotations"))
    anns = [a for a in anns if a.is_dir() and any(a.glob("*.xml"))]
    normal = [a for a in anns if "rotate" not in str(a).lower()] or anns
    if not normal:
        tree = "\n".join(str(p.relative_to(ex)) for p in list(ex.rglob("*"))[:60])
        raise SystemExit(f"no VOC Annotations folder found. First entries:\n{tree}")
    ann = normal[0]
    base = ann.parent
    imgs = next((base / d for d in ("JPEGImages", "images", "Images", "image") if (base / d).is_dir()), None)
    if imgs is None:  # images might live elsewhere in the archive
        cands = [p for p in ex.rglob("*") if p.is_dir() and any(p.glob("*.jpg"))]
        imgs = cands[0]
    splits = base / "ImageSets" / "Main"
    log(f"annotations {ann}  images {imgs}  splits {splits if splits.is_dir() else 'none'}")
    return ann, imgs, splits if splits.is_dir() else None


def main() -> None:
    epochs = int(os.environ.get("EPOCHS", "25"))
    ex = download()
    ann, imgs, splits = find_voc(ex)
    ds = WORK / "hituav_person"
    cmd = [
        sys.executable,
        str(ROOT / "perception" / "voc_to_yolo.py"),
        "--images",
        str(imgs),
        "--annotations",
        str(ann),
        "--classes",
        "Person,person",
        "--out",
        str(ds),
    ]
    if splits:
        cmd += ["--splits", str(splits)]
    subprocess.run(cmd, check=True)

    from ultralytics import YOLO

    model = YOLO("yolo11n.pt")
    t0 = time.time()
    model.train(
        data=str(ds / "data.yaml"),
        epochs=epochs,
        imgsz=640,
        batch=16,
        device="cpu",
        workers=4,
        hsv_h=0.0,
        hsv_s=0.0,
        hsv_v=0.3,
        fliplr=0.5,
        patience=10,
        project=str(WORK / "runs"),
        name="person",
        seed=0,
        deterministic=True,
        plots=False,
        verbose=False,
    )
    train_min = (time.time() - t0) / 60
    best = WORK / "runs" / "person" / "weights" / "best.pt"
    model = YOLO(str(best))

    metrics = {
        "dataset": "HIT-UAV (Suo et al., Scientific Data 10:227, 2023), Person class only",
        "model": "YOLO11n (Ultralytics), COCO-pretrained, fine-tuned",
        "epochs": epochs,
        "imgsz": 640,
        "device": f"CPU ({platform.processor() or platform.machine()})",
        "train_minutes": round(train_min, 1),
        "split": "test",
        "results": {},
    }
    for conf in (0.25, 0.10):
        m = model.val(data=str(ds / "data.yaml"), split="test", conf=conf, device="cpu", plots=False, verbose=False)
        metrics["results"][f"conf_{conf}"] = {
            "precision": round(float(m.box.mp), 3),
            "recall": round(float(m.box.mr), 3),
            "mAP50": round(float(m.box.map50), 3),
            "mAP50_95": round(float(m.box.map), 3),
        }
    counts = {s: len(list((ds / "labels" / s).glob("*.txt"))) for s in ("train", "val", "test")}
    metrics["images"] = counts
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log(json.dumps(metrics, indent=2))

    # a contact sheet of predictions on test images that contain people
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    test_imgs = sorted((ds / "images" / "test").glob("*"))
    with_people = [p for p in test_imgs if (ds / "labels" / "test" / f"{p.stem}.txt").read_text().strip()][:6]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.4), facecolor="#101215")
    for ax, p in zip(axes.ravel(), with_people):
        r = model.predict(str(p), conf=0.25, device="cpu", verbose=False)[0]
        ax.imshow(r.plot()[..., ::-1])
        ax.set_title(f"{p.name} · {len(r.boxes)} detected", color="#f0efec", fontsize=10)
        ax.axis("off")
    fig.suptitle("YOLO11n person detector on held-out HIT-UAV thermal test images", color="#f0efec", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "predictions.png", dpi=110, facecolor="#101215")

    wdir = ROOT / "perception" / "weights"
    wdir.mkdir(parents=True, exist_ok=True)
    (wdir / "hituav_person_yolo11n.pt").write_bytes(best.read_bytes())
    log("done")


if __name__ == "__main__":
    main()
