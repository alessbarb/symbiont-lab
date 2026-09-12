from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ExperimentSpec:
    title: str = "Untitled experiment"
    hypothesis: str = ""
    success_criteria: str = ""
    notes: str = ""
    hosts: int = 100
    steps: int = 300
    seed: int = 7
    threat_rate: float = 0.018
    poison_fraction: float = 0.08
    heterogeneity: float = 0.12
    drift_step: int | None = None
    drift_fraction: float = 0.35
    drift_magnitude: float = 0.22
    delay: float = 0.04

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _bounded_text(value: Any, *, default: str = "", limit: int = 2000) -> str:
    if value is None:
        return default
    return str(value).strip()[:limit]


def _int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(high, max(low, parsed))


def _float(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return min(high, max(low, parsed))


def spec_from_payload(payload: dict[str, Any], defaults: ExperimentSpec | None = None) -> ExperimentSpec:
    d = defaults or ExperimentSpec()
    raw_drift = payload.get("drift_step", d.drift_step)
    if raw_drift in (None, "", -1, "-1"):
        drift_step = None
    else:
        drift_step = _int(raw_drift, 0, 0, 1_000_000)

    return ExperimentSpec(
        title=_bounded_text(payload.get("title"), default=d.title, limit=160) or d.title,
        hypothesis=_bounded_text(payload.get("hypothesis"), default=d.hypothesis),
        success_criteria=_bounded_text(payload.get("success_criteria"), default=d.success_criteria),
        notes=_bounded_text(payload.get("notes"), default=d.notes, limit=4000),
        hosts=_int(payload.get("hosts"), d.hosts, 1, 5_000),
        steps=_int(payload.get("steps"), d.steps, 1, 100_000),
        seed=_int(payload.get("seed"), d.seed, 0, 2_147_483_647),
        threat_rate=_float(payload.get("threat_rate"), d.threat_rate, 0.0, 1.0),
        poison_fraction=_float(payload.get("poison_fraction"), d.poison_fraction, 0.0, 1.0),
        heterogeneity=_float(payload.get("heterogeneity"), d.heterogeneity, 0.0, 1.0),
        drift_step=drift_step,
        drift_fraction=_float(payload.get("drift_fraction"), d.drift_fraction, 0.0, 1.0),
        drift_magnitude=_float(payload.get("drift_magnitude"), d.drift_magnitude, 0.0, 0.60),
        delay=_float(payload.get("delay"), d.delay, 0.0, 5.0),
    )
