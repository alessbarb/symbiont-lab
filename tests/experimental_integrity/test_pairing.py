from __future__ import annotations

import pytest
from symbiont_lab.studies.common.pairing import (
    assert_disjoint_seeds,
    assert_paired_seeds,
    assert_unique_seeds,
)


def test_unique_seeds_enforcement():
    assert_unique_seeds([1, 2, 3])
    with pytest.raises(ValueError, match="Duplicate seed"):
        assert_unique_seeds([1, 2, 2, 3])


def test_disjoint_seeds_enforcement():
    assert_disjoint_seeds([1, 2], [3, 4])
    with pytest.raises(ValueError, match="Colliding seeds"):
        assert_disjoint_seeds([1, 2], [2, 3])


def test_paired_seeds_enforcement():
    assert_paired_seeds([10, 20, 30], [10, 20, 30])
    with pytest.raises(ValueError, match="Seed pairing mismatch"):
        assert_paired_seeds([10, 20], [10, 30])
