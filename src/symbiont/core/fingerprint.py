"""Deterministic scientific runtime fingerprinting for Symbiont organisms.

Produces a canonical, versioned cryptographic hash of all parameters and
structures that can affect an organism's developmental and cognitive trajectory.

Ensures strict experimental reproducibility across studies and long-term audits.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any

from .epistemic import EpistemicConventions, DEFAULT_EPISTEMIC_CONVENTIONS
from .limits import OrganismLimits
from .physiology import PhysiologyConfig, DEFAULT_PHYSIOLOGY_CONFIG
from ..cognition.limits import KernelLimits

FINGERPRINT_SCHEMA_VERSION = 1


def _canonical_normalize(value: Any) -> Any:
    """Recursively normalize data structures to stable, sorted primitives."""
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_normalize(asdict(value))
    if isinstance(value, dict):
        return {str(k): _canonical_normalize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonical_normalize(v) for v in value]
    if isinstance(value, float):
        # Canonical float formatting: avoids platform-specific string discrepancies
        if not (-1e15 < value < 1e15):
            return repr(value)
        return round(value, 10)
    return value


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
    """Generate a reproducible, canonical SHA-256 fingerprint for the runtime configuration."""
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
]
