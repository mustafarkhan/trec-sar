"""Casualty reports in formats a European command-and-control system can read.

* CAP 1.2 — the OASIS Common Alerting Protocol (ITU-T X.1303), the alert format used
  by public-warning and emergency-management systems across Europe.
* GeoJSON (RFC 7946) — casualty, command post, relays and the robot's track for any
  GIS or map display.

Positions are ETRS89 latitude/longitude plus the national grid (ETRS-TM35FIN in
Finland, ETRS89 / UTM elsewhere). The site must be georeferenced (Terrain.georef).

Messages from the simulator carry CAP status "Exercise" and scope "Restricted": a
casualty's position is personal data and is addressed to the incident command, not
to the public.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

from .geo import grid_reference

CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"


@dataclass(frozen=True)
class CasualtyReport:
    scenario: str
    title: str
    lat: float
    lon: float
    grid: str
    easting: float
    northing: float
    x_m: float  # site frame: east of the south-west corner
    y_m: float
    radius_m: float  # position uncertainty: half a grid cell diagonal
    time_detect_s: float
    time_report_s: float
    channel: str  # "video" or "narrowband"
    relays_used: int
    planner: str
    seed: int
    illustrative_position: bool

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        for k in ("lat", "lon"):
            d[k] = round(d[k], 7)
        for k in ("easting", "northing", "x_m", "y_m", "radius_m", "time_detect_s", "time_report_s"):
            d[k] = round(float(d[k]), 1)
        return d


def casualty_report(world, result) -> CasualtyReport | None:
    """Report for a finished mission, or None when the casualty was not reported."""
    if not result.success:
        return None
    t = world.sc.terrain
    if t.georef is None:
        raise ValueError(
            f"site '{t.name}' is not georeferenced; add `georef: {{lat: .., lon: ..}}` to the site file "
            "(ETRS89 position of the map's south-west corner)"
        )
    x, y = t.cell_to_xy(t.rc(result.casualty))
    lat, lon = t.georef.to_latlon(x, y)
    grid, e, n = grid_reference(lat, lon)
    return CasualtyReport(
        scenario=world.sc.key,
        title=world.sc.title,
        lat=lat,
        lon=lon,
        grid=grid,
        easting=e,
        northing=n,
        x_m=x,
        y_m=y,
        radius_m=t.resolution * 0.71,
        time_detect_s=float(result.time_detect_s),
        time_report_s=float(result.time_report_s),
        channel=result.report_channel or "video",
        relays_used=result.relays_used,
        planner=result.planner,
        seed=result.seed,
        illustrative_position=t.georef.illustrative,
    )


def _cap_time(dt: datetime) -> str:
    """CAP 1.2 dateTime: explicit numeric offset, never 'Z'."""
    if dt.tzinfo is None:
        raise ValueError("CAP timestamps need a time zone; pass an aware datetime")
    s = dt.replace(microsecond=0).isoformat()
    return s[:-6] + "-00:00" if s.endswith("+00:00") else s


def to_cap(
    report: CasualtyReport,
    mission_start: datetime,
    status: str = "Exercise",
    sender: str = "trec-sar.simulation",
    identifier: str | None = None,
) -> str:
    """CAP 1.2 alert for one casualty report (XML text).

    `mission_start` is the wall-clock time the robot launched; the alert is stamped at
    mission_start + time_report_s. Use status="Actual" only for a real incident.
    """
    if status not in ("Actual", "Exercise", "System", "Test", "Draft"):
        raise ValueError(f"invalid CAP status '{status}'")
    if re.search(r"[\s,<&]", sender):
        raise ValueError("CAP sender must not contain spaces, commas or the characters < and &")
    sent = mission_start + timedelta(seconds=report.time_report_s)
    ident = identifier or f"trecsar-{report.scenario}-{report.seed}-{sent.strftime('%Y%m%dT%H%M%S')}"
    if re.search(r"[\s,<&]", ident):
        raise ValueError("CAP identifier must not contain spaces, commas or the characters < and &")

    ET.register_namespace("", CAP_NS)
    alert = ET.Element(f"{{{CAP_NS}}}alert")

    def add(parent, tag, text):
        el = ET.SubElement(parent, f"{{{CAP_NS}}}{tag}")
        el.text = str(text)
        return el

    add(alert, "identifier", ident)
    add(alert, "sender", sender)
    add(alert, "sent", _cap_time(sent))
    add(alert, "status", status)
    add(alert, "msgType", "Alert")
    add(alert, "source", f"TREC-SAR search robot, planner {report.planner}")
    add(alert, "scope", "Restricted")
    add(alert, "restriction", "Incident command and assigned rescue units only: contains the position of a casualty")
    if status == "Exercise":
        note = "Simulated mission. Not a real incident."
        if report.illustrative_position:
            note += " The coordinates are an illustrative anchor for a fictional site."
        add(alert, "note", note)

    info = ET.SubElement(alert, f"{{{CAP_NS}}}info")
    add(info, "language", "en-GB")
    add(info, "category", "Rescue")
    add(info, "event", "Casualty located by search robot")
    add(info, "responseType", "Execute")
    add(info, "urgency", "Immediate")
    add(info, "severity", "Unknown")  # the robot cannot assess the person's condition
    add(info, "certainty", "Likely")  # machine detection, to be confirmed by the operator on the image
    add(info, "onset", _cap_time(mission_start + timedelta(seconds=report.time_detect_s)))
    add(info, "senderName", "TREC-SAR ground robot")
    add(info, "headline", f"Person detected at {report.lat:.5f}, {report.lon:.5f}")
    add(
        info,
        "description",
        f"{report.title}. The ground robot detected a person {report.time_detect_s / 60:.1f} min after launch and "
        f"delivered this report at {report.time_report_s / 60:.1f} min over the "
        f"{'narrowband 868 MHz link (thumbnail image)' if report.channel == 'narrowband' else 'video link'}. "
        f"Position {report.grid}: E {report.easting:.0f}, N {report.northing:.0f}; uncertainty about "
        f"{report.radius_m:.0f} m.",
    )
    add(info, "instruction", "Confirm the detection on the robot's image, then send a team to the position.")
    for name, value in (
        ("grid", report.grid),
        ("easting_m", f"{report.easting:.1f}"),
        ("northing_m", f"{report.northing:.1f}"),
        ("report_channel", report.channel),
        ("time_detect_s", f"{report.time_detect_s:.0f}"),
        ("time_report_s", f"{report.time_report_s:.0f}"),
        ("relays_used", report.relays_used),
    ):
        p = ET.SubElement(info, f"{{{CAP_NS}}}parameter")
        add(p, "valueName", name)
        add(p, "value", value)
    area = ET.SubElement(info, f"{{{CAP_NS}}}area")
    add(area, "areaDesc", f"Detected position, {report.title}")
    add(area, "circle", f"{report.lat:.6f},{report.lon:.6f} {report.radius_m / 1000:.3f}")
    ET.indent(alert)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(alert, encoding="unicode") + "\n"


def to_geojson(world, result) -> dict:
    """GeoJSON FeatureCollection (RFC 7946: longitude, latitude) of a mission: casualty if reported,
    command post, relays, and the robot's track when the run was recorded."""
    t = world.sc.terrain
    if t.georef is None:
        raise ValueError(f"site '{t.name}' is not georeferenced; add a `georef` anchor to the site file")

    def lonlat(cell_rc):
        lat, lon = t.georef.to_latlon(*t.cell_to_xy(cell_rc))
        return [round(lon, 7), round(lat, 7)]

    def feature(geometry_type, coords, **props):
        return {"type": "Feature", "geometry": {"type": geometry_type, "coordinates": coords}, "properties": props}

    feats = [feature("Point", lonlat(t.base), kind="command_post")]
    feats += [feature("Point", lonlat(t.rc(c)), kind="relay", order=i + 1) for i, c in enumerate(result.relays)]
    if len(result.trajectory) > 1:
        feats.append(
            feature(
                "LineString", [lonlat(t.rc(c)) for c in result.trajectory], kind="robot_track", planner=result.planner
            )
        )
    rep = casualty_report(world, result)
    if rep is not None:
        feats.append(feature("Point", [round(rep.lon, 7), round(rep.lat, 7)], kind="casualty", **rep.as_dict()))
    return {
        "type": "FeatureCollection",
        "name": f"{world.sc.key} seed {result.seed}",
        "features": feats,
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
