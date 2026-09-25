"""Bounded longitudinal memory for bodies and embodiment episodes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Mapping

from .history import EmbodimentEpisodeSummary


@dataclass(slots=True)
class BodySpecificMemory:
    body_id: str
    contract_fingerprint: str
    last_embodiment_id: str
    body_schema_prior: dict[str, object] | None = None
    dynamics_prior: dict[str, object] | None = None
    execution_binding_priors: dict[str, object] | None = None
    historical_causal_state: dict[str, object] | None = None
    historical_motor_candidates: tuple[dict[str, object], ...] = ()
    motor_cognitive_surface: dict[str, object] | None = None
    private_model_ids: tuple[str, ...] = ()

    def checkpoint(self) -> dict[str, object]:
        return {
            "body_id": self.body_id,
            "contract_fingerprint": self.contract_fingerprint,
            "last_embodiment_id": self.last_embodiment_id,
            "body_schema_prior": deepcopy(self.body_schema_prior),
            "dynamics_prior": deepcopy(self.dynamics_prior),
            "execution_binding_priors": deepcopy(self.execution_binding_priors),
            "historical_causal_state": deepcopy(self.historical_causal_state),
            "historical_motor_candidates": [
                deepcopy(item) for item in self.historical_motor_candidates
            ],
            "motor_cognitive_surface": deepcopy(self.motor_cognitive_surface),
            "private_model_ids": list(self.private_model_ids),
        }


@dataclass(frozen=True, slots=True)
class EmbodimentPrior:
    """Historical hypothesis package; never current execution authority."""

    relation: str
    source_body_id: str | None = None
    source_embodiment_id: str | None = None
    contract_fingerprint: str | None = None
    body_schema_prior: dict[str, object] | None = None
    dynamics_prior: dict[str, object] | None = None
    execution_binding_priors: dict[str, object] | None = None
    historical_motor_candidates: tuple[dict[str, object], ...] = ()
    private_model_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.relation not in {"novel", "same-contract", "same-body"}:
            raise ValueError("invalid embodiment prior relation")

    @classmethod
    def novel(cls) -> "EmbodimentPrior":
        return cls(relation="novel")

    @classmethod
    def from_memory(
        cls,
        relation: str,
        memory: BodySpecificMemory,
    ) -> "EmbodimentPrior":
        return cls(
            relation=relation,
            source_body_id=memory.body_id,
            source_embodiment_id=memory.last_embodiment_id,
            contract_fingerprint=memory.contract_fingerprint,
            body_schema_prior=deepcopy(memory.body_schema_prior),
            dynamics_prior=deepcopy(memory.dynamics_prior),
            execution_binding_priors=deepcopy(memory.execution_binding_priors),
            historical_motor_candidates=tuple(
                deepcopy(item) for item in memory.historical_motor_candidates
            ),
            private_model_ids=tuple(memory.private_model_ids),
        )

    def checkpoint(self) -> dict[str, object]:
        return {
            "relation": self.relation,
            "authority": "hypothesis_only",
            "source_body_id": self.source_body_id,
            "source_embodiment_id": self.source_embodiment_id,
            "contract_fingerprint": self.contract_fingerprint,
            "body_schema_prior": deepcopy(self.body_schema_prior),
            "dynamics_prior": deepcopy(self.dynamics_prior),
            "execution_binding_priors": deepcopy(self.execution_binding_priors),
            "historical_motor_candidates": [
                deepcopy(item) for item in self.historical_motor_candidates
            ],
            "private_model_ids": list(self.private_model_ids),
        }

    @classmethod
    def restore(
        cls,
        payload: Mapping[str, object] | None,
    ) -> "EmbodimentPrior":
        if payload is None:
            return cls.novel()
        if payload.get("authority") not in {None, "hypothesis_only"}:
            raise ValueError("embodiment prior cannot carry authority")
        candidates = payload.get("historical_motor_candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("invalid embodiment historical candidates")
        private_ids = payload.get("private_model_ids", [])
        if not isinstance(private_ids, list):
            raise ValueError("invalid embodiment prior model ids")
        return cls(
            relation=str(payload.get("relation") or "novel"),
            source_body_id=(
                str(payload["source_body_id"])
                if payload.get("source_body_id") is not None
                else None
            ),
            source_embodiment_id=(
                str(payload["source_embodiment_id"])
                if payload.get("source_embodiment_id") is not None
                else None
            ),
            contract_fingerprint=(
                str(payload["contract_fingerprint"])
                if payload.get("contract_fingerprint") is not None
                else None
            ),
            body_schema_prior=deepcopy(payload.get("body_schema_prior")),
            dynamics_prior=deepcopy(payload.get("dynamics_prior")),
            execution_binding_priors=deepcopy(payload.get("execution_binding_priors")),
            historical_motor_candidates=tuple(
                deepcopy(dict(item)) for item in candidates if isinstance(item, Mapping)
            ),
            private_model_ids=tuple(str(value) for value in private_ids),
        )


class EmbodimentArchive:
    """Bounded history indexed independently by embodiment, body and contract."""

    SCHEMA_VERSION = 3

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
            item for item in self._summaries if item.embodiment_id != summary.embodiment_id
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

    def prior_for(
        self,
        *,
        body_id: str,
        contract_fingerprint: str,
    ) -> EmbodimentPrior:
        exact = self.for_body(body_id)
        if exact is not None:
            return EmbodimentPrior.from_memory("same-body", exact)
        compatible = self.for_contract(contract_fingerprint)
        if compatible:
            return EmbodimentPrior.from_memory(
                "same-contract",
                compatible[0],
            )
        return EmbodimentPrior.novel()

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
        archive_schema = int(payload.get("schema_version") or 0)
        if archive_schema not in {2, cls.SCHEMA_VERSION}:
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
            raw_candidates = entry.get("historical_motor_candidates", [])
            raw_private_ids = entry.get("private_model_ids", [])
            if not isinstance(raw_candidates, list):
                raise ValueError("invalid historical motor candidates")
            if not isinstance(raw_private_ids, list):
                raise ValueError("invalid private model ids")
            obj._body_memories.append(
                BodySpecificMemory(
                    body_id=str(entry["body_id"]),
                    contract_fingerprint=str(entry["contract_fingerprint"]),
                    last_embodiment_id=str(entry["last_embodiment_id"]),
                    body_schema_prior=deepcopy(entry.get("body_schema_prior")),
                    dynamics_prior=deepcopy(entry.get("dynamics_prior")),
                    execution_binding_priors=deepcopy(
                        entry.get(
                            "execution_binding_priors",
                            entry.get("embodied_competence_priors"),
                        )
                    ),
                    historical_causal_state=deepcopy(entry.get("historical_causal_state")),
                    historical_motor_candidates=tuple(
                        deepcopy(dict(item)) for item in raw_candidates if isinstance(item, Mapping)
                    ),
                    motor_cognitive_surface=deepcopy(entry.get("motor_cognitive_surface")),
                    private_model_ids=tuple(str(value) for value in raw_private_ids),
                )
            )
        for entry in raw_summaries:
            if not isinstance(entry, Mapping):
                raise ValueError("invalid embodiment summary")
            obj._summaries.append(EmbodimentEpisodeSummary.restore(entry))
        return obj


def archive_episode_checkpoint(
    archive: EmbodimentArchive,
    episode_payload: Mapping[str, object],
    *,
    body_schema_prior: Mapping[str, object] | None,
    living_body: Mapping[str, object] | None,
    symbiont_tick: int,
    end_reason: str,
    historical_motor_candidates: tuple[Mapping[str, object], ...] = (),
    motor_cognitive_surface: Mapping[str, object] | None = None,
    private_model_ids: tuple[str, ...] = (),
) -> EmbodimentEpisodeSummary:
    """Close one persisted episode into bounded longitudinal memory.

    This helper works on checkpoint data so re-embodiment can archive the old
    body before the new physical adapter exists. Historical state remains a
    prior; this function grants no current execution authority.
    """
    if int(episode_payload.get("schema_version") or 0) not in {2, 3}:
        raise ValueError("unsupported embodiment episode checkpoint")
    contract = episode_payload.get("contract")
    contract = contract if isinstance(contract, Mapping) else {}
    contract_fp = str(contract.get("contract_fingerprint") or "")
    if not contract_fp:
        raise ValueError("episode checkpoint lacks contract fingerprint")
    body_id = str(episode_payload.get("body_id") or "")
    embodiment_id = str(episode_payload.get("embodiment_id") or "")
    symbiont_id = str(episode_payload.get("symbiont_id") or "")
    if not body_id or not embodiment_id or not symbiont_id:
        raise ValueError("episode checkpoint lacks canonical identities")

    archive.remember_body(
        BodySpecificMemory(
            body_id=body_id,
            contract_fingerprint=contract_fp,
            last_embodiment_id=embodiment_id,
            body_schema_prior=deepcopy(dict(body_schema_prior))
            if isinstance(body_schema_prior, Mapping)
            else None,
            dynamics_prior=deepcopy(episode_payload.get("dynamics_model"))
            if isinstance(episode_payload.get("dynamics_model"), Mapping)
            else None,
            execution_binding_priors=deepcopy(
                episode_payload.get("execution_bindings")
                if isinstance(episode_payload.get("execution_bindings"), Mapping)
                else episode_payload.get("embodied_competences")
            )
            if isinstance(
                episode_payload.get("execution_bindings")
                if episode_payload.get("execution_bindings") is not None
                else episode_payload.get("embodied_competences"),
                Mapping,
            )
            else None,
            historical_causal_state=deepcopy(episode_payload.get("causal_evidence"))
            if isinstance(episode_payload.get("causal_evidence"), Mapping)
            else None,
            historical_motor_candidates=tuple(
                deepcopy(dict(item)) for item in historical_motor_candidates
            ),
            motor_cognitive_surface=(
                deepcopy(dict(motor_cognitive_surface))
                if isinstance(motor_cognitive_surface, Mapping)
                else None
            ),
            private_model_ids=tuple(str(value) for value in private_model_ids),
        )
    )

    adaptation = episode_payload.get("adaptation")
    adaptation = adaptation if isinstance(adaptation, Mapping) else {}
    schema = body_schema_prior if isinstance(body_schema_prior, Mapping) else {}
    body = living_body if isinstance(living_body, Mapping) else {}
    state = str(schema.get("state") or "undeveloped")
    parts = schema.get("parts")
    parts = parts if isinstance(parts, list) else []
    confidence_classes = [
        int(item.get("existence_confidence_class", 0))
        for item in parts
        if isinstance(item, Mapping)
    ]
    schema_confidence = (
        sum(confidence_classes) / (15.0 * len(confidence_classes)) if confidence_classes else 0.0
    )
    bindings = episode_payload.get("execution_bindings")
    if not isinstance(bindings, Mapping):
        bindings = episode_payload.get("embodied_competences")
    bindings = bindings if isinstance(bindings, Mapping) else {}
    items = bindings.get("items")
    items = items if isinstance(items, list) else []
    revalidated = sum(
        1
        for item in items
        if isinstance(item, Mapping)
        and item.get("surface_fingerprint", item.get("surface_binding"))
        and item.get("evidence_refs")
    )
    causal = episode_payload.get("causal_evidence")
    causal = causal if isinstance(causal, Mapping) else {}
    evidence = causal.get("evidence")
    evidence = evidence if isinstance(evidence, list) else []
    contract_history = episode_payload.get("contract_history")
    contract_history = contract_history if isinstance(contract_history, list) else []

    summary = EmbodimentEpisodeSummary(
        embodiment_id=embodiment_id,
        epoch=max(1, int(episode_payload.get("epoch") or 1)),
        symbiont_id=symbiont_id,
        body_id=body_id,
        initial_contract_fingerprint=(
            str(contract_history[0].get("previous_fingerprint"))
            if contract_history and isinstance(contract_history[0], Mapping)
            else contract_fp
        ),
        final_contract_fingerprint=contract_fp,
        contract_transition_count=len(contract_history),
        started_at_symbiont_tick=int(episode_payload.get("start_symbiont_tick") or 0),
        ended_at_symbiont_tick=int(symbiont_tick),
        embodiment_ticks=int(episode_payload.get("embodiment_tick") or 0),
        final_body_age_ticks=(
            int(body.get("age_ticks")) if body.get("age_ticks") is not None else None
        ),
        end_reason=str(end_reason),
        body_vital_state=str(body.get("vital_state") or "unknown"),
        initial_body_schema_state="undeveloped",
        final_body_schema_state=state,
        initial_schema_confidence=0.0,
        final_schema_confidence=float(schema_confidence),
        schema_revision_count=int(
            (
                schema.get("boundary_evidence")
                if isinstance(schema.get("boundary_evidence"), Mapping)
                else {}
            ).get("revision_count", 0)
        ),
        initial_prediction_error=0.0,
        final_prediction_error=float(adaptation.get("prediction_error_recent", 0.0)),
        peak_prediction_shock=float(
            adaptation.get(
                "peak_prediction_shock",
                adaptation.get("prediction_shock", 0.0),
            )
        ),
        initial_controllability_confidence=0.0,
        final_controllability_confidence=float(adaptation.get("controllability_confidence", 0.0)),
        competences_present_at_start=0,
        competences_revalidated=revalidated,
        competences_acquired=max(0, len(items) - revalidated),
        competences_lost=0,
        causal_relations_acquired=len(evidence),
        causal_relations_revalidated=0,
        adaptation_first_revision_tick=(
            int(adaptation["first_revision_tick"])
            if adaptation.get("first_revision_tick") is not None
            else None
        ),
        adaptation_recovery_tick=(
            int(adaptation["recovery_tick"])
            if adaptation.get("recovery_tick") is not None
            else None
        ),
    )
    archive.append_summary(summary)
    return summary


__all__ = [
    "BodySpecificMemory",
    "EmbodimentArchive",
    "EmbodimentPrior",
    "archive_episode_checkpoint",
]
