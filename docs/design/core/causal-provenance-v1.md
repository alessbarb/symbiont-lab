# Causal Provenance v1 — Draft Specification

**Status:** APPROVED to proceed (owner, 2026-09-27) with the §9 proposals as defaults. Contract implemented; adoption step 1 (footprints) done — see §10.
**Origin:** owner requirement (2026-09-27): *every causal claim in Symbiont
must be traceable in symbiont-lab*; review of the footprint registry
(`factorized-effect-representation-v1.md` §13.7).
**Depends on:** Agency Acquisition v1, Executive Outcome Learning v1.1,
Factorized Effect Representation v1.

---

## 1. Problem

Causal traceability exists today only in islands:

- `ActionTrace` (per motor command) and `action_trace()` reconstruct "why did
  the body move" from organism records, but only for the latest attempt and
  only inside the action domain;
- the footprint registry now records its own transitions, versions and pin
  snapshots, but in a vocabulary of its own;
- competences, affordances, intents, reconciliation, commitments,
  controllers, actuation, outcome learning and cognition each keep ids, but
  nothing states which prior entity *caused* each new one.

So a question such as "why did intent I72 exist, and what physical evidence
supports the effect it pursued?" cannot be answered end to end, and bounded
per-domain buffers silently lose the ancestry needed to interpret long-lived
references.

## 2. Goal

One minimal, transversal provenance contract that every domain uses, such
that for any decision the lab can reconstruct:

```text
evidence -> estimate -> footprint version -> dimension -> competence
-> affordance -> admission -> intent -> commitment -> controller -> actuation
-> transition (physical consequence) -> reconciliation -> outcome learning
```

and, for cognition, observation -> representation -> hypothesis -> agenda ->
prediction -> decision.

Timestamps say **when**; provenance says **why**. Both are required.

## 3. Constraints (CLAUDE.md, unchanged)

- Organism checkpoints stay **bounded** and never persist raw sensor
  histories or raw telemetry.
- `symbiont` never imports `symbiont_lab`; observation flows outward only;
  nothing the lab records feeds back into cognition.
- Ground truth stays evaluator-side.
- Live transport changes need their own contract (this spec is that
  contract for provenance events).

Therefore **durable provenance lives in the lab**, and the organism keeps only
what it needs to continue and to keep references interpretable.

## 4. Contract

```python
@dataclass(frozen=True)
class CausalRef:
    kind: str       # "evidence", "atom_estimate", "footprint_version", "dimension",
                    # "competence_version", "affordance", "intent", "commitment",
                    # "controller", "actuation", "transition", "outcome", ...
    id: str         # stable, organism-owned identity (versioned where it evolves)

@dataclass(frozen=True)
class CausalEvent:
    event_id: str                  # hash of (tick, operation, subject, caused_by, produced)
    tick: int
    domain: str                    # "acquisition", "footprint", "competence", "intention", ...
    operation: str                 # "enter", "exit", "version", "admit", "form", "activate",
                                   # "commit", "actuate", "observe", "reconcile", "learn", ...
    subject: CausalRef
    caused_by: tuple[CausalRef, ...]
    produced: tuple[CausalRef, ...]
    rule: str | None               # the named rule/threshold that decided it
    parameters: Mapping[str, float | int | str]  # margins, thresholds, similarity...
```

Rules:

1. **Every state-changing decision emits exactly one event** naming what
   caused it and what it produced. Reads emit nothing.
2. **Ids are stable and correlatable.** Entities that evolve have an entity id
   plus a version (`footprint.<h>@v7`, `competence.<id>@v3`); content
   fingerprints (e.g. `footprint_id(atoms)`) are recorded as attributes, never
   used as the only identity.
3. **Aggregates name their inputs by id, bounded**: an estimate built from
   many facts refers to them by range or by the ids of its contributing units
   (e.g. pulse commitment ids + the passive-window tick range), never by
   copying their values.
4. **Snapshots are explicit.** A pinned/referenced historical state has its
   own kind (`pinned_footprint_snapshot`), never the name of the live entity.
5. **No semantics.** Kinds and operations are structural; no body, world or
   task meaning enters provenance.
6. **Deterministic.** Event ids are pure functions of their content; a
   restored organism emits the same events as the uninterrupted one from the
   restore point (Agency v1 §82.3 exceptions stated explicitly).

## 5. Organism side (bounded)

- Each domain emits `CausalEvent`s into one organism-owned
  `ProvenanceBuffer` (bounded ring, e.g. 8192 events).
- The checkpoint stores a **provenance frontier** instead of the full log:
  the current entity versions, live pins/snapshots and live references (intent,
  commitment, bindings, EOL keys), each with the ids of its immediate causes.
  The frontier is bounded by the number of live entities, not by age.
- Invariant: any reference still live in the organism can be explained from
  the frontier plus the durable journal; eviction from the ring never removes
  the last explanation of a live reference.

