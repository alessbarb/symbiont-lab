from __future__ import annotations

from dataclasses import asdict, dataclass

from .study_archive import StudyRecord


@dataclass(slots=True, frozen=True)
class CampaignProposal:
    parameter: str
    baseline: float
    variant: float
    recommended_seed_count: int
    parent_record_id: str
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class CampaignAssessment:
    root_record_id: str
    current_record_id: str
    studies: int
    status: str
    parameter: str
    repeated_conditions: int
    initial_span: float
    latest_span: float
    latest_confidence: float
    summary: str
    proposal: CampaignProposal | None

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["proposal"] = self.proposal.as_dict() if self.proposal else None
        return payload


def _study_values(record: StudyRecord) -> tuple[str, float, float, int]:
    study = record.study
    parameter = str(study.get("parameter", ""))
    baseline = float(dict(study.get("baseline", {})).get("parameter_value", 0.0))
    variant = float(dict(study.get("variant", {})).get("parameter_value", 0.0))
    seeds = tuple(study.get("seeds", ()))
    return parameter, baseline, variant, len(seeds)


def _confidence(record: StudyRecord) -> float:
    try:
        return min(1.0, max(0.0, float(record.interpretation.get("confidence", 0.0))))
    except (TypeError, ValueError):
        return 0.0


def _follow_up(record: StudyRecord) -> dict[str, object]:
    raw = record.interpretation.get("follow_up", {})
    return dict(raw) if isinstance(raw, dict) else {}


def analyze_campaign(lineage: list[StudyRecord]) -> CampaignAssessment:
    """Analyze one observer-side parent chain, newest to oldest.

    The result is research guidance only. It never feeds back into the simulated
    species and never launches a study.
    """
    if not lineage:
        raise ValueError("campaign requires at least one study record")

    newest = lineage[0]
    chronological = list(reversed(lineage))
    root = chronological[0]
    latest_parameter, latest_baseline, latest_variant, latest_seed_count = _study_values(newest)
    initial_parameter, initial_baseline, initial_variant, _ = _study_values(root)
    initial_span = abs(initial_variant - initial_baseline)
    latest_span = abs(latest_variant - latest_baseline)
    latest_confidence = _confidence(newest)

    signatures = [_study_values(record)[:3] for record in chronological]
    latest_signature = signatures[-1]
    repeated_conditions = sum(signature == latest_signature for signature in signatures)
    same_parameter = all(signature[0] == latest_parameter for signature in signatures)

    spans = [abs(variant - baseline) for _, baseline, variant in signatures]
    nonincreasing_span = all(
        later <= earlier + 1e-12 for earlier, later in zip(spans, spans[1:])
    )
    weak_tail = [
        str(record.interpretation.get("summary", "")).startswith("No strong paired effect")
        for record in chronological[-3:]
    ]

    status = "continue"
    summary = "The research line has useful evidence but has not converged yet."
    proposal: CampaignProposal | None = None

    if len(lineage) >= 3 and same_parameter and nonincreasing_span and latest_confidence >= 0.70:
        convergence_limit = max(initial_span * 0.30, 0.01)
        if latest_span <= convergence_limit:
            status = "converged"
            summary = (
                f"The {latest_parameter} line has narrowed from a span of {initial_span:.4f} "
                f"to {latest_span:.4f} with high observer confidence. Treat this line as converged "
                "unless a new hypothesis justifies reopening it."
            )

    if status != "converged" and repeated_conditions >= 2:
        if latest_confidence < 0.70:
            status = "increase_evidence"
            summary = (
                "The same comparison has been repeated without enough confidence. Increase paired seeds "
                "instead of changing the synthetic condition again."
            )
            proposal = CampaignProposal(
                parameter=latest_parameter,
                baseline=latest_baseline,
                variant=latest_variant,
                recommended_seed_count=max(latest_seed_count * 2, 10),
                parent_record_id=newest.record_id,
                rationale=summary,
            )
        else:
            status = "stalled"
            summary = (
                "The campaign is repeating an already well-supported comparison. Do not run the same "
                "condition again; use the observer follow-up or close this line."
            )

    if (
        status == "continue"
        and len(weak_tail) == 3
        and all(weak_tail)
        and same_parameter
    ):
        status = "no_robust_effect"
        summary = (
            f"Three consecutive {latest_parameter} studies show no strong paired effect. "
            "This line is not producing useful discrimination; close it or start a new hypothesis "
            "rather than escalating synthetic stress indefinitely."
        )

    if status == "continue":
        follow = _follow_up(newest)
        try:
            proposal = CampaignProposal(
                parameter=str(follow.get("parameter") or latest_parameter),
                baseline=float(follow.get("baseline", latest_baseline)),
                variant=float(follow.get("variant", latest_variant)),
                recommended_seed_count=max(
                    int(follow.get("recommended_seed_count", latest_seed_count or 1)),
                    latest_seed_count or 1,
                ),
                parent_record_id=newest.record_id,
                rationale=str(follow.get("rationale") or summary),
            )
        except (TypeError, ValueError):
            proposal = None

    if len(lineage) == 1 and status == "continue":
        summary = "This is the first study in the line; one follow-up is needed before campaign trends exist."

    return CampaignAssessment(
        root_record_id=root.record_id,
        current_record_id=newest.record_id,
        studies=len(lineage),
        status=status,
        parameter=latest_parameter or initial_parameter,
        repeated_conditions=repeated_conditions,
        initial_span=initial_span,
        latest_span=latest_span,
        latest_confidence=latest_confidence,
        summary=summary,
        proposal=proposal,
    )
