from __future__ import annotations

from symbiont.actuation.competence import (
    CompetenceEvidence,
    MotorCompetence,
)
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.core.domains.action import ActionDomain
from symbiont.core.embodiment.body_schema import BodySchemaEngine


def test_schema3_roundtrip_preserves_execution_binding_authority() -> None:
    surface = derive_actuator_constitution(1, physical_contract="body.roundtrip")
    domain = ActionDomain(
        organism_id="organism.roundtrip",
        enabled=True,
        surface=surface,
        embodiment_id="embodiment.roundtrip",
    )
    competence = MotorCompetence(
        competence_id="competence.roundtrip",
        controller_id="controller.roundtrip",
        effect_id="effect.roundtrip",
        evidence=CompetenceEvidence(
            controller_seed_ref="seed.roundtrip",
            effect_evidence_refs=("evidence.roundtrip",),
            controllability_evidence_refs=("evidence.roundtrip",),
            support=4,
            failures=0,
            reproducibility=0.9,
            controllability=0.9,
            directional_consistency=0.9,
        ),
    )
    domain.competence_library.add(competence)
    domain.execution_bindings.bind_from_evidence(
        competence_id=competence.competence_id,
        surface_fingerprint=surface.contract_fingerprint,
        effect_id="effect.roundtrip",
        evidence_refs=("evidence.roundtrip",),
        reliability=0.9,
        controllability=0.9,
        tick=12,
    )
    payload = domain.checkpoint_v2()

    restored = ActionDomain(
        organism_id="organism.roundtrip",
        enabled=True,
        surface=surface,
    )
    restored.restore_v2(payload, body_schema=BodySchemaEngine())
    restored_competence = restored.competence_library.get("competence.roundtrip")
    assert restored_competence is not None
    assert restored.embodiment_id == "embodiment.roundtrip"
    assert restored.execution_bindings.is_executable(
        restored_competence,
        surface_fingerprint=surface.contract_fingerprint,
    )
