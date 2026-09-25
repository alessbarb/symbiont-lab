"""Longitudinal A→B→A re-embodiment reacclimation analysis.

This module is evaluator-only. It consumes checkpoints captured during real
embodiment runs and never feeds targets, labels or priors back into Symbiont.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence


_CAUSAL_THRESHOLD = 0.45
_CONTROLLABILITY_THRESHOLD = 0.35
_SCHEMA_UNCERTAINTY_THRESHOLD = 0.35
_PREDICTION_SHOCK_THRESHOLD = 0.20


class ReacclimationVerdict(StrEnum):
    CONTAMINATED_RESTORE = "contaminated_restore"
    NO_TRANSFER = "no_transfer"
    REVALIDATED_TRANSFER = "revalidated_transfer"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class ReembodimentObservation:
    embodiment_id: str
    body_id: str
    embodiment_tick: int
    contract_fingerprint: str
    prior_relation: str
    prior_authority: str
    prediction_shock: float
    schema_uncertainty: float
    causal_confidence: float
    controllability_confidence: float
    recovery_tick: int | None
    historical_candidate_ids: tuple[str, ...]
    executable_binding_ids: tuple[str, ...]
    causal_evidence_count: int

    @property
    def executable_count(self) -> int:
        return len(self.executable_binding_ids)


@dataclass(frozen=True, slots=True)
class EpochReacclimationMetrics:
    embodiment_id: str
    contract_fingerprint: str
    prior_relation: str
    start_executable_count: int
    start_historical_candidate_count: int
    first_causal_tick: int | None
    first_controllability_tick: int | None
    first_low_uncertainty_tick: int | None
    first_low_prediction_shock_tick: int | None
    first_binding_tick: int | None
    first_prior_revalidation_tick: int | None
    recovery_tick: int | None
    final_executable_count: int
    final_causal_evidence_count: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReembodimentReacclimationStudy:
    a1: EpochReacclimationMetrics
    b: EpochReacclimationMetrics
    a2: EpochReacclimationMetrics
    same_contract_return: bool
    clean_a2_start: bool
    historical_hypotheses_present: bool
    faster_dimensions: tuple[str, ...]
    verdict: ReacclimationVerdict

    @property
    def passed(self) -> bool:
        return self.verdict is ReacclimationVerdict.REVALIDATED_TRANSFER

    def as_dict(self) -> dict[str, object]:
        return {
            "a1": self.a1.as_dict(),
            "b": self.b.as_dict(),
            "a2": self.a2.as_dict(),
            "same_contract_return": self.same_contract_return,
            "clean_a2_start": self.clean_a2_start,
            "historical_hypotheses_present": self.historical_hypotheses_present,
            "faster_dimensions": list(self.faster_dimensions),
            "verdict": self.verdict.value,
            "passed": self.passed,
        }


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def observation_from_checkpoint(
    payload: Mapping[str, Any],
) -> ReembodimentObservation:
    episode = _mapping(payload.get("embodiment_episode"))
    contract = _mapping(episode.get("contract"))
    adaptation = _mapping(episode.get("adaptation"))
    prior = _mapping(episode.get("prior"))

    actuation = _mapping(payload.get("actuation"))
    action_domain = _mapping(actuation.get("action_domain"))
    competence_development = _mapping(
        action_domain.get("competence_development")
    )
    historical = _items(
        competence_development.get("historical_candidates")
    )

    bindings = _mapping(episode.get("execution_bindings"))
    if not bindings:
        sensorimotor_v2 = _mapping(
            action_domain.get("sensorimotor_v2")
        )
        bindings = _mapping(
            sensorimotor_v2.get("execution_bindings")
        )
    binding_items = _items(bindings.get("items"))

    causal = _mapping(episode.get("causal_evidence"))
    evidence = causal.get("evidence")
    evidence_count = len(evidence) if isinstance(evidence, list) else 0

    historical_ids = tuple(
        sorted(
            str(item["primitive_id"])
            for item in historical
            if isinstance(item.get("primitive_id"), str)
            and item.get("primitive_id")
        )
    )
    binding_ids = tuple(
        sorted(
            str(item["competence_id"])
            for item in binding_items
            if isinstance(item.get("competence_id"), str)
            and item.get("competence_id")
        )
    )

    return ReembodimentObservation(
        embodiment_id=str(episode.get("embodiment_id") or ""),
        body_id=str(episode.get("body_id") or ""),
        embodiment_tick=int(episode.get("embodiment_tick") or 0),
        contract_fingerprint=str(
            contract.get("contract_fingerprint") or ""
        ),
        prior_relation=str(prior.get("relation") or "novel"),
        prior_authority=str(
            prior.get("authority") or "hypothesis_only"
        ),
        prediction_shock=float(
            adaptation.get("prediction_shock") or 0.0
        ),
        schema_uncertainty=float(
            adaptation.get("schema_uncertainty", 1.0)
        ),
        causal_confidence=float(
            adaptation.get("causal_confidence") or 0.0
        ),
        controllability_confidence=float(
            adaptation.get("controllability_confidence") or 0.0
        ),
        recovery_tick=(
            int(adaptation["recovery_tick"])
            if adaptation.get("recovery_tick") is not None
            else None
        ),
        historical_candidate_ids=historical_ids,
        executable_binding_ids=binding_ids,
        causal_evidence_count=evidence_count,
    )


def _first_tick(
    trace: Sequence[ReembodimentObservation],
    predicate,
) -> int | None:
    for point in trace:
        if predicate(point):
            return point.embodiment_tick
    return None


def analyze_observation_epoch(
    observations: Sequence[ReembodimentObservation],
) -> EpochReacclimationMetrics:
    if not observations:
        raise ValueError("epoch trace must not be empty")
    trace = tuple(
        sorted(
            observations,
            key=lambda point: point.embodiment_tick,
        )
    )
    identity = trace[0].embodiment_id
    contract = trace[0].contract_fingerprint
    if not identity or not contract:
        raise ValueError("epoch trace lacks canonical embodiment identity")
    if any(point.embodiment_id != identity for point in trace):
        raise ValueError("epoch trace mixes embodiment ids")
    if any(point.contract_fingerprint != contract for point in trace):
        raise ValueError("epoch trace changes contract")

    start = trace[0]
    final = trace[-1]
    historical = set(start.historical_candidate_ids)
    return EpochReacclimationMetrics(
        embodiment_id=identity,
        contract_fingerprint=contract,
        prior_relation=start.prior_relation,
        start_executable_count=start.executable_count,
        start_historical_candidate_count=len(historical),
        first_causal_tick=_first_tick(
            trace,
            lambda point: point.causal_confidence >= _CAUSAL_THRESHOLD,
        ),
        first_controllability_tick=_first_tick(
            trace,
            lambda point: (
                point.controllability_confidence
                >= _CONTROLLABILITY_THRESHOLD
            ),
        ),
        first_low_uncertainty_tick=_first_tick(
            trace,
            lambda point: (
                point.schema_uncertainty
                <= _SCHEMA_UNCERTAINTY_THRESHOLD
            ),
        ),
        first_low_prediction_shock_tick=_first_tick(
            trace,
            lambda point: (
                point.prediction_shock
                <= _PREDICTION_SHOCK_THRESHOLD
            ),
        ),
        first_binding_tick=_first_tick(
            trace,
            lambda point: point.executable_count > 0,
        ),
        first_prior_revalidation_tick=_first_tick(
            trace,
            lambda point: bool(
                historical.intersection(
                    point.executable_binding_ids
                )
            ),
        ),
        recovery_tick=next(
            (
                point.recovery_tick
                for point in trace
                if point.recovery_tick is not None
            ),
            None,
        ),
        final_executable_count=final.executable_count,
        final_causal_evidence_count=final.causal_evidence_count,
    )


def analyze_epoch(
    checkpoints: Sequence[Mapping[str, Any]],
) -> EpochReacclimationMetrics:
    return analyze_observation_epoch(
        tuple(observation_from_checkpoint(item) for item in checkpoints)
    )


def _faster(
    first: int | None,
    second: int | None,
) -> bool:
    return first is not None and second is not None and second < first


def analyze_reembodiment_observations(
    *,
    a1_trace: Sequence[ReembodimentObservation],
    b_trace: Sequence[ReembodimentObservation],
    a2_trace: Sequence[ReembodimentObservation],
) -> ReembodimentReacclimationStudy:
    a1 = analyze_observation_epoch(a1_trace)
    b = analyze_observation_epoch(b_trace)
    a2 = analyze_observation_epoch(a2_trace)

    same_contract_return = (
        a1.contract_fingerprint == a2.contract_fingerprint
        and b.contract_fingerprint != a1.contract_fingerprint
    )
    clean_a2_start = (
        a2.prior_relation == "same-contract"
        and a2.start_executable_count == 0
    )
    historical_hypotheses_present = (
        a2.start_historical_candidate_count > 0
    )

    comparisons = {
        "causal_confidence": (
            a1.first_causal_tick,
            a2.first_causal_tick,
        ),
        "controllability": (
            a1.first_controllability_tick,
            a2.first_controllability_tick,
        ),
        "schema_uncertainty": (
            a1.first_low_uncertainty_tick,
            a2.first_low_uncertainty_tick,
        ),
        "recovery": (
            a1.recovery_tick,
            a2.recovery_tick,
        ),
        "execution_binding": (
            a1.first_binding_tick,
            a2.first_binding_tick,
        ),
    }
    faster_dimensions = tuple(
        name
        for name, (first, second) in comparisons.items()
        if _faster(first, second)
    )

    a2_has_instant_authority = (
        a2.start_executable_count > 0
        or (
            a2.first_binding_tick is not None
            and a2.first_binding_tick <= 0
        )
    )
    if a2_has_instant_authority:
        verdict = ReacclimationVerdict.CONTAMINATED_RESTORE
    elif not same_contract_return:
        verdict = ReacclimationVerdict.INCONCLUSIVE
    elif not historical_hypotheses_present:
        verdict = ReacclimationVerdict.NO_TRANSFER
    elif (
        a2.first_prior_revalidation_tick is not None
        and a2.first_prior_revalidation_tick > 0
        and faster_dimensions
    ):
        verdict = ReacclimationVerdict.REVALIDATED_TRANSFER
    elif (
        a1.first_causal_tick is None
        or a2.first_causal_tick is None
        or a1.first_controllability_tick is None
        or a2.first_controllability_tick is None
    ):
        verdict = ReacclimationVerdict.INCONCLUSIVE
    else:
        verdict = ReacclimationVerdict.NO_TRANSFER

    return ReembodimentReacclimationStudy(
        a1=a1,
        b=b,
        a2=a2,
        same_contract_return=same_contract_return,
        clean_a2_start=clean_a2_start,
        historical_hypotheses_present=historical_hypotheses_present,
        faster_dimensions=faster_dimensions,
        verdict=verdict,
    )


def analyze_reembodiment_reacclimation(
    *,
    a1_trace: Sequence[Mapping[str, Any]],
    b_trace: Sequence[Mapping[str, Any]],
    a2_trace: Sequence[Mapping[str, Any]],
) -> ReembodimentReacclimationStudy:
    return analyze_reembodiment_observations(
        a1_trace=tuple(
            observation_from_checkpoint(item) for item in a1_trace
        ),
        b_trace=tuple(
            observation_from_checkpoint(item) for item in b_trace
        ),
        a2_trace=tuple(
            observation_from_checkpoint(item) for item in a2_trace
        ),
    )


__all__ = [
    "EpochReacclimationMetrics",
    "ReacclimationVerdict",
    "ReembodimentObservation",
    "ReembodimentReacclimationStudy",
    "analyze_epoch",
    "analyze_observation_epoch",
    "analyze_reembodiment_observations",
    "analyze_reembodiment_reacclimation",
    "observation_from_checkpoint",
]
