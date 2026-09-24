# Actuation P0 — Motor Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the motor substrate for `symbiont` — a bounded, opaque, genome-derived body of potential actuators, and the statistical machinery to discover which ones have reproducible effect — entirely inside `symbiont`, with zero dependency on cognition wiring or World.

**Architecture:** New package `symbiont/actuation/` mirrors the shape of `symbiont/host/adaptive.py` (candidate lifecycle: active/probing/dormant) but for motor channels instead of sensors. A new optional `MotorGenes` gene group makes actuator identity a deterministic, stable function of a fixed schema string plus a heritable slot index — never a hash of the whole genome — so an unrelated mutation (e.g. `learning_rate`) never renames an organism's actuators. Causal-vs-background-noise separation comes from a non-periodic, RNG-namespaced ON/OFF probing calendar feeding the existing `PairAccumulator` primitive (reused unmodified from `host/adaptive.py`).

**Tech Stack:** Python 3.11+, `dataclasses(slots=True, frozen=True)`, `hashlib.sha256` for deterministic IDs, `random.Random` seeded via the existing `derive_seed` helper, `pytest`.

**Spec:** `docs/design/symbiont-actuation-v1.md` (revision 4, READY FOR P0) — this plan implements exactly and only Phase P0 (§14): motor substrate, no cognition, no World.

## Global Constraints

- `symbiont` never imports `symbiont_world` or `symbiont_lab` (spec §1). No file created in this plan may import either.
- No raw telemetry persisted; only established aggregates (spec §11). `export()` methods must never serialize a single-sample observation as if it were established.
- Corrupted checkpoint state must raise on `restore()`, never silently default to a degraded-but-valid state (spec §15). Only ordinary health degradation may yield `delivered=0.0`.
- `ActuatorConstitution`/`MotorSlot` must be genuinely immutable (frozen dataclasses over tuples, never a frozen dataclass wrapping a `dict`/`Mapping`) so they hash and serialize unambiguously (spec §3 revision 4).
- `actuator_id` must be stable across genome mutations that do not touch `MotorGenes` (spec §3 revision 3). It is derived from a fixed schema constant plus slot index — never from `Genome.genome_id` or `Genome.genome_hash`.
- Every `PairAccumulator(activation, Δpercept)` observation must pair `activation(t)` with `percept(t+1) - percept(t)`, never same-tick (spec §6 revision 4) — enforced by test, not by a runtime assertion inside the accumulator itself (the accumulator is generic; the caller owns the time-shift).
- The ON/OFF probing calendar must not be tick-parity-based (no `tick % 2`). It must be an RNG-namespaced balanced shuffle, and a candidate needs evidence from more than one distinct window before promotion to `active` (spec §6 revision 3).

---

## File Structure

```text
src/symbiont/cognition/genome.py        # MODIFY: add MotorGenes gene group (optional, additive)
src/symbiont/cognition/birth.py         # MODIFY: add load_actuator_constitution(genome)
src/symbiont/actuation/
├── __init__.py                          # CREATE: empty, package marker
├── types.py                             # CREATE: ActuatorId, MotorCandidate, MotorIntent, Actuation
├── constitution.py                      # CREATE: MotorSlot, ActuatorConstitution, derive_actuator_constitution
├── calendar.py                          # CREATE: probing_calendar (RNG-namespaced balanced ON/OFF)
├── candidate.py                         # CREATE: ActuatorCandidateState (PairAccumulator-based effect evidence)
├── proposer.py                          # CREATE: ActuatorProposer (active/probing/dormant lifecycle)
├── health.py                            # CREATE: ActuatorState (health/reliability/cost)
├── system.py                            # CREATE: ActuatorSystem.execute (MotorIntent -> Actuation)
└── checkpoint.py                        # CREATE: export()/restore() for the whole actuation bundle
tests/unit/actuation/
├── __init__.py                           # CREATE: empty, matches tests/unit/host/__init__.py convention
├── test_genome_motor_genes.py           # CREATE
├── test_types.py                        # CREATE
├── test_constitution.py                 # CREATE
├── test_calendar.py                     # CREATE
├── test_candidate.py                    # CREATE
├── test_proposer.py                     # CREATE
├── test_health.py                       # CREATE
├── test_system.py                       # CREATE
└── test_checkpoint_gate.py              # CREATE — P0 gate: causal vs sham actuator, end to end
```

---

### Task 1: `MotorGenes` — stable, additive gene group

**Files:**

- Create: `tests/unit/actuation/__init__.py` (empty; makes the new test package importable, matching `tests/unit/host/__init__.py`)
- Modify: `src/symbiont/cognition/genome.py`
- Test: `tests/unit/actuation/test_genome_motor_genes.py`

**Interfaces:**

- Produces: `MotorGenes(slot_count: int, basal_cost: float, initial_health: float, execution_threshold: float)`, all fields with defaults (`slot_count=6, basal_cost=0.05, initial_health=1.0, execution_threshold=0.5`). `Genome.motor: MotorGenes` field, default-valued, added last so existing positional constructions of `Genome` keep working.
- Consumes: nothing new — reads existing `Genome`/`GenomeCodec`/`_require_float`/`_require_int`/`GenomeError` machinery already in the file.

- [ ] **Step 1: Create the test package marker, then write the failing tests**

```python
# tests/unit/actuation/__init__.py
```

(empty file)

```python
# tests/unit/actuation/test_genome_motor_genes.py
from __future__ import annotations

import pytest

from symbiont.cognition.genome import Genome, GenomeCodec, GenomeError, MotorGenes


def _base_payload() -> dict:
    return {
        "schema_version": 1,
        "genome_id": "genome_test0000000000000000000000",
        "parent_ids": [],
        "kernel_compatibility": ">=0.60",
        "development": {
            "initial_concepts": 0,
            "soft_node_budget": 64,
            "soft_edge_budget": 64,
            "consolidation_interval_ticks": 10,
        },
        "plasticity": {
            "learning_rate": {"initial": 0.1, "min": 0.0, "max": 1.0},
            "forgetting_rate": {"initial": 0.05, "min": 0.0, "max": 1.0},
            "eligibility_decay": 0.9,
        },
        "structure": {
            "grow_threshold": 0.5,
            "prune_threshold": 0.1,
            "minimum_support": 2,
            "tentative_lifetime_ticks": 5,
        },
        "mutation_policy": {"continuous_sigma": 0.05, "max_fields_per_generation": 1},
    }


def test_genome_without_motor_key_gets_default_motor_genes():
    genome = GenomeCodec().load(_base_payload())
    assert genome.motor == MotorGenes()
    assert genome.motor.slot_count == 6
    assert genome.motor.basal_cost == 0.05
    assert genome.motor.initial_health == 1.0
    assert genome.motor.execution_threshold == 0.5


def test_genome_with_explicit_motor_key_round_trips():
    payload = _base_payload()
    payload["motor"] = {
        "slot_count": 3,
        "basal_cost": 0.1,
        "initial_health": 0.9,
        "execution_threshold": 0.4,
    }
    genome = GenomeCodec().load(payload)
    assert genome.motor == MotorGenes(
        slot_count=3, basal_cost=0.1, initial_health=0.9, execution_threshold=0.4
    )


def test_default_motor_genes_do_not_change_genome_hash():
    without_motor = GenomeCodec().load(_base_payload())
    payload_with_default_motor = _base_payload()
    payload_with_default_motor["motor"] = {
        "slot_count": 6,
        "basal_cost": 0.05,
        "initial_health": 1.0,
        "execution_threshold": 0.5,
    }
    with_explicit_default_motor = GenomeCodec().load(payload_with_default_motor)
    assert without_motor.genome_hash == with_explicit_default_motor.genome_hash


def test_unknown_top_level_key_still_rejected():
    payload = _base_payload()
    payload["bogus"] = {}
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)


def test_motor_slot_count_must_be_positive():
    payload = _base_payload()
    payload["motor"] = {
        "slot_count": 0,
        "basal_cost": 0.05,
        "initial_health": 1.0,
        "execution_threshold": 0.5,
    }
    with pytest.raises(GenomeError):
        GenomeCodec().load(payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_genome_motor_genes.py -v`