## 6. Lab side (durable)

- `symbiont_lab` subscribes to the observation stream and appends every
  `CausalEvent` to an append-only **provenance journal** per organism run
  (compacted by checkpointing: a checkpoint summary + subsequent events).
- A query API reconstructs chains: `explain(ref)`, `ancestors(ref, depth)`,
  `descendants(ref)`, `why(decision)`; the Observatory can render them.
- The journal is apparatus data: it is never read back by the organism.

## 7. Adoption order

1. Footprints (registry transitions, versions, snapshots) — first user, maps
   directly onto the contract.
2. Acquisition: evidence, atom estimates (with pulse/quiet-window ancestry),
   dimensions.
3. Competence grounding, bindings, affordances.
4. Admission, intents, commitments, controllers, actuation, transitions,
   reconciliation.
5. Executive outcome learning.
6. Cognition (observation -> representation -> hypothesis -> agenda ->
   prediction -> decision), in its own follow-up once 1-5 are proven.

Wiring footprints into dimensions/competences (factorized effects §4-§9)
happens at step 3 using this contract, not before.

## 8. Tests (gate)

1. Every state change in an adopted domain emits one event with non-empty
   `caused_by` (except explicit roots: raw evidence).
2. For any live reference, `explain` reaches raw evidence through the frontier
   plus journal, after the ring has wrapped.
3. Continuous vs checkpoint -> restore -> run: same entity ids, version
   sequences, content fingerprints, causal parent ids, event kinds and order,
   pinned snapshot resolution and downstream references.
4. A pinned snapshot referenced before a restore still resolves exactly after
   the entity evolves several versions, and current evidence stays
   independent of it.
5. Organism checkpoint size stays bounded under long runs; no raw values in
   events.
6. Provenance emission adds no more than 5% per-tick overhead.

## 9. Open decisions for the owner

1. Ring size (proposed 8192) and whether the frontier also keeps the last N
   events per live entity.
2. Journal format and location (proposed: JSON lines per run under the run's
   artifact directory, compacted at checkpoints).
3. Whether cognition (step 6) is in scope for v1 or a v2.
4. Whether provenance emission can be disabled for performance studies (it
   must never change behaviour).

## 10. Implementation status

- `symbiont/provenance.py`: `CausalRef`, `CausalEvent` (content-addressed
  ids, scalar-only parameters, bounded causes), `ProvenanceLog` (ring of
  8192, frontier of live references checkpointed instead of the log,
  outward-only subscribers).
- `symbiont_lab/observation/provenance_journal.py`: append-only JSON-lines
  journal with `explain` and `ancestors`; apparatus data, never read back.
- **Step 1, footprints** (`symbiont/actuation/footprint.py`): each changed
  atom estimate emits an `estimate` event caused by its pulse commitments and
  passive-window range; each version change emits a `version` event caused by
  the previous version and those estimates; pins emit a
  `pinned_footprint_snapshot`; eviction emits an `evict` version. The
  frontier retires superseded versions and their estimates, so it stays
  bounded by live references.
- Gates covered by tests: events name their causes down to pulses; the
  frontier keeps only live references; a live pinned snapshot is explained
  from the journal after the ring wraps; a restored organism emits the same
  events and frontier as the uninterrupted one; emission never changes
  behaviour.
- Next: step 2 (acquisition evidence -> dimensions) and step 3 (competence
  grounding on footprints), wired with this contract.

### 10.1 Adoption status (2026-09-27)

| Step | Domain | Events | Status |
| --- | --- | --- | --- |
| 1 | footprints | `estimate` (caused by pulse commitments + passive-window range), `version`, `pin`, `evict` | done |
| 2 | acquisition | footprints refreshed per closed pulse inside `AgencyAcquisition`, which owns the organism-level `ProvenanceLog` | done |
| 3 | competence | `ground` (caused by the footprint versions used; rule `own_footprint` / `footprint_union`), `revise_effect` | done (factorized mode) |
| 4 | intention | `form` (caused by competence and anticipated effect), `satisfied` / `failed` / `rejected` / `interrupted` / `invalidated` (caused by intent and commitment, with recall parameters) | done |
| 5 | outcome learning | `learn` (caused by intent and commitment; class, admission factor, suppression), `lift_suppression` | done |
| — | admission, commitment, controller, actuation, transition | not yet emitted; the intent's commitment id links to the ledger's commitment evidence | pending |
| 6 | cognition | not started (owner decision 3) | pending |

Lab side: `ProvenanceIndex` (summary, find, why, ancestors, reaches) and
`symbiont-lab provenance summary|find|why <journal>`. On the running
Physics3D acceptance journal, `why competence:<id>` already reconstructs
competence -> footprint version -> atom estimates -> pulse commitments and
the passive-window range.
