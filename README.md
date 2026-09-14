# Symbiont Lab

A **safe, simulation-only** research prototype and scientific laboratory for distributed defensive intelligence. Every host, pathogen, reporter, measurement and counterfactual is synthetic; the project deliberately has no propagation, persistence, network scanning, OS modification, stealth/evasion, exploitation or access to real user data.

## Architecture: Two Decoupled Packages

Symbiont Lab is structured as an epistemologically decoupled monorepo:

* **`symbiont`** (Research Subject):
  * `core/`: Agent cognition (`agent.py`), host model (`model.py`), bounded memory (`memory.py`), revisable local beliefs (`beliefs.py`), collective consensus (`collective.py`), reasoning (`reasoning.py`), curiosity planner (`curiosity.py`), metacognition (`metacognition.py`), and heritage (`heritage.py`).
  * `environment/`: Synthetic ecology (`world.py`), regime shifts (`regimes.py`), and deterministic orthogonal RNG streams (`rng.py`).
  * `simulation/`: Engine orchestrator (`engine.py`), sensory vs evaluator events (`events.py`), evaluation counts (`evaluation.py`), mathematical metrics (`metrics.py`), result structures (`result.py`), and streaming snapshots (`snapshots.py`).

* **`symbiont_lab`** (Scientific Apparatus):
  * `experiments/`: Declarative experiment specs, loader (`loader.py`), execution manifests (`manifest.py`), protocol registry (`registry.py`), and unified runner (`runner.py`).
  * `studies/`: Research protocols organized by domain: `attention/`, `evidence/`, `heritage/`, and `campaigns/`, backed by `common/` statistical and digest utilities.
  * `archive/`: Append-only research memory for runs, studies, and lineages (`.symbiont/`).
  * `cli/`: Unified command-line interface (`symbiont-lab`).
  * `dashboard/`: Localhost-only passive visualization.

### Organism milestone: v0.28 revisable local beliefs

Each agent now maintains a bounded, private belief model for recurring synthetic
patterns. Beliefs accumulate evidence, expose uncertainty, register contradiction,
can reverse direction, and influence later assessments only in proportion to their
certainty. The model never receives evaluator labels or laboratory results.

### Organism milestone: v0.29 host discovery protocol

Symbiont can now discover the safe capabilities offered by a consenting local host
through an OS-agnostic manifest. Platform-specific providers sit outside cognition,
fail independently, and are constrained by a default policy that permits only local,
read-only discovery. The built-in provider reports only Python runtime, logical CPU
and monotonic-clock capabilities; it collects no hostname, username, address, path
or user content.

### Organism milestone: v0.30 sensor reading contract

Symbiont now has a typed contract for a single sample from a discovered capability:
`SensorReading` carries a unit, a monotonic timestamp, a quality
(nominal/degraded/stale/unavailable), and a privacy class that is always aggregate
or non-identifying — there is no identifying option in the type. A reading is only
trustworthy once checked against the v0.29 discovery manifest
(`reading_matches_manifest`); this milestone defines the shape of a reading only —
no real sensor samples a host yet (that starts at v0.31).

### Organism milestone: v0.31 cross-platform resource provider

Symbiont can now sample real, read-only readings from a consenting local host:
CPU load (as a load-per-logical-core ratio) and disk usage (as a percent), using
only Python's standard library — this project keeps zero runtime dependencies.
Memory, thermal and power are intentionally reported as `unavailable` rather than
approximated, since stdlib alone has no portable, safe way to read them.
`HostSampler` only ever returns a reading for a capability/source pair v0.29's
discovery already accepted (`reading_matches_manifest` as a hard gate), and one
provider failing cannot blind the others — the same isolation guarantee v0.29's
`HostDiscovery` already gives.

### Organism milestone: v0.32 sensor lifecycle

