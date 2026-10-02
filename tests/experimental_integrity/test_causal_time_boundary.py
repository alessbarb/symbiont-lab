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
_CLOCK_NAMES = {
    "time",
    "time_ns",
    "monotonic",
    "monotonic_ns",
    "perf_counter",
    "perf_counter_ns",
    "process_time",
    "now",
    "today",
    "utcnow",
}
# path relative to src/symbiont -> (exact number of clock reads, reason).
# Exact counts, not whole-file exemptions: a new read anywhere in an
# allowlisted file (e.g. perception, where the leak lived) fails the test.
DECLARED_EXCEPTIONS = {
    "host/providers/interoception.py": (1, "apparatus reading timestamp"),
    "host/providers/linux_surfaces.py": (1, "apparatus reading timestamp"),
    "host/providers/portable_surfaces.py": (1, "apparatus reading timestamp"),
    "host/providers/stdlib_readings.py": (1, "apparatus reading timestamp"),
    "host/readings.py": (2, "profiling clock -> observed_elapsed_s only"),
    "host/lifecycle.py": (1, "profiling clock -> observed_elapsed_s only"),
    "host/second_look.py": (1, "profiling clock -> observed_elapsed_s only"),
    "core/domains/epistemic.py": (1, "profiling clock -> observed_elapsed_s only"),
    "core/orchestration/governor.py": (1, "safety: consent and tick rate guard"),
    "core/host/advisory.py": (1, "safety: outward advisory rate limit"),
    "core/host/local_habitat.py": (2, "local capsule mailbox TTL and file ids"),
    "core/orchestration/runtime.py": (1, "real-host interoception tick latency"),
    "core/domains/lifecycle.py": (1, "real-host interoception tick latency"),
    "core/domains/perception.py": (1, "reading-timestamp metadata fallback"),
}


def _clock_reads(tree: ast.AST) -> int:
    """Count wall-clock reads, resolving ``import time as t`` and
    ``from time import perf_counter as pc`` style aliases."""
    modules: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"time", "datetime"}:
                    modules.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module in {"time", "datetime"}:
            for alias in node.names:
                if alias.name == "datetime":
                    modules.add(alias.asname or alias.name)
                elif alias.name in _CLOCK_NAMES:
                    names.add(alias.asname or alias.name)
    reads = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _CLOCK_NAMES:
            owner = node.value
            if isinstance(owner, ast.Name) and owner.id in modules:
                reads += 1
            elif isinstance(owner, ast.Attribute) and owner.attr == "datetime":
                reads += 1
        elif isinstance(node, ast.Name) and node.id in names and isinstance(node.ctx, ast.Load):
            reads += 1
    return reads


def test_wall_clock_reads_match_declared_exceptions_exactly() -> None:
    observed = {}
    for path in ROOT.rglob("*.py"):
        reads = _clock_reads(ast.parse(path.read_text(encoding="utf-8")))
        if reads:
            observed[path.relative_to(ROOT).as_posix()] = reads
    expected = {path: count for path, (count, _reason) in DECLARED_EXCEPTIONS.items()}
    assert observed == expected


def test_alias_detection_catches_disguised_clock_reads() -> None:
    disguised = ast.parse(
        "import time as t\nfrom time import perf_counter as pc\n"
        "from datetime import datetime as dt\nx = t.monotonic() + pc() + dt.now().hour\n"
    )
    assert _clock_reads(disguised) == 3


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
