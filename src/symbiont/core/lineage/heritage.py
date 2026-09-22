from __future__ import annotations

from dataclasses import asdict, dataclass

from ..social.collective import CollectiveMemory


@dataclass(slots=True, frozen=True)
class HeritagePattern:
    fingerprint: str
    threat_probability: float
    certainty: float
    support: int
    source_generation: int

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class SpeciesHeritage:
    generation: int
    patterns: tuple[HeritagePattern, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "generation": self.generation,
            "patterns": [pattern.as_dict() for pattern in self.patterns],
        }


def apply_heritage(collective: CollectiveMemory, heritage: SpeciesHeritage | None) -> None:
    """Install inherited priors without creating reporters, trust or host memory."""
    if heritage is None:
        return
    for pattern in heritage.patterns:
        collective.inherit(
            pattern.fingerprint,
            pattern.threat_probability,
            pattern.certainty,
            generation=pattern.source_generation,
            support=pattern.support,
        )


def distill_heritage(
    collective: CollectiveMemory,
    *,
    generation: int,
    max_patterns: int = 24,
    min_reports: int = 6,
    min_sources: int = 4,
    min_certainty: float = 0.68,
    min_separation: float = 0.20,
) -> SpeciesHeritage:
    """Compress current-generation live evidence into weak inheritable priors.

    Existing inherited priors alone cannot be re-exported. A pattern must earn
    fresh current-generation reports and source diversity before it can survive.
    """
    candidates: list[tuple[float, HeritagePattern]] = []
    for fingerprint, evidence in collective.patterns.items():
        if evidence.reports < min_reports or len(evidence.votes) < min_sources:
            continue
        probability, certainty = collective.live_belief(fingerprint)
        separation = abs(probability - 0.5)
        if certainty < min_certainty or separation < min_separation:
            continue

        inherited_certainty = min(0.55, 0.25 + 0.35 * certainty)
        pattern = HeritagePattern(
            fingerprint=fingerprint,
            threat_probability=probability,
            certainty=inherited_certainty,
            support=evidence.reports,
            source_generation=max(0, generation),
        )
        report_strength = min(1.0, evidence.reports / 20.0)
        score = certainty * report_strength * min(1.0, separation * 2.0)
        candidates.append((score, pattern))

    candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1].support,
            item[1].fingerprint,
        )
    )
    limit = max(0, int(max_patterns))
    return SpeciesHeritage(
        generation=max(0, generation),
        patterns=tuple(pattern for _, pattern in candidates[:limit]),
    )
