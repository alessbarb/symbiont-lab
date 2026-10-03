"""Body ownership can be learned before motor competence (§26-§27, §97)."""

from __future__ import annotations

from symbiont.core.embodiment.body_schema import BodySchemaEngine

from ..actuation.acquisition_support import A, acquire_agentic_dimension, fresh_acquisition


def test_body_schema_can_learn_before_competence():
    acquisition = fresh_acquisition()
    body_schema = BodySchemaEngine()
    acquire_agentic_dimension(
        acquisition,
        channels={A: 0.5},
        changes={"signal.a": 0.4},
        body_schema=body_schema,
    )
    assert body_schema.sensorimotor_dependency_evidence_count > 0
    assert "signal.a" in body_schema.agentic_feature_refs
    assert "signal.a" in acquisition.self_caused_features(min_confidence=0.35)


def test_body_boundary_agency_excludes_estimates_from_prior_embodiment():
    acquisition = fresh_acquisition()
    end_tick = acquire_agentic_dimension(
        acquisition,
        channels={A: 0.5},
        changes={"signal.a": 0.4},
    )

    assert "signal.a" in acquisition.self_caused_features(
        min_confidence=0.35, updated_after_tick=0
    )
    assert not acquisition.self_caused_features(
        min_confidence=0.35, updated_after_tick=end_tick
    )


def test_body_schema_requires_agentic_or_sensorimotor_evidence():
    body_schema = BodySchemaEngine()
    body_schema.observe_agentic_sensorimotor_evidence(
        causal_source_ref="intervention.signature.x",
        effect_id="effect.x",
        feature_refs=("signal.a",),
        controllability_confidence=0.0,
        agency_confidence=0.0,
        tick=3,
    )
    assert body_schema.sensorimotor_dependency_evidence_count == 0
    assert body_schema.agentic_feature_refs == ()


def test_body_schema_does_not_treat_command_echo_as_body_ownership():
    body_schema = BodySchemaEngine()
    body_schema.observe_agentic_sensorimotor_evidence(
        causal_source_ref="intervention.signature.x",
        effect_id="effect.x",
        feature_refs=("channel.0123456789abcdef",),
        controllability_confidence=1.0,
        agency_confidence=1.0,
        tick=3,
    )
    assert body_schema.sensorimotor_dependency_evidence_count == 0
    assert body_schema.agentic_feature_refs == ()
