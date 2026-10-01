"""Pure geometry helpers for the Physics3D monitor."""

from __future__ import annotations

from collections.abc import Sequence


def _convex_hull_2d(points: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Compute 2D convex hull via Monotone Chain algorithm."""
    unique_pts = sorted(set(points))
    if len(unique_pts) <= 2:
        return list(unique_pts)

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in unique_pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[float, float]] = []
    for point in reversed(unique_pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _point_in_polygon_2d(point: tuple[float, float], poly: Sequence[tuple[float, float]]) -> bool:
    """Ray casting point-in-polygon containment test."""
    if len(poly) < 3:
        return False
    x, y = point
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside
