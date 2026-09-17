from __future__ import annotations

import math
from typing import Any

from ..cognition.birth import load_base_graph
from ..core.physiology import VitalState
from ..core.reproduction import ReproductivePressure
from ..core.runtime import OrganismDeadError, OrganismRuntime
from .authority import ArchitectureId, ModelArtifactManifest, ModelObjective, TrainingRequest
from .gateway import PrivateModelBridge
from .proposals import ModelPredictionProposal
from .registry import ModelRecord, ModelRegistry, ModelState


class ModeledOrganismRuntime(OrganismRuntime):
    """OrganismRuntime with an acquired private-model phenotype.

    The biological runtime remains unchanged. This subclass adds only governed
    training requests, content-addressed model metadata, shadow/active inference,
    and checkpoint semantics. Model weights and ML frameworks stay outside the
    organism package and are never serialized into the organism checkpoint.
    """

    def __init__(
        self,
        *,
        model_registry: ModelRegistry | None = None,
        private_model_bridge: PrivateModelBridge | None = None,
        model_request_base_cost: float = 0.01,
        model_storage_scale: float = 0.02,
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
        self._model_registry = model_registry or ModelRegistry(self.organism_id)
        self._private_model_bridge = private_model_bridge
        self._model_request_base_cost = float(model_request_base_cost)
        self._model_storage_scale = float(model_storage_scale)

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry

    def attach_private_model_bridge(self, bridge: PrivateModelBridge | None) -> None:
        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot attach model inference")
        if bridge is not None and not isinstance(bridge, PrivateModelBridge):
            raise ValueError("bridge must be a PrivateModelBridge")
        self._private_model_bridge = bridge

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
    ) -> TrainingRequest:
        """Create a bounded external training request and pay local opportunity cost."""

        if self._physiology.state is VitalState.DEAD:
            raise OrganismDeadError("dead organisms cannot request model training")
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
        )
        compute_fraction = min(0.20, requested_steps / 100_000.0 + requested_parameters / 50_000_000.0)
        self._charge_metabolism("cognition", self._model_request_base_cost + compute_fraction)
        self._charge_metabolism("persistence", self._model_request_base_cost * 0.5)
        return request

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
    ) -> ModelPredictionProposal:
        if self._private_model_bridge is None:
            raise ValueError("no private model inference bridge is attached")
        active = self._model_registry.active
        if active is None:
            raise ValueError("no active private model")
        return self._private_model_bridge.predict(
            context_tokens,
            model_id=active.model_id,
            target_token=target_token,
            allow_shadow=False,
        )

    def checkpoint(self) -> dict[str, Any]:
        payload = super().checkpoint()
        payload["private_model_registry"] = self._model_registry.checkpoint()
        payload["private_model_config"] = {
            "model_request_base_cost": self._model_request_base_cost,
            "model_storage_scale": self._model_storage_scale,
        }
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
        runtime = super().from_checkpoint(payload, **constructor)
        if not isinstance(runtime, cls):
            raise RuntimeError("modeled runtime restore returned wrong runtime type")
        runtime._model_registry = ModelRegistry.restore(
            payload.get("private_model_registry"),
            organism_id=runtime.organism_id,
        )
        runtime._private_model_bridge = None
        return runtime

    def materialize_clonal_bud(self) -> "ModeledOrganismRuntime | None":
        """Birth preserves the modeling capability but never the acquired private model."""

        inherited = self._next_heritable_genome()
        record = self._attempt_clonal_bud_with_inherited(inherited)
        if record is None or self._genome is None or self._birth_authority is None:
            return None
        child_genome = self._child_genome(inherited) if inherited is not None else self._genome
        graph = load_base_graph(kernel_limits=self._kernel_limits)
        child = type(self)(
            attention_budget=self._attention_budget,
            investigate_ticks=self._investigate_ticks,
            conflict_z=2.0,
            min_samples=5,
            discover_senses=self._discover_senses,
            bootstrap_semantic_senses=self._bootstrap_semantic_senses,
            genome=child_genome,
            heritable_genome=inherited,
            mutation_seed=self._mutation_seed + self._generation + 1,
            epigenetic_priors=self._epigenetic_priors,
            epigenetic_decay=self._epigenetic_decay,
            kernel_limits=self._kernel_limits,
            cognitive_graph=graph,
            organism_id=record.organism_id,
            birth_authority=self._birth_authority,
            generation=record.generation,
            social_habitat=None,
            resource_habitats=self._resource_habitats,
            reproductive_pressure=(
                ReproductivePressure(threshold_ticks=self._reproductive_pressure.threshold_ticks)
                if self._reproductive_pressure is not None else None
            ),
            explicit_metabolism=self._explicit_metabolism,
            reproduction_cost=self._reproduction_cost,
            social_exchange_quantum=self._social_exchange_quantum,
            social_exchange_cost=self._social_exchange_cost,
            autonomous_behavior=self._autonomous_behavior,
            behavior_exploration=max(0.0, min(1.0, float(
                (dict(inherited.loci) if inherited is not None else {}).get(
                    "behavior_exploration", self._behavior_exploration)))),
            interoception_enabled=self._interoception_enabled,
            interoception_mode=self._interoception_mode,
            model_request_base_cost=self._model_request_base_cost,
            model_storage_scale=self._model_storage_scale,
        )
        if self._social_habitat is not None:
            child.join_social_habitat(self._social_habitat)
        if child.model_registry.records:
            raise RuntimeError("private model inheritance invariant violated")
        return child
