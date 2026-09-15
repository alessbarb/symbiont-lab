"""Backward-compatible import surface for bounded birth authority."""
from .birth_authority import BirthRecord, DeathRecord, HabitatBirthAuthority

__all__ = ["BirthRecord", "DeathRecord", "HabitatBirthAuthority"]
