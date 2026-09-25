from __future__ import annotations

import ast
from pathlib import Path

from symbiont.actuation.binding import CompetenceExecutionBindingRegistry
from symbiont.actuation.competence import CompetenceEvidence, MotorCompetence
from symbiont.actuation.model import AgencyModel, CompetenceEffectModel
from symbiont.core.embodiment.body_schema import BodySchemaEngine
from symbiont.core.embodiment.dynamics import SensorimotorDynamicsModel
from symbiont.core.symbiont import Symbiont


def test_production_symbiont_uses_only_canonical_embodiment_models() -> None:
    sym = Symbiont("canonical-embodiment-test")
    assert isinstance(sym.body_schema, BodySchemaEngine)
    assert isinstance(sym.sensorimotor_model, SensorimotorDynamicsModel)
    assert isinstance(sym.competence_effect_model, CompetenceEffectModel)
    assert isinstance(sym.agency_model, AgencyModel)


def test_motor_competence_has_no_execution_surface_authority() -> None:
    competence = MotorCompetence(
        competence_id="competence.test",
        controller_id="controller.test",
        effect_id="effect.test",
        evidence=CompetenceEvidence(
            controller_seed_ref="seed.test",
            support=8,
            reproducibility=0.9,
            controllability=0.8,
            directional_consistency=0.9,
        ),
    )
    assert not hasattr(competence, "surface_binding")
    assert not hasattr(competence, "executable")

    bindings = CompetenceExecutionBindingRegistry()
    assert not bindings.is_executable(
        competence,
        surface_fingerprint="surface.a",
    )
    bindings.bind_from_evidence(
        competence_id=competence.competence_id,
        surface_fingerprint="surface.a",
        effect_id="effect.test",
        evidence_refs=("causal.test",),
        reliability=0.9,
        controllability=0.8,
        tick=1,
    )
    assert bindings.is_executable(
        competence,
        surface_fingerprint="surface.a",
    )
    assert not bindings.is_executable(
        competence,
        surface_fingerprint="surface.b",
    )


def test_retired_agency_stack_is_not_imported_by_production_symbiont() -> None:
    root = Path(__file__).resolve().parents[3]
    production = (
        root
        / "src"
        / "symbiont"
        / "core"
        / "orchestration"
        / "symbiont.py"
    )
    tree = ast.parse(production.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported_modules.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
    assert not any(
        module.endswith("embodiment.agency")
        for module in imported_modules
    )


def test_core_public_api_does_not_export_retired_body_schema() -> None:
    import symbiont.core as core

    assert core.AgencyModel is AgencyModel
    assert core.BodySchemaEngine is BodySchemaEngine
    assert core.SensorimotorDynamicsModel is SensorimotorDynamicsModel
    assert not hasattr(core, "InferredBodySchema")
    assert not hasattr(core, "PerceptualStructure")
