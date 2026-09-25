"""Evidence-first sequential competence composition."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SequentialCompositionEvidence:
    first_competence_id: str
    second_competence_id: str
    effect_id: str
    support: int = 0
    failures: int = 0

    @property
    def observations(self) -> int:
        return self.support + self.failures

    @property
    def reproducibility(self) -> float:
        return self.support / max(1, self.observations)

    @property
    def established(self) -> bool:
        return self.support >= 4 and self.reproducibility >= (2.0 / 3.0)

    def checkpoint(self) -> dict[str, object]:
        return {
            "first_competence_id": self.first_competence_id,
            "second_competence_id": self.second_competence_id,
            "effect_id": self.effect_id,
            "support": self.support,
            "failures": self.failures,
        }


class CompositionEngine:
    SCHEMA_VERSION = 1

    def __init__(self, *, max_relations: int = 512) -> None:
        if max_relations < 1:
            raise ValueError("max_relations must be positive")
        self._max_relations = int(max_relations)
        self._sequential: dict[
            tuple[str, str, str],
            SequentialCompositionEvidence,
        ] = {}

    def observe(
        self,
        first: str,
        second: str,
        effect_id: str,
        *,
        success: bool,
    ) -> SequentialCompositionEvidence:
        if not first or not second or first == second:
            raise ValueError("sequential composition requires two distinct competences")
        if not effect_id.startswith("effect."):
            raise ValueError("composition effect must be organism-owned")
        key = (first, second, effect_id)
        evidence = self._sequential.setdefault(
            key,
            SequentialCompositionEvidence(first, second, effect_id),
        )
        if success:
            evidence.support += 1
        else:
            evidence.failures += 1
        if len(self._sequential) > self._max_relations:
            retained = sorted(
                self._sequential.items(),
                key=lambda item: (
                    -item[1].support,
                    item[1].failures,
                    item[0],
                ),
            )[: self._max_relations]
            self._sequential = dict(retained)
        return evidence

    def observe_absence(self, first: str, second: str) -> None:
        """Record that an observed A->B completion failed to reproduce known effects."""
        for key, evidence in self._sequential.items():
            if key[0] == first and key[1] == second:
                evidence.failures += 1

    @property
    def evidence(self) -> tuple[SequentialCompositionEvidence, ...]:
        return tuple(
            sorted(
                self._sequential.values(),
                key=lambda item: (
                    item.first_competence_id,
                    item.second_competence_id,
                    item.effect_id,
                ),
            )
        )

    @property
    def established(self) -> tuple[SequentialCompositionEvidence, ...]:
        return tuple(item for item in self.evidence if item.established)

    def checkpoint(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "max_relations": self._max_relations,
            "sequential": [item.checkpoint() for item in self.evidence],
        }

    @classmethod
    def restore(cls, payload: dict[str, object]) -> "CompositionEngine":
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported composition checkpoint")
        engine = cls(max_relations=int(payload.get("max_relations", 512)))
        raw = payload.get("sequential", [])
        if not isinstance(raw, list):
            raise ValueError("invalid composition checkpoint")
        for item in raw[: engine._max_relations]:
            if not isinstance(item, dict):
                raise ValueError("invalid composition evidence")
            evidence = SequentialCompositionEvidence(
                first_competence_id=str(item["first_competence_id"]),
                second_competence_id=str(item["second_competence_id"]),
                effect_id=str(item["effect_id"]),
                support=int(item.get("support", 0)),
                failures=int(item.get("failures", 0)),
            )
            if (
                not evidence.first_competence_id
                or not evidence.second_competence_id
                or evidence.first_competence_id == evidence.second_competence_id
                or not evidence.effect_id.startswith("effect.")
                or evidence.support < 0
                or evidence.failures < 0
            ):
                raise ValueError("invalid composition evidence")
            engine._sequential[
                (
                    evidence.first_competence_id,
                    evidence.second_competence_id,
                    evidence.effect_id,
                )
            ] = evidence
        return engine
