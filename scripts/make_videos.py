#!/usr/bin/env python3
"""Render the project videos from real simulation runs.

    python3 scripts/make_videos.py --which linkedin     # 1080x1350, ~50 s
    python3 scripts/make_videos.py --which github       # 1920x1080, ~2 min
    python3 scripts/make_videos.py --which both --stills  # also writes a PNG per scene

Every map frame is a recorded mission from trecsar_core.sim (same seeds as the
results), not an illustration. Needs matplotlib and ffmpeg on PATH.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))
from trecsar_core import World, build, run  # noqa: E402

# ------------------------------------------------------------------ theme ----------
BG = "#101215"
PANEL = "#181b20"
INK = "#f0efec"
INK2 = "#a8a7a2"
MUTED = "#6c6b67"
BLUE = "#3987e5"       # TREC-SAR
ORANGE = "#d95926"
AQUA = "#199e70"       # link-unaware greedy
YELLOW = "#c98500"
RED = "#e66767"
GOOD = "#3fb97a"
PLANNER_COLOR = {"trecsar": BLUE, "greedy_bayes": AQUA, "greedy_sf": ORANGE, "lawnmower": YELLOW}
PLANNER_NAME = {"trecsar": "TREC-SAR (link-aware)", "greedy_bayes": "Link-unaware search",
                "greedy_sf": "Greedy + planned link loss", "lawnmower": "Lawnmower sweep"}

for f in font_manager.findSystemFonts():
    if "Inter" in f:
        font_manager.fontManager.addfont(f)
FONT = "Inter" if any("Inter" in f.name for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({"font.family": FONT, "text.color": INK, "figure.facecolor": BG, "axes.facecolor": BG,
                     "savefig.facecolor": BG})

AUTHOR = "Mustafa R. Khan"
REPO = "github.com/mustafarkhan/trec-sar"


def ease(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def appear(u: float, start: float, dur: float = 0.12) -> float:
    return ease((u - start) / dur)


@dataclass
class Scene:
    seconds: float
    setup: Callable          # setup(fig, fmt) -> update(u in 0..1)
    name: str


# ------------------------------------------------------------------ text scenes ----
def text_scene(lines, seconds, name, align="left"):
    """lines: list of (text, size, color, weight, y, start)"""
    def setup(fig, fmt):
        objs = []
        x = 0.08 if align == "left" else 0.5
        ha = "left" if align == "left" else "center"
        for text, size, color, weight, y, start in lines:
            t = fig.text(x, y, text, fontsize=size * fmt.scale, color=color, weight=weight, ha=ha, va="top",
                         wrap=True, linespacing=1.25)
            t._get_wrap_line_width = (lambda w=fig.get_figwidth() * fig.dpi * 0.84: w)
            objs.append((t, start))

        def update(u):
            for t, start in objs:
                t.set_alpha(appear(u, start))
        return update
    return Scene(seconds, setup, name)


def title_scene(fmt_vertical: bool):
    y0 = 0.62 if fmt_vertical else 0.66
    return text_scene([
        ("TREC-SAR", 64, INK, "bold", y0, 0.0),
        ("From a fielded tracked ground robot\nto civilian search and rescue", 26, INK2, "normal",
         y0 - (0.11 if fmt_vertical else 0.15), 0.12),
        (f"{AUTHOR}  ·  open source  ·  ROS 2 / Gazebo / Python", 15, MUTED, "normal", 0.12, 0.3),
    ], 4.5, "title")


def trec_scene(seconds=9.0):
    def setup(fig, fmt):
        v = fmt.vertical
        fig.text(0.08, 0.93, "PART 1  ·  THE ORIGINAL PROJECT", fontsize=14 * fmt.scale, color=BLUE, weight="bold", va="top")
        fig.text(0.08, 0.89, "TREC", fontsize=40 * fmt.scale, weight="bold", va="top")
        fig.text(0.08, 0.83 if v else 0.80, "Tele-operated, Tracked, Reconfigurable Unmanned Ground Vehicle",
                 fontsize=17 * fmt.scale, color=INK, va="top")
        fig.text(0.08, 0.80 if v else 0.755, "Government of Pakistan  ·  NUST College of Electrical & Mechanical Engineering",
                 fontsize=13 * fmt.scale, color=INK2, va="top")
        img1 = plt.imread(ROOT / "docs/media/trec_robot.jpg")
        img2 = plt.imread(ROOT / "docs/media/trec_mine_detector.jpg")
        if v:
            a1 = fig.add_axes([0.08, 0.52, 0.40, 0.22]); a2 = fig.add_axes([0.52, 0.52, 0.40, 0.22])
        else:
            a1 = fig.add_axes([0.06, 0.37, 0.40, 0.30]); a2 = fig.add_axes([0.06, 0.04, 0.40, 0.28])
        for a, im, cap in ((a1, img1, "TREC with manipulator"), (a2, img2, "Land-mine detector payload")):
            a.imshow(im, aspect="auto"); a.set_xticks([]); a.set_yticks([])
            for sp in a.spines.values():
                sp.set_color(MUTED)
            a.set_title(cap, fontsize=11 * fmt.scale, color=INK2, loc="left", pad=6)
        facts = [
            ("Demonstrated to senior government stakeholders", INK, "bold"),
            ("Prototype handed over for field trials", INK, "bold"),
            ("80 kg  ·  8 km/h  ·  turns on the spot  ·  climbs steep slopes", INK2, "normal"),
            ("NI cRIO-9012 control  ·  live video  ·  30 m night vision", INK2, "normal"),
            ("Swappable payloads: manipulator arm, mine detector", INK2, "normal"),
            ("Operator console with connection failsafe and battery alarm", INK2, "normal"),
        ]
        objs = []
        x = 0.08 if v else 0.53
        y = 0.45 if v else 0.66
        step = 0.058 if v else 0.085
        for i, (txt, col, w) in enumerate(facts):
            t = fig.text(x, y - i * step, "•  " + txt, fontsize=(17 if v else 18) * fmt.scale, color=col, weight=w,
                         va="top", wrap=True)
            t._get_wrap_line_width = (lambda W=fig.get_figwidth() * fig.dpi * (0.84 if v else 0.42): W)
            objs.append((t, 0.08 + i * 0.09))
        for a in (a1, a2):
            a.set_alpha(1)

        def update(u):
            for t, s in objs:
                t.set_alpha(appear(u, s))
        return update
    return Scene(seconds, setup, "trec")


# ------------------------------------------------------------------ map replay -----
def basemap(t):
    img = np.ones(t.shape + (3,)) * np.array([0.12, 0.14, 0.13])
    shade = {"dense spruce": (0.07, 0.11, 0.08), "bog (suo)": (0.16, 0.15, 0.11), "trail": (0.28, 0.26, 0.22),
             "road": (0.30, 0.30, 0.30), "tunnels": (0.26, 0.24, 0.21), "rock-fall rubble": (0.38, 0.27, 0.20),
             "pipe racks": (0.18, 0.19, 0.24), "gas plume (no humans)": (0.30, 0.25, 0.08)}
    if t.name == "hazmat_industrial":
        img[:] = (0.17, 0.17, 0.18)
    for name, mask in t.labels.items():
        if name in shade:
            img[mask] = shade[name]
    img[~t.passable] = (0.04, 0.045, 0.05)
    if "lake (no-go: ice not trusted)" in t.labels:
        img[t.labels["lake (no-go: ice not trusted)"]] = (0.08, 0.14, 0.22)
    return img


class ReplayPanel:
    def __init__(self, ax, hud_ax, world, result, planner, fmt):
        self.w, self.r, self.p, self.fmt = world, result, planner, fmt
        t = world.sc.terrain
        self.t = t
        self.times = [f.time_s for f in result.frames]
        self.p0 = float(result.frames[0].belief.max())
        ax.imshow(basemap(t), interpolation="nearest")
        rgba = np.zeros(t.shape + (4,))
        rgba[..., :3] = (0.62, 0.42, 0.95)
        self.rgba = rgba
        self.belief_im = ax.imshow(rgba, interpolation="bilinear")
        self.cov_cache = {}
        self.cov_art = None
        self.ax = ax
        col = PLANNER_COLOR[planner]
        self.trail, = ax.plot([], [], color=col, lw=2.0 * fmt.scale, alpha=0.95, solid_capstyle="round")
        self.robot, = ax.plot([], [], "o", ms=11 * fmt.scale, color=INK, mec=col, mew=3 * fmt.scale)
        self.relays, = ax.plot([], [], "^", ms=12 * fmt.scale, color=ORANGE, mec=BG, mew=1.5)
        bx, by = t.base[1], t.base[0]
        ax.plot(bx, by, "s", ms=12 * fmt.scale, color=RED, mec=INK, mew=1.5)
        cr, cc = t.rc(result.casualty)
        self.cas, = ax.plot(cc, cr, "X", ms=13 * fmt.scale, color=RED, mec=INK, mew=1.2, alpha=0.35)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color(MUTED)
        hud_ax.axis("off")
        hud_ax.set_xlim(0, 1); hud_ax.set_ylim(0, 1)
        if fmt.vertical:
            ty, bx0, by, ix, iy = 0.5, 0.52, 0.5, 0.74, 0.5
        else:   # two lines: name + badge on top, status underneath
            ty, bx0, by, ix, iy = 0.75, 0.66, 0.75, 0.0, 0.18
        self.hud_title = hud_ax.text(0, ty, PLANNER_NAME[planner], fontsize=16 * fmt.scale, weight="bold",
                                     color=col, va="center")
        self.badge = hud_ax.text(bx0, by, "", fontsize=12 * fmt.scale, weight="bold", va="center",
                                 bbox=dict(boxstyle="round,pad=0.35", fc=GOOD, ec="none"))
        self.info = hud_ax.text(ix, iy, "", fontsize=12 * fmt.scale, color=INK2, va="center")
        self.banner = ax.text(0.5, 0.06, "", transform=ax.transAxes, ha="center", va="bottom",
                              fontsize=15 * fmt.scale, weight="bold", color=BG,
                              bbox=dict(boxstyle="round,pad=0.5", fc=GOOD, ec="none"), alpha=0)
        self.banner.get_bbox_patch().set_alpha(0)

    def coverage(self, n_relays):
        if n_relays not in self.cov_cache:
            nodes = [self.t.base] + [self.t.rc(c) for c in self.r.relays[:n_relays]]
            cov = self.w.link.coverage(nodes) >= self.w.sc.mission.link_threshold_db
            self.cov_cache[n_relays] = cov
        return self.cov_cache[n_relays]

    def draw(self, sim_t):
        i = max(0, bisect.bisect_right(self.times, sim_t) - 1)
        f = self.r.frames[i]
        self.rgba[..., 3] = np.clip(f.belief / self.p0, 0, 1) ** 1.3 * 0.75
        self.belief_im.set_data(self.rgba)
        if self.cov_art is None or self.cov_art[0] != f.relays_down:
            if self.cov_art is not None:
                self.cov_art[1].remove()
            cs = self.ax.contour(self.coverage(f.relays_down), levels=[0.5], colors=[INK2], linewidths=1.2,
                                 linestyles="--")
            self.cov_art = (f.relays_down, cs)
        tr = np.array([self.t.rc(c) for c in self.r.trajectory[:max(f.traj_len, 1)]])
        self.trail.set_data(tr[:, 1], tr[:, 0])
        rr, rc = self.t.rc(f.pos)
        self.robot.set_data([rc], [rr])
        rel = np.array([self.t.rc(c) for c in self.r.relays[:f.relays_down]]).reshape(-1, 2)
        self.relays.set_data(rel[:, 1], rel[:, 0])
        reported = self.r.success and sim_t >= self.r.time_report_s
        if reported:
            self.badge.set_text(" REPORTED ")
            self.badge.get_bbox_patch().set_facecolor(GOOD)
            self.badge.set_color(BG)
        elif sim_t >= self.times[-1] and not self.r.success:
            self.badge.set_text(" NOT REPORTED ")
            self.badge.get_bbox_patch().set_facecolor("#7a2e2e")
            self.badge.set_color(INK)
        elif f.connected:
            self.badge.set_text(" LINK OK ")
            self.badge.get_bbox_patch().set_facecolor("#24563f")
            self.badge.set_color(INK)
        else:
            self.badge.set_text(" LINK LOST ")
            self.badge.get_bbox_patch().set_facecolor("#7a2e2e")
            self.badge.set_color(INK)
        st_txt = {"SEARCH": "searching", "LINK_RECOVERY": "returning to signal", "REPORT": "person found, reporting",
                  "RTH": "returning home", "DONE": "done", "FAILED": "stopped", "TIMEOUT": "stopped"}.get(f.state, f.state)
        if reported:
            st_txt = "done"
        self.info.set_text(f"relays {f.relays_down}  ·  {st_txt}")
        end = self.times[-1]
        if reported:
            self.cas.set_alpha(1.0)
            self.banner.set_text(f"Casualty reported to command post  ·  {self.r.time_report_s / 60:.1f} min")
            self.banner.set_alpha(1); self.banner.get_bbox_patch().set_alpha(0.95)
            self.banner.get_bbox_patch().set_facecolor(GOOD)
        elif sim_t >= end and not self.r.success:
            why = {"FAILED": "returned without a report", "TIMEOUT": "time limit reached"}.get(self.r.end_state,
                                                                                                    self.r.end_state.lower())
            self.banner.set_text(f"Not reported  ·  {why} at {end / 60:.0f} min")
            self.banner.set_alpha(1); self.banner.get_bbox_patch().set_alpha(0.95)
            self.banner.get_bbox_patch().set_facecolor(RED)


def replay_scene(scenario, seed, planners, seconds, heading, caption, name, sub=None):
    def setup(fig, fmt):
        w = World(build(scenario))
        runs = [run(w, p, seed, record=True, frame_every_s=6.0) for p in planners]
        T = max(r.frames[-1].time_s for r in runs)
        v = fmt.vertical
        fig.text(0.05, 0.965, heading, fontsize=(22 if v else 24) * fmt.scale, weight="bold", va="top")
        fig.text(0.05, 0.925 if v else 0.915, sub or w.sc.title, fontsize=13 * fmt.scale, color=INK2, va="top")
        clock = fig.text(0.95, 0.965, "", fontsize=18 * fmt.scale, ha="right", va="top", color=INK,
                         family="DejaVu Sans Mono")
        panels = []
        n = len(planners)
        for k, (p, r) in enumerate(zip(planners, runs)):
            if v:
                top = 0.885 - k * 0.405
                hud = fig.add_axes([0.08, top - 0.04, 0.84, 0.04])
                ax = fig.add_axes([0.08, top - 0.405, 0.84, 0.36])
                ax.set_anchor("C")
            else:
                left = 0.03 + k * (0.94 / n)
                width = 0.94 / n - 0.02
                hud = fig.add_axes([left, 0.79, width, 0.07])
                ax = fig.add_axes([left, 0.10, width, 0.68])
                ax.set_anchor("N")
            panels.append(ReplayPanel(ax, hud, w, r, p, fmt))
        fig.text(0.05, 0.02 if v else 0.03, caption, fontsize=11.5 * fmt.scale, color=MUTED, va="bottom", wrap=True)

        def update(u):
            st = min(u / 0.86, 1.0) * T
            mm, ss = divmod(int(st), 60)
            clock.set_text(f"mission  {mm:02d}:{ss:02d}")
            for pnl in panels:
                pnl.draw(st)
        return update
    return Scene(seconds, setup, name)


# ------------------------------------------------------------------ results --------
def load_results():
    rows = list(csv.DictReader(open(ROOT / "results" / "results.csv")))
    out = {}
    for r in rows:
        k = (r["variant"], r["planner"])
        out.setdefault(k, []).append(r)
    agg = {k: (np.mean([int(x["success"]) for x in v]), np.mean([int(x["relays_used"]) for x in v]))
           for k, v in out.items()}
    return agg


def results_scene(planners, seconds, name):
    agg = load_results()
    variants = [("forest_winter", "Winter forest"), ("tunnel", "Tunnel"), ("hazmat_industrial", "Chemical release")]

    def setup(fig, fmt):
        v = fmt.vertical
        fig.text(0.06, 0.95, "Results  ·  200 simulated missions per bar", fontsize=24 * fmt.scale,
                 weight="bold", va="top")
        fig.text(0.06, 0.905, "Share of missions where the command post received the casualty report",
                 fontsize=13 * fmt.scale, color=INK2, va="top")
        bars = []
        for j, (vk, vt) in enumerate(variants):
            if v:
                ax = fig.add_axes([0.30, 0.66 - j * 0.24, 0.62, 0.17])
            else:
                ax = fig.add_axes([0.06 + j * 0.315, 0.20, 0.27, 0.56])
            ax.set_facecolor(BG)
            vals = [agg[(vk, p)][0] for p in planners]
            rel = [agg[(vk, p)][1] for p in planners]
            pos = np.arange(len(planners))
            if v:
                b = ax.barh(pos[::-1], [0] * len(planners), color=[PLANNER_COLOR[p] for p in planners], height=0.62)
                ax.set_xlim(0, 1.25); ax.set_yticks([])
                ax.text(-0.02, 1.08, vt, transform=ax.transAxes, fontsize=17 * fmt.scale, weight="bold", va="bottom")
            else:
                b = ax.bar(pos, [0] * len(planners), color=[PLANNER_COLOR[p] for p in planners], width=0.62)
                ax.set_ylim(0, 1.18); ax.set_xticks([])
                ax.set_title(vt, fontsize=18 * fmt.scale, weight="bold", color=INK, loc="left")
            for sp in ax.spines.values():
                sp.set_visible(False)
            ax.tick_params(colors=MUTED, labelsize=10 * fmt.scale)
            if v:
                ax.set_xticks([])
            else:
                ax.set_yticks([])
            labels = []
            for i in range(len(planners)):
                labels.append(ax.text(0, 0, "", fontsize=13 * fmt.scale, color=INK, weight="bold",
                                      va="center" if v else "bottom", ha="left" if v else "center"))
            bars.append((b, vals, rel, labels, v))
        # legend
        for i, p in enumerate(planners):
            y = (0.13 - i * 0.03) if v else 0.10
            x = 0.06 if v else 0.06 + i * 0.235
            fig.patches.append(Rectangle((x, y - 0.012), 0.018 if v else 0.012, 0.02, transform=fig.transFigure,
                                         color=PLANNER_COLOR[p]))
            fig.text(x + (0.03 if v else 0.02), y, PLANNER_NAME[p], fontsize=12.5 * fmt.scale, color=INK2,
                     va="center")
        fig.text(0.06, 0.02, "Simulation, held-out seeds. Labels show success and mean relays used per mission.",
                 fontsize=11 * fmt.scale, color=MUTED, va="bottom")

        def update(u):
            g = ease(u / 0.45)
            for b, vals, rel, labels, vert in bars:
                for i, (rect, val) in enumerate(zip(b, vals)):
                    cur = val * g
                    if vert:
                        rect.set_width(cur)
                        y = rect.get_y() + rect.get_height() / 2
                        labels[i].set_position((cur + 0.03, y))
                    else:
                        rect.set_height(cur)
                        labels[i].set_position((rect.get_x() + rect.get_width() / 2, cur + 0.02))
                    labels[i].set_text(f"{cur:.0%}" + (f"  ·  {rel[i]:.1f} relays" if vert else f"\n{rel[i]:.1f} relays")
                                       if g > 0.98 else f"{cur:.0%}")
        return update
    return Scene(seconds, setup, name)


# ------------------------------------------------------------------ diagram --------
def how_scene(seconds=12.0):
    def setup(fig, fmt):
        fig.text(0.06, 0.94, "How TREC-SAR decides", fontsize=28 * fmt.scale, weight="bold", va="top")
        fig.text(0.06, 0.88, "Every replan: where to look next, and how the report gets home",
                 fontsize=14 * fmt.scale, color=INK2, va="top")
        ax = fig.add_axes([0.03, 0.06, 0.94, 0.78]); ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 60)
        boxes = [
            (2, 38, 20, 14, "Drone", "thermal cue:\n'possible person here'", INK2),
            (28, 38, 22, 14, "Probability map", "Bayesian update after\nevery look that finds nobody", "#9e6bf2"),
            (56, 38, 20, 14, "Candidate goals", "expected detection\nper metre of travel", INK2),
            (56, 8, 40, 20, "Radio check per goal", "in coverage?  →  go\nrelay at last good point covers it?  →  drop relay\nreturn before failsafe?  →  short excursion\notherwise  →  planned link-loss window", BLUE),
            (30, 8, 20, 18, "UGV", "Nav2 + SLAM\nthermal mast\nrelay dropper", INK2),
            (2, 8, 22, 18, "Command post", "report only counts\nwhen video arrives", GOOD),
        ]
        arts = []
        for i, (x, y, w_, h, title, body, col) in enumerate(boxes):
            p = FancyBboxPatch((x, y), w_, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=PANEL, ec=col, lw=2)
            ax.add_patch(p)
            t1 = ax.text(x + 1.2, y + h - 1.4, title, fontsize=15 * fmt.scale, weight="bold", color=col, va="top")
            t2 = ax.text(x + 1.2, y + h - 4.6, body, fontsize=11.5 * fmt.scale, color=INK, va="top", linespacing=1.35)
            arts.append(([p, t1, t2], 0.05 + i * 0.12))
        arrows = [((22.5, 45), (27.5, 45)), ((50.5, 45), (55.5, 45)), ((76, 37.5), (76, 28.5)),
                  ((55.5, 17), (50.5, 17)), ((29.5, 13), (24.5, 13))]
        arr_objs = []
        for i, (a, b) in enumerate(arrows):
            an = ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.8))
            arr_objs.append((an, 0.15 + i * 0.12))

        def update(u):
            for group, s in arts:
                al = appear(u, s)
                for o in group:
                    o.set_alpha(al)
            for an, s in arr_objs:
                an.arrow_patch.set_alpha(appear(u, s))
        return update
    return Scene(seconds, setup, "how")


# ------------------------------------------------------------------ rendering ------
@dataclass
class Fmt:
    w: int
    h: int
    fps: int
    vertical: bool
    scale: float


FADE = 0.35


def render(scenes, fmt, out: Path, stills_dir: Path | None = None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{fmt.w}x{fmt.h}",
           "-r", str(fmt.fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19",
           "-preset", "medium", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = 0
    for sc in scenes:
        fig = plt.figure(figsize=(fmt.w / 100, fmt.h / 100), dpi=100)
        update = sc.setup(fig, fmt)
        shade = fig.add_artist(Rectangle((0, 0), 1, 1, transform=fig.transFigure, color=BG, zorder=1000))
        n = int(round(sc.seconds * fmt.fps))
        for k in range(n):
            u = k / max(n - 1, 1)
            update(u)
            ts = k / fmt.fps
            fade = max(1 - ts / FADE, 0, 1 - (sc.seconds - ts) / FADE)
            shade.set_alpha(min(max(fade, 0), 1))
            fig.canvas.draw()
            buf = np.asarray(fig.canvas.buffer_rgba())
            proc.stdin.write(buf.tobytes())
            if stills_dir is not None and k == int(n * 0.85):
                fig.savefig(stills_dir / f"{out.stem}_{sc.name}.png", dpi=100)
        total += n
        plt.close(fig)
        print(f"  {sc.name:12s} {sc.seconds:5.1f} s")
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out}  ({total / fmt.fps:.0f} s, {out.stat().st_size / 1e6:.1f} MB)")


def preview(scenes, fmt, out_dir: Path, tag: str, u: float = 0.9):
    """Render one still per scene (fast layout check)."""
    for sc in scenes:
        fig = plt.figure(figsize=(fmt.w / 100, fmt.h / 100), dpi=100)
        sc.setup(fig, fmt)(u)
        fig.savefig(out_dir / f"{tag}_{sc.name}.png", dpi=100)
        plt.close(fig)
        print("  still", tag, sc.name)


def linkedin_scenes():
    return [
        title_scene(True),
        trec_scene(8.0),
        text_scene([
            ("PART 2  ·  THE CIVILIAN SUCCESSOR", 14, BLUE, "bold", 0.80, 0.0),
            ("A rescue robot that finds a missing person out of radio range hasn't helped anyone yet.",
             30, INK, "bold", 0.74, 0.05),
            ("TREC-SAR plans the search and the radio network together: where to look, where to drop relays, "
             "and when to accept a short, planned loss of signal.", 18, INK2, "normal", 0.54, 0.3),
        ], 6.5, "problem"),
        replay_scene("forest_winter", 1002, ["greedy_bayes", "trecsar"], 20.0,
                     "Same forest. Same missing person.", "Replays of recorded simulation runs · purple = where the "
                     "person may be · dashed = radio coverage · ▲ relay · ■ command post · × person", "replay_forest",
                     sub="Winter night, boreal forest  ·  simulation"),
        results_scene(["greedy_bayes", "trecsar"], 8.0, "results"),
        text_scene([
            ("Open source", 34, INK, "bold", 0.66, 0.0),
            ("Python · ROS 2 Jazzy · Gazebo · Nav2 · YOLO", 18, INK2, "normal", 0.58, 0.1),
            (REPO, 22, BLUE, "bold", 0.47, 0.2),
            ("Simulation results with confidence intervals, ablation and failure-mode analysis in the repo.",
             14, MUTED, "normal", 0.36, 0.35),
            (AUTHOR, 18, INK, "bold", 0.14, 0.4),
        ], 5.5, "end", align="left"),
    ]


def github_scenes():
    return [
        title_scene(False),
        trec_scene(10.0),
        text_scene([
            ("PART 2  ·  THE CIVILIAN SUCCESSOR", 14, BLUE, "bold", 0.80, 0.0),
            ("A detection is worth nothing until a human at the command post receives it.", 34, INK, "bold", 0.74, 0.05),
            ("In forests, tunnels and industrial sites the radio link fails long before the batteries do. "
             "TREC-SAR treats the link as a planning constraint, not an afterthought.", 20, INK2, "normal", 0.50, 0.3),
        ], 7.0, "problem"),
        how_scene(13.0),
        replay_scene("forest_winter", 1002, ["greedy_bayes", "trecsar"], 24.0,
                     "Scenario 1 · winter forest, missing elderly person",
                     "Recorded simulation runs, same casualty and detection luck for both · purple = probability map · "
                     "dashed = radio coverage · ▲ relay · ■ command post · × person (unknown to the robot)",
                     "replay_forest"),
        replay_scene("tunnel", 1003, ["greedy_bayes", "trecsar"], 17.0,
                     "Scenario 2 · tunnel network after a rock fall",
                     "No GPS, radio stops at the first bend. TREC-SAR reports with zero relays here by planning a "
                     "short link-loss window — at the cost of minutes without live video.", "replay_tunnel"),
        replay_scene("hazmat_industrial", 1022, ["greedy_bayes", "trecsar"], 14.0,
                     "Scenario 3 · chemical release at an industrial site",
                     "This seed shows a failure of link-unaware search behind steel tanks. Across 200 runs the methods differ "
                     "less here: 96 % vs 98 % success.", "replay_hazmat"),
        results_scene(["lawnmower", "greedy_bayes", "greedy_sf", "trecsar"], 12.0, "results"),
        text_scene([
            ("What the ablation shows", 30, INK, "bold", 0.82, 0.0),
            ("•  Planning the link loss is the big win: forest success rises from about 40 % to about 60 %.",
             20, INK, "normal", 0.68, 0.1),
            ("•  Probability-driven relay placement then reaches the same success with about half the relays "
             "in the forest and about 90 % fewer in the tunnel.", 20, INK, "normal", 0.56, 0.25),
            ("•  The price is more time without live video. That is an operator's trade-off, so it is a tunable weight.",
             20, INK, "normal", 0.40, 0.4),
            ("•  In the open industrial site all probability-driven methods perform the same.", 20, INK2, "normal",
             0.28, 0.55),
        ], 11.0, "ablation"),
        text_scene([
            ("Limits, stated plainly", 30, INK, "bold", 0.82, 0.0),
            ("•  All results are simulation. Radio, detection and lost-person models are plausible placeholders.",
             19, INK2, "normal", 0.70, 0.1),
            ("•  Tuned on seeds 100–159, evaluated on 1000–1199, with 95 % confidence intervals.", 19, INK2,
             "normal", 0.60, 0.22),
            ("•  The ROS 2 / Gazebo stack is written and checked, not yet field-tested on hardware.", 19, INK2,
             "normal", 0.50, 0.34),
            ("•  Next: radio site survey, thermal tests under spruce canopy, cold-battery logs.", 19, INK2,
             "normal", 0.40, 0.46),
        ], 9.0, "limits"),
        text_scene([
            ("Run it yourself", 32, INK, "bold", 0.74, 0.0),
            ("pip install -e core  ·  pytest  ·  python3 scripts/run_experiments.py", 18, INK2, "normal", 0.64, 0.1),
            ("ros2 launch trecsar_bringup bringup.launch.py scenario:=forest_winter", 18, INK2, "normal", 0.58, 0.15),
            (REPO, 26, BLUE, "bold", 0.44, 0.25),
            (f"{AUTHOR}  ·  Apache-2.0", 18, INK, "bold", 0.16, 0.35),
        ], 7.0, "end"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", choices=["linkedin", "github", "both"], default="both")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--preview", action="store_true", help="only render one still per scene")
    ap.add_argument("--out", type=Path, default=ROOT / "media")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    stills = a.out / "stills" if a.stills else None
    if stills:
        stills.mkdir(exist_ok=True)
    if a.preview:
        d = a.out / "preview"
        d.mkdir(exist_ok=True)
        if a.which in ("linkedin", "both"):
            preview(linkedin_scenes(), Fmt(1080, 1350, a.fps, True, 1.15), d, "linkedin")
        if a.which in ("github", "both"):
            preview(github_scenes(), Fmt(1920, 1080, a.fps, False, 1.25), d, "github")
        return
    if a.which in ("linkedin", "both"):
        render(linkedin_scenes(), Fmt(1080, 1350, a.fps, True, 1.15), a.out / "trec-sar_linkedin.mp4", stills)
    if a.which in ("github", "both"):
        render(github_scenes(), Fmt(1920, 1080, a.fps, False, 1.25), a.out / "trec-sar_github.mp4", stills)


if __name__ == "__main__":
    main()
