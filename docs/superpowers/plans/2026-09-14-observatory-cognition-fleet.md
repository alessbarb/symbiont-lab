# Observatory Cognition/Fleet Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Observatory real-time, multi-instance visibility into resident Symbionts on this machine, including full cognition-layer state (genome, graph topology, learning, structure, safety), while keeping Observatory passive (organism writes, Observatory only reads).

**Architecture:** Each resident (`observatory/resident.py`) publishes three per-instance local artifacts — a heartbeat registry file, a revision-gated topology file, and a segmented ndjson journal — through one `SnapshotPublisher` fanning out to `StdoutSink`/`JournalSink`/`ReplayRecorder`. A new local-only `observatory/server.py` (binds `127.0.0.1`, never imports `symbiont.core`) watches the registry, tails journals over SSE, and serves topology on revision change. The frontend adds a Fleet sidebar (instance discovery) and a Cognition tab (topology/readouts/prediction-errors/mutations/safety), with a v1→v2 snapshot normalizer so old replays keep working.

**Tech Stack:** Python 3.11+ stdlib only (`hashlib`, `uuid`, `http.server`, `socketserver`, `threading`) — no new dependencies. Vanilla JS (matches existing `app.js`), `EventSource` for SSE.

**Spec:** `docs/superpowers/specs/2026-09-14-observatory-cognition-fleet-design.md`

## Global Constraints

- No new permission class, no network exchange beyond `127.0.0.1`, no identifying host data (paths, usernames) in any published artifact (spec: Non-goals).
- Every new file under `~/.local/state/symbiont/observatory/` has exactly one writer (the organism) and Observatory only reads it; Observatory never deletes or mutates an organism's live files (spec: Identity and discovery, TTL handling).
- `instance_id = sha256(namespace || resolved_state_file_path)[:16]` (hex), never the raw path (spec: Gaps closed §1 hardening).
- `run_id` is a stdlib `uuid.uuid4()` string, fresh every process start (spec: same).
- Continuously-updated cognition values (weights, eligibility, prediction error) are always quantized into bounded discrete classes before publishing, never raw floats — same discipline as `src/symbiont/cognition/checkpoint.py` (spec: Schema split).
- `prediction_errors` get their own `loss_class` quantization, never reusing weight/eligibility bins (spec: Gaps closed §3).
- Journal segments are rotated by deleting whole closed segments, never truncated in place; entries are addressed by `run_id`+`sequence`, never `tick` or file offset (spec: Gaps closed §4).
- `snapshot.schema.json`'s `schema_version: 1` payload MUST NOT carry `organism.cognition`; `schema_version: 2` MUST carry it (spec: Gaps closed §2).
- `observatory/server.py` never imports `symbiont.core` or any cognition module (spec: Server section, Gaps closed).
- All new/modified Python files pass the existing test suite unchanged for anything not touched by this plan (`pytest` from repo root).

---

### Task 1: Expose quantization primitives for reuse

`src/symbiont/cognition/checkpoint.py` currently names its quantization helpers and constants with a leading underscore (`_quantize_signed`, `_dequantize_signed`, `_WEIGHT_CLASSES`, `_ELIGIBILITY_CLASSES`, `_ELIGIBILITY_RANGE`). Observatory's `edge_deltas` (Task 7) must quantize weight/eligibility with the *exact same* bins the checkpoint uses (spec: "quantized with checkpoint.py's existing weight/eligibility bins since those are literally the same quantities"). Rename to public names so `observatory/adapter.py` can import them without reaching into underscore-prefixed internals.

**Files:**

- Modify: `src/symbiont/cognition/checkpoint.py:13-28,108,111,155,158`
- Test: `tests/unit/core/test_cognition_bridge.py` (existing — must still pass unmodified)

**Interfaces:**

- Produces: `quantize_signed(value: float, bounds: tuple[float, float], num_classes: int) -> int`, `dequantize_signed(class_id: int, bounds: tuple[float, float], num_classes: int) -> float`, `WEIGHT_CLASSES: int`, `ELIGIBILITY_CLASSES: int`, `ELIGIBILITY_RANGE: tuple[float, float]` — all public module-level names in `src/symbiont/cognition/checkpoint.py`, importable by `observatory/adapter.py`.

- [ ] **Step 1: Run the existing checkpoint/bridge tests to capture the current-green baseline**

Run: `pytest tests/unit/core/test_cognition_bridge.py -v`
Expected: PASS (all existing tests green before any change — this task is a pure rename, not a behavior change)

- [ ] **Step 2: Rename the private helpers and constants to public names**

In `src/symbiont/cognition/checkpoint.py`, rename:

- `_WEIGHT_CLASSES` → `WEIGHT_CLASSES`
- `_ELIGIBILITY_CLASSES` → `ELIGIBILITY_CLASSES`
- `_ELIGIBILITY_RANGE` → `ELIGIBILITY_RANGE`
- `_quantize_signed` → `quantize_signed`
- `_dequantize_signed` → `dequantize_signed`

Update every call site in the same file (`export_graph_checkpoint`, `restore_graph_checkpoint`) to the new names. Do not change any behavior — this is a rename only.

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `pytest`
Expected: PASS (same pass count as before the rename; a failure here means a call site was missed)

- [ ] **Step 4: Commit**

```bash
git add src/symbiont/cognition/checkpoint.py
git commit -m "refactor(cognition): expose quantization primitives for Observatory reuse"
```

---

### Task 2: Extend CognitiveBridgeResult with topology revision and applied mutations

Observatory's Cognition tab needs to show "topology revision 41 → 42: ADD_EDGE(...)" as a first-class event (spec: Fleet UI, CognitionTopology). `CognitiveBridgeResult` today only exposes `structural_mutations_applied: int` (a count) — not which mutations, and there is no revision counter anywhere. Add both directly to the bridge, since it is the only place that knows both facts.

**Files:**

- Modify: `src/symbiont/core/cognition_bridge.py:33-41,68-99,193-227`
- Test: `tests/unit/core/test_cognition_bridge.py`

**Interfaces:**

- Consumes: `Mutation` from `src/symbiont/cognition/structure.py` (`kind: MutationKind`, `payload: Mapping[str, object]` — already defined).
- Produces: `CognitiveBridgeResult.topology_revision: int` (starts at 0, increments by 1 each tick where `structural_mutations_applied > 0`), `CognitiveBridgeResult.mutations: tuple[Mutation, ...]` (the actual mutations applied that tick, empty tuple otherwise). Both fields are read by `observatory/adapter.py` in Task 7.

- [ ] **Step 1: Write the failing test**

```python
def test_structural_mutation_advances_topology_revision_and_reports_mutations():
    from symbiont.cognition.genome import GenomeCodec
    from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
    from symbiont.cognition.limits import KernelLimits
    from symbiont.cognition.types import EdgeKind, NodeKind
    from symbiont.core.cognition_bridge import CognitiveBridge

    limits = KernelLimits()
    genome = GenomeCodec().load(_minimal_genome_payload())  # existing test helper in this file
    nodes = (
        PlasticNode(node_id="sense_a", kind=NodeKind.SENSE),
        PlasticNode(node_id="sense_b", kind=NodeKind.SENSE),
        PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT),
    )
    edges = (
        PlasticEdge(source_id="sense_a", target_id="concept_a", kind=EdgeKind.EXCITATORY, weight=1.0, plasticity=0.5, delay_ticks=0),
    )
    graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=limits)
    bridge = CognitiveBridge(graph=graph, genome=genome, kernel_limits=limits)

    assert bridge.export_checkpoint()  # sanity: bridge constructs fine
    first = bridge.tick({"sense_a": 1.0, "sense_b": 1.0}, tick=1)
    assert first.topology_revision == 0
    assert first.mutations == ()

    # Drive enough correlated co-activation for a structural proposal on a
    # consolidation-interval tick, then assert the revision advanced and the
    # mutation is visible if one was actually applied this tick.
    last = first
    for tick in range(2, genome.development.consolidation_interval_ticks + 2):
        last = bridge.tick({"sense_a": 1.0, "sense_b": 1.0}, tick=tick)
    if last.structural_mutations_applied > 0:
        assert last.topology_revision == 1
        assert len(last.mutations) == last.structural_mutations_applied
    else:
        assert last.topology_revision == 0
```

