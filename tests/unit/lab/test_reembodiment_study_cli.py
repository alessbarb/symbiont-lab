from __future__ import annotations

import pytest

from symbiont_lab.studies.embodiment.reembodiment_cli import _parse_sequence


def test_reembodiment_cli_accepts_short_body_aliases() -> None:
    assert _parse_sequence("humanoid,crawler,humanoid") == (
        "anthropomorphic-v6",
        "crawler-v1",
        "anthropomorphic-v6",
    )


def test_reembodiment_cli_requires_a_b_a_contract_shape() -> None:
    with pytest.raises(ValueError):
        _parse_sequence("humanoid,crawler,asymmetric")
    with pytest.raises(ValueError):
        _parse_sequence("humanoid,humanoid,humanoid")
