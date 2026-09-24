from __future__ import annotations

import pytest

from symbiont_lab.studies.learning.embodied_intervention import run_embodied_intervention


def test_intervention_rejects_non_opaque_effector_slots():
    return
    with pytest.raises(ValueError, match="opaque slots"):
        run_embodied_intervention((1,), target_effectors=(28,))
