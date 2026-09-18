from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SensoryLimits:
    """Hard non-learnable bounds for the organism-owned sensory phenotype."""

    max_modalities: int = 4
    max_active_sensors: int = 64
    max_nascent_sensors: int = 8
    max_sources_per_sensor: int = 4
    max_transduction_nodes: int = 8
    max_temporal_depth: int = 64
    max_sensor_mutations_per_window: int = 4
    mutation_window_ticks: int = 16
    max_sensor_checkpoint_bytes: int = 131_072

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
