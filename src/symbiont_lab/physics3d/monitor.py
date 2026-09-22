"""Compatibility facade for the application-owned Physics3D monitor.

The implementation belongs to :mod:`symbiont_lab.app.physics3d_monitor`.
This module deliberately re-exports private helpers too because the historical
Physics3D CLI and its regression tests import a small number of them directly.
"""
from symbiont_lab.app import physics3d_monitor as _impl

__all__ = [
    name
    for name in dir(_impl)
    if not name.startswith("__")
]
globals().update({name: getattr(_impl, name) for name in __all__})


def __getattr__(name: str):
    return getattr(_impl, name)