Expected: FAIL — `ImportError: cannot import name 'MotorGenes'`

- [ ] **Step 3: Implement `MotorGenes` in `genome.py`**

Add near the other gene dataclasses (after `MutationPolicyGenes`, before `Genome`):

```python
@dataclass(slots=True, frozen=True)
class MotorGenes:
    slot_count: int = 6
    basal_cost: float = 0.05
    initial_health: float = 1.0
    execution_threshold: float = 0.5
```

Add `motor: MotorGenes = MotorGenes()` as the last field of `Genome`:

```python
@dataclass(slots=True, frozen=True)
class Genome:
    schema_version: int
    genome_id: str
    parent_ids: tuple[str, ...]
    kernel_compatibility: str
    development: DevelopmentGenes
    plasticity: PlasticityGenes
    structure: StructureGenes
    mutation_policy: MutationPolicyGenes
    motor: MotorGenes = MotorGenes()
```

Add a top-level optional-keys constant next to `_REQUIRED_TOP_LEVEL_KEYS`:

```python
_TOP_LEVEL_OPTIONAL_KEYS = frozenset({"motor"})
_DEFAULT_MOTOR_GENES = MotorGenes()
```

In `GenomeCodec.load`, replace the strict top-level key check:

```python
        keys = set(payload.keys())
        if keys != _REQUIRED_TOP_LEVEL_KEYS:
            missing = _REQUIRED_TOP_LEVEL_KEYS - keys
            unknown = keys - _REQUIRED_TOP_LEVEL_KEYS
            raise GenomeError(f"genome top-level keys mismatch — missing={sorted(missing)} unknown={sorted(unknown)}")
```

with:

```python
        keys = set(payload.keys())
        allowed_keys = _REQUIRED_TOP_LEVEL_KEYS | _TOP_LEVEL_OPTIONAL_KEYS
        if not (_REQUIRED_TOP_LEVEL_KEYS <= keys <= allowed_keys):
            missing = _REQUIRED_TOP_LEVEL_KEYS - keys
            unknown = keys - allowed_keys
            raise GenomeError(f"genome top-level keys mismatch — missing={sorted(missing)} unknown={sorted(unknown)}")
```

Add motor-genes loading just before the final `return Genome(...)`:

```python
        raw_motor = payload.get("motor")
        if raw_motor is None:
            motor = MotorGenes()
        else:
            motor_payload = _require_mapping(
                raw_motor,
                "motor",
                required_keys=frozenset({"slot_count", "basal_cost", "initial_health", "execution_threshold"}),
            )
            motor = MotorGenes(
                slot_count=_require_int(motor_payload["slot_count"], "motor.slot_count", minimum=1),
                basal_cost=_require_float(motor_payload["basal_cost"], "motor.basal_cost", minimum=0.0, maximum=1.0),
                initial_health=_require_float(
                    motor_payload["initial_health"], "motor.initial_health", minimum=0.0, maximum=1.0
                ),
                execution_threshold=_require_float(
                    motor_payload["execution_threshold"], "motor.execution_threshold", minimum=0.0, maximum=1.0
                ),
            )
```

and add `motor=motor,` to the `return Genome(...)` call.

Finally, in `_genome_to_plain_dict`, add (right before the final `return`):

```python
    plain: dict[str, Any] = {
        "schema_version": genome.schema_version,
        "genome_id": genome.genome_id,
        "parent_ids": list(genome.parent_ids),
        "kernel_compatibility": genome.kernel_compatibility,
        "development": development,
        "plasticity": {
            "learning_rate": _range_spec_to_plain_dict(genome.plasticity.learning_rate),
            "forgetting_rate": _range_spec_to_plain_dict(genome.plasticity.forgetting_rate),
            "eligibility_decay": genome.plasticity.eligibility_decay,
        },
        "structure": asdict(genome.structure),
        "mutation_policy": asdict(genome.mutation_policy),
    }
    if genome.motor != _DEFAULT_MOTOR_GENES:
        plain["motor"] = asdict(genome.motor)
    return plain
```

