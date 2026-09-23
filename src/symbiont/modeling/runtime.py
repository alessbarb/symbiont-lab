from __future__ import annotations

import hashlib
import math
from collections import deque
from dataclasses import dataclass
from typing import Any

from ..cognition.birth import load_base_graph
from ..core.embodiment.physiology import LivingBodyState, VitalState
from ..core.embodiment.metabolism import MetabolicLedger
from ..core.orchestration.runtime import OrganismDeadError, OrganismRuntime
from .authority import ArchitectureId, ModelArtifactManifest, ModelObjective, TrainingRequest
from .corpus import TrainingCorpus, build_training_corpus
from .experience import EpistemicStatus, ExperienceRecord, SourceKind
from .gateway import PrivateModelBridge
from .ledger import ExperienceLedger
from .episodic import (
    CognitiveReplay,
    EpisodeMatch,
    EpisodicExperienceMemory,
    EpisodicPrediction,
)
from .culture import (
    CulturalAction,
    CulturalComposite,
    CulturalDecisionRecord,
    CulturalPolicy,
    CulturalPolicyConfig,
    SocialClaim,
    SocialChannel,
    SocialEpistemicStatus,
    SocialEvidenceLedger,
    DeliveryResult,
)
from .symbols import (
    MAX_HISTORY,
    SymbolAction,
    SymbolChannel,
    SymbolDecisionRecord,
    SymbolGroundingLedger,
    SymbolMessage,
    SymbolPolicy,
    SymbolReinforcementSignal,
    default_symbol_space,
)
from .sequences import (
    MAX_SEQUENCE_LENGTH,
    SequenceGroundingLedger,
    SequenceChannel,
    SequenceDecisionRecord,
    SequenceMessage,
    SymbolSequence,
    choose_sequence,
)
from .proposals import ModelPredictionProposal
from .registry import ModelRecord, ModelRegistry, ModelState
from .tokenizer import NativeTokenizer


_PRIVATE_LEARNING_MIN_BOOTSTRAP_TRANSITIONS = 64
_PRIVATE_LEARNING_MIN_NEW_TRANSITIONS = 32
_PRIVATE_LEARNING_FORCE_NEW_TRANSITIONS = 96
_PRIVATE_LEARNING_VALIDATION_WINDOW = 32
_PRIVATE_LEARNING_MIN_VALIDATIONS = 8
_PRIVATE_LEARNING_CONTRADICTION_TRIGGER = 0.35


@dataclass(frozen=True, slots=True)
class AutonomousTrainingPlan:
    """Organism-authored request plus the exact private corpus it chose.

    The host may execute or defer this plan according to available compute,
    but it does not choose the trigger, corpus, objective, or requested work.
    """

    request: TrainingRequest
    corpus: TrainingCorpus
    tokenizer: NativeTokenizer
    reason: str
    transition_count: int
    new_transition_count: int
    contradiction_ratio: float
    replay_pressure: float

