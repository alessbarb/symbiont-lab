from __future__ import annotations

from pathlib import Path


def test_runtime_delegates_death_release_and_journal() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    assert "self._lifecycle_domain.release_on_death(" in runtime
    assert "self._lifecycle_domain.record_journal(" in runtime
    assert "self._habitat.release(" not in runtime
    assert "journal_entry = {" not in runtime


def test_body_age_advances_only_through_physiology_domain() -> None:
    root = Path(__file__).resolve().parents[2]
    runtime = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    physiology = (
        root / "src" / "symbiont" / "core" / "domains" / "physiology.py"
    ).read_text(encoding="utf-8")
    assert "self._living_body_state.advance_age()" not in runtime
    assert "living_body_state.advance_age()" in physiology
