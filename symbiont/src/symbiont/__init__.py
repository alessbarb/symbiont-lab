"""Symbiont: the organism."""

__version__ = "0.90.0"

# Importing the core first fixes the initialisation order of the organism's
# packages. Several of them (cognition.checkpoint, host.acclimation) import
# each other in a cycle that only resolves when entered through the core.
from symbiont import core as core  # noqa: E402

__all__ = ["__version__", "core"]
