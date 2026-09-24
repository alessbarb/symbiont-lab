from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math

from ..cognition.types import NodeKind
from ..core.orchestration.runtime import RuntimeTickResult
from .episodic import EpisodicProjection
from .experience import EpistemicStatus, ExperienceRecord, SourceKind
from .runtime import ModeledOrganismRuntime


_MAX_CAPTURED_SENSES = 128
_MAX_TEMPORAL_OUTCOMES = 64


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
    homeostatic_deviation: float
    episodic_projection: EpisodicProjection


class PrivateModelOrganismRuntime(ModeledOrganismRuntime):
    """Complete private-model organism with temporal native experience capture.

    Private training episodes are causal transitions, not same-tick echoes:

        state(t) + action(t) -> independently observed state(t+1)

    The projection remains intentionally lossy and opaque. Raw percept values are
    used only transiently to classify change and are never written to the
    ExperienceLedger or checkpoint. A restart deliberately drops one pending
    transition rather than fabricating a consequence across the discontinuity.
    """

    def __init__(
        self,
        *,
        capture_private_experience: bool = True,
        enable_prospective_agency: bool = True,
        **kwargs,
    ) -> None:
        if not isinstance(capture_private_experience, bool):
            raise ValueError("capture_private_experience must be boolean")
        if not isinstance(enable_prospective_agency, bool):
            raise ValueError("enable_prospective_agency must be boolean")
        self._capture_private_experience = capture_private_experience
        self._enable_prospective_agency = enable_prospective_agency
        self._pending_private_frame: _PrivateFrame | None = None
        super().__init__(**kwargs)
        self._init_prospective_agency(
            enable_prospective_agency=enable_prospective_agency,
        )

    @property
    def capture_private_experience(self) -> bool:
        return self._capture_private_experience

    @property
    def last_prospective_decision(self):
        return self._last_prospective_decision

    @property
    def last_prospective_query_count(self) -> int:
        return self._last_prospective_query_count

    @property
    def last_prospective_cost(self) -> float:
        return self._last_prospective_cost

    @property
    def prospective_outcome_value_count(self) -> int:
        if self._prospective_agency is None:
            return 0
        return self._prospective_agency.outcome_value_ledger.known_outcome_count

    @property
    def last_prospective_value_samples(self) -> int:
        decision = self._last_prospective_decision
        if (
            self._prospective_agency is None
            or decision is None
            or decision.predicted_outcome is None
        ):
            return 0
        estimate = self._prospective_agency.outcome_value_ledger.estimate(
            decision.predicted_outcome
        )
        return 0 if estimate is None else int(estimate.samples)

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

    def _private_context_tokens_from_percepts(
        self,
        percepts: tuple[object, ...],
        signal_references: dict[str, str],
    ) -> tuple[str, ...]:
        """Build context in the same private vocabulary used by training."""
        context: list[str] = []
        values: dict[str, float] = {}
        for percept in percepts:
            name = getattr(percept, "name", None)
            raw = getattr(percept, "value", None)
            signal_id = signal_references.get(str(name)) if name is not None else None
            if (
                signal_id is None
                or raw is None
                or isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(float(raw))
            ):
                continue
            values[str(signal_id)] = float(raw)

        for signal_id in sorted(values)[:_MAX_CAPTURED_SENSES]:
            context.append(f"sense.{signal_id}")
            context.append(
                f"{_opaque_class('state.sense', signal_id)}."
                f"level.{self._value_class(values[signal_id])}"
            )

        metabolism_snapshot = self._metabolism.snapshot()
        pressure_value = getattr(
            getattr(metabolism_snapshot, "pressure", None),
            "value",
            None,
        )
        if isinstance(pressure_value, str) and pressure_value:
            context.append(f"internal.pressure.{pressure_value}")

        physiology_state = getattr(self._physiology, "state", None)
        vital_value = getattr(physiology_state, "value", None)
        if isinstance(vital_value, str) and vital_value:
            context.append(f"internal.vital.{vital_value}")

        development_value = self._last_runtime_development_phase
        if isinstance(development_value, str) and development_value:
            context.append(f"internal.development.{development_value}")

        if not context:
            context.append("internal.quiet")
        return tuple(context[:512])
    def _episodic_projection(
        self,
        result: RuntimeTickResult,
        *,
        action_token: str | None,
        pressure: str | None,
        vital: str | None,
        development: str | None,
    ) -> EpisodicProjection:
        """Capture the sparse cognitive state actually available at this tick."""
        cognition = result.cognition
        activations = (
            cognition.activations
            if cognition is not None and isinstance(cognition.activations, dict)
            else {}
        )
        kinds = {}
        if self._cognitive_bridge is not None:
            kinds = {
                node.node_id: node.kind
                for node in self._cognitive_bridge.graph.nodes
            }

        ranked_senses = sorted(
            (
                (abs(float(value)), node_id)
                for node_id, value in activations.items()
                if (
                    kinds.get(node_id) is NodeKind.SENSE
                    and isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(float(value))
                    and abs(float(value)) > 1e-9
                )
            ),
            key=lambda item: (-item[0], item[1]),
        )
        sense_ids = tuple(node_id for _, node_id in ranked_senses[:16])

        concept_ids = ()
        if cognition is not None:
            concept_ids = tuple(
                concept_id
                for concept_id in cognition.active_concept_ids
                if kinds.get(concept_id) is NodeKind.CONCEPT
            )[:8]

        internal_tokens = tuple(
            token
            for token in (
                f"internal.pressure.{pressure}" if pressure else None,
                f"internal.vital.{vital}" if vital else None,
                f"internal.development.{development}" if development else None,
            )
            if token is not None
        )

        return EpisodicProjection(
            sense_ids=sense_ids,
            concept_ids=concept_ids,
            internal_tokens=internal_tokens,
            action_token=action_token,
        )

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
            motor_origin = self.last_motor_origin_detail
            executed_pid = self._last_executed_primitive_id
            named_primitive = (
                executed_pid is not None
                and motor_origin in {
                    "primitive_cognition",
                    "primitive_reactive",
                    "primitive_prospective",
                }
            )
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
                # A named learned primitive already has a stable opaque
                # action token. Do not condition its causal training episode on
                # post-execution delivered values that are unavailable during
                # counterfactual choice. Composite babbling still needs channel
                # detail because it has no acquired action identity.
                if not named_primitive:
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
            # When the execution originated from a named primitive, use the
            # primitive's opaque identity as the action token. This gives
            # counterfactual inference the same token that was produced during
            # training — one representation for learning and imagining.
            # For babbling and non-primitive multi-channel vectors, the
            # composite fallback preserves the existing behaviour.
            if named_primitive:
                action_token = f"action.{executed_pid}"
            else:
                action_token = "action.motor.composite"
            source = SourceKind.ACTION_OUTCOME
        elif signal_ids:
            source = SourceKind.DIRECT

        if not context and action_token is None:
            context.append("internal.quiet")
        if not evidence:
            evidence.append(_evidence_ref(self.organism_id, result.tick, "internal"))

        episodic_projection = self._episodic_projection(
            result,
            action_token=action_token,
            pressure=pressure,
            vital=vital,
            development=development,
        )
        return _PrivateFrame(
            tick=result.tick,
            context_tokens=tuple(context[:512]),
            action_token=action_token,
            evidence_refs=tuple(evidence[:16]),
            source_kind=source,
            percept_values=percept_values,
            pressure=pressure,
            vital=vital,
            development=development,
            homeostatic_deviation=float(self._homeostasis.deviation()),
            episodic_projection=episodic_projection,
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
        self.record_experience(ExperienceRecord(
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

    # ------------------------------------------------------------------ #
    #  L8: Prospective Agency integration                                  #
    # ------------------------------------------------------------------ #

    def _init_prospective_agency(
        self,
        *,
        enable_prospective_agency: bool = True,
    ) -> None:
        """Initialise the prospective agency subsystem.

        Called once from __init__ after super().__init__() so physiology_config
        is available. Configuration/programming errors fail closed during
        construction; runtime absence of an ACTIVE model merely abstains.
        """
        self._prospective_agency = None
        self._last_prospective_decision = None
        self._last_prospective_query_count = 0
        self._last_prospective_cost = 0.0
        self._pending_outcome_value_credit: list[
            tuple[int, str, float, float]
        ] = []
        if not enable_prospective_agency:
            return

        from ..agency import OutcomeValueLedger, ProspectiveAgency, ProspectivePolicy

        config = self.physiology_config
        policy = ProspectivePolicy(
            organism_id=self.organism_id,
            min_model_confidence=config.prospective_min_model_confidence,
            min_value_samples=config.prospective_min_value_samples,
            decision_margin=config.prospective_decision_margin,
        )
        self._prospective_agency = ProspectiveAgency(
            organism_id=self.organism_id,
            outcome_value_ledger=OutcomeValueLedger(),
            policy=policy,
            query_budget=config.prospective_max_candidates,
        )

    def predict_primitive_outcome(
        self,
        primitive_id: str,
        context_tokens: tuple[str, ...],
    ) -> "ModelPredictionProposal":
        """Predict the outcome of a primitive action counterfactually.

        This is an imagination query — it uses the ACTIVE private SLM to
        predict what would happen *if* the organism executed ``primitive_id``.
        No ExperienceRecord is created.

        Args:
            primitive_id: Opaque primitive identifier (e.g. ``"primitive.<hex>"``).
            context_tokens: Private cognitive context tokens.

        Returns:
            A ModelPredictionProposal with the predicted outcome token and
            confidence class.

        Raises:
            ValueError: If no ACTIVE model exists, or bridge is unavailable,
                or the organism is dead.
        """
        action_token = f"action.{primitive_id}"
        return self.active_private_counterfactual(
            context_tokens,
            action_token=action_token,
            target_token="<OUTCOME>",
        )

    def _choose_acquired_primitive(
        self,
        *,
        cognition: "CognitiveBridgeResult",
        percepts: "tuple[Percept, ...]",
        candidate_ids: "tuple[str, ...]",
        signal_references: "dict[str, str]",
        tick: int,
    ) -> str | None:
        """Override: consult ProspectiveAgency for model-based primitive selection.

        Returns the chosen primitive ID, or None to fall back to the existing
        cognitive-readout / babbling selection.
        """
        self._last_prospective_decision = None
        self._last_prospective_query_count = 0
        self._last_prospective_cost = 0.0
        if self._prospective_agency is None:
            return None
        if not candidate_ids:
            return None
        active = self._model_registry.active if self._private_model_bridge else None
        if active is None:
            return None

        # A sensorimotor competence becomes a prospective action only after
        # its primitive readout has actually entered the cognitive graph.
        primitive_readouts = cognition.readouts_for_family("primitive")
        admitted_ids = tuple(
            pid for pid in candidate_ids if pid in primitive_readouts
        )
        if not admitted_ids:
            return None

        # Counterfactual inference stays inside the same private token language
        # used for observed training episodes.
        context = self._private_context_tokens_from_percepts(
            percepts,
            signal_references,
        )

        from ..agency import ProspectiveCandidate
        candidates = tuple(
            ProspectiveCandidate(action_id=pid, family="primitive")
            for pid in admitted_ids
        )

        config = self.physiology_config
        homeostatic_deviation = self._homeostasis.deviation()
        query_count = 0

        def _predictor(action_id: str, ctx: tuple[str, ...]) -> "CounterfactualPrediction":
            nonlocal query_count
            from ..agency import CounterfactualPrediction
            # Count an actual inference attempt, including one that fails
            # inside the model gateway: computation was still requested.
            query_count += 1
            proposal = self.predict_primitive_outcome(action_id, ctx)
            return CounterfactualPrediction(
                action_id=action_id,
                predicted_outcome=proposal.predicted_token,
                confidence_class=proposal.confidence_class,
            )

        from ..core.embodiment.physiology import VitalState
        decision = self._prospective_agency.deliberate(
            tick=tick,
            candidates=candidates,
            context_tokens=context,
            homeostatic_deviation=homeostatic_deviation,
            predictor=_predictor,
            has_active_model=active is not None,
            organism_alive=self._physiology.state is not VitalState.DEAD,
        )
        self._last_prospective_query_count = query_count
        query_cost = config.prospective_query_cost * query_count
        self._last_prospective_cost = float(query_cost)
        if query_cost > 0:
            self._charge_metabolism("maintenance", query_cost)
        self._last_prospective_decision = decision

        if decision.reason == "selected" and decision.candidate_id is not None:
            # Predicted outcomes influence choice only. Endogenous value is
            # learned later from independently observed real outcomes.
            return decision.candidate_id

        return None

    def _schedule_observed_outcome_value_credit(
        self,
        episode: ExperienceRecord,
        *,
        baseline_deviation: float,
        tick: int,
    ) -> None:
        """Schedule endogenous value learning from observed outcomes only."""
        if (
            self._prospective_agency is None
            or episode.action_token is None
            or not episode.outcome_tokens
        ):
            return
        for horizon, discount in ((4, 1.0), (16, 0.85), (64, 0.65), (256, 0.40)):
            due_tick = int(tick) + horizon
            for outcome_id in episode.outcome_tokens:
                self._pending_outcome_value_credit.append(
                    (due_tick, str(outcome_id), float(baseline_deviation), discount)
                )
        if len(self._pending_outcome_value_credit) > 4096:
            self._pending_outcome_value_credit.sort(key=lambda item: item[0])
            self._pending_outcome_value_credit = self._pending_outcome_value_credit[:4096]
    def _resolve_outcome_value_credit(self, *, tick: int) -> None:
        """Resolve pending outcome-value credit traces at due ticks."""
        if not self._pending_outcome_value_credit or self._prospective_agency is None:
            return
        if not self._living_body_state.alive:
            self._pending_outcome_value_credit.clear()
            return
        current_deviation = self._homeostasis.deviation()
        remaining: list[tuple[int, str, float, float]] = []
        for due_tick, outcome_id, baseline, discount in self._pending_outcome_value_credit:
            if due_tick > tick:
                remaining.append((due_tick, outcome_id, baseline, discount))
                continue
            intrinsic_value = (baseline - current_deviation) * discount
            self._prospective_agency.outcome_value_ledger.observe(
                outcome_id,
                intrinsic_value,
                tick=tick,
            )
        self._pending_outcome_value_credit = remaining

    def tick(self) -> RuntimeTickResult:
        result = super().tick()
        # Resolve outcome-value credit traces at due ticks (L8).
        # This must happen on every tick regardless of _capture_private_experience
        # because prospective decisions may have been made before the flag was set.
        tick = result.tick
        self._resolve_outcome_value_credit(tick=tick)

        if self._capture_private_experience:
            # WARN(invariant): The canonical runtime may complete a terminal tick and transition
            # physiology to DEAD before returning its passive result.  Once
            # death has occurred the organism must not mutate experience/model
            # state.  Drop the pending causal bridge rather than fabricating
            # post-mortem learning or weakening record_experience()'s invariant.
            if "death" in result.runtime_events:
                self._pending_private_frame = None
                self._pending_outcome_value_credit.clear()
                return result

            current = self._capture_private_frame(result)
            previous = self._pending_private_frame
            if previous is not None:
                episode = self._finalize_private_transition(previous, current)
                self.record_experience(
                    episode,
                    episodic_projection=previous.episodic_projection.with_effects(
                        episode.outcome_tokens
                    ),
                )
                self._schedule_observed_outcome_value_credit(
                    episode,
                    baseline_deviation=previous.homeostatic_deviation,
                    tick=previous.tick,
                )
                self._validate_active_model_on_episode(episode)
            self._pending_private_frame = current
        return result

    def checkpoint(self) -> dict[str, object]:
        payload = super().checkpoint()
        config = dict(payload.get("private_model_config", {}))
        config["capture_private_experience"] = self._capture_private_experience
        config["enable_prospective_agency"] = self._enable_prospective_agency
        payload["private_model_config"] = config

        # WARN(no-cross-restart-bridging): Persist agency state (OutcomeValueLedger only; pending traces are NOT
        # checkpointed — they cannot bridge across a restart without fabricating
        # a causal consequence that never happened in the restored timeline).
        if self._prospective_agency is not None:
            payload["prospective_agency"] = self._prospective_agency.checkpoint()

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
        if "enable_prospective_agency" not in constructor:
            value = raw_config.get("enable_prospective_agency", True)
            if not isinstance(value, bool):
                raise ValueError("invalid prospective agency checkpoint flag")
            constructor["enable_prospective_agency"] = value
        runtime = super().from_checkpoint(payload, **constructor)
        # WARN: Never bridge t -> t+1 across a restart. The first post-restore tick
        # establishes a new independent frame.
        runtime._pending_private_frame = None

        # WARN: Restore agency OutcomeValueLedger. Pending outcome-value credit
        # traces are NOT restored — no cross-restart causal bridging.
        runtime._pending_outcome_value_credit = []
        if runtime._prospective_agency is not None:
            raw_agency = payload.get("prospective_agency") if isinstance(payload, dict) else None
            if raw_agency is not None:
                if not isinstance(raw_agency, dict):
                    raise ValueError("invalid prospective agency checkpoint")
                from ..agency import ProspectiveAgency, ProspectivePolicy
                config = runtime.physiology_config
                policy = ProspectivePolicy(
                    organism_id=runtime.organism_id,
                    min_model_confidence=config.prospective_min_model_confidence,
                    min_value_samples=config.prospective_min_value_samples,
                    decision_margin=config.prospective_decision_margin,
                )
                runtime._prospective_agency = ProspectiveAgency.restore(
                    raw_agency,
                    organism_id=runtime.organism_id,
                    policy=policy,
                    query_budget=config.prospective_max_candidates,
                )
        return runtime
