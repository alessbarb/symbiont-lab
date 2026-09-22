"""Experimental-only characterization of cognitive kernel capacity.

This package deliberately constructs explicit ``KernelLimits`` instances. It
never changes the defaults used by the resident Symbiont runtime.
"""

from .config import BASELINE_KERNEL, KernelVariant

__all__ = ["BASELINE_KERNEL", "KernelVariant"]
