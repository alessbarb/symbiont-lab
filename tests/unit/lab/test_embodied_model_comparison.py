from __future__ import annotations

import pytest

from symbiont_lab.studies.learning.embodied_model_comparison import run_embodied_model_comparison


def test_model_comparison_rejects_empty_seed_set():
    with pytest.raises(ValueError, match="seeds"):
        run_embodied_model_comparison((), ticks=64)
