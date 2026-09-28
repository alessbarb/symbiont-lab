"""ADR-0042: host clocks and CPU speed are never an implicit causal authority.

Every wall-clock read inside the organism package must be in the declared
exception list (apparatus timestamps, profiling, safety/rate guards, local
mailbox IO, real-host interoception). The profiling field
``observed_elapsed_s`` may be produced but never read by the organism.
"""

from __future__ import annotations

import ast
from pathlib import Path

import symbiont

ROOT = Path(symbiont.__file__).parent
_CLOCK_ATTRS = {
    ("time", "time"),
    ("time", "time_ns"),
    ("time", "monotonic"),
    ("time", "monotonic_ns"),
    ("time", "perf_counter"),
    ("time", "perf_counter_ns"),
    ("datetime", "now"),
    ("datetime", "today"),
    ("datetime", "utcnow"),
}
# path relative to src/symbiont -> reason (ADR-0042 §5)
DECLARED_EXCEPTIONS = {
    "host/readings.py": "profiling clock -> observed_elapsed_s only",
    "host/lifecycle.py": "profiling clock -> observed_elapsed_s only",
    "host/second_look.py": "profiling clock -> observed_elapsed_s only",
    "core/domains/epistemic.py": "profiling clock -> observed_elapsed_s only",
    "core/orchestration/governor.py": "safety: consent and tick rate guard",
    "core/host/advisory.py": "safety: outward advisory rate limit",
    "core/host/local_habitat.py": "local capsule mailbox TTL and file ids",
    "core/orchestration/runtime.py": "real-host interoception tick latency",
    "core/domains/lifecycle.py": "real-host interoception tick latency",
    "core/domains/perception.py": "reading-timestamp metadata fallback",
}


def _clock_reads(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if (node.value.id, node.attr) in _CLOCK_ATTRS:
                lines.append(node.lineno)
        if isinstance(node, ast.ImportFrom) and node.module in {"time", "datetime"}:
            lines.append(node.lineno)
    return lines


def test_wall_clock_reads_are_confined_to_declared_exceptions() -> None:
    offenders = {}
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("host/providers/") or relative in DECLARED_EXCEPTIONS:
            continue
        lines = _clock_reads(ast.parse(path.read_text(encoding="utf-8")))
        if lines:
            offenders[relative] = lines
    assert offenders == {}


def test_declared_exceptions_still_exist() -> None:
    # A stale allowlist silently widens the boundary.
    for relative in DECLARED_EXCEPTIONS:
        assert (ROOT / relative).is_file(), relative


def test_observed_elapsed_time_is_never_read_by_the_organism() -> None:
    readers = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        if relative == "host/readings.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "observed_elapsed_s":
                readers.append(f"{relative}:{node.lineno}")
    assert readers == []


def test_rhythm_context_comes_from_causal_tick() -> None:
    from symbiont.core.domains.context import TickContext
    from symbiont.host.rhythms import CYCLE_PERIOD_TICKS, CyclePhase

    phases = {
        TickContext(symbiont_id="s", symbiont_tick=tick).macro_phase
        for tick in range(0, CYCLE_PERIOD_TICKS, CYCLE_PERIOD_TICKS // 8)
    }
    assert phases == set(CyclePhase)
    assert (
        TickContext(symbiont_id="s", symbiont_tick=7).macro_phase
        == TickContext(symbiont_id="other", symbiont_tick=7 + CYCLE_PERIOD_TICKS).macro_phase
    )
