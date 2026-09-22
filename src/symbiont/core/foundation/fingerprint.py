"""Deterministic scientific runtime fingerprinting for Symbiont organisms.

Produces a canonical, versioned cryptographic hash of all declarative parameters,
budgets, and structures that govern an organism's cognitive constitution.

Important: This is a configuration fingerprint, not an entire trajectory identity.
It strictly excludes learned dynamic state, observation buffers, checkpoint weights,
instance identifiers (organism_id), tick counts, file paths, and environment dynamics.
Full experimental replication requires the configuration fingerprint, the initial
seed/checkpoint state, and the deterministic simulator/environment harness.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from typing import Any

from .epistemic import EpistemicConventions, DEFAULT_EPISTEMIC_CONVENTIONS
from .limits import OrganismLimits
from ..embodiment.physiology_config import PhysiologyConfig, DEFAULT_PHYSIOLOGY_CONFIG
from ...cognition.limits import KernelLimits

FINGERPRINT_SCHEMA_VERSION = 5


def _canonical_normalize(value: Any) -> Any:
    """Recursively normalize data structures to stable, deterministic primitives.

    Strictly enforces canonical representation types:
    - None
    - bool
    - int
    - float (encoded using exact IEEE-754 float.hex(), preventing rounding collisions)
    - str
    - bytes / bytearray (encoded as bijective hexadecimal strings)
    - dataclasses (converted to dict via asdict)
    - dict (keys must be strictly str; sorted lexicographically)
    - set / frozenset (normalized and sorted deterministically)
    - list / tuple (preserves sequence order)

    Any other type raises TypeError rather than silently falling back to str(value).
    """
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_normalize(asdict(value))
    if isinstance(value, dict):
        normalized_dict: dict[str, Any] = {}
        for k in sorted(value.keys()):
            if not isinstance(k, str):
                raise TypeError(
                    f"Dictionary keys in configuration fingerprint must be strings; got {type(k).__name__}"
                )
            normalized_dict[k] = _canonical_normalize(value[k])
        return normalized_dict
    if isinstance(value, (set, frozenset)):
        normalized_items = [_canonical_normalize(item) for item in value]
        return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [_canonical_normalize(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value.hex()
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, str):
        return value
    raise TypeError(
        f"Cannot canonically normalize object of type {type(value).__name__} for configuration fingerprint"
    )


def generate_runtime_fingerprint_from_runtime(
    runtime: Any,
    *,
    software_version: str | None = None,
    build_identity: str | None = None,
) -> str:
    """Derive a canonical configuration fingerprint from a live OrganismRuntime instance.

    Captures only declarative parameters, budgets, limits, and structures that govern
    behavior and developmental trajectory: software version, optional build identity,
    effective physiology, full kernel limits, genome, heritable genome, mutation seed,
    epigenetic configuration, attention budget, investigate ticks, conflict_z, min_samples,
    discovery modes, explicit metabolism, and autonomous behavior options.

    Strictly excludes:
    - checkpoint / learned dynamic state (synaptic weights, observations)
    - external environment definition
    - observation sequence
    - instance identity (organism_id)
    - timestamps, ticks, and wall-clock time
    - local filesystem paths, host PIDs or sockets

    Scientific note: The configuration fingerprint identifies the organism's declarative
    constitution, not its realized trajectory. Full trajectory replication requires the
    configuration fingerprint, the initial state/checkpoint, and the environment harness.

    Scientific recommendation: Reproducible experiments should explicitly supply ``build_identity``
    (preferably the commit SHA) whenever ``symbiont.__version__`` may remain identical across
    developmental commits.
    """
    if software_version is None:
        try:
            import symbiont
            software_version = getattr(symbiont, "__version__", "unknown")
        except Exception:
            software_version = "unknown"

    effective = dict(runtime.effective_configuration())

    # Exclude instance identity and transient runtime markers
    effective.pop("organism_id", None)
    effective.pop("saved_at_tick", None)
    effective.pop("tick_count", None)

    payload: dict[str, Any] = {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "software_version": str(software_version),
        "build_identity": str(build_identity) if build_identity is not None else None,
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
    build_identity: str | None = None,
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
        "build_identity": str(build_identity) if build_identity is not None else None,
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
