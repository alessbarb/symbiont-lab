from __future__ import annotations

import math
from typing import Any

_KNOWN = {
    "compute.logical_cpu": {
        "label": "CPU load",
        "category": "compute",
        "unit": "%",
        "scale": 100.0,
    },
    "storage.disk_usage": {"label": "Disk usage", "category": "storage", "unit": "%", "scale": 1.0},
    "internal.tick_latency": {
        "label": "Tick latency",
        "category": "internal",
        "unit": "ms",
        "scale": 1000.0,
    },
    "internal.memory_rss": {
        "label": "Process memory",
        "category": "internal",
        "unit": "MiB",
        "scale": 1.0 / (1024.0 * 1024.0),
    },
    "internal.epistemic_surprise": {
        "label": "Epistemic surprise",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
    "internal.metabolic_reserve": {
        "label": "Metabolic reserve",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
    "internal.integrity": {
        "label": "Integrity",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
    "internal.metabolic_pressure": {
        "label": "Metabolic pressure",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
    "internal.repair_pressure": {
        "label": "Repair pressure",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
    "internal.waste_pressure": {
        "label": "Waste pressure",
        "category": "internal",
        "unit": "ratio",
        "scale": 1.0,
    },
}

_ALLOWED_CATEGORIES = {
    "compute",
    "memory",
    "storage",
    "network",
    "thermal",
    "power",
    "system",
    "internal",
    "unknown",
}


def _descriptor(runtime: Any, capability: Any) -> dict[str, object]:
    capability_id = str(getattr(capability, "capability_id", ""))
    known = _KNOWN.get(capability_id)
    if known is not None:
        return dict(known)

    provider_id = str(getattr(capability, "source", ""))
    for provider in tuple(getattr(runtime, "_reading_providers", ())):
        if str(getattr(provider, "provider_id", "")) != provider_id:
            continue
        describe = getattr(provider, "observer_descriptor", None)
        if callable(describe):
            payload = describe(capability_id)
            if isinstance(payload, dict):
                return dict(payload)
    kind = str(
        getattr(getattr(capability, "kind", None), "value", getattr(capability, "kind", "unknown"))
    )
    category = kind if kind in _ALLOWED_CATEGORIES else "unknown"
    label = {
        "compute": "Compute signal",
        "memory": "Memory signal",
        "storage": "Storage signal",
        "network": "Network signal",
        "thermal": "Temperature",
        "power": "Power signal",
    }.get(category, "Aggregate signal")
    return {"label": label, "category": category, "unit": "", "scale": 1.0}


def build_observer_provenance(runtime: Any, result: Any) -> list[dict[str, object]]:
    """Translate opaque signals for the human observer only.

    This function is Observatory apparatus. The returned labels never enter
    RuntimeTickResult, organism checkpoint state, cognition or learning.
    """
    manifest = getattr(getattr(result, "snapshot", None), "manifest", None)
    available = tuple(getattr(manifest, "available", ()))[:256]
    readings = {
        str(getattr(reading, "capability_id", "")): reading
        for reading in tuple(getattr(getattr(result, "snapshot", None), "readings", ()))[:256]
    }
    signal_identity = getattr(runtime, "_signal_identity", None)
    if signal_identity is None:
        return []

    rows: list[dict[str, object]] = []
    for capability in available:
        capability_id = str(getattr(capability, "capability_id", ""))
        if not capability_id:
            continue
        signal_id = signal_identity.signal_id(capability_id)
        descriptor = _descriptor(runtime, capability)
        reading = readings.get(capability_id)
        raw_value = getattr(reading, "value", None) if reading is not None else None
        scale = descriptor.get("scale", 1.0)
        try:
            value = None if raw_value is None else float(raw_value) * float(scale)
        except (TypeError, ValueError):
            value = None
        if value is not None and (not math.isfinite(value) or abs(value) > 1e15):
            value = None
        quality = (
            str(getattr(getattr(reading, "quality", None), "value", "unavailable"))
            if reading is not None
            else "unavailable"
        )
        if quality not in {"nominal", "degraded", "stale", "unavailable"}:
            quality = "unavailable"
        category = str(descriptor.get("category", "unknown"))
        if category not in _ALLOWED_CATEGORIES:
            category = "unknown"
        rows.append(
            {
                "signal_id": signal_id,
                "label": str(descriptor.get("label", "Aggregate signal"))[:64],
                "category": category,
                "scope": "internal" if category == "internal" else "external",
                "value": None if value is None else round(value, 6),
                "unit": str(descriptor.get("unit", ""))[:16],
                "quality": quality,
            }
        )
    rows.sort(key=lambda row: str(row["signal_id"]))
    return rows
