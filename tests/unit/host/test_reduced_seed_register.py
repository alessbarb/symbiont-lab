"""The reduced seed's transplant semantics are a declared contract.

Two longitudinal semantics exist: canonical re-embodiment keeps
embodiment-specific inference as knowledge, the reduced clean-embodiment seed
restarts it. These tests pin the reduced path attribute by attribute and pin
exactly where it differs from the canonical register, so neither path can drift
towards or away from the other unnoticed.
"""

from __future__ import annotations

from copy import deepcopy

from symbiont.actuation.competence import CompetenceEvidence, MotorCompetence
from symbiont.core.embodiment.body import create_standard_body
from symbiont.core.orchestration.individual import Individual, create_individual
from symbiont.core.orchestration.symbiont import Symbiont
from symbiont.host.continuity import (
    REDUCED_SEED_REGISTER,
    REGISTER,
    Reembodiment,
    Transplant,
)

CANONICAL = {entry.attribute: entry for entry in REGISTER}
REDUCED = {entry.attribute: entry for entry in REDUCED_SEED_REGISTER}
# Canonical re-embodiment keeps this state as knowledge (with or without authority).
KEPT_AS_KNOWLEDGE = {Reembodiment.PRESERVED, Reembodiment.INVALIDATED}
DISCARDS = {Transplant.RESET, Transplant.DETACHED}


def _developed() -> Individual:
    individual = create_individual("sym.seed", "body.a", num_receptors=3, num_effectors=3)
    for _ in range(120):
        individual.step()
    individual.symbiont.competence_library.add(
        MotorCompetence(
            competence_id="competence.body.a",
            controller_id="controller.body.a",
            effect_id="effect.body.a",
            evidence=CompetenceEvidence(
                controller_seed_ref="controller.body.a",
                support=8,
                failures=0,
                reproducibility=0.9,
                controllability=0.8,
                directional_consistency=0.9,
            ),
            controller_strategy_ref="controller.body.a",
        )
    )
    return individual


def test_every_reduced_seed_attribute_is_classified() -> None:
    names = [entry.attribute for entry in REDUCED_SEED_REGISTER]
    assert sorted(names) == sorted(set(names))
    assert set(names) == set(vars(Symbiont("sym.probe")))
    assert set(names) == set(vars(_developed().symbiont))


def test_canonical_counterparts_exist() -> None:
    for entry in REDUCED_SEED_REGISTER:
        assert entry.canonical is None or entry.canonical in CANONICAL, entry.attribute


def test_declared_divergences_are_exactly_the_real_ones() -> None:
    real = {
        entry.attribute
        for entry in REDUCED_SEED_REGISTER
        if entry.canonical is not None
        and entry.transplant in DISCARDS
        and CANONICAL[entry.canonical].reembodiment in KEPT_AS_KNOWLEDGE
    }
    declared = {entry.attribute for entry in REDUCED_SEED_REGISTER if entry.diverges}

    assert declared == real
    assert declared == {
        "action_domain",
        "body_schema",
        "competence_library",
        "sensorimotor_model",
    }


def test_transplant_treats_each_attribute_as_declared() -> None:
    individual = _developed()
    seed = individual.symbiont
    assert seed.sensorimotor_model.relation_count > 0
    before = dict(vars(seed))
    plain = (int, float, str, tuple, set, dict, type(None))
    values = {name: deepcopy(value) for name, value in before.items() if isinstance(value, plain)}
    rng_state = seed._rng.getstate()

    individual.transplant_to(create_standard_body("body.b", num_receptors=3, num_effectors=3))

    for name, entry in REDUCED.items():
        after = getattr(seed, name)
        if entry.transplant is Transplant.PRESERVED:
            if name in values:
                assert after == values[name], name
            else:
                assert after is before[name], name
        elif entry.transplant is Transplant.RESET:
            assert after is None or after is not before[name], name
        elif entry.transplant is Transplant.DETACHED:
            assert after is before[name], name
    assert seed._rng.getstate() == rng_state


def test_reset_inference_is_naive_and_competences_lose_their_grounding() -> None:
    individual = _developed()
    seed = individual.symbiont
    assert seed.causal_evidence.evidence
    assert [item.effect_id for item in seed.competence_library.items] == ["effect.body.a"]

    individual.transplant_to(create_standard_body("body.b", num_receptors=3, num_effectors=3))

    assert seed.sensorimotor_model.relation_count == 0
    assert seed.causal_evidence.evidence == ()
    assert seed.agency_model.estimates == ()
    assert seed.body_schema.boundary_confidence == 0.0
    assert seed.action_domain.competence_library is seed.competence_library
    assert [item.competence_id for item in seed.competence_library.items] == ["competence.body.a"]
    assert [item.effect_id for item in seed.competence_library.items] == [None]
    assert seed.current_output_channels == set(individual.session.output_bindings)
