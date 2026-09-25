from __future__ import annotations

from pathlib import Path


def test_runtime_tick_is_domain_orchestration_not_algorithm_ownership() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")

    required_domain_calls = (
        "self._physiology_domain.preflight(",
        "self._perception_domain.step(",
        "self._action_domain.prepare_cognition(",
        "self._cognition_domain.step(",
        "self._memory_domain.observe(",
        "self._action_domain.step(",
        "self._epistemic_domain.investigate(",
        "self._embodiment_domain.observe(",
        "self._physiology_domain.advance(",
        "self._regulation_domain.resolve_homeostatic_action_credit(",
        "self._lifecycle_domain.release_on_death(",
        "self._lifecycle_domain.events(",
        "self._development_domain.update_gene_expression(",
        "self._lifecycle_domain.record_journal(",
        "self._development_domain.decay_epigenetic_priors(",
    )
    for call in required_domain_calls:
        assert call in source

    forbidden_runtime_algorithms = (
        "MotorIntentSelector(",
        "SensorimotorLearner(",
        "ActuatorProposer(",
        "MotorCommand.from_mapping(",
        "ActuatorSystem(",
        "self._cognitive_bridge.tick(",
        "self._sensory_system.transduce(",
        "self._memory_consolidator.observe(",
        "self._body_schema.observe_cognition(",
        "self._body_schema.observe_sensory_phenotype(",
        "SecondLookSession(",
        "RegulatorySignals(",
    )
    for call in forbidden_runtime_algorithms:
        assert call not in source


def test_runtime_surfaces_real_action_domain_execution_result() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    tick = source[
        source.index("    def tick("):
        source.index("\n    def run(", source.index("    def tick("))
    ]
    assert "action_result = self._action_domain.step(" in tick
    assert "action_result: ActionExecutionResult | None = None" not in tick


def test_runtime_does_not_inspect_cognition_graph_or_action_evidence_in_tick() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src" / "symbiont" / "core" / "orchestration" / "runtime.py"
    ).read_text(encoding="utf-8")
    tick = source[source.index("    def tick("):source.index("\n    def run(", source.index("    def tick("))]
    assert "_cognitive_bridge.graph" not in tick
    assert "_action_domain.actuator_evidence" not in tick
    assert "_action_domain.competence_development" not in tick
