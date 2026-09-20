"""Physical digital body substrate (v1.0 embodiment architecture).

Under the multidimensional evolutionary inheritance architecture, Body represents
the replaceable physical substrate of an organism. It encapsulates:
- Morphology, physical layout and anatomy (which NEVER enter cognition).
- Physical receptors (transduced to opaque sensory signals).
- Physical effectors (driven by opaque activations).
- Physical physiology, material reserves and degradation.
- Strict physical causality: metabolic reserve increases exclusively through
  explicit physical intake via MaterialTransfer, never cognitive/social success (Invariant C).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
from typing import Any, Callable, Mapping, Sequence


@dataclass(slots=True)
class ReceptorPort:
    """Physical receptor on the body surface or interior.

    Its physical identity and kind belong strictly to the apparatus/Body.
    They are never exposed to cognition.
    `ordinal` defines physical structural order, decoupling human-readable IDs
    from channel mapping (AUD-030).
    """

    port_id: str
    kind: str
    ordinal: int = 0
    baseline_value: float = 0.0
    current_value: float = 0.0
    noise_sigma: float = 0.0
    read_fn: Callable[[], float] | None = None

    def sample(self) -> float:
        """Sample the receptor reading, bounded to [0.0, 1.0]."""
        if self.read_fn is not None:
            raw = float(self.read_fn())
        else:
            raw = self.current_value
        val = max(0.0, min(1.0, raw))
        return val


@dataclass(frozen=True, slots=True)
class PhysicalEffect:
    """Explicit physical mechanics produced by an effector (AUD-006, AUD-007, AUD-015)."""

    effect_type: str  # "impulse", "interaction", "emission"
    magnitude: float
    direction: int | None = None
    symbol: int | None = None


@dataclass(slots=True)
class EffectorPort:
    """Physical effector on the body.

    Physical kind and mechanics belong strictly to Body/World.
    Cognition interacts with effectors solely through opaque activation channels.
    `ordinal` defines physical structural order, independent of labels (AUD-030).
    """

    port_id: str
    kind: str
    ordinal: int = 0
    cost_per_activation: float = 0.01
    disabled: bool = False
    efficiency: float = 1.0
    direction: int | None = None
    last_activation: float = 0.0
    last_consequence: float = 0.0

    def execute(self, activation_level: float) -> tuple[float, float, PhysicalEffect]:
        """Execute physical movement/action given activation level in [0.0, 1.0].

        Returns (applied_activation, physical_consequence_magnitude, physical_effect).
        """
        level = max(0.0, min(1.0, float(activation_level)))
        self.last_activation = level
        if self.disabled or self.efficiency <= 0.0:
            self.last_consequence = 0.0
            effect = PhysicalEffect(
                effect_type=self.kind,
                magnitude=0.0,
                direction=self.direction,
            )
            return level, 0.0, effect

        consequence = level * self.efficiency
        self.last_consequence = consequence
        effect = PhysicalEffect(
            effect_type=self.kind,
            magnitude=consequence,
            direction=self.direction,
        )
        return level, consequence, effect


@dataclass(slots=True)
class BodyPhysiology:
    """Physical vitality, metabolic reserve and material integrity of the Body.

    Cognition never accesses these variables directly. Somatic state is only
    accessible if interoceptive receptors transduce it into opaque signals.
    """

    energy_reserve: float = 1.0
    max_energy: float = 2.0
    structural_integrity: float = 1.0
    temperature: float = 0.5
    basal_metabolic_rate: float = 0.005
    degradation_rate: float = 0.0005
    alive: bool = True

    def consume_energy(self, amount: float) -> float:
        """Consume energy from physical reserve. Returns actual amount consumed."""
        consumed = min(self.energy_reserve, max(0.0, amount))
        self.energy_reserve -= consumed
        if self.energy_reserve <= 0.0:
            self.alive = False
        return consumed

    def add_energy(self, amount: float) -> float:
        """Physically add energy (e.g. from physical intake). Returns amount added."""
        if amount <= 0.0 or not self.alive:
            return 0.0
        space = max(0.0, self.max_energy - self.energy_reserve)
        added = min(space, amount)
        self.energy_reserve += added
        return added

    def apply_wear(self, amount: float) -> None:
        """Apply structural wear / physical damage."""
        damage = max(0.0, amount)
        self.structural_integrity = max(0.0, self.structural_integrity - damage)
        if self.structural_integrity <= 0.0:
            self.alive = False


@dataclass(frozen=True, slots=True)
class MaterialTransfer:
    """Material transfer with physical conservation guarantees (AUD-034)."""

    source_id: str
    target_body_id: str
    amount: float
    composition: str = "organic"

    def __post_init__(self) -> None:
        if not self.target_body_id:
            raise ValueError("target_body_id must not be empty")
        if not math.isfinite(self.amount) or self.amount < 0.0:
            raise ValueError("transfer amount must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class ActivationConsequence:
    """Physical outcome of applying an opaque activation to an effector."""

    effector_id: str
    requested_level: float
    applied_level: float
    energy_cost: float
    physical_effect: float
    mechanics: PhysicalEffect | None = None


class Body:
    """Replaceable physical substrate of an organism.

    Holds the real morphology, physical receptor set, physical effector set,
    metabolism and physical degradation.
    """

    def __init__(
        self,
        body_id: str,
        *,
        morphology_name: str = "standard",
        receptors: Sequence[ReceptorPort] | None = None,
        effectors: Sequence[EffectorPort] | None = None,
        physiology: BodyPhysiology | None = None,
    ) -> None:
        if not body_id:
            raise ValueError("body_id must not be empty")
        self.body_id = body_id
        self.morphology_name = morphology_name
        self._receptors: dict[str, ReceptorPort] = {
            r.port_id: r for r in (receptors or ())
        }
        self._effectors: dict[str, EffectorPort] = {
            e.port_id: e for e in (effectors or ())
        }
        self.physiology = physiology or BodyPhysiology()
        self._age_ticks: int = 0

    @property
    def receptor_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._receptors.keys()))

    @property
    def effector_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._effectors.keys()))

    @property
    def ordered_receptors(self) -> tuple[ReceptorPort, ...]:
        """Return receptors ordered by physical ordinal (AUD-030)."""
        return tuple(sorted(self._receptors.values(), key=lambda r: (r.ordinal, r.port_id)))

    @property
    def ordered_effectors(self) -> tuple[EffectorPort, ...]:
        """Return effectors ordered by physical ordinal (AUD-030)."""
        return tuple(sorted(self._effectors.values(), key=lambda e: (e.ordinal, e.port_id)))

    @property
    def age_ticks(self) -> int:
        return self._age_ticks

    @property
    def is_viable(self) -> bool:
        return (
            self.physiology.alive
            and self.physiology.energy_reserve > 0.0
            and self.physiology.structural_integrity > 0.0
        )

    @property
    def is_alive(self) -> bool:
        return self.is_viable

    def apply_damage(self, amount: float) -> None:
        """Apply environmental or hazard damage directly to physical body (AUD-015)."""
        self.physiology.apply_wear(amount)
        if not self.physiology.alive or self.physiology.structural_integrity <= 0.0:
            self.physiology.alive = False

    def get_receptor(self, port_id: str) -> ReceptorPort | None:
        return self._receptors.get(port_id)

    def get_effector(self, port_id: str) -> EffectorPort | None:
        return self._effectors.get(port_id)

    def absorb_material(self, transfer: MaterialTransfer) -> float:
        """Absorb physical nutrients/matter via explicit transfer (AUD-034, Invariant C)."""
        if transfer.target_body_id != self.body_id:
            return 0.0
        return self.physiology.add_energy(transfer.amount)

    def _test_physical_intake(
        self, amount: float, *, source_id: str = "test:apparatus"
    ) -> float:
        """Test-only helper for injecting material without environment (AUD-034, NEW-AUD-001).

        Production code MUST receive material through World environment via MaterialTransfer.
        """
        transfer = MaterialTransfer(
            source_id=source_id,
            target_body_id=self.body_id,
            amount=amount,
        )
        return self.absorb_material(transfer)

    def physical_intake(self, amount: float) -> float:
        """Deprecated test helper. Use _test_physical_intake in tests; production must use MaterialTransfer."""
        return self._test_physical_intake(amount, source_id="test:legacy_physical_intake")

    def break_effector(self, port_id: str) -> bool:
        """Silently disable an effector for causal revision experiments."""
        eff = self._effectors.get(port_id)
        if eff is None:
            return False
        eff.disabled = True
        return True

    def repair_effector(self, port_id: str) -> bool:
        """Restore an effector's functionality."""
        eff = self._effectors.get(port_id)
        if eff is None:
            return False
        eff.disabled = False
        return True

    def transduce_signals(
        self, external_stimuli: Mapping[str, float] | None = None
    ) -> dict[str, float]:
        """Transduce physical receptor states into normalized numeric signals."""
        if external_stimuli:
            for port_id, value in external_stimuli.items():
                if port_id in self._receptors:
                    self._receptors[port_id].current_value = float(value)

        readings: dict[str, float] = {}
        for port_id, receptor in self._receptors.items():
            readings[port_id] = receptor.sample()
        return readings

    def apply_activations(
        self, activations: Mapping[str, float]
    ) -> dict[str, ActivationConsequence]:
        """Apply motor activations to physical effectors.

        Burns metabolic energy based on effector cost and executes physical effect.
        """
        consequences: dict[str, ActivationConsequence] = {}
        for port_id, level in activations.items():
            effector = self._effectors.get(port_id)
            if effector is None:
                continue
            applied_level, physical_effect, mechanics = effector.execute(level)
            cost = effector.cost_per_activation * applied_level
            self.physiology.consume_energy(cost)
            consequences[port_id] = ActivationConsequence(
                effector_id=port_id,
                requested_level=level,
                applied_level=applied_level,
                energy_cost=cost,
                physical_effect=physical_effect,
                mechanics=mechanics,
            )
        return consequences

    def tick_physics(self) -> None:
        """Apply passive physical decay, basal metabolism and wear."""
        self._age_ticks += 1
        self.physiology.consume_energy(self.physiology.basal_metabolic_rate)
        self.physiology.apply_wear(self.physiology.degradation_rate)


