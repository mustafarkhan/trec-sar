#!/usr/bin/env python3
"""Convert Pascal-VOC XML annotations (HIT-UAV, HERIDAL, ...) to a person-only YOLO dataset.

    python3 voc_to_yolo.py --images HIT-UAV/normal_xml/JPEGImages \
        --annotations HIT-UAV/normal_xml/Annotations --splits HIT-UAV/normal_xml/ImageSets/Main \
        --classes Person --out datasets/hituav_person

Every listed class name (case-insensitive) maps to YOLO class 0 "person".
Images without people are kept as negatives (empty label file) — important for
search and rescue, where most frames contain nobody.
If no split files are given, a deterministic 80/10/10 split is made.
"""

from __future__ import annotations

import argparse
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")


def parse_voc(xml_path: Path, wanted: set[str]):
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    w, h = float(size.find("width").text), float(size.find("height").text)
    boxes = []
    for obj in root.findall("object"):
        name = (obj.findtext("name") or "").strip().lower()
        if name not in wanted:
            continue
        bb = obj.find("bndbox")
        x0, y0, x1, y1 = (float(bb.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax"))
        x0, x1 = max(0.0, min(x0, x1)), min(w, max(x0, x1))
        y0, y1 = max(0.0, min(y0, y1)), min(h, max(y0, y1))
        if x1 - x0 < 1 or y1 - y0 < 1:
            continue
        boxes.append(((x0 + x1) / 2 / w, (y0 + y1) / 2 / h, (x1 - x0) / w, (y1 - y0) / h))
    return root.findtext("filename"), boxes


def find_image(images: Path, stem: str, filename: str | None):
    if filename and (images / filename).exists():
        return images / filename
    for ext in IMG_EXT:
        p = images / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--splits", type=Path, help="folder with train.txt / val.txt / test.txt (VOC ImageSets)")
    ap.add_argument("--classes", default="Person,person,human,humans")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    wanted = {c.strip().lower() for c in a.classes.split(",") if c.strip()}
    xmls = sorted(a.annotations.glob("*.xml"))
    if not xmls:
        raise SystemExit(f"no XML files in {a.annotations}")
    stems = [x.stem for x in xmls]

    split_of = {}
    if a.splits:
        for name in ("train", "val", "test"):
            f = a.splits / f"{name}.txt"
            if f.exists():
                for line in f.read_text().split():
                    split_of[Path(line).stem] = name
    if not split_of:
        rnd = random.Random(a.seed)
        shuffled = stems[:]
        rnd.shuffle(shuffled)
        n = len(shuffled)
        for i, s in enumerate(shuffled):
            split_of[s] = "train" if i < 0.8 * n else ("val" if i < 0.9 * n else "test")

    counts = {k: [0, 0] for k in ("train", "val", "test")}  # images, boxes
    for x in xmls:
        split = split_of.get(x.stem)
        if split is None:
            continue
        fname, boxes = parse_voc(x, wanted)
        img = find_image(a.images, x.stem, fname)
        if img is None:
            continue
        (a.out / "images" / split).mkdir(parents=True, exist_ok=True)
        (a.out / "labels" / split).mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, a.out / "images" / split / img.name)
        (a.out / "labels" / split / f"{img.stem}.txt").write_text(
            "".join(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n" for cx, cy, bw, bh in boxes)
        )
        counts[split][0] += 1
        counts[split][1] += len(boxes)

    (a.out / "data.yaml").write_text(
        f"path: {a.out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\n"
    )
    for k, (n_img, n_box) in counts.items():
        print(f"{k:5s}: {n_img} images, {n_box} person boxes")
    print(f"wrote {a.out / 'data.yaml'}")


if __name__ == "__main__":
    main()
