"""Versioned Physics3D telemetry formats, readers, and tools."""

from lab.physics3d.telemetry.reader import (
    TelemetryReaderProtocol,
    detect_telemetry_run,
    open_telemetry,
)
from lab.physics3d.telemetry.v41 import (
    AsyncTelemetryV41Writer,
    TelemetryV41Reader,
    TelemetryV41Writer,
    verify_v41_run,
)

__all__ = [
    "AsyncTelemetryV41Writer",
    "TelemetryReaderProtocol",
    "TelemetryV41Reader",
    "TelemetryV41Writer",
    "detect_telemetry_run",
    "open_telemetry",
    "verify_v41_run",
]
