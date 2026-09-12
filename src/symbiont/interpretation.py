from __future__ import annotations

from dataclasses import asdict, dataclass

from .study import COMPARABLE_PARAMETERS, METRICS, StudyResult


_DESIRED_DIRECTION: dict[str, int] = {
    "detection_rate": 1,
    "precision": 1,
    "false_positive_rate": -1,
    "calibration_error": -1,
    "blind_spot_rate": -1,
    "recent_drift_false_positive_rate": -1,
}

_MEANINGFUL_DELTA: dict[str, float] = {
    "detection_rate": 0.01,
    "precision": 0.01,
    "false_positive_rate": 0.005,
    "calibration_error": 0.01,
    "blind_spot_rate": 0.01,
    "recent_drift_false_positive_rate": 0.01,
    "top_probe_utility": 0.02,
    "self_confidence": 0.02,
    "epistemic_pressure": 0.02,
}


@dataclass(slots=True, frozen=True)
class StudyFinding:
    metric: str
    delta: float
    direction_agreement: float
    effect_ratio: float
    classification: str
    evidence: str
    text: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class FollowUpStudy:
    parameter: str
    baseline: float
    variant: float
    recommended_seed_count: int
    rationale: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class StudyInterpretation:
    summary: str
    confidence: float
    findings: tuple[StudyFinding, ...]
    follow_up: FollowUpStudy

    def as_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "confidence": self.confidence,
            "findings": [finding.as_dict() for finding in self.findings],
            "follow_up": self.follow_up.as_dict(),
        }


def _effect_ratio(delta: float, stdev: float, threshold: float) -> float:
    denominator = max(stdev, threshold / 2.0, 1e-9)
    return min(9.99, abs(delta) / denominator)


def _evidence(delta: float, agreement: float, effect_ratio: float, threshold: float) -> str:
    if abs(delta) < threshold:
        return "weak"
    if agreement >= 0.80 and effect_ratio >= 0.75:
        return "strong"
    if agreement >= 0.65 and effect_ratio >= 0.45:
        return "moderate"
    return "weak"


def _classification(metric: str, delta: float, threshold: float) -> str:
    if abs(delta) < threshold:
        return "stable"
    desired = _DESIRED_DIRECTION.get(metric)
    if desired is None:
        return "increased" if delta > 0 else "decreased"
    return "improved" if delta * desired > 0 else "worsened"


def _finding_text(metric: str, delta: float, agreement: float, classification: str) -> str:
    points = abs(delta) * 100.0
    direction = "rose" if delta > 0 else "fell"
    if classification == "stable":
        return f"{metric} stayed effectively stable across the paired seeds."
    if classification in {"improved", "worsened"}:
        return (
            f"{metric} {classification} by {points:.2f} percentage points on average; "
            f"{agreement:.0%} of paired seeds moved in the same direction."
        )
    return (
        f"{metric} {direction} by {points:.2f} percentage points on average; "
        f"{agreement:.0%} of paired seeds moved in the same direction."
    )


def _follow_up(study: StudyResult, findings: tuple[StudyFinding, ...]) -> FollowUpStudy:
    baseline = study.baseline.parameter_value
    variant = study.variant.parameter_value
    strong = [finding for finding in findings if finding.evidence == "strong" and finding.classification != "stable"]
    moderate = [finding for finding in findings if finding.evidence == "moderate" and finding.classification != "stable"]
    seed_count = len(study.seeds)

    if strong and abs(variant - baseline) > 1e-12:
        midpoint = baseline + (variant - baseline) / 2.0
        rationale = (
            "A consistent effect is already visible. Test the midpoint next to locate where the effect begins "
            "instead of increasing complexity immediately."
        )
        return FollowUpStudy(
            parameter=study.parameter,
            baseline=baseline,
            variant=midpoint,
            recommended_seed_count=max(seed_count, 7),
            rationale=rationale,
        )

    if moderate:
        return FollowUpStudy(
            parameter=study.parameter,
            baseline=baseline,
            variant=variant,
            recommended_seed_count=max(seed_count * 2, 10),
            rationale=(
                "The effect is suggestive but not yet consistent enough. Repeat the same comparison with more "
                "paired seeds before changing another subsystem."
            ),
        )

    low, high = COMPARABLE_PARAMETERS[study.parameter]
    direction = variant - baseline
    if abs(direction) < 1e-12:
        direction = max((high - low) * 0.10, 0.01)
    candidate = baseline + direction * 1.5
    candidate = min(high, max(low, candidate))
    if abs(candidate - baseline) < 1e-12:
        candidate = min(high, baseline + max((high - low) * 0.10, 0.01))
    return FollowUpStudy(
        parameter=study.parameter,
        baseline=baseline,
        variant=candidate,
        recommended_seed_count=max(seed_count * 2, 10),
        rationale=(
            "No robust effect is visible yet. Increase the synthetic stress modestly and use more paired seeds "
            "before concluding that the parameter is irrelevant."
        ),
    )


def interpret_study(study: StudyResult) -> StudyInterpretation:
    findings: list[StudyFinding] = []
    for metric in METRICS:
        paired = study.paired_deltas[metric]
        threshold = _MEANINGFUL_DELTA[metric]
        effect_ratio = _effect_ratio(paired.mean, paired.stdev, threshold)
        evidence = _evidence(paired.mean, paired.direction_agreement, effect_ratio, threshold)
        classification = _classification(metric, paired.mean, threshold)
        findings.append(
            StudyFinding(
                metric=metric,
                delta=paired.mean,
                direction_agreement=paired.direction_agreement,
                effect_ratio=effect_ratio,
                classification=classification,
                evidence=evidence,
                text=_finding_text(metric, paired.mean, paired.direction_agreement, classification),
            )
        )

    evidence_rank = {"strong": 0, "moderate": 1, "weak": 2}
    findings.sort(key=lambda finding: (evidence_rank[finding.evidence], -abs(finding.delta), finding.metric))
    finding_tuple = tuple(findings)

    strong = [finding for finding in finding_tuple if finding.evidence == "strong" and finding.classification != "stable"]
    strong_harm = [finding.metric for finding in strong if finding.classification == "worsened"]
    strong_gain = [finding.metric for finding in strong if finding.classification == "improved"]
    strong_shift = [finding.metric for finding in strong if finding.classification in {"increased", "decreased"}]

    if strong_harm:
        summary = "The variant consistently worsened " + ", ".join(strong_harm[:3]) + "."
    elif strong_gain:
        summary = "The variant consistently improved " + ", ".join(strong_gain[:3]) + "."
    elif strong_shift:
        summary = "The variant produced a consistent cognitive-state shift in " + ", ".join(strong_shift[:3]) + "."
    else:
        summary = "No strong paired effect is established yet; treat the current result as exploratory."

    informative = [finding for finding in finding_tuple if finding.classification != "stable"]
    if informative:
        confidence = sum(
            finding.direction_agreement * min(1.0, finding.effect_ratio)
            for finding in informative[:3]
        ) / min(3, len(informative))
    else:
        confidence = 0.25

    return StudyInterpretation(
        summary=summary,
        confidence=min(1.0, max(0.0, confidence)),
        findings=finding_tuple,
        follow_up=_follow_up(study, finding_tuple),
    )
