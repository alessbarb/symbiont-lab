from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ...host.acclimation import CapabilityBaseline, HostAcclimation
from ..cognition.attention import AttentionAllocation, uncertainty_from_baseline
from ..cognition.evidence import DissentRecord

_UNFAMILIAR = "unfamiliar"
_FAMILIAR = "familiar"


@dataclass(slots=True, frozen=True)
class NarrativeEntry:
    """One inspectable, plain-language account of what the organism
    currently believes about a capability, why it attended (or didn't),
    what evidence it gathered and whether that belief was contested
    (roadmap v0.41 — the capstone of Milestone C).

    Every field is already something v0.33 (belief/uncertainty), v0.38
    (attention) and v0.40 (evidence/dissent) commit to exposing publicly on
    their own — this gathers them into one explainable account per
    capability rather than leaving a reader to cross-reference four
    separate objects. Purely descriptive, never a threat or classification
    verdict (``docs/adr/ADR-0003-attention-is-not-classification.md``), and
    never a raw reading — only the abstract state those modules already
    expose.
    """

    capability_id: str
    familiarity: str
    uncertainty: float
    attended: bool
    attention_cost: float | None
    evidence_gathered: int
    dissent: DissentRecord | None
    summary: str

    @property
    def contested(self) -> bool:
        return self.dissent is not None


def _familiarity_for(baseline: CapabilityBaseline | None) -> str:
    return _UNFAMILIAR if baseline is None else _FAMILIAR


def _summarize(
    *,
    capability_id: str,
    familiarity: str,
    uncertainty: float,
    attended: bool,
    evidence_gathered: int,
    dissent: DissentRecord | None,
) -> str:
    if familiarity == _UNFAMILIAR:
        belief_clause = f"{capability_id} is not yet familiar — no baseline has been learned for it"
    elif uncertainty == float("inf"):
        belief_clause = f"{capability_id} is familiar but its uncertainty could not be computed"
    else:
        belief_clause = (
            f"{capability_id} is familiar, with a relative uncertainty of {uncertainty:.3f}"
        )

    attention_clause = (
        "it received attention this tick" if attended else "it did not receive attention this tick"
    )

    evidence_clause = (
        f", {evidence_gathered} new reading(s) were gathered as evidence"
        if evidence_gathered > 0
        else ""
    )
    dissent_clause = (
        f" and that evidence (mean {dissent.evidence_mean:.3f}) contested its prior belief "
        f"(mean {dissent.prior_mean:.3f}, z-score {dissent.z_score:.2f})"
        if dissent is not None
        else ""
    )

    return f"{belief_clause}; {attention_clause}{evidence_clause}{dissent_clause}."


def narrate_capability(
    *,
    capability_id: str,
    baseline: CapabilityBaseline | None,
    allocation: AttentionAllocation | None = None,
    evidence_gathered: int = 0,
    dissent: DissentRecord | None = None,
) -> NarrativeEntry:
    """Build one inspectable narrative entry for a single capability."""
    uncertainty = uncertainty_from_baseline(baseline)
    familiarity = _familiarity_for(baseline)
    attended = allocation is not None
    summary = _summarize(
        capability_id=capability_id,
        familiarity=familiarity,
        uncertainty=uncertainty,
        attended=attended,
        evidence_gathered=evidence_gathered,
        dissent=dissent,
    )
    return NarrativeEntry(
        capability_id=capability_id,
        familiarity=familiarity,
        uncertainty=uncertainty,
        attended=attended,
        attention_cost=allocation.cost if allocation is not None else None,
        evidence_gathered=evidence_gathered,
        dissent=dissent,
        summary=summary,
    )


def narrate_host(
    acclimation: HostAcclimation,
    *,
    allocations: Iterable[AttentionAllocation] = (),
    evidence_counts: Mapping[str, int] | None = None,
    dissent_by_capability: Mapping[str, DissentRecord] | None = None,
) -> tuple[NarrativeEntry, ...]:
    """Build one narrative entry per capability the organism has ever
    observed, gathering v0.33's baseline, v0.38's attention allocation and
    v0.40's evidence/dissent into one inspectable account each.
    """
    allocation_by_name = {allocation.name: allocation for allocation in allocations}
    resolved_evidence_counts = evidence_counts if evidence_counts is not None else {}
    resolved_dissent = dissent_by_capability if dissent_by_capability is not None else {}
    return tuple(
        narrate_capability(
            capability_id=capability_id,
            baseline=acclimation.baseline(capability_id),
            allocation=allocation_by_name.get(capability_id),
            evidence_gathered=resolved_evidence_counts.get(capability_id, 0),
            dissent=resolved_dissent.get(capability_id),
        )
        for capability_id in acclimation.known_capabilities
    )
