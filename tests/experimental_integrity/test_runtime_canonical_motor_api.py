from __future__ import annotations

import inspect

from symbiont.core.runtime import OrganismRuntime


def test_runtime_constructor_exposes_only_canonical_motor_dependencies() -> None:
    parameters = inspect.signature(OrganismRuntime).parameters
    assert "actuator_evidence" in parameters
    assert "competence_development" in parameters
    assert "motor_selection_threshold" in parameters
    assert "actuator_system" in parameters
    assert "actuator_proposer" not in parameters
    assert "sensorimotor_learner" not in parameters
    assert "motor_intent_selector" not in parameters