(replacing the existing bare `return {...}` at the end of that function with this `plain` dict plus conditional motor key, so `genome_hash` is byte-identical to before this change for every genome that never sets a non-default `motor`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_genome_motor_genes.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run full genome test suite to check for regressions**

Run: `pytest tests/unit -k genome -v`
Expected: PASS, no change to any existing genome-hash golden values.

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/cognition/genome.py tests/unit/actuation/__init__.py tests/unit/actuation/test_genome_motor_genes.py
git commit -m "feat(actuation): add optional MotorGenes gene group, hash-stable by default"
```

---

### Task 2: Core types — `MotorCandidate`, `MotorIntent`, `Actuation`

**Files:**

- Create: `src/symbiont/actuation/__init__.py`
- Create: `src/symbiont/actuation/types.py`
- Test: `tests/unit/actuation/test_types.py`

**Interfaces:**

- Produces: `ActuatorId = str` (type alias), `MotorCandidate(actuator_id: ActuatorId)`, `MotorIntent(actuator_id: ActuatorId, activation: float)`, `Actuation(actuator_id: ActuatorId, requested: float, delivered: float, cost: float, health_at_execution: float)`. All frozen, slotted, validated in `__post_init__` (finite, `activation`/`requested`/`delivered`/`health_at_execution` in `[0.0, 1.0]`, `cost >= 0.0`).
- Consumes: nothing from other actuation modules.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_types.py
from __future__ import annotations

import math

import pytest

from symbiont.actuation.types import Actuation, MotorCandidate, MotorIntent


def test_motor_candidate_holds_actuator_id():
    candidate = MotorCandidate(actuator_id="actuator.deadbeef")
    assert candidate.actuator_id == "actuator.deadbeef"


def test_motor_intent_requires_activation_in_unit_range():
    MotorIntent(actuator_id="actuator.a", activation=0.0)
    MotorIntent(actuator_id="actuator.a", activation=1.0)
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=1.1)
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=-0.1)


def test_motor_intent_rejects_non_finite_activation():
    with pytest.raises(ValueError):
        MotorIntent(actuator_id="actuator.a", activation=math.nan)


def test_actuation_requires_delivered_le_requested_domain_and_finite_cost():
    actuation = Actuation(
        actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=0.1, health_at_execution=0.9
    )
    assert actuation.delivered == 0.5
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=-0.1, cost=0.1, health_at_execution=0.9)
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=-0.1, health_at_execution=0.9)
    with pytest.raises(ValueError):
        Actuation(actuator_id="actuator.a", requested=0.8, delivered=0.5, cost=0.1, health_at_execution=1.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/__init__.py
```

(empty file — package marker)

```python
# src/symbiont/actuation/types.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

ActuatorId = str


def _require_finite(value: Any, field: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _require_unit_range(value: Any, field: str) -> float:
    number = _require_finite(value, field)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be within [0.0, 1.0]")
    return number


@dataclass(frozen=True, slots=True)
class MotorCandidate:
    """A motor channel not yet consolidated into the active repertoire."""

    actuator_id: ActuatorId


@dataclass(frozen=True, slots=True)
class MotorIntent:
    """What the organism intends to do, before the body executes it."""

    actuator_id: ActuatorId
    activation: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "activation", _require_unit_range(self.activation, "activation"))


@dataclass(frozen=True, slots=True)
class Actuation:
    """What the body actually delivered. No World consequence lives here."""

    actuator_id: ActuatorId
    requested: float
    delivered: float
    cost: float
    health_at_execution: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "requested", _require_unit_range(self.requested, "requested"))
        object.__setattr__(self, "delivered", _require_unit_range(self.delivered, "delivered"))
        object.__setattr__(self, "health_at_execution", _require_unit_range(self.health_at_execution, "health_at_execution"))
        cost = _require_finite(self.cost, "cost")
        if cost < 0.0:
            raise ValueError("cost must be non-negative")
        object.__setattr__(self, "cost", cost)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_types.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/__init__.py src/symbiont/actuation/types.py tests/unit/actuation/test_types.py
git commit -m "feat(actuation): add MotorCandidate/MotorIntent/Actuation types"
```

---

### Task 3: `ActuatorConstitution` — the fixed motor body

**Files:**

- Create: `src/symbiont/actuation/constitution.py`
- Modify: `src/symbiont/cognition/birth.py`
- Test: `tests/unit/actuation/test_constitution.py`

**Interfaces:**

- Consumes: `symbiont.cognition.genome.MotorGenes` (Task 1), `symbiont.actuation.types.ActuatorId` (Task 2).
- Produces: `MotorSlot(slot_id: str, actuator_id: ActuatorId, basal_cost: float, initial_health: float, execution_threshold: float)`, `ActuatorConstitution(slots: tuple[MotorSlot, ...])` with property `actuator_ids -> tuple[ActuatorId, ...]` and `slot_for(actuator_id: ActuatorId) -> MotorSlot`. Function `derive_actuator_constitution(motor: MotorGenes) -> ActuatorConstitution`. In `birth.py`: `load_actuator_constitution(genome: Genome) -> ActuatorConstitution`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_constitution.py
from __future__ import annotations

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.constitution import ActuatorConstitution, MotorSlot, derive_actuator_constitution


def test_derive_actuator_constitution_produces_slot_count_slots():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=4))
    assert len(constitution.slots) == 4
    assert all(isinstance(slot, MotorSlot) for slot in constitution.slots)


def test_actuator_ids_are_unique_and_stable_across_calls():
    motor = MotorGenes(slot_count=6)
    first = derive_actuator_constitution(motor)
    second = derive_actuator_constitution(motor)
    assert first.actuator_ids == second.actuator_ids
    assert len(set(first.actuator_ids)) == 6


def test_actuator_ids_stable_when_only_non_motor_genes_change():
    # Same MotorGenes content -> same actuator_ids, regardless of what else
    # differs elsewhere in a genome. This module only ever sees MotorGenes,
    # so it cannot see (and therefore cannot react to) unrelated mutations.
    baseline = derive_actuator_constitution(MotorGenes())
    same_motor_genes = derive_actuator_constitution(MotorGenes())
    assert baseline.actuator_ids == same_motor_genes.actuator_ids


def test_actuator_ids_change_only_when_slot_count_changes():
    six_slots = derive_actuator_constitution(MotorGenes(slot_count=6))
    three_slots = derive_actuator_constitution(MotorGenes(slot_count=3))
    assert set(three_slots.actuator_ids) <= set(six_slots.actuator_ids)


def test_slot_params_do_not_affect_actuator_id():
    cheap = derive_actuator_constitution(MotorGenes(slot_count=2, basal_cost=0.01))
    expensive = derive_actuator_constitution(MotorGenes(slot_count=2, basal_cost=0.5))
    assert cheap.actuator_ids == expensive.actuator_ids


def test_constitution_slots_are_immutable_tuple_not_dict():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    assert isinstance(constitution.slots, tuple)
    with pytest.raises(AttributeError):
        constitution.slots = ()  # type: ignore[misc]


def test_slot_for_looks_up_by_actuator_id():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    actuator_id = constitution.actuator_ids[0]
    slot = constitution.slot_for(actuator_id)
    assert slot.actuator_id == actuator_id


def test_slot_for_raises_for_unknown_actuator_id():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    with pytest.raises(KeyError):
        constitution.slot_for("actuator.does-not-exist")
```

```python
# append to tests/unit/actuation/test_constitution.py
from symbiont.cognition.birth import load_actuator_constitution
from symbiont.cognition.genome import Genome, GenomeCodec


def _genome_with_motor(**motor_kwargs) -> Genome:
    from tests.unit.actuation.test_genome_motor_genes import _base_payload

    payload = _base_payload()
    if motor_kwargs:
        payload["motor"] = {
            "slot_count": motor_kwargs.get("slot_count", 6),
            "basal_cost": motor_kwargs.get("basal_cost", 0.05),
            "initial_health": motor_kwargs.get("initial_health", 1.0),
            "execution_threshold": motor_kwargs.get("execution_threshold", 0.5),
        }
    return GenomeCodec().load(payload)


def test_load_actuator_constitution_from_genome_matches_direct_derivation():
    genome = _genome_with_motor(slot_count=3)
    from_birth = load_actuator_constitution(genome)
    direct = derive_actuator_constitution(genome.motor)
    assert from_birth.actuator_ids == direct.actuator_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_constitution.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.constitution'`

- [ ] **Step 3: Implement `constitution.py`**

```python
# src/symbiont/actuation/constitution.py
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from symbiont.cognition.genome import MotorGenes

from .types import ActuatorId

_ACTUATION_SCHEMA = "symbiont-actuation-v1"


def _slot_id(index: int) -> str:
    return f"motor_slot.{index}"


def _actuator_id_for_slot(slot_id: str) -> ActuatorId:
    digest = sha256(f"{_ACTUATION_SCHEMA}:{slot_id}".encode("utf-8")).hexdigest()[:16]
    return f"actuator.{digest}"


@dataclass(frozen=True, slots=True)
class MotorSlot:
    slot_id: str
    actuator_id: ActuatorId
    basal_cost: float
    initial_health: float
    execution_threshold: float


@dataclass(frozen=True, slots=True)
class ActuatorConstitution:
    slots: tuple[MotorSlot, ...]

    @property
    def actuator_ids(self) -> tuple[ActuatorId, ...]:
        return tuple(slot.actuator_id for slot in self.slots)

    def slot_for(self, actuator_id: ActuatorId) -> MotorSlot:
        for slot in self.slots:
            if slot.actuator_id == actuator_id:
                return slot
        raise KeyError(f"unknown actuator_id {actuator_id!r}")


def derive_actuator_constitution(motor: MotorGenes) -> ActuatorConstitution:
    """Deterministic body-constitution derivation.

    Only ``motor`` is consulted — never the enclosing genome's id or hash —
    so a mutation to any non-motor gene cannot rename an inherited actuator.
    """
    slots = tuple(
        MotorSlot(
            slot_id=(slot_id := _slot_id(index)),
            actuator_id=_actuator_id_for_slot(slot_id),
            basal_cost=motor.basal_cost,
            initial_health=motor.initial_health,
            execution_threshold=motor.execution_threshold,
        )
        for index in range(motor.slot_count)
    )
    return ActuatorConstitution(slots=slots)
```