def create_standard_body(
    body_id: str,
    *,
    num_receptors: int = 4,
    num_effectors: int = 2,
    morphology: str = "standard",
) -> Body:
    """Construct a default Body with specified receptor and effector count.

    Connects actual physical interoception to physiology (AUD-032).
    Assigns stable ordinals to prevent label-based routing divergence (AUD-030).
    """
    physiology = BodyPhysiology()

    receptors = [
        ReceptorPort(port_id=f"rec.{i}", kind="exteroceptive", ordinal=i)
        for i in range(num_receptors)
    ]

    # Real interoceptive transduction from physical somatic state (AUD-032)
    def _somatic_read() -> float:
        energy_ratio = physiology.energy_reserve / max(1e-6, physiology.max_energy)
        return 0.5 * min(1.0, energy_ratio) + 0.5 * physiology.structural_integrity

    receptors.append(
        ReceptorPort(
            port_id="rec.somatic",
            kind="interoceptive",
            ordinal=num_receptors,
            read_fn=_somatic_read,
        )
    )

    effectors = [
        EffectorPort(
            port_id=f"eff.{j}",
            kind="locomotor",
            ordinal=j,
            direction=(j % 6),
            cost_per_activation=0.01,
        )
        for j in range(num_effectors)
    ]

    return Body(
        body_id=body_id,
        morphology_name=morphology,
        receptors=receptors,
        effectors=effectors,
        physiology=physiology,
    )


__all__ = [
    "ActivationConsequence",
    "Body",
    "BodyPhysiology",
    "EffectorPort",
    "MaterialTransfer",
    "PhysicalEffect",
    "ReceptorPort",
    "create_standard_body",
]
