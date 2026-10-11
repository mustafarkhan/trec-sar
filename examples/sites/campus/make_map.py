#!/usr/bin/env python3
"""Regenerate campus.png — an example of how a site map is drawn. Any paint program works too."""

from pathlib import Path

from PIL import Image, ImageDraw

W = H = 90
OPEN, ROAD, FOREST, DENSE, WATER, BUILDING, TRAIL = (
    "#ffffff",
    "#808080",
    "#1f5f1f",
    "#0f3f0f",
    "#2060c0",
    "#000000",
    "#c8a060",
)
im = Image.new("RGB", (W, H), OPEN)
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W, 44], fill=FOREST)  # park forest in the north
d.ellipse([10, 6, 38, 26], fill=DENSE)  # dense thicket
d.ellipse([52, 8, 76, 24], fill=WATER)  # pond
d.line([(5, 88), (5, 50), (45, 46), (60, 30), (84, 4)], fill=TRAIL, width=2)  # trail into the park
for x0, y0, x1, y1 in [(12, 52, 30, 64), (40, 54, 58, 66), (66, 50, 84, 62), (16, 70, 34, 82), (48, 72, 70, 84)]:
    d.rectangle([x0, y0, x1, y1], fill=BUILDING)  # campus buildings
d.line([(0, 87), (89, 87)], fill=ROAD, width=3)  # ring road
d.line([(38, 46), (38, 89)], fill=ROAD, width=2)  # main walkway
im.save(Path(__file__).with_name("campus.png"))
print("wrote campus.png")
