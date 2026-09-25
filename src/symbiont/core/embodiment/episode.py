"""Canonical persistent Embodiment episode aggregate."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import uuid
from typing import Mapping

from ...actuation.evidence import CausalEvidenceLedger
from ...actuation.model import AgencyModel, CompetenceEffectModel, ControllabilityModel
from .adaptation import EmbodimentAdaptation
from .body_schema import BodySchemaEngine
from .competence import EmbodiedCompetenceLibrary
from .contract import EmbodimentContract
from .dynamics import SensorimotorDynamicsModel
from .reachability import ReachabilityModel


class EmbodimentState(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class EmbodimentEndReason(StrEnum):
    BODY_DEATH = "body_death"
    BODY_REPLACED = "body_replaced"
    DETACHED = "detached"
    LOST = "lost"
    EXPLICIT_MIGRATION = "explicit_migration"
    UNRECOVERABLE_CONTRACT_LOSS = "unrecoverable_contract_loss"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ContractTransition:
    tick: int
    previous_fingerprint: str
    new_fingerprint: str
    reason: str


@dataclass(slots=True)
class EmbodimentEpisode:
    """One persistent biographical coupling between a Symbiont and one Body."""

    embodiment_id: str
    symbiont_id: str
    body_id: str
    epoch: int
    start_symbiont_tick: int
    contract: EmbodimentContract
    state: EmbodimentState = EmbodimentState.ACTIVE
    end_symbiont_tick: int | None = None
    embodiment_tick: int = 0
    end_reason: EmbodimentEndReason | None = None
    body_schema: BodySchemaEngine = field(default_factory=BodySchemaEngine)
    dynamics_model: SensorimotorDynamicsModel = field(
        default_factory=SensorimotorDynamicsModel
    )
    causal_evidence: CausalEvidenceLedger = field(default_factory=CausalEvidenceLedger)
    effect_model: CompetenceEffectModel = field(default_factory=CompetenceEffectModel)
    controllability_model: ControllabilityModel = field(
        default_factory=ControllabilityModel
    )
    agency_model: AgencyModel = field(default_factory=AgencyModel)
    adaptation: EmbodimentAdaptation = field(default_factory=EmbodimentAdaptation)
    reachability: ReachabilityModel = field(default_factory=ReachabilityModel)
    embodied_competences: EmbodiedCompetenceLibrary | None = None
    contract_history: list[ContractTransition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.embodiment_id or not self.symbiont_id or not self.body_id:
            raise ValueError("embodiment, symbiont and body ids must be non-empty")
        if self.epoch < 1 or self.start_symbiont_tick < 0 or self.embodiment_tick < 0:
            raise ValueError("invalid embodiment temporal coordinates")
        if self.embodied_competences is None:
            self.embodied_competences = EmbodiedCompetenceLibrary(
                embodiment_id=self.embodiment_id
            )
        elif self.embodied_competences.embodiment_id != self.embodiment_id:
            raise ValueError("embodied competence library belongs to another episode")

    @classmethod
    def begin(
        cls,
        *,
        symbiont_id: str,
        body_id: str,
        epoch: int,
        start_symbiont_tick: int,
        contract: EmbodimentContract,
        embodiment_id: str | None = None,
    ) -> "EmbodimentEpisode":
        if embodiment_id is None:
            material = (
                f"{symbiont_id}|{body_id}|{epoch}|{start_symbiont_tick}|"
                f"{uuid.uuid4().hex}"
            )
            embodiment_id = "embodiment." + hashlib.sha256(
                material.encode("utf-8")
            ).hexdigest()[:24]
        return cls(
            embodiment_id=embodiment_id,
            symbiont_id=symbiont_id,
            body_id=body_id,
            epoch=epoch,
            start_symbiont_tick=start_symbiont_tick,
            contract=contract,
        )

    @property
    def active(self) -> bool:
        return self.state is EmbodimentState.ACTIVE

    def advance(self) -> int:
        if self.state is EmbodimentState.CLOSED:
            raise RuntimeError("closed embodiment cannot advance")
        if self.state is EmbodimentState.ACTIVE:
            self.embodiment_tick += 1
        return self.embodiment_tick

    def suspend(self) -> None:
        if self.state is EmbodimentState.CLOSED:
            raise RuntimeError("closed embodiment cannot be suspended")
        self.state = EmbodimentState.SUSPENDED

    def resume(self) -> None:
        if self.state is EmbodimentState.CLOSED:
            raise RuntimeError("closed embodiment cannot resume")
        self.state = EmbodimentState.ACTIVE

    def transition_contract(
        self,
        contract: EmbodimentContract,
        *,
        reason: str,
    ) -> None:
        if self.state is EmbodimentState.CLOSED:
            raise RuntimeError("closed embodiment cannot change contract")
        previous = self.contract.contract_fingerprint
        current = contract.contract_fingerprint
        if previous == current:
            self.contract = contract
            return
        self.contract_history.append(
            ContractTransition(
                tick=self.embodiment_tick,
                previous_fingerprint=previous,
                new_fingerprint=current,
                reason=str(reason),
            )
        )
        self.contract = contract

    def close(
        self,
        *,
        symbiont_tick: int,
        reason: EmbodimentEndReason,
    ) -> None:
        if self.state is EmbodimentState.CLOSED:
            if self.end_symbiont_tick != symbiont_tick or self.end_reason is not reason:
                raise RuntimeError("closed embodiment cannot be closed differently")
            return
        if symbiont_tick < self.start_symbiont_tick:
            raise ValueError("end tick predates embodiment start")
        self.state = EmbodimentState.CLOSED
        self.end_symbiont_tick = symbiont_tick
        self.end_reason = reason

    def checkpoint(self, *, current_tick: int) -> dict[str, object]:
        assert self.embodied_competences is not None
        return {
            "schema_version": 2,
            "embodiment_id": self.embodiment_id,
            "symbiont_id": self.symbiont_id,
            "body_id": self.body_id,
            "epoch": self.epoch,
            "state": self.state.value,
            "start_symbiont_tick": self.start_symbiont_tick,
            "end_symbiont_tick": self.end_symbiont_tick,
            "embodiment_tick": self.embodiment_tick,
            "end_reason": self.end_reason.value if self.end_reason is not None else None,
            "contract": self.contract.checkpoint(),
            "contract_history": [
                {
                    "tick": item.tick,
                    "previous_fingerprint": item.previous_fingerprint,
                    "new_fingerprint": item.new_fingerprint,
                    "reason": item.reason,
                }
                for item in self.contract_history
            ],
            "body_schema": self.body_schema.export(current_tick=current_tick),
            "dynamics_model": self.dynamics_model.checkpoint(),
            "causal_evidence": self.causal_evidence.checkpoint(),
            "adaptation": self.adaptation.checkpoint(),
            "reachability": self.reachability.checkpoint(),
            "embodied_competences": self.embodied_competences.checkpoint(),
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object],
        *,
        contract: EmbodimentContract,
        body_schema: BodySchemaEngine,
        causal_evidence: CausalEvidenceLedger,
        effect_model: CompetenceEffectModel,
        controllability_model: ControllabilityModel,
        agency_model: AgencyModel,
        current_tick: int,
    ) -> "EmbodimentEpisode":
        """Restore one episode while reattaching canonical runtime services.

        BodySchema and causal inference are not duplicated here: the restored
        organism runtime remains their factual owner and the episode references
        those exact instances.
        """
        if payload.get("schema_version") != 2:
            raise ValueError("unsupported embodiment episode checkpoint")
        raw_contract = payload.get("contract")
        if not isinstance(raw_contract, Mapping):
            raise ValueError("embodiment episode contract is missing")
        persisted_fp = raw_contract.get("contract_fingerprint")
        if persisted_fp != contract.contract_fingerprint:
            raise ValueError(
                "embodiment episode contract does not match attached physical interface"
            )
        embodiment_id = str(payload.get("embodiment_id") or "")
        symbiont_id = str(payload.get("symbiont_id") or "")
        body_id = str(payload.get("body_id") or "")
        embodied = EmbodiedCompetenceLibrary.restore(
            payload.get("embodied_competences")
            if isinstance(payload.get("embodied_competences"), Mapping)
            else None,
            embodiment_id=embodiment_id,
        )
        obj = cls(
            embodiment_id=embodiment_id,
            symbiont_id=symbiont_id,
            body_id=body_id,
            epoch=int(payload.get("epoch") or 0),
            start_symbiont_tick=int(payload.get("start_symbiont_tick") or 0),
            contract=contract,
            state=EmbodimentState(str(payload.get("state") or "active")),
            end_symbiont_tick=(
                int(payload["end_symbiont_tick"])
                if payload.get("end_symbiont_tick") is not None
                else None
            ),
            embodiment_tick=int(payload.get("embodiment_tick") or 0),
            end_reason=(
                EmbodimentEndReason(str(payload["end_reason"]))
                if payload.get("end_reason") is not None
                else None
            ),
            body_schema=body_schema,
            dynamics_model=SensorimotorDynamicsModel.restore(
                payload.get("dynamics_model")
                if isinstance(payload.get("dynamics_model"), Mapping)
                else None
            ),
            causal_evidence=causal_evidence,
            effect_model=effect_model,
            controllability_model=controllability_model,
            agency_model=agency_model,
            adaptation=EmbodimentAdaptation.restore(
                payload.get("adaptation")
                if isinstance(payload.get("adaptation"), Mapping)
                else None
            ),
            reachability=ReachabilityModel.restore(
                payload.get("reachability")
                if isinstance(payload.get("reachability"), Mapping)
                else None
            ),
            embodied_competences=embodied,
        )
        raw_history = payload.get("contract_history", [])
        if not isinstance(raw_history, list):
            raise ValueError("invalid embodiment contract history")
        for item in raw_history:
            if not isinstance(item, Mapping):
                raise ValueError("invalid embodiment contract transition")
            transition = ContractTransition(
                tick=int(item["tick"]),
                previous_fingerprint=str(item["previous_fingerprint"]),
                new_fingerprint=str(item["new_fingerprint"]),
                reason=str(item["reason"]),
            )
            if transition.tick < 0 or transition.tick > obj.embodiment_tick:
                raise ValueError("embodiment contract transition tick is invalid")
            obj.contract_history.append(transition)
        if obj.state is EmbodimentState.CLOSED and obj.end_symbiont_tick is None:
            raise ValueError("closed embodiment is missing end tick")
        if obj.end_symbiont_tick is not None and obj.end_symbiont_tick > current_tick:
            raise ValueError("embodiment end tick is in the future")
        return obj


__all__ = [
    "ContractTransition",
    "EmbodimentEndReason",
    "EmbodimentEpisode",
    "EmbodimentState",
]
