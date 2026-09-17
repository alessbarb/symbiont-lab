"""Deterministic scientific runtime fingerprinting for Symbiont organisms.

Produces a canonical, versioned cryptographic hash of all parameters and
structures that can affect an organism's developmental and cognitive trajectory.

Ensures strict experimental reproducibility across studies and long-term audits.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from typing import Any

from .epistemic import EpistemicConventions, DEFAULT_EPISTEMIC_CONVENTIONS
from .limits import OrganismLimits
from .physiology_config import PhysiologyConfig, DEFAULT_PHYSIOLOGY_CONFIG
from ..cognition.limits import KernelLimits

FINGERPRINT_SCHEMA_VERSION = 2


def _canonical_normalize(value: Any) -> Any:
    """Recursively normalize data structures to stable, deterministic primitives.

    - Floats are encoded using exact IEEE-754 hex representations (`float.hex()`),
      guaranteeing that identical binary floats yield identical representations
      and distinct floats never collide due to arbitrary rounding.
    - Sets and frozensets are recursively normalized and sorted by deterministic JSON serialization.
    - Dicts are recursively normalized and sorted by string keys.
    - Lists and tuples preserve sequence order.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_normalize(asdict(value))
    if isinstance(value, dict):
        return {
            str(k): _canonical_normalize(v)
            for k, v in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (set, frozenset)):
        normalized_items = [_canonical_normalize(item) for item in value]
        return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [_canonical_normalize(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value.hex()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def generate_runtime_fingerprint_from_runtime(runtime: Any) -> str:
    """Derive a canonical configuration fingerprint from a live OrganismRuntime instance.

    Captures only parameters and structures that govern behavior and trajectory:
    effective physiology, kernel limits, genome, heritable genome, mutation seed,
    epigenetic configuration, attention budget, investigate ticks, discovery modes,
    metabolism, and autonomous behavior options.

    Strictly excludes instance identity (organism_id), tick counters, timestamps,
    file paths, PIDs, and learned dynamic state.
    """
    effective = dict(runtime.effective_configuration())

    # Exclude instance identity and transient runtime markers
    effective.pop("organism_id", None)
    effective.pop("saved_at_tick", None)
    effective.pop("tick_count", None)

    payload: dict[str, Any] = {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "effective_configuration": effective,
        "epistemic_conventions": asdict(DEFAULT_EPISTEMIC_CONVENTIONS),
        "canonical_limits": asdict(OrganismLimits()),
    }

    normalized = _canonical_normalize(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generate_runtime_fingerprint(
    *,
    software_version: str,
    genome_id: str | None = None,
    genome_hash: str | None = None,
    epistemic_conventions: EpistemicConventions | None = None,
    physiology_config: PhysiologyConfig | None = None,
    organism_limits: OrganismLimits | None = None,
    kernel_limits: KernelLimits | None = None,
    subsystem_overrides: dict[str, Any] | None = None,
) -> str:
    """Low-level helper to generate a reproducible fingerprint from explicit arguments."""
    payload: dict[str, Any] = {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "software_version": str(software_version),
        "genome_id": genome_id,
        "genome_hash": genome_hash,
        "epistemic": asdict(epistemic_conventions or DEFAULT_EPISTEMIC_CONVENTIONS),
        "physiology": asdict(physiology_config or DEFAULT_PHYSIOLOGY_CONFIG),
        "organism_limits": asdict(organism_limits or OrganismLimits()),
        "kernel_limits": asdict(kernel_limits or KernelLimits()),
        "subsystems": dict(subsystem_overrides or {}),
    }

    normalized = _canonical_normalize(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "FINGERPRINT_SCHEMA_VERSION",
    "generate_runtime_fingerprint",
    "generate_runtime_fingerprint_from_runtime",
]
