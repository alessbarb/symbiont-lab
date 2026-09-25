from __future__ import annotations

from pathlib import Path


def test_tick_scoped_domains_use_typed_tick_context() -> None:
    root = Path(__file__).resolve().parents[2]
    domain_names = (
        "perception.py",
        "cognition.py",
        "memory.py",
        "epistemic.py",
        "embodiment.py",
        "action.py",
    )
    for name in domain_names:
        source = (root / "src" / "symbiont" / "core" / "domains" / name).read_text(encoding="utf-8")
        assert "TickContext" in source

    runtime = (root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "context=context" in runtime
