"""Defensive ingestion bounds and operational defaults for Observatory.

Observatory is a passive, read-only scientific viewing apparatus.
It understands only its own contracts and ingestion schemas, and does NOT
depend on or import symbiont.core or organism internal limits.
"""

from __future__ import annotations

# Operational server & streaming defaults
DEFAULT_OBSERVATORY_DIR: str = "~/.local/state/symbiont/observatory"
DEFAULT_SERVER_HOST: str = "127.0.0.1"
DEFAULT_SERVER_PORT: int = 8899
DEFAULT_SSE_POLL_SECONDS: float = 1.0
DEFAULT_HEARTBEAT_INTERVAL_SECONDS: float = 15.0
STALE_HEARTBEAT_FACTOR: int = 3

# Defensive ingestion limits (protecting the visualizer from malformed/runaway inputs)
INGESTION_MAX_TICKS: int = 10_000
INGESTION_MAX_SENSORY_PARTS: int = 256
INGESTION_MAX_COGNITIVE_REGIONS: int = 32
INGESTION_MAX_BODY_PARTS: int = INGESTION_MAX_SENSORY_PARTS + INGESTION_MAX_COGNITIVE_REGIONS
INGESTION_MAX_BODY_DEPENDENCIES: int = 256

__all__ = [
    "DEFAULT_OBSERVATORY_DIR",
    "DEFAULT_SERVER_HOST",
    "DEFAULT_SERVER_PORT",
    "DEFAULT_SSE_POLL_SECONDS",
    "DEFAULT_HEARTBEAT_INTERVAL_SECONDS",
    "STALE_HEARTBEAT_FACTOR",
    "INGESTION_MAX_TICKS",
    "INGESTION_MAX_SENSORY_PARTS",
    "INGESTION_MAX_COGNITIVE_REGIONS",
    "INGESTION_MAX_BODY_PARTS",
    "INGESTION_MAX_BODY_DEPENDENCIES",
]
