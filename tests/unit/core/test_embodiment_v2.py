from __future__ import annotations

from symbiont.actuation.binding import CompetenceExecutionBindingRegistry
from symbiont.actuation.evidence import CausalEvidenceLedger
from symbiont.actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from symbiont.actuation.surface import ActuatorSurface
from symbiont.core.embodiment import (
    BodySpecificMemory,
    EmbodimentAdaptation,
    EmbodimentArchive,
    EmbodimentContract,
    EmbodimentEndReason,
    EmbodimentEpisode,
    EmbodimentState,
    EvidenceProvenance,
    PerceptualSurface,
    SensorimotorDynamicsModel,
    TimingContract,
    archive_episode_checkpoint,
    select_prior,
)
from symbiont.core.embodiment.body_schema import BodySchemaEngine


def _contract(*, percepts: int = 3, actuators: int = 2) -> EmbodimentContract:
    return EmbodimentContract(
        perceptual_surface=PerceptualSurface.from_count(percepts),
        actuator_surface=ActuatorSurface.from_count(actuators),
        timing=TimingContract(tick_hz=24.0),
    )


def test_episode_has_identity_independent_from_body_epoch_and_contract() -> None:
    episode = EmbodimentEpisode.begin(
        symbiont_id="symbiont.a",
        body_id="body.a",
        epoch=7,
        start_symbiont_tick=100,
        contract=_contract(),
    )
    assert episode.embodiment_id.startswith("embodiment.")
    assert episode.embodiment_id not in {"body.a", "7"}
    assert episode.epoch == 7
    assert episode.embodiment_tick == 0


def test_suspend_does_not_end_episode_or_advance_embodiment_time() -> None:
    episode = EmbodimentEpisode.begin(
        symbiont_id="symbiont.a",
        body_id="body.a",
        epoch=1,
        start_symbiont_tick=10,
        contract=_contract(),
    )
    assert episode.advance() == 1
    episode.suspend()
    assert episode.advance() == 1
    assert episode.state is EmbodimentState.SUSPENDED
    episode.resume()
    assert episode.advance() == 2
    assert episode.embodiment_id


def test_contract_change_does_not_imply_new_body_or_episode() -> None:
    first = _contract(percepts=3)
    second = _contract(percepts=4)
    episode = EmbodimentEpisode.begin(
        symbiont_id="symbiont.a",
        body_id="body.a",
        epoch=1,
        start_symbiont_tick=0,
        contract=first,
    )
    episode.advance()
    old_id = episode.embodiment_id
    episode.transition_contract(second, reason="sensor_surface_changed")
    assert episode.embodiment_id == old_id
    assert episode.body_id == "body.a"
    assert len(episode.contract_history) == 1
    assert episode.contract.contract_fingerprint == second.contract_fingerprint


def test_restore_reattaches_canonical_inference_instances() -> None:
    contract = _contract()
    original = EmbodimentEpisode.begin(
        symbiont_id="symbiont.a",
        body_id="body.a",
        epoch=2,
        start_symbiont_tick=20,
        contract=contract,
    )
    original.advance()
    payload = original.checkpoint(current_tick=21)

    schema = BodySchemaEngine()
    ledger = CausalEvidenceLedger()
    effects = CompetenceEffectModel()
    control = ControllabilityModel()
    agency = AgencyModel()
    bindings = CompetenceExecutionBindingRegistry()
    restored = EmbodimentEpisode.restore(
        payload,
        contract=contract,
        body_schema=schema,
        causal_evidence=ledger,
        effect_model=effects,
        controllability_model=control,
        agency_model=agency,
        execution_bindings=bindings,
        current_tick=21,
    )
    assert restored.body_schema is schema
    assert restored.causal_evidence is ledger
    assert restored.effect_model is effects
    assert restored.controllability_model is control
    assert restored.agency_model is agency
    assert restored.execution_bindings is bindings
    assert restored.embodiment_id == original.embodiment_id
    assert restored.body_id == original.body_id
    assert restored.embodiment_tick == 1


