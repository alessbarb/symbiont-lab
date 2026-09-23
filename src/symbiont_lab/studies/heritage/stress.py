from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import mean

from symbiont.core.collective import CollectiveMemory
from symbiont.core.heritage import HeritagePattern, SpeciesHeritage, apply_heritage, distill_heritage
from symbiont.core.model import fingerprint
from symbiont.simulation import EventContext, SimulationResult, _run_population, run_simulation


@dataclass(slots=True, frozen=True)
class HeritageStressCondition:
    name: str
    inherited_patterns: int
    world_digest: str
    attention_recall: float | None
    attention_precision: float | None
    attention_false_positive_rate: float | None
    classification_recall: float | None
    classification_precision: float | None
    classification_false_positive_rate: float | None
    calibration_error: float
    brier_score: float
    high_confidence_miss_rate: float
    observed_prior_patterns: int
    prior_mae: float | None
    live_mae: float | None
    combined_mae: float | None
    correction_gain: float | None
    live_override_rate: float | None
    exported_patterns: int
    reexported_patterns: int
    direction_flips: int
    evaluable_reexports: int
    improved_reexports: int
    worsened_reexports: int
    mean_reexport_mae_gain: float | None
    reexport_rate: float | None

    @property
    def corrected_reexports(self) -> int:
        """Legacy alias: historically this counted threshold-direction flips."""
        return self.direction_flips

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        # NOTE(legacy): Preserve the legacy serialized key so older research readers can still
        # load the record, but make its meaning explicit in the new schema.
        payload["corrected_reexports"] = self.direction_flips
        return payload


@dataclass(slots=True, frozen=True)
class HeritageStressStudy:
    source_seed: int
    target_seed: int
    source_patterns: int
    conditions: tuple[HeritageStressCondition, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source_seed": self.source_seed,
            "target_seed": self.target_seed,
            "source_patterns": self.source_patterns,
            "conditions": [condition.as_dict() for condition in self.conditions],
        }


def invert_heritage(heritage: SpeciesHeritage) -> SpeciesHeritage:
    return SpeciesHeritage(
        generation=heritage.generation,
        patterns=tuple(
            HeritagePattern(
                fingerprint=pattern.fingerprint,
                threat_probability=1.0 - pattern.threat_probability,
                certainty=pattern.certainty,
                support=pattern.support,
                source_generation=pattern.source_generation,
            )
            for pattern in heritage.patterns
        ),
    )


def misalign_heritage(heritage: SpeciesHeritage) -> SpeciesHeritage:
    """Rotate learned beliefs across fingerprints without changing support volume."""
    patterns = list(heritage.patterns)
    if len(patterns) < 2:
        return heritage
    payloads = patterns[-1:] + patterns[:-1]
    remapped = tuple(
        HeritagePattern(
            fingerprint=target.fingerprint,
            threat_probability=source.threat_probability,
            certainty=source.certainty,
            support=source.support,
            source_generation=source.source_generation,
        )
        for target, source in zip(patterns, payloads)
    )
    return SpeciesHeritage(generation=heritage.generation, patterns=remapped)


def _event_digest_update(digest, event: EventContext) -> None:
    vector = ",".join(f"{value:.12f}" for value in event.observation.vector())
    digest.update(
        (
            f"{event.step}|{event.host_index}|{event.truth_label}|{event.phase}|"
            f"{event.drift_state}|{vector}\n"
        ).encode("utf-8")
    )


def _empirical_rates(events: list[EventContext]) -> dict[str, float]:
    counts: dict[str, list[int]] = {}
    for event in events:
        fp = fingerprint(event.observation)
        pair = counts.setdefault(fp, [0, 0])
        pair[0] += 1
        pair[1] += int(event.is_threat)
    return {fp: threats / total for fp, (total, threats) in counts.items() if total}


def _mae(values: list[float]) -> float | None:
    return mean(values) if values else None


def _alignment(
    inherited: SpeciesHeritage,
    collective: CollectiveMemory,
    empirical: dict[str, float],
) -> tuple[int, float | None, float | None, float | None, float | None, float | None]:
    prior_errors: list[float] = []
    live_errors: list[float] = []
    combined_errors: list[float] = []
    overrides = 0
    override_candidates = 0

    for pattern in inherited.patterns:
        target = empirical.get(pattern.fingerprint)
        if target is None:
            continue
        prior_errors.append(abs(pattern.threat_probability - target))
        live_probability, live_certainty = collective.live_belief(pattern.fingerprint)
        combined_probability, _ = collective.belief(pattern.fingerprint)
        if live_certainty > 0:
            live_errors.append(abs(live_probability - target))
        combined_errors.append(abs(combined_probability - target))

        if live_certainty >= 0.30 and abs(pattern.threat_probability - 0.5) >= 0.05:
            override_candidates += 1
            overrides += int(
                (live_probability >= 0.5) != (pattern.threat_probability >= 0.5)
            )

    prior_mae = _mae(prior_errors)
    combined_mae = _mae(combined_errors)
    correction_gain = (
        prior_mae - combined_mae
        if prior_mae is not None and combined_mae is not None
        else None
    )
    return (
        len(prior_errors),
        prior_mae,
        _mae(live_errors),
        combined_mae,
        overrides / override_candidates if override_candidates else None,
        correction_gain,
    )


