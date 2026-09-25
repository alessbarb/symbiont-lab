from __future__ import annotations

from pathlib import Path

import pytest
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.domains.context import TickContext


def test_tick_context_rejects_wrong_symbiont_identity() -> None:
    runtime = OrganismRuntime(organism_id="symbiont.context.test")
    with pytest.raises(ValueError, match="another Symbiont"):
        runtime.tick(
            context=TickContext(
                symbiont_id="symbiont.other",
                symbiont_tick=1,
            )
        )


def test_physics3d_passes_both_time_domains_explicitly() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "src" / "symbiont_lab" / "physics3d" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "symbiont_tick=self.tick_count + 1" in source
    assert "embodiment_tick=self.embodiment_tick" in source
    assert "body_id=self.body_identity" in source


def test_tick_without_explicit_context_uses_next_symbiont_tick() -> None:
    runtime = OrganismRuntime(organism_id="symbiont.context.default")
    result = runtime.tick()
    assert result.tick == 1
    assert runtime.tick_count == 1
