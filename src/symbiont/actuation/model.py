"""Predictive, controllability and agency views over canonical causal evidence."""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from .evidence import CausalEvidence, CausalEvidenceLedger


@dataclass(frozen=True, slots=True)
class EffectPrediction:
    prediction_id: str
    competence_id: str
    context_id: str | None
    effect_id: str
    confidence: float
    support: int


class CompetenceEffectModel:
    """Bounded abstract forward model: competence/context -> learned effect."""

    def __init__(self, *, max_contexts: int = 512) -> None:
        if max_contexts < 1:
            raise ValueError("max_contexts must be positive")
        self._max_contexts = int(max_contexts)
        self._counts: dict[tuple[str, str | None], Counter[str]] = {}

    def observe(self, evidence: CausalEvidence) -> None:
        if evidence.competence_id is None or evidence.effect_id is None:
            return
        key = (evidence.competence_id, evidence.context_ref)
        counter = self._counts.setdefault(key, Counter())
        counter[evidence.effect_id] += 1
        if len(self._counts) > self._max_contexts:
            retained = sorted(
                self._counts.items(),
                key=lambda item: (-sum(item[1].values()), item[0][0], item[0][1] or ""),
            )[: self._max_contexts]
            self._counts = dict(retained)

    def rebuild(self, ledger: CausalEvidenceLedger) -> None:
        self._counts = {}
        for evidence in ledger.evidence:
            self.observe(evidence)

    @property
    def context_count(self) -> int:
        return len(self._counts)

    def predict(
        self,
        *,
        competence_id: str,
        context_id: str | None,
    ) -> EffectPrediction | None:
        counter = self._counts.get((competence_id, context_id))
        if not counter:
            # Fall back to competence-wide evidence when this context is new.
            merged: Counter[str] = Counter()
            for (known_competence, _known_context), values in self._counts.items():
                if known_competence == competence_id:
                    merged.update(values)
            counter = merged
        if not counter:
            return None
        effect_id, support = min(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
        total = sum(counter.values())
        confidence = support / max(1, total)
        material = (
            f"{competence_id}|{context_id or '*'}|{effect_id}|{support}|{total}"
        ).encode("utf-8")
        return EffectPrediction(
            prediction_id="prediction." + hashlib.sha256(material).hexdigest()[:24],
            competence_id=competence_id,
            context_id=context_id,
            effect_id=effect_id,
            confidence=confidence,
            support=support,
        )


@dataclass(frozen=True, slots=True)
class ControllabilityEstimate:
    effect_id: str
    competence_id: str
    context_id: str | None
    confidence: float
    reliability: float
    counterfactual_rate: float | None
    causal_advantage: float | None
    action_support: int
    counterfactual_support: int
    last_updated_tick: int


class ControllabilityModel:
    """Infer control only when intervention evidence beats alternatives."""

    def __init__(self) -> None:
        self._estimates: dict[tuple[str, str, str | None], ControllabilityEstimate] = {}

    def update_from_ledger(
        self,
        ledger: CausalEvidenceLedger,
        *,
        effect_id: str,
        competence_id: str,
        context_id: str | None,
        tick: int,
    ) -> ControllabilityEstimate:
        action_n, action_hits, other_n, other_hits = ledger.effect_opportunities(
            effect_id,
            competence_id=competence_id,
            context_ref=context_id,
        )
        reliability = action_hits / action_n if action_n else 0.0
        counterfactual_rate = (other_hits / other_n) if other_n else None
        advantage = (
            reliability - counterfactual_rate
            if counterfactual_rate is not None
            else None
        )
        if action_n == 0:
            confidence = 0.0
        elif other_n == 0:
            confidence = min(0.25, action_n / 32.0)
        else:
            support = min(1.0, min(action_n, other_n) / 8.0)
            confidence = max(0.0, min(1.0, (advantage or 0.0) * support))
        estimate = ControllabilityEstimate(
            effect_id=effect_id,
            competence_id=competence_id,
            context_id=context_id,
            confidence=confidence,
            reliability=reliability,
            counterfactual_rate=counterfactual_rate,
            causal_advantage=advantage,
            action_support=action_n,
            counterfactual_support=other_n,
            last_updated_tick=tick,
        )
        self._estimates[(effect_id, competence_id, context_id)] = estimate
        return estimate

    def rebuild(self, ledger: CausalEvidenceLedger) -> None:
        self._estimates = {}
        keys = {
            (item.effect_id, item.competence_id, item.context_ref)
            for item in ledger.evidence
            if item.effect_id is not None and item.competence_id is not None
        }
        for effect_id, competence_id, context_id in sorted(
            keys,
            key=lambda item: (item[0], item[1], item[2] or ""),
        ):
            relevant_ticks = [
                item.observation_tick
                for item in ledger.evidence
                if item.effect_id == effect_id
                and item.competence_id == competence_id
                and item.context_ref == context_id
            ]
            self.update_from_ledger(
                ledger,
                effect_id=effect_id,
                competence_id=competence_id,
                context_id=context_id,
                tick=max(relevant_ticks, default=0),
            )

    def estimate(
        self,
        effect_id: str,
        competence_id: str,
        context_id: str | None = None,
    ) -> ControllabilityEstimate | None:
        return self._estimates.get((effect_id, competence_id, context_id))

    @property
    def estimates(self) -> tuple[ControllabilityEstimate, ...]:
        return tuple(
            sorted(
                self._estimates.values(),
                key=lambda item: (item.effect_id, item.competence_id, item.context_id or ""),
            )
        )


@dataclass(frozen=True, slots=True)
class AgencyEstimate:
    effect_id: str
    competence_id: str
    context_id: str | None
    confidence: float
    temporal_contingency: float
    causal_specificity: float
    prediction_match: float | None
    support: int
    last_updated_tick: int


class AgencyModel:
    """Infer ownership of consequences without duplicating factual evidence."""

    def __init__(self) -> None:
        self._estimates: dict[tuple[str, str, str | None], AgencyEstimate] = {}

    def update_from_ledger(
        self,
        ledger: CausalEvidenceLedger,
        *,
        effect_id: str,
        competence_id: str,
        context_id: str | None,
        tick: int,
        prediction_match: float | None,
    ) -> AgencyEstimate:
        action_n, action_hits, other_n, other_hits = ledger.effect_opportunities(
            effect_id,
            competence_id=competence_id,
            context_ref=context_id,
        )
        temporal = action_hits / action_n if action_n else 0.0
        other_rate = other_hits / other_n if other_n else 0.0
        specificity = max(0.0, min(1.0, temporal - other_rate))
        support_factor = min(1.0, action_n / 8.0)
        if prediction_match is None:
            predictive = 0.5
        else:
            predictive = max(0.0, min(1.0, float(prediction_match)))
        confidence = max(
            0.0,
            min(
                1.0,
                support_factor
                * (
                    0.45 * temporal
                    + 0.35 * specificity
                    + 0.20 * predictive
                ),
            ),
        )
        estimate = AgencyEstimate(
            effect_id=effect_id,
            competence_id=competence_id,
            context_id=context_id,
            confidence=confidence,
            temporal_contingency=temporal,
            causal_specificity=specificity,
            prediction_match=prediction_match,
            support=action_n,
            last_updated_tick=tick,
        )
        self._estimates[(effect_id, competence_id, context_id)] = estimate
        return estimate

    def rebuild(self, ledger: CausalEvidenceLedger) -> None:
        self._estimates = {}
        keys = {
            (item.effect_id, item.competence_id, item.context_ref)
            for item in ledger.evidence
            if item.effect_id is not None and item.competence_id is not None
        }
        for effect_id, competence_id, context_id in sorted(
            keys,
            key=lambda item: (item[0], item[1], item[2] or ""),
        ):
            relevant_ticks = [
                item.observation_tick
                for item in ledger.evidence
                if item.effect_id == effect_id
                and item.competence_id == competence_id
                and item.context_ref == context_id
            ]
            self.update_from_ledger(
                ledger,
                effect_id=effect_id,
                competence_id=competence_id,
                context_id=context_id,
                tick=max(relevant_ticks, default=0),
                prediction_match=None,
            )

    def estimate(
        self,
        effect_id: str,
        competence_id: str,
        context_id: str | None = None,
    ) -> AgencyEstimate | None:
        return self._estimates.get((effect_id, competence_id, context_id))

    @property
    def estimates(self) -> tuple[AgencyEstimate, ...]:
        return tuple(
            sorted(
                self._estimates.values(),
                key=lambda item: (item.effect_id, item.competence_id, item.context_id or ""),
            )
        )


# Historical import name retained as a strict alias during checkpoint/API migration.
# There is one implementation only: low-level body dynamics live separately in
# core.embodiment.dynamics.SensorimotorDynamicsModel.
SensorimotorModel = CompetenceEffectModel

