"""Spatial weights matrix construction for panel models."""

from __future__ import annotations

from typing import Any

from ..analysis._geo import haversine_distance_meters


def build_distance_weights(
    unit_centroids: dict[str, tuple[float, float]],
    *,
    threshold_meters: float = 2000.0,
    row_standardize: bool = True,
) -> dict[str, dict[str, float]]:
    """Build a distance-based spatial weights matrix.

    Creates a symmetric weights matrix where units within the distance
    threshold are neighbors, weighted by inverse distance.

    Args:
        unit_centroids: Mapping of unit_id -> (latitude, longitude).
        threshold_meters: Maximum distance for two units to be neighbors.
        row_standardize: If True, normalize each row to sum to 1.0.

    Returns:
        Nested dict: unit_id -> neighbor_unit_id -> weight.
        Units with no neighbors have an empty inner dict.

    Example:
        >>> centroids = {"T1": (40.75, -73.99), "T2": (40.751, -73.991)}
        >>> weights = build_distance_weights(centroids, threshold_meters=500)
        >>> len(weights)
        2
    """

    unit_ids = sorted(unit_centroids)
    raw_weights: dict[str, dict[str, float]] = {uid: {} for uid in unit_ids}

    for i, uid_a in enumerate(unit_ids):
        lat_a, lon_a = unit_centroids[uid_a]
        for uid_b in unit_ids[i + 1 :]:
            lat_b, lon_b = unit_centroids[uid_b]
            distance = haversine_distance_meters(
                latitude_a=lat_a,
                longitude_a=lon_a,
                latitude_b=lat_b,
                longitude_b=lon_b,
            )
            if distance <= threshold_meters and distance > 0:
                weight = 1.0 / distance
                raw_weights[uid_a][uid_b] = weight
                raw_weights[uid_b][uid_a] = weight

    if row_standardize:
        for uid in unit_ids:
            row_sum = sum(raw_weights[uid].values())
            if row_sum > 0:
                raw_weights[uid] = {
                    neighbor: w / row_sum for neighbor, w in raw_weights[uid].items()
                }

    return raw_weights


def weights_to_pysal(
    weights: dict[str, dict[str, float]],
) -> Any:
    """Convert a weights dict to a PySAL W object.

    Args:
        weights: Nested dict from ``build_distance_weights``.

    Returns:
        A ``libpysal.weights.W`` instance.

    Raises:
        ImportError: If libpysal is not installed.

    Example:
        >>> w = weights_to_pysal(weights)
        >>> w.n
        200
    """

    try:
        from libpysal.weights import W
    except ImportError as exc:
        message = (
            "libpysal is required for spatial weights. "
            "Install with: pip install subway-access[spatial-models]"
        )
        raise ImportError(message) from exc

    neighbors = {uid: list(nbrs) for uid, nbrs in weights.items()}
    weight_values = {uid: list(nbrs.values()) for uid, nbrs in weights.items()}
    return W(neighbors, weight_values)
