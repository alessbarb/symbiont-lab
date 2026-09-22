"""Compatibility facade for the application-owned Physics3D monitor.

All public and private symbols are forwarded during the migration because the
existing Physics3D CLI and regression tests intentionally use a small number of
private helpers such as _viewer_main and _event_transition.
"""
from symbiont_lab.app import physics3d_monitor as _impl

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

__all__ = [name for name in globals() if not name.startswith("__")]