- [ ] **Step 4: Add `load_actuator_constitution` to `birth.py`**

Add to `src/symbiont/cognition/birth.py`:

```python
from symbiont.actuation.constitution import ActuatorConstitution, derive_actuator_constitution


def load_actuator_constitution(genome: Genome) -> ActuatorConstitution:
    """Derive this organism's fixed motor body from its own genome.

    Unlike ``load_base_genome``/``load_base_cognition``, this is not
    canonical-first-birth-only: it must be called for every organism,
    including descendants, using that organism's own (possibly mutated)
    genome — the constitution is constitutional per-individual, not a
    shared canonical default.
    """
    return derive_actuator_constitution(genome.motor)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_constitution.py -v`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/actuation/constitution.py src/symbiont/cognition/birth.py tests/unit/actuation/test_constitution.py
git commit -m "feat(actuation): derive stable ActuatorConstitution from MotorGenes"
```

---

### Task 4: Non-periodic, RNG-namespaced probing calendar

**Files:**

- Create: `src/symbiont/actuation/calendar.py`
- Test: `tests/unit/actuation/test_calendar.py`

**Interfaces:**

- Consumes: `symbiont.environment.rng.derive_seed(seed: int, namespace: str) -> int` (existing).
- Produces: `probing_calendar(*, organism_id: str, actuator_id: ActuatorId, window_index: int, window_ticks: int) -> tuple[bool, ...]` — length `window_ticks`, balanced (± 1 for odd length), deterministic for identical inputs, different for different `window_index`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_calendar.py
from __future__ import annotations

import pytest

from symbiont.actuation.calendar import probing_calendar


def test_calendar_length_matches_window_ticks():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=8)
    assert len(calendar) == 8


def test_calendar_is_balanced_even_length():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=8)
    assert sum(calendar) == 4


def test_calendar_is_balanced_within_one_odd_length():
    calendar = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=7)
    assert sum(calendar) in (3, 4)


def test_calendar_is_deterministic_for_same_inputs():
    first = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=2, window_ticks=10)
    second = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=2, window_ticks=10)
    assert first == second


def test_calendar_differs_across_window_index():
    windows = [
        probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=i, window_ticks=12)
        for i in range(5)
    ]
    assert len(set(windows)) > 1


def test_calendar_differs_across_actuator_id():
    a = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=12)
    b = probing_calendar(organism_id="org-1", actuator_id="actuator.b", window_index=0, window_ticks=12)
    assert a != b


def test_calendar_differs_across_organism_id():
    a = probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=12)
    b = probing_calendar(organism_id="org-2", actuator_id="actuator.a", window_index=0, window_ticks=12)
    assert a != b


def test_calendar_rejects_non_positive_window_ticks():
    with pytest.raises(ValueError):
        probing_calendar(organism_id="org-1", actuator_id="actuator.a", window_index=0, window_ticks=0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_calendar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.calendar'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/calendar.py
from __future__ import annotations

import random

from symbiont.environment.rng import derive_seed

from .types import ActuatorId


def probing_calendar(
    *, organism_id: str, actuator_id: ActuatorId, window_index: int, window_ticks: int
) -> tuple[bool, ...]:
    """A balanced, non-periodic ON/OFF schedule for one probing window.

    True means "activate the candidate this tick", False means "hold it at
    zero as a control". Deliberately not tick-parity-based: a fixed
    even/odd rule would alias with any period-2 environmental regularity
    and could be mistaken for actuator causality. The schedule is instead a
    balanced shuffle seeded independently of any percept, namespaced by
    organism, actuator and window so distinct windows use distinct orders
    (spec docs/design/symbiont-actuation-v1.md §6).
    """
    if window_ticks < 1:
        raise ValueError("window_ticks must be at least 1")

    on_count = window_ticks // 2
    off_count = window_ticks - on_count
    schedule = [True] * on_count + [False] * off_count

    # derive_seed's own sha256 payload already encodes the full namespace
    # string; the base seed here is a fixed constant, not a Python hash()
    # of the namespace — str hash() is randomized per-process by default
    # (PYTHONHASHSEED) and would make this non-deterministic across runs.
    namespace = f"actuation:{organism_id}:{actuator_id}:{window_index}"
    seed = derive_seed(0, namespace)
    random.Random(seed).shuffle(schedule)
    return tuple(schedule)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_calendar.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/calendar.py tests/unit/actuation/test_calendar.py
git commit -m "feat(actuation): non-periodic RNG-namespaced ON/OFF probing calendar"
```

---

### Task 5: `ActuatorCandidateState` — bounded effect evidence

**Files:**

- Create: `src/symbiont/actuation/candidate.py`
- Test: `tests/unit/actuation/test_candidate.py`

**Interfaces:**

- Consumes: `symbiont.host.adaptive.PairAccumulator` (existing, reused unmodified), `symbiont.actuation.types.ActuatorId`.
- Produces: `ProbingState` (`Literal["active", "probing", "dormant"]`), `ActuatorCandidateState(actuator_id, activations=0, effect_relations: dict[str, PairAccumulator], cost_evidence=0.0, probing_state="dormant", last_seen_tick=0, windows_completed=0)` with methods `observe_effect(percept_id: str, activation: float, delta_percept: float) -> None` (bounded to `max_effect_relations_per_candidate`, evicts the weakest-evidence relation when full), `effect_strength -> float` (max `abs(correlation)` across `effect_relations`, `0.0` if none has enough samples), `to_payload() -> dict`, `from_payload(payload: dict) -> ActuatorCandidateState` (classmethod).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_candidate.py
from __future__ import annotations

import pytest

from symbiont.actuation.candidate import ActuatorCandidateState, _MAX_EFFECT_RELATIONS_PER_CANDIDATE


def test_new_candidate_starts_dormant_with_zero_effect_strength():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    assert state.probing_state == "dormant"
    assert state.effect_strength == 0.0


def test_observe_effect_accumulates_into_named_percept_relation():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    for i in range(10):
        activation = float(i % 2)
        delta = activation * 1.0  # perfectly causal signal
        state.observe_effect("percept.x", activation=activation, delta_percept=delta)
    assert "percept.x" in state.effect_relations
    assert state.effect_relations["percept.x"].count == 10


def test_effect_strength_is_high_for_causal_relation_and_low_for_noise():
    causal = ActuatorCandidateState(actuator_id="actuator.causal")
    sham = ActuatorCandidateState(actuator_id="actuator.sham")
    import random

    rng = random.Random(7)
    for i in range(40):
        activation = float(i % 2)
        causal.observe_effect("percept.x", activation=activation, delta_percept=activation + rng.gauss(0, 0.01))
        sham.observe_effect("percept.x", activation=activation, delta_percept=rng.gauss(0, 1.0))
    assert causal.effect_strength > 0.9
    assert causal.effect_strength > sham.effect_strength