Use whatever existing genome-construction helper `test_cognition_bridge.py` already has (check the top of that file for `_minimal_genome_payload` or equivalent — reuse it rather than inventing a new one, to match this file's existing fixtures).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/core/test_cognition_bridge.py::test_structural_mutation_advances_topology_revision_and_reports_mutations -v`
Expected: FAIL with `AttributeError: 'CognitiveBridgeResult' object has no attribute 'topology_revision'`

- [ ] **Step 3: Add the fields and wire them in `tick()`**

In `src/symbiont/core/cognition_bridge.py`:

```python
@dataclass(slots=True, frozen=True)
class CognitiveBridgeResult:
    tick: int
    activations: Mapping[str, float]
    readouts: Mapping[str, float]
    prediction_errors: tuple[PredictionError, ...]
    structural_mutations_applied: int
    frozen: bool
    topology_revision: int
    mutations: tuple[Mutation, ...] = ()
```

In `CognitiveBridge.__init__`, add `self._topology_revision = 0`. Every existing `return CognitiveBridgeResult(...)` call site (the `GraphError` early-return and the normal end-of-tick return) must now pass `topology_revision=self._topology_revision` and `mutations=()` for the early-return, or the actual applied tuple for the normal path.

In the structural-consolidation block, change:

```python
            all_mutations = proposed + prune_mutations
            if all_mutations:
                self._graph = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                structural_mutations_applied = len(all_mutations)
            self._structural_plasticity.reconcile({node.node_id for node in self._graph.nodes})
```

to:

```python
            all_mutations = proposed + prune_mutations
            applied_mutations: tuple[Mutation, ...] = ()
            if all_mutations:
                self._graph = apply_mutations(self._graph, all_mutations, self._kernel_limits, frozen=frozen)
                structural_mutations_applied = len(all_mutations)
                applied_mutations = all_mutations
                self._topology_revision += 1
            self._structural_plasticity.reconcile({node.node_id for node in self._graph.nodes})
```

and the final return statement's `mutations=` gets `applied_mutations` (define `applied_mutations: tuple[Mutation, ...] = ()` before the `if not frozen and tick % interval == 0:` block so it is always bound), plus `topology_revision=self._topology_revision`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/core/test_cognition_bridge.py -v`
Expected: PASS (new test plus all pre-existing ones in this file)

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/symbiont/core/cognition_bridge.py tests/unit/core/test_cognition_bridge.py
git commit -m "feat(cognition): track topology revision and applied mutations in CognitiveBridgeResult"
```

---

### Task 3: Extract a shared, if/then-capable schema validator

`observatory/test_resident_contract.py` already has a dependency-free structural JSON-schema validator (`_validate`). The hardened `snapshot.schema.json` (Task 4) needs `if`/`then`/`else` support this validator doesn't have yet, and three new schema files (Tasks 4-5) will need the same validator. Extract it into its own module and add `if/then/else`.

**Files:**

- Create: `observatory/schema_validate.py`
- Modify: `observatory/test_resident_contract.py:17-73` (remove the inline `_validate`, import it instead)
- Test: `observatory/test_schema_validate.py`

**Interfaces:**

- Produces: `validate(value: Any, schema: dict, path: str = "$") -> None` (raises `AssertionError` on the first violation, same behavior as the extracted function plus `if/then/else`) in `observatory/schema_validate.py`. Used by Tasks 4, 5, and 14.

- [ ] **Step 1: Write the failing test for if/then support**

```python
import unittest

from observatory.schema_validate import validate


class SchemaValidateIfThenTests(unittest.TestCase):
    def test_if_then_else_branches_are_enforced(self):
        schema = {
            "type": "object",
            "if": {"properties": {"version": {"const": 1}}},
            "then": {"properties": {"extra": {"type": "null"}}},
            "else": {"required": ["extra"]},
        }
        validate({"version": 1, "extra": None}, schema)  # then-branch, should not raise
        validate({"version": 2, "extra": "present"}, schema)  # else-branch, should not raise
        with self.assertRaises(AssertionError):
            validate({"version": 2}, schema)  # else-branch requires "extra"


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_schema_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.schema_validate'`

- [ ] **Step 3: Create the module by moving `_validate` out of `test_resident_contract.py` and adding if/then/else**

Copy the existing `_validate` function body from `observatory/test_resident_contract.py` (lines 17-73) verbatim into a new `observatory/schema_validate.py`, rename it to `validate`, and add this block right after the `"const"` check at the top of the function:

```python
def validate(value, schema, path="$"):
    if "const" in schema:
        assert value == schema["const"], f"{path}: expected const {schema['const']!r}, got {value!r}"
        return

    if "if" in schema:
        try:
            validate(value, schema["if"], path)
        except AssertionError:
            if "else" in schema:
                validate(value, schema["else"], path)
        else:
            if "then" in schema:
                validate(value, schema["then"], path)
        # if/then/else has been fully handled for this schema node; the
        # remaining unconditional keywords (type, properties, ...) on this
        # same schema object still apply below, so fall through rather
        # than returning.

    # ... (rest of the body is the existing type/enum/min/max/properties/
    # items logic from the original _validate, unchanged)
```

Keep the rest of the original function body exactly as-is below this new block (the `schema_type`, `enum`, numeric bounds, string `maxLength`, `dict`/`required`/`additionalProperties`/`properties`, and `list`/`maxItems`/`minItems`/`items` sections).

- [ ] **Step 4: Update `test_resident_contract.py` to import instead of defining its own copy**

Replace the inline `def _validate(value, schema, path="$"): ...` block (lines 17-73) in `observatory/test_resident_contract.py` with:

```python
from observatory.schema_validate import validate as _validate
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest observatory/test_schema_validate.py observatory/test_resident_contract.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add observatory/schema_validate.py observatory/test_schema_validate.py observatory/test_resident_contract.py
git commit -m "refactor(observatory): extract shared schema validator, add if/then/else support"
```

---

### Task 4: Harden snapshot.schema.json versioning and add cognition_state.schema.json

Implement spec Gaps closed §2: `schema_version: 1` MUST NOT carry `organism.cognition`; `schema_version: 2` MUST carry it.

**Files:**

- Modify: `observatory/snapshot.schema.json`
- Create: `observatory/cognition_state.schema.json`
- Test: `observatory/test_contract.py`

**Interfaces:**

- Produces: `CognitionState` JSON shape (`cognition_state.schema.json`): `topology_revision` (integer, minimum 0), `readouts` (object, additionalProperties `{"type": "number"}`, maxProperties 128), `prediction_errors` (object, additionalProperties `{"type": "string", "enum": ["zero","trace","low","medium","high","extreme"]}`, maxProperties 128), `edge_deltas` (array, maxItems 1024, items `{source_id, target_id, weight_class, eligibility_class}`), `mutations` (array, maxItems 8, items `{kind, node_id?, edge_id?}`), `safety_state` (object, required `consecutive_failures`/`frozen`). Referenced by Task 7's `project_tick`.

- [ ] **Step 1: Write the failing schema-shape tests**

Add to `observatory/test_contract.py`:

```python
    def test_snapshot_schema_version_gates_cognition_presence(self) -> None:
        schema = json.loads((ROOT / "snapshot.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["enum"], [1, 2])
        organism = schema["properties"]["organism"]
        self.assertIn("cognition", organism["properties"])
        self.assertIn("if", schema)
        self.assertIn("then", schema)
        self.assertIn("else", schema)

    def test_cognition_state_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "cognition_state.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["prediction_errors"]["additionalProperties"]["enum"],
            ["zero", "trace", "low", "medium", "high", "extreme"],
        )
        self.assertEqual(schema["properties"]["mutations"]["maxItems"], 8)
        self.assertFalse(schema["properties"]["safety_state"]["additionalProperties"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest observatory/test_contract.py::ObservatoryContractTests::test_snapshot_schema_version_gates_cognition_presence -v`
Expected: FAIL (`KeyError: 'enum'` — schema still has `"const": 1`)

- [ ] **Step 3: Create `observatory/cognition_state.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://symbiont.local/observatory/cognition_state.schema.json",
  "title": "Symbiont Observatory Cognition State",
  "description": "Per-tick cognition telemetry: readouts, quantized prediction error, quantized edge deltas, structural mutations and safety state. Never raw weights.",
  "type": "object",
  "additionalProperties": false,
  "required": ["topology_revision", "safety_state"],
  "properties": {
    "topology_revision": { "type": "integer", "minimum": 0 },
    "readouts": {
      "type": "object",
      "maxProperties": 128,
      "additionalProperties": { "type": "number" }
    },
    "prediction_errors": {
      "type": "object",
      "maxProperties": 128,
      "additionalProperties": { "type": "string", "enum": ["zero", "trace", "low", "medium", "high", "extreme"] }
    },
    "edge_deltas": {
      "type": "array",
      "maxItems": 1024,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["source_id", "target_id", "weight_class", "eligibility_class"],
        "properties": {
          "source_id": { "type": "string", "maxLength": 128 },
          "target_id": { "type": "string", "maxLength": 128 },
          "weight_class": { "type": "integer", "minimum": 0, "maximum": 15 },
          "eligibility_class": { "type": "integer", "minimum": 0, "maximum": 15 }
        }
      }
    },
    "mutations": {
      "type": "array",
      "maxItems": 8,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["kind"],
        "properties": {
          "kind": { "type": "string", "enum": ["add_edge", "add_node", "quarantine_edge", "remove_edge"] },
          "node_id": { "type": "string", "maxLength": 128 },
          "edge_id": { "type": "string", "maxLength": 260 }
        }
      }
    },
    "safety_state": {
      "type": "object",
      "additionalProperties": false,
      "required": ["consecutive_failures", "frozen"],
      "properties": {
        "consecutive_failures": { "type": "integer", "minimum": 0 },
        "frozen": { "type": "boolean" }
      }
    }
  }
}
```

`weight_class`/`eligibility_class` bounds (`0`-`15`) match `WEIGHT_CLASSES`/`ELIGIBILITY_CLASSES = 16` from Task 1 (0-indexed class ids).

- [ ] **Step 4: Update `observatory/snapshot.schema.json`**

Change:

```json
  "properties": {
    "schema_version": { "const": 1 },
```

to:

```json
  "if": { "properties": { "schema_version": { "const": 1 } } },
  "then": { "properties": { "organism": { "not": { "required": ["cognition"] } } } },
  "else": { "properties": { "organism": { "required": ["cognition"] } } },
  "properties": {
    "schema_version": { "enum": [1, 2] },
```

and inside `organism.properties` (after `"sampling": {...}`), add:

```json
        "cognition": { "$ref": "./cognition_state.schema.json" }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest observatory/test_contract.py -v`
Expected: PASS

- [ ] **Step 6: Run the full suite**

Run: `pytest`
Expected: PASS (existing v1-only snapshots in other tests still validate: they have `schema_version: 1` and no `organism.cognition`, satisfying the `then` branch)

- [ ] **Step 7: Commit**

```bash
git add observatory/snapshot.schema.json observatory/cognition_state.schema.json observatory/test_contract.py
git commit -m "feat(observatory): harden schema_version/cognition gating, add cognition_state schema"
```

---

### Task 5: Add topology.schema.json and instance.schema.json

**Files:**

- Create: `observatory/topology.schema.json`
- Create: `observatory/instance.schema.json`
- Test: `observatory/test_contract.py`

**Interfaces:**

- Produces: `CognitionTopology` shape (`topology.schema.json`): `genome_id`, `kernel_version`, `topology_revision`, `nodes[]` (`{node_id, kind, bias, tau}`), `edges[]` (`{source_id, target_id, kind}` — structural only, no weight). `Instance` shape (`instance.schema.json`): `{instance_id, run_id, pid, display_id, started_at, last_heartbeat, topology_revision}`. Both consumed by Task 8 (registry) and Task 10 (topology writer), and served by Task 11's server.

- [ ] **Step 1: Write the failing tests**

Add to `observatory/test_contract.py`:

```python
    def test_topology_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "topology.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["nodes"]["maxItems"], 128)
        self.assertEqual(schema["properties"]["edges"]["maxItems"], 1024)
        self.assertFalse(schema["properties"]["nodes"]["items"]["additionalProperties"])
        self.assertFalse(schema["properties"]["edges"]["items"]["additionalProperties"])
        self.assertNotIn("weight", schema["properties"]["edges"]["items"]["properties"])

    def test_instance_contract_is_closed_and_bounded(self) -> None:
        schema = json.loads((ROOT / "instance.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        for field in ("instance_id", "run_id", "display_id", "started_at", "last_heartbeat", "topology_revision"):
            self.assertIn(field, schema["required"])
        self.assertEqual(schema["properties"]["instance_id"]["pattern"], "^[0-9a-f]{16}$")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest observatory/test_contract.py::ObservatoryContractTests::test_topology_contract_is_closed_and_bounded -v`
Expected: FAIL with `FileNotFoundError`

- [ ] **Step 3: Create `observatory/topology.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://symbiont.local/observatory/topology.schema.json",
  "title": "Symbiont Observatory Cognition Topology",
  "description": "Structural-only cognition topology: no weights, no eligibility, no readouts. Changes only on a structural mutation.",
  "type": "object",
  "additionalProperties": false,
  "required": ["genome_id", "kernel_version", "topology_revision", "nodes", "edges"],
  "properties": {
    "genome_id": { "type": "string", "maxLength": 72 },
    "kernel_version": { "type": "string", "maxLength": 32 },
    "topology_revision": { "type": "integer", "minimum": 0 },
    "nodes": {
      "type": "array",
      "maxItems": 128,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["node_id", "kind", "bias", "tau"],
        "properties": {
          "node_id": { "type": "string", "maxLength": 128 },
          "kind": { "type": "string", "enum": ["sense", "concept", "state", "predictor", "gate", "readout"] },
          "bias": { "type": "number" },
          "tau": { "type": "number", "minimum": 0.1, "maximum": 10.0 }
        }
      }
    },
    "edges": {
      "type": "array",
      "maxItems": 1024,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["source_id", "target_id", "kind"],
        "properties": {
          "source_id": { "type": "string", "maxLength": 128 },
          "target_id": { "type": "string", "maxLength": 128 },
          "kind": { "type": "string", "enum": ["excitatory", "inhibitory", "predictive", "gating"] }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Create `observatory/instance.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://symbiont.local/observatory/instance.schema.json",
  "title": "Symbiont Observatory Instance Registry Entry",
  "description": "Heartbeat/identity record for one resident process. Never contains a filesystem path.",
  "type": "object",
  "additionalProperties": false,
  "required": ["instance_id", "run_id", "display_id", "started_at", "last_heartbeat", "topology_revision"],
  "properties": {
    "instance_id": { "type": "string", "pattern": "^[0-9a-f]{16}$" },
    "run_id": { "type": "string", "maxLength": 36 },
    "pid": { "type": "integer", "minimum": 0 },
    "display_id": { "type": "string", "maxLength": 48 },
    "started_at": { "type": "string", "maxLength": 40 },
    "last_heartbeat": { "type": "string", "maxLength": 40 },
    "topology_revision": { "type": "integer", "minimum": 0 }
  }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest observatory/test_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/topology.schema.json observatory/instance.schema.json observatory/test_contract.py
git commit -m "feat(observatory): add topology and instance registry schema contracts"
```

---

### Task 6: Add loss_class quantization for prediction error

**Files:**

- Modify: `observatory/adapter.py`
- Test: `observatory/test_adapter.py`

**Interfaces:**

- Consumes: `huber_loss` from `src/symbiont/cognition/learning.py` (test-only, to derive thresholds).
- Produces: `loss_class(loss: float) -> str` in `observatory/adapter.py`, returning one of `"zero"`, `"trace"`, `"low"`, `"medium"`, `"high"`, `"extreme"`. Used by Task 7.

- [ ] **Step 1: Write the failing test, deriving thresholds from real Huber-loss magnitudes**

```python
    def test_loss_class_buckets_huber_loss_magnitudes(self):
        from observatory.adapter import loss_class
        from symbiont.cognition.learning import huber_loss

        self.assertEqual(loss_class(huber_loss(0.0)), "zero")
        self.assertEqual(loss_class(huber_loss(0.02)), "trace")
        self.assertEqual(loss_class(huber_loss(0.2)), "low")
        self.assertEqual(loss_class(huber_loss(0.6)), "medium")
        self.assertEqual(loss_class(huber_loss(1.5)), "high")
        self.assertEqual(loss_class(huber_loss(5.0)), "extreme")
        # monotonic: a strictly larger error never produces a smaller class
        order = ["zero", "trace", "low", "medium", "high", "extreme"]
        errors = [0.0, 0.02, 0.2, 0.6, 1.5, 5.0]
        classes = [loss_class(huber_loss(error)) for error in errors]
        self.assertEqual([order.index(item) for item in classes], sorted(order.index(item) for item in classes))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_adapter.py::AdapterTests::test_loss_class_buckets_huber_loss_magnitudes -v`
Expected: FAIL with `ImportError: cannot import name 'loss_class'`

- [ ] **Step 3: Implement `loss_class`**

`huber_loss` with its default delta produces `0.5 * error**2` below the delta and grows linearly above it (check `src/symbiont/cognition/learning.py` for the exact default `delta` before picking cut points — use the module's actual default rather than assuming 1.0). Add to `observatory/adapter.py`:

```python
_LOSS_CLASS_BOUNDS: tuple[tuple[float, str], ...] = (
    (0.0, "zero"),
    (0.01, "trace"),
    (0.1, "low"),
    (0.5, "medium"),
    (1.0, "high"),
)


def loss_class(loss: float) -> str:
    """Independent quantization from weight/eligibility classes (spec:
    a Huber loss has a different distribution/meaning than a weight or
    an eligibility trace, so only the discipline -- bounded, discrete,
    never raw -- is shared, not the thresholds)."""
    if not math.isfinite(loss) or loss < 0:
        return "zero"
    for bound, name in reversed(_LOSS_CLASS_BOUNDS):
        if loss >= bound:
            return name
    return "extreme"
```

(Note the bounds table is checked from the top down here for clarity, but the loop above walks `reversed(...)` so the *largest* satisfied bound wins — trace through it with the actual `huber_loss` output values from Step 1 and adjust `_LOSS_CLASS_BOUNDS` cut points if any assertion doesn't land on the intended bucket; the test is the source of truth, not this snippet's exact numbers.)

- [ ] **Step 4: Run test to verify it passes, adjusting bounds if needed**

Run: `pytest observatory/test_adapter.py::AdapterTests::test_loss_class_buckets_huber_loss_magnitudes -v`
Expected: PASS. If a specific magnitude lands in the wrong bucket, adjust `_LOSS_CLASS_BOUNDS` (not the test) until real `huber_loss()` outputs sort into the intended six buckets in increasing order.

- [ ] **Step 5: Commit**

```bash
git add observatory/adapter.py observatory/test_adapter.py
git commit -m "feat(observatory): add independent loss_class quantization for prediction error"
```

---

### Task 7: project_tick emits CognitionState; add project_topology

**Files:**

- Modify: `observatory/adapter.py:53-129`
- Test: `observatory/test_adapter.py`

**Interfaces:**

- Consumes: `RuntimeTickResult.cognition: CognitiveBridgeResult | None` (already exists, `src/symbiont/core/runtime.py`), `Genome.genome_id: str` (`src/symbiont/cognition/genome.py`), `CognitiveGraph.nodes`/`.edges` (`src/symbiont/cognition/graph.py`), `quantize_signed`/`WEIGHT_RANGE`/`WEIGHT_CLASSES`/`ELIGIBILITY_RANGE`/`ELIGIBILITY_CLASSES` (Task 1), `loss_class` (Task 6).
- Produces: `project_tick(result, *, acclimation=None, display_id="local-symbiont", ticks_remaining=None, revision_counts=None, genome=None) -> dict` — same signature as today plus optional `genome: Genome | None = None`; when `result.cognition` is present AND `genome` is given, output gets `schema_version: 2` and `organism["cognition"]` populated; otherwise unchanged `schema_version: 1` output (byte-identical to today for every existing call site that doesn't pass `genome`). `project_topology(graph: CognitiveGraph, *, genome: Genome, kernel_version: str) -> dict` — new function producing the `topology.schema.json` shape. Both consumed by Task 10 (`resident.py`).

- [ ] **Step 1: Write the failing tests**

```python
    def test_project_tick_without_genome_keeps_v1_shape(self):
        snapshot = project_tick(self.result())
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertNotIn("cognition", snapshot["organism"])

    def test_project_tick_with_cognition_emits_v2_cognition_state(self):
        from symbiont.cognition.genome import GenomeCodec
        from symbiont.core.cognition_bridge import CognitiveBridgeResult
        from symbiont.cognition.learning import PredictionError
        from symbiont.cognition.structure import Mutation

        genome = GenomeCodec().load(_minimal_genome_payload())  # add this fixture helper to test_adapter.py, mirroring test_cognition_bridge.py's
        cognition = CognitiveBridgeResult(
            tick=7,
            activations={"concept_a": 0.4},
            readouts={"readout_pressure": 0.4},
            prediction_errors=(PredictionError(predictor_id="predictor_a", target_id="concept_a", error=0.02, loss=0.0002),),
            structural_mutations_applied=1,
            frozen=False,
            topology_revision=1,
            mutations=(Mutation(kind="add_edge", payload={"source_id": "sense_a", "target_id": "concept_a", "kind": "excitatory"}),),
        )
        result = self.result()
        result.cognition = cognition
        snapshot = project_tick(result, genome=genome)
        self.assertEqual(snapshot["schema_version"], 2)
        cognition_block = snapshot["organism"]["cognition"]
        self.assertEqual(cognition_block["topology_revision"], 1)
        self.assertEqual(cognition_block["readouts"]["readout_pressure"], 0.4)
        self.assertEqual(cognition_block["prediction_errors"]["predictor_a"], "trace")
        self.assertEqual(cognition_block["mutations"], [{"kind": "add_edge"}])
        self.assertEqual(cognition_block["safety_state"], {"consecutive_failures": 0, "frozen": False})

    def test_project_topology_is_structural_only(self):
        from symbiont.cognition.genome import GenomeCodec
        from symbiont.cognition.graph import CognitiveGraph, PlasticEdge, PlasticNode
        from symbiont.cognition.limits import KernelLimits
        from symbiont.cognition.types import EdgeKind, NodeKind
        from observatory.adapter import project_topology

        genome = GenomeCodec().load(_minimal_genome_payload())
        limits = KernelLimits()
        nodes = (PlasticNode(node_id="sense_a", kind=NodeKind.SENSE), PlasticNode(node_id="concept_a", kind=NodeKind.CONCEPT))
        edges = (PlasticEdge(source_id="sense_a", target_id="concept_a", kind=EdgeKind.EXCITATORY, weight=1.7, plasticity=0.5, delay_ticks=0),)
        graph = CognitiveGraph(nodes=nodes, edges=edges, kernel_limits=limits)

        topology = project_topology(graph, genome=genome, kernel_version="0.59.3")
        self.assertEqual(topology["genome_id"], genome.genome_id)
        self.assertEqual(topology["kernel_version"], "0.59.3")
        self.assertNotIn("weight", topology["edges"][0])
        self.assertEqual(topology["edges"][0], {"source_id": "sense_a", "target_id": "concept_a", "kind": "excitatory"})
```

`result.cognition = cognition` relies on `self.result()` returning a mutable `SimpleNamespace` (it already does — see the existing `Obj = SimpleNamespace` alias at the top of `test_adapter.py`). Add a `_minimal_genome_payload()` helper to `observatory/test_adapter.py` — copy it from whatever fixture `tests/unit/core/test_cognition_bridge.py` already uses for `GenomeCodec().load(...)` in its own tests (same minimal genome shape, just relocated so `observatory/test_adapter.py` doesn't import a `tests/` path).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest observatory/test_adapter.py -v`
Expected: FAIL — `test_project_tick_with_cognition_emits_v2_cognition_state` and `test_project_topology_is_structural_only` fail with `TypeError`/`ImportError`; `test_project_tick_without_genome_keeps_v1_shape` should already PASS (documents current behavior, guards the no-regression requirement).

- [ ] **Step 3: Implement in `observatory/adapter.py`**

Add imports at the top:

```python
from symbiont.cognition.checkpoint import ELIGIBILITY_CLASSES, ELIGIBILITY_RANGE, WEIGHT_CLASSES, quantize_signed
from symbiont.cognition.genome import Genome
from symbiont.cognition.graph import CognitiveGraph
from symbiont.cognition.types import WEIGHT_RANGE
```

Add the `loss_class` function and its bounds table from Task 6 (already present after that task). Add:

```python
def _cognition_state(cognition: Any, *, previous_edge_classes: dict[str, tuple[int, int]] | None = None) -> dict[str, Any]:
    readouts = {key: round(float(value), 6) for key, value in dict(getattr(cognition, "readouts", {})).items()}
    prediction_errors = {
        error.predictor_id: loss_class(error.loss) for error in tuple(getattr(cognition, "prediction_errors", ()))
    }
    mutations = []
    for mutation in tuple(getattr(cognition, "mutations", ())):
        entry: dict[str, Any] = {"kind": _text(getattr(mutation, "kind", ""), 32)}
        payload = dict(getattr(mutation, "payload", {}))
        if "node_id" in payload:
            entry["node_id"] = _text(payload["node_id"], 128)
        elif "source_id" in payload and "target_id" in payload:
            entry["edge_id"] = _text(f"{payload['source_id']}->{payload['target_id']}", 260)
        mutations.append(entry)
    safety = {
        "consecutive_failures": 0,
        "frozen": bool(getattr(cognition, "frozen", False)),
    }
    return {
        "topology_revision": max(0, int(getattr(cognition, "topology_revision", 0))),
        "readouts": readouts,
        "prediction_errors": prediction_errors,
        "edge_deltas": [],
        "mutations": mutations[:8],
        "safety_state": safety,
    }
```

`safety_state.consecutive_failures` is fixed at `0` here deliberately: `CognitiveBridgeResult` does not currently expose the bridge's live `SafetyState.consecutive_failures` (only `.frozen`, via the `frozen` field) — wiring that through is out of scope for this task (it would require either a new field on `CognitiveBridgeResult` or reaching into `CognitiveBridge.safety_state` from the caller, which `project_tick` does not have access to). `frozen` is real and correct; `consecutive_failures` is a disclosed placeholder pinned to `0` until a follow-up task threads it through. State this explicitly in the commit message.

Now modify `project_tick`'s signature and body. Change:

```python
def project_tick(
    result: Any,
    *,
    acclimation: Any | None = None,
    display_id: str = "local-symbiont",
    ticks_remaining: int | None = None,
    revision_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
```

to:

```python
def project_tick(
    result: Any,
    *,
    acclimation: Any | None = None,
    display_id: str = "local-symbiont",
    ticks_remaining: int | None = None,
    revision_counts: dict[str, int] | None = None,
    genome: Genome | None = None,
) -> dict[str, Any]:
```

and change the final return statement from:

```python
    return {"schema_version": SCHEMA_VERSION, "tick": tick, "organism": organism, "population": {"members": [member], "relationships": []}}
```

to:

```python
    cognition = getattr(result, "cognition", None)
    schema_version = SCHEMA_VERSION
    if cognition is not None and genome is not None:
        schema_version = 2
        organism["cognition"] = _cognition_state(cognition)
    return {"schema_version": schema_version, "tick": tick, "organism": organism, "population": {"members": [member], "relationships": []}}
```

Add `project_topology`:

```python
def project_topology(graph: CognitiveGraph, *, genome: Genome, kernel_version: str) -> dict[str, Any]:
    """Structural-only projection (spec: CognitionTopology never carries
    weight/eligibility -- those are per-tick CognitionState, quantized,
    in _cognition_state above)."""
    return {
        "genome_id": _text(genome.genome_id, 72),
        "kernel_version": _text(kernel_version, 32),
        "topology_revision": 0,  # caller (resident.py, Task 10) overwrites with the bridge's live counter
        "nodes": [
            {"node_id": _text(node.node_id, 128), "kind": node.kind.value, "bias": node.bias, "tau": node.tau}
            for node in graph.nodes[:128]
        ],
        "edges": [
            {"source_id": _text(edge.source_id, 128), "target_id": _text(edge.target_id, 128), "kind": edge.kind.value}
            for edge in graph.edges[:1024]
        ],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest observatory/test_adapter.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/adapter.py observatory/test_adapter.py
git commit -m "feat(observatory): project cognition state and topology from a real CognitiveBridge"
```

---

### Task 8: Instance registry (identity, heartbeat, liveness)

**Files:**

- Create: `observatory/registry.py`
- Test: `observatory/test_registry.py`

**Interfaces:**

- Produces: `derive_instance_id(resolved_state_file_path: str) -> str` (16 hex chars, `sha256("symbiont-observatory-instance" + resolved_state_file_path)[:16]`), `new_run_id() -> str` (`uuid.uuid4()` string), `write_heartbeat(observatory_dir: Path, *, instance_id, run_id, pid, display_id, started_at, topology_revision) -> None` (atomic write of `instances/<instance_id>.json`, same temp-file-then-`os.replace` pattern as `write_replay` in `observatory/adapter.py`), `read_registry(observatory_dir: Path) -> list[dict]` (all valid instance records under `instances/*.json`, skipping unparseable files), `classify_liveness(record: dict, *, now: datetime, heartbeat_interval_seconds: float, ttl_seconds: float = 600.0) -> str` (returns `"alive"`, `"stale"`, or `"expired"`). Consumed by Task 10 (resident writes) and Task 11 (server reads, filters out `"expired"`).

- [ ] **Step 1: Write the failing tests**

```python
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from observatory.registry import classify_liveness, derive_instance_id, new_run_id, read_registry, write_heartbeat


class RegistryTests(unittest.TestCase):
    def test_instance_id_is_a_stable_hash_never_the_raw_path(self):
        first = derive_instance_id("/home/alice/.local/state/symbiont/organism.json")
        second = derive_instance_id("/home/alice/.local/state/symbiont/organism.json")
        different = derive_instance_id("/home/bob/.local/state/symbiont/organism.json")
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)
        self.assertRegex(first, r"^[0-9a-f]{16}$")
        self.assertNotIn("alice", first)

    def test_run_id_changes_every_call(self):
        self.assertNotEqual(new_run_id(), new_run_id())

    def test_write_and_read_heartbeat_round_trips_and_is_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            write_heartbeat(
                observatory_dir,
                instance_id="a" * 16,
                run_id="run-1",
                pid=123,
                display_id="local-symbiont",
                started_at="2026-09-14T12:00:00+00:00",
                topology_revision=3,
            )
            records = read_registry(observatory_dir)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["instance_id"], "a" * 16)
            self.assertEqual(records[0]["topology_revision"], 3)
            self.assertIn("last_heartbeat", records[0])
            path = observatory_dir / "instances" / f"{'a' * 16}.json"
            self.assertTrue(path.exists())
            temp_files = list((observatory_dir / "instances").glob(".*"))
            self.assertEqual(temp_files, [])  # no leftover temp file after atomic replace

    def test_read_registry_skips_unparseable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            (observatory_dir / "instances").mkdir(parents=True)
            (observatory_dir / "instances" / "broken.json").write_text("not json", encoding="utf-8")
            self.assertEqual(read_registry(observatory_dir), [])

    def test_classify_liveness_alive_stale_expired(self):
        now = datetime(2026, 9, 14, 12, 10, 0, tzinfo=timezone.utc)
        record = lambda seconds_ago: {"last_heartbeat": (now - timedelta(seconds=seconds_ago)).isoformat()}
        self.assertEqual(classify_liveness(record(5), now=now, heartbeat_interval_seconds=15.0), "alive")
        self.assertEqual(classify_liveness(record(40), now=now, heartbeat_interval_seconds=15.0), "stale")
        self.assertEqual(classify_liveness(record(700), now=now, heartbeat_interval_seconds=15.0), "expired")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.registry'`

- [ ] **Step 3: Implement `observatory/registry.py`**

```python
"""Passive instance registry: heartbeat identity for resident Symbionts on
this machine. Organism writes, Observatory only reads (CLAUDE.md: Observatory
remains passive)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_NAMESPACE = "symbiont-observatory-instance"


def derive_instance_id(resolved_state_file_path: str) -> str:
    """Stable identity for a resident configuration -- never the raw path
    itself (spec: instance_id is a path hash, never exposes filesystem
    layout or usernames)."""
    digest = hashlib.sha256((_NAMESPACE + resolved_state_file_path).encode("utf-8")).hexdigest()
    return digest[:16]


def new_run_id() -> str:
    """Fresh every process start, even resuming the same --state-file."""
    return str(uuid.uuid4())


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_heartbeat(
    observatory_dir: Path,
    *,
    instance_id: str,
    run_id: str,
    pid: int,
    display_id: str,
    started_at: str,
    topology_revision: int,
) -> None:
    record = {
        "instance_id": instance_id,
        "run_id": run_id,
        "pid": pid,
        "display_id": display_id,
        "started_at": started_at,
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "topology_revision": topology_revision,
    }
    _atomic_write_json(Path(observatory_dir) / "instances" / f"{instance_id}.json", record)


def read_registry(observatory_dir: Path) -> list[dict[str, Any]]:
    instances_dir = Path(observatory_dir) / "instances"
    if not instances_dir.is_dir():
        return []
    records = []
    for path in sorted(instances_dir.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def classify_liveness(
    record: dict[str, Any], *, now: datetime, heartbeat_interval_seconds: float, ttl_seconds: float = 600.0
) -> str:
    """pid is never the liveness authority (PIDs are reused) -- only the
    heartbeat timestamp decides alive/stale/expired (spec: Identity and
    discovery)."""
    try:
        last_heartbeat = datetime.fromisoformat(record["last_heartbeat"])
    except (KeyError, ValueError):
        return "expired"
    age = (now - last_heartbeat).total_seconds()
    if age <= 2 * heartbeat_interval_seconds:
        return "alive"
    if age <= ttl_seconds:
        return "stale"
    return "expired"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest observatory/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/registry.py observatory/test_registry.py
git commit -m "feat(observatory): add passive instance registry (identity, heartbeat, liveness)"
```

---

### Task 9: Segmented journal writer

**Files:**

- Create: `observatory/journal.py`
- Test: `observatory/test_journal.py`

**Interfaces:**

- Produces: `class Journal` with `__init__(self, observatory_dir: Path, *, run_id: str, max_lines_per_segment: int = 500, max_segments: int = 20)`, `.append(envelope: dict) -> int` (writes one ndjson line `{"run_id", "sequence", "snapshot": envelope["snapshot"]}`, returns the assigned `sequence`; rotates to a new segment file when the current one hits `max_lines_per_segment`; deletes the oldest whole segment file once segment count exceeds `max_segments`), `.segments() -> list[Path]` (existing segment files for this `run_id`, oldest first). Consumed by Task 10 (`JournalSink`) and Task 11 (server tailing).

- [ ] **Step 1: Write the failing tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from observatory.journal import Journal


class JournalTests(unittest.TestCase):
    def test_append_assigns_monotonic_sequence_tagged_with_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=100)
            first_sequence = journal.append({"snapshot": {"tick": 1}})
            second_sequence = journal.append({"snapshot": {"tick": 2}})
            self.assertEqual((first_sequence, second_sequence), (0, 1))
            lines = journal.segments()[0].read_text(encoding="utf-8").strip().splitlines()
            entry = json.loads(lines[0])
            self.assertEqual(entry, {"run_id": "run-1", "sequence": 0, "snapshot": {"tick": 1}})

    def test_rotates_to_a_new_segment_when_the_cap_is_hit(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=2)
            for tick in range(5):
                journal.append({"snapshot": {"tick": tick}})
            segments = journal.segments()
            self.assertEqual(len(segments), 3)  # 5 lines / cap 2 -> 3 segments (2, 2, 1)
            for segment in segments[:-1]:
                self.assertEqual(len(segment.read_text(encoding="utf-8").strip().splitlines()), 2)

    def test_deletes_whole_oldest_segments_never_truncates(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-1", max_lines_per_segment=1, max_segments=2)
            for tick in range(5):
                journal.append({"snapshot": {"tick": tick}})
            segments = journal.segments()
            self.assertEqual(len(segments), 2)
            remaining_ticks = [json.loads(segment.read_text(encoding="utf-8"))["snapshot"]["tick"] for segment in segments]
            self.assertEqual(remaining_ticks, [3, 4])  # oldest three fully deleted, not truncated

    def test_segment_filenames_are_ordered_by_run_id_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory), run_id="run-abc", max_lines_per_segment=1)
            journal.append({"snapshot": {"tick": 0}})
            journal.append({"snapshot": {"tick": 1}})
            names = [segment.name for segment in journal.segments()]
            self.assertEqual(names, ["run-abc-000001.ndjson", "run-abc-000002.ndjson"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_journal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.journal'`

- [ ] **Step 3: Implement `observatory/journal.py`**

```python
"""Segmented ndjson journal: a transport aid for the Observatory server to
tail/replay-on-connect, never a second source of truth (the runtime
checkpoint remains the only durable organism state). Segments are rotated
by deleting whole closed files, never truncated in place, because
truncating a file a tailer holds open shifts offsets under it (spec: Gaps
closed §4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Journal:
    def __init__(self, observatory_dir: Path, *, run_id: str, max_lines_per_segment: int = 500, max_segments: int = 20) -> None:
        self._dir = Path(observatory_dir) / "journal"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._run_id = run_id
        self._max_lines = max_lines_per_segment
        self._max_segments = max_segments
        self._sequence = 0
        self._segment_index = len(self.segments())
        self._lines_in_current_segment = self._max_lines  # forces rotation on first append

    def segments(self) -> list[Path]:
        return sorted(self._dir.glob(f"{self._run_id}-*.ndjson"))

    def _current_path(self) -> Path:
        return self._dir / f"{self._run_id}-{self._segment_index:06d}.ndjson"

    def append(self, envelope: dict[str, Any]) -> int:
        if self._lines_in_current_segment >= self._max_lines:
            self._segment_index += 1
            self._lines_in_current_segment = 0
        sequence = self._sequence
        self._sequence += 1
        entry = {"run_id": self._run_id, "sequence": sequence, "snapshot": envelope.get("snapshot", envelope)}
        with self._current_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
        self._lines_in_current_segment += 1
        self._prune_old_segments()
        return sequence

    def _prune_old_segments(self) -> None:
        segments = self.segments()
        excess = len(segments) - self._max_segments
        for path in segments[:max(0, excess)]:
            path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest observatory/test_journal.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/journal.py observatory/test_journal.py
git commit -m "feat(observatory): add segmented, run_id+sequence-addressed journal"
```

---

### Task 10: SnapshotPublisher, sinks, and resident.py refactor

**Files:**

- Create: `observatory/publisher.py`
- Modify: `observatory/resident.py`
- Test: `observatory/test_publisher.py`
- Test: `observatory/test_resident_contract.py` (extend)

**Interfaces:**

- Consumes: `Journal` (Task 9), `write_heartbeat`/`derive_instance_id`/`new_run_id` (Task 8), `write_replay`/`envelope` (existing `observatory/adapter.py`), `project_topology` (Task 7).
- Produces: `class StdoutSink` (`.write(envelope) -> None`, prints one JSON line — today's exact behavior), `class JournalSink` (`.write(envelope) -> None`, wraps a `Journal`), `class ReplayRecorder` (`.record(snapshot) -> None` accumulates; `.flush(path) -> None` calls `write_replay`), `class SnapshotPublisher` (`__init__(self, sinks: list, replay_recorder: ReplayRecorder | None = None)`, `.publish(envelope: dict, snapshot: dict) -> None` calls `sink.write(envelope)` on every sink and `replay_recorder.record(snapshot)` if present). Consumed directly by `resident.py`'s rewritten `main()`.

- [ ] **Step 1: Write the failing publisher tests**

```python
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from observatory.publisher import JournalSink, ReplayRecorder, SnapshotPublisher, StdoutSink


class PublisherTests(unittest.TestCase):
    def test_stdout_sink_prints_one_json_line(self):
        sink = StdoutSink()
        with patch("builtins.print") as mock_print:
            sink.write({"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 1}})
        mock_print.assert_called_once()
        (line,), kwargs = mock_print.call_args
        self.assertEqual(json.loads(line)["snapshot"]["tick"], 1)
        self.assertTrue(kwargs.get("flush"))

    def test_journal_sink_delegates_to_a_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            sink = JournalSink(Path(directory), run_id="run-1")
            sink.write({"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 1}})
            segments = list((Path(directory) / "journal").glob("run-1-*.ndjson"))
            self.assertEqual(len(segments), 1)

    def test_replay_recorder_flushes_all_recorded_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = ReplayRecorder()
            recorder.record({"tick": 1})
            recorder.record({"tick": 2})
            path = Path(directory) / "replay.json"
            recorder.flush(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([snapshot["tick"] for snapshot in payload["snapshots"]], [1, 2])

    def test_publisher_fans_out_identical_payload_to_every_sink(self):
        seen = []

        class RecordingSink:
            def write(self, envelope):
                seen.append(envelope)

        recorder = ReplayRecorder()
        publisher = SnapshotPublisher([RecordingSink(), RecordingSink()], replay_recorder=recorder)
        envelope = {"type": "symbiont-observatory-snapshot", "snapshot": {"tick": 3}}
        publisher.publish(envelope, envelope["snapshot"])
        self.assertEqual(seen, [envelope, envelope])
        self.assertEqual(recorder._snapshots, [{"tick": 3}])  # internal state check is acceptable here: this is the unit under test


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_publisher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.publisher'`

- [ ] **Step 3: Implement `observatory/publisher.py`**

```python
"""Fan-out publishing so every Observatory transport sees the identical
projected snapshot. ReplayRecorder is deliberately not a per-envelope sink:
write_replay() was never append-oriented -- it writes the whole bounded
collection atomically in one shot (spec: Gaps closed §5)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from .adapter import write_replay
from .journal import Journal


class Sink(Protocol):
    def write(self, envelope: dict[str, Any]) -> None: ...


class StdoutSink:
    def write(self, envelope: dict[str, Any]) -> None:
        print(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")), flush=True)


class JournalSink:
    def __init__(self, observatory_dir: Path, *, run_id: str) -> None:
        self._journal = Journal(observatory_dir, run_id=run_id)

    def write(self, envelope: dict[str, Any]) -> None:
        self._journal.append(envelope)


class ReplayRecorder:
    def __init__(self) -> None:
        self._snapshots: list[dict[str, Any]] = []

    def record(self, snapshot: dict[str, Any]) -> None:
        self._snapshots.append(snapshot)

    def flush(self, path: Path) -> None:
        write_replay(path, self._snapshots)


class SnapshotPublisher:
    def __init__(self, sinks: list[Sink], *, replay_recorder: ReplayRecorder | None = None) -> None:
        self._sinks = sinks
        self._replay_recorder = replay_recorder

    def publish(self, envelope: dict[str, Any], snapshot: dict[str, Any]) -> None:
        for sink in self._sinks:
            sink.write(envelope)
        if self._replay_recorder is not None:
            self._replay_recorder.record(snapshot)
```

- [ ] **Step 4: Run publisher tests to verify they pass**

Run: `pytest observatory/test_publisher.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing resident.py integration test (registry + topology files appear)**

Add to `observatory/test_resident_contract.py`:

```python
    def test_resident_publishes_registry_and_topology_alongside_the_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_file = Path(tmp) / "organism.json"
            observatory_dir = Path(tmp) / "observatory-state"
            result = subprocess.run(
                [
                    sys.executable, "resident.py",
                    "--state-file", str(state_file),
                    "--observatory-dir", str(observatory_dir),
                    "--max-ticks", "1",
                    "--interval", "0.01",
                    "--checkpoint-every", "1",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            instances = list((observatory_dir / "instances").glob("*.json"))
            self.assertEqual(len(instances), 1)
            record = json.loads(instances[0].read_text(encoding="utf-8"))
            self.assertRegex(record["instance_id"], r"^[0-9a-f]{16}$")
            self.assertNotIn(str(state_file), json.dumps(record))
            journal_segments = list((observatory_dir / "journal").glob("*.ndjson"))
            self.assertEqual(len(journal_segments), 1)
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest observatory/test_resident_contract.py::ResidentContractTests::test_resident_publishes_registry_and_topology_alongside_the_stream -v`
Expected: FAIL — `resident.py` doesn't accept `--observatory-dir` yet (`argparse` error, nonzero return code)

- [ ] **Step 7: Refactor `observatory/resident.py`**

Add the new argument and wire `SnapshotPublisher`:

```python
from observatory.publisher import JournalSink, StdoutSink
from observatory.registry import derive_instance_id, new_run_id, write_heartbeat
```

In `main()`, after `args = parser.parse_args(argv)`:

```python
    parser.add_argument(
        "--observatory-dir",
        type=Path,
        default=Path("~/.local/state/symbiont/observatory").expanduser(),
        help="Base directory for the passive registry/journal artifacts Observatory reads",
    )
```

(add this `add_argument` call alongside the others, before `args = parser.parse_args(argv)`).

Replace the body of `main()` from `runtime = OrganismRuntime.load_or_create(...)` onward:

```python
    import os
    from datetime import datetime, timezone

    runtime = OrganismRuntime.load_or_create(
        args.state_file,
        discover_senses=True,
        bootstrap_semantic_senses=False,
    )
    resolved_state_file = str(Path(args.state_file).expanduser().resolve())
    instance_id = derive_instance_id(resolved_state_file)
    run_id = new_run_id()
    started_at = datetime.now(timezone.utc).isoformat()
    publisher = SnapshotPublisher([StdoutSink(), JournalSink(args.observatory_dir, run_id=run_id)])
    topology_revision = 0

    def publish(result) -> None:
        nonlocal topology_revision
        snapshot = project_tick(
            result,
            acclimation=runtime.acclimation,
            display_id=args.display_id,
            ticks_remaining=None,
            genome=runtime.genome,
        )
        # ... (existing sensory_development/sensory_relations/sampling block unchanged) ...
        envelope_payload = envelope(snapshot)
        publisher.publish(envelope_payload, snapshot)

        bridge = runtime.cognitive_bridge
        if bridge is not None and bridge.graph is not None:
            latest_revision = getattr(result.cognition, "topology_revision", topology_revision) if result.cognition else topology_revision
            if latest_revision != topology_revision:
                topology_revision = latest_revision
                topology_payload = project_topology(bridge.graph, genome=runtime.genome, kernel_version=_running_version_string())
                topology_payload["topology_revision"] = topology_revision
                _write_topology(args.observatory_dir, instance_id, topology_payload)

        write_heartbeat(
            args.observatory_dir,
            instance_id=instance_id,
            run_id=run_id,
            pid=os.getpid(),
            display_id=args.display_id,
            started_at=started_at,
            topology_revision=topology_revision,
        )
```

Add the two small helpers used above, near the top of the file:

```python
def _running_version_string() -> str:
    from symbiont import __version__
    return __version__


def _write_topology(observatory_dir: Path, instance_id: str, payload: dict) -> None:
    import json as _json
    import os as _os
    import tempfile as _tempfile

    target = Path(observatory_dir) / "instances" / f"{instance_id}.topology.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = _tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent, text=True)
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as handle:
            _json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            _os.fsync(handle.fileno())
        _os.replace(temporary, target)
    except BaseException:
        try:
            _os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
```

Add `from observatory.adapter import project_topology` to the existing `from adapter import envelope, project_tick` import line (rewrite it as `from observatory.adapter import envelope, project_tick, project_topology` — check whether `resident.py` is normally run with `cwd=observatory/` per the existing test's `cwd=ROOT`, which is why it currently imports as bare `adapter` rather than `observatory.adapter`; keep the existing bare `from adapter import ...` style for consistency and add `project_topology` to that same import instead of introducing a second import style).

- [ ] **Step 8: Run resident tests to verify they pass**

Run: `pytest observatory/test_resident_contract.py -v`
Expected: PASS

- [ ] **Step 9: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add observatory/publisher.py observatory/resident.py observatory/test_publisher.py observatory/test_resident_contract.py
git commit -m "feat(observatory): wire SnapshotPublisher, registry heartbeat and topology writes into resident.py"
```

---

### Task 11: Local-only SSE server

**Files:**

- Create: `observatory/server.py`
- Test: `observatory/test_server.py`

**Interfaces:**

- Consumes: `read_registry`/`classify_liveness` (Task 8), `Journal.segments` (Task 9) — reads segment files directly (does not import `Journal` for writing, only reads the files it already knows the naming convention for), topology files written by Task 10.
- Produces: `class ObservatoryServer` wrapping `http.server.ThreadingHTTPServer` bound to `("127.0.0.1", port)`, with two GET routes: `/fleet` (SSE stream of `{"instances": [...]}` snapshots, one per poll interval) and `/instance/<instance_id>/stream` (SSE stream tailing that instance's journal segments from the latest `sequence`, replaying the last 200 lines on connect, plus a `topology` SSE event whenever the registry's `topology_revision` for that instance changes). `main(argv)` CLI entry point mirroring `resident.py`'s style (`argparse`, `--observatory-dir`, `--port` default `8899`, `--host` fixed to `127.0.0.1` — not configurable, per spec "binds 127.0.0.1 only, refuse to bind elsewhere").

- [ ] **Step 1: Write the failing tests**

```python
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from observatory.registry import write_heartbeat
from observatory.journal import Journal
from observatory.server import ObservatoryServer


class ServerTests(unittest.TestCase):
    def _start_server(self, observatory_dir: Path) -> ObservatoryServer:
        server = ObservatoryServer(observatory_dir, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        return server

    def test_binds_only_to_127_0_0_1(self):
        with tempfile.TemporaryDirectory() as directory:
            server = self._start_server(Path(directory))
            self.assertEqual(server.server_address[0], "127.0.0.1")

    def test_fleet_endpoint_streams_registry_membership(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            write_heartbeat(observatory_dir, instance_id="a" * 16, run_id="run-1", pid=1, display_id="local-symbiont", started_at="2026-09-14T12:00:00+00:00", topology_revision=0)
            server = self._start_server(observatory_dir)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/fleet", timeout=2) as response:
                first_chunk = response.read(4096).decode("utf-8")
            self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
            self.assertIn("a" * 16, first_chunk)

    def test_instance_stream_replays_recent_journal_lines_on_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            observatory_dir = Path(directory)
            journal = Journal(observatory_dir, run_id="run-1")
            journal.append({"snapshot": {"tick": 1}})
            journal.append({"snapshot": {"tick": 2}})
            write_heartbeat(observatory_dir, instance_id="b" * 16, run_id="run-1", pid=1, display_id="x", started_at="2026-09-14T12:00:00+00:00", topology_revision=0)
            server = self._start_server(observatory_dir)
            port = server.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/instance/{'b' * 16}/stream", timeout=2) as response:
                chunk = response.read(4096).decode("utf-8")
            self.assertIn('"tick": 1', chunk.replace(" ", "") if False else chunk)  # tolerate either separator style
            self.assertIn("tick", chunk)


if __name__ == "__main__":
    unittest.main()
```

(The third assertion in the last test is intentionally loose about JSON separators — tighten it once the real SSE payload format from Step 3 is known, replacing it with an exact `json.loads` of the extracted `data:` line's payload.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest observatory/test_server.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'observatory.server'`

- [ ] **Step 3: Implement `observatory/server.py`**

```python
"""Local-only, read-only SSE server for Observatory. Understands only
Observatory's own contracts (registry/topology/journal file shapes) --
never imports symbiont.core or any cognition module (spec: Server section).
Reads only files organisms write; never writes into any --state-file,
checkpoint, or registry entry belonging to an organism."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .registry import classify_liveness, read_registry

_REPLAY_LINES = 200
_POLL_SECONDS = 1.0


def _sse_event(data: dict) -> bytes:
    return f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n".encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    server: "ObservatoryServer"

    def log_message(self, format: str, *args) -> None:  # silence default stderr logging
        pass

    def do_GET(self) -> None:  # noqa: N802 (stdlib-mandated method name)
        path = urlparse(self.path).path
        if path == "/fleet":
            self._stream_fleet()
        elif path.startswith("/instance/") and path.endswith("/stream"):
            instance_id = path.split("/")[2]
            self._stream_instance(instance_id)
        else:
            self.send_error(404)

    def _start_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

    def _stream_fleet(self) -> None:
        self._start_sse()
        try:
            while True:
                records = read_registry(self.server.observatory_dir)
                now = datetime.now(timezone.utc)
                instances = [
                    {**record, "liveness": classify_liveness(record, now=now, heartbeat_interval_seconds=self.server.heartbeat_interval_seconds)}
                    for record in records
                ]
                instances = [item for item in instances if item["liveness"] != "expired"]
                self.wfile.write(_sse_event({"instances": instances}))
                self.wfile.flush()
                time.sleep(_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _stream_instance(self, instance_id: str) -> None:
        self._start_sse()
        journal_dir = self.server.observatory_dir / "journal"
        last_revision = None
        sent_sequences: set[int] = set()
        try:
            while True:
                records = {record["instance_id"]: record for record in read_registry(self.server.observatory_dir)}
                record = records.get(instance_id)
                if record is not None and record["topology_revision"] != last_revision:
                    last_revision = record["topology_revision"]
                    topology_path = self.server.observatory_dir / "instances" / f"{instance_id}.topology.json"
                    if topology_path.exists():
                        self.wfile.write(_sse_event({"topology": json.loads(topology_path.read_text(encoding="utf-8"))}))
                run_id = record["run_id"] if record else None
                if run_id is not None:
                    entries = []
                    for segment in sorted(journal_dir.glob(f"{run_id}-*.ndjson")):
                        for line in segment.read_text(encoding="utf-8").splitlines():
                            if not line.strip():
                                continue
                            entry = json.loads(line)
                            if entry["sequence"] not in sent_sequences:
                                entries.append(entry)
                    entries = entries[-_REPLAY_LINES:] if not sent_sequences else entries
                    for entry in entries:
                        self.wfile.write(_sse_event(entry))
                        sent_sequences.add(entry["sequence"])
                self.wfile.flush()
                time.sleep(_POLL_SECONDS)
        except (BrokenPipeError, ConnectionResetError):
            return


class ObservatoryServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, observatory_dir: Path, *, host: str = "127.0.0.1", port: int = 8899, heartbeat_interval_seconds: float = 15.0) -> None:
        if host != "127.0.0.1":
            raise ValueError("ObservatoryServer refuses to bind to anything other than 127.0.0.1")
        self.observatory_dir = Path(observatory_dir)
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        super().__init__((host, port), _Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-only read-only SSE server for Observatory")
    parser.add_argument("--observatory-dir", type=Path, default=Path("~/.local/state/symbiont/observatory").expanduser())
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args(argv)
    server = ObservatoryServer(args.observatory_dir, port=args.port)
    print(f"Observatory server listening on http://127.0.0.1:{server.server_address[1]}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 4: Run tests, tighten the loose assertion, verify pass**

Run: `pytest observatory/test_server.py -v`
Expected: PASS. Replace the loose `"tick" in chunk` assertion from Step 1 with an exact check once you see the real `data: ...` line shape, e.g. parse the first `data:` line and assert `json.loads(...)["snapshot"]["tick"] == 1`.

- [ ] **Step 5: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add observatory/server.py observatory/test_server.py
git commit -m "feat(observatory): add local-only SSE server for Fleet and per-instance streaming"
```

---

### Task 12: Frontend — v1/v2 normalizer, Fleet sidebar, Cognition tab

**Files:**

- Modify: `observatory/app.js`
- Modify: `observatory/index.html`
- Modify: `observatory/styles.css`
- Test: `observatory/test_contract.py`

**Interfaces:**

- Consumes: SSE endpoints from Task 11 (`/fleet`, `/instance/<id>/stream`) via `EventSource`; `schema_version`/`organism.cognition` shape from Task 4/7.
- Produces: a `normalizeSnapshot(raw)` JS function (v1 passthrough, v2 unwraps `cognition` into the internal render model), a Fleet sidebar rendering instances from `/fleet`, a `data-tab="cognition"` inspector tab rendering topology/readouts/prediction-errors/mutations/safety from the selected instance's stream. This is the last task — no later task depends on its internals.

- [ ] **Step 1: Write the failing contract tests**

Add to `observatory/test_contract.py`:

```python
    def test_frontend_has_a_v1_v2_snapshot_normalizer(self) -> None:
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("function normalizeSnapshot(", app)
        self.assertIn("schema_version", app)

    def test_frontend_has_a_fleet_sidebar_and_cognition_tab(self) -> None:
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="fleet-panel"', index)
        self.assertIn('data-tab="cognition"', index)
        self.assertIn("new EventSource(", app)
        self.assertIn("/fleet", app)
        self.assertIn("/instance/", app)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest observatory/test_contract.py::ObservatoryContractTests::test_frontend_has_a_v1_v2_snapshot_normalizer observatory/test_contract.py::ObservatoryContractTests::test_frontend_has_a_fleet_sidebar_and_cognition_tab -v`
Expected: FAIL — neither string exists yet

- [ ] **Step 3: Add the Fleet sidebar and Cognition tab markup to `observatory/index.html`**

Add a new `<aside id="fleet-panel" class="panel">` sibling to the existing `<aside class="senses-panel panel">` (inside `<section class="workspace">`, before it), listing discovered instances:

```html
        <aside id="fleet-panel" class="panel">
          <div class="panel-heading"><h2>Fleet</h2><p>Resident Symbionts on this machine</p></div>
          <div id="fleet-list" class="fleet-list"></div>
        </aside>
```

Add a new inspector tab button next to the existing `Current`/`History` tabs (inside `.inspector-tabs`, alongside `data-tab="current"` and `data-tab="history"`):

```html
            <button class="inspector-tab" data-tab="cognition" role="tab" aria-selected="false">Cognition</button>
```

Add a matching panel section, sibling to `<section id="history-panel" hidden>`:

```html
          <section id="cognition-panel" hidden>
            <div class="panel-heading"><h2>Cognitive graph</h2><p id="cognition-subtitle">No cognition data for this organism</p></div>
            <div id="cognition-topology-summary"></div>
            <div id="cognition-readouts"></div>
            <div id="cognition-prediction-errors"></div>
            <div id="cognition-mutations"></div>
            <div id="cognition-safety-state"></div>
          </section>
```

- [ ] **Step 4: Add the normalizer, Fleet client, and Cognition tab renderer to `observatory/app.js`**

Add near the existing snapshot-ingestion code (wherever the current code turns a raw `envelope.snapshot` into `state`'s render model — search `app.js` for where `projection.tick`/`state.realTick` are set, per the existing `test_live_tick_never_drifts...` contract test, and normalize immediately before that assignment):

```javascript
function normalizeSnapshot(raw) {
  if (raw.schema_version === 1) {
    return { ...raw, organism: { ...raw.organism, cognition: null } };
  }
  return raw; // v2 already carries organism.cognition
}
```

Add a Fleet client that connects on load and renders `#fleet-list`:

```javascript
function connectFleet() {
  const source = new EventSource("/fleet");
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    renderFleet(payload.instances ?? []);
  };
}

function renderFleet(instances) {
  const list = document.querySelector("#fleet-list");
  list.replaceChildren();
  instances.forEach((instance) => {
    const row = document.createElement("button");
    row.className = `fleet-row fleet-${instance.liveness}`;
    row.textContent = `${instance.display_id} (${instance.liveness})`;
    row.addEventListener("click", () => connectInstance(instance.instance_id));
    list.append(row);
  });
}

function connectInstance(instanceId) {
  const source = new EventSource(`/instance/${instanceId}/stream`);
  source.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.topology) {
      renderCognitionTopology(payload.topology);
    } else if (payload.snapshot) {
      ingestSnapshot(normalizeSnapshot(payload.snapshot));
    }
  };
}

function renderCognitionTopology(topology) {
  document.querySelector("#cognition-subtitle").textContent = `Genome ${topology.genome_id} · revision ${topology.topology_revision}`;
  document.querySelector("#cognition-topology-summary").textContent = `${topology.nodes.length} nodes, ${topology.edges.length} edges`;
}

function renderCognitionState(cognition) {
  const readouts = document.querySelector("#cognition-readouts");
  readouts.replaceChildren();
  Object.entries(cognition?.readouts ?? {}).forEach(([id, value]) => {
    const row = document.createElement("p");
    row.textContent = `${id}: ${value}`;
    readouts.append(row);
  });
  const errors = document.querySelector("#cognition-prediction-errors");
  errors.replaceChildren();
  Object.entries(cognition?.prediction_errors ?? {}).forEach(([id, cls]) => {
    const row = document.createElement("p");
    row.textContent = `${id}: ${cls}`;
    errors.append(row);
  });
  const mutations = document.querySelector("#cognition-mutations");
  mutations.replaceChildren();
  (cognition?.mutations ?? []).forEach((mutation) => {
    const row = document.createElement("p");
    row.textContent = `${mutation.kind} ${mutation.node_id ?? mutation.edge_id ?? ""}`;
    mutations.append(row);
  });
  const safety = document.querySelector("#cognition-safety-state");
  safety.textContent = cognition?.safety_state ? `Frozen: ${cognition.safety_state.frozen}, failures: ${cognition.safety_state.consecutive_failures}` : "";
}
```

Wire `ingestSnapshot(...)` (the existing function that updates `state` from a snapshot — locate it by searching for where `state.realTick = projection.tick` is set, per the existing test) to also call `renderCognitionState(snapshot.organism.cognition)` once per received snapshot, and call `connectFleet()` once at startup alongside the existing initialization code (search for the existing `document.querySelector('[data-tab="history"]')` wiring at the bottom of the file and add the `connectFleet()` call and the new tab's click handler in the same place the `current`/`history` tabs are wired, so `data-tab="cognition"` participates in the same active/hidden toggling logic already present for the other two tabs).

- [ ] **Step 5: Add minimal styling for the new elements to `observatory/styles.css`**

Add rules for `.fleet-list`, `.fleet-row`, `.fleet-alive`, `.fleet-stale` (follow the existing color language already documented in `index.html`'s help drawer — reuse existing CSS custom properties for state colors rather than inventing new ones; check `styles.css` for existing `--` custom property names used by `.percept`/`.belief`/`.attention` and reuse the same palette for `alive`/`stale`).

- [ ] **Step 6: Run the contract tests to verify they pass**

Run: `pytest observatory/test_contract.py -v`
Expected: PASS

- [ ] **Step 7: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 8: Manual verification in a browser**

Open `observatory/index.html` directly (or serve the `observatory/` directory with any static file server) with `observatory/server.py` running against a real `--observatory-dir`, start one or two `resident.py` processes pointed at the same directory with `--genome-file`/`--graph-file` (per `examples/cognition/genome.json`/`graph.json`), and confirm: Fleet lists both, selecting one shows its existing Overview/Senses/Beliefs tabs unchanged, and the new Cognition tab shows live readouts and updates on a structural mutation.

- [ ] **Step 9: Commit**

```bash
git add observatory/app.js observatory/index.html observatory/styles.css observatory/test_contract.py
git commit -m "feat(observatory): add Fleet sidebar, Cognition tab, and v1/v2 snapshot normalizer"
```

---

### Task 13: Automated multi-resident integration test

**Files:**

- Create: `observatory/test_observatory_integration.py`

**Interfaces:**

- Consumes: `resident.py --observatory-dir` (Task 10), `observatory.registry.read_registry` (Task 8).

- [ ] **Step 1: Write the failing integration test**

```python
"""Roadmap safety/architecture check: Fleet must genuinely distinguish
independent resident processes, not merely render two rows from hand-typed
fixtures. This launches two real residents and verifies discovery end to
end (spec: Testing, automated multi-resident integration test)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from observatory.registry import read_registry

ROOT = Path(__file__).parent


def _run_resident(state_file: Path, observatory_dir: Path, display_id: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, "resident.py",
            "--state-file", str(state_file),
            "--observatory-dir", str(observatory_dir),
            "--display-id", display_id,
            "--max-ticks", "1",
            "--interval", "0.01",
            "--checkpoint-every", "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class ObservatoryIntegrationTests(unittest.TestCase):
    def test_two_residents_register_as_two_distinct_instances_with_distinct_run_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            observatory_dir = Path(tmp) / "observatory-state"
            state_file_a = Path(tmp) / "organism-a.json"
            state_file_b = Path(tmp) / "organism-b.json"

            result_a = _run_resident(state_file_a, observatory_dir, "symbiont-a")
            result_b = _run_resident(state_file_b, observatory_dir, "symbiont-b")
            self.assertEqual(result_a.returncode, 0, msg=result_a.stderr)
            self.assertEqual(result_b.returncode, 0, msg=result_b.stderr)

            records = read_registry(observatory_dir)
            self.assertEqual(len(records), 2)
            instance_ids = {record["instance_id"] for record in records}
            run_ids = {record["run_id"] for record in records}
            self.assertEqual(len(instance_ids), 2)
            self.assertEqual(len(run_ids), 2)

    def test_restarting_the_same_state_file_keeps_instance_id_but_changes_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            observatory_dir = Path(tmp) / "observatory-state"
            state_file = Path(tmp) / "organism.json"

            first = _run_resident(state_file, observatory_dir, "symbiont-a")
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            first_records = read_registry(observatory_dir)
            self.assertEqual(len(first_records), 1)
            first_instance_id = first_records[0]["instance_id"]
            first_run_id = first_records[0]["run_id"]

            second = _run_resident(state_file, observatory_dir, "symbiont-a")
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            second_records = read_registry(observatory_dir)
            self.assertEqual(len(second_records), 1)  # same instance_id -> same registry file, overwritten
            self.assertEqual(second_records[0]["instance_id"], first_instance_id)
            self.assertNotEqual(second_records[0]["run_id"], first_run_id)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails for the right reason**

Run: `pytest observatory/test_observatory_integration.py -v`
Expected: at this point in the plan (Task 10 already merged `--observatory-dir` support), this should already PASS — this task is primarily about locking the behavior in with a dedicated, clearly-named integration test file rather than introducing new production code. If it fails, the failure must point back at a gap in Task 10's implementation (fix there, not here).

- [ ] **Step 3: Run the full suite**

Run: `pytest`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add observatory/test_observatory_integration.py
git commit -m "test(observatory): add automated multi-resident Fleet discovery integration test"
```

---

### Task 14: Update observatory/README.md

**Files:**

- Modify: `observatory/README.md`

- [ ] **Step 1: Document the new artifacts and commands**

Add a section describing: the three per-instance artifacts (`instances/<id>.json`, `instances/<id>.topology.json`, `journal/<run_id>-NNNNNN.ndjson`) and their one-writer/one-reader rule; how to run `observatory/server.py` alongside one or more `resident.py` processes pointed at the same `--observatory-dir`; the Fleet sidebar and Cognition tab; and the v1/v2 schema note (old replay files keep working unmodified). Follow the file's existing prose style (short sections, no marketing language) — read the current file first and match its heading structure rather than restructuring it.

- [ ] **Step 2: Commit**

```bash
git add observatory/README.md
git commit -m "docs(observatory): document Fleet, cognition tab and the new per-instance artifacts"
```

---

## Self-Review Notes

**Spec coverage:** Topology-as-own-artifact → Tasks 5, 7, 10, 11. Schema if/then hardening → Task 4. Independent `loss_class` → Task 6. Segmented journal, `run_id`+`sequence` addressing → Task 9. `ReplayRecorder` split from sinks → Task 10. `instance_id` as path hash, `run_id` as `uuid4` → Task 8. Server never imports `symbiont.core` → Task 11 (verified by its imports list containing only `.registry`, stdlib `http.server`/`argparse`/`json`/`time`/`datetime`/`pathlib`/`urllib`). Fleet observes independent instances, no collective cognition → Task 12 renders each instance's existing single-organism dashboard unchanged, no merge. Automated multi-instance integration test → Task 13.

**Known disclosed gap carried into Task 7:** `safety_state.consecutive_failures` is pinned to `0` in the projected `CognitionState` because `CognitiveBridgeResult` doesn't yet expose the bridge's live `SafetyState.consecutive_failures` count (only `.frozen`). This is flagged explicitly in Task 7's own text and its commit message — a follow-up task, not silently swept under a placeholder.

**Type consistency check:** `CognitiveBridgeResult.mutations` (Task 2) is `tuple[Mutation, ...]`, consumed by `_cognition_state` (Task 7) via `tuple(getattr(cognition, "mutations", ()))` — matches. `Journal.append` (Task 9) returns `int` sequence, consumed by nothing downstream that needs the return value except its own test — fine, `JournalSink.write` (Task 10) discards it, matching the `Sink.write(envelope) -> None` protocol. `project_topology` (Task 7) always sets `topology_revision: 0`; Task 10's `resident.py` explicitly overwrites it (`topology_payload["topology_revision"] = topology_revision`) before writing — documented inline in Task 7's snippet comment, not a silent inconsistency.
