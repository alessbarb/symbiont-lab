from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from governance.classify import ChangeClass, assess


def test_private_model_promotion_is_scientific_by_semantics() -> None:
    result = assess(
        ROOT,
        "HEAD",
        ["src/symbiont_lab/physics3d/private_model_training.py"],
        "+ activate_private_model(... promotion_authorized=True)",
    )
    assert result.classification == ChangeClass.SCIENTIFIC
    assert "promotion-eligible" in result.equivalence_scenarios


def test_observatory_presentation_is_ordinary() -> None:
    result = assess(ROOT, "HEAD", ["observatory/ui/view.js"], "+ renderLabel()")
    assert result.classification == ChangeClass.ORDINARY
