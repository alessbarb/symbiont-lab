"""Immutable longitudinal summaries for Embodiment v2."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping


@dataclass(frozen=True, slots=True)
class EmbodimentEpisodeSummary:
    embodiment_id: str
    epoch: int
    symbiont_id: str
    body_id: str
    initial_contract_fingerprint: str
    final_contract_fingerprint: str
    contract_transition_count: int
    started_at_symbiont_tick: int
    ended_at_symbiont_tick: int
    embodiment_ticks: int
    final_body_age_ticks: int | None
    end_reason: str
    body_vital_state: str
    initial_body_schema_state: str
    final_body_schema_state: str
    initial_schema_confidence: float
    final_schema_confidence: float
    schema_revision_count: int
    initial_prediction_error: float
    final_prediction_error: float
    peak_prediction_shock: float
    initial_controllability_confidence: float
    final_controllability_confidence: float
    competences_present_at_start: int
    competences_revalidated: int
    competences_acquired: int
    competences_lost: int
    causal_relations_acquired: int
    causal_relations_revalidated: int
    adaptation_first_revision_tick: int | None
    adaptation_recovery_tick: int | None

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": 2, **asdict(self)}

    @classmethod
    def restore(cls, payload: Mapping[str, object]) -> "EmbodimentEpisodeSummary":
        if payload.get("schema_version") != 2:
            raise ValueError("unsupported embodiment summary")
        values = {key: value for key, value in payload.items() if key != "schema_version"}
        return cls(**values)  # type: ignore[arg-type]


__all__ = ["EmbodimentEpisodeSummary"]