Symbiont can now run bounded, repeated discovery-and-sampling ticks through
`HostLifecycle`: hot capability changes are observable across ticks
(`capability_changes()`), a reading provider that keeps failing is skipped for a
growing number of ticks instead of being retried every single one — and is
retried at full frequency again the moment it next succeeds — and history never
grows past a fixed `history_limit`. Nothing here changes what v0.29-v0.31 already
discover or sample; this only governs how repeatedly and resiliently they run.

### Organism milestone: v0.33 acclimation — Milestone A complete

Symbiont can now learn an initial descriptive baseline (mean, stdev, sample count)
per capability from real readings via `HostAcclimation`, closing
[Milestone A — Safe real perception](https://github.com/alessbarb/symbiont-lab/issues/32)
(v0.30-v0.33). Threat classification is withheld by construction, not just by
convention: `CapabilityBaseline`'s only public fields are `count`/`mean`/`variance`/
`stdev` — there is no deviation, novelty or anomaly signal anywhere in this
milestone's surface. `baseline()` itself returns `None` until enough samples exist,
so even a two-point average is never treated as something to act on. Distinguishing
novelty from gradual change is explicitly [Milestone B](https://github.com/alessbarb/symbiont-lab/issues/34)'s
job (v0.36), not this one's.

### Organism milestone: v0.34 percept synthesis — Milestone B begins

Symbiont can now turn a real sensor reading into a `Percept`: a platform-neutral
perception identified only by a stable semantic name (`system_load`,
`storage_pressure`), never by the `capability_id`/`source` tokens discovery and
sampling use internally. This is the first step of
[Milestone B — Adaptive host model](https://github.com/alessbarb/symbiont-lab/issues/34)
(v0.34-v0.37), and it exists specifically so that a future cognition component
can consume percepts without ever importing a platform provider — the milestone's
own exit gate. A capability with no entry in the percept-name mapping is skipped
rather than guessed at, so an unrecognized signal never reaches cognition under
an invented name.

### Organism milestone: v0.35 context and rhythms

Symbiont can now learn a separate descriptive baseline per (percept, time-of-day)
pair via `RhythmModel` — e.g. "system_load tends to run lower at night than in
the afternoon" — plus which percepts co-occur within a given time bucket. Time of
day is quantized into four coarse, cyclical buckets (night/morning/afternoon/
evening) by `time_bucket_for_hour`; the actual hour is read only to compute the
bucket and is never stored or exposed, so nothing here can reveal a calendar date
or exact schedule — only a recurring phase of day. Reuses v0.33's bounded,
O(1)-per-context statistics machinery, and keeps the same guarantee: a baseline's
only public fields are `count`/`mean`/`variance`/`stdev`, no deviation or anomaly
signal anywhere.

### Organism milestone: v0.36 drift-aware beliefs

Symbiont can now separate three ways a percept can relate to its own baseline:
a one-off `isolated` outlier, an in-progress but unconfirmed `gradual` shift,
and a `regime_shift` confirmed after enough consecutive deviations in the same
direction. `DriftAwareBaseline` buffers a candidate run and only commits it to
the baseline once confirmed — discarding it if the run breaks first — so a
single spike, or a revert back to normal after one, never contaminates the
baseline (an earlier continuously-tracking design was tried and rejected for
exactly this failure mode; see the class docstring for the full account).
Known limitation: this detects a sustained *step*, not slow creep — a value
drifting by a tiny increment every tick never crosses the deviation threshold
on any single observation, so true gradual creep is out of scope for this
release. `DriftObservation` keeps the same discipline as every other host
module: it exposes only a classification label and a z-score, never a threat
or security verdict.

### Organism milestone: v0.37 safe checkpoints

Symbiont can now export and re-import the abstract beliefs learned by
v0.33/v0.35/v0.36 (acclimation baselines, per-time-bucket rhythms, drift
baselines) as a single schema-versioned JSON document, via
`export_checkpoint`/`import_checkpoint`. A checkpoint carries only what
those modules already commit to exposing — count/mean/variance per
capability, context or percept — never a raw reading, a capability detail
or a timestamp; `import_checkpoint` refuses anything not written by the
current schema version outright rather than guessing at a migration. A
drift baseline's pending, unconfirmed streak buffer (raw recent values) is
deliberately never exported — a restored drift baseline always resumes
with a clean slate for any in-progress candidate shift, only the already-
committed baseline carries over. This completes Milestone B (#34): restarts
can now restore only safe abstract state, never raw telemetry.

### Organism milestone: v0.38 live attention budget

Symbiont's cognition (`symbiont.core`) now depends on `symbiont.host` for the
first time: `attend_to_host` allocates a hard, bounded attention budget across
a host's known capabilities via `AttentionBudget`, weighted by
`uncertainty_from_baseline` — an unacclimated capability always outranks an
established one; among established ones, higher coefficient-of-variation
(more relatively-uncertain) wins. Selection is a greedy uncertainty-per-cost
heuristic, not an exact knapsack solve, with deterministic name tie-breaks.
Same discipline as `docs/adr/ADR-0003-attention-is-not-classification.md`:
this is a resource-allocation mechanism, not a threat or classification
judgment — `AttentionAllocation` exposes only `name`/`uncertainty`/`cost`.
Begins Milestone C (#33); "the organism can state why a pattern is uncertain"
now has a number attached to it, though the full inspectable narrative is
v0.41's job, not this release's.

### Organism milestone: v0.39 read-only second look

`SecondLookSession` lets the organism temporarily sample one already-
discovered capability at higher resolution — e.g. the capability v0.38's
attention allocation ranked most uncertain — for a bounded number of ticks.
Three properties hold by construction, not caller discipline: **authorized**
(the constructor rejects any capability id the host's own manifest doesn't
already report as available — it can request a closer look, never a new
kind of measurement), **read-only** (every tick delegates to `HostSampler`,
which never writes), and **cancellable** (`cancel()` ends a session early;
`is_active` reflects both the cancellation and the `max_ticks` bound).
Continues Milestone C (#33).

### Organism milestone: v0.40 evidence revision

`EvidenceRevisionLedger` folds a batch of new evidence (e.g. a v0.39 second
look) into an existing acclimation baseline via `HostAcclimation.observe`,
the same way any other reading would be — a conflicting batch is never held
back or discarded, since a belief should still move toward what was
actually observed. What "preserving contradiction and dissent" adds is
narrower: when the evidence's mean is `conflict_z` or more standard
deviations from the prior baseline, a `DissentRecord` is appended to a
bounded, inspectable ledger (`dissent_history`) — the fact that a revision
was contested is kept, not smoothed away as if the evidence had agreed all
along. A zero-stdev prior is never flagged (no basis to compute a z-score
from). `DissentRecord` exposes only statistical fields, the same
classification-free discipline as everything else here. Continues
Milestone C (#33); v0.41 (organism narrative) remains.

### Organism milestone: v0.41 organism narrative — Milestone C complete

`narrate_host`/`narrate_capability` are the capstone of Milestone C: for
each capability, they gather v0.33's baseline, v0.38's `AttentionAllocation`
and v0.40's evidence count/`DissentRecord` into one `NarrativeEntry` with a
plain-language `summary` — e.g. *"compute.logical_cpu is familiar, with a
relative uncertainty of 0.000; it received attention this tick, 3 new
reading(s) were gathered as evidence."* An unacclimated capability is
reported `unfamiliar` with infinite uncertainty rather than omitted. Every
field is already something those three earlier releases commit to exposing
— this only composes them; `NarrativeEntry` carries no raw reading and no
threat or classification verdict (ADR-0003 applies here too). This directly
answers the gap flagged when Milestone B closed ("the organism can state
why a pattern is familiar, novel or uncertain") — it now can, per capability,
in one inspectable object.

**Milestone C (#33, v0.38–v0.41) is complete.**

### Organism milestone: v0.42 knowledge capsules

`create_capsule`/`verify_capsule` (`symbiont.core.capsule`) wrap an abstract
knowledge payload — e.g. a v0.37 `export_checkpoint` document — into a
`KnowledgeCapsule`: signed with Ed25519 (the project's first external
dependency, `cryptography`), tamper-evident, and identity-minimized by
construction. A `CapsuleKeyPair`'s public key is freshly generated random
bytes with no relationship to hostname, user or any other real host
identity — it lets a recipient recognize "the same signer as before" and
detect forgery/tampering, nothing more; rotating identity is just
generating a new keypair. `verify_capsule` never raises on malformed or
forged input — untrusted external data always returns `True`/`False`, never
an exception. This is **offline exchange only**: nothing here does network
I/O, moves bytes between machines, or discovers a peer — that is v0.53's
job (Milestone E), explicitly gated on its own architectural/safety decision
by the roadmap's decision gates, precisely so the data contract (this
release) gets reviewed before transport exists. Wires `symbiont-lab capsule create`/
`capsule verify`. Shipped under the original Milestone D — Cooperative species
(#35); a 2026-09-13 restructure closed #35 and split its remainder into
[Milestone D — Operational embodiment (#55)](https://github.com/alessbarb/symbiont-lab/issues/55)
(inserted first) and
[Milestone E — Cooperative species (#56)](https://github.com/alessbarb/symbiont-lab/issues/56)
— see `docs/roadmap.md` for the full rationale.

**Design note:** the roadmap line only says "signed, identity-minimized" —
it does not mandate a cryptographic scheme. A hand-rolled signature
primitive was considered and rejected: asymmetric cryptography is one of
the most reliably disastrous things to reimplement from scratch (invalid-
curve attacks, nonce reuse, non-constant-time comparisons), and Python
offers no reliable constant-time guarantees for such code. Ed25519 via the
audited `cryptography` package was chosen deliberately, with the
project-owner's explicit sign-off, over both hand-rolled crypto and a
weaker symmetric-HMAC scheme (which cannot give the non-repudiable,
per-source identity that v0.43's contextual trust and v0.54's Sybil/replay
defenses will need).

### Organism milestone: v0.43 contextual source trust

`SourceTrustModel` (`symbiont.core.trust`) learns a per-(capsule signer,
pattern family) reliability score from repeated agreement between a
capsule's claims and this organism's own local beliefs. `agreement_score`
compares a capsule-claimed capability mean against this host's own
`CapabilityBaseline` as a smooth `(0, 1]` value (1.0 at a perfect match,
decaying with distance) — returning `None`, not a manufactured number, when
there's no local basis to compare against yet. `observe_capsule_trust`
verifies the capsule itself before trusting anything in it (never relies on
the caller having already checked), then feeds one agreement score per
shared capability into the model.

Deliberately narrow scope: this is **local and per-source only** — it never
aggregates across multiple sources or treats agreement-by-many as truth.
That composition, done without treating a majority as truth, is Milestone
E's job (`docs/roadmap.md`) and is kept structurally separate here so it
can't be silently reintroduced by accident. `TrustSnapshot` exposes only
count/mean/variance — a running average of an agreement signal, never a
trust/distrust verdict (ADR-0003 applies here too). Wires
`symbiont-lab capsule ingest --ticks N`.

**Known limitation, flagged 2026-09-13:** `agreement_score` measures
*agrees with this host's own local baseline*, which is compatibility, not
reliability — a genuinely different-but-correct environment is penalized,
and a source that mimics local expectations is rewarded regardless of
whether it is actually right. This is an echo-chamber risk in the shipped
design, not a hypothetical one. [Milestone E's](https://github.com/alessbarb/symbiont-lab/issues/56)
v0.51 ("Evidence-aware trust") must supersede this model — separating
ecological compatibility, historical consistency, evidence quality,
freshness, source independence, and cryptographic vs. epistemic trust —
before any collective-revision work (v0.52) is allowed to build on it
again.

### Organism milestone: v0.44 organism runtime — Milestone D begins

`OrganismRuntime` (`symbiont.core.runtime`) is the first release of
[Milestone D — Operational embodiment](https://github.com/alessbarb/symbiont-lab/issues/55):
one continuous cognitive cycle — discover → observe → acclimate → perceive
→ track drift → attend → investigate → revise → explain — replacing the
one-shot CLI verbs v0.30–v0.43 shipped as separate, disconnected commands.
`tick()` runs the cycle once and returns a full `RuntimeTickResult`;
`run(n)` repeats it; `checkpoint()` exports the accumulated state via
v0.37's format. It invents no new sensing, scoring or trust logic — every
step delegates to the exact primitive that release already built and
tested (`HostLifecycle`, `HostAcclimation`, `synthesize_percepts`,
`DriftAwareBaseline`, `attend_to_host`, `SecondLookSession`,
`EvidenceRevisionLedger`, `narrate_host`). Investigation each tick is
bounded to the single highest-attention capability, and only if that
capability is still available in that tick's own manifest — the same
authorization check v0.39 already enforces, not a new one. Resource and
consent governance (how often the organism may run, within what budget) is
deliberately out of scope here — that is v0.45's job; this release only
proves the cycle itself closes and repeats correctly. Wires
`symbiont-lab organism run --ticks N --attention-budget B --investigate-ticks M`.

### Organism milestone: v0.45 consent and resource governor

`GovernedOrganism` (`symbiont.core.governor`) wraps v0.44's runtime with
explicit, continuously-checked consent and a bounded resource budget.
Consent is a live toggle, not a construction-time flag — `revoke()` takes
effect on the very next `tick()`, the same discipline CLAUDE.md requires
for individual samples ("consent is checked before every sample, not just
once at startup"), applied one level up to the whole cognitive cycle.
Frequency is bounded by `min_seconds_between_ticks`: a tick attempted too
soon is refused outright, never delayed, queued or silently throttled —
this class never sleeps or spawns a background loop, so it introduces no
durable background execution. Total resource use is bounded by `max_ticks`;
once reached, every further tick is refused. Capability-level permission
(which senses are allowed at all) is not reinvented here — it already
exists as `DiscoveryPolicy`, passed to the wrapped `OrganismRuntime`.
`symbiont-lab organism run` now reports `ticks_run`/`ticks_remaining`/
`is_consented`/`stopped_early` and stops gracefully, returning whatever
ticks it completed, the moment consent, rate or budget is exceeded — see
`--min-seconds-between-ticks`/`--max-ticks`. Continues Milestone D (#55).

### Organism milestone: v0.46 durable organism state

Checkpoints (v0.37) gain three things: **atomic disk persistence**
(`save_checkpoint_atomic`/`load_checkpoint_file` — write to a temp file in
the same directory, fsync, then `os.replace` into place, so a crash or
power loss mid-write can only ever leave the temp file behind, never a
half-written state file), a **schema migration chain** (`CHECKPOINT_SCHEMA_VERSION`
is now 2, adding an optional `saved_at_tick` field; an older payload is
migrated forward automatically rather than rejected, and only a version
with no registered migration path — or one newer than this code
understands — is refused), and `OrganismRuntime.save`/`.from_checkpoint`/
`.load_or_create` give the v0.44 runtime itself durable, crash/restart-safe
state: `load_or_create(path)` resumes exactly where a prior run left off if
`path` exists, or starts fresh if it doesn't — the same function handles
both cases correctly. `symbiont-lab organism run --state-file PATH` wires
this in: omit it for an ephemeral, in-process-only run exactly like before.
Continues Milestone D (#55): v0.47 (cross-platform proof), v0.48 (defensive
advisory — decision-gated) and v0.49 (real-host evaluation) remain.

### Organism milestone: v0.47 cross-platform proof

Milestone A's "same cognitive input schema across supported platforms" exit
gate (#32) was asserted from code inspection, never actually run — CI
executed on `ubuntu-latest` only. This release adds real cross-platform CI
execution: a `host-cross-platform` job runs the host/checkpoint/runtime
test suite plus `host discover`/`host sample`/`organism run` on
`ubuntu-latest`, `windows-latest` and `macos-latest`, and a
`host-constrained-environment` job runs the host test suite inside a
`python:3.12-alpine` container (musl libc, minimal base image) to exercise
a genuinely degraded environment rather than another full desktop OS.

**What's actually verified vs. pending, stated honestly:** the Alpine/musl
job was run locally via Docker as part of this release — 127 host tests
pass, `discover`/`sample` work, and `os.getloadavg` works fine even under
musl (no degradation found there, a real finding, not an assumption).
Windows and macOS execution could **not** be verified locally — there is no
way to run those OS images from this development environment — so this
release adds the CI configuration and documents the plan; the actual
Windows/macOS results only exist once GitHub Actions runs this workflow for
real. Closing #32's caveat requires seeing those checks pass, not just
adding them — that will be updated once CI (currently blocked by an
unrelated GitHub Actions billing issue this session hit) actually executes
this job and its results can be observed.

### Organism milestone: v0.48 defensive advisory

`DefensiveAdvisor` (`symbiont.core.advisory`) is Milestone D's
decision-gated release: a consultative, explainable recommendation that a
human review one capability — never autonomous action, never irreversible,
always requiring human review. It was implemented only after the
project owner explicitly resolved seven design questions up front:

* **Delivery**: CLI-only pull (`symbiont-lab organism run --advisory-consent`), never push (no email/webhook/notification); also a plain Python class like everything else here, not CLI-exclusive.
* **Trigger**: a fixed rule composition of existing signals, never a synthesized risk score. A `DriftKind.REGIME_SHIFT` ("persistent deviation") is the anchor and never fires alone; it needs at least one corroborating signal — elevated relative uncertainty on the same capability ("unusual activity") or an active `DissentRecord` from that tick's investigation on that same capability ("contradictory evidence") — matching the roadmap's own example phrasing exactly.
* **Vocabulary**: a fixed summary template, and `_BANNED_WORDS` (threat/malicious/attack/infected/malware/virus/hack/compromise) is enforced by a dedicated test — this is a recommendation to look, described in engineering language, never a verdict in security language.
* **Scope**: escalation-only — "review this," never a suggested remediation. Left open to revisit, not foreclosed by the type system.
* **Rate limiting**: its own independent throttle (`min_seconds_between_advisories`) — a rate-limited tick returns no advisories rather than raising, since silence is a normal per-tick outcome here, unlike v0.45's `GovernedOrganism` where a refused tick is an error to handle.
* **Persistence**: `append_advisories_to_log`/`load_advisory_log` — a durable, atomically-written log (reusing v0.46's atomic-write primitive), append-only, a no-op for an empty tick.
* **Consent**: fully independent from v0.45's sensing consent — `--advisory-consent` is a separate flag; consenting to be perceived does not imply consenting to receive recommendations, and vice versa. Without it, `DefensiveAdvisor.evaluate` raises `AdvisoryConsentRequiredError` rather than silently no-op'ing.

Continues Milestone D (#55): only v0.49 (real-host evaluation) remains.

### Organism milestone: v0.49 real-host evaluation — Milestone D complete

`symbiont_lab.evaluation.advisory_evaluation` measures v0.48's fired
advisories against a real human operator's own judgment — never against
synthetic ground truth, and never fed back into the organism. This is
laboratory apparatus, not organism cognition — exactly the roadmap's own
rule ("laboratory work is added only when a new organism capability needs
a new measurement instrument") applied to a real host for the first time.
`record_operator_judgment` refuses to label an advisory that never
actually fired; `evaluate_advisories` reports `usefulness_rate`/
`false_alarm_rate`/`label_coverage` (each `None`, not a manufactured
number, until something has actually been labeled); `evaluate_advisories_over_time`
buckets by tick windows so a *trend* is visible rather than one lifetime
number, omitting windows with nothing fired rather than reporting a fake
zero. The one-way flow — advisory log → operator label → evaluation
summary, never back into `DefensiveAdvisor`'s trigger logic — is enforced
structurally by the same AST-based boundary test that has always verified
`symbiont` never imports `symbiont_lab`: this evaluation code lives
entirely on the `symbiont_lab` side, so there is no code path for it to
feed back even by accident. Wires `symbiont-lab evaluate advisories
label`/`summary [--window-ticks N]`.

**Milestone D — Operational embodiment (#55, v0.44–v0.49) is complete**,
with one honest caveat carried forward: v0.47's Windows/macOS CI results
are still pending actual execution (blocked by this session's GitHub
Actions billing issue) — the configuration exists and the Alpine/musl
constrained environment was verified locally, but "multi-platform" isn't
fully closed until those two checks actually run and pass.

### Strict Epistemological Rule

The experimental subject (`symbiont`) **never** imports or depends on the scientific apparatus (`symbiont_lab`). Synthetic ground truth belongs exclusively to the evaluator and never feeds back into agent cognition. This boundary is enforced via continuous AST inspection in CI.

## Organism roadmap

Development from real perception through cooperative intelligence is defined in
[the organism roadmap](docs/roadmap.md) and tracked in
[GitHub issue #36](https://github.com/alessbarb/symbiont-lab/issues/36).

## Unified CLI: `symbiont-lab`

All experiments, studies, audits, and reproductions are accessible through a single entrypoint:

```bash
# 1. Run a synthetic simulation
symbiont-lab simulate --hosts 100 --steps 300 --seed 7

# 2. Launch localhost dashboard
symbiont-lab dashboard --port 8765

# 3. Run a declarative experiment from TOML spec
symbiont-lab experiment run experiments/attention/causal-v0242-revalidation/experiment.toml

# 4. Run an experimental study protocol
symbiont-lab study run attention.replicated --seeds 101,127,149

# 5. Verify laboratory experimental invariants
symbiont-lab audit verify

# 6. List and inspect recent archived runs and studies
symbiont-lab archive list

# 7. Bitwise reproduction of an execution from its manifest
symbiont-lab reproduce .symbiont/runs/<run_id>/manifest.json

# 8. Discover the safe, read-only, identity-free capabilities this host offers
symbiont-lab host discover

# 9. Sample real, typed readings for the capabilities this host discovers
symbiont-lab host sample

# 10. Run bounded, backoff-aware discovery+sampling ticks
symbiont-lab host monitor --ticks 5

# 11. Learn a descriptive baseline per capability (no threat conclusions)
symbiont-lab host acclimate --ticks 5

# 12. Synthesize platform-neutral percepts from this host's real readings
symbiont-lab host perceive

# 13. Learn a per-time-bucket baseline and co-occurrence for this host's percepts
symbiont-lab host rhythms --ticks 5

# 14. Classify each percept against its own aging baseline: isolated, gradual or regime shift
symbiont-lab host drift --ticks 5

# 15. Export safe abstract beliefs (no raw telemetry) to a schema-versioned checkpoint
symbiont-lab host checkpoint export --ticks 5

# 16. Restore beliefs from a checkpoint read on stdin
symbiont-lab host checkpoint export --ticks 5 | symbiont-lab host checkpoint import

# 17. Allocate a hard attention budget across this host's capabilities by uncertainty and cost
symbiont-lab host attend --ticks 5 --budget 1.5

# 18. Temporarily sample one already-discovered capability at higher resolution
symbiont-lab host second-look --capability-id compute.logical_cpu --ticks 5

# 19. Revise a capability's baseline from a second-look evidence batch, keeping any conflict as dissent
symbiont-lab host revise --capability-id compute.logical_cpu --acclimate-ticks 5 --evidence-ticks 3

# 20. Build an inspectable narrative combining belief, attention, evidence and uncertainty
symbiont-lab host narrate --ticks 5 --budget 1.5 --evidence-ticks 3

# 21. Sign a checkpoint into an offline, identity-minimized knowledge capsule
symbiont-lab capsule create --ticks 5 --keyfile my-signing-key.json

# 22. Verify a knowledge capsule's signature, read as JSON on stdin
symbiont-lab capsule create --keyfile my-signing-key.json | symbiont-lab capsule verify

# 23. Verify a capsule and learn per-source reliability against this host's own beliefs
symbiont-lab capsule create --keyfile their-key.json | symbiont-lab capsule ingest --ticks 5

# 24. Run the organism's continuous cognitive cycle: discover, observe, acclimate,
#     perceive, track drift, attend, investigate, revise, explain — repeatedly
symbiont-lab organism run --ticks 5 --attention-budget 1.5 --investigate-ticks 2

# 25. Run it under an explicit, revocable consent and resource budget
symbiont-lab organism run --ticks 10 --max-ticks 5 --min-seconds-between-ticks 1.0

# 26. Run it with durable state: resumes from --state-file if present, saves atomically after
symbiont-lab organism run --ticks 5 --state-file organism-state.json

# 27. Run it with defensive advisories enabled (separate, explicit consent required) and logged
symbiont-lab organism run --ticks 10 --advisory-consent --advisory-log advisories.json

# 28. Record a real operator's judgment of one fired advisory (laboratory apparatus, not cognition)
symbiont-lab evaluate advisories label --advisory-log advisories.json --labels-file labels.json \
  --tick 3 --capability-id compute.logical_cpu --judgment useful

# 29. Summarize usefulness/false-alarm rate against those real judgments
symbiont-lab evaluate advisories summary --advisory-log advisories.json --labels-file labels.json
```

*(Legacy entrypoints such as `symbiont-sim`, `symbiont-dashboard`, `symbiont-causal-budget-study`, etc. remain available as deprecated backwards-compatible wrappers.)*

## Declarative Experiments & Manifests

Experiments are specified declaratively in TOML (using Python 3.11's stdlib `tomllib` with zero external dependencies):

```toml
schema_version = 1

[experiment]
id = "attention.causal.v0242-revalidation"
title = "Corrected causal attention revalidation"
protocol = "attention.replicated"
protocol_version = 3

[world]
hosts = 100
steps = 300
threat_rate = 0.018
poison_fraction = 0.08
heterogeneity = 0.12

[design]
seeds = [101, 127, 149, 173, 199]

[attention]
budgets_per_1000 = [5, 12, 20]
reference_strategy = "random"
```

Each run generates an immutable execution manifest in `.symbiont/runs/<run_id>/manifest.json` recording software version, git sha, master seed, config digest, world digest, selection digests, and metric outcomes.

## Architectural Decision Records (ADRs)

Formal laboratory memory is documented in `docs/adr/` and mirrored in `research/decisions/`:

* **ADR-0001:** Two-Package Architecture Boundary
* **ADR-0002:** Synthetic Ground Truth Isolation
* **ADR-0003:** Attention is Not Classification
* **ADR-0004:** Separated RNG Streams
* **ADR-0005:** Shadow-Only Second-Look Evidence Probes
* **ADR-0006:** Evidence Revision Identity
* **ADR-0007:** Common Causal Eligibility for Attention Allocation

## Testing Taxonomy

The test suite is organized into 5 epistemological suites:

* `tests/unit/`: Component-level unit tests for organism (`core`), universe (`environment`), simulation engine (`simulation`), and lab apparatus (`lab`).
* `tests/integration/`: Multi-module pipelines and study workflows.
* `tests/experimental_integrity/`: Rigorous invariant checks: AST dependency checks, RNG stream independence, deterministic world digests, seed pairing, evidence replay idempotency, and prefix causality.
* `tests/regression/`: Historical audit regression tests (e.g. `audits/v021`, `audits/v024`).
* `tests/smoke/`: CLI commands and dashboard server execution smoke tests.

```bash
pytest                                                     # full suite
pytest tests/experimental_integrity/                      # scientific invariants
pytest tests/smoke/                                       # CLI & server smoke tests
```

## Safety Boundaries

Symbiont cognition and all threats remain synthetic. Real-host interaction is limited to explicit, local, read-only, identity-free capability discovery. Never introduce remote discovery, network scanning, propagation, persistence, stealth/evasion, OS modification, exploitation, credential access, autonomous real-world actions, or collection of user content.
