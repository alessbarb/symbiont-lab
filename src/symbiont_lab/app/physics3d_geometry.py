"""Compatibility facade; implementation lives in the Physics3D package."""

from .physics3d.geometry import *  # noqa: F403
from .physics3d.geometry import _convex_hull_2d, _point_in_polygon_2d  # noqa: F401
