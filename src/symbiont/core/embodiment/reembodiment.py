"""Core re-embodiment semantics independent of any simulator."""

from __future__ import annotations

from .contract import EmbodimentContract
from .episode import EmbodimentEndReason, EmbodimentEpisode
from .memory import EmbodimentArchive, EmbodimentPrior


def select_prior(
    archive: EmbodimentArchive,
    *,
    body_id: str,
    contract_fingerprint: str,
) -> EmbodimentPrior:
    return archive.prior_for(
        body_id=body_id,
        contract_fingerprint=contract_fingerprint,
    )


def begin_reembodiment(
    *,
    symbiont_id: str,
    body_id: str,
    epoch: int,
    symbiont_tick: int,
    contract: EmbodimentContract,
    archive: EmbodimentArchive,
) -> tuple[EmbodimentEpisode, EmbodimentPrior]:
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
        prior=prior,
    )
    return episode, prior


def replace_body(
    current: EmbodimentEpisode,
    *,
    symbiont_tick: int,
    new_body_id: str,
    new_contract: EmbodimentContract,
    archive: EmbodimentArchive,
) -> tuple[EmbodimentEpisode, EmbodimentPrior]:
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
    "begin_reembodiment",
    "replace_body",
    "select_prior",
]
