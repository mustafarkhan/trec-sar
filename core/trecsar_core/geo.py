"""Georeferencing: site grid <-> ETRS89 coordinates, without a GIS dependency.

European emergency services exchange positions in ETRS89 (EPSG:4258; within a metre
of WGS 84 for this purpose) and in ETRS89 / UTM grids such as ETRS-TM35FIN
(EPSG:3067) in Finland or EPSG:25832/25833 in central Europe. A site becomes
georeferenced by anchoring its south-west corner:

    Georef(lat=62.0, lon=26.0)

Local metres are converted with the GRS80 radii of curvature at the anchor (a
local tangent-plane approximation: about 0.15 m of error 1 km from the anchor,
growing with the square of the distance — use it for sites of a few kilometres). Grid coordinates use the Krüger
series for the transverse Mercator projection (Karney 2011), accurate to
millimetres inside a UTM zone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# GRS80 ellipsoid (the ETRS89 reference ellipsoid)
_A = 6378137.0
_F = 1 / 298.257222101
_E2 = _F * (2 - _F)
_K0 = 0.9996


@dataclass(frozen=True)
class Georef:
    """Anchor of a site: ETRS89 latitude/longitude (degrees) of the grid's south-west corner.

    The grid is north-up: x east, y north, as in Terrain.cell_to_xy.
    `illustrative=True` marks anchors of the fictional built-in scenarios.
    """

    lat: float
    lon: float
    illustrative: bool = False

    def __post_init__(self):
        if not (-90 < self.lat < 90 and -180 <= self.lon <= 180):
            raise ValueError(f"georef anchor ({self.lat}, {self.lon}) is not a valid latitude/longitude")

    def to_latlon(self, x_m: float, y_m: float) -> tuple[float, float]:
        """Local east/north metres from the anchor -> ETRS89 (lat, lon) in degrees."""
        phi = math.radians(self.lat)
        w = math.sqrt(1 - _E2 * math.sin(phi) ** 2)
        m = _A * (1 - _E2) / w**3  # meridian radius of curvature
        n = _A / w  # prime-vertical radius of curvature
        return self.lat + math.degrees(y_m / m), self.lon + math.degrees(x_m / (n * math.cos(phi)))


def utm_zone(lon: float) -> int:
    return int((lon + 180) // 6) % 60 + 1


def etrs89_to_utm(lat: float, lon: float, zone: int | None = None) -> tuple[int, float, float]:
    """ETRS89 (lat, lon) -> (zone, easting, northing) on GRS80, northern hemisphere.

    With zone=35 this is ETRS-TM35FIN (EPSG:3067), which uses zone 35 for all of Finland;
    with the natural zone it is EPSG:258xx (ETRS89 / UTM zone xx N).
    """
    if lat < 0:
        raise ValueError("southern-hemisphere grid coordinates are not supported")
    zone = utm_zone(lon) if zone is None else int(zone)
    lon0 = math.radians(zone * 6 - 183)
    phi, lam = math.radians(lat), math.radians(lon) - lon0
    n = _F / (2 - _F)
    a_hat = _A / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    alpha = (
        n / 2 - 2 * n**2 / 3 + 5 * n**3 / 16,
        13 * n**2 / 48 - 3 * n**3 / 5,
        61 * n**3 / 240,
    )
    c = 2 * math.sqrt(n) / (1 + n)
    t = math.sinh(math.atanh(math.sin(phi)) - c * math.atanh(c * math.sin(phi)))
    xi = math.atan2(t, math.cos(lam))
    eta = math.atanh(math.sin(lam) / math.sqrt(1 + t * t))
    e = eta + sum(a * math.cos(2 * j * xi) * math.sinh(2 * j * eta) for j, a in enumerate(alpha, start=1))
    nn = xi + sum(a * math.sin(2 * j * xi) * math.cosh(2 * j * eta) for j, a in enumerate(alpha, start=1))
    return zone, 500_000.0 + _K0 * a_hat * e, _K0 * a_hat * nn


def grid_reference(lat: float, lon: float) -> tuple[str, float, float]:
    """(grid name with EPSG code, easting, northing) in the grid a European service would expect.

    Finland uses one zone for the whole country (ETRS-TM35FIN); elsewhere the natural UTM zone.
    """
    if 59.0 <= lat <= 70.5 and 19.0 <= lon <= 32.0:
        _, e, n = etrs89_to_utm(lat, lon, zone=35)
        return "ETRS-TM35FIN (EPSG:3067)", e, n
    zone, e, n = etrs89_to_utm(lat, lon)
    return f"ETRS89 / UTM zone {zone}N (EPSG:258{zone:02d})", e, n
