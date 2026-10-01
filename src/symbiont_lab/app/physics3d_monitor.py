"""Compatibility facade; implementation lives in the Physics3D package."""

from .physics3d.monitor.viewer import *  # noqa: F403
from .physics3d.monitor.viewer import __dict__ as _viewer_dict

globals().update({k: v for k, v in _viewer_dict.items() if not k.startswith("__")})
