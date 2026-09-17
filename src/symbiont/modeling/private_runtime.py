from __future__ import annotations

import hashlib

from ..core.runtime import RuntimeTickResult
from .experience import EpistemicStatus, ExperienceRecord, SourceKind
from .runtime import ModeledOrganismRuntime


_MAX_CAPTURED_SENSES = 48


def _evidence_ref(*parts: object) -> str:
    material = ":".join(str(part) for part in parts).encode("utf-8")
    return f"evidence.{hashlib.sha256(material).hexdigest()[:32]}"


def _opaque_class(prefix: str, value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}.{digest}"


class PrivateModelOrganismRuntime(ModeledOrganismRuntime):
    """Complete private-model organism: biology + modeling + native experience capture.

    The projection is intentionally lossy. It retains opaque signal identities,
    internal state classes and action outcomes, never percept values, host paths,
    evaluator-only ``runtime_events`` or laboratory metrics. Each tick becomes an
    immutable organism-owned episode that may later enter its private corpus.

    An ACTIVE model can also run a causal shadow prediction every time a local
    action produced an outcome. The prediction input is built only from context,
    action and epistemic/source markers; the real outcome is withheld until after
    inference and then used as independent support/contradiction evidence. Model
    output therefore cannot validate itself or directly control the action.
    """

    def __init__(self, *, capture_private_experience: bool = True, **kwargs) -> None:
        if not isinstance(capture_private_experience, bool):
            raise ValueError("capture_private_experience must be boolean")
        self._capture_private_experience = capture_private_experience
        super().__init__(**kwargs)

    @property
    def capture_private_experience(self) -> bool:
        return self._capture_private_experience

    def _project_tick_experience(self, result: RuntimeTickResult) -> ExperienceRecord:
        context: list[str] = []
        evidence: list[str] = []

        signal_ids = sorted(set((result.signal_references or {}).values()))[:_MAX_CAPTURED_SENSES]
        for signal_id in signal_ids:
            context.append(f"sense.{signal_id}")
            if len(evidence) < 12:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "sense", signal_id))

        if result.metabolism is not None:
            pressure = result.metabolism.pressure.value
            context.append(f"internal.pressure.{pressure}")
            if len(evidence) < 14:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "pressure", pressure))

        if result.physiology is not None:
            vital = result.physiology.state.value
            context.append(f"internal.vital.{vital}")
            if len(evidence) < 15:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "vital", vital))

        if result.development is not None:
            context.append(f"internal.development.{result.development.phase.value}")

        action_token = None
        outcome: list[str] = []
        source = SourceKind.INTERNAL
        if result.action_result is not None:
            action_id = result.action_result.action_id
            action_token = f"action.{action_id}"
            outcome.append("outcome.executed" if result.action_result.executed else "outcome.rejected")
            if result.action_result.reason:
                outcome.append(_opaque_class("outcome.reason", result.action_result.reason))
            source = SourceKind.ACTION_OUTCOME
            if len(evidence) < 16:
                evidence.append(_evidence_ref(
                    self.organism_id,
                    result.tick,
                    "action",
                    action_id,
                    result.action_result.executed,
                ))
        elif signal_ids:
            source = SourceKind.DIRECT

        if result.homeostasis is not None:
            outcome.append(f"internal.homeostasis.{result.homeostasis.action.value}")

        if not context and action_token is None and not outcome:
            raise RuntimeError("runtime tick exposes no admissible private experience")
        if not evidence:
            evidence.append(_evidence_ref(self.organism_id, result.tick, "internal"))

        digest = hashlib.sha256(
            f"{self.organism_id}:{result.tick}:{tuple(context)}:{action_token}:{tuple(outcome)}".encode("utf-8")
        ).hexdigest()[:24]
        return ExperienceRecord(
            record_id=f"life.{digest}",
            organism_id=self.organism_id,
            tick_class=result.tick,
            context_tokens=tuple(context[:256]),
            action_token=action_token,
            outcome_tokens=tuple(outcome[:32]),
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=tuple(evidence[:16]),
            confidence_class=7,
            source_kind=source,
        )

    def _validate_active_model_on_episode(self, episode: ExperienceRecord) -> None:
        active = self._model_registry.active
        if (
            active is None
            or self._private_model_bridge is None
            or episode.action_token is None
            or not episode.outcome_tokens
        ):
            return

        # Mirror the training record prefix exactly, stopping before outcomes.
        prefix = (
            "<BOS>",
            *episode.context_tokens,
            "<SEP>",
            episode.action_token,
            f"<EPI:{episode.epistemic_status.value}>",
            f"<SRC:{episode.source_kind.value}>",
        )
        proposal = self._private_model_bridge.predict(
            prefix,
            model_id=active.model_id,
            target_token="<OUTCOME>",
            allow_shadow=False,
        )
        prediction_digest = hashlib.sha256(
            f"{proposal.model_id}:{episode.record_id}:{proposal.predicted_token}".encode("utf-8")
        ).hexdigest()[:24]
        prediction = ExperienceRecord(
            record_id=f"model.{prediction_digest}",
            organism_id=self.organism_id,
            tick_class=episode.tick_class,
            context_tokens=tuple(prefix[:256]),
            action_token=None,
            outcome_tokens=(proposal.predicted_token,),
            epistemic_status=EpistemicStatus.PREDICTED,
            evidence_refs=(),
            confidence_class=proposal.confidence_class,
            source_kind=SourceKind.MODEL,
        )
        self._experience_ledger.append(prediction)

        supported = proposal.predicted_token == episode.outcome_tokens[0]
        status = EpistemicStatus.SUPPORTED if supported else EpistemicStatus.CONTRADICTED
        validation_digest = hashlib.sha256(
            f"{prediction.record_id}:{status.value}:{episode.evidence_refs}".encode("utf-8")
        ).hexdigest()[:24]
        self._experience_ledger.append(ExperienceRecord(
            record_id=f"validation.{validation_digest}",
            organism_id=self.organism_id,
            tick_class=episode.tick_class,
            context_tokens=prediction.context_tokens,
            action_token=None,
            outcome_tokens=prediction.outcome_tokens,
            epistemic_status=status,
            evidence_refs=episode.evidence_refs,
            confidence_class=proposal.confidence_class,
            source_kind=SourceKind.MODEL,
        ))

    def tick(self) -> RuntimeTickResult:
        result = super().tick()
        if self._capture_private_experience:
            episode = self._project_tick_experience(result)
            self._experience_ledger.append(episode)
            self._validate_active_model_on_episode(episode)
        return result

    def checkpoint(self) -> dict[str, object]:
        payload = super().checkpoint()
        config = dict(payload.get("private_model_config", {}))
        config["capture_private_experience"] = self._capture_private_experience
        payload["private_model_config"] = config
        return payload

    @classmethod
    def from_checkpoint(cls, payload: dict[str, object], **kwargs):
        raw_config = payload.get("private_model_config", {}) if isinstance(payload, dict) else {}
        if raw_config is not None and not isinstance(raw_config, dict):
            raise ValueError("invalid private model configuration checkpoint")
        constructor = dict(kwargs)
        if "capture_private_experience" not in constructor:
            value = raw_config.get("capture_private_experience", True)
            if not isinstance(value, bool):
                raise ValueError("invalid private experience capture checkpoint")
            constructor["capture_private_experience"] = value
        return super().from_checkpoint(payload, **constructor)
