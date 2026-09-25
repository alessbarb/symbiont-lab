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

from collections.abc import Callable, Collection

from .policy import EvaluatedCandidate, ProspectivePolicy
from .readiness import check_readiness
from .types import (
    CounterfactualPrediction,
    ProspectiveCandidate,
    ProspectiveDecision,
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
    6. Return ProspectiveDecision

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
        has_active_model: bool = True,
        organism_alive: bool = True,
    ) -> ProspectiveDecision:
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
            ProspectiveDecision describing the chosen action or the reason for
            abstention.
        """
        # --- Death gate (highest priority) ---
        if not organism_alive:
            return ProspectiveDecision(
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
            return ProspectiveDecision(
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
            # Map first failure reason to a ProspectiveDecision reason
            first_reason = readiness.reasons[0] if readiness.reasons else "no_candidates"
            reason = self._map_readiness_reason(first_reason)
            return ProspectiveDecision(
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

            evaluated.append(
                EvaluatedCandidate(
                    candidate=candidate,
                    prediction=prediction,
                    value=value,
                    estimated_cost=None,
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
        """Map internal readiness failure codes to ProspectiveDecision reasons."""
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


__all__ = [
    "ProspectiveAgency",
]