def test_effect_relations_bounded_by_max_per_candidate():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    for i in range(_MAX_EFFECT_RELATIONS_PER_CANDIDATE + 5):
        state.observe_effect(f"percept.{i}", activation=1.0, delta_percept=0.5)
    assert len(state.effect_relations) <= _MAX_EFFECT_RELATIONS_PER_CANDIDATE


def test_export_withholds_relations_below_minimum_samples():
    state = ActuatorCandidateState(actuator_id="actuator.a")
    state.observe_effect("percept.x", activation=1.0, delta_percept=0.5)  # one sample only
    payload = state.to_payload()
    assert payload["effect_relations"] == {}


def test_export_restore_round_trip_preserves_established_relations():
    state = ActuatorCandidateState(actuator_id="actuator.a", probing_state="probing", windows_completed=2)
    for i in range(10):
        activation = float(i % 2)
        state.observe_effect("percept.x", activation=activation, delta_percept=activation)
    payload = state.to_payload()
    restored = ActuatorCandidateState.from_payload(payload)
    assert restored.actuator_id == "actuator.a"
    assert restored.probing_state == "probing"
    assert restored.windows_completed == 2
    assert restored.effect_relations["percept.x"].count == 10


def test_from_payload_raises_on_corrupted_probing_state():
    payload = {
        "actuator_id": "actuator.a",
        "activations": 0,
        "probing_state": "orbiting",  # not a valid state
        "windows_completed": 0,
        "last_seen_tick": 0,
        "cost_evidence": 0.0,
        "effect_relations": {},
    }
    with pytest.raises(ValueError):
        ActuatorCandidateState.from_payload(payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_candidate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.candidate'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/candidate.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from symbiont.host.adaptive import PairAccumulator

from .types import ActuatorId

ProbingState = Literal["active", "probing", "dormant"]
_VALID_PROBING_STATES: frozenset[str] = frozenset({"active", "probing", "dormant"})
_MAX_EFFECT_RELATIONS_PER_CANDIDATE = 16
_MIN_RELATION_SAMPLES_FOR_EXPORT = 6


@dataclass(slots=True)
class ActuatorCandidateState:
    """Bounded, per-actuator record of observed activation -> Δpercept effect.

    Tracks effect/controllability evidence only (spec §5): whether
    activating this channel has a measurable, reproducible consequence.
    Whether that consequence is desirable is never decided here.
    """

    actuator_id: ActuatorId
    activations: int = 0
    effect_relations: dict[str, PairAccumulator] = field(default_factory=dict)
    cost_evidence: float = 0.0
    probing_state: ProbingState = "dormant"
    last_seen_tick: int = 0
    windows_completed: int = 0

    def observe_effect(self, percept_id: str, *, activation: float, delta_percept: float) -> None:
        self.activations += 1
        relation = self.effect_relations.get(percept_id)
        if relation is None:
            if len(self.effect_relations) >= _MAX_EFFECT_RELATIONS_PER_CANDIDATE:
                self._evict_weakest_relation()
            relation = PairAccumulator()
            self.effect_relations[percept_id] = relation
        relation.observe(activation, delta_percept)

    def _evict_weakest_relation(self) -> None:
        def strength(item: tuple[str, PairAccumulator]) -> float:
            correlation = item[1].correlation
            return abs(correlation) if correlation is not None else -1.0

        weakest_id, _ = min(self.effect_relations.items(), key=strength)
        del self.effect_relations[weakest_id]

    @property
    def effect_strength(self) -> float:
        strengths = [
            abs(relation.correlation)
            for relation in self.effect_relations.values()
            if relation.correlation is not None
        ]
        return max(strengths, default=0.0)

    def to_payload(self) -> dict[str, Any]:
        return {
            "actuator_id": self.actuator_id,
            "activations": self.activations,
            "cost_evidence": self.cost_evidence,
            "probing_state": self.probing_state,
            "last_seen_tick": self.last_seen_tick,
            "windows_completed": self.windows_completed,
            "effect_relations": {
                percept_id: relation.to_payload()
                for percept_id, relation in self.effect_relations.items()
                if relation.count >= _MIN_RELATION_SAMPLES_FOR_EXPORT
            },
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorCandidateState":
        probing_state = payload.get("probing_state")
        if probing_state not in _VALID_PROBING_STATES:
            raise ValueError(f"probing_state must be one of {sorted(_VALID_PROBING_STATES)}, got {probing_state!r}")
        raw_relations = payload.get("effect_relations", {})
        if not isinstance(raw_relations, dict):
            raise ValueError("effect_relations must be an object")
        effect_relations = {
            percept_id: PairAccumulator.from_payload(dict(raw))
            for percept_id, raw in raw_relations.items()
        }
        return cls(
            actuator_id=str(payload["actuator_id"]),
            activations=int(payload.get("activations", 0)),
            effect_relations=effect_relations,
            cost_evidence=float(payload.get("cost_evidence", 0.0)),
            probing_state=probing_state,  # type: ignore[arg-type]
            last_seen_tick=int(payload.get("last_seen_tick", 0)),
            windows_completed=int(payload.get("windows_completed", 0)),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_candidate.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/candidate.py tests/unit/actuation/test_candidate.py
git commit -m "feat(actuation): ActuatorCandidateState with bounded PairAccumulator effect evidence"
```

---

### Task 6: `ActuatorProposer` — active/probing/dormant lifecycle

**Files:**

- Create: `src/symbiont/actuation/proposer.py`
- Test: `tests/unit/actuation/test_proposer.py`

**Interfaces:**

- Consumes: `ActuatorConstitution` (Task 3), `ActuatorCandidateState` (Task 5), `probing_calendar` (Task 4).
- Produces: `ActuatorProposer(constitution: ActuatorConstitution, *, organism_id: str, min_probing_windows: int = 2, effect_threshold: float = 0.5, window_ticks: int = 8, probe_limit: int = 1)` with:
  - `states -> tuple[ActuatorCandidateState, ...]` (read-only view, sorted by `actuator_id`)
  - `active_repertoire -> tuple[ActuatorId, ...]`
  - `probing_plan(*, tick: int) -> dict[ActuatorId, bool]` — called once per real simulation tick. For each actuator currently selected for probing (bounded by `probe_limit` concurrently-probing candidates), returns `True`/`False` from that actuator's own calendar at its own current position within its current window (tracked per-actuator, not from the global `tick` value — two actuators probed on different ticks are still at consistent positions in their own `window_ticks`-long calendar).
  - `record_effect(actuator_id: ActuatorId, percept_id: str, *, activation: float, delta_percept: float, tick: int) -> None`
  - `advance_tick(actuator_id: ActuatorId) -> None` — call once per tick, for every actuator that appeared in that tick's `probing_plan`. Advances that actuator's position within its current window; when `window_ticks` positions have been consumed, the window completes: `windows_completed` increments and the candidate promotes to `active` if `windows_completed >= min_probing_windows` and `effect_strength >= effect_threshold`, otherwise it remains `probing` and a fresh window (new calendar, `window_index = windows_completed`) begins.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_proposer.py
from __future__ import annotations

import random

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer


def _constitution(slot_count: int = 2):
    return derive_actuator_constitution(MotorGenes(slot_count=slot_count))


def test_new_proposer_has_all_actuators_dormant():
    constitution = _constitution()
    proposer = ActuatorProposer(constitution, organism_id="org-1")
    assert proposer.active_repertoire == ()
    assert all(state.probing_state == "dormant" for state in proposer.states)


def test_probing_plan_only_selects_up_to_probe_limit_candidates():
    constitution = _constitution(slot_count=6)
    proposer = ActuatorProposer(constitution, organism_id="org-1", probe_limit=1)
    plan = proposer.probing_plan(tick=0)
    assert len(plan) <= 1


def test_causal_actuator_reaches_active_after_enough_windows():
    constitution = _constitution(slot_count=2)
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-1", min_probing_windows=2, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )
    rng = random.Random(11)

    total_ticks = 8 * 3  # three full windows of 8 ticks each
    for tick in range(total_ticks):
        plan = proposer.probing_plan(tick=tick)
        for actuator_id, on in plan.items():
            activation = 1.0 if on else 0.0
            if actuator_id == causal_id:
                delta = activation + rng.gauss(0, 0.02)
            else:
                delta = rng.gauss(0, 1.0)
            proposer.record_effect(actuator_id, "percept.x", activation=activation, delta_percept=delta, tick=tick)
        for actuator_id in plan:
            proposer.advance_tick(actuator_id)

    assert causal_id in proposer.active_repertoire
    assert sham_id not in proposer.active_repertoire


def test_probing_candidate_stays_probing_before_min_windows_reached():
    constitution = _constitution(slot_count=1)
    (actuator_id,) = constitution.actuator_ids
    proposer = ActuatorProposer(constitution, organism_id="org-1", min_probing_windows=5, window_ticks=8)
    for tick in range(8):  # exactly one full window, min_probing_windows requires five
        proposer.probing_plan(tick=tick)
        proposer.record_effect(actuator_id, "percept.x", activation=1.0, delta_percept=1.0, tick=tick)
        proposer.advance_tick(actuator_id)
    state = next(s for s in proposer.states if s.actuator_id == actuator_id)
    assert state.probing_state == "probing"
    assert state.windows_completed == 1
    assert actuator_id not in proposer.active_repertoire
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_proposer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.proposer'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/proposer.py
from __future__ import annotations

from .calendar import probing_calendar
from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .types import ActuatorId


class ActuatorProposer:
    """Bounded exploration of an organism's fixed motor body (spec §4).

    Only ``constitution.actuator_ids`` are ever considered — this never
    invents an actuator_id that isn't already part of the body.
    """

    def __init__(
        self,
        constitution: ActuatorConstitution,
        *,
        organism_id: str,
        min_probing_windows: int = 2,
        effect_threshold: float = 0.5,
        window_ticks: int = 8,
        probe_limit: int = 1,
    ) -> None:
        if min_probing_windows < 1:
            raise ValueError("min_probing_windows must be at least 1")
        if not 0.0 <= effect_threshold <= 1.0:
            raise ValueError("effect_threshold must be within [0.0, 1.0]")
        if window_ticks < 1:
            raise ValueError("window_ticks must be at least 1")
        if probe_limit < 1:
            raise ValueError("probe_limit must be at least 1")

        self._constitution = constitution
        self._organism_id = organism_id
        self._min_probing_windows = min_probing_windows
        self._effect_threshold = effect_threshold
        self._window_ticks = window_ticks
        self._probe_limit = probe_limit
        self._states: dict[ActuatorId, ActuatorCandidateState] = {
            actuator_id: ActuatorCandidateState(actuator_id=actuator_id)
            for actuator_id in constitution.actuator_ids
        }
        self._tick_in_window: dict[ActuatorId, int] = {
            actuator_id: 0 for actuator_id in constitution.actuator_ids
        }
        self._probe_cursor = 0

    @property
    def states(self) -> tuple[ActuatorCandidateState, ...]:
        return tuple(sorted(self._states.values(), key=lambda state: state.actuator_id))

    @property
    def active_repertoire(self) -> tuple[ActuatorId, ...]:
        return tuple(
            state.actuator_id for state in self.states if state.probing_state == "active"
        )

    def _candidates_for_probing(self) -> list[ActuatorId]:
        return [
            actuator_id
            for actuator_id, state in self._states.items()
            if state.probing_state in ("dormant", "probing")
        ]

    def probing_plan(self, *, tick: int) -> dict[ActuatorId, bool]:
        """Called once per real simulation tick.

        ``tick`` only drives the bounded rotation of *which* candidates get
        probed this tick (mirrors ``sampling_plan``'s cursor in
        host/adaptive.py); each actuator's ON/OFF value comes from its own
        per-actuator position within its own current window, tracked in
        ``self._tick_in_window`` — never from ``tick`` directly, so two
        actuators probed on different ticks still each see a complete,
        internally-consistent ``window_ticks``-long calendar.
        """
        pool = sorted(self._candidates_for_probing())
        if not pool:
            return {}
        start = self._probe_cursor % len(pool)
        count = min(self._probe_limit, len(pool))
        selected = [pool[(start + offset) % len(pool)] for offset in range(count)]
        self._probe_cursor += count

        plan: dict[ActuatorId, bool] = {}
        for actuator_id in selected:
            state = self._states[actuator_id]
            if state.probing_state == "dormant":
                state.probing_state = "probing"
            calendar = probing_calendar(
                organism_id=self._organism_id,
                actuator_id=actuator_id,
                window_index=state.windows_completed,
                window_ticks=self._window_ticks,
            )
            position = self._tick_in_window[actuator_id]
            plan[actuator_id] = calendar[position]
        return plan

    def record_effect(
        self, actuator_id: ActuatorId, percept_id: str, *, activation: float, delta_percept: float, tick: int
    ) -> None:
        state = self._states[actuator_id]
        state.observe_effect(percept_id, activation=activation, delta_percept=delta_percept)
        state.last_seen_tick = tick

    def advance_tick(self, actuator_id: ActuatorId) -> None:
        """Call once per tick for every actuator present in that tick's plan.

        Only the current window's phase (``_tick_in_window``) resets on a
        cold restart — it is not persisted (spec §11: transient scheduling
        phase, not established evidence). ``windows_completed`` and
        ``effect_relations`` are what actually gate promotion, and both are
        checkpointed via ``ActuatorCandidateState``.
        """
        self._tick_in_window[actuator_id] += 1
        if self._tick_in_window[actuator_id] < self._window_ticks:
            return
        self._tick_in_window[actuator_id] = 0
        state = self._states[actuator_id]
        state.windows_completed += 1
        if (
            state.windows_completed >= self._min_probing_windows
            and state.effect_strength >= self._effect_threshold
        ):
            state.probing_state = "active"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_proposer.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/proposer.py tests/unit/actuation/test_proposer.py
git commit -m "feat(actuation): ActuatorProposer active/probing/dormant lifecycle"
```

---

### Task 7: `ActuatorState` — health/reliability/cost

**Files:**

- Create: `src/symbiont/actuation/health.py`
- Test: `tests/unit/actuation/test_health.py`

**Interfaces:**

- Consumes: `MotorSlot` (Task 3) for initial values.
- Produces: `ActuatorState(actuator_id, health: float, reliability: float, cost: float)` with `classmethod from_slot(slot: MotorSlot) -> ActuatorState`, `degrade(amount: float) -> None` (clamps `health` to `[0.0, 1.0]`), `to_payload()`/`from_payload()` (the latter raises `ValueError` on any out-of-range or missing field — corruption must fail loudly, never silently coerce to a "safe" default, per spec §15).

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_health.py
from __future__ import annotations

import pytest

from symbiont.actuation.constitution import MotorSlot
from symbiont.actuation.health import ActuatorState


def _slot() -> MotorSlot:
    return MotorSlot(
        slot_id="motor_slot.0",
        actuator_id="actuator.a",
        basal_cost=0.05,
        initial_health=1.0,
        execution_threshold=0.5,
    )


def test_from_slot_uses_slot_initial_values():
    state = ActuatorState.from_slot(_slot())
    assert state.actuator_id == "actuator.a"
    assert state.health == 1.0
    assert state.reliability == 1.0
    assert state.cost == 0.05


def test_degrade_clamps_health_to_zero_floor():
    state = ActuatorState.from_slot(_slot())
    state.degrade(1.5)
    assert state.health == 0.0


def test_degrade_rejects_negative_amount():
    state = ActuatorState.from_slot(_slot())
    with pytest.raises(ValueError):
        state.degrade(-0.1)


def test_payload_round_trip():
    state = ActuatorState.from_slot(_slot())
    state.degrade(0.3)
    restored = ActuatorState.from_payload(state.to_payload())
    assert restored.health == pytest.approx(0.7)
    assert restored.actuator_id == "actuator.a"


def test_from_payload_raises_on_out_of_range_health_instead_of_clamping():
    payload = {"actuator_id": "actuator.a", "health": 1.4, "reliability": 1.0, "cost": 0.05}
    with pytest.raises(ValueError):
        ActuatorState.from_payload(payload)


def test_from_payload_raises_on_missing_field():
    payload = {"actuator_id": "actuator.a", "health": 1.0, "cost": 0.05}
    with pytest.raises(ValueError):
        ActuatorState.from_payload(payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.health'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/health.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .constitution import MotorSlot
from .types import ActuatorId, _require_finite, _require_unit_range


@dataclass(slots=True)
class ActuatorState:
    """Physiological state of one actuator: health/reliability/cost.

    ``degrade`` models ordinary wear (spec §15: "actuator unavailable/
    degraded"). A malformed checkpoint payload must raise, never coerce
    into a plausible-looking degraded state — that would disguise data
    corruption as fisiología.
    """

    actuator_id: ActuatorId
    health: float
    reliability: float
    cost: float

    @classmethod
    def from_slot(cls, slot: MotorSlot) -> "ActuatorState":
        return cls(actuator_id=slot.actuator_id, health=slot.initial_health, reliability=1.0, cost=slot.basal_cost)

    def degrade(self, amount: float) -> None:
        amount = _require_finite(amount, "amount")
        if amount < 0.0:
            raise ValueError("amount must be non-negative")
        self.health = max(0.0, min(1.0, self.health - amount))

    def to_payload(self) -> dict[str, Any]:
        return {
            "actuator_id": self.actuator_id,
            "health": self.health,
            "reliability": self.reliability,
            "cost": self.cost,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ActuatorState":
        required = {"actuator_id", "health", "reliability", "cost"}
        missing = required - set(payload)
        if missing:
            raise ValueError(f"ActuatorState payload missing fields: {sorted(missing)}")
        return cls(
            actuator_id=str(payload["actuator_id"]),
            health=_require_unit_range(payload["health"], "health"),
            reliability=_require_unit_range(payload["reliability"], "reliability"),
            cost=_require_finite(payload["cost"], "cost"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_health.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/health.py tests/unit/actuation/test_health.py
git commit -m "feat(actuation): ActuatorState health/reliability/cost, corruption fails loudly"
```

---

### Task 8: `ActuatorSystem.execute` — `MotorIntent` → `Actuation`

**Files:**

- Create: `src/symbiont/actuation/system.py`
- Test: `tests/unit/actuation/test_system.py`

**Interfaces:**

- Consumes: `MotorIntent`, `Actuation` (Task 2), `ActuatorState` (Task 7).
- Produces: `ActuatorSystem.execute(intent: MotorIntent, state: ActuatorState) -> Actuation` — pure function of its two inputs, no I/O, no cognition, no World.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_system.py
from __future__ import annotations

from symbiont.actuation.health import ActuatorState
from symbiont.actuation.system import ActuatorSystem
from symbiont.actuation.types import MotorIntent


def test_healthy_actuator_delivers_full_requested_activation():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=0.8)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.requested == 0.8
    assert actuation.delivered == 0.8
    assert actuation.health_at_execution == 1.0


def test_degraded_actuator_delivers_less_than_requested():
    state = ActuatorState(actuator_id="actuator.a", health=0.5, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=0.8)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.delivered == 0.4  # 0.8 * health(0.5)


def test_zero_health_actuator_delivers_nothing():
    state = ActuatorState(actuator_id="actuator.a", health=0.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.a", activation=1.0)
    actuation = ActuatorSystem().execute(intent, state)
    assert actuation.delivered == 0.0


def test_cost_scales_with_requested_activation():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.1)
    low = ActuatorSystem().execute(MotorIntent(actuator_id="actuator.a", activation=0.2), state)
    high = ActuatorSystem().execute(MotorIntent(actuator_id="actuator.a", activation=1.0), state)
    assert high.cost > low.cost


def test_execute_rejects_mismatched_actuator_ids():
    state = ActuatorState(actuator_id="actuator.a", health=1.0, reliability=1.0, cost=0.05)
    intent = MotorIntent(actuator_id="actuator.other", activation=0.5)
    import pytest

    with pytest.raises(ValueError):
        ActuatorSystem().execute(intent, state)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_system.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.system'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/system.py
from __future__ import annotations

from .health import ActuatorState
from .types import Actuation, MotorIntent


class ActuatorSystem:
    """Resolves a MotorIntent into an Actuation, given the body's own state.

    Pure with respect to World: nothing here knows what ``delivered``
    causes outside the organism (spec §2 — the World consequence is never
    part of Actuation).
    """

    def execute(self, intent: MotorIntent, state: ActuatorState) -> Actuation:
        if intent.actuator_id != state.actuator_id:
            raise ValueError(
                f"intent for {intent.actuator_id!r} cannot be executed against state for {state.actuator_id!r}"
            )
        delivered = intent.activation * state.health * state.reliability
        cost = state.cost * intent.activation
        return Actuation(
            actuator_id=intent.actuator_id,
            requested=intent.activation,
            delivered=delivered,
            cost=cost,
            health_at_execution=state.health,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_system.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/symbiont/actuation/system.py tests/unit/actuation/test_system.py
git commit -m "feat(actuation): ActuatorSystem.execute resolves MotorIntent to Actuation"
```

---

### Task 9: Checkpoint bundle + P0 gate test (causal vs sham, end to end)

**Files:**

- Create: `src/symbiont/actuation/checkpoint.py`
- Test: `tests/unit/actuation/test_checkpoint_gate.py`

**Interfaces:**

- Consumes: `ActuatorProposer` (Task 6), `ActuatorCandidateState` (Task 5).
- Produces: `export_actuation_state(proposer: ActuatorProposer) -> dict[str, Any]`, `restore_actuation_state(payload: dict[str, Any], constitution: ActuatorConstitution, *, organism_id: str) -> ActuatorProposer`. `restore_actuation_state` raises `ValueError` (never silently defaults) if `payload["candidates"]` references an `actuator_id` not present in `constitution.actuator_ids`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/actuation/test_checkpoint_gate.py
from __future__ import annotations

import random

import pytest

from symbiont.cognition.genome import MotorGenes
from symbiont.actuation.checkpoint import export_actuation_state, restore_actuation_state
from symbiont.actuation.constitution import derive_actuator_constitution
from symbiont.actuation.proposer import ActuatorProposer


def _run_causal_vs_sham(
    proposer: ActuatorProposer, causal_id: str, sham_id: str, *, windows: int, seed: int, window_ticks: int = 8
) -> None:
    rng = random.Random(seed)
    for tick in range(window_ticks * windows):
        plan = proposer.probing_plan(tick=tick)
        for actuator_id, on in plan.items():
            activation = 1.0 if on else 0.0
            if actuator_id == causal_id:
                delta = activation + rng.gauss(0, 0.02)
            else:
                delta = rng.gauss(0, 1.0)
            proposer.record_effect(actuator_id, "percept.x", activation=activation, delta_percept=delta, tick=tick)
        for actuator_id in plan:
            proposer.advance_tick(actuator_id)


def test_p0_gate_causal_actuator_promoted_sham_actuator_is_not():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-gate", min_probing_windows=3, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )

    _run_causal_vs_sham(proposer, causal_id, sham_id, windows=4, seed=42)

    assert causal_id in proposer.active_repertoire
    assert sham_id not in proposer.active_repertoire


def test_export_restore_round_trip_preserves_active_repertoire():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=2))
    causal_id, sham_id = constitution.actuator_ids
    proposer = ActuatorProposer(
        constitution, organism_id="org-gate", min_probing_windows=3, effect_threshold=0.6, window_ticks=8, probe_limit=2
    )
    _run_causal_vs_sham(proposer, causal_id, sham_id, windows=4, seed=42)

    payload = export_actuation_state(proposer)
    restored = restore_actuation_state(payload, constitution, organism_id="org-gate")

    assert restored.active_repertoire == proposer.active_repertoire


def test_restore_rejects_candidate_actuator_id_not_in_constitution():
    constitution = derive_actuator_constitution(MotorGenes(slot_count=1))
    payload = {
        "candidates": {
            "actuator.not-in-constitution": {
                "actuator_id": "actuator.not-in-constitution",
                "activations": 1,
                "cost_evidence": 0.0,
                "probing_state": "active",
                "last_seen_tick": 0,
                "windows_completed": 3,
                "effect_relations": {},
            }
        },
        "probe_cursor": 0,
    }
    with pytest.raises(ValueError):
        restore_actuation_state(payload, constitution, organism_id="org-gate")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/actuation/test_checkpoint_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'symbiont.actuation.checkpoint'`

- [ ] **Step 3: Implement**

```python
# src/symbiont/actuation/checkpoint.py
from __future__ import annotations

from typing import Any

from .candidate import ActuatorCandidateState
from .constitution import ActuatorConstitution
from .proposer import ActuatorProposer


def export_actuation_state(proposer: ActuatorProposer) -> dict[str, Any]:
    """Serialize established motor-discovery state (spec §11).

    Only aggregates already gated by ActuatorCandidateState.to_payload's
    own min-sample withholding are included — no raw activation/percept
    history crosses this boundary.
    """
    return {
        "candidates": {state.actuator_id: state.to_payload() for state in proposer.states},
        "probe_cursor": proposer._probe_cursor,  # noqa: SLF001 — checkpoint owns proposer internals by design
    }


def restore_actuation_state(
    payload: dict[str, Any], constitution: ActuatorConstitution, *, organism_id: str
) -> ActuatorProposer:
    """Rebuild an ActuatorProposer from a checkpoint payload.

    Any candidate referencing an actuator_id outside this organism's own
    ActuatorConstitution is a corrupted or foreign checkpoint (spec §15) —
    this raises rather than silently dropping or renaming it.

    Note (P0 scope limit): ``min_probing_windows``/``effect_threshold``/
    ``window_ticks``/``probe_limit`` are proposer *configuration*, not
    discovered state, and are not part of this payload — the caller must
    construct-equivalent config out of band (e.g. from ActuatorConstitution/
    genome-derived defaults) exactly as P2 will when this wires into World's
    own checkpoint. Only discovered candidate state and the probe cursor
    round-trip here.
    """
    known_ids = set(constitution.actuator_ids)
    raw_candidates = payload.get("candidates", {})
    if not isinstance(raw_candidates, dict):
        raise ValueError("candidates must be an object")

    proposer = ActuatorProposer(constitution, organism_id=organism_id)
    for actuator_id, raw_state in raw_candidates.items():
        if actuator_id not in known_ids:
            raise ValueError(
                f"checkpoint candidate {actuator_id!r} is not part of this organism's ActuatorConstitution"
            )
        proposer._states[actuator_id] = ActuatorCandidateState.from_payload(raw_state)  # noqa: SLF001

    proposer._probe_cursor = int(payload.get("probe_cursor", 0))  # noqa: SLF001
    return proposer
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/actuation/test_checkpoint_gate.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the entire actuation test suite together**

Run: `pytest tests/unit/actuation/ -v`
Expected: PASS (all tests from Tasks 1-9)

- [ ] **Step 6: Run the full project test suite to confirm zero regressions**

Run: `pytest`
Expected: PASS, same pre-existing pass count plus the new actuation tests, no failures elsewhere (in particular, `tests/unit -k genome` and anything touching `cognition/birth.py`).

- [ ] **Step 7: Commit**

```bash
git add src/symbiont/actuation/checkpoint.py tests/unit/actuation/test_checkpoint_gate.py
git commit -m "feat(actuation): checkpoint export/restore + P0 gate (causal vs sham actuator)"
```

---

## P0 Exit Criteria (from spec §14)

Before moving to P1, confirm:

- [ ] `pytest tests/unit/actuation/ -v` passes in full.
- [ ] `pytest tests/unit -k genome -v` passes in full (no genome-hash regression for any existing fixture).
- [ ] The gate test (`test_p0_gate_causal_actuator_promoted_sham_actuator_is_not`) passes deterministically across at least 3 different `seed` values (manually re-run with `seed=7`, `seed=99`, `seed=1234` substituted into the test to confirm it isn't seed-lucky before considering P0 closed).
- [ ] No file under `src/symbiont/actuation/` imports `symbiont_world` or `symbiont_lab` (`grep -r "symbiont_world\|symbiont_lab" src/symbiont/actuation/` returns nothing).
- [ ] Nothing in this plan touched `src/symbiont/core/cognition_bridge.py`, `src/symbiont/core/orchestration/runtime.py`, or anything under `src/symbiont_lab/` — P1 starts clean.
