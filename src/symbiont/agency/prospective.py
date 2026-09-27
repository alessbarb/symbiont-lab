"""Central orchestrator for L8 Prospective Agency.

Coordinates candidate evaluation, counterfactual prediction, outcome-value
lookup, and policy decision. Does not execute motor actions; that is the
runtime's responsibility.

Separation:
    agency chooses
    runtime executes
    sensorimotor owns motor skill
"""

from __future__ import annotations

import math
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass

from .affordance import ActionAffordance
from .intention import AdmissionRoute
from .policy import EvaluatedCandidate, ProspectivePolicy
from .readiness import check_readiness
from .types import (
    CounterfactualPrediction,
    DeliberationOutcome,
    ProspectiveCandidate,
)
from .value import OutcomeValueLedger

# TODO(p1): How much confidence relaxation per non-selected candidate (unused in P0)
_QUERY_BUDGET_DEFAULT = 8


class ProspectiveAgency:
    """Deliberation orchestrator for model-based prospective action selection.

    Responsibilities:
    1. Check deliberation readiness
    2. Limit candidate set to query budget
    3. Request counterfactual predictions via caller-supplied predictor
    4. Look up outcome-value estimates from ledger
    5. Delegate to ProspectivePolicy
    6. Return DeliberationOutcome

    Never executes motors. Never records experience. Never imports symbiont_lab.
    """

    def __init__(
        self,
        *,
        organism_id: str,
        outcome_value_ledger: OutcomeValueLedger,
        policy: ProspectivePolicy,
        query_budget: int = _QUERY_BUDGET_DEFAULT,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id:
            raise ValueError("organism_id must be a non-empty string")
        if not isinstance(outcome_value_ledger, OutcomeValueLedger):
            raise ValueError("outcome_value_ledger must be an OutcomeValueLedger")
        if not isinstance(policy, ProspectivePolicy):
            raise ValueError("policy must be a ProspectivePolicy")
        if isinstance(query_budget, bool) or not isinstance(query_budget, int) or query_budget < 1:
            raise ValueError("query_budget must be a positive integer")

        self._organism_id = organism_id
        self._ledger = outcome_value_ledger
        self._policy = policy
        self._query_budget = query_budget

    @property
    def outcome_value_ledger(self) -> OutcomeValueLedger:
        return self._ledger

    def deliberate(
        self,
        *,
        tick: int,
        candidates: Collection[ProspectiveCandidate],
        context_tokens: tuple[str, ...],
        homeostatic_deviation: float,
        predictor: Callable[[str, tuple[str, ...]], CounterfactualPrediction],
        epistemic_value_provider: Callable[[str], float] | None = None,
        has_active_model: bool = True,
        organism_alive: bool = True,
    ) -> DeliberationOutcome:
        """Run one deliberation cycle and return a decision.

        Args:
            tick: Current organism tick.
            candidates: Prospective action candidates (from candidates.py).
            context_tokens: Current private cognitive context tokens.
            homeostatic_deviation: Current physiological deviation in [0, 1].
            predictor: Callable(action_id, context_tokens) -> CounterfactualPrediction.
                Called per candidate. Exceptions are caught; the candidate is
                skipped (fail-closed) rather than propagating.
            has_active_model: Whether an ACTIVE private SLM exists.
            organism_alive: Whether the organism's physiology is alive.

        Returns:
            DeliberationOutcome describing the chosen action or the reason for
            abstention.
        """
        # --- Death gate (highest priority) ---
        if not organism_alive:
            return DeliberationOutcome(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason="physiology_dead",
            )

        # --- Model gate ---
        if not has_active_model:
            return DeliberationOutcome(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason="no_active_model",
            )

        # --- Readiness gate ---
        candidate_list = list(candidates)
        readiness = check_readiness(
            has_active_model=has_active_model,
            competence_count=len(candidate_list),
            has_competence_readouts=bool(candidate_list),
            context_token_count=len(context_tokens),
            has_outcome_evidence=self._ledger.known_outcome_count > 0,
            organism_alive=organism_alive,
        )
        if not readiness.ready:
            # Map first failure reason to a DeliberationOutcome reason
            first_reason = readiness.reasons[0] if readiness.reasons else "no_candidates"
            reason = self._map_readiness_reason(first_reason)
            return DeliberationOutcome(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason=reason,
            )

        # --- Budget gate ---
        if len(candidate_list) > self._query_budget:
            candidate_list = candidate_list[: self._query_budget]

        # --- Evaluate candidates ---
        evaluated: list[EvaluatedCandidate] = []
        for candidate in candidate_list:
            try:
                prediction = predictor(candidate.action_id, context_tokens)
            except Exception:  # noqa: BLE001
                # WARN(fail-closed): skip this candidate if predictor raises
                continue

            if not isinstance(prediction, CounterfactualPrediction):
                continue

            # Look up historical value for the predicted outcome
            value = self._ledger.estimate(prediction.predicted_outcome)
            epistemic_value = 0.0
            if epistemic_value_provider is not None:
                try:
                    epistemic_value = float(epistemic_value_provider(candidate.action_id))
                except (TypeError, ValueError):
                    epistemic_value = 0.0
                epistemic_value = max(0.0, min(1.0, epistemic_value))

            evaluated.append(
                EvaluatedCandidate(
                    candidate=candidate,
                    prediction=prediction,
                    value=value,
                    estimated_cost=None,
                    epistemic_value=epistemic_value,
                )
            )

        # --- Delegate to policy ---
        return self._policy.choose(
            evaluated,
            homeostatic_deviation=homeostatic_deviation,
            tick=tick,
        )

    @staticmethod
    def _map_readiness_reason(readiness_reason: str) -> str:
        """Map internal readiness failure codes to DeliberationOutcome reasons."""
        mapping = {
            "organism_dead": "physiology_dead",
            "no_active_model": "no_active_model",
            "no_competences": "no_candidates",
            "no_competence_readouts": "no_candidates",
            "empty_context": "no_active_model",
            "no_outcome_evidence": "no_value_evidence",
        }
        return mapping.get(readiness_reason, "no_candidates")

    def checkpoint(self) -> dict[str, object]:
        """Export agency state for persistence.

        Only the OutcomeValueLedger is persisted. Pending counterfactuals and
        deliberation state are ephemeral and are not restored across restarts.
        """
        return {
            "schema_version": 1,
            "outcome_value_ledger": self._ledger.checkpoint(),
        }

    @classmethod
    def restore(
        cls,
        payload: dict[str, object],
        *,
        organism_id: str,
        policy: ProspectivePolicy,
        query_budget: int = _QUERY_BUDGET_DEFAULT,
    ) -> "ProspectiveAgency":
        """Restore from a checkpoint payload. Fails closed on schema mismatch."""
        if not isinstance(payload, dict):
            raise ValueError("invalid prospective agency checkpoint")
        version = payload.get("schema_version")
        if version != 1:
            raise ValueError(
                f"unsupported prospective agency checkpoint schema version: {version!r}"
            )
        ledger_payload = payload.get("outcome_value_ledger", {})
        ledger = OutcomeValueLedger.restore(ledger_payload)
        return cls(
            organism_id=organism_id,
            outcome_value_ledger=ledger,
            policy=policy,
            query_budget=query_budget,
        )


@dataclass(frozen=True, slots=True)
class ProspectiveDecision:
    """A candidate selected for executive admission (§50).

    Ephemeral projection: never checkpointed, never a motor authority.  It is
    transformed into an ActionIntent by IntentionDomain.form().
    """

    competence_id: str

    anticipated_effect_id: str | None

    prediction_ref: str | None

    confidence: float
    epistemic_relevance: float
    homeostatic_relevance: float

    origin_refs: tuple[str, ...]

    admission: AdmissionRoute = AdmissionRoute.COGNITIVE
    supporting_affordance_id: str | None = None

    def __post_init__(self) -> None:
        if not self.competence_id:
            raise ValueError("a prospective decision names an acquired competence")
        if not self.origin_refs:
            raise ValueError("a prospective decision must be traceable to its origin")
        for name in ("confidence", "epistemic_relevance", "homeostatic_relevance"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")


@dataclass(frozen=True)
class ExecutiveAdmissionPolicy:
    """Explicit gate from "represented" to "selected for realization" (§47-§48)."""

    readout_threshold: float = 0.1
    minimum_relevance: float = 0.2

    def __post_init__(self) -> None:
        for name in ("readout_threshold", "minimum_relevance"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class GenerativeAnticipation:
    """One effect anticipated by Generative Cognition, with its hypothesis origin."""

    effect_id: str
    hypothesis_refs: tuple[str, ...]


def admit_afforded_action(
    *,
    affordances: Collection[ActionAffordance],
    primitive_readouts: Mapping[str, float],
    generative_affordances: Collection[tuple[ActionAffordance, GenerativeAnticipation]] = (),
    epistemic_value: Callable[[str], float | None],
    homeostatic_relevance: Callable[[str], float],
    policy: ExecutiveAdmissionPolicy,
) -> ProspectiveDecision | None:
    """Model-free executive admission of one currently afforded competence.

    A primitive readout alone is only a representation: it may be memory,
    rehearsal or association.  A competence is admitted only when

    * it is represented — its readout is active (cognitive route) or an
      effect anticipated by Generative Cognition resolves to it
      (generative route);
    * it is currently afforded (executable here, with an expected effect);
    * and there is executive reason to realize it now: epistemic relevance
      (what it would do is still uncertain, by generative expectation or by
      its own predictive confidence) or homeostatic relevance (it has
      relieved the current need before) reaches the admission threshold.

    This is ProspectiveAgency's model-free admission, not another selector;
    the ActionArbitrator still decides motor authority.
    """
    candidates: list[tuple[ActionAffordance, AdmissionRoute, tuple[str, ...]]] = []
    for affordance in affordances:
        raw = primitive_readouts.get(affordance.competence_id)
        if (
            isinstance(raw, (int, float))
            and not isinstance(raw, bool)
            and math.isfinite(float(raw))
            and float(raw) >= policy.readout_threshold
        ):
            candidates.append(
                (
                    affordance,
                    AdmissionRoute.COGNITIVE,
                    (f"readout.primitive.{affordance.competence_id}",),
                )
            )
    for affordance, anticipation in generative_affordances:
        candidates.append(
            (
                affordance,
                AdmissionRoute.GENERATIVE,
                tuple(anticipation.hypothesis_refs) or (f"anticipated.{anticipation.effect_id}",),
            )
        )
    best: tuple[tuple[float, ...], ProspectiveDecision] | None = None
    for affordance, route, origins in candidates:
        # Epistemic relevance: the stronger of the organism's own signals that
        # realizing this competence would still be informative -- generative
        # expected uncertainty reduction, or its own predictive uncertainty.
        generative_epistemic = epistemic_value(affordance.competence_id)
        epistemic = max(
            0.0,
            min(
                1.0,
                max(
                    float(generative_epistemic) if generative_epistemic is not None else 0.0,
                    1.0 - affordance.prediction_confidence,
                ),
            ),
        )
        homeostatic = max(0.0, min(1.0, float(homeostatic_relevance(affordance.competence_id))))
        relevance = max(epistemic, homeostatic)
        if relevance < policy.minimum_relevance:
            continue
        decision = ProspectiveDecision(
            competence_id=affordance.competence_id,
            anticipated_effect_id=affordance.anticipated_effect_id,
            prediction_ref=affordance.prediction_ref,
            confidence=affordance.prediction_confidence,
            epistemic_relevance=epistemic,
            homeostatic_relevance=homeostatic,
            origin_refs=(*origins, affordance.affordance_id),
            admission=route,
            supporting_affordance_id=affordance.affordance_id,
        )
        key = (
            relevance,
            affordance.controllability,
            affordance.prediction_confidence,
            1.0 if route is AdmissionRoute.GENERATIVE else 0.0,
        )
        if (
            best is None
            or key > best[0]
            or (key == best[0] and decision.competence_id < best[1].competence_id)
        ):
            best = (key, decision)
    return best[1] if best is not None else None


__all__ = [
    "ExecutiveAdmissionPolicy",
    "GenerativeAnticipation",
    "ProspectiveAgency",
    "ProspectiveDecision",
    "admit_afforded_action",
]
