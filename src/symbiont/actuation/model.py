"""Predictive, controllability and agency views over canonical causal evidence.

Controllability and agency are inferred for a generalized causal source
(Agency Acquisition v1 §21-§23): a provisional intervention family, a learned
ActionDimension or a MotorCompetence.  One implementation serves all three so
the mathematics is never duplicated, and none of them requires a competence
to exist first.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from .evidence import CausalEvidence, CausalEvidenceLedger, Opportunities, OpportunityView


class CausalSourceKind(StrEnum):
    INTERVENTION = "intervention"
    DIMENSION = "dimension"
    COMPETENCE = "competence"


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
        material = (f"{competence_id}|{context_id or '*'}|{effect_id}|{support}|{total}").encode(
            "utf-8"
        )
        return EffectPrediction(
            prediction_id="prediction." + hashlib.sha256(material).hexdigest()[:24],
            competence_id=competence_id,
            context_id=context_id,
            effect_id=effect_id,
            confidence=confidence,
            support=support,
        )


def source_opportunities(
    ledger: OpportunityView,
    *,
    source_kind: CausalSourceKind,
    source_ref: str,
    effect_id: str,
    context_id: str | None,
    dimension_signature_refs: tuple[str, ...] | None = None,
) -> Opportunities:
    """Intervention-versus-alternative opportunities for any causal source."""
    if source_kind is CausalSourceKind.COMPETENCE:
        return ledger.effect_opportunities(
            effect_id, competence_id=source_ref, context_ref=context_id
        )
    if source_kind is CausalSourceKind.INTERVENTION:
        return ledger.signature_effect_opportunities(
            effect_id, intervention_signature_id=source_ref, context_ref=context_id
        )
    if not dimension_signature_refs:
        raise ValueError("dimension opportunities require its intervention families")
    return ledger.signatures_effect_opportunities(
        effect_id,
        intervention_signature_ids=dimension_signature_refs,
        context_ref=context_id,
    )


_Key = tuple[CausalSourceKind, str, str, str | None]


def _source_keys(ledger: CausalEvidenceLedger) -> dict[_Key, int]:
    """Every (kind, ref, effect, context) with evidence, and its latest tick."""
    keys: dict[_Key, int] = {}
    for item in ledger.intervention_evidence:
        if item.effect_id is None:
            continue
        for kind, ref in (
            (CausalSourceKind.COMPETENCE, item.competence_id),
            (CausalSourceKind.INTERVENTION, item.intervention_signature_id),
        ):
            if ref is None:
                continue
            key = (kind, ref, item.effect_id, item.context_ref)
            keys[key] = max(keys.get(key, 0), item.observation_tick)
    return keys


def _dimension_keys(
    ledger: CausalEvidenceLedger,
    dimensions: Mapping[str, tuple[str, ...]],
) -> dict[_Key, int]:
    """Context-free (dimension, effect) keys: dimensions are discovered context-free."""
    member_of = {
        signature_ref: dimension_id
        for dimension_id, refs in dimensions.items()
        for signature_ref in refs
    }
    keys: dict[_Key, int] = {}
    for item in ledger.intervention_evidence:
        dimension_id = member_of.get(item.intervention_signature_id or "")
        if dimension_id is None or item.effect_id is None:
            continue
        key = (CausalSourceKind.DIMENSION, dimension_id, item.effect_id, None)
        keys[key] = max(keys.get(key, 0), item.observation_tick)
    return keys


MAX_ESTIMATES = 8192


class _SourceIndexed:
    """Shared per-source lookup, bound and persistence for estimate registries."""

    _estimates: dict
    _by_source: dict
    _estimate_type: type

    def _store(self, key: _Key, estimate) -> None:
        self._estimates[key] = estimate
        self._by_source.setdefault((key[0], key[1]), set()).add(key)
        self._by_kind.setdefault(key[0], set()).add(key)
        if len(self._estimates) > MAX_ESTIMATES + MAX_ESTIMATES // 8:
            self._prune()

    def _prune(self) -> None:
        """Keep the most recently supported relations; bounded organism memory."""
        retained = sorted(
            self._estimates.items(),
            key=lambda item: (
                -item[1].last_updated_tick,
                item[0][0],
                item[0][1],
                item[0][2],
                item[0][3] or "",
            ),
        )[:MAX_ESTIMATES]
        self._estimates = dict(retained)
        self._by_source = {}
        self._by_kind = {}
        for key in self._estimates:
            self._by_source.setdefault((key[0], key[1]), set()).add(key)
            self._by_kind.setdefault(key[0], set()).add(key)

    def checkpoint(self) -> list[dict[str, object]]:
        return [
            {
                field: (value.value if isinstance(value, CausalSourceKind) else value)
                for field, value in (
                    (name, getattr(estimate, name))
                    for name in self._estimate_type.__dataclass_fields__
                )
            }
            for estimate in self.estimates
        ]

    def restore_estimates(self, payload: object) -> None:
        if not isinstance(payload, list) or len(payload) > MAX_ESTIMATES + MAX_ESTIMATES // 8:
            raise ValueError("invalid or unbounded causal estimate table")
        self._estimates = {}
        self._by_source = {}
        self._by_kind = {}
        for raw in payload:
            if not isinstance(raw, Mapping):
                raise ValueError("invalid causal estimate")
            values = dict(raw)
            values["source_kind"] = CausalSourceKind(str(values["source_kind"]))
            estimate = self._estimate_type(**values)
            self._store(
                (
                    estimate.source_kind,
                    estimate.source_ref,
                    estimate.effect_id,
                    estimate.context_id,
                ),
                estimate,
            )

    def estimates_for(self, source_kind: CausalSourceKind) -> tuple:
        keys = self._by_kind.get(source_kind, ())
        return tuple(
            self._estimates[key] for key in sorted(keys, key=lambda k: (k[1], k[2], k[3] or ""))
        )

    def __len__(self) -> int:
        return len(self._estimates)

    @property
    def estimates(self) -> tuple:
        return tuple(
            sorted(
                self._estimates.values(),
                key=lambda item: (
                    item.source_kind,
                    item.source_ref,
                    item.effect_id,
                    item.context_id or "",
                ),
            )
        )

    def for_source(self, source_kind: CausalSourceKind, source_ref: str) -> tuple:
        keys = self._by_source.get((source_kind, source_ref), ())
        return tuple(self._estimates[key] for key in sorted(keys, key=lambda k: (k[2], k[3] or "")))


@dataclass(frozen=True, slots=True)
class ControllabilityEstimate:
    source_kind: CausalSourceKind
    source_ref: str

    effect_id: str
    context_id: str | None

    confidence: float
    reliability: float

    counterfactual_rate: float | None
    causal_advantage: float | None

    action_support: int
    counterfactual_support: int

    last_updated_tick: int


class ControllabilityModel(_SourceIndexed):
    """Infer control only when intervention evidence beats alternatives."""

    _estimate_type = ControllabilityEstimate

    def __init__(self) -> None:
        self._estimates: dict[_Key, ControllabilityEstimate] = {}
        self._by_source: dict[tuple[CausalSourceKind, str], set[_Key]] = {}
        self._by_kind: dict[CausalSourceKind, set[_Key]] = {}

    def update_from_ledger(
        self,
        ledger: OpportunityView,
        *,
        source_kind: CausalSourceKind,
        source_ref: str,
        effect_id: str,
        context_id: str | None,
        tick: int,
        dimension_signature_refs: tuple[str, ...] | None = None,
    ) -> ControllabilityEstimate:
        action_n, action_hits, other_n, other_hits = source_opportunities(
            ledger,
            source_kind=source_kind,
            source_ref=source_ref,
            effect_id=effect_id,
            context_id=context_id,
            dimension_signature_refs=dimension_signature_refs,
        )
        reliability = action_hits / action_n if action_n else 0.0
        counterfactual_rate = (other_hits / other_n) if other_n else None
        advantage = reliability - counterfactual_rate if counterfactual_rate is not None else None
        if action_n == 0:
            confidence = 0.0
        elif other_n == 0:
            confidence = min(0.25, action_n / 32.0)
        else:
            support = min(1.0, min(action_n, other_n) / 8.0)
            confidence = max(0.0, min(1.0, (advantage or 0.0) * support))
        estimate = ControllabilityEstimate(
            source_kind=source_kind,
            source_ref=source_ref,
            effect_id=effect_id,
            context_id=context_id,
            confidence=confidence,
            reliability=reliability,
            counterfactual_rate=counterfactual_rate,
            causal_advantage=advantage,
            action_support=action_n,
            counterfactual_support=other_n,
            last_updated_tick=tick,
        )
        self._store((source_kind, source_ref, effect_id, context_id), estimate)
        return estimate

    def rebuild(
        self,
        ledger: CausalEvidenceLedger,
        *,
        dimensions: Mapping[str, tuple[str, ...]] | None = None,
        view: OpportunityView | None = None,
    ) -> None:
        self._estimates = {}
        self._by_source = {}
        self._by_kind = {}
        keys = _source_keys(ledger)
        keys.update(_dimension_keys(ledger, dimensions or {}))
        for (kind, ref, effect_id, context_id), tick in sorted(
            keys.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3] or "")
        ):
            self.update_from_ledger(
                view if view is not None else ledger,
                source_kind=kind,
                source_ref=ref,
                effect_id=effect_id,
                context_id=context_id,
                tick=tick,
                dimension_signature_refs=(dimensions or {}).get(ref)
                if kind is CausalSourceKind.DIMENSION
                else None,
            )

    def estimate(
        self,
        *,
        source_kind: CausalSourceKind,
        source_ref: str,
        effect_id: str,
        context_id: str | None = None,
    ) -> ControllabilityEstimate | None:
        return self._estimates.get((source_kind, source_ref, effect_id, context_id))

    def discard_source(self, source_kind: CausalSourceKind, source_ref: str) -> None:
        for key in self._by_source.pop((source_kind, source_ref), set()):
            self._estimates.pop(key, None)
            self._by_kind.get(source_kind, set()).discard(key)


@dataclass(frozen=True, slots=True)
class AgencyEstimate:
    source_kind: CausalSourceKind
    source_ref: str

    effect_id: str
    context_id: str | None

    confidence: float
    temporal_contingency: float
    causal_specificity: float
    prediction_match: float | None
    support: int
    counterfactual_support: int
    last_updated_tick: int


class AgencyModel(_SourceIndexed):
    """Infer ownership of consequences without duplicating factual evidence.

    Agency is contingency + specificity + intervention evidence +
    counterfactual evidence + prediction + support (§23).  A matched
    prediction alone never yields agency: without positive temporal
    contingency *and* positive specificity against counterfactual windows the
    estimate is zero whatever the prediction agreement.
    """

    _estimate_type = AgencyEstimate

    def __init__(self) -> None:
        self._estimates: dict[_Key, AgencyEstimate] = {}
        self._by_source: dict[tuple[CausalSourceKind, str], set[_Key]] = {}
        self._by_kind: dict[CausalSourceKind, set[_Key]] = {}

    def update_from_ledger(
        self,
        ledger: OpportunityView,
        *,
        source_kind: CausalSourceKind,
        source_ref: str,
        effect_id: str,
        context_id: str | None,
        tick: int,
        prediction_match: float | None,
        dimension_signature_refs: tuple[str, ...] | None = None,
    ) -> AgencyEstimate:
        action_n, action_hits, other_n, other_hits = source_opportunities(
            ledger,
            source_kind=source_kind,
            source_ref=source_ref,
            effect_id=effect_id,
            context_id=context_id,
            dimension_signature_refs=dimension_signature_refs,
        )
        temporal = action_hits / action_n if action_n else 0.0
        other_rate = other_hits / other_n if other_n else 0.0
        specificity = max(0.0, min(1.0, temporal - other_rate))
        support_factor = min(1.0, action_n / 8.0)
        counterfactual_factor = min(1.0, other_n / 8.0)
        if prediction_match is None:
            predictive = 0.5
        else:
            predictive = max(0.0, min(1.0, float(prediction_match)))
        if temporal <= 0.0 or specificity <= 0.0:
            confidence = 0.0
        else:
            confidence = max(
                0.0,
                min(
                    1.0,
                    min(support_factor, counterfactual_factor)
                    * (0.45 * temporal + 0.35 * specificity + 0.20 * predictive),
                ),
            )
        estimate = AgencyEstimate(
            source_kind=source_kind,
            source_ref=source_ref,
            effect_id=effect_id,
            context_id=context_id,
            confidence=confidence,
            temporal_contingency=temporal,
            causal_specificity=specificity,
            prediction_match=prediction_match,
            support=action_n,
            counterfactual_support=other_n,
            last_updated_tick=tick,
        )
        self._store((source_kind, source_ref, effect_id, context_id), estimate)
        return estimate

    def rebuild(
        self,
        ledger: CausalEvidenceLedger,
        *,
        dimensions: Mapping[str, tuple[str, ...]] | None = None,
        view: OpportunityView | None = None,
    ) -> None:
        self._estimates = {}
        self._by_source = {}
        self._by_kind = {}
        keys = _source_keys(ledger)
        keys.update(_dimension_keys(ledger, dimensions or {}))
        for (kind, ref, effect_id, context_id), tick in sorted(
            keys.items(), key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3] or "")
        ):
            self.update_from_ledger(
                view if view is not None else ledger,
                source_kind=kind,
                source_ref=ref,
                effect_id=effect_id,
                context_id=context_id,
                tick=tick,
                prediction_match=None,
                dimension_signature_refs=(dimensions or {}).get(ref)
                if kind is CausalSourceKind.DIMENSION
                else None,
            )

    def estimate(
        self,
        *,
        source_kind: CausalSourceKind,
        source_ref: str,
        effect_id: str,
        context_id: str | None = None,
    ) -> AgencyEstimate | None:
        return self._estimates.get((source_kind, source_ref, effect_id, context_id))

    def discard_source(self, source_kind: CausalSourceKind, source_ref: str) -> None:
        for key in self._by_source.pop((source_kind, source_ref), set()):
            self._estimates.pop(key, None)
            self._by_kind.get(source_kind, set()).discard(key)