def test_imagined_dynamics_never_updates_factual_model() -> None:
    model = SensorimotorDynamicsModel()
    model.predict({"actuator.a": 1.0}, ["percept.a"])
    model.observe(
        {"percept.a": 0.8},
        tick=1,
        provenance=EvidenceProvenance.IMAGINED,
    )
    assert model.relation_count == 0
    assert model.mean_prediction_error == 0.0

    model.predict({"actuator.a": 1.0}, ["percept.a"])
    model.observe(
        {"percept.a": 0.8},
        tick=2,
        provenance=EvidenceProvenance.EXPERIENCED,
    )
    assert model.relation_count == 1
    assert model.mean_prediction_error > 0.0


def test_body_schema_boundary_requires_explicit_somatic_evidence() -> None:
    schema = BodySchemaEngine(id_salt="1" * 32)
    schema.observe_agency_boundary(
        observed_channels={"opaque.1", "opaque.2", "opaque.external"},
        self_caused_channels={"opaque.1"},
        somatic_correlated_channels={"opaque.2"},
        prediction_error=0.1,
    )
    assert schema.self_caused_channels == ("opaque.1",)
    assert schema.somatic_correlated_channels == ("opaque.2",)
    assert schema.external_channels == ("opaque.external",)
    assert schema.boundary_confidence > 0.0


def test_adaptation_is_evidence_driven_not_fixed_tick_completion() -> None:
    adaptation = EmbodimentAdaptation()
    for tick in range(100):
        adaptation.observe(
            tick=tick,
            prediction_error=0.9,
            schema_confidence=0.1,
            causal_confidence=0.0,
            controllability_confidence=0.0,
        )
    assert not adaptation.snapshot().converged

    for tick in range(100, 180):
        adaptation.observe(
            tick=tick,
            prediction_error=0.01,
            schema_confidence=0.95,
            causal_confidence=0.9,
            controllability_confidence=0.8,
        )
    assert adaptation.snapshot().converged
    assert adaptation.recovery_tick is not None


def test_archive_distinguishes_same_body_from_same_contract() -> None:
    archive = EmbodimentArchive()
    contract = _contract()
    archive.remember_body(
        BodySpecificMemory(
            body_id="body.a",
            contract_fingerprint=contract.contract_fingerprint,
            last_embodiment_id="embodiment.old",
        )
    )
    exact = select_prior(
        archive,
        body_id="body.a",
        contract_fingerprint=contract.contract_fingerprint,
    )
    compatible = select_prior(
        archive,
        body_id="body.b",
        contract_fingerprint=contract.contract_fingerprint,
    )
    novel = select_prior(
        archive,
        body_id="body.c",
        contract_fingerprint=_contract(percepts=4).contract_fingerprint,
    )
    assert exact.relation == "same-body"
    assert compatible.relation == "same-contract"
    assert novel.relation == "novel"


def test_closed_episode_archives_body_specific_state_without_authority() -> None:
    contract = _contract()
    episode = EmbodimentEpisode.begin(
        symbiont_id="symbiont.a",
        body_id="body.a",
        epoch=1,
        start_symbiont_tick=0,
        contract=contract,
    )
    episode.advance()
    episode.close(symbiont_tick=1, reason=EmbodimentEndReason.BODY_REPLACED)
    payload = episode.checkpoint(current_tick=1)
    archive = EmbodimentArchive()
    summary = archive_episode_checkpoint(
        archive,
        payload,
        body_schema_prior=episode.body_schema.export(current_tick=1),
        living_body={"age_ticks": 1, "vital_state": "active"},
        symbiont_tick=1,
        end_reason="body_replaced",
    )
    assert summary.body_id == "body.a"
    assert archive.for_body("body.a") is not None
    assert archive.for_body("body.a").last_embodiment_id == episode.embodiment_id
    assert len(archive.summaries) == 1
