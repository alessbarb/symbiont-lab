"""Independent longitudinal harness for the biological-closure study.

This module is apparatus code.  It records observations from supplied
organisms and owns only the synthetic environment schedule.  It never passes
regime names, fitness, ground truth, or event labels into an organism's tick.
The organism factory is deliberately a dependency-injected boundary so the
harness cannot silently acquire a second decision path.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import random
from typing import Any, Callable, Iterable, Mapping, Protocol

from symbiont.core.birth_authority import HabitatBirthAuthority
from symbiont.core.ecology import SharedHabitat
from symbiont.core.social import SocialHabitat
from .evolution import EvolutionarySnapshot, measure_lineages


class TickableOrganism(Protocol):
    organism_id: str

    def tick(self) -> Any: ...

    def checkpoint(self) -> dict[str, object]: ...


class LifeEvent(StrEnum):
    BIRTH = "birth"
    DEVELOPMENT = "development"
    FIRST_SENSE = "first_sense"
    FIRST_CONCEPT = "first_concept"
    FIRST_PREDICTION = "first_prediction"
    OBSERVATION = "observation"
    ACQUISITION = "resource_acquisition"
    LEARNING = "learning"
    REGULATION = "internal_regulation"
    HOMEOSTATIC_RESCUE = "homeostatic_rescue"
    STRESS = "stress"
    REST = "rest"
    REPAIR = "repair"
    DAMAGE = "environmental_damage"
    RECOVERY = "recovery"
    REGIME_CHANGE = "regime_change"
    TERMINAL = "terminal"
    INTERACTION = "ecological_interaction"
    REPRODUCTION = "reproduction"
    DEATH = "death"
    RESOURCE_RELEASE = "resource_release"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True, slots=True)
class HarnessConfig:
    """Bounded defaults for a serious run; tests may use smaller explicit values."""

    population: int = 8
    generations: int = 1
    ticks: int = 100_000
    checkpoint_interval: int = 1_000
    random_checkpoint_count: int = 8
    seed: int = 7
    resource_classes: tuple[str, ...] = ("resource_a", "resource_b", "resource_c")
    regimes: tuple[str, ...] = ("abundance", "scarcity", "shift", "recovery", "novelty")
    adversarial_conditions: tuple[str, ...] = ()
    damage_pulses: tuple[int, ...] = ()
    resource_scale: float = 1.0

    def __post_init__(self) -> None:
        if not 8 <= self.population <= 32:
            raise ValueError("population must be within [8, 32]")
        if self.generations < 1 or self.ticks < 1 or self.checkpoint_interval < 1:
            raise ValueError("generations, ticks and checkpoint_interval must be positive")
        if self.random_checkpoint_count < 0 or self.random_checkpoint_count > 64:
            raise ValueError("random_checkpoint_count exceeds bounded capacity")
        if (isinstance(self.resource_scale, bool) or not isinstance(self.resource_scale, (int, float))
                or not 0.0 < self.resource_scale <= 64.0):
            raise ValueError("resource_scale must be within (0, 64]")
        if len(self.resource_classes) < 3 or len(self.resource_classes) > 16:
            raise ValueError("resource_classes must contain between 3 and 16 opaque classes")
        if len(self.regimes) < 3 or len(self.regimes) > 16:
            raise ValueError("regimes must contain between 3 and 16 entries")
        if any(not item or len(item) > 32 for item in (*self.resource_classes, *self.regimes)):
            raise ValueError("environment labels must be bounded and non-empty")
        supported = {"false_correlations", "stale_resources", "resource_inversion"}
        if (len(set(self.adversarial_conditions)) != len(self.adversarial_conditions)
                or any(item not in supported for item in self.adversarial_conditions)):
            raise ValueError("unsupported adversarial condition")
        if (len(set(self.damage_pulses)) != len(self.damage_pulses)
                or any(isinstance(item, bool) or not isinstance(item, int) or item < 1
                       or item > self.ticks * self.generations for item in self.damage_pulses)):
            raise ValueError("damage_pulses must be unique ticks within the run horizon")


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    tick: int
    regime: str
    resources: tuple[tuple[str, float], ...]


class OpaqueEnvironment:
    """Synthetic environment whose schedule is visible only to the apparatus."""

    def __init__(self, config: HarnessConfig, *, horizon: int | None = None) -> None:
        self._config = config
        self._horizon = horizon or config.ticks
        self._tick = 0
        self._resources = {name: 1.0 for name in config.resource_classes}
        # Seeded apparatus variation makes replicate runs independent while
        # keeping the resource identities opaque to the organism.  The
        # permutation is derived from the configuration and therefore remains
        # reproducible after checkpoint restoration.
        self._resource_order = list(config.resource_classes)
        random.Random(config.seed).shuffle(self._resource_order)

    @property
    def tick(self) -> int:
        return self._tick

    def advance(self) -> EnvironmentSnapshot:
        regime = self._config.regimes[min(
            len(self._config.regimes) - 1,
            ((self._tick + 1) * len(self._config.regimes) - 1) // max(self._horizon, 1),
        )]
        names = tuple(self._resources)
        if regime == "abundance":
            profile = [1.0] * len(names)
        elif regime == "scarcity":
            profile = [0.15] * len(names)
        elif regime == "shift":
            profile = [0.8 if index == 1 else 0.05 for index in range(len(names))]
        elif regime == "recovery":
            profile = [0.65 if index % 2 == 0 else 0.25 for index in range(len(names))]
        else:  # novelty: a new distribution, not a semantic instruction
            profile = [0.9 if index == len(names) - 1 else 0.1
                       for index in range(len(names))]
        values = {name: profile[index] for index, name in enumerate(self._resource_order)}
        conditions = set(self._config.adversarial_conditions)
        if "false_correlations" in conditions:
            # Periodic anti-correlation prevents a stable shortcut from being
            # encoded by the apparatus.  Only quantities cross the habitat
            # boundary; this condition name remains evaluator-only.
            values = {
                name: (0.85 if (self._tick + index) % 2 == 0 else 0.12)
                for index, name in enumerate(self._resource_order)
            }
        if "resource_inversion" in conditions:
            # Reverse the usual abundance ordering.  The organism can only
            # observe the resulting opaque surfaces and must revise local
            # evidence rather than receive a regime directive.
            ordered = tuple(values[name] for name in self._resources)
            values = {name: ordered[-index - 1] for index, name in enumerate(self._resources)}
        if "stale_resources" in conditions:
            # Free supply goes stale while existing allocations remain intact;
            # SharedHabitat.set_environment_resources deliberately preserves
            # those allocations so residency is not silently rewritten.
            values = {name: 0.0 for name in self._resources}
        else:
            values = {name: value * self._config.resource_scale for name, value in values.items()}
        self._resources = values
        self._tick += 1
        return EnvironmentSnapshot(self._tick, regime, tuple(sorted(values.items())))

    def apply_resources(self, snapshot: EnvironmentSnapshot,
                        habitats: Mapping[str, SharedHabitat]) -> None:
        """Apply only quantities to supplied resource surfaces.

        The regime label stays in the apparatus trace.  Organisms receive no
        phase, target quantity, or evaluator directive; they only encounter
        whatever bounded surfaces their own runtime can sample or consume.
        """
        values = dict(snapshot.resources)
        if set(values) != set(habitats):
            raise ValueError("resource habitat IDs must match opaque environment classes")
        stale = "stale_resources" in self._config.adversarial_conditions
        for resource_id, habitat in habitats.items():
            habitat.set_environment_resources(values[resource_id])
            # Renewal is a physical property of the surface.  It is applied
            # after the scheduled free supply so unlike a regime label it is
            # experienced only as a changed quantity.  Stale-resource
            # adversarial runs intentionally suppress renewal.
            if not stale:
                habitat.renew()

    def checkpoint(self) -> dict[str, object]:
        return {"schema_version": 1, "tick": self._tick, "resources": dict(self._resources)}

    @classmethod
    def from_checkpoint(cls, config: HarnessConfig, payload: object, *, horizon: int) -> "OpaqueEnvironment":
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("invalid environment checkpoint")
        environment = cls(config, horizon=horizon)
        tick = payload.get("tick")
        resources = payload.get("resources")
        if (isinstance(tick, bool) or not isinstance(tick, int) or tick < 0
                or tick > horizon or not isinstance(resources, dict)
                or set(resources) != set(config.resource_classes)):
            raise ValueError("invalid environment checkpoint state")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not 0.0 <= float(value) <= 64.0 for value in resources.values()):
            raise ValueError("invalid environment checkpoint resources")
        environment._tick = tick
        environment._resources = {key: float(value) for key, value in resources.items()}
        return environment


@dataclass(frozen=True, slots=True)
class LifeRecord:
    tick: int
    organism_id: str
    event: LifeEvent
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SubjectObservation:
    """Evaluator-side observation of one subject after a biological tick."""

    tick: int
    organism_id: str
    vital_state: str
    integrity: float | None = None
    reserve: float | None = None
    phase: str | None = None
    sensory_count: int | None = None
    topology_health: str | None = None
    prediction_error: float | None = None
    action_attempts: int | None = None
    resource_id: str | None = None
    resource_amount: float | None = None


@dataclass(frozen=True, slots=True)
class LifeMetrics:
    """Evaluator-only aggregates derived after an autonomous run."""

    organism_count: int
    births: int
    deaths: int
    resource_acquisitions: int
    repair_events: int
    rest_events: int
    recovery_events: int
    reproduction_events: int
    interaction_events: int
    checkpoint_events: int
    mean_lifespan: float | None
    regime_counts: dict[str, int]
    population_peak: int = 0
    final_population: int = 0
    extinction_events: int = 0
    mean_population: float | None = None
    viability_transitions: int = 0
    mean_metabolic_balance: float | None = None
    mean_prediction_error: float | None = None
    mean_sensory_repertoire: float | None = None
    phenotypic_diversity: int = 0
    time_to_first_cognitive_path: dict[str, int] = field(default_factory=dict)
    time_to_stable_prediction: dict[str, int] = field(default_factory=dict)
    resource_distribution: dict[str, float] = field(default_factory=dict)
    carrying_capacity_occupancy: float | None = None
    birth_rate: float | None = None
    death_rate: float | None = None
    niche_overlap: float | None = None
    offspring_viability: float | None = None
    homeostatic_rescue_events: int = 0


@dataclass(slots=True)
class LifeTrace:
    records: list[LifeRecord] = field(default_factory=list)
    checkpoints: list[dict[str, object]] = field(default_factory=list)
    environment: list[EnvironmentSnapshot] = field(default_factory=list)
    population: list[tuple[int, int]] = field(default_factory=list)
    evolutionary: list[EvolutionarySnapshot] = field(default_factory=list)
    observations: list[SubjectObservation] = field(default_factory=list)

    def add(self, tick: int, organism_id: str, event: LifeEvent, detail: str = "") -> None:
        if len(self.records) >= 1_000_000:
            return
        self.records.append(LifeRecord(tick, organism_id[:96], event, detail[:96]))

    def as_dict(self) -> dict[str, object]:
        return {
            "records": [asdict(record) for record in self.records],
            "checkpoints": list(self.checkpoints),
            "environment": [asdict(snapshot) for snapshot in self.environment],
            "population": [list(item) for item in self.population],
            "evolutionary": [asdict(item) for item in self.evolutionary],
            "observations": [asdict(item) for item in self.observations],
        }

    def metrics(self) -> LifeMetrics:
        """Compute scientific aggregates without exposing them to organisms."""
        counts = {event: 0 for event in LifeEvent}
        birth_ticks: dict[str, int] = {}
        lifespans: list[int] = []
        for record in self.records:
            counts[record.event] += 1
            if record.event is LifeEvent.BIRTH:
                birth_ticks.setdefault(record.organism_id, record.tick)
            elif record.event is LifeEvent.DEATH and record.organism_id in birth_ticks:
                lifespans.append(max(0, record.tick - birth_ticks[record.organism_id]))
        regime_counts: dict[str, int] = {}
        for snapshot in self.environment:
            regime_counts[snapshot.regime] = regime_counts.get(snapshot.regime, 0) + 1
        zero_population_transitions = sum(
            count == 0 and (index == 0 or self.population[index - 1][1] > 0)
            for index, (_, count) in enumerate(self.population)
        )
        by_subject: dict[str, list[SubjectObservation]] = {}
        for observation in self.observations:
            by_subject.setdefault(observation.organism_id, []).append(observation)
        states = [item for items in by_subject.values() for item in items]
        viability_transitions = sum(
            sum(previous.vital_state != current.vital_state
                for previous, current in zip(items, items[1:]))
            for items in by_subject.values()
        )
        balances = [item.reserve for item in states if item.reserve is not None]
        prediction_errors = [item.prediction_error for item in states if item.prediction_error is not None]
        sensory = [item.sensory_count for item in states if item.sensory_count is not None]
        phenotype_vectors = {
            (round(item.reserve or 0.0, 2), round(item.integrity or 0.0, 2),
             item.sensory_count or 0, item.action_attempts or 0)
            for item in states
        }
        first_path: dict[str, int] = {}
        stable_prediction: dict[str, int] = {}
        resource_totals: dict[str, float] = {}
        resource_sets: dict[str, set[str]] = {}
        for subject_id, items in by_subject.items():
            path = next((item.tick for item in items
                         if item.topology_health in {"connected", "adaptive"}), None)
            if path is not None:
                first_path[subject_id] = path
            consecutive = 0
            for item in items:
                if item.prediction_error is not None and item.prediction_error <= 0.25:
                    consecutive += 1
                    if consecutive >= 3:
                        stable_prediction[subject_id] = item.tick - 2
                        break
                else:
                    consecutive = 0
            for item in items:
                if item.resource_id is not None and item.resource_amount is not None:
                    resource_totals[item.resource_id] = resource_totals.get(item.resource_id, 0.0) + item.resource_amount
                    resource_sets.setdefault(subject_id, set()).add(item.resource_id)
        resource_distribution = {key: round(value, 6) for key, value in sorted(resource_totals.items())}
        overlaps: list[float] = []
        subject_sets = list(resource_sets.values())
        for index, left in enumerate(subject_sets):
            for right in subject_sets[index + 1:]:
                union = left | right
                if union:
                    overlaps.append(len(left & right) / len(union))
        observation_ticks = max((tick for tick, _ in self.population), default=0)
        return LifeMetrics(
            organism_count=len(birth_ticks),
            births=counts[LifeEvent.BIRTH],
            deaths=counts[LifeEvent.DEATH],
            resource_acquisitions=counts[LifeEvent.ACQUISITION],
            repair_events=counts[LifeEvent.REPAIR],
            rest_events=counts[LifeEvent.REST],
            recovery_events=counts[LifeEvent.RECOVERY],
            reproduction_events=counts[LifeEvent.REPRODUCTION],
            interaction_events=counts[LifeEvent.INTERACTION],
            checkpoint_events=counts[LifeEvent.CHECKPOINT],
            mean_lifespan=(sum(lifespans) / len(lifespans)) if lifespans else None,
            regime_counts=regime_counts,
            population_peak=max((count for _, count in self.population), default=0),
            final_population=(self.population[-1][1] if self.population else 0),
            extinction_events=zero_population_transitions,
            mean_population=(sum(count for _, count in self.population) / len(self.population)
                             if self.population else None),
            viability_transitions=viability_transitions,
            mean_metabolic_balance=(sum(balances) / len(balances)) if balances else None,
            mean_prediction_error=(sum(prediction_errors) / len(prediction_errors)
                                   if prediction_errors else None),
            mean_sensory_repertoire=(sum(sensory) / len(sensory)) if sensory else None,
            phenotypic_diversity=len(phenotype_vectors),
            time_to_first_cognitive_path=first_path,
            time_to_stable_prediction=stable_prediction,
            resource_distribution=resource_distribution,
            carrying_capacity_occupancy=(sum(count for _, count in self.population)
                                         / (len(self.population) * 32)
                                         if self.population else None),
            birth_rate=counts[LifeEvent.BIRTH] / observation_ticks if observation_ticks else None,
            death_rate=counts[LifeEvent.DEATH] / observation_ticks if observation_ticks else None,
            niche_overlap=(sum(overlaps) / len(overlaps)) if overlaps else None,
            offspring_viability=(self.evolutionary[-1].offspring_viability
                                 if self.evolutionary else None),
            homeostatic_rescue_events=counts[LifeEvent.HOMEOSTATIC_RESCUE],
        )


def _events_for_result(result: Any) -> tuple[LifeEvent, ...]:
    runtime_events = getattr(result, "runtime_events", None)
    if runtime_events is not None:
        mapping = {
            "development": LifeEvent.DEVELOPMENT,
            "first_sense": LifeEvent.FIRST_SENSE,
            "first_concept": LifeEvent.FIRST_CONCEPT,
            "first_prediction": LifeEvent.FIRST_PREDICTION,
            "observation": LifeEvent.OBSERVATION,
            "resource_acquisition": LifeEvent.ACQUISITION,
            "learning": LifeEvent.LEARNING,
            "regulation": LifeEvent.REGULATION,
            "homeostatic_rescue": LifeEvent.HOMEOSTATIC_RESCUE,
            "stress": LifeEvent.STRESS,
            "rest": LifeEvent.REST,
            "repair": LifeEvent.REPAIR,
            "damage": LifeEvent.DAMAGE,
            "recovery": LifeEvent.RECOVERY,
            "regime_shift": LifeEvent.REGIME_CHANGE,
            "terminal": LifeEvent.TERMINAL,
            "interaction": LifeEvent.INTERACTION,
            "reproduction": LifeEvent.REPRODUCTION,
            "death": LifeEvent.DEATH,
            "resource_release": LifeEvent.RESOURCE_RELEASE,
        }
        return tuple(dict.fromkeys(mapping[event] for event in runtime_events if event in mapping))
    events: list[LifeEvent] = [LifeEvent.DEVELOPMENT, LifeEvent.LEARNING]
    action = getattr(result, "action_result", None)
    if action is not None and bool(getattr(action, "executed", False)):
        action_id = str(getattr(action, "action_id", ""))
        if action_id == "intake" or action_id.startswith("intake:"):
            events.append(LifeEvent.ACQUISITION)
        elif action_id in {"reproduce", "social_exchange"}:
            events.append({"reproduce": LifeEvent.REPRODUCTION,
                           "social_exchange": LifeEvent.INTERACTION}[action_id])
        elif action_id == "rest":
            events.append(LifeEvent.REST)
        elif action_id == "repair":
            events.append(LifeEvent.REPAIR)
    physiology = getattr(result, "physiology", None)
    state = str(getattr(getattr(physiology, "state", None), "value", ""))
    # Dormancy is an intentional regulatory state and is measured separately
    # as REST.  Counting it as stress would make successful down-regulation
    # appear biologically worse in the ablation.
    if state in {"stressed", "agonizing"}:
        events.append(LifeEvent.STRESS)
    if state == "active" and getattr(result, "metabolism", None) is not None:
        events.append(LifeEvent.REGULATION)
    if state == "dead":
        events.extend((LifeEvent.DEATH, LifeEvent.RESOURCE_RELEASE))
    return tuple(dict.fromkeys(events))


def _offspring_from_result(result: Any) -> TickableOrganism | None:
    """Extract only a runtime-shaped offspring from an action result.

    The harness may register a child created by the organism, but it does not
    construct, select, or otherwise direct that child.  The result itself is
    never written to the trace.
    """
    action = getattr(result, "action_result", None)
    child = getattr(action, "result", None) if action is not None else None
    if (child is None or not isinstance(getattr(child, "organism_id", None), str)
            or not callable(getattr(child, "tick", None))
            or not callable(getattr(child, "checkpoint", None))):
        return None
    return child


def _subject_observation(tick: int, organism_id: str, result: Any) -> SubjectObservation:
    """Extract bounded evaluator measurements without changing the result."""
    physiology = getattr(result, "physiology", None)
    vital_state = str(getattr(getattr(physiology, "state", None), "value", "unknown"))[:32]
    homeostasis = getattr(result, "homeostasis", None)
    integrity = getattr(homeostasis, "integrity", None)
    metabolism = getattr(result, "metabolism", None)
    reserves = getattr(metabolism, "reserve", {})
    reserve = None
    if isinstance(reserves, dict) and reserves:
        numeric = [float(value) for value in reserves.values()
                   if isinstance(value, (int, float)) and not isinstance(value, bool)]
        capacities = getattr(metabolism, "capacity", {})
        ratios = [value / max(float(capacities.get(key, 1.0)), 1e-12)
                  for key, value in reserves.items()
                  if isinstance(value, (int, float)) and not isinstance(value, bool)
                  and isinstance(capacities, dict)]
        if ratios:
            reserve = max(-1.0, min(1.0, sum(ratios) / len(ratios)))
        elif numeric:
            reserve = sum(numeric) / len(numeric)
    development = getattr(result, "development", None)
    cognition = getattr(result, "cognition", None)
    errors = getattr(cognition, "prediction_errors", ()) if cognition is not None else ()
    error_values = [abs(float(getattr(item, "error", 0.0))) for item in errors
                    if isinstance(getattr(item, "error", None), (int, float))]
    action = getattr(result, "action_result", None)
    action_id = str(getattr(action, "action_id", ""))
    resource_id = action_id.split(":", 1)[1][:64] if action_id.startswith("intake:") else None
    amount = getattr(action, "result", None) if resource_id is not None else None
    return SubjectObservation(
        tick=tick, organism_id=organism_id[:96], vital_state=vital_state,
        integrity=(float(integrity) if isinstance(integrity, (int, float)) else None),
        reserve=reserve,
        phase=(str(getattr(getattr(development, "phase", None), "value", ""))[:32]
               if development is not None else None),
        sensory_count=(int(getattr(development, "sensory_count"))
                       if development is not None and isinstance(getattr(development, "sensory_count", None), int)
                       else None),
        topology_health=(str(getattr(development, "topology_health"))[:64]
                        if development is not None else None),
        prediction_error=(sum(error_values) / len(error_values) if error_values else None),
        action_attempts=(int(getattr(development, "action_attempts"))
                         if development is not None and isinstance(getattr(development, "action_attempts", None), int)
                         else None),
        resource_id=resource_id,
        resource_amount=(float(amount) if isinstance(amount, (int, float)) and not isinstance(amount, bool) else None),
    )


def _tupleize(value: object) -> object:
    """Restore ``random`` state after a JSON round-trip."""
    if isinstance(value, list):
        return tuple(_tupleize(item) for item in value)
    if isinstance(value, dict):
        return {key: _tupleize(item) for key, item in value.items()}
    return value


class AutonomousLifeHarness:
    """Run organisms without injecting environment semantics into decisions."""

    def __init__(self, organisms: Iterable[TickableOrganism], *, config: HarnessConfig,
                 resource_habitats: Mapping[str, SharedHabitat] | None = None,
                 social_habitat: SocialHabitat | None = None,
                 birth_authority: HabitatBirthAuthority | None = None,
                 _allow_partial_population: bool = False) -> None:
        self._organisms = list(organisms)
        if ((_allow_partial_population and len(self._organisms) > 32)
                or (not _allow_partial_population and len(self._organisms) != config.population)):
            raise ValueError("organism count must equal configured population")
        self._config = config
        self._total_ticks = config.ticks * config.generations
        self._environment = OpaqueEnvironment(config, horizon=self._total_ticks)
        self._resource_habitats = dict(resource_habitats or {})
        self._social_habitat = social_habitat
        self._birth_authority = birth_authority
        if self._resource_habitats and set(self._resource_habitats) != set(config.resource_classes):
            raise ValueError("resource_habitats must match configured opaque resource classes")
        self._rng = random.Random(config.seed)
        self._last_states: dict[str, str] = {}
        self._checkpoint_ticks = self._make_checkpoint_ticks()

    def _make_checkpoint_ticks(self) -> set[int]:
        return {
            *range(self._config.checkpoint_interval, self._total_ticks + 1,
                   self._config.checkpoint_interval),
            *(self._rng.sample(range(1, self._total_ticks + 1),
                               min(self._config.random_checkpoint_count, self._total_ticks))),
        }

    def checkpoint(self) -> dict[str, object]:
        """Capture resumable apparatus state without inventing organism state."""
        return {
            "schema_version": 1,
            "environment": self._environment.checkpoint(),
            "rng_state": self._rng.getstate(),
            "checkpoint_ticks": sorted(self._checkpoint_ticks),
            "last_states": dict(self._last_states),
            "organisms": [organism.checkpoint() for organism in self._organisms],
            "resource_habitats": {
                resource_id: habitat.checkpoint()
                for resource_id, habitat in self._resource_habitats.items()
            },
            "social_habitat": (self._social_habitat.checkpoint()
                               if self._social_habitat is not None else None),
            "birth_authority": (self._birth_authority.checkpoint()
                                 if self._birth_authority is not None else None),
        }

    @classmethod
    def from_checkpoint(
        cls,
        payload: object,
        *,
        config: HarnessConfig,
        organism_restorer: Callable[[dict[str, object]], TickableOrganism],
        resource_habitats: Mapping[str, SharedHabitat] | None = None,
        social_habitat: SocialHabitat | None = None,
        birth_authority: HabitatBirthAuthority | None = None,
    ) -> "AutonomousLifeHarness":
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("invalid autonomous-life checkpoint")
        raw_organisms = payload.get("organisms")
        if not isinstance(raw_organisms, list):
            raise ValueError("invalid autonomous-life organisms")
        organisms = [organism_restorer(item) for item in raw_organisms
                     if isinstance(item, dict)]
        if len(organisms) != len(raw_organisms):
            raise ValueError("invalid organism checkpoint")
        harness = cls(organisms, config=config, resource_habitats=resource_habitats,
                      social_habitat=social_habitat, birth_authority=birth_authority,
                      _allow_partial_population=True)
        raw_habitats = payload.get("resource_habitats", {})
        if not isinstance(raw_habitats, dict):
            raise ValueError("invalid resource habitat checkpoint")
        if set(raw_habitats) != set(harness._resource_habitats):
            raise ValueError("resource habitat checkpoint IDs do not match supplied surfaces")
        for resource_id, habitat_payload in raw_habitats.items():
            if not isinstance(habitat_payload, dict):
                raise ValueError("invalid resource habitat checkpoint")
            harness._resource_habitats[resource_id].restore_checkpoint(habitat_payload)
        social_payload = payload.get("social_habitat")
        if (harness._social_habitat is None) != (social_payload is None):
            raise ValueError("social habitat checkpoint does not match supplied surface")
        if social_payload is not None:
            if not isinstance(social_payload, dict):
                raise ValueError("invalid social habitat checkpoint")
            harness._social_habitat.restore_checkpoint(social_payload)
        authority_payload = payload.get("birth_authority")
        if (harness._birth_authority is None) != (authority_payload is None):
            raise ValueError("birth authority checkpoint does not match supplied authority")
        if authority_payload is not None:
            if not isinstance(authority_payload, dict):
                raise ValueError("invalid birth authority checkpoint")
            harness._birth_authority.restore_checkpoint(authority_payload)
        harness._environment = OpaqueEnvironment.from_checkpoint(
            config, payload.get("environment"), horizon=harness._total_ticks
        )
        try:
            harness._rng.setstate(_tupleize(payload["rng_state"]))
        except (KeyError, TypeError, ValueError):
            raise ValueError("invalid autonomous-life random state") from None
        raw_ticks = payload.get("checkpoint_ticks")
        raw_states = payload.get("last_states", {})
        if (not isinstance(raw_ticks, list) or
                any(isinstance(item, bool) or not isinstance(item, int)
                    or not 0 < item <= harness._total_ticks for item in raw_ticks)
                or not isinstance(raw_states, dict)):
            raise ValueError("invalid autonomous-life checkpoint metadata")
        harness._checkpoint_ticks = set(raw_ticks)
        harness._last_states = {str(key): str(value) for key, value in raw_states.items()}
        return harness

    def run(self, *, max_ticks: int | None = None) -> LifeTrace:
        trace = LifeTrace()
        known_ids = {str(getattr(organism, "organism_id", "")) for organism in self._organisms}
        if self._environment.tick == 0:
            for organism_id in sorted(known_ids):
                trace.add(0, organism_id, LifeEvent.BIRTH)
        remaining = self._total_ticks - self._environment.tick
        if max_ticks is None:
            ticks_to_run = remaining
        elif isinstance(max_ticks, bool) or not isinstance(max_ticks, int) or not 0 <= max_ticks <= remaining:
            raise ValueError("max_ticks must be within the remaining harness horizon")
        else:
            ticks_to_run = max_ticks
        for _ in range(ticks_to_run):
            environment_snapshot = self._environment.advance()
            trace.environment.append(environment_snapshot)
            if self._resource_habitats:
                self._environment.apply_resources(environment_snapshot, self._resource_habitats)
            for organism in tuple(self._organisms):
                organism_id = str(getattr(organism, "organism_id", ""))
                if self._environment.tick in self._config.damage_pulses:
                    apply_damage = getattr(organism, "apply_environmental_damage", None)
                    if callable(apply_damage):
                        applied = float(apply_damage(0.20))
                        if applied > 0.0:
                            trace.add(self._environment.tick, organism_id, LifeEvent.DAMAGE,
                                      f"amount={applied:.3f}")
                try:
                    result = organism.tick()
                except RuntimeError as exc:
                    # A terminal organism rejection is expected; other runtime
                    # errors are apparatus failures and must remain visible.
                    if exc.__class__.__name__ != "OrganismDeadError":
                        raise
                    trace.add(self._environment.tick, organism_id, LifeEvent.DEATH, "tick_rejected")
                    # A dead organism cannot remain schedulable. Keeping it in
                    # the population would turn an irreversible terminal
                    # state into repeated pseudo-life on later ticks.
                    self._organisms.remove(organism)
                    continue
                if len(trace.observations) < 1_000_000:
                    trace.observations.append(
                        _subject_observation(self._environment.tick, organism_id, result)
                    )
                for event in _events_for_result(result):
                    trace.add(self._environment.tick, organism_id, event)
                physiology = getattr(result, "physiology", None)
                state = str(getattr(getattr(physiology, "state", None), "value", ""))
                previous_state = self._last_states.get(organism_id)
                if state == "active" and previous_state in {"stressed", "agonizing", "dormant"}:
                    trace.add(self._environment.tick, organism_id, LifeEvent.RECOVERY)
                if state:
                    self._last_states[organism_id] = state
                child = _offspring_from_result(result)
                if child is not None and all(child is not existing for existing in self._organisms):
                    if len(self._organisms) >= 32:
                        raise RuntimeError("autonomous population exceeded bounded capacity")
                    self._organisms.append(child)
                    known_ids.add(str(child.organism_id))
                    trace.add(self._environment.tick, str(child.organism_id), LifeEvent.BIRTH)
                if self._environment.tick in self._checkpoint_ticks:
                    trace.checkpoints.append({
                        "tick": self._environment.tick,
                        "organism_id": organism_id,
                        "state": organism.checkpoint(),
                    })
                    trace.add(self._environment.tick, organism_id, LifeEvent.CHECKPOINT)
                if str(getattr(getattr(getattr(result, "physiology", None), "state", None),
                                   "value", "")) == "dead":
                    self._organisms.remove(organism)
            current_ids = {str(getattr(organism, "organism_id", "")) for organism in self._organisms}
            for new_id in sorted(current_ids - known_ids):
                trace.add(self._environment.tick, new_id, LifeEvent.BIRTH)
            known_ids = current_ids
            trace.population.append((self._environment.tick, len(self._organisms)))
            if self._birth_authority is not None:
                trace.evolutionary.append(measure_lineages(self._birth_authority))
        return trace


def run_autonomous_life(
    organism_factory: Callable[[int, HarnessConfig], Iterable[TickableOrganism]],
    *, config: HarnessConfig | None = None,
) -> LifeTrace:
    """Construct and run a population through an explicit factory boundary."""
    selected = config or HarnessConfig()
    organisms = organism_factory(selected.population, selected)
    return AutonomousLifeHarness(organisms, config=selected).run()


__all__ = [
    "AutonomousLifeHarness", "HarnessConfig", "LifeEvent", "LifeRecord",
    "LifeMetrics", "LifeTrace", "SubjectObservation", "OpaqueEnvironment",
    "run_autonomous_life",
]
