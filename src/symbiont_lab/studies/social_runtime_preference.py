"""Evaluator-only study of local evidence-driven social selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimePreferenceStudy:
    ticks: int
    selected_positive: int
    selected_negative: int
    selected_unknown: int
    deterministic: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_preference_study(*, ticks: int = 8) -> SocialRuntimePreferenceStudy:
    """Measure a runtime's local evidence preference without a social policy.

    The harness supplies aggregate prior evidence only; no label or objective is
    passed into the runtime.  The three channels remain available, so selecting
    a positive channel is a reversible local choice rather than enforcement.
    """
    if ticks < 1:
        raise ValueError("ticks must be positive")
    habitat = SocialHabitat(EcologicalResourcePool({"food": float(ticks * 2)}))
    for member in ("observer", "positive", "negative", "unknown"):
        habitat.admit(member)
    runtime = OrganismRuntime(organism_id="observer", social_habitat=habitat)
    runtime.social_ledger.observe("observer", "positive", benefit=4.0, tick=0)
    runtime.social_ledger.observe("observer", "negative", cost=4.0, tick=0)
    selected: list[str] = []
    for _ in range(ticks):
        opportunity = runtime.select_social_opportunity()
        if opportunity is None:
            break
        selected.append(opportunity.target_id)
    return SocialRuntimePreferenceStudy(
        ticks=ticks,
        selected_positive=selected.count("positive"),
        selected_negative=selected.count("negative"),
        selected_unknown=selected.count("unknown"),
        deterministic=selected == ["positive"] * len(selected),
    )


__all__ = ["SocialRuntimePreferenceStudy", "run_social_runtime_preference_study"]
