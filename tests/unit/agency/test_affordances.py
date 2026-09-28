"""ActionAffordance is a derived, authority-free projection (§34-§38, §99)."""

from __future__ import annotations

import dataclasses

import pytest

from symbiont.actuation.binding import CompetenceExecutionBindingRegistry
from symbiont.actuation.competence import CompetenceEvidence, CompetenceLibrary, MotorCompetence
from symbiont.actuation.effects import EffectMatcher, EffectSpace
from symbiont.actuation.model import ControllabilityModel, EffectPrediction
from symbiont.actuation.surface import derive_actuator_constitution
from symbiont.agency.affordance import ActionAffordance, affordance_id_for
from symbiont.agency.affordances import AffordanceResolver
from symbiont.core.domains.action import ActionDomain

SURFACE = derive_actuator_constitution(2, physical_contract="affordance-unit")


def _world():
    space = EffectSpace()
    near = space.observe({"signal.near": 0.5})
    far = space.observe({"signal.far": -0.5})
    library = CompetenceLibrary()
    bindings = CompetenceExecutionBindingRegistry()
    evidence = CompetenceEvidence(
        controller_seed_ref="seed",
        support=8,
        reproducibility=0.9,
        controllability=0.6,
        directional_consistency=0.9,
    )
    for competence_id, effect in (("competence.near", near), ("competence.far", far)):
        library.add(
            MotorCompetence(
                competence_id=competence_id,
                controller_id=f"controller.{competence_id}",
                effect_id=effect.effect_id,
                evidence=evidence,
            )
        )
        bindings.bind_from_evidence(
            competence_id=competence_id,
            surface_fingerprint=SURFACE.contract_fingerprint,
            effect_id=effect.effect_id,
            evidence_refs=(f"causal.{competence_id}",),
            reliability=0.8,
            controllability=0.7,
            tick=3,
        )
    return space, near, far, library, bindings


def _predict(library):
    def predict(*, competence_id: str, context_id: str | None) -> EffectPrediction | None:
        competence = library.get(competence_id)
        if competence is None or competence.effect_id is None:
            return None
        return EffectPrediction(
            prediction_id=f"prediction.{competence_id}",
            competence_id=competence_id,
            context_id=context_id,
            effect_id=competence.effect_id,
            confidence=0.6,
            support=4,
        )

    return predict


def _resolver(space, library, bindings, *, surface=SURFACE.contract_fingerprint, embodiment="e1"):
    return AffordanceResolver(
        competences=library,
        predict=_predict(library),
        controllability_model=ControllabilityModel(),
        execution_bindings=bindings,
        executable=lambda competence: bindings.is_executable(
            competence, surface_fingerprint=surface
        ),
        effect_space=space,
        effect_matcher=EffectMatcher(),
        surface_fingerprint=surface,
        embodiment_id=embodiment,
    )


def test_affordance_is_derived_not_checkpointed():
    space, _near, _far, library, bindings = _world()
    resolver = _resolver(space, library, bindings)
    first = resolver.current(context_ref="context.a", embodiment_id="e1")
    second = resolver.current(context_ref="context.a", embodiment_id="e1")
    assert first == second and first is not second
    assert not hasattr(resolver, "checkpoint") and not hasattr(ActionAffordance, "checkpoint")
    domain = ActionDomain(organism_id="organism.aff", enabled=True, surface=SURFACE)
    assert "affordance" not in repr(domain.checkpoint_v2()).lower()


def test_for_effect_returns_executable_competences():
    space, near, _far, library, bindings = _world()
    affordances = _resolver(space, library, bindings).for_effect(
        effect_id=near.effect_id, context_ref=None, embodiment_id="e1"
    )
    assert [item.competence_id for item in affordances] == ["competence.near"]
    assert affordances[0].anticipated_effect_id == near.effect_id


def test_for_effect_excludes_unbound_competence():
    space, near, _far, library, bindings = _world()
    other_surface = _resolver(space, library, bindings, surface="surface.other")
    assert (
        other_surface.for_effect(effect_id=near.effect_id, context_ref=None, embodiment_id="e1")
        == ()
    )
    immature = CompetenceLibrary()
    immature.add(
        MotorCompetence(
            competence_id="competence.near",
            controller_id="controller.near",
            effect_id=near.effect_id,
            evidence=CompetenceEvidence(controller_seed_ref="seed", support=1),
        )
    )
    assert (
        _resolver(space, immature, bindings).for_effect(
            effect_id=near.effect_id, context_ref=None, embodiment_id="e1"
        )
        == ()
    )


def test_current_returns_state_applicable_affordances():
    space, near, far, library, bindings = _world()
    resolver = _resolver(space, library, bindings)
    current = resolver.current(context_ref="context.a", embodiment_id="e1")
    assert {(item.competence_id, item.anticipated_effect_id) for item in current} == {
        ("competence.near", near.effect_id),
        ("competence.far", far.effect_id),
    }
    assert all(item.context_ref == "context.a" for item in current)
    # Another embodiment is not the current situation.
    assert resolver.current(context_ref="context.a", embodiment_id="e2") == ()


def test_affordance_does_not_authorize_action():
    space, _near, _far, library, bindings = _world()
    fields = {field.name for field in dataclasses.fields(ActionAffordance)}
    assert not fields & {"commitment_id", "proposal_id", "command_id", "controller_id"}
    resolver = _resolver(space, library, bindings)
    assert not any(
        hasattr(resolver, name) for name in ("commit", "issue_command", "propose", "arbitrate")
    )
    before = bindings.checkpoint()
    resolver.current(context_ref=None, embodiment_id="e1")
    assert bindings.checkpoint() == before


def test_affordance_contains_no_actuator_semantics():
    space, _near, _far, library, bindings = _world()
    for affordance in _resolver(space, library, bindings).current(
        context_ref=None, embodiment_id="e1"
    ):
        rendered = repr(affordance)
        assert all(actuator_id not in rendered for actuator_id in SURFACE.actuator_ids)
    with pytest.raises(ValueError):
        ActionAffordance(
            affordance_id=affordance_id_for(
                competence_id="competence.x",
                anticipated_effect_id="effect.x",
                context_ref=None,
                embodiment_id=None,
            ),
            competence_id="competence.x",
            anticipated_effect_id="effect.x",
            context_ref=None,
            embodiment_id=None,
            prediction_confidence=0.5,
            controllability=0.5,
            executability_confidence=0.5,
            prediction_ref=None,
            evidence_refs=(SURFACE.actuator_ids[0],),
        )
