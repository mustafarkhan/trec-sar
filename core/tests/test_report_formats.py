"""Georeferencing and the CAP 1.2 / GeoJSON casualty report."""

import json
import re
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import pytest

from trecsar_core import World, build, run
from trecsar_core.cli import main
from trecsar_core.geo import Georef, etrs89_to_utm, grid_reference
from trecsar_core.report import CAP_NS, casualty_report, to_cap, to_geojson

# Element order and enumerations of the CAP 1.2 schema (OASIS / ITU-T X.1303 bis).
ALERT_ORDER = [
    "identifier", "sender", "sent", "status", "msgType", "source", "scope", "restriction", "addresses", "code",
    "note", "references", "incidents", "info",
]  # fmt: skip
INFO_ORDER = [
    "language", "category", "event", "responseType", "urgency", "severity", "certainty", "audience", "eventCode",
    "effective", "onset", "expires", "senderName", "headline", "description", "instruction", "web", "contact",
    "parameter", "resource", "area",
]  # fmt: skip
AREA_ORDER = ["areaDesc", "polygon", "circle", "geocode", "altitude", "ceiling"]
REQUIRED = {
    "alert": ["identifier", "sender", "sent", "status", "msgType", "scope"],
    "info": ["category", "event", "urgency", "severity", "certainty"],
    "area": ["areaDesc"],
}
ENUMS = {
    "status": {"Actual", "Exercise", "System", "Test", "Draft"},
    "msgType": {"Alert", "Update", "Cancel", "Ack", "Error"},
    "scope": {"Public", "Restricted", "Private"},
    "category": {"Geo", "Met", "Safety", "Security", "Rescue", "Fire", "Health", "Env", "Transport", "Infra", "CBRNE", "Other"},
    "responseType": {"Shelter", "Evacuate", "Prepare", "Execute", "Avoid", "Monitor", "Assess", "AllClear", "None"},
    "urgency": {"Immediate", "Expected", "Future", "Past", "Unknown"},
    "severity": {"Extreme", "Severe", "Moderate", "Minor", "Unknown"},
    "certainty": {"Observed", "Likely", "Possible", "Unlikely", "Unknown"},
}  # fmt: skip
CAP_DATETIME = re.compile(r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d[-,+]\d\d:\d\d")
START = datetime(2026, 1, 15, 18, 40, tzinfo=timezone(timedelta(hours=2)))


def _check(el, name, order):
    tags = [c.tag.replace(f"{{{CAP_NS}}}", "") for c in el]
    assert all(c.tag.startswith(f"{{{CAP_NS}}}") for c in el), "every element is in the CAP namespace"
    assert all(t in order for t in tags), f"unknown element in {name}: {tags}"
    assert [order.index(t) for t in tags] == sorted(order.index(t) for t in tags), f"{name} children out of order"
    for req in REQUIRED[name]:
        assert req in tags, f"{name} lacks required <{req}>"
    for c in el:
        tag = c.tag.replace(f"{{{CAP_NS}}}", "")
        if tag in ENUMS:
            assert c.text in ENUMS[tag], f"<{tag}>{c.text}"
        if tag in ("sent", "effective", "onset", "expires"):
            assert CAP_DATETIME.fullmatch(c.text), c.text


def _reported_run(key="forest_winter", radio=None):
    sc = build(key)
    sc.mission.report_radio = radio
    w = World(sc)
    for seed in range(1000, 1040):
        r = run(w, "trecsar", seed, record=True)
        if r.success:
            return w, r
    raise AssertionError("no reported mission in 40 seeds")


def test_transverse_mercator_matches_reference_values():
    # reference values computed with PROJ (EPSG:4258 -> EPSG:3067 / 25832 / 25833)
    for lat, lon, zone, e, n in [
        (62.0, 26.0, 35, 447624.200, 6874583.727),
        (60.1699, 24.9384, 35, 385611.317, 6672118.380),
        (68.9, 21.0, 35, 259271.514, 7654984.736),  # far from the central meridian: TM35FIN still one zone
        (47.37, 8.54, 32, 465270.423, 5246384.776),
        (42.35, 13.40, 33, 368218.799, 4689877.222),
    ]:
        z, ee, nn = etrs89_to_utm(lat, lon, zone)
        assert z == zone and ee == pytest.approx(e, abs=2e-3) and nn == pytest.approx(n, abs=2e-3)
    assert etrs89_to_utm(47.37, 8.54)[0] == 32


def test_grid_reference_uses_the_national_grid():
    assert grid_reference(62.0, 26.0)[0] == "ETRS-TM35FIN (EPSG:3067)"
    assert grid_reference(68.9, 21.0)[0] == "ETRS-TM35FIN (EPSG:3067)"
    assert grid_reference(47.37, 8.54)[0] == "ETRS89 / UTM zone 32N (EPSG:25832)"


def test_local_metres_to_latlon_is_consistent_with_the_grid():
    g = Georef(62.0, 26.0)
    _, e0, n0 = etrs89_to_utm(62.0, 26.0, 35)
    lat, lon = g.to_latlon(400.0, 300.0)
    _, e1, n1 = etrs89_to_utm(lat, lon, 35)
    # grid distances are scaled by the projection (about 0.9996) and rotated by grid convergence (< 1 degree here)
    assert ((e1 - e0) ** 2 + (n1 - n0) ** 2) ** 0.5 == pytest.approx(500.0 * 0.9996, abs=0.3)
    with pytest.raises(ValueError):
        Georef(95.0, 26.0)


def test_cap_alert_follows_the_schema_and_is_marked_as_an_exercise():
    w, r = _reported_run()
    rep = casualty_report(w, r)
    xml = to_cap(rep, START)
    alert = ET.fromstring(xml)
    assert alert.tag == f"{{{CAP_NS}}}alert"
    _check(alert, "alert", ALERT_ORDER)
    info = alert.find(f"{{{CAP_NS}}}info")
    _check(info, "info", INFO_ORDER)
    area = info.find(f"{{{CAP_NS}}}area")
    _check(area, "area", AREA_ORDER)
    get = lambda el, tag: el.find(f"{{{CAP_NS}}}{tag}").text  # noqa: E731
    assert get(alert, "status") == "Exercise" and "Not a real incident" in get(alert, "note")
    assert get(alert, "scope") == "Restricted" and alert.find(f"{{{CAP_NS}}}restriction") is not None
    lat, lon, radius = re.fullmatch(r"(-?[\d.]+),(-?[\d.]+) ([\d.]+)", get(area, "circle")).groups()
    assert float(lat) == pytest.approx(rep.lat, abs=1e-6) and float(lon) == pytest.approx(rep.lon, abs=1e-6)
    assert 0 < float(radius) < 0.05  # kilometres
    assert not re.search(r"[\s,<&]", get(alert, "identifier"))


def test_cap_times_are_offsets_never_z_and_need_a_time_zone():
    w, r = _reported_run()
    rep = casualty_report(w, r)
    xml = to_cap(rep, datetime(2026, 1, 15, 16, 40, tzinfo=timezone.utc))
    sent = ET.fromstring(xml).find(f"{{{CAP_NS}}}sent").text
    assert sent.endswith("-00:00") and "Z" not in sent
    with pytest.raises(ValueError, match="time zone"):
        to_cap(rep, datetime(2026, 1, 15, 16, 40))
    with pytest.raises(ValueError, match="status"):
        to_cap(rep, START, status="Real")


def test_report_position_is_the_casualty_cell_inside_the_site():
    w, r = _reported_run("hazmat_industrial")
    rep = casualty_report(w, r)
    t = w.sc.terrain
    assert (rep.x_m, rep.y_m) == t.cell_to_xy(t.rc(r.casualty))
    assert t.georef.lat < rep.lat < t.georef.lat + 0.01 and t.georef.lon < rep.lon < t.georef.lon + 0.01
    assert rep.illustrative_position and rep.grid.startswith("ETRS89 / UTM zone 31N")


def test_no_report_without_success_and_clear_error_without_georef():
    w, r = _reported_run()
    r.success = False
    assert casualty_report(w, r) is None
    r.success = True
    w.sc.terrain.georef = None
    with pytest.raises(ValueError, match="not georeferenced"):
        casualty_report(w, r)


def test_geojson_has_casualty_command_post_and_track_in_lon_lat_order():
    w, r = _reported_run(radio="eu868_500mw")
    gj = to_geojson(w, r)
    assert gj["type"] == "FeatureCollection"
    kinds = [f["properties"]["kind"] for f in gj["features"]]
    assert kinds.count("casualty") == 1 and "command_post" in kinds and "robot_track" in kinds
    cas = next(f for f in gj["features"] if f["properties"]["kind"] == "casualty")
    lon, lat = cas["geometry"]["coordinates"]
    assert 25.9 < lon < 26.1 and 61.9 < lat < 62.1  # RFC 7946: longitude first
    json.dumps(gj)  # serialisable


def test_cli_writes_cap_and_geojson(tmp_path, capsys):
    cap, gj = tmp_path / "report.xml", tmp_path / "mission.geojson"
    assert main(["run", "--scenario", "hazmat_industrial", "--seed", "5", "--cap", str(cap), "--geojson", str(gj)]) == 0
    assert ET.parse(cap).getroot().tag == f"{{{CAP_NS}}}alert"
    assert json.loads(gj.read_text())["features"]


def test_custom_site_georef_from_yaml():
    t = build("examples/sites/campus/site.yaml").terrain
    assert t.georef == Georef(60.2, 24.9, illustrative=True)
