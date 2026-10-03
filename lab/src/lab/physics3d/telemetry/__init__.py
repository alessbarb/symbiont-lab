"""Versioned Physics3D telemetry formats, readers, and tools."""

from lab.physics3d.telemetry.reader import (
    TelemetryReaderProtocol,
    detect_telemetry_run,
    open_telemetry,
)
from lab.physics3d.telemetry.v3 import TelemetryV3Writer, verify_v3_run
from lab.physics3d.telemetry.v4 import (
    AsyncTelemetryV4Writer,
    TelemetryV4Reader,
    TelemetryV4Writer,
    verify_v4_run,
)
from lab.physics3d.telemetry.v41 import (
    AsyncTelemetryV41Writer,
    TelemetryV41Reader,
    TelemetryV41Writer,
    verify_v41_run,
)

__all__ = [
    "AsyncTelemetryV4Writer",
    "AsyncTelemetryV41Writer",
    "TelemetryReaderProtocol",
    "TelemetryV3Writer",
    "TelemetryV4Reader",
    "TelemetryV4Writer",
    "TelemetryV41Reader",
    "TelemetryV41Writer",
    "detect_telemetry_run",
    "open_telemetry",
    "verify_v3_run",
    "verify_v4_run",
    "verify_v41_run",
]
