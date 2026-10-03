# P0 finding — canonical germline is not expressed into Symbiont phenotype

Status: **confirmed, open**

Baseline: `b11be6566931d1377c953124219419a5aaa28bd9`

## Finding

The canonical clean World constructs:

```python
sym_genome = create_standard_genome(organism_id)
germline = GermlineState(birth_expression=dict(sym_genome.loci_values))
sym = Symbiont(organism_id, genome=sym_genome, germline=germline)
```

but `Symbiont.__init__()` currently derives its operative phenotype from
constructor defaults/arguments:

```python
learning_rate = 0.1
exploration_rate = 0.2
SensorimotorModel(learning_rate=learning_rate)
```

The transmitted `SymbiontGenome` and `GermlineState` are retained as
objects but do not currently determine these operative parameters.

Repository search confirms:
- `GermlineState.effective_expression()` is used only by germline tests;
- `capture_acquired_variation()` is defined and unit-tested but is not invoked
  by the canonical embodied Symbiont lifecycle;
- no canonical clean path calls `sym_genome.get(...)` to construct the
  cognitive phenotype.

## Scientific consequence

The present architecture demonstrates **inheritance integrity** (learned state
does not cross birth), but not yet **functional evolutionary inheritance** in
the new embodied runtime.

A locus can mutate/recombine/transmit without changing the actual learning or
exploration behaviour of the child.

Therefore a multigenerational result in this runtime cannot currently be
interpreted as adaptation driven by the new germline.

## Required remediation

1. If a genome is present, derive supported operative cognitive parameters from
   genome expression rather than constructor defaults.
2. Apply legitimate epigenetic regulation through
   `GermlineState.effective_expression()`.
3. Initially wire only traits with a real phenotype in the current minimal
   Symbiont:
   - `learning_rate`
   - `exploration_rate`
4. Do not invent consumers for `initial_concepts`, `soft_node_budget`,
   `soft_edge_budget` or `forgetting_rate` until the corresponding mechanism
   exists in this canonical runtime.
5. Do not fabricate lifetime epigenetic acquisition merely to make
   `capture_acquired_variation()` fire. It may capture only genuine internally
   acquired expression changes.
6. Add adversarial tests proving:
   - genome learning-rate variation changes actual learning phenotype;
   - epigenetic modulation changes expressed phenotype;
   - same seed + different exploration locus changes exploratory trajectory;
   - child learned models remain germinal despite inherited predisposition.

## Separate cleanup

`SymbiontGenome.to_heritable_genome()` /
`from_heritable_genome()` remain explicit legacy compatibility bridges.
They are not on the clean canonical execution path, but conflict with the
project's eventual zero-legacy rule and should be removed after remaining
consumers are audited.
