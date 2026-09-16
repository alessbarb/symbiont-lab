"""Evaluator-only study of local adaptation to opaque resource availability."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from symbiont.core.interactions import EcologicalResourcePool
from symbiont.core.runtime import OrganismRuntime
from symbiont.core.social import SocialHabitat


@dataclass(frozen=True, slots=True)
class SocialRuntimeResourceAdaptationStudy:
    initial_resource: str
    adapted_resource: str
    checkpoint_replay_equal: bool
    denied_initial_request: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_social_runtime_resource_adaptation_study() -> SocialRuntimeResourceAdaptationStudy:
    """Measure resource selection after one local availability surprise.

    The harness exposes only opaque tokens and finite inventory. It does not
    tell the runtime which token is useful or assign a social role/objective.
    """
    habitat = SocialHabitat(EcologicalResourcePool({"food": 0.0, "water": 2.0}))
    habitat.admit("observer")
    habitat.admit("peer")
    runtime = OrganismRuntime(
        organism_id="observer", social_habitat=habitat, social_exchange_quantum=0.5
    )
    first = runtime.autonomous_social_step()
    if first is None:
        raise AssertionError("resource adaptation study produced no initial request")
    checkpoint = runtime.checkpoint()
    restored = OrganismRuntime.from_checkpoint(checkpoint, social_habitat=habitat)
    replay_equal = restored.social_resource_ledger.evidence == runtime.social_resource_ledger.evidence
    second = restored.autonomous_social_step()
    if second is None:
        raise AssertionError("resource adaptation study produced no adapted request")
    return SocialRuntimeResourceAdaptationStudy(
        initial_resource=first.resource,
        adapted_resource=second.resource,
        checkpoint_replay_equal=replay_equal,
        denied_initial_request=first.granted == 0.0,
    )


__all__ = [
    "SocialRuntimeResourceAdaptationStudy",
    "run_social_runtime_resource_adaptation_study",
]
