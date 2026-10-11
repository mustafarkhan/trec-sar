"""Custom sites, the command-line tool and the benchmark API."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "core"))

from trecsar_core import World, build, run  # noqa: E402
from trecsar_core.bench import run_benchmark  # noqa: E402
from trecsar_core.cli import main  # noqa: E402
from trecsar_core.site import CLASSES, terrain_from_image  # noqa: E402

CAMPUS = ROOT / "examples" / "sites" / "campus" / "site.yaml"


def test_terrain_from_image_maps_colours_to_classes():
    img = np.zeros((4, 5, 3), np.uint8) + 255
    img[1, 1:4] = (0, 0, 0)  # building row
    legend = {"#ffffff": "open", "#000000": "building"}
    t = terrain_from_image(img, legend, CLASSES, 5.0, base=(3, 0), lkp=(0, 4))
    assert not t.passable[1, 2] and t.passable[0, 0]
    assert t.rf_db_per_m[1, 2] == CLASSES["building"]["rf_db_per_m"]


def test_unknown_colour_is_reported_clearly():
    img = np.zeros((3, 3, 3), np.uint8)
    img[1, 1] = (255, 0, 0)
    with pytest.raises(ValueError, match="matches no legend entry"):
        terrain_from_image(img, {"#000000": "open"}, CLASSES, 5.0, base=(0, 0), lkp=(2, 2))


def test_unknown_class_is_reported_clearly():
    img = np.zeros((3, 3, 3), np.uint8)
    with pytest.raises(ValueError, match="not defined"):
        terrain_from_image(img, {"#000000": "lava"}, CLASSES, 5.0, base=(0, 0), lkp=(2, 2))


def test_example_campus_site_runs_end_to_end():
    sc = build(str(CAMPUS))
    assert sc.terrain.shape == (90, 90)
    assert sc.mission.relays == 2
    r = run(World(sc), "trecsar", 1)
    assert r.end_state in ("DONE", "FAILED", "TIMEOUT")


def test_unknown_scenario_name_is_a_clear_error():
    with pytest.raises(KeyError, match="unknown scenario"):
        build("atlantis")


def test_cli_run_json(capsys):
    assert main(["run", "--scenario", "hazmat_industrial", "--seed", "1", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["planner"] == "trecsar" and out["scenario"] == "hazmat_industrial"


def test_cli_compare_on_custom_site_writes_plot(tmp_path, capsys):
    pytest.importorskip("matplotlib")
    png = tmp_path / "cmp.png"
    assert (
        main(
            ["compare", "--site", str(CAMPUS), "--seed", "2", "--planners", "greedy_bayes,trecsar", "--plot", str(png)]
        )
        == 0
    )
    assert png.stat().st_size > 10_000


def test_cli_bad_site_path_exits_with_error(capsys):
    assert main(["run", "--site", "does/not/exist.yaml"]) == 2
    assert "error" in capsys.readouterr().err


def test_benchmark_api_writes_results(tmp_path):
    summary = run_benchmark(runs=2, workers=1, out=tmp_path, variant_keys=["hazmat_industrial"])
    assert (tmp_path / "results.csv").exists() and (tmp_path / "summary.md").exists()
    assert {s["planner"] for s in summary} == {"lawnmower", "greedy_bayes", "greedy_sf", "trecsar", "trecsar_cal"}
