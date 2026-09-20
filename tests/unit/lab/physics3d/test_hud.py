from pathlib import Path

import pytest

from symbiont_lab.physics3d.hud import Physics3DHud


def test_hud_ranks_opaque_outputs_without_anatomical_semantics():
    strongest = Physics3DHud._strongest_outputs(
        {"out.3": 0.2, "out.1": 0.9, "out.2": 0.5, "out.0": 0.1},
        limit=3,
    )
    assert strongest == [("out.1", 0.9), ("out.2", 0.5), ("out.3", 0.2)]


def test_hud_shortens_long_paths_without_changing_suffix():
    path = Path("/very/long/path/to/a/portable/subject.symbiont.json")
    shortened = Physics3DHud._safe_text(path, max_len=24)

    assert len(shortened) <= 24
    assert shortened.startswith("...")
    assert shortened.endswith("symbiont.json")
