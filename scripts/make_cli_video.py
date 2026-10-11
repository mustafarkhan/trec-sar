#!/usr/bin/env python3
"""Render media/trec-sar_cli_demo.mp4: a terminal walkthrough of the `trecsar` tool.

Every command is executed while the video renders and its real output is shown,
so the video can never drift from what the software actually does.

    python3 scripts/make_cli_video.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1920, 1080, 30
BG, TERM, INK, INK2, MUTED = "#101215", "#0b0d10", "#f0efec", "#a8a7a2", "#6c6b67"
PROMPT, GREEN, BLUE = "#3fb97a", "#3fb97a", "#3987e5"
MONO = "DejaVu Sans Mono"
WORK = Path(tempfile.mkdtemp(prefix="trecsar_demo_"))


def sh(cmd: str, max_lines: int = 18) -> list[str]:
    """Run a shell command from the repo root and return its (trimmed) output lines."""
    env = dict(os.environ, COLUMNS="110")
    exe = shutil.which("trecsar")
    if exe is None:  # running from a source checkout without `pip install`
        cmd = cmd.replace("trecsar ", f"{sys.executable} -m trecsar_core ", 1)
        env["PYTHONPATH"] = str(ROOT / "core")
    out = subprocess.run(cmd, shell=True, cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout
    lines = [ln.rstrip() for ln in out.splitlines()]
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + [f"... ({len(lines) - max_lines + 1} more lines)"]
    return lines


def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    return fig


def terminal_scene(title: str, subtitle: str, steps: list[tuple[str, list[str]]], seconds: float):
    """steps: (command, output lines). Commands are typed, then output appears line by line."""
    timeline = []  # (start_u, end_u) for each step
    weights = [1.0 + 0.06 * len(out) for _, out in steps]
    total = sum(weights)
    acc = 0.04
    for w in weights:
        span = 0.88 * w / total
        timeline.append((acc, acc + span))
        acc += span

    def setup(fig):
        fig.text(0.05, 0.95, title, fontsize=30, weight="bold", color=INK, va="top")
        fig.text(0.05, 0.895, subtitle, fontsize=16, color=INK2, va="top")
        fig.patches.append(
            FancyBboxPatch(
                (0.05, 0.05),
                0.90,
                0.80,
                boxstyle="round,pad=0.004,rounding_size=0.012",
                transform=fig.transFigure,
                fc=TERM,
                ec="#2a2d33",
                lw=1.5,
            )
        )
        for i, c in enumerate(("#e66767", "#c98500", "#3fb97a")):
            fig.patches.append(plt.Circle((0.07 + i * 0.016, 0.83), 0.005, transform=fig.transFigure, color=c))
        n_lines = sum(1 + len(o) for _, o in steps) + len(steps)
        line_h = min(0.034, 0.74 / max(n_lines, 1))
        fs = min(17, line_h * H * 0.55)
        arts = []
        y = 0.80
        for cmd, out in steps:
            a_cmd = fig.text(0.07, y, "", fontsize=fs, family=MONO, color=INK, va="top")
            y -= line_h
            outs = []
            for ln in out:
                color = GREEN if ("REPORTED at" in ln or "reported" in ln.lower() and "not" not in ln.lower()) else INK2
                if "NOT REPORTED" in ln:
                    color = "#e66767"
                outs.append(fig.text(0.07, y, ln, fontsize=fs, family=MONO, color=color, va="top", alpha=0))
                y -= line_h
            y -= line_h * 0.6
            arts.append((cmd, a_cmd, outs))

        def update(u):
            for (cmd, a_cmd, outs), (s, e) in zip(arts, timeline):
                type_end = s + (e - s) * 0.35
                if u < s:
                    a_cmd.set_text("")
                else:
                    k = int(len(cmd) * min(1.0, (u - s) / max(type_end - s, 1e-6)))
                    cursor = "█" if u < type_end and int(u * 60) % 2 == 0 else ""
                    a_cmd.set_text("$ " + cmd[:k] + cursor)
                    a_cmd.set_color(INK)
                for j, t in enumerate(outs):
                    appear = type_end + (e - type_end) * 0.6 * (j / max(len(outs), 1))
                    t.set_alpha(1.0 if u >= appear else 0.0)

        return update

    return seconds, setup


def image_scene(
    title: str,
    subtitle: str,
    left_img: Path,
    right_img: Path | None,
    caption: str,
    seconds: float,
    left_title: str = "",
    right_title: str = "",
):
    def setup(fig):
        fig.text(0.05, 0.95, title, fontsize=30, weight="bold", color=INK, va="top")
        fig.text(0.05, 0.895, subtitle, fontsize=16, color=INK2, va="top")
        if right_img is None:
            ax = fig.add_axes([0.05, 0.10, 0.90, 0.76])
            ax.imshow(plt.imread(left_img))
            ax.axis("off")
            axes = [ax]
        else:
            a1 = fig.add_axes([0.05, 0.10, 0.36, 0.74])
            im = plt.imread(left_img)
            a1.imshow(im, interpolation="nearest")
            a1.set_xticks([])
            a1.set_yticks([])
            a1.set_title(left_title, color=INK2, fontsize=14, loc="left")
            for sp in a1.spines.values():
                sp.set_color(MUTED)
            a2 = fig.add_axes([0.43, 0.08, 0.54, 0.78])
            a2.imshow(plt.imread(right_img))
            a2.axis("off")
            a2.set_title(right_title, color=INK2, fontsize=14, loc="left")
            axes = [a1, a2]
        cap = fig.text(0.05, 0.03, caption, fontsize=14, color=MUTED, va="bottom")

        def update(u):
            for ax in axes:
                for im in ax.get_images():
                    im.set_alpha(min(1.0, u / 0.15))
            cap.set_alpha(min(1.0, u / 0.25))

        return update

    return seconds, setup


def text_scene(lines, seconds):
    def setup(fig):
        objs = []
        for text, size, color, weight, y, start, family in lines:
            objs.append(
                (
                    fig.text(
                        0.07,
                        y,
                        text,
                        fontsize=size,
                        color=color,
                        weight=weight,
                        va="top",
                        family=family or "DejaVu Sans",
                    ),
                    start,
                )
            )

        def update(u):
            for t, s in objs:
                t.set_alpha(float(np.clip((u - s) / 0.12, 0, 1)))

        return update

    return seconds, setup


def yaml_card(path: Path) -> Path:
    """Render the site YAML as an image for the custom-site scene."""
    lines = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")][:22]
    fig = plt.figure(figsize=(7.0, 8.2), dpi=120, facecolor=TERM)
    for i, ln in enumerate(lines):
        fig.text(
            0.04,
            0.97 - i * 0.043,
            ln[:62],
            fontsize=12.5,
            family=MONO,
            color=BLUE if ":" in ln and not ln.startswith(" ") else INK2,
            va="top",
        )
    out = WORK / "yaml.png"
    fig.savefig(out, facecolor=TERM)
    plt.close(fig)
    return out


def render(scenes, out: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "19",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        str(out),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for seconds, setup in scenes:
        fig = new_fig()
        update = setup(fig)
        shade = fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, color=BG, zorder=1000))
        n = int(seconds * FPS)
        for k in range(n):
            u = k / max(n - 1, 1)
            update(u)
            ts = k / FPS
            shade.set_alpha(float(np.clip(max(1 - ts / 0.3, 1 - (seconds - ts) / 0.3), 0, 1)))
            fig.canvas.draw()
            proc.stdin.write(np.asarray(fig.canvas.buffer_rgba()).tobytes())
        plt.close(fig)
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


def main():
    site = ROOT / "examples/sites/campus/site.yaml"
    campus_plot = WORK / "campus_compare.png"
    print("running the commands shown in the video ...")
    s_version = sh("trecsar --version")
    s_scen = sh("trecsar scenarios", 12)
    s_cmp = sh("trecsar compare --scenario tunnel --seed 1003", 8)
    s_run = sh("trecsar run --scenario forest_winter --seed 1002 --events", 16)
    s_site = sh(
        f"trecsar compare --site {site.relative_to(ROOT)} --seed 2 --planners greedy_bayes,trecsar "
        f"--plot {campus_plot}",
        8,
    )
    s_site = [ln if not ln.startswith("plot:") else "plot: campus_compare.png" for ln in s_site]
    s_json = sh("trecsar run --scenario hazmat_industrial --seed 5 --json", 16)
    scenes = [
        text_scene(
            [
                ("TREC-SAR", 64, INK, "bold", 0.66, 0.0, None),
                ("The command-line tool", 30, INK2, "normal", 0.53, 0.12, None),
                (
                    "Search-and-rescue planning you can run on any laptop · v0.1.0",
                    18,
                    MUTED,
                    "normal",
                    0.44,
                    0.25,
                    None,
                ),
                ('pip install -e "core[viz]"', 22, PROMPT, "normal", 0.30, 0.4, MONO),
            ],
            4.5,
        ),
        terminal_scene(
            "1 · Install and explore",
            "Python 3.10+ on Linux, macOS or Windows",
            [("trecsar --version", s_version), ("trecsar scenarios", s_scen)],
            9.0,
        ),
        terminal_scene(
            "2 · Compare every planner on the same mission",
            "Same tunnel, same missing worker, same detection luck for each planner",
            [("trecsar compare --scenario tunnel --seed 1003", s_cmp)],
            9.0,
        ),
        terminal_scene(
            "3 · Read the mission log",
            "What the robot decided, minute by minute",
            [("trecsar run --scenario forest_winter --seed 1002 --events", s_run)],
            11.0,
        ),
        terminal_scene(
            "4 · Bring your own site",
            "Paint a map, describe it in YAML, and every planner runs on it",
            [
                (
                    f"trecsar compare --site {site.relative_to(ROOT)} --seed 2 "
                    "--planners greedy_bayes,trecsar --plot campus_compare.png",
                    s_site,
                )
            ],
            8.0,
        ),
        image_scene(
            "4 · Bring your own site",
            "examples/sites/campus — a campus park at night, 90 × 90 cells at 5 m",
            yaml_card(site),
            campus_plot,
            "Left: the site file.  Right: the plot written by --plot. One pixel of the map = one 5 m grid cell.",
            9.0,
            "site.yaml",
            "campus_compare.png",
        ),
        terminal_scene(
            "5 · Script it",
            "Every command speaks JSON",
            [("trecsar run --scenario hazmat_industrial --seed 5 --json", s_json)],
            7.5,
        ),
        text_scene(
            [
                ("6 · Run the ROS 2 stack — no GPU needed", 30, INK, "bold", 0.86, 0.0, None),
                (
                    "$ ros2 launch trecsar_bringup headless.launch.py scenario:=hazmat_industrial seed:=5",
                    19,
                    INK,
                    "normal",
                    0.72,
                    0.08,
                    MONO,
                ),
                ("$ ros2 topic echo --once /trecsar/report", 19, INK, "normal", 0.66, 0.16, MONO),
                (
                    "Mission manager, radio-link simulator, detector and drone cue run as ROS 2 nodes with a",
                    18,
                    INK2,
                    "normal",
                    0.54,
                    0.26,
                    None,
                ),
                (
                    "stand-in robot. GitHub runs this full mission on every push and fails unless a casualty",
                    18,
                    INK2,
                    "normal",
                    0.49,
                    0.26,
                    None,
                ),
                (
                    "report arrives. The 3D Gazebo + Nav2 demo uses the same nodes.",
                    18,
                    INK2,
                    "normal",
                    0.44,
                    0.26,
                    None,
                ),
                ("github.com/mustafarkhan/trec-sar", 26, BLUE, "bold", 0.26, 0.45, None),
                (
                    "Mustafa R. Khan  ·  MIT license  ·  simulation results, limits documented in the repo",
                    15,
                    MUTED,
                    "normal",
                    0.17,
                    0.55,
                    None,
                ),
            ],
            8.5,
        ),
    ]
    out = ROOT / "media" / "trec-sar_cli_demo.mp4"
    render(scenes, out)


if __name__ == "__main__":
    main()
