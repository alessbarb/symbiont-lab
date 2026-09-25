from __future__ import annotations

import inspect

from symbiont.modeling.private_runtime import PrivateModelOrganismRuntime


def test_private_runtime_forwards_canonical_tick_context() -> None:
    source = inspect.getsource(PrivateModelOrganismRuntime.tick)

    assert "context: TickContext | None = None" in source
    assert "super().tick(context=context)" in source
    assert "super().tick()" not in source
