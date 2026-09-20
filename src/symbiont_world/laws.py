"""Generic, domain-name-free dynamics laws (docs/design/symbiont-world-v1.md
§13). Numeric parameters only -- no field/resource ever carries a domain
label such as "temperature" or "food" inside symbiont_world.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True, slots=True)
class PeriodicFieldLaw:
    amplitude: float
    bias: float
    angular_frequency: float
    phase: float = 0.0

    def value_at(self, tick: int) -> float:
        return self.bias + self.amplitude * math.sin(self.angular_frequency * tick + self.phase)


@dataclass(frozen=True, slots=True)
class ResourceLaw:
    capacity: float
    renewal_rate: float
    decay_rate: float
    initial_quantity: float

    def __post_init__(self) -> None:
        if self.capacity < 0 or self.renewal_rate < 0 or self.decay_rate < 0:
            raise ValueError("resource law parameters must be non-negative")
        if not 0.0 <= self.initial_quantity <= self.capacity:
            raise ValueError("initial_quantity must be within [0, capacity]")

    def step(self, current: float) -> float:
        renewed = current + self.renewal_rate * (self.capacity - current)
        decayed = renewed - self.decay_rate
        return min(self.capacity, max(0.0, decayed))


@dataclass(frozen=True, slots=True)
class HazardLaw:
    """Generic hazard exposure law.

    Exposure may depend on local *living* density and on a periodic temporal
    modulation. The law carries no semantic label; apparatus meaning remains
    outside symbiont_world.
    """

    base_probability: float
    density_coupling: float
    temporal_amplitude: float = 0.0
    angular_frequency: float = 0.0
    phase: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.base_probability <= 1.0:
            raise ValueError("base_probability must be within [0, 1]")
        if self.density_coupling < 0:
            raise ValueError("density_coupling must be non-negative")
        if not 0.0 <= self.temporal_amplitude <= 1.0:
            raise ValueError("temporal_amplitude must be within [0, 1]")
        if self.angular_frequency < 0:
            raise ValueError("angular_frequency must be non-negative")

    def exposure(self, local_density: float, *, tick: int = 0) -> float:
        density = max(0.0, min(1.0, float(local_density)))
        density_term = 1.0 + self.density_coupling * density
        temporal_term = 1.0
        if self.temporal_amplitude > 0.0 and self.angular_frequency > 0.0:
            temporal_term += self.temporal_amplitude * math.sin(
                self.angular_frequency * tick + self.phase
            )
        raw = self.base_probability * density_term * temporal_term
        return min(1.0, max(0.0, raw))
