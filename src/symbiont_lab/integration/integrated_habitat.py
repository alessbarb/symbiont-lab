"""Canonical population orchestration for the existing modeled organism.

This module owns lifecycle ordering and population bookkeeping only.  It does
not select claims, symbols, sequences, receivers, or meanings.  Those choices
remain inside each :class:`ModeledOrganismRuntime`.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from importlib import resources
from typing import Any

from symbiont.cognition.genome import GenomeCodec
from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.heredity import HeritableGenome
from symbiont.core.interactions import EcologicalResourcePool
from symbiont.host.discovery import HostDiscovery
from symbiont.host.lifecycle import HostLifecycle
from symbiont.core.metabolism import MetabolicLedger
from symbiont.core.physiology import PhysiologyController
from symbiont.core.social import SocialHabitat
from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont.modeling.sequences import SequenceChannel
from symbiont.modeling.telemetry import CommunicationTelemetry


@dataclass(frozen=True, slots=True)
class IntegratedHabitatConfig:
    habitat_id: str = "integrated-habitat-v1"
    initial_population: int = 2
    max_population: int = 4
    max_ticks: int = 1000
    seed: int = 101
    sequence_max_length: int = 4
    # Transport capacity is a per-tick window. The telemetry sink remains the
    # separately bounded observable history.
    channel_max_deliveries: int = 256
    telemetry_max_events: int = 2048
    telemetry_max_events_per_tick: int = 128
    telemetry_max_age_ticks: int | None = None
    resource_budget: float = 16.0
    trigger_lifecycle_probe: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.habitat_id, str) or not self.habitat_id:
            raise ValueError("habitat_id must be non-empty")
        if not 1 <= self.initial_population <= self.max_population <= 32:
            raise ValueError("population exceeds integrated habitat bound")
        if not 1 <= self.max_ticks <= 10_000:
            raise ValueError("max_ticks exceeds integrated habitat bound")
        if not 0 <= self.seed <= 2**31 - 1:
            raise ValueError("seed exceeds bound")
        if not 1 <= self.sequence_max_length <= 4:
            raise ValueError("sequence length exceeds existing bound")
        if not 1 <= self.channel_max_deliveries <= 512:
            raise ValueError("channel deliveries exceed bound")
        if not 1 <= self.telemetry_max_events <= 2048:
            raise ValueError("telemetry events exceed bound")
        if not 1 <= self.telemetry_max_events_per_tick <= 128:
            raise ValueError("telemetry per-tick bound exceeded")
        if self.telemetry_max_age_ticks is not None and self.telemetry_max_age_ticks < 1:
            raise ValueError("telemetry age bound must be positive")
        if (isinstance(self.resource_budget, bool) or not isinstance(self.resource_budget, (int, float))
                or not math.isfinite(float(self.resource_budget))
                or self.resource_budget < float(self.max_population)):
            raise ValueError("resource budget cannot admit initial population")


@dataclass(frozen=True, slots=True)
class IntegratedTickSummary:
    tick: int
    live_ids: tuple[str, ...]
    births: tuple[str, ...]
    deaths: tuple[str, ...]
    communication_events: int
    grounding_exposures: int
    private_model_records: int
    claims: int
    composites: int


class IntegratedHabitatRuntime:
    """One bounded habitat containing the existing modeled runtimes.

    Ordinary ticks run through :meth:`OrganismRuntime.tick`. The optional
    ``trigger_lifecycle_probe`` is evaluator-only: it stages physical maturity
    before calling the canonical birth boundary so lifecycle plumbing can be
    exercised deterministically. It is never evidence of emergent reproductive
    behaviour and never feeds a readiness signal into cognition.
    """

    SCHEMA_VERSION = 1

    def __init__(self, config: IntegratedHabitatConfig | None = None, *, _restored: bool = False) -> None:
        self.config = config or IntegratedHabitatConfig()
        self.tick_count = 0
        self.authority = HabitatBirthAuthority(
            habitat_id=self.config.habitat_id,
            capacity=self.config.max_population,
            organism_id_prefix=f"{self.config.habitat_id}-org",
        )
        self.social_habitat = SocialHabitat(
            EcologicalResourcePool({"food": self.config.resource_budget}),
            max_members=self.config.max_population,
        )
        self.telemetry = CommunicationTelemetry(
            max_events=self.config.telemetry_max_events,
            max_events_per_tick=self.config.telemetry_max_events_per_tick,
            max_age_ticks=self.config.telemetry_max_age_ticks,
        )
        self.sequence_channel = SequenceChannel(
            authorized_pairs=set(), max_deliveries=self.config.channel_max_deliveries,
            telemetry=self.telemetry,
        )
        self.population: dict[str, ModeledOrganismRuntime] = {}
        self.dead: dict[str, ModeledOrganismRuntime | None] = {}
        self.history: list[IntegratedTickSummary] = []
        if not _restored:
            for index in range(self.config.initial_population):
                self._add_founder(index)
            self._authorize_current_pairs()

    @staticmethod
    def _genome() -> tuple[Any, HeritableGenome]:
        payload = json.loads(resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text())
        genome = GenomeCodec().load(payload)
        heritable = HeritableGenome(genome_id=genome.genome_id, loci=())
        return genome, heritable

    def _new_runtime(self, organism_id: str, generation: int, *, genome: Any, heritable: HeritableGenome) -> ModeledOrganismRuntime:
        # This is an explicit habitat resource envelope, not a behavioural
        # change: it keeps the bounded smoke path viable long enough to cover
        # communication and a lifecycle transition.
        replenishment = {kind: 0.25 for kind in ("observation", "cognition", "persistence", "maintenance")}
        runtime = ModeledOrganismRuntime(
            organism_id=organism_id,
            # The integrated habitat is a deterministic laboratory surface.
            # Do not inherit the default real-host providers here: their wall
            # clock/load readings are outside the habitat and would make the
            # observer-equivalence contract depend on machine activity.
            host_lifecycle=HostLifecycle(
                discovery=HostDiscovery(providers=()), reading_providers=()
            ),
            genome=genome,
            heritable_genome=heritable,
            birth_authority=self.authority,
            generation=generation,
            social_habitat=self.social_habitat,
            metabolism=MetabolicLedger(replenishment=replenishment),
            explicit_metabolism=True,
            physiology=PhysiologyController(),
            bootstrap_semantic_senses=True,
            discover_senses=False,
            interoception_mode="absent",
            min_samples=1,
            mutation_seed=self.config.seed + generation,
            cultural_policy_seed=self.config.seed + generation,
            symbol_policy_seed=self.config.seed + generation,
            sequence_max_length=self.config.sequence_max_length,
        )
        if not runtime.join_social_habitat(self.social_habitat):
            raise RuntimeError("organism could not join integrated social habitat")
        return runtime

    def _add_founder(self, index: int) -> None:
        organism_id = f"integrated-{index:03d}"
        genome, heritable = self._genome()
        if self.authority.register_existing(
            organism_id=organism_id, genome_id=genome.genome_id, generation=0
        ) is None:
            raise RuntimeError("founder could not be registered")
        runtime = self._new_runtime(organism_id, 0, genome=genome, heritable=heritable)
        self.population[organism_id] = runtime

    def _authorize_current_pairs(self) -> None:
        live = tuple(sorted(self.population))
        self.sequence_channel.authorize_pairs({(sender, receiver) for sender in live for receiver in live if sender != receiver})

    def _remove_dead(self) -> tuple[str, ...]:
        from symbiont.core.physiology import VitalState
        dead = tuple(sorted(identifier for identifier, runtime in self.population.items() if runtime._physiology.state is VitalState.DEAD))
        for identifier in dead:
            self.dead[identifier] = self.population.pop(identifier)
        return dead

    def _birth_probe(self) -> tuple[str, ...]:
        if not self.config.trigger_lifecycle_probe or self.tick_count != 1:
            return ()
        parent = next(iter(sorted(self.population.values(), key=lambda item: item.organism_id)), None)
        if parent is None:
            return ()
        parent.living_body_state.growth_progress = 1.0
        child = parent.materialize_clonal_bud()
        if child is None:
            return ()
        if not child.join_social_habitat(self.social_habitat):
            raise RuntimeError("integrated child could not join habitat")
        self.population[child.organism_id] = child
        self._authorize_current_pairs()
        return (child.organism_id,)

    def _death_probe(self) -> None:
        if self.config.trigger_lifecycle_probe and self.tick_count == 3 and self.population:
            victim = sorted(self.population)[0]
            self.population[victim].metabolism.charge("maintenance", 2.0)

    def step(self) -> IntegratedTickSummary:
        if self.tick_count >= self.config.max_ticks:
            raise RuntimeError("integrated habitat tick ceiling reached")
        current = tuple(sorted(self.population.values(), key=lambda item: item.organism_id))
        self._reset_sequence_window()
        for runtime in current:
            from symbiont.core.physiology import VitalState
            if runtime._physiology.state is not VitalState.DEAD:
                runtime.tick()
        deaths = self._remove_dead()
        births = self._birth_probe()
        self._death_probe()
        current = tuple(sorted(self.population.values(), key=lambda item: item.organism_id))
        for runtime in current:
            from symbiont.core.physiology import VitalState
            if runtime._physiology.state is VitalState.DEAD:
                continue
            neighbors = tuple(other for other in current if other.organism_id != runtime.organism_id)
            runtime.autonomous_symbol_step(
                self._symbol_channel(), neighbors, local_context_token="habitat.presence", tick=self.tick_count
            )
            try:
                runtime.autonomous_sequence_step(
                    self.sequence_channel, neighbors, local_context_tokens=("habitat.presence",), tick=self.tick_count
                )
            except ValueError as exc:
                # The existing channel reports a full bounded window as an
                # exception.  Capacity exhaustion is a transport outcome,
                # not a runtime failure; do not retry or choose another
                # message/receiver here.  All other validation failures
                # remain fail-closed.
                if str(exc) != "sequence channel capacity exceeded":
                    raise
            runtime.autonomous_cultural_step(self._social_channel(), neighbors, tick=self.tick_count)
        self.tick_count += 1
        events = len(self.telemetry.events)
        summary = IntegratedTickSummary(
            tick=self.tick_count,
            live_ids=tuple(sorted(self.population)),
            births=births,
            deaths=deaths,
            communication_events=events,
            grounding_exposures=sum(len(item.sequence_grounding_ledger.exposures) for item in current),
            private_model_records=sum(len(item.model_registry.records) for item in current),
            claims=sum(len(item.social_evidence_ledger.claims) for item in current),
            composites=sum(len(item.social_evidence_ledger.composites) for item in current),
        )
        self.history.append(summary)
        if len(self.history) > 256:
            self.history = self.history[-256:]
        return summary

    def _symbol_channel(self):
        from symbiont.modeling.symbols import SymbolChannel
        return SymbolChannel(authorized_pairs=set(self.sequence_channel.authorized_pairs))

    def _social_channel(self):
        from symbiont.modeling.culture import SocialChannel
        return SocialChannel(authorized_pairs=set(self.sequence_channel.authorized_pairs))

    def _reset_sequence_window(self) -> None:
        """Renew transport capacity without changing organism state."""
        self.sequence_channel = SequenceChannel(
            authorized_pairs=set(self.sequence_channel.authorized_pairs),
            max_deliveries=self.config.channel_max_deliveries,
            telemetry=self.telemetry,
        )

    def run(self, ticks: int | None = None) -> tuple[IntegratedTickSummary, ...]:
        target = self.config.max_ticks if ticks is None else ticks
        if not 0 <= target <= self.config.max_ticks:
            raise ValueError("requested ticks exceed integrated habitat bound")
        while self.tick_count < target and self.population:
            self.step()
        return tuple(self.history)

    def checkpoint(self) -> dict[str, Any]:
        if self.history and self.history[-1].tick != self.tick_count:
            raise RuntimeError("checkpoint must be captured at end of tick")
        return {
            "schema_version": self.SCHEMA_VERSION,
            "config": asdict(self.config),
            "tick": self.tick_count,
            "authority": self.authority.checkpoint(),
            "social_habitat": self.social_habitat.checkpoint(),
            "telemetry": self.telemetry.checkpoint(),
            "sequence_deliveries": self.sequence_channel.deliveries,
            "population": [runtime.checkpoint() for runtime in self.population.values()],
            "dead_ids": sorted(self.dead),
            "history": [asdict(item) for item in self.history[-256:]],
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "IntegratedHabitatRuntime":
        if not isinstance(payload, dict) or payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("invalid integrated habitat checkpoint")
        config_payload = payload.get("config")
        if not isinstance(config_payload, dict):
            raise ValueError("invalid integrated habitat config")
        config = IntegratedHabitatConfig(**config_payload)
        runtime = cls(config, _restored=True)
        tick = payload.get("tick")
        if isinstance(tick, bool) or not isinstance(tick, int) or not 0 <= tick <= config.max_ticks:
            raise ValueError("invalid integrated habitat tick")
        runtime.tick_count = tick
        runtime.authority = HabitatBirthAuthority.from_checkpoint(payload["authority"])
        runtime.social_habitat = SocialHabitat.from_checkpoint(payload["social_habitat"])
        runtime.telemetry = CommunicationTelemetry.restore(payload["telemetry"])
        runtime.sequence_channel = SequenceChannel(authorized_pairs=set(), max_deliveries=config.channel_max_deliveries, telemetry=runtime.telemetry)
        deliveries = payload.get("sequence_deliveries", 0)
        if isinstance(deliveries, bool) or not isinstance(deliveries, int) or not 0 <= deliveries <= config.channel_max_deliveries:
            raise ValueError("invalid integrated sequence delivery count")
        runtime.sequence_channel.deliveries = deliveries
        raw_population = payload.get("population", [])
        if not isinstance(raw_population, list) or len(raw_population) > config.max_population:
            raise ValueError("invalid integrated habitat population")
        runtime.population = {}
        for raw in raw_population:
            organism = ModeledOrganismRuntime.from_checkpoint(
                raw, birth_authority=runtime.authority, social_habitat=runtime.social_habitat,
                bootstrap_semantic_senses=True, discover_senses=False,
            )
            if organism.organism_id in runtime.population:
                raise ValueError("duplicate organism in integrated habitat checkpoint")
            runtime.population[organism.organism_id] = organism
        runtime._authorize_current_pairs()
        dead_ids = payload.get("dead_ids", [])
        if (not isinstance(dead_ids, list) or len(dead_ids) > config.max_population
                or any(not isinstance(item, str) or not item for item in dead_ids)
                or set(dead_ids) & set(runtime.population)):
            raise ValueError("invalid integrated dead organism IDs")
        runtime.dead = {item: None for item in dead_ids}
        raw_history = payload.get("history", [])
        if not isinstance(raw_history, list) or len(raw_history) > 256:
            raise ValueError("invalid integrated habitat history")
        runtime.history = [IntegratedTickSummary(
            tick=item["tick"], live_ids=tuple(item["live_ids"]), births=tuple(item["births"]),
            deaths=tuple(item["deaths"]), communication_events=item["communication_events"],
            grounding_exposures=item["grounding_exposures"], private_model_records=item["private_model_records"],
            claims=item["claims"], composites=item["composites"],
        ) for item in raw_history]
        if runtime.history and runtime.history[-1].tick != runtime.tick_count:
            raise ValueError("integrated habitat history is not at checkpoint boundary")
        return runtime

    def digest(self) -> str:
        payload = self.checkpoint()
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


__all__ = ["IntegratedHabitatConfig", "IntegratedHabitatRuntime", "IntegratedTickSummary"]
