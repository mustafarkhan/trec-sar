"""Static checks that run without a ROS installation (CI-friendly)."""

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "trecsar_mission"


def test_all_nodes_parse_and_define_main():
    for f in PKG.glob("*.py"):
        tree = ast.parse(f.read_text())
        if f.stem in ("mission_manager", "link_sim", "aerial_spotter", "sim_detector", "yolo_detector"):
            assert any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body), f.name
