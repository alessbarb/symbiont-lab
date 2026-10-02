# Design Status Register

**Authority:** canonical register for the lifecycle and implementation status of
design documents under `docs/design/`.
**Last triaged:** 2026-10-02.
**Owner:** Project owner.

This register exists so design proposals remain discoverable without changing
the scientific roadmap. The roadmap remains authoritative for research
direction, priority, gates, and authorization to run experiments. This register
tracks whether a design has been reviewed or approved and whether its approved
work has been implemented. Neither a design document nor a register entry
authorizes a change that requires a separate owner or governance decision.

## Required reading and maintenance

Before creating, reviewing, approving, implementing, or reporting completion of
a design under `docs/design/`, read this register. Every non-archived design
must have an entry here. Update this register in the same change that changes a
design's review, approval, implementation, or supersession state. A design not
yet assessed is **Triage required**; do not infer approval or implementation
from its title, age, roadmap mention, or the presence of similar code.

`docs/design/README.md` is a navigation page, not a competing status source.
The roadmap may link to register entries to show where a design relates to a
milestone, but only the roadmap sets milestone priority and acceptance.

## Lifecycle states

Use one **Design state** and one **Implementation state**. Review is not
approval, approval is not scheduling, and implementation is not scientific
acceptance.

### Design state

- **Triage required** — not yet classified in this register.
- **Proposed** — recorded for consideration; no review or implementation
  authorization is implied.
- **In review** — an identified reviewer is evaluating the design.
- **Reviewed** — documentary/source triage is complete and its result is
  recorded; this alone does not approve the design.
- **Approved** — the authorized owner has accepted the design for its stated
  scope. Record the decision reference and date.
- **Frozen** — the bounded design or mechanism is closed to revision and may
  only be studied under its existing contract or reopened by the owner.
- **Closed** — the design/study is closed; record whether closure was positive,
  negative, or not assessable. Closure is not a general capability claim.
- **Reference** — explanatory or audit material, not an implementation
  proposal.
- **Rejected** — the owner declined the proposal; preserve the rationale.
- **Superseded** — another design replaces it; link the replacement.

### Implementation state

- **Not started** — no implementation is claimed.
- **Pending** — approved work awaits scheduling or a prerequisite. This is not
  authorization to start.
- **In progress** — implementation is authorized and underway; link its work
  item or branch/PR when applicable.
- **Partial** — some bounded elements exist, but the design is not fully
  implemented; state the boundary.
- **Implemented** — source-level implementation is identified and validated
  against the design's bounded contract. Link evidence; this does not imply
  scientific acceptance.
- **On hold** — implementation or follow-up is explicitly paused; cite the
  decision. This is not an invitation to restart it.
- **Not applicable** — the document is an audit, rationale, or other artifact
  that does not specify implementation work.

Do not mark work **Approved** based only on review comments. Do not mark it
**Implemented** because a similarly named feature exists. Record owner,
reviewer, decision/evidence references, and dates whenever a state changes.

## Triage record

The initial triage below was completed on 2026-10-01 against document status
statements, owner decisions recorded in those documents, the active roadmap,
and source/test markers where an implementation claim was explicit. It is a
documentary inventory, not a fresh scientific validation or blanket technical
review. **Approved**, **Frozen**, and **Closed** states are used only where the
source documents or roadmap record the corresponding owner disposition.
Implementation status describes only the stated bounded scope; it does not
imply scientific success. Where approval was not recorded, a completed or
partial implementation is not retroactively treated as approved.

