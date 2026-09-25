"""Evaluator-only longitudinal adaptation of local social evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime

from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeAdaptationStudy:
    initial_choice: str
    revised_choice: str
    final_valence: str
    evidence_observations: int
    changed_after_contradiction: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_adaptation_study() -> SocialRuntimeAdaptationStudy:
    """Show reversible choice after contradictory local evidence.

    The harness injects only bounded aggregate outcomes into the runtime-owned
    ledger. It does not set a preferred peer or return the study labels.
    """
    habitat = SocialHabitat(EcologicalResourcePool({"food": 4.0}))
    for member in ("observer", "candidate", "unknown"):
        habitat.admit(member)
    runtime = OrganismRuntime(organism_id="observer", social_habitat=habitat)
    runtime.social_ledger.observe("observer", "candidate", benefit=4.0, tick=0)
    initial = runtime.select_social_opportunity()
    # A later contradictory outcome outweighs the earlier support while the
    # unknown channel remains available for renewed evidence gathering.
    runtime.social_ledger.observe("observer", "candidate", cost=8.0, conflict=True, tick=1)
    revised = runtime.select_social_opportunity()
    relation = next(
        item for item in runtime.social_ledger.relations if item.target_id == "candidate"
    )
    return SocialRuntimeAdaptationStudy(
        initial_choice=initial.target_id if initial else "none",
        revised_choice=revised.target_id if revised else "none",
        final_valence=relation.valence.value,
        evidence_observations=relation.observations,
        changed_after_contradiction=(
            initial is not None and revised is not None and initial.target_id != revised.target_id
        ),
    )


__all__ = ["SocialRuntimeAdaptationStudy", "run_social_runtime_adaptation_study"]
