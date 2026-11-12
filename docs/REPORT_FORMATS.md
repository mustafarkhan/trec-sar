# Casualty report formats

A casualty report is only useful if the command post's own systems can read it. TREC-SAR exports it in two open
formats that European emergency-management software already handles.

```bash
trecsar run --scenario forest_winter --seed 1011 --report-radio eu868_500mw \
        --cap report.xml --geojson mission.geojson
```

```python
from datetime import datetime, timezone
from trecsar_core import World, build, run
from trecsar_core.report import casualty_report, to_cap, to_geojson

world = World(build("forest_winter"))
result = run(world, "trecsar", 1011, record=True)
report = casualty_report(world, result)  # None if the mission did not report
xml = to_cap(report, mission_start=datetime(2026, 1, 15, 16, 40, tzinfo=timezone.utc))
geo = to_geojson(world, result)
```

## CAP 1.2

The Common Alerting Protocol (OASIS CAP 1.2, also ITU-T X.1303) is the XML alert format used by public-warning
and emergency-management systems in Europe and worldwide. `to_cap` writes one alert per casualty:

| Field | Value | Why |
|---|---|---|
| `status` | `Exercise` (default), with a `note` | Simulated missions must never look like real incidents. `Actual` has to be requested explicitly |
| `scope` | `Restricted`, with a `restriction` | A casualty's position is personal data: addressed to incident command, not the public |
| `category` / `event` | `Rescue` / "Casualty located by search robot" | |
| `urgency`, `severity`, `certainty` | `Immediate`, `Unknown`, `Likely` | The robot cannot assess the person's condition, and a machine detection is not `Observed` until the operator confirms the image |
| `onset`, `sent` | detection time, delivery time | The gap between them is the time to report, the project's metric |
| `area/circle` | `lat,lon radius_km` | ETRS89 position with half a grid cell of uncertainty |
| `parameter` | national grid, easting, northing, report channel, relays used | Machine-readable extras |

Timestamps use an explicit numeric offset (`-00:00` for UTC), as CAP requires. Element order and enumerations are
tested against the published schema.

## GeoJSON

`to_geojson` returns an RFC 7946 FeatureCollection — casualty, command post, relays and, for recorded runs, the
robot's track — in longitude/latitude order, ready for QGIS or any web map.

## Coordinates

Sites are georeferenced by anchoring the map's south-west corner in ETRS89, the European reference system
(within a metre of WGS 84 for this purpose):

```yaml
georef: {lat: 61.4500, lon: 23.8500}     # in site.yaml
```

Reports give ETRS89 latitude/longitude and the grid a national service expects: **ETRS-TM35FIN (EPSG:3067)** in
Finland, **ETRS89 / UTM (EPSG:258xx)** elsewhere. The projection is implemented in
[`core/trecsar_core/geo.py`](../core/trecsar_core/geo.py) without a GIS dependency and agrees with PROJ to within
a millimetre at the test points. Local metres are converted with a tangent-plane approximation: about 0.15 m of
error 1 km from the anchor, so it suits sites of a few kilometres.

The built-in scenarios are fictional. Their anchors exist only to make the outputs well-formed, and every
report from them is flagged `illustrative_position`.

## Not covered

CAP carries the alert, not the imagery; the thumbnail or video travels on the robot's own link. EMSI (ISO/TR
22351) and NG112 location formats are not implemented.
