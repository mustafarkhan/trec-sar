"""Robot model checks (URDF). Skipped when xacro is not installed."""

import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

XACRO = Path(__file__).resolve().parents[2] / "ros2_ws/src/trecsar_description/urdf/trecsar.urdf.xacro"


def _urdf(cameras: bool = True) -> ET.Element:
    if shutil.which("xacro") is None:
        pytest.skip("xacro not installed")
    out = subprocess.run(["xacro", str(XACRO), f"cameras:={str(cameras).lower()}"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return ET.fromstring(out.stdout)


def _positions(root):
    joints = {}
    for j in root.findall("joint"):
        o = j.find("origin")
        xyz = [float(v) for v in (o.get("xyz") if o is not None and o.get("xyz") else "0 0 0").split()]
        joints[j.find("child").get("link")] = (j.find("parent").get("link"), np.array(xyz))

    def pos(link):
        p = np.zeros(3)
        while link in joints:
            parent, xyz = joints[link]
            p = p + xyz
            link = parent
        return p

    return pos


def test_tree_has_single_root_and_trec_mass():
    root = _urdf()
    links = {link.get("name") for link in root.findall("link")}
    children = {j.find("child").get("link") for j in root.findall("joint")}
    assert links - children == {"base_footprint"}
    base = next(link for link in root.findall("link") if link.get("name") == "base_link")
    assert float(base.find("inertial/mass").get("value")) == pytest.approx(80.0)  # TREC spec


@pytest.mark.parametrize("cameras", [True, False])
def test_lidar_scan_plane_is_clear_of_the_robot_body(cameras):
    """Regression: a lidar that sees the robot's own parts makes Nav2 report 'collision ahead'."""
    root = _urdf(cameras)
    pos = _positions(root)
    lz = pos("lidar_link")[2]
    for link in root.findall("link"):
        if link.get("name") == "lidar_link":
            continue
        for v in link.findall("visual"):
            g, o = v.find("geometry"), v.find("origin")
            off = np.array([float(x) for x in o.get("xyz").split()]) if o is not None and o.get("xyz") else np.zeros(3)
            cz = (pos(link.get("name")) + off)[2]
            if g.find("box") is not None:
                half = float(g.find("box").get("size").split()[2]) / 2
            elif g.find("cylinder") is not None:
                half = float(g.find("cylinder").get("length")) / 2
            else:
                continue
            assert not (cz - half <= lz <= cz + half), f"{link.get('name')} crosses the lidar scan plane"


def test_camera_switch_removes_camera_sensors():
    assert len(_urdf(True).findall(".//sensor")) == 4
    assert len(_urdf(False).findall(".//sensor")) == 2
