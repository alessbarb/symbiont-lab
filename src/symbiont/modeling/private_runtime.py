from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

from ..core.runtime import RuntimeTickResult
from .experience import EpistemicStatus, ExperienceRecord, SourceKind
from .runtime import ModeledOrganismRuntime


_MAX_CAPTURED_SENSES = 48
_MAX_TEMPORAL_OUTCOMES = 16


def _evidence_ref(*parts: object) -> str:
    material = ":".join(str(part) for part in parts).encode("utf-8")
    return f"evidence.{hashlib.sha256(material).hexdigest()[:32]}"


def _opaque_class(prefix: str, value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}.{digest}"


@dataclass(frozen=True, slots=True)
class _PrivateFrame:
    """Ephemeral t-state waiting for independently observed t+1 consequences."""

    tick: int
    context_tokens: tuple[str, ...]
    action_token: str | None
    evidence_refs: tuple[str, ...]
    source_kind: SourceKind
    percept_values: dict[str, float]
    pressure: str | None
    vital: str | None
    development: str | None


class PrivateModelOrganismRuntime(ModeledOrganismRuntime):
    """Complete private-model organism with temporal native experience capture.

    Private training episodes are causal transitions, not same-tick echoes:

        state(t) + action(t) -> independently observed state(t+1)

    The projection remains intentionally lossy and opaque. Raw percept values are
    used only transiently to classify change and are never written to the
    ExperienceLedger or checkpoint. A restart deliberately drops one pending
    transition rather than fabricating a consequence across the discontinuity.
    """

    def __init__(self, *, capture_private_experience: bool = True, **kwargs) -> None:
        if not isinstance(capture_private_experience, bool):
            raise ValueError("capture_private_experience must be boolean")
        self._capture_private_experience = capture_private_experience
        self._pending_private_frame: _PrivateFrame | None = None
        super().__init__(**kwargs)

    @property
    def capture_private_experience(self) -> bool:
        return self._capture_private_experience

    def _percept_values(self, result: RuntimeTickResult) -> dict[str, float]:
        references = result.signal_references or {}
        values: dict[str, float] = {}
        for percept in result.percepts:
            raw = percept.value
            signal_id = references.get(percept.name)
            if (
                signal_id is None
                or raw is None
                or isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(float(raw))
            ):
                continue
            values[str(signal_id)] = float(raw)
        return values

    @staticmethod
    def _value_class(value: float) -> int:
        """Bound a numeric percept into an opaque three-bit state class."""
        if 0.0 <= value <= 1.0:
            normalized = value
        else:
            normalized = 0.5 + 0.5 * math.tanh(value)
        return max(0, min(7, round(normalized * 7)))

    def _capture_private_frame(self, result: RuntimeTickResult) -> _PrivateFrame:
        context: list[str] = []
        evidence: list[str] = []
        percept_values = self._percept_values(result)

        signal_ids = sorted(set((result.signal_references or {}).values()))[:_MAX_CAPTURED_SENSES]
        for signal_id in signal_ids:
            context.append(f"sense.{signal_id}")
            if signal_id in percept_values:
                context.append(
                    f"{_opaque_class('state.sense', signal_id)}."
                    f"level.{self._value_class(percept_values[signal_id])}"
                )
            if len(evidence) < 12:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "sense", signal_id))

        pressure = None
        if result.metabolism is not None:
            pressure = result.metabolism.pressure.value
            context.append(f"internal.pressure.{pressure}")
            if len(evidence) < 14:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "pressure", pressure))

        vital = None
        if result.physiology is not None:
            vital = result.physiology.state.value
            context.append(f"internal.vital.{vital}")
            if len(evidence) < 15:
                evidence.append(_evidence_ref(self.organism_id, result.tick, "vital", vital))

        development = None
        if result.development is not None:
            development = result.development.phase.value
            context.append(f"internal.development.{development}")

        action_token = None
        source = SourceKind.INTERNAL
        if result.action_result is not None:
            action_id = result.action_result.action_id
            action_token = f"action.{action_id}"
            context.append(
                "internal.action.executed"
                if result.action_result.executed
                else "internal.action.rejected"
            )
            if result.action_result.reason:
                context.append(_opaque_class("internal.action.reason", result.action_result.reason))
            source = SourceKind.ACTION_OUTCOME
            if len(evidence) < 16:
                evidence.append(_evidence_ref(
                    self.organism_id,
                    result.tick,
                    "action",
                    action_id,
                    result.action_result.executed,
                ))
        elif result.actuations or result.actuation is not None:
            actuations = result.actuations or (
                (result.actuation,) if result.actuation is not None else ()
            )
            pattern = []
            for actuation in sorted(actuations, key=lambda item: item.actuator_id):
                delivered_class = max(
                    0, min(7, round(float(actuation.delivered) * 7))
                )
                requested_class = max(
                    0, min(7, round(float(actuation.requested) * 7))
                )
                actuator_token = _opaque_class(
                    "motor.channel",
                    actuation.actuator_id,
                )
                pattern.append(
                    (actuator_token, requested_class, delivered_class)
                )
                context.append(
                    f"internal.{actuator_token}.requested.{requested_class}"
                )
                context.append(
                    f"internal.{actuator_token}.delivered.{delivered_class}"
                )
                if len(evidence) < 16:
                    evidence.append(_evidence_ref(
                        self.organism_id,
                        result.tick,
                        "motor",
                        actuation.actuator_id,
                        delivered_class,
                    ))
            action_token = _opaque_class(
                "action.motor.pattern",
                repr(tuple(pattern)),
            )
            source = SourceKind.ACTION_OUTCOME
        elif signal_ids:
            source = SourceKind.DIRECT

        if not context and action_token is None:
            context.append("internal.quiet")
        if not evidence:
            evidence.append(_evidence_ref(self.organism_id, result.tick, "internal"))

        return _PrivateFrame(
            tick=result.tick,
            context_tokens=tuple(context[:256]),
            action_token=action_token,
            evidence_refs=tuple(evidence[:16]),
            source_kind=source,
            percept_values=percept_values,
            pressure=pressure,
            vital=vital,
            development=development,
        )

    @staticmethod
    def _change_bucket(delta: float) -> tuple[str, int]:
        magnitude = abs(delta)
        direction = "up" if delta > 0.0 else "down"
        if magnitude < 0.01:
            return direction, 1
        if magnitude < 0.05:
            return direction, 2
        if magnitude < 0.20:
            return direction, 3
        return direction, 4

    def _temporal_outcomes(
        self,
        previous: _PrivateFrame,
        current: _PrivateFrame,
    ) -> tuple[str, ...]:
        ranked: list[tuple[float, str]] = []
        for signal_id in sorted(set(previous.percept_values) & set(current.percept_values)):
            before = previous.percept_values[signal_id]
            after = current.percept_values[signal_id]
            scale = max(abs(before), abs(after), 1.0)
            delta = (after - before) / scale
            if abs(delta) < 0.002:
                continue
            direction, bucket = self._change_bucket(delta)
            token = f"{_opaque_class('outcome.sense', signal_id)}.{direction}.{bucket}"
            ranked.append((abs(delta), token))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        outcomes = [token for _, token in ranked[:12]]

        for prefix, before, after in (
            ("pressure", previous.pressure, current.pressure),
            ("vital", previous.vital, current.vital),
            ("development", previous.development, current.development),
        ):
            if before is not None and after is not None and before != after:
                outcomes.append(f"outcome.{prefix}.{after}")

        if not outcomes:
            outcomes.append("outcome.sensory.stable")
        return tuple(outcomes[:_MAX_TEMPORAL_OUTCOMES])

    def _finalize_private_transition(
        self,
        previous: _PrivateFrame,
        current: _PrivateFrame,
    ) -> ExperienceRecord:
        outcomes = self._temporal_outcomes(previous, current)
        evidence = tuple(dict.fromkeys((*previous.evidence_refs, *current.evidence_refs)))[:16]
        digest = hashlib.sha256(
            (
                f"{self.organism_id}:{previous.tick}:{current.tick}:"
                f"{previous.context_tokens}:{previous.action_token}:{outcomes}"
            ).encode("utf-8")
        ).hexdigest()[:24]
        return ExperienceRecord(
            record_id=f"transition.{digest}",
            organism_id=self.organism_id,
            tick_class=previous.tick,
            context_tokens=previous.context_tokens,
            action_token=previous.action_token,
            outcome_tokens=outcomes,
            epistemic_status=EpistemicStatus.OBSERVED,
            evidence_refs=evidence or (_evidence_ref(self.organism_id, current.tick, "transition"),),
            confidence_class=7,
            source_kind=previous.source_kind,
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
        self.record_experience(prediction)

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
            current = self._capture_private_frame(result)
            previous = self._pending_private_frame
            if previous is not None:
                episode = self._finalize_private_transition(previous, current)
                self.record_experience(episode)
                self._validate_active_model_on_episode(episode)
            self._pending_private_frame = current
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
        runtime = super().from_checkpoint(payload, **constructor)
        # Never bridge t -> t+1 across a restart. The first post-restore tick
        # establishes a new independent frame.
        runtime._pending_private_frame = None
        return runtime
