"""Core re-embodiment semantics independent of any simulator."""
from __future__ import annotations

from dataclasses import dataclass

from .contract import EmbodimentContract
from .episode import EmbodimentEndReason, EmbodimentEpisode
from .memory import BodySpecificMemory, EmbodimentArchive


@dataclass(frozen=True, slots=True)
class ReembodimentPrior:
    relation: str
    body_memory: BodySpecificMemory | None
    same_contract_memories: tuple[BodySpecificMemory, ...]


def select_prior(
    archive: EmbodimentArchive,
    *,
    body_id: str,
    contract_fingerprint: str,
) -> ReembodimentPrior:
    exact = archive.for_body(body_id)
    same_contract = archive.for_contract(contract_fingerprint)
    if exact is not None:
        relation = "same-body"
    elif same_contract:
        relation = "same-contract"
    else:
        relation = "novel"
    return ReembodimentPrior(
        relation=relation,
        body_memory=exact,
        same_contract_memories=same_contract,
    )


def begin_reembodiment(
    *,
    symbiont_id: str,
    body_id: str,
    epoch: int,
    symbiont_tick: int,
    contract: EmbodimentContract,
    archive: EmbodimentArchive,
) -> tuple[EmbodimentEpisode, ReembodimentPrior]:
    prior = select_prior(
        archive,
        body_id=body_id,
        contract_fingerprint=contract.contract_fingerprint,
    )
    # Priors are deliberately not installed as factual episode state here.
    # Adapters may expose them to hypothesis/candidate machinery only.
    episode = EmbodimentEpisode.begin(
        symbiont_id=symbiont_id,
        body_id=body_id,
        epoch=epoch,
        start_symbiont_tick=symbiont_tick,
        contract=contract,
    )
    return episode, prior


def replace_body(
    current: EmbodimentEpisode,
    *,
    symbiont_tick: int,
    new_body_id: str,
    new_contract: EmbodimentContract,
    archive: EmbodimentArchive,
) -> tuple[EmbodimentEpisode, ReembodimentPrior]:
    current.close(
        symbiont_tick=symbiont_tick,
        reason=EmbodimentEndReason.BODY_REPLACED,
    )
    return begin_reembodiment(
        symbiont_id=current.symbiont_id,
        body_id=new_body_id,
        epoch=current.epoch + 1,
        symbiont_tick=symbiont_tick,
        contract=new_contract,
        archive=archive,
    )


__all__ = [
    "ReembodimentPrior",
    "begin_reembodiment",
    "replace_body",
    "select_prior",
]
