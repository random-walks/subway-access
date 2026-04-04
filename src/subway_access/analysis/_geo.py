"""Geodesy helpers for catchment generation.

The preferred implementation lives in ``nyc-geo-toolkit``. ``subway-access``
keeps a local fallback so the core workflow still works in a fresh source tree.
"""

from __future__ import annotations

__all__ = [
    "build_circle_polygon",
    "haversine_distance_meters",
    "walk_radius_meters",
]

try:
    from nyc_geo_toolkit import (
        build_circle_polygon as _toolkit_build_circle_polygon,
    )
    from nyc_geo_toolkit import (
        haversine_distance_meters as _toolkit_haversine_distance_meters,
    )
    from nyc_geo_toolkit import (
        walk_radius_meters as _toolkit_walk_radius_meters,
    )
except ImportError:  # pragma: no cover - fallback until dependency is installed
    from math import asin, atan2, cos, degrees, pi, radians, sin, sqrt

    EARTH_RADIUS_METERS = 6_371_000.0
    METERS_PER_MINUTE_WALKING = 80.0
    _POSITIVE_MINUTES_MESSAGE = "Catchment minutes must be positive."
    _POSITIVE_RADIUS_MESSAGE = "Catchment radius must be positive."
    _MINIMUM_SIDES_MESSAGE = "Catchment polygon needs at least 8 sides."

    def _local_haversine_distance_meters(
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float,
    ) -> float:
        """Return the great-circle distance between two points in meters."""

        lat1 = radians(latitude_a)
        lon1 = radians(longitude_a)
        lat2 = radians(latitude_b)
        lon2 = radians(longitude_b)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        haversine_term = (
            sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )
        return 2 * EARTH_RADIUS_METERS * asin(sqrt(haversine_term))

    def _local_walk_radius_meters(minutes: int) -> float:
        """Convert walking minutes into the first-pass Euclidean radius."""

        if minutes <= 0:
            raise ValueError(_POSITIVE_MINUTES_MESSAGE)
        return minutes * METERS_PER_MINUTE_WALKING

    def _local_build_circle_polygon(
        latitude: float,
        longitude: float,
        radius_meters: float,
        *,
        sides: int = 24,
    ) -> tuple[tuple[float, float], ...]:
        """Build a lon/lat polygon approximating a circle around a point."""

        if radius_meters <= 0:
            raise ValueError(_POSITIVE_RADIUS_MESSAGE)
        if sides < 8:
            raise ValueError(_MINIMUM_SIDES_MESSAGE)

        latitude_radians = radians(latitude)
        angular_distance = radius_meters / EARTH_RADIUS_METERS
        points: list[tuple[float, float]] = []

        for index in range(sides):
            bearing = 2 * pi * (index / sides)
            lat = asin(
                sin(latitude_radians) * cos(angular_distance)
                + cos(latitude_radians) * sin(angular_distance) * cos(bearing)
            )
            lon = radians(longitude) + atan2(
                sin(bearing) * sin(angular_distance) * cos(latitude_radians),
                cos(angular_distance) - sin(latitude_radians) * sin(lat),
            )
            points.append((round(degrees(lon), 6), round(degrees(lat), 6)))

        points.append(points[0])
        return tuple(points)

    haversine_distance_meters = _local_haversine_distance_meters
    walk_radius_meters = _local_walk_radius_meters
    build_circle_polygon = _local_build_circle_polygon
else:  # pragma: no cover - exercised via dependency integration

    def haversine_distance_meters(
        latitude_a: float,
        longitude_a: float,
        latitude_b: float,
        longitude_b: float,
    ) -> float:
        return _toolkit_haversine_distance_meters(
            latitude_a,
            longitude_a,
            latitude_b,
            longitude_b,
        )

    def walk_radius_meters(minutes: int) -> float:
        return _toolkit_walk_radius_meters(float(minutes))

    def build_circle_polygon(
        latitude: float,
        longitude: float,
        radius_meters: float,
        *,
        sides: int = 24,
    ) -> tuple[tuple[float, float], ...]:
        return _toolkit_build_circle_polygon(
            latitude,
            longitude,
            radius_meters,
            sides=sides,
        )
