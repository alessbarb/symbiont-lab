from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SensoryLimits:
    """Hard non-learnable bounds for the organism-owned sensory phenotype."""

    # Safety ceilings; sensory development remains evidence/plasticity gated.
    max_modalities: int = 16
    max_active_sensors: int = 256
    max_nascent_sensors: int = 32
    max_sources_per_sensor: int = 16
    max_transduction_nodes: int = 32
    max_temporal_depth: int = 256
    max_sensor_mutations_per_window: int = 16
    mutation_window_ticks: int = 16
    max_sensor_checkpoint_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