def _run_condition(
    *,
    name: str,
    heritage: SpeciesHeritage,
    target_seed: int,
    hosts: int,
    steps: int,
    threat_rate: float,
    poison_fraction: float,
    heterogeneity: float,
    drift_step: int | None,
    drift_fraction: float,
    drift_magnitude: float,
    heritage_limit: int,
) -> HeritageStressCondition:
    collective = CollectiveMemory()
    apply_heritage(collective, heritage)
    events: list[EventContext] = []
    digest = sha256()

    def capture(event: EventContext) -> None:
        events.append(event)
        _event_digest_update(digest, event)

    result, final_collective = _run_population(
        hosts=hosts,
        steps=steps,
        seed=target_seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
        collective=collective,
        on_event=capture,
    )
    empirical = _empirical_rates(events)
    (
        observed_prior_patterns,
        prior_mae,
        live_mae,
        combined_mae,
        live_override_rate,
        correction_gain,
    ) = _alignment(heritage, final_collective, empirical)

    exported = distill_heritage(
        final_collective,
        generation=max(1, heritage.generation + 1),
        max_patterns=heritage_limit,
    )
    initial = {pattern.fingerprint: pattern for pattern in heritage.patterns}
    reexported = [pattern for pattern in exported.patterns if pattern.fingerprint in initial]
    direction_flips = sum(
        (pattern.threat_probability >= 0.5)
        != (initial[pattern.fingerprint].threat_probability >= 0.5)
        for pattern in reexported
    )

    reexport_gains: list[float] = []
    improved_reexports = 0
    worsened_reexports = 0
    for pattern in reexported:
        target = empirical.get(pattern.fingerprint)
        if target is None:
            continue
        old_error = abs(initial[pattern.fingerprint].threat_probability - target)
        new_error = abs(pattern.threat_probability - target)
        gain = old_error - new_error
        reexport_gains.append(gain)
        if gain > 1e-12:
            improved_reexports += 1
        elif gain < -1e-12:
            worsened_reexports += 1

    return HeritageStressCondition(
        name=name,
        inherited_patterns=len(heritage.patterns),
        world_digest=digest.hexdigest(),
        attention_recall=result.attention_recall,
        attention_precision=result.attention_precision,
        attention_false_positive_rate=result.attention_false_positive_rate,
        classification_recall=result.classification_recall,
        classification_precision=result.classification_precision,
        classification_false_positive_rate=result.classification_false_positive_rate,
        calibration_error=result.calibration_error,
        brier_score=result.brier_score,
        high_confidence_miss_rate=result.high_confidence_miss_rate,
        observed_prior_patterns=observed_prior_patterns,
        prior_mae=prior_mae,
        live_mae=live_mae,
        combined_mae=combined_mae,
        correction_gain=correction_gain,
        live_override_rate=live_override_rate,
        exported_patterns=len(exported.patterns),
        reexported_patterns=len(reexported),
        direction_flips=direction_flips,
        evaluable_reexports=len(reexport_gains),
        improved_reexports=improved_reexports,
        worsened_reexports=worsened_reexports,
        mean_reexport_mae_gain=_mae(reexport_gains),
        reexport_rate=(len(reexported) / len(heritage.patterns)) if heritage.patterns else None,
    )


def run_heritage_stress_study(
    *,
    source_seed: int = 7,
    target_seed: int = 1016,
    hosts: int = 100,
    steps: int = 300,
    threat_rate: float = 0.018,
    poison_fraction: float = 0.08,
    heterogeneity: float = 0.12,
    drift_step: int | None = None,
    drift_fraction: float = 0.35,
    drift_magnitude: float = 0.22,
    heritage_limit: int = 24,
) -> HeritageStressStudy:
    _, source_collective = run_simulation(
        hosts=hosts,
        steps=steps,
        seed=source_seed,
        threat_rate=threat_rate,
        poison_fraction=poison_fraction,
        heterogeneity=heterogeneity,
        drift_step=drift_step,
        drift_fraction=drift_fraction,
        drift_magnitude=drift_magnitude,
    )
    learned = distill_heritage(
        source_collective,
        generation=1,
        max_patterns=heritage_limit,
    )
    conditions = (
        ("naive", SpeciesHeritage(generation=1)),
        ("learned", learned),
        ("inverted", invert_heritage(learned)),
        ("misaligned", misalign_heritage(learned)),
    )
    results = tuple(
        _run_condition(
            name=name,
            heritage=heritage,
            target_seed=target_seed,
            hosts=hosts,
            steps=steps,
            threat_rate=threat_rate,
            poison_fraction=poison_fraction,
            heterogeneity=heterogeneity,
            drift_step=drift_step,
            drift_fraction=drift_fraction,
            drift_magnitude=drift_magnitude,
            heritage_limit=heritage_limit,
        )
        for name, heritage in conditions
    )
    digests = {condition.world_digest for condition in results}
    if len(digests) != 1:
        raise RuntimeError("heritage conditions did not receive the same synthetic target world")
    return HeritageStressStudy(
        source_seed=source_seed,
        target_seed=target_seed,
        source_patterns=len(learned.patterns),
        conditions=results,
    )
