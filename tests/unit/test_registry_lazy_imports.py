from __future__ import annotations

import importlib
import sys


def test_registry_does_not_eager_import_visual_protocol_modules() -> None:
    sys.modules.pop("lab.experiments.registry", None)
    sys.modules.pop("lab.studies.learning.visual_acquisition", None)
    sys.modules.pop("lab.studies.learning.visual_predictor_audit", None)

    registry = importlib.import_module("lab.experiments.registry")

    assert "learning.visual-acquisition-v1" in registry.PROTOCOLS
    assert "learning.visual-predictor-audit" in registry.PROTOCOLS
    assert "lab.studies.learning.visual_acquisition" not in sys.modules
    assert "lab.studies.learning.visual_predictor_audit" not in sys.modules
