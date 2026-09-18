from __future__ import annotations

from typing import Any

from .system import SensorySystem


def export_sensory_checkpoint(system: SensorySystem) -> dict[str, Any]:
    return system.checkpoint()


def restore_sensory_checkpoint(
    payload: dict[str, Any] | None,
    *,
    plasticity_enabled: bool | None = None,
) -> SensorySystem:
    return SensorySystem.restore(payload, plasticity_enabled=plasticity_enabled)
