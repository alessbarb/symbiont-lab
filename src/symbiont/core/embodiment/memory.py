"""Bounded longitudinal memory for bodies and embodiment episodes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Mapping

from .history import EmbodimentEpisodeSummary


@dataclass(slots=True)
class BodySpecificMemory:
    body_id: str
    contract_fingerprint: str
    last_embodiment_id: str
    body_schema_prior: dict[str, object] | None = None
    dynamics_prior: dict[str, object] | None = None
    embodied_competence_priors: dict[str, object] | None = None
    historical_causal_state: dict[str, object] | None = None

    def checkpoint(self) -> dict[str, object]:
        return {
            "body_id": self.body_id,
            "contract_fingerprint": self.contract_fingerprint,
            "last_embodiment_id": self.last_embodiment_id,
            "body_schema_prior": deepcopy(self.body_schema_prior),
            "dynamics_prior": deepcopy(self.dynamics_prior),
            "embodied_competence_priors": deepcopy(self.embodied_competence_priors),
            "historical_causal_state": deepcopy(self.historical_causal_state),
        }


class EmbodimentArchive:
    """Bounded history indexed independently by embodiment, body and contract."""

    SCHEMA_VERSION = 2

    def __init__(
        self,
        *,
        max_body_memories: int = 16,
        max_summaries: int = 32,
    ) -> None:
        self.max_body_memories = int(max_body_memories)
        self.max_summaries = int(max_summaries)
        if self.max_body_memories < 1 or self.max_summaries < 1:
            raise ValueError("embodiment archive bounds must be positive")
        self._body_memories: list[BodySpecificMemory] = []
        self._summaries: list[EmbodimentEpisodeSummary] = []

    def remember_body(self, memory: BodySpecificMemory) -> None:
        self._body_memories = [
            item for item in self._body_memories if item.body_id != memory.body_id
        ]
        self._body_memories.append(memory)
        self._body_memories = self._body_memories[-self.max_body_memories :]

    def append_summary(self, summary: EmbodimentEpisodeSummary) -> None:
        self._summaries = [
            item
            for item in self._summaries
            if item.embodiment_id != summary.embodiment_id
        ]
        self._summaries.append(summary)
        self._summaries = self._summaries[-self.max_summaries :]

    def for_body(self, body_id: str) -> BodySpecificMemory | None:
        for item in reversed(self._body_memories):
            if item.body_id == body_id:
                return item
        return None

    def for_contract(self, contract_fingerprint: str) -> tuple[BodySpecificMemory, ...]:
        return tuple(
            item
            for item in reversed(self._body_memories)
            if item.contract_fingerprint == contract_fingerprint
        )

    @property
    def summaries(self) -> tuple[EmbodimentEpisodeSummary, ...]:
        return tuple(self._summaries)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "max_body_memories": self.max_body_memories,
            "max_summaries": self.max_summaries,
            "body_memories": [item.checkpoint() for item in self._body_memories],
            "summaries": [item.checkpoint() for item in self._summaries],
        }

    @classmethod
    def restore(cls, payload: Mapping[str, object] | None) -> "EmbodimentArchive":
        if payload is None:
            return cls()
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported embodiment archive")
        obj = cls(
            max_body_memories=int(payload.get("max_body_memories", 16)),
            max_summaries=int(payload.get("max_summaries", 32)),
        )
        raw_memories = payload.get("body_memories", [])
        raw_summaries = payload.get("summaries", [])
        if (
            not isinstance(raw_memories, list)
            or len(raw_memories) > obj.max_body_memories
            or not isinstance(raw_summaries, list)
            or len(raw_summaries) > obj.max_summaries
        ):
            raise ValueError("invalid or unbounded embodiment archive")
        for entry in raw_memories:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid body-specific memory")
            obj._body_memories.append(
                BodySpecificMemory(
                    body_id=str(entry["body_id"]),
                    contract_fingerprint=str(entry["contract_fingerprint"]),
                    last_embodiment_id=str(entry["last_embodiment_id"]),
                    body_schema_prior=deepcopy(entry.get("body_schema_prior")),
                    dynamics_prior=deepcopy(entry.get("dynamics_prior")),
                    embodied_competence_priors=deepcopy(
                        entry.get("embodied_competence_priors")
                    ),
                    historical_causal_state=deepcopy(
                        entry.get("historical_causal_state")
                    ),
                )
            )
        for entry in raw_summaries:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid embodiment summary")
            obj._summaries.append(EmbodimentEpisodeSummary.restore(entry))
        return obj


__all__ = ["BodySpecificMemory", "EmbodimentArchive"]