| Design | Design state | Implementation state | Triage result / next action |
|---|---|---|---|
| [Adaptive Experience Replay v1](cognition/adaptive-experience-replay-v1.md) | Reviewed | Partial | Document reports an implemented foundation; reconcile stale `unclassified` metadata in a later doc cleanup. |
| [Autonomous Experience Replay v1](cognition/autonomous-experience-replay-v1.md) | Reviewed | Partial | Document reports an implemented foundation; no broader scientific acceptance inferred. |
| [Autonomous Replay Stopping v1](cognition/autonomous-replay-stopping-v1.md) | Reviewed | Implemented | Implementation stated complete; scientific gates remain pending execution. |
| [Cognitive Atlas v2 Phase A Audit](cognition/cognitive-atlas-v2-phase-a-audit.md) | Reference | Not applicable | Audit artifact, not an implementation proposal; its `unclassified` frontmatter is non-authoritative. |
| [Emergent Symbol Grounding v1](cognition/emergent-symbol-grounding-v1.md) | Reviewed | Implemented | Preregistered study results are recorded in the document; this does not imply general language capability. |
| [Episodic Experience Memory v2](cognition/episodic-experience-memory-v2.md) | Reviewed | Implemented | Document calls this the implemented replacement for v1; retain that bounded scope. |
| [Generative Cognition v1](cognition/generative-cognition-v1.md) | Proposed | Partial | Still marked a proposed freeze candidate; implementation audit records partial implementation. Do not call it canonical or authorize further work from this entry. |
| [Generative Cognition v1 Implementation Gap Audit](cognition/generative-cognition-v1_implementation-gap-audit-against-main.md) | Reference | Not applicable | Audit records bounded gates and gaps; its historical validation snapshot is not current-main validation. |
| [Predictor Promotion Throughput v1](cognition/predictor-promotion-throughput-v1.md) | Proposed | On hold | Explicitly not approved, not implemented, not run, and unscheduled; roadmap says it is not a D1 follow-up. |
| [Autonomous Cultural Agency v1](communication/autonomous-cultural-agency-v1.md) | Reviewed | Implemented | Bounded implementation and study exist; frontmatter says unclassified, and no broader acceptance is inferred. |
| [Cultural Future](communication/cultural-future.md) | Reference | Not applicable | Synthesis/status document; individual capabilities and studies retain their own evidence. |
| [Emergent Structured Communication v1](communication/emergent-structured-communication-v1.md) | Reviewed | Implemented | Document reports bounded implementation and base study; composition/generalization claims stay separate. |
| [Structured Communication Characterization v1](communication/structured-communication-characterization-v1.md) | Reviewed | Partial | Preregistered characterization exists; technical status is not equivalent to positive study closure. |
| [Agency Acquisition and Executive Action v1](core/agency-acquisition-and-executive-action-v1.md) | Frozen | Implemented | Roadmap and owner audit freeze architecture; E4/E2/E5 limitations remain open only under their separate protocols. |
| [Agency Acquisition and Executive Action v1 Implementation Audit](core/agency-acquisition-and-executive-action-v1_implementation-audit.md) | Reference | Not applicable | Owner audit records architecture closure and separate bounded experimental outcomes. |
| [Binding Degradation v1](core/binding-degradation-v1.md) | Approved | Not started | Owner-approved preregistered design; document explicitly says not implemented. Any execution/implementation still follows its recorded gates. |
| [Causal Provenance v1](core/causal-provenance-v1.md) | Approved | Partial | Owner approved defaults; contract is implemented, adoption is incomplete (step 1 only per §10). |
| [Cross-Domain Revision Coherence v1](core/cross-domain-revision-coherence-v1.md) | Approved | Partial | Wave 0 approved; Wave 1 awaits owner start; later waves remain gated. Roadmap governs current sequencing. |
| [Executive Outcome Learning v1](core/executive-outcome-learning-v1.md) | Frozen | Implemented | v1/v1.1 are frozen on roadmap; further mechanism work is deferred to Phase B. |
| [Factorized Effect Representation v1](core/factorized-effect-representation-v1.md) | Approved | On hold | Owner-approved scope is explicitly on hold after unstable footprint evidence; return to owner, do not restart from register. |
| [Footprint Precision v1](core/footprint-precision-v1.md) | Proposed | Not started | FP-0 is preregistered; proposed mechanism remains distinct from approval to implement it. |
| [Private Model Learnability v1](core/private-model-learnability-v1.md) | Closed | Implemented | Roadmap closes the bounded P6 experimental scope; scaling remains paused. No production scaling authorization. |
| [Promotion Stability v1](core/promotion-stability-v1.md) | Proposed | On hold | Design phase; confirmation and P5.2 paused until P0/P1 close. |
| [Simulation Throughput v1](core/simulation-throughput-v1.md) | Reviewed | Partial | Owner decisions approve only stated bounded levels; do not infer approval for every proposed level or causal optimization. |
| [Social Epistemology Ownership v1](core/social-epistemology-ownership-v1.md) | Proposed | Implemented | ARCH-1 consumer/ownership matrix. Owner decision of 2026-10-02: Option A, the modeled ledger is the single canonical owner in the organism runtime; implemented. The fate of the legacy envelope transport is recorded as open. |
| [Embodiment Epoch Summary v1](embodiment/embodiment-epoch-summary-v1.md) | Proposed | Partial | Active observational-contract delta over Embodiment v2; two runtime-specific summary stores remain distinct. Semantics, retention, provenance, and no-leakage acceptance are specified as residual work; no runtime change or experiment authorization. |
| [Embodiment Memory v1](embodiment/embodiment-memory-v1.md) | Superseded | Partial | Active architecture replaced by Embodiment v2; legacy `embodiment_memory` is a one-way migration input only. This does not establish useful transfer or satisfy every historical proposal. |
| [Embodiment v2](embodiment/embodiment-v2.md) | Reviewed | Implemented | Document says implemented on `main`; preserve distinction between implementation and scientific acceptance. |
| [Living Body P0](embodiment/living-body-p0.md) | Reviewed | In progress | L1–L4 complete and L5 mechanism implemented; validation remains pending per document. |
| [Longitudinal Re-embodiment Implementation Plan](embodiment/longitudinal-reembodiment-implementation-plan.md) | Reviewed | Partial | Plan says implementation-ready; implementation exists in the repository, but this triage does not claim every plan item closed. Reconcile against current code before further work. |
| [Longitudinal Re-embodiment v1](embodiment/longitudinal-reembodiment-v1.md) | Proposed | Partial | Active only for residual scientific questions; architecture/mechanical continuity is covered by Embodiment v2 and Longitudinal Integrity v1. No functional-transfer claim or experiment authorization. |
| [Lifecycle Continuity Contract v1](core/lifecycle-continuity-contract-v1.md) | Proposed | Implemented | Single description of every lifecycle operation (save, restart, historical and owner-facing restore, canonical re-embodiment, reduced-seed transplant) against the executable continuity registers. Declares the two transplant semantics and the durable lineage history; convergence, legacy sunset and functional transfer are recorded as owner decisions. No scientific-value claim. |
| [Longitudinal Integrity v1](core/longitudinal-integrity-v1.md) | Closed | Implemented | Owner closed the gate positively on 2026-10-02: mechanical longitudinal continuity established within the documented scope. Focused validation: 280 passed; no future-state equivalence, historical pre-schema-11 identity, functional transfer, or scientific-value claim. |
| [Perception and Embodiment](embodiment/perception-and-embodiment.md) | Reviewed | Implemented | Document records design closure and bounded implementation/test evidence; no extension beyond that evidence. |
| [Physics3D Embodiment v0](embodiment/physics3d-embodiment-v0.md) | Reviewed | Implemented | Document identifies canonical-runtime integration as implemented. |
| [Symbiont Body Temporal Separation v1](embodiment/symbiont-body-temporal-separation-v1.md) | Superseded | Partial | Architectural/mechanical contract replaced by Embodiment v2 and Longitudinal Integrity v1. Historical rationale retained; no scientific conclusion is implied. |
| [Adaptive Sensory Specialisation Experiments](experimentation/adaptive-sensory-specialisation-experiments.md) | Proposed | Not started | Preregistration design; no executed or accepted result inferred. |
| [Experimental Decontamination P0](experimentation/experimental-decontamination-p0.md) | Reviewed | Implemented | Document reports implementation; extended by P1. |
| [Experimental Decontamination P1](experimentation/experimental-decontamination-p1.md) | Reviewed | Implemented | Document reports implementation; extended by P2. |
| [Experimental Decontamination P2](experimentation/experimental-decontamination-p2.md) | Reviewed | Implemented | Document reports implemented candidate; do not infer wider acceptance. |
| [Private Model Causal Contribution v1 — Preregistration Draft](experimentation/private-model-causal-contribution-v1.md) | Proposed | Not started | Draft preregistration for an evidence follow-up after Longitudinal Integrity v1. Not approved, not registered, not scheduled; no experiment, protocol or runner exists. Requires the owner to close the LI-1 gate and approve the design before any run. |
| [Model Ancestry Matched-Budget Utility v1 — Preregistration Draft](experimentation/model-ancestry-matched-budget-v1.md) | Proposed | Not started | Draft preregistration for an evidence follow-up after Longitudinal Integrity v1. Not approved, not registered, not scheduled; no experiment, protocol or runner exists. Requires the owner to close the LI-1 gate and approve the design before any run. |
| [Generative Cognition Causal Contribution v1 — Preregistration Draft](experimentation/generative-cognition-causal-contribution-v1.md) | Proposed | Not started | Draft preregistration for an evidence follow-up after Longitudinal Integrity v1. Not approved, not registered, not scheduled; no experiment, protocol or runner exists. Requires the owner to close the LI-1 gate and approve the design before any run. |
| [Re-embodiment Functional Transfer v1 — Preregistration Draft](experimentation/reembodiment-functional-transfer-v1.md) | Proposed | Not started | Draft preregistration for the first evidence follow-up after Longitudinal Integrity v1. Not approved, not registered, not scheduled; no experiment, protocol or runner exists. Requires the owner to close the LI-1 gate and to approve the design before any run. |
| [Experimental Organism v1 Freeze](experimentation/experimental-organism-v1-freeze.md) | Frozen | Implemented | Freeze contract is active as recorded; changes require the applicable owner/governance decision. |
| [Endogenous Metaplastic Epigenetics v1](genome/endogenous-metaplastic-epigenetics-v1.md) | Proposed | Partial | Proposal/preregistration predates implementation; regulation components exist, but the full inheritance/validation contract is not thereby accepted. |
| [Genome v2](genome/genome-v2.md) | Reviewed | Implemented | Document states implemented in core and main adapters. |
| [Self-Model Workbench v1](observability/self-model-workbench-v1.md) | Reviewed | Implemented | Document marks implementation complete; Observatory remains passive. |
| [Cognitive Panel Observability States v1](observability/cognitive-panel-observability-states-v1.md) | Proposed | Implemented | Nine named states for cognitive panels (absent, disabled, not ready, idle, empty, active, unavailable, stale, error). Lifecycle is derived from organism facts on the Lab side; implemented for the generative panel and for the empty states of the Mind data panels. Other subsystems publish no lifecycle status yet. |
| [Experience and World Architecture v1 Implementation Gap Specification](observability/symbiont-lab-experience-and-world-architecture-specification-v1-spec.md) | Reference | Not applicable | Gap analysis against target specification, not an independent implementation authorization. |
| [Experience and World Architecture v1](observability/symbiont-lab-experience-and-world-architecture-specification-v1.md) | Proposed | Partial | Architecture specification spans implemented and proposed seams; use the gap analysis and roadmap for actual scope. |
| [Body in World v1](observatory/body-in-world-v1.md) | Reviewed | Implemented | Document identifies the observation contract as implemented; maintain passive/read-only authority boundary. |
| [Experienced World v1](observatory/experienced-world-v1.md) | Proposed | Partial | Draft separates implemented observation paths from proposed features; do not treat the entire draft as implemented. |
| [Integrated Habitat Runtime v1](runtime/integrated-habitat-runtime-v1.md) | Reviewed | Partial | Runtime/checkpoint code and tests exist; full status remains the bounded restore/replay evidence recorded in the document. |
| [Sensorimotor Development v1](sensorimotor/sensorimotor-development-v1.md) | Reviewed | Partial | Baseline is implemented; empirical validation remains pending. |
| [Symbiont Actuation v1](sensorimotor/symbiont-actuation-v1.md) | Reviewed | Implemented | P0 is declared closed in revision 6; do not interpret that as acceptance of broader sensorimotor capability. |
| [Physics3D Telemetry v4.1](telemetry/physics3d-telemetry-v4.1.md) | Reviewed | Implemented | Document identifies the canonical writer for new Physics3D runs. |
| [Population Communication Telemetry v1](telemetry/population-communication-telemetry-v1.md) | Proposed | Not started | No approval or implementation evidence recorded in the document. |
| [Visual Acquisition v1](vision/visual-acquisition-v1.md) | Closed | Implemented | D1-v2 is a structural negative/not assessable; held-out seeds are disabled. Runner implementation is not acquisition success. |
| [World Responsibility Map v1](world/world-responsibility-map-v1.md) | Proposed | Implemented | Inventory of every environment family, its owning layer, role, consumers and state. Removes nothing and authorizes nothing; relocation, retirement and vocabulary are recorded as owner decisions. |
| [Symbiont World v1 Rationale](world/symbiont-world-v1-rationale.md) | Reference | Not applicable | Rationale/audit artifact; use current World design and code as status sources. |
| [Symbiont World v3](world/symbiont-world-v3.md) | Reviewed | Implemented | Document records implementation on `main`; preserve its bounded P0–P6 scope. |
| [Symbiont World v4](world/symbiont-world-v4.md) | Proposed | Not started | Technical specification with `planned` implementation state; roadmap priority/authorization still controls. |
| [World Ecology v1](world/world-ecology-v1.md) | Reviewed | Implemented | Document reports implemented; extended by later ecology work. |
| [World Ecology v2](world/world-ecology-v2.md) | Reviewed | Implemented | Core corrections are implemented; viability characterization is separate. |
| [Passive Runtime Audit Trace v1](observability/passive-runtime-audit-trace-v1.md) | Proposed | Not started | Revisit after A9 baseline inventory; owner disposition required before implementation. |

Archived documents remain in `archive/` and are not active register entries.