class ModeledOrganismRuntime(OrganismRuntime):
    """OrganismRuntime with an acquired private-model phenotype.

    The biological runtime remains unchanged. This subclass adds only governed
    training requests, organism-owned abstract experience, content-addressed
    model metadata, shadow/active inference, and checkpoint semantics. Model
    weights and ML frameworks stay outside the organism package and are never
    serialized into the organism checkpoint.
    """

    def __init__(
        self,
        *,
        model_registry: ModelRegistry | None = None,
        experience_ledger: ExperienceLedger | None = None,
        episodic_memory: EpisodicExperienceMemory | None = None,
        private_model_bridge: PrivateModelBridge | None = None,
        social_evidence_ledger: SocialEvidenceLedger | None = None,
        model_request_base_cost: float = 0.01,
        model_storage_scale: float = 0.02,
        cultural_policy_seed: int = 0,
        cultural_policy_config: CulturalPolicyConfig | None = None,
        symbol_policy_seed: int = 0,
        symbol_space: tuple[str, ...] | None = None,
        symbol_grounding_ledger: SymbolGroundingLedger | None = None,
        sequence_grounding_ledger: SequenceGroundingLedger | None = None,
        sequence_max_length: int = MAX_SEQUENCE_LENGTH,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if (isinstance(model_request_base_cost, bool)
                or not isinstance(model_request_base_cost, (int, float))
                or not math.isfinite(float(model_request_base_cost))
                or not 0.0 <= float(model_request_base_cost) <= 0.25):
            raise ValueError("model_request_base_cost must be within [0, 0.25]")
        if (isinstance(model_storage_scale, bool)
                or not isinstance(model_storage_scale, (int, float))
                or not math.isfinite(float(model_storage_scale))
                or not 0.0 <= float(model_storage_scale) <= 0.25):
            raise ValueError("model_storage_scale must be within [0, 0.25]")
        if model_registry is not None and model_registry.organism_id != self.organism_id:
            raise ValueError("private model registry belongs to a different organism")
        if experience_ledger is not None and experience_ledger.organism_id != self.organism_id:
            raise ValueError("experience ledger belongs to a different organism")
        self._model_registry = model_registry or ModelRegistry(self.organism_id)
        self._experience_ledger = experience_ledger or ExperienceLedger(self.organism_id)
        if episodic_memory is not None and episodic_memory.organism_id != self.organism_id:
            raise ValueError("episodic memory belongs to a different organism")
        self._episodic_memory = episodic_memory or EpisodicExperienceMemory(
            self.organism_id,
            kernel_limits=self._kernel_limits,
        )
        if social_evidence_ledger is not None and social_evidence_ledger.organism_id != self.organism_id:
            raise ValueError("social evidence ledger belongs to a different organism")
        self._social_evidence_ledger = social_evidence_ledger or SocialEvidenceLedger(self.organism_id)
        self._private_model_bridge = private_model_bridge
        self._model_request_base_cost = float(model_request_base_cost)
        self._model_storage_scale = float(model_storage_scale)
        self._cultural_policy = CulturalPolicy(
            self.organism_id, seed=cultural_policy_seed, config=cultural_policy_config
        )
        if symbol_grounding_ledger is not None and symbol_grounding_ledger.organism_id != self.organism_id:
            raise ValueError("symbol grounding ledger belongs to a different organism")
        self._symbol_grounding_ledger = symbol_grounding_ledger or SymbolGroundingLedger(self.organism_id)
        self._symbol_policy = SymbolPolicy(self.organism_id, seed=symbol_policy_seed, symbol_space=symbol_space or default_symbol_space())
        if sequence_grounding_ledger is not None and sequence_grounding_ledger.organism_id != self.organism_id:
            raise ValueError("sequence grounding ledger belongs to a different organism")
        self._sequence_grounding_ledger = sequence_grounding_ledger or SequenceGroundingLedger(self.organism_id)
        if isinstance(sequence_max_length, bool) or not isinstance(sequence_max_length, int) or not 1 <= sequence_max_length <= MAX_SEQUENCE_LENGTH:
            raise ValueError("sequence_max_length exceeds sequence bound")
        self._sequence_max_length = sequence_max_length
        # Decision history is observational state and must remain bounded like
        # the symbol/culture decision histories.  Keeping an ordinary list here
        # would make long-lived modeled organisms grow without a ceiling.
        self._sequence_decisions: deque[SequenceDecisionRecord] = deque(maxlen=MAX_HISTORY)
        self._private_learning_last_transition_tick = -1
        self._private_learning_last_corpus_hash: str | None = None
        self._private_learning_latest_transition_tick = -1
        self._private_learning_total_transition_count = 0
        self._private_learning_new_transition_count = 0
        self._private_learning_validation_window: deque[bool] = deque(
            maxlen=_PRIVATE_LEARNING_VALIDATION_WINDOW
        )
        self._private_learning_settled_requests: deque[str] = deque(maxlen=64)

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    @property
    def experience_ledger(self) -> ExperienceLedger:
        return self._experience_ledger

    @property
    def episodic_memory(self) -> EpisodicExperienceMemory:
        """Resident long-horizon experience memory.

        The laboratory may inspect aggregate metrics through passive adapters,
        but episode creation, retrieval, reinterpretation and consolidation are
        organism-owned.
        """
        return self._episodic_memory

    @property
    def social_evidence_ledger(self) -> SocialEvidenceLedger:
        """Private social memory; it is not part of the private SLM corpus."""
        return self._social_evidence_ledger

    @property
    def cultural_policy(self) -> CulturalPolicy:
        """Organism-owned policy; the laboratory can only observe its records."""
        return self._cultural_policy

    @property
    def symbol_grounding_ledger(self) -> SymbolGroundingLedger:
        return self._symbol_grounding_ledger

    @property
    def symbol_policy(self) -> SymbolPolicy:
        return self._symbol_policy

    @property
    def sequence_grounding_ledger(self) -> SequenceGroundingLedger:
        return self._sequence_grounding_ledger

    @property
    def sequence_decisions(self) -> tuple[SequenceDecisionRecord, ...]:
        return tuple(self._sequence_decisions)

    def autonomous_sequence_step(
        self,
        channel: SequenceChannel,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        local_context_tokens: tuple[str, ...],
        tick: int | None = None,
    ) -> SequenceDecisionRecord:
        decision = self.autonomous_sequence_decision(
            neighbors, local_context_tokens=local_context_tokens, tick=tick
        )
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if decision.selected_action is SymbolAction.EMIT and decision.selected_symbols is not None:
            receiver = by_id[decision.selected_recipient_id]
            channel.deliver(SequenceMessage(SymbolSequence(decision.selected_symbols), self.organism_id, receiver.organism_id, current_tick), receiver=receiver.sequence_grounding_ledger, tick=current_tick)
        return decision

    def autonomous_sequence_decision(
        self,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        local_context_tokens: tuple[str, ...],
        tick: int | None = None,
    ) -> SequenceDecisionRecord:
        """Select an opaque sequence without performing transport.

        This is used by controlled permutation experiments; the ordinary
        runtime path remains :meth:`autonomous_sequence_step`, which delivers
        exactly the policy-selected payload.
        """
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if len(by_id) != len(neighbors) or self.organism_id in by_id:
            raise ValueError("invalid sequence neighbor set")
        decision = choose_sequence(self._symbol_policy, local_context_tokens=local_context_tokens, neighbor_ids=by_id, tick=current_tick, max_length=self._sequence_max_length)
        self._sequence_decisions.append(decision)
        return decision

    def observe_sequence_outcome(self, outcome_tokens: tuple[str, ...], *, tick: int | None = None, supported: bool = True) -> None:
        current_tick = self._tick_count if tick is None else tick
        self._sequence_grounding_ledger.observe_outcome(outcome_tokens, tick=current_tick, supported=supported)

    def predict_sequence(self, sequence: SymbolSequence) -> tuple[str, ...] | None:
        return self._sequence_grounding_ledger.predict_exact(sequence)

    def autonomous_retransmit_sequence(self, channel: SequenceChannel, neighbors: tuple["ModeledOrganismRuntime", ...], *, outcome_tokens: tuple[str, ...], tick: int | None = None) -> SequenceDecisionRecord:
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        candidates = [item for item in self._sequence_grounding_ledger.associations if item.outcome_tokens == outcome_tokens and item.support > item.contradiction]
        if not by_id or not candidates:
            decision = choose_sequence(self._symbol_policy, local_context_tokens=(), neighbor_ids=by_id, tick=current_tick)
            self._sequence_decisions.append(decision)
            return decision
        item = max(candidates, key=lambda value: (value.support - value.contradiction, value.last_tick, value.sequence_id))
        recipient_id = max(by_id, key=lambda value: self._symbol_policy._digest((self.organism_id, value, current_tick)))
        digest = self._symbol_policy._digest((item.sequence_id, tuple(sorted(by_id))))
        decision = SequenceDecisionRecord("sequence-decision." + self._symbol_policy._digest((self.organism_id, current_tick, item.sequence_id))[:48], self.organism_id, current_tick, digest, SymbolAction.EMIT, item.sequence_id, item.symbols, recipient_id, len(item.symbols))
        self._sequence_decisions.append(decision)
        receiver = by_id[recipient_id]
        channel.deliver(SequenceMessage(SymbolSequence(item.symbols), self.organism_id, receiver.organism_id, current_tick), receiver=receiver.sequence_grounding_ledger, tick=current_tick, event_kind="RETRANSMIT")
        return decision

    def autonomous_symbol_step(
        self,
        channel: SymbolChannel,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        local_context_token: str,
        tick: int | None = None,
    ) -> SymbolDecisionRecord:
        """Select and emit an opaque symbol from local state only."""
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if len(by_id) != len(neighbors) or self.organism_id in by_id:
            raise ValueError("invalid symbol neighbor set")
        decision = self._symbol_policy.choose(
            local_context_token=local_context_token, neighbor_ids=by_id, tick=current_tick
        )
        if decision.selected_action is SymbolAction.EMIT:
            receiver = by_id[decision.selected_recipient_id]
            channel.deliver(
                SymbolMessage(decision.selected_symbol_id, self.organism_id, receiver.organism_id, current_tick),
                receiver=receiver.symbol_grounding_ledger,
                tick=current_tick,
            )
        return decision

    def observe_symbolic_outcome(self, outcome_token: str, *, tick: int | None = None, supported: bool = True) -> None:
        current_tick = self._tick_count if tick is None else tick
        self._symbol_grounding_ledger.observe_outcome(outcome_token, tick=current_tick, supported=supported)

    def autonomous_grounded_symbol_step(
        self,
        channel: SymbolChannel,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        outcome_token: str,
        tick: int | None = None,
    ) -> SymbolDecisionRecord:
        """Retransmit a symbol selected from a locally learned association."""
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if len(by_id) != len(neighbors) or self.organism_id in by_id:
            raise ValueError("invalid symbol neighbor set")
        decision = self._symbol_policy.choose_grounded(
            self._symbol_grounding_ledger,
            outcome_token=outcome_token,
            neighbor_ids=by_id,
            tick=current_tick,
        )
        if decision.selected_action is SymbolAction.EMIT:
            receiver = by_id[decision.selected_recipient_id]
            channel.deliver(
                SymbolMessage(decision.selected_symbol_id, self.organism_id, receiver.organism_id, current_tick),
                receiver=receiver.symbol_grounding_ledger,
                tick=current_tick,
            )
        return decision

    def predict_symbolic_outcome(self, symbol_id: str) -> str | None:
        return self._symbol_grounding_ledger.predict(symbol_id)

    def autonomous_adaptive_symbol_step(
        self,
        channel: SymbolChannel,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        local_context_token: str,
        tick: int | None = None,
    ) -> SymbolDecisionRecord:
        """Select and emit an opaque symbol using locally accumulated emission bias."""
        current_tick = self._tick_count if tick is None else tick
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if len(by_id) != len(neighbors) or self.organism_id in by_id:
            raise ValueError("invalid symbol neighbor set")
        decision = self._symbol_policy.choose_adaptive(
            local_context_token=local_context_token, neighbor_ids=by_id, tick=current_tick
        )
        if decision.selected_action is SymbolAction.EMIT:
            receiver = by_id[decision.selected_recipient_id]
            channel.deliver(
                SymbolMessage(decision.selected_symbol_id, self.organism_id, receiver.organism_id, current_tick),
                receiver=receiver.symbol_grounding_ledger,
                tick=current_tick,
            )
        return decision

    def report_symbol_reinforcement(self, signal: SymbolReinforcementSignal) -> None:
        """Apply a receiver's own success report to this organism's emission policy."""
        if signal.sender_id != self.organism_id:
            raise ValueError("symbol reinforcement sender ownership mismatch")
        self._symbol_policy.reinforce(
            local_context_token=signal.context_token,
            symbol_id=signal.symbol_id,
            success=signal.success,
            tick=signal.tick,
        )

    def autonomous_cultural_step(
        self,
        channel: SocialChannel,
        neighbors: tuple["ModeledOrganismRuntime", ...],
        *,
        tick: int | None = None,
    ) -> tuple[CulturalDecisionRecord, ...]:
        """Take one bounded local cultural turn.

        ``neighbors`` is topology supplied by the laboratory.  Content,
        recipient, composition and silence are selected by the organism-side
        policy; no claim/composite identifier is accepted by this method.
        """
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot take cultural actions")
        current_tick = self._tick_count if tick is None else tick
        if isinstance(current_tick, bool) or not isinstance(current_tick, int) or current_tick < 0:
            raise ValueError("cultural action tick must be non-negative")
        by_id = {neighbor.organism_id: neighbor for neighbor in neighbors}
        if len(by_id) != len(neighbors) or self.organism_id in by_id:
            raise ValueError("invalid cultural neighbor set")
        decisions: list[CulturalDecisionRecord] = []
        composition_record, claim_ids, parent_ids = self._cultural_policy.composition(
            self._social_evidence_ledger, tick=current_tick
        )
        decisions.append(composition_record)
        if composition_record.selected_action is CulturalAction.COMPOSE:
            self.compose_cultural_claims(
                claim_ids, parent_composite_ids=parent_ids,
                operation="extend" if parent_ids else "combine",
            )
        transmission = self._cultural_policy.transmission(
            self._social_evidence_ledger, by_id, tick=current_tick
        )
        decisions.append(transmission)
        if transmission.selected_action is CulturalAction.TRANSMIT and transmission.selected_recipient_id:
            receiver = by_id[transmission.selected_recipient_id]
            item_id = transmission.selected_item_ids[0]
            try:
                if item_id.startswith("composite."):
                    self.transmit_cultural_composite(channel, item_id, receiver=receiver)
                else:
                    self.transmit_social_claim(channel, item_id, receiver=receiver)
            except ValueError as exc:
                # Repeated delivery is a local transport outcome, not a reason
                # to let the policy bypass the channel or mutate provenance.
                if "duplicate" not in str(exc):
                    raise
        return tuple(decisions)

    def autonomous_retention_step(self, *, tick: int | None = None) -> CulturalDecisionRecord:
        current_tick = self._tick_count if tick is None else tick
        record = self._cultural_policy.retention(self._social_evidence_ledger, tick=current_tick)
        if record.selected_action is CulturalAction.DROP:
            for item_id in record.selected_item_ids:
                if item_id in {claim.claim_id for claim in self._social_evidence_ledger.claims}:
                    self._social_evidence_ledger.drop_claim(item_id)
                elif self._social_evidence_ledger.composite_graph.get(item_id) is not None:
                    self._social_evidence_ledger.retire_composite(item_id, tick=current_tick)
        return record

    def autonomous_validation_proposal(self, *, tick: int | None = None) -> CulturalDecisionRecord:
        current_tick = self._tick_count if tick is None else tick
        return self._cultural_policy.validation(self._social_evidence_ledger, tick=current_tick)

    def originate_social_claim(self, *, proposition_tokens: tuple[str, ...], evidence_id: str, confidence_class: int = 0) -> SocialClaim:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot originate social claims")
        return self._social_evidence_ledger.originate(
            proposition_tokens=proposition_tokens,
            evidence_id=evidence_id,
            tick=self._tick_count,
            confidence_class=confidence_class,
        )

    def receive_social_claim(self, claim: SocialClaim, *, sender_id: str, tick: int | None = None) -> SocialClaim:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot receive social claims")
        return self._social_evidence_ledger.receive(
            claim, sender_id=sender_id, tick=self._tick_count if tick is None else tick
        )

    def transmit_social_claim(self, channel: SocialChannel, claim_id: str, *, receiver: "ModeledOrganismRuntime") -> DeliveryResult:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot transmit social claims")
        if not isinstance(receiver, ModeledOrganismRuntime):
            raise ValueError("social receiver must be a modeled organism runtime")
        result = channel.deliver(
            self._social_evidence_ledger.retransmit(
                claim_id, receiver_id=receiver.organism_id, tick=self._tick_count
            ),
            sender_id=self.organism_id,
            receiver=receiver.social_evidence_ledger,
            tick=self._tick_count,
            source=self._social_evidence_ledger,
        )
        self._charge_metabolism("cognition", self._social_exchange_cost)
        return result

    def compose_cultural_claims(self, claim_ids: tuple[str, ...] = (), *, parent_composite_ids: tuple[str, ...] = (), operation: str = "combine", retired: bool = False, replace_component_claim_ids: tuple[str, ...] = ()) -> CulturalComposite:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot compose cultural claims")
        composite = self._social_evidence_ledger.compose(
            claim_ids, parent_composite_ids=parent_composite_ids, tick=self._tick_count,
            operation=operation, retired=retired, replace_component_claim_ids=replace_component_claim_ids,
        )
        self._charge_metabolism("cognition", self._social_exchange_cost)
        return composite

    def transmit_cultural_composite(self, channel: SocialChannel, composite_id: str, *, receiver: "ModeledOrganismRuntime") -> DeliveryResult:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot transmit cultural composites")
        if not isinstance(receiver, ModeledOrganismRuntime):
            raise ValueError("cultural receiver must be a modeled organism runtime")
        composite = self._social_evidence_ledger.composite_graph.get(composite_id)
        if composite is None:
            raise ValueError("unknown cultural composite")
        result = channel.deliver_composite(
            composite, sender_id=self.organism_id, receiver=receiver.social_evidence_ledger,
            tick=self._tick_count, source=self._social_evidence_ledger,
        )
        self._charge_metabolism("cognition", self._social_exchange_cost)
        return result

    def record_experience(self, record: ExperienceRecord) -> None:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot record new experience")
        self._experience_ledger.append(record)
        if (
            record.record_id.startswith("transition.")
            and record.epistemic_status is EpistemicStatus.OBSERVED
            and record.source_kind is not SourceKind.MODEL
        ):
            # Episodic memory sees only independently observed causal records.
            # Model proposals/validations never become lived experience.
            finalized_episode = self._episodic_memory.observe(record)
            self._refresh_episodic_interpretations()
            if finalized_episode is not None:
                self._project_episodic_consolidation()
            self._private_learning_total_transition_count += 1
            self._private_learning_new_transition_count += 1
            self._private_learning_latest_transition_tick = max(
                self._private_learning_latest_transition_tick,
                record.tick_class,
            )
        elif (
            record.record_id.startswith("validation.")
            and record.source_kind is SourceKind.MODEL
            and record.epistemic_status in {
                EpistemicStatus.SUPPORTED,
                EpistemicStatus.CONTRADICTED,
            }
        ):
            self._private_learning_validation_window.append(
                record.epistemic_status is EpistemicStatus.CONTRADICTED
            )

    def _refresh_episodic_interpretations(self) -> int:
        """Let newly learned graph representations reinterpret old experience.

        Concept lineage is generic cognitive provenance, not semantic ground
        truth. The factual episode core stays immutable; only a revisable
        interpretation index is extended.
        """
        bridge = getattr(self, "_cognitive_bridge", None)
        if bridge is None:
            return 0
        changed = 0
        lineages = bridge.concept_lineage
        # Concept lineage may contain concepts built from older concepts.
        # Iterate to a fixed point so retrospective indexing can propagate
        # through the hierarchy without depending on lexical concept IDs.
        for _pass in range(max(1, len(lineages))):
            pass_changed = 0
            for lineage in lineages:
                support: list[str] = []
                for parent_id in lineage.parent_ids:
                    support.extend(
                        (
                            parent_id,
                            f"sense.{parent_id}",
                            f"concept.{parent_id}",
                        )
                    )
                pass_changed += self._episodic_memory.reinterpret(
                    lineage.concept_id,
                    tuple(support),
                    min_overlap=0.5,
                )
            changed += pass_changed
            if pass_changed == 0:
                break
        return changed

    @staticmethod
    def _episodic_graph_sense_ids(context_tokens: tuple[str, ...]) -> tuple[str, ...]:
        """Map private opaque context tokens back to existing graph sense ids."""
        return tuple(sorted({
            token.removeprefix("sense.")
            for token in context_tokens
            if token.startswith("sense.") and len(token) > len("sense.")
        }))

    def _project_episodic_consolidation(self) -> int:
        """Expose consolidated episodic co-occurrence to normal concept formation."""
        bridge = getattr(self, "_cognitive_bridge", None)
        if bridge is None:
            return 0
        gained = 0
        for contingency in self._episodic_memory.consolidated:
            source_ids = self._episodic_graph_sense_ids(
                contingency.context_tokens
            )
            gained += bridge.observe_retrospective_support(
                source_ids,
                support_epochs=contingency.support_epochs,
            )
        return gained

    def recall_experiences(
        self,
        context_tokens: tuple[str, ...],
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[EpisodeMatch, ...]:
        """Retrieve similar lived episodes without selecting or executing an action."""
        if self._physiology.state is VitalState.DEAD:
            return ()
        return self._episodic_memory.retrieve(
            context_tokens,
            action_token=action_token,
            k=k,
        )

    def predict_from_experience(
        self,
        context_tokens: tuple[str, ...],
        *,
        action_token: str | None,
        k: int | None = None,
    ) -> EpisodicPrediction | None:
        """State-conditioned prediction from lived experience only."""
        if self._physiology.state is VitalState.DEAD:
            return None
        return self._episodic_memory.predict(
            context_tokens,
            action_token=action_token,
            k=k,
        )

    def cognitive_replay(
        self,
        context_tokens: tuple[str, ...],
        *,
        action_token: str | None = None,
        k: int | None = None,
    ) -> tuple[CognitiveReplay, ...]:
        """Reactivate past episode representations without motor execution."""
        if self._physiology.state is VitalState.DEAD:
            return ()
        return self._episodic_memory.cognitive_replay(
            context_tokens,
            action_token=action_token,
            k=k,
        )

    def episodic_memory_snapshot(self) -> dict[str, object]:
        """Passive, aggregate Observatory surface with no control path."""
        metrics = self._episodic_memory.metrics(current_tick=self._tick_count)
        return {
            "schema_version": self._episodic_memory.SCHEMA_VERSION,
            "episode_count": metrics.episode_count,
            "pending_records": metrics.pending_records,
            "compressed_episode_count": metrics.compressed_episode_count,
            "interpretation_count": metrics.interpretation_count,
            "consolidated_contingencies": metrics.consolidated_contingencies,
            "retrieval_count": metrics.retrieval_count,
            "replay_count": metrics.replay_count,
            "compaction_count": metrics.compaction_count,
            "eviction_count": metrics.eviction_count,
            "oldest_episode_age": metrics.oldest_episode_age,
            "mean_episode_age": metrics.mean_episode_age,
        }

    def build_private_corpus(self, *, max_records: int = 8192) -> TrainingCorpus:
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or not 3 <= max_records <= 65536
        ):
            raise ValueError("max_records must be an integer within [3, 65536]")

        # The live ledger is intentionally short and causal. Episodic memory
        # extends the organism's usable past after older causal records age out
        # of that ledger. Never duplicate a lived record or overwrite a
        # conflicting record id silently.
        combined: dict[str, ExperienceRecord] = {}
        for record in self._episodic_memory.replay_records(max_records=max_records):
            combined[record.record_id] = record
        for record in self._experience_ledger.records:
            previous = combined.get(record.record_id)
            if previous is not None and previous.content_hash != record.content_hash:
                raise ValueError("episodic/live experience record mismatch")
            combined[record.record_id] = record

        ordered = sorted(
            combined.values(),
            key=lambda record: (record.tick_class, record.record_id),
        )
        # Keep the most recent bounded causal history. Older episodes remain in
        # episodic memory and can re-enter future corpora as capacity permits.
        selected = tuple(ordered[-max_records:])
        return build_training_corpus(selected, max_records=max_records)

    def build_private_tokenizer(self, corpus: TrainingCorpus | None = None) -> NativeTokenizer:
        selected = corpus or self.build_private_corpus()
        return NativeTokenizer.from_records(selected.train)

    def attach_private_model_bridge(self, bridge: PrivateModelBridge | None) -> None:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot attach model inference")
        if bridge is not None and not isinstance(bridge, PrivateModelBridge):
            raise ValueError("bridge must be a PrivateModelBridge")
        self._private_model_bridge = bridge

    def _private_causal_records(self) -> tuple[ExperienceRecord, ...]:
        """Return only independently observed temporal transitions."""
        return tuple(
            record
            for record in self._experience_ledger.records
            if record.record_id.startswith("transition.")
            and record.epistemic_status is EpistemicStatus.OBSERVED
            and record.source_kind is not SourceKind.MODEL
        )

    def _private_validation_contradiction_ratio(self) -> tuple[int, float]:
        count = len(self._private_learning_validation_window)
        if count == 0:
            return 0, 0.0
        contradictions = sum(self._private_learning_validation_window)
        return count, contradictions / count

    def autonomous_private_learning_plan(self) -> AutonomousTrainingPlan | None:
        """Create one endogenous bounded replay/training plan when warranted.

        The trigger uses only this organism's own causal transitions and
        independently validated model outcomes. No wall-clock cadence, task
        reward, evaluator label, or laboratory-selected target enters here.
        """
        if self._physiology.state is VitalState.DEAD:
            return None

        if (
            self._private_learning_total_transition_count
            < _PRIVATE_LEARNING_MIN_BOOTSTRAP_TRANSITIONS
        ):
            return None

        latest_tick = self._private_learning_latest_transition_tick
        new_transitions = self._private_learning_new_transition_count
        active = self._model_registry.active
        validation_count, contradiction_ratio = (
            self._private_validation_contradiction_ratio()
        )

        reason: str | None = None
        if active is None:
            if new_transitions >= _PRIVATE_LEARNING_MIN_BOOTSTRAP_TRANSITIONS:
                reason = "bootstrap-experience"
        elif new_transitions >= _PRIVATE_LEARNING_FORCE_NEW_TRANSITIONS:
            reason = "accumulated-experience"
        elif (
            new_transitions >= _PRIVATE_LEARNING_MIN_NEW_TRANSITIONS
            and validation_count >= _PRIVATE_LEARNING_MIN_VALIDATIONS
            and contradiction_ratio >= _PRIVATE_LEARNING_CONTRADICTION_TRIGGER
        ):
            reason = "prediction-revision"

        if reason is None:
            return None

        transitions = self._private_causal_records()
        corpus = build_training_corpus(transitions)
        if corpus.manifest.corpus_hash == self._private_learning_last_corpus_hash:
            return None
        tokenizer = NativeTokenizer.from_records(corpus.train)
        seed = (
            int.from_bytes(
                hashlib.sha256(
                    (
                        f"{self.organism_id}:{latest_tick}:"
                        f"{corpus.manifest.corpus_hash}:{reason}"
                    ).encode("utf-8")
                ).digest()[:8],
                "big",
            )
            & 0x7FFFFFFF
        )
        experience_pressure = min(
            1.0,
            new_transitions / float(_PRIVATE_LEARNING_FORCE_NEW_TRANSITIONS),
        )
        contradiction_pressure = (
            contradiction_ratio
            if validation_count >= _PRIVATE_LEARNING_MIN_VALIDATIONS
            else 0.0
        )
        replay_pressure = max(experience_pressure, contradiction_pressure)
        requested_epochs = 2 + round(6 * replay_pressure)
        requested_steps = 12 + round(36 * replay_pressure)
        request = self.request_private_model_training(
            corpus_hash=corpus.manifest.corpus_hash,
            tokenizer_hash=tokenizer.tokenizer_hash,
            architecture_id=ArchitectureId.GRU_V1,
            context_window=96,
            requested_parameters=1_000_000,
            requested_epochs=requested_epochs,
            requested_steps=requested_steps,
            seed=seed,
            autonomous_stopping=True,
            requested_patience=2,
            requested_min_validation_gain=0.005,
        )
        self._private_learning_last_transition_tick = latest_tick
        self._private_learning_last_corpus_hash = corpus.manifest.corpus_hash
        self._private_learning_new_transition_count = 0
        return AutonomousTrainingPlan(
            request=request,
            corpus=corpus,
            tokenizer=tokenizer,
            reason=reason,
            transition_count=len(transitions),
            new_transition_count=new_transitions,
            contradiction_ratio=contradiction_ratio,
            replay_pressure=replay_pressure,
        )

    def request_private_model_training(
        self,
        *,
        corpus_hash: str,
        tokenizer_hash: str,
        architecture_id: ArchitectureId,
        context_window: int,
        requested_parameters: int,
        requested_epochs: int,
        requested_steps: int,
        seed: int,
        parent_model_id: str | None = None,
        adaptation_reason: str | None = None,
        autonomous_stopping: bool = False,
        requested_patience: int = 4,
        requested_min_validation_gain: float = 1e-9,
    ) -> TrainingRequest:
        """Create a bounded external training request and pay local opportunity cost."""

        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot request model training")
        if parent_model_id is not None:
            parent = self._model_registry.get(parent_model_id)
            if parent is None or parent.state is not ModelState.ACTIVE:
                raise ValueError("parent-bearing requests require this organism's active model")
            if adaptation_reason is None:
                raise ValueError("parent-bearing requests require an adaptation reason")
        elif adaptation_reason is not None:
            raise ValueError("adaptation_reason requires a parent model")
        request = TrainingRequest(
            organism_id=self.organism_id,
            corpus_hash=corpus_hash,
            tokenizer_hash=tokenizer_hash,
            architecture_id=architecture_id,
            objective=ModelObjective.NEXT_TOKEN,
            seed=seed,
            context_window=context_window,
            requested_parameters=requested_parameters,
            requested_epochs=requested_epochs,
            requested_steps=requested_steps,
            created_tick_class=self._tick_count,
            parent_model_id=parent_model_id,
            adaptation_reason=adaptation_reason,
            autonomous_stopping=autonomous_stopping,
            requested_patience=requested_patience,
            requested_min_validation_gain=requested_min_validation_gain,
        )
        structural_fraction = min(0.20, requested_parameters / 50_000_000.0)
        self._charge_metabolism("cognition", self._model_request_base_cost + structural_fraction)
        self._charge_metabolism("persistence", self._model_request_base_cost * 0.5)
        return request

    def settle_private_model_training_compute(
        self,
        *,
        request_id: str,
        steps_completed: int,
    ) -> bool:
        """Charge replay compute once, from work actually executed by the substrate."""
        if (
            not isinstance(request_id, str)
            or len(request_id) != 64
            or any(char not in "0123456789abcdef" for char in request_id)
        ):
            raise ValueError("request_id must be a lowercase sha256 digest")
        if (
            isinstance(steps_completed, bool)
            or not isinstance(steps_completed, int)
            or steps_completed < 0
        ):
            raise ValueError("steps_completed must be a non-negative integer")
        if request_id in self._private_learning_settled_requests:
            return False
        self._charge_metabolism(
            "cognition",
            min(0.20, steps_completed / 100_000.0),
        )
        self._private_learning_settled_requests.append(request_id)
        return True

    def request_private_model_adaptation(
        self,
        *,
        parent_model_id: str,
        corpus_hash: str,
        tokenizer_hash: str,
        architecture_id: ArchitectureId,
        context_window: int,
        requested_parameters: int,
        requested_epochs: int,
        requested_steps: int,
        seed: int,
        adaptation_reason: str,
        autonomous_stopping: bool = False,
        requested_patience: int = 4,
        requested_min_validation_gain: float = 1e-9,
    ) -> TrainingRequest:
        """Request bounded adaptation of this organism's active private model."""
        parent = self._model_registry.get(parent_model_id)
        if parent is None or parent.state is not ModelState.ACTIVE:
            raise ValueError("adaptation parent must be this organism's active model")
        return self.request_private_model_training(
            corpus_hash=corpus_hash,
            tokenizer_hash=tokenizer_hash,
            architecture_id=architecture_id,
            context_window=context_window,
            requested_parameters=requested_parameters,
            requested_epochs=requested_epochs,
            requested_steps=requested_steps,
            seed=seed,
            parent_model_id=parent_model_id,
            adaptation_reason=adaptation_reason,
            autonomous_stopping=autonomous_stopping,
            requested_patience=requested_patience,
            requested_min_validation_gain=requested_min_validation_gain,
        )

    def adopt_private_model(
        self,
        artifact: ModelArtifactManifest,
        *,
        evaluation_summary: tuple[int, ...] = (),
    ) -> ModelRecord:
        """Adopt a verified external artifact as SHADOW, never directly ACTIVE."""

        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot adopt model artifacts")
        if artifact.organism_id != self.organism_id:
            raise ValueError("private model artifact belongs to a different organism")
        if artifact.parent_model_id is not None:
            parent = self._model_registry.get(artifact.parent_model_id)
            if parent is None or parent.organism_id != self.organism_id:
                raise ValueError("private model artifact parent is not owned by this organism")
            if parent.architecture_id is not artifact.architecture_id or parent.tokenizer_hash != artifact.tokenizer_hash:
                raise ValueError("private model artifact parent is structurally incompatible")
        storage_fraction = min(0.20, artifact.artifact_bytes / float(256 * 1024 * 1024))
        self._charge_metabolism("persistence", self._model_storage_scale + storage_fraction)
        record = self._model_registry.register(artifact)
        if record.state is ModelState.CANDIDATE:
            record = self._model_registry.transition(
                record.model_id,
                ModelState.SHADOW,
                evaluation_summary=evaluation_summary,
            )
        return record

    def private_model_observations(self) -> tuple[dict[str, object], ...]:
        """Return passive, weight-free model status for the Observatory."""
        return tuple({
            "model_id": record.model_id,
            "parent_model_id": record.parent_model_id,
            "generation": record.generation,
            "state": record.state.value,
            "evaluation_summary": list(record.evaluation_summary),
            "adaptation_count": record.generation,
        } for record in self._model_registry.records)

    def cultural_observations(self) -> dict[str, object]:
        """Passive, weight-free cultural lineage for Observatory projection."""
        ledger = self._social_evidence_ledger
        claims = ledger.claims
        composites = ledger.composites
        assessments = ledger.assessments
        roots = set()
        for claim in claims:
            roots.update(ledger.graph.root_evidence_ids(claim))
        roots.update(item.evidence_id for item in assessments)
        return {
            "claim_count": len(claims),
            "composite_count": len(composites),
            "unique_contributors": len({organism_id for item in composites for organism_id in item.contributing_organism_ids}),
            "cultural_generation": max((item.generation for item in composites), default=0),
            "unique_roots": len(roots),
            "independent_roots": len(roots),
            "transmission_depth": max((claim.transmission_depth for claim in claims), default=0),
            "mutation_depth": max((claim.mutation_depth for claim in claims), default=0),
            "confirmed_locally": sum(item.status is SocialEpistemicStatus.SOCIAL_SUPPORTED for item in assessments),
            "contradicted_locally": sum(item.status is SocialEpistemicStatus.SOCIAL_CONTRADICTED for item in assessments),
            "freshness": tuple({
                "claim_id": claim.claim_id,
                "value": ledger.freshness(claim.claim_id, current_tick=self._tick_count),
            } for claim in claims),
            "claim_lineage": tuple({
                "claim_id": claim.claim_id,
                "source": claim.source_organism_id,
                "parents": claim.parent_claim_ids,
                "roots": ledger.graph.root_evidence_ids(claim),
            } for claim in claims),
            "composite_lineage": tuple({
                "composite_id": item.composite_id,
                "components": item.component_claim_ids,
                "parents": item.parent_composite_ids,
                "contributors": item.contributing_organism_ids,
                "roots": ledger.composite_graph.root_evidence_ids(item),
                "generation": item.generation,
                "retired": item.retired,
            } for item in composites),
            "cultural_decisions": tuple({
                "decision_id": item.decision_id,
                "tick": item.decision_tick,
                "action": item.selected_action.value,
                "items": item.selected_item_ids,
                "recipient": item.selected_recipient_id,
                "cost": item.cost,
            } for item in self._cultural_policy.decisions),
            "cultural_policy_cost": self._cultural_policy.cost,
            "symbols_known": len({item.symbol_id for item in self._symbol_grounding_ledger.exposures}),
            "symbols_emitted": sum(record.selected_action is SymbolAction.EMIT for record in self._symbol_policy.decisions),
            "symbol_exposures": len(self._symbol_grounding_ledger.exposures),
            "grounding_updates": len(self._symbol_grounding_ledger.associations),
            "symbol_grounding": tuple({
                "symbol_id": item.symbol_id,
                "support": item.support,
                "contradiction": item.contradiction,
                "strength": max(0, item.support - item.contradiction),
            } for item in self._symbol_grounding_ledger.associations),
            "symbol_decisions": tuple({
                "decision_id": record.decision_id,
                "tick": record.decision_tick,
                "action": record.selected_action.value,
                "symbol_id": record.selected_symbol_id,
                "recipient_id": record.selected_recipient_id,
                "cost": record.cost,
            } for record in self._symbol_policy.decisions),
            "symbol_policy_cost": self._symbol_policy.cost,
            "sequences_known": len({item.sequence.sequence_id for item in self._sequence_grounding_ledger.exposures}),
            "sequence_emissions": sum(record.selected_action is SymbolAction.EMIT for record in self._sequence_decisions),
            "sequence_exposures": len(self._sequence_grounding_ledger.exposures),
            "sequence_grounding_updates": len(self._sequence_grounding_ledger.associations),
            "sequence_grounding": tuple({
                "sequence_id": item.sequence_id,
                "length": len(item.symbols),
                "support": item.support,
                "contradiction": item.contradiction,
                "strength": max(0, item.support - item.contradiction),
            } for item in self._sequence_grounding_ledger.associations),
            "sequence_decisions": tuple({
                "decision_id": item.decision_id,
                "tick": item.decision_tick,
                "action": item.selected_action.value,
                "sequence_id": item.selected_sequence_id,
                "recipient_id": item.selected_recipient_id,
                "cost": item.cost,
            } for item in self._sequence_decisions),
            "sequence_policy_cost": sum(item.cost for item in self._sequence_decisions),
        }

    def activate_private_model(
        self,
        model_id: str,
        *,
        promotion_authorized: bool,
        evaluation_summary: tuple[int, ...] = (),
    ) -> ModelRecord:
        """Activate only after an independent held-out promotion decision."""

        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot activate private models")
        return self._model_registry.transition(
            model_id,
            ModelState.ACTIVE,
            promotion_authorized=promotion_authorized,
            evaluation_summary=evaluation_summary,
        )

    def retire_private_model(self, model_id: str) -> ModelRecord:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot change private model state")
        return self._model_registry.transition(model_id, ModelState.RETIRED)

    def shadow_private_prediction(
        self,
        context_tokens: tuple[str, ...],
        *,
        model_id: str,
        target_token: str = "<NEXT>",
    ) -> ModelPredictionProposal:
        if self._private_model_bridge is None:
            raise ValueError("no private model inference bridge is attached")
        return self._private_model_bridge.predict(
            context_tokens,
            model_id=model_id,
            target_token=target_token,
            allow_shadow=True,
        )

    def active_private_prediction(
        self,
        context_tokens: tuple[str, ...],
        *,
        target_token: str = "<NEXT>",
        record: bool = True,
    ) -> ModelPredictionProposal:
        if self._private_model_bridge is None:
            raise ValueError("no private model inference bridge is attached")
        active = self._model_registry.active
        if active is None:
            raise ValueError("no active private model")
        proposal = self._private_model_bridge.predict(
            context_tokens,
            model_id=active.model_id,
            target_token=target_token,
            allow_shadow=False,
        )
        if record:
            digest = hashlib.sha256(
                f"{proposal.model_id}:{self._tick_count}:{context_tokens}:{proposal.predicted_token}".encode("utf-8")
            ).hexdigest()[:24]
            self.record_experience(ExperienceRecord(
                record_id=f"model.{digest}",
                organism_id=self.organism_id,
                tick_class=self._tick_count,
                context_tokens=context_tokens,
                action_token=None,
                outcome_tokens=(proposal.predicted_token,),
                epistemic_status=EpistemicStatus.PREDICTED,
                evidence_refs=(),
                confidence_class=proposal.confidence_class,
                source_kind=SourceKind.MODEL,
            ))
        return proposal

    def active_private_counterfactual(
        self,
        context_tokens: tuple[str, ...],
        *,
        action_token: str,
        target_token: str = "<OUTCOME>",
    ) -> ModelPredictionProposal:
        """Query the ACTIVE model counterfactually — without recording anything.

        This is the agency imagination path:

            <BOS> <context> <SEP> action_token <EPI:observed> <SRC:action_outcome>

        A counterfactual is never an ExperienceRecord; it must not enter the
        ledger, trigger training, or update any model statistics. The clear
        separation between ``active_private_prediction()`` (which records by
        default) and this method makes the boundary unambiguous.

        Requirements:
        - An ACTIVE private model must exist.
        - A PrivateModelBridge must be attached.
        - The organism must be alive (SHADOW models are never used here).
        - ``action_token`` must be a printable ASCII token bounded to 96 chars.
        - Never calls record_experience().
        """
        from ..core.embodiment.physiology import VitalState
        if self._physiology.state is VitalState.DEAD:
            raise ValueError("counterfactual inference is not permitted after death")
        if self._private_model_bridge is None:
            raise ValueError("no private model inference bridge is attached")
        active = self._model_registry.active
        if active is None:
            raise ValueError("no active private model for counterfactual")
        # Validate action_token: printable ASCII, bounded
        if (
            not isinstance(action_token, str)
            or not action_token
            or len(action_token) > 96
            or any(ord(c) < 33 or ord(c) > 126 for c in action_token)
        ):
            raise ValueError(
                "action_token must be a bounded printable ASCII string"
            )
        # Build the counterfactual prefix exactly matching the training schema
        from .experience import EpistemicStatus, SourceKind
        prefix = (
            "<BOS>",
            *context_tokens,
            "<SEP>",
            action_token,
            f"<EPI:{EpistemicStatus.OBSERVED.value}>",
            f"<SRC:{SourceKind.ACTION_OUTCOME.value}>",
        )
        # ACTIVE only, no SHADOW, record=False implicit (bridge.predict is stateless)
        return self._private_model_bridge.predict(
            prefix,
            model_id=active.model_id,
            target_token=target_token,
            allow_shadow=False,
        )

    def validate_model_prediction(
        self,
        prediction_record_id: str,
        *,
        supported: bool,
        evidence_refs: tuple[str, ...],
    ) -> ExperienceRecord:
        """Append independent validation; never mutate the original model proposal."""

        original = self._experience_ledger.get(prediction_record_id)
        if original is None or original.source_kind is not SourceKind.MODEL:
            raise ValueError("unknown model prediction record")
        if original.epistemic_status is not EpistemicStatus.PREDICTED:
            raise ValueError("only raw model predictions can be validated")
        status = EpistemicStatus.SUPPORTED if supported else EpistemicStatus.CONTRADICTED
        digest = hashlib.sha256(
            f"{prediction_record_id}:{status.value}:{evidence_refs}".encode("utf-8")
        ).hexdigest()[:24]
        validated = ExperienceRecord(
            record_id=f"validation.{digest}",
            organism_id=self.organism_id,
            tick_class=self._tick_count,
            context_tokens=original.context_tokens,
            action_token=None,
            outcome_tokens=original.outcome_tokens,
            epistemic_status=status,
            evidence_refs=evidence_refs,
            confidence_class=original.confidence_class,
            source_kind=SourceKind.MODEL,
        )
        self.record_experience(validated)
        return validated

    def checkpoint(self) -> dict[str, Any]:
        payload = super().checkpoint()
        payload["private_model_registry"] = self._model_registry.checkpoint()
        payload["experience_ledger"] = self._experience_ledger.checkpoint()
        payload["episodic_memory"] = self._episodic_memory.checkpoint()
        payload["social_evidence_ledger"] = self._social_evidence_ledger.checkpoint()
        payload["private_model_config"] = {
            "model_request_base_cost": self._model_request_base_cost,
            "model_storage_scale": self._model_storage_scale,
        }
        payload["private_learning_state"] = {
            "last_transition_tick": self._private_learning_last_transition_tick,
            "last_corpus_hash": self._private_learning_last_corpus_hash,
            "latest_transition_tick": self._private_learning_latest_transition_tick,
            "total_transition_count": self._private_learning_total_transition_count,
            "new_transition_count": self._private_learning_new_transition_count,
            "validation_window": list(self._private_learning_validation_window),
            "settled_request_ids": list(self._private_learning_settled_requests),
        }
        payload["cultural_policy"] = self._cultural_policy.checkpoint()
        payload["symbol_grounding_ledger"] = self._symbol_grounding_ledger.checkpoint()
        payload["symbol_policy"] = self._symbol_policy.checkpoint()
        payload["sequence_grounding_ledger"] = self._sequence_grounding_ledger.checkpoint()
        payload["sequence_max_length"] = self._sequence_max_length
        payload["sequence_decisions"] = [item.__dict__ if hasattr(item, "__dict__") else {field: getattr(item, field) for field in item.__dataclass_fields__} for item in self._sequence_decisions]
        return payload

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any], **kwargs: Any) -> "ModeledOrganismRuntime":
        raw_config = payload.get("private_model_config", {}) if isinstance(payload, dict) else {}
        if raw_config is not None and not isinstance(raw_config, dict):
            raise ValueError("invalid private model configuration checkpoint")
        constructor = dict(kwargs)
        if "model_request_base_cost" not in constructor:
            constructor["model_request_base_cost"] = float(raw_config.get("model_request_base_cost", 0.01))
        if "model_storage_scale" not in constructor:
            constructor["model_storage_scale"] = float(raw_config.get("model_storage_scale", 0.02))
        if "sequence_max_length" not in constructor:
            constructor["sequence_max_length"] = payload.get("sequence_max_length", MAX_SEQUENCE_LENGTH)
        runtime = super().from_checkpoint(payload, **constructor)
        if not isinstance(runtime, cls):
            raise RuntimeError("modeled runtime restore returned wrong runtime type")
        runtime._model_registry = ModelRegistry.restore(
            payload.get("private_model_registry"),
            organism_id=runtime.organism_id,
        )
        runtime._experience_ledger = ExperienceLedger.restore(
            payload.get("experience_ledger"),
            organism_id=runtime.organism_id,
        )
        raw_episodic_memory = payload.get("episodic_memory")
        runtime._episodic_memory = EpisodicExperienceMemory.restore(
            raw_episodic_memory,
            organism_id=runtime.organism_id,
            kernel_limits=runtime._kernel_limits,
        )
        if raw_episodic_memory is None:
            # One-way migration for checkpoints created before episodic memory
            # existed. Reconstruct only from the bounded causal ledger already
            # owned by the organism; no lab/world data is imported.
            for record in runtime._experience_ledger.records:
                runtime._episodic_memory.observe(record)
            runtime._episodic_memory.flush()
        runtime._project_episodic_consolidation()
        runtime._social_evidence_ledger = SocialEvidenceLedger.restore(
            payload.get("social_evidence_ledger"), organism_id=runtime.organism_id
        )
        runtime._cultural_policy = CulturalPolicy.restore(
            payload.get("cultural_policy"), organism_id=runtime.organism_id
        )
        runtime._symbol_grounding_ledger = SymbolGroundingLedger.restore(
            payload.get("symbol_grounding_ledger"), organism_id=runtime.organism_id
        )
        runtime._symbol_policy = SymbolPolicy.restore(
            payload.get("symbol_policy"), organism_id=runtime.organism_id
        )
        runtime._sequence_grounding_ledger = SequenceGroundingLedger.restore(
            payload.get("sequence_grounding_ledger"), organism_id=runtime.organism_id
        )
        raw_decisions = payload.get("sequence_decisions", [])
        if not isinstance(raw_decisions, list) or len(raw_decisions) > MAX_HISTORY:
            raise ValueError("sequence decision history exceeds bound")
        runtime._sequence_decisions = deque(
            (SequenceDecisionRecord.restore(item) for item in raw_decisions),
            maxlen=MAX_HISTORY,
        )
        raw_learning_state = payload.get("private_learning_state")
        transitions = runtime._private_causal_records()
        validations = [
            record.epistemic_status is EpistemicStatus.CONTRADICTED
            for record in runtime._experience_ledger.records
            if record.record_id.startswith("validation.")
            and record.source_kind is SourceKind.MODEL
            and record.epistemic_status in {
                EpistemicStatus.SUPPORTED,
                EpistemicStatus.CONTRADICTED,
            }
        ][-_PRIVATE_LEARNING_VALIDATION_WINDOW:]
        if raw_learning_state is None:
            latest_tick = max(
                (record.tick_class for record in transitions),
                default=-1,
            )
            runtime._private_learning_latest_transition_tick = latest_tick
            runtime._private_learning_total_transition_count = len(transitions)
            runtime._private_learning_validation_window = deque(
                validations,
                maxlen=_PRIVATE_LEARNING_VALIDATION_WINDOW,
            )
            if runtime._model_registry.active is not None and transitions:
                runtime._private_learning_last_transition_tick = latest_tick
                runtime._private_learning_new_transition_count = 0
            else:
                runtime._private_learning_last_transition_tick = -1
                runtime._private_learning_new_transition_count = len(transitions)
            runtime._private_learning_last_corpus_hash = None
            runtime._private_learning_settled_requests = deque(maxlen=64)
        else:
            if not isinstance(raw_learning_state, dict):
                raise ValueError("invalid private learning state checkpoint")
            raw_last_tick = raw_learning_state.get("last_transition_tick", -1)
            raw_latest_tick = raw_learning_state.get("latest_transition_tick", -1)
            raw_total = raw_learning_state.get("total_transition_count", 0)
            raw_new = raw_learning_state.get("new_transition_count", 0)
            for name, value, minimum in (
                ("last_transition_tick", raw_last_tick, -1),
                ("latest_transition_tick", raw_latest_tick, -1),
                ("total_transition_count", raw_total, 0),
                ("new_transition_count", raw_new, 0),
            ):
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < minimum
                ):
                    raise ValueError(f"invalid private learning {name}")
            raw_hash = raw_learning_state.get("last_corpus_hash")
            if raw_hash is not None and (
                not isinstance(raw_hash, str)
                or len(raw_hash) != 64
                or any(char not in "0123456789abcdef" for char in raw_hash)
            ):
                raise ValueError("invalid private learning last_corpus_hash")
            raw_window = raw_learning_state.get("validation_window", [])
            if (
                not isinstance(raw_window, list)
                or len(raw_window) > _PRIVATE_LEARNING_VALIDATION_WINDOW
                or any(not isinstance(value, bool) for value in raw_window)
            ):
                raise ValueError("invalid private learning validation_window")
            runtime._private_learning_last_transition_tick = raw_last_tick
            runtime._private_learning_last_corpus_hash = raw_hash
            runtime._private_learning_latest_transition_tick = raw_latest_tick
            runtime._private_learning_total_transition_count = raw_total
            runtime._private_learning_new_transition_count = raw_new
            runtime._private_learning_validation_window = deque(
                raw_window,
                maxlen=_PRIVATE_LEARNING_VALIDATION_WINDOW,
            )
            raw_settled = raw_learning_state.get("settled_request_ids", [])
            if (
                not isinstance(raw_settled, list)
                or len(raw_settled) > 64
                or any(
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(char not in "0123456789abcdef" for char in value)
                    for value in raw_settled
                )
            ):
                raise ValueError("invalid private learning settled_request_ids")
            runtime._private_learning_settled_requests = deque(raw_settled, maxlen=64)
        runtime._private_model_bridge = None
        return runtime

    def materialize_clonal_bud(self, *, body_schema: Any = None) -> "ModeledOrganismRuntime | None":
        """Birth preserves modeling capacity but no acquired model or experience."""

        if (
            self._birth_authority is None
            or self._genome is None
            or not self._ontogeny.reproductively_ready()
            or not self._birth_surfaces_available()
        ):
            return None

        inherited = self._next_heritable_genome()
        child_genome_id = inherited.identity if inherited is not None else self._genome.genome_id
        record = self._birth_authority.birth(
            genome_id=child_genome_id,
            parent_ids=(self._organism_id,),
            generation=self._generation + 1,
        )
        if record is None:
            return None

        birth_energy = self._ontogeny.reproduction_energy()
        child_genome = self._child_genome(inherited) if inherited is not None else self._genome
        child_state = LivingBodyState(
            energy_reserve=birth_energy,
            max_energy=self._living_body_state.max_energy,
            growth_progress=0.0,
            senescence=0.0,
        )
        parent_metabolism = self._metabolism.snapshot()
        child_metabolism = MetabolicLedger(
            capacity=dict(parent_metabolism.capacity),
            replenishment=dict(self._metabolism.checkpoint()["replenishment"]),
            physiology_config=self._physiology_config,
            body_state=child_state,
        )
        graph = load_base_graph(kernel_limits=self._kernel_limits)

        try:
            child = type(self)(
                attention_budget=self._attention_budget,
                investigate_ticks=self._investigate_ticks,
                conflict_z=2.0,
                min_samples=5,
                discover_senses=self._discover_senses,
                bootstrap_semantic_senses=self._bootstrap_semantic_senses,
                sensory_system=self._sensory_system.germinal_copy(),
                genome=child_genome,
                heritable_genome=inherited,
                mutation_seed=self._mutation_seed + self._generation + 1,
                epigenetic_priors=self._epigenetic_priors,
                epigenetic_decay=self._epigenetic_decay,
                kernel_limits=self._kernel_limits,
                cognitive_graph=graph,
                host_lifecycle=self._lifecycle.fork_for_child(),
                body_schema=body_schema,
                physiology_config=self._physiology_config,
                metabolism=child_metabolism,
                living_body_state=child_state,
                organism_id=record.organism_id,
                birth_authority=self._birth_authority,
                generation=record.generation,
                social_habitat=None,
                resource_habitats=self._resource_habitats,
                explicit_metabolism=self._explicit_metabolism,
                social_exchange_quantum=self._social_exchange_quantum,
                social_exchange_cost=self._social_exchange_cost,
                interoception_enabled=self._interoception_enabled,
                interoception_mode=self._interoception_mode,
                model_request_base_cost=self._model_request_base_cost,
                model_storage_scale=self._model_storage_scale,
                cultural_policy_seed=self._cultural_policy.seed,
                cultural_policy_config=self._cultural_policy.config,
                symbol_policy_seed=self._symbol_policy.seed,
                symbol_space=self._symbol_policy.symbol_space,
                symbol_grounding_ledger=SymbolGroundingLedger(record.organism_id),
                sequence_grounding_ledger=SequenceGroundingLedger(record.organism_id),
                sequence_max_length=self._sequence_max_length,
                social_evidence_ledger=SocialEvidenceLedger(record.organism_id),
            )
        except Exception:
            self._birth_authority.death(record.organism_id)
            raise

        self._metabolism.charge("maintenance", birth_energy)

        if self._social_habitat is not None:
            child.join_social_habitat(self._social_habitat)
        if child.model_registry.records or child.experience_ledger.records:
            raise RuntimeError("private model/corpus inheritance invariant violated")
        if child.symbol_grounding_ledger.exposures or child.symbol_grounding_ledger.associations:
            raise RuntimeError("symbol grounding inheritance invariant violated")
        if child.sequence_grounding_ledger.exposures or child.sequence_grounding_ledger.associations:
            raise RuntimeError("sequence grounding inheritance invariant violated")
        return child
