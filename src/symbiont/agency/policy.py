"""Prospective decision policy for L8 Prospective Agency.

Pure decision logic. Receives pre-evaluated candidates and returns a
ProspectiveDecision. Knows nothing about models, physiology, or motor
execution.

Utility formula (P0):
    utility = mean_value × value_confidence × model_confidence_normalized

where model_confidence_normalized = confidence_class / 7.

No environmental or evaluator metrics feed into this computation.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Collection
from dataclasses import dataclass

from .types import (
    CounterfactualPrediction,
    OutcomeValueEstimate,
    ProspectiveCandidate,
    ProspectiveDecision,
)

_MIN_CONFIDENCE_CLASS = 1  # confidence_class 0 is considered no-signal
_CONFIDENCE_CLASS_MAX = 7  # denominator for normalising confidence_class


@dataclass(frozen=True)
class EvaluatedCandidate:
    """One candidate after model prediction and value lookup have been applied."""

    candidate: ProspectiveCandidate
    prediction: CounterfactualPrediction
    value: OutcomeValueEstimate | None
    estimated_cost: float | None  # reserved for L8.6+; unused in P0 utility


class ProspectivePolicy:
    """Conservative selection policy for prospective action deliberation.

    A candidate dominates only if all of the following hold:
    - prediction.confidence_class >= min_confidence_class
    - value evidence exists (OutcomeValueEstimate is not None)
    - value confidence (from ledger) meets sample threshold
    - utility margin over the next-best candidate >= decision_margin

    Utility (P0): mean_value × value_confidence × model_confidence_normalized

    Tie-breaking is deterministic: sha256 of organism_id + tick + action_id.

    Costs are reserved for L8.6+; not used in P0 utility ranking.
    """

    def __init__(
        self,
        *,
        organism_id: str,
        min_model_confidence: float = 0.5,
        min_value_samples: int = 4,
        decision_margin: float = 0.02,
    ) -> None:
        if not isinstance(organism_id, str) or not organism_id:
            raise ValueError("organism_id must be a non-empty string")
        if (
            isinstance(min_model_confidence, bool)
            or not isinstance(min_model_confidence, (int, float))
            or not math.isfinite(float(min_model_confidence))
            or not 0.0 <= float(min_model_confidence) <= 1.0
        ):
            raise ValueError("min_model_confidence must be in [0, 1]")
        if (
            isinstance(min_value_samples, bool)
            or not isinstance(min_value_samples, int)
            or min_value_samples < 1
        ):
            raise ValueError("min_value_samples must be a positive integer")
        if (
            isinstance(decision_margin, bool)
            or not isinstance(decision_margin, (int, float))
            or not math.isfinite(float(decision_margin))
            or float(decision_margin) < 0.0
        ):
            raise ValueError("decision_margin must be a non-negative finite float")

        self._organism_id = organism_id
        self._min_model_confidence = float(min_model_confidence)
        self._min_value_confidence = float(min_value_samples) / 16.0
        self._decision_margin = float(decision_margin)

    def _tiebreak_key(self, action_id: str, tick: int) -> str:
        """Deterministic tiebreak — never interprets action_id semantically."""
        material = f"{self._organism_id}:{tick}:{action_id}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def _utility(
        value: OutcomeValueEstimate,
        confidence_class: int,
    ) -> float:
        """P0 utility: mean_value × value_confidence × model_confidence_normalized."""
        model_conf = confidence_class / float(_CONFIDENCE_CLASS_MAX)
        return float(value.mean_value) * float(value.confidence) * model_conf

    def choose(
        self,
        candidates: Collection[EvaluatedCandidate],
        *,
        homeostatic_deviation: float,
        tick: int,
    ) -> ProspectiveDecision:
        """Select the best candidate, or return a non-selecting decision.

        Args:
            candidates: Pre-evaluated candidates (prediction + value already
                resolved by ProspectiveAgency).
            homeostatic_deviation: Current physiological disequilibrium in [0, 1].
                Accepted for future extensions; not currently used in utility.
            tick: Current organism tick for deterministic tiebreaking.

        Returns:
            A ProspectiveDecision with reason indicating outcome.
        """
        candidate_list = list(candidates)

        if not candidate_list:
            return ProspectiveDecision(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason="no_candidates",
            )

        # Filter candidates with sufficient evidence
        valued = [ec for ec in candidate_list if ec.value is not None]
        if not valued:
            return ProspectiveDecision(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason="no_value_evidence",
            )

        # Apply confidence gates
        confident: list[tuple[float, str, EvaluatedCandidate]] = []
        for ec in valued:
            assert ec.value is not None  # narrowing
            model_conf_norm = ec.prediction.confidence_class / float(_CONFIDENCE_CLASS_MAX)
            if model_conf_norm < self._min_model_confidence:
                continue
            if ec.value.confidence < self._min_value_confidence:
                continue
            if ec.prediction.confidence_class < _MIN_CONFIDENCE_CLASS:
                continue
            utility = self._utility(ec.value, ec.prediction.confidence_class)
            tiebreak = self._tiebreak_key(ec.candidate.action_id, tick)
            confident.append((utility, tiebreak, ec))

        if not confident:
            return ProspectiveDecision(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=None,
                reason="insufficient_confidence",
            )

        # Sort by utility desc, then by deterministic tiebreak asc
        confident.sort(key=lambda item: (-item[0], item[1]))
        best_utility, _, best_ec = confident[0]

        # Check decision margin against second-best
        second_utility = confident[1][0] if len(confident) > 1 else -math.inf
        margin = best_utility - second_utility

        if margin < self._decision_margin:
            return ProspectiveDecision(
                tick=tick,
                candidate_id=None,
                predicted_outcome=None,
                expected_value=None,
                model_confidence=None,
                value_confidence=None,
                decision_margin=float(margin) if math.isfinite(margin) else None,
                reason="insufficient_margin",
            )

        assert best_ec.value is not None  # narrowing
        return ProspectiveDecision(
            tick=tick,
            candidate_id=best_ec.candidate.action_id,
            predicted_outcome=best_ec.prediction.predicted_outcome,
            expected_value=float(best_utility),
            model_confidence=best_ec.prediction.confidence_class / float(_CONFIDENCE_CLASS_MAX),
            value_confidence=float(best_ec.value.confidence),
            decision_margin=float(margin) if math.isfinite(margin) else None,
            reason="selected",
        )


__all__ = [
    "EvaluatedCandidate",
    "ProspectivePolicy",
]
