# Symbiont Lab Constitution

## Purpose

This document defines permanent constraints on the repository, the research subject and the scientific apparatus. It is intentionally more stable than the roadmap.

Changes to this document are L4 and require an explicit owner decision plus an accepted ADR.

## Authority

The project owner chooses scientific direction, accepts constitutional changes, authorises held-out/confirmation execution and may open or close capability programmes.

Agents may analyse freely, but implementation authority is bounded by `agent-policy.md`. Technical ability to edit a file does not grant scientific authority.

## Ontology

- `symbiont` is the organism/research subject.
- `symbiont_lab` is the scientific apparatus.
- `symbiont_world` is the external world.
- Observatory is passive.
- Only Lab may connect World and Symbiont.
- Refactoring convenience never justifies collapsing these boundaries.

## Epistemic separation

Symbiont may know only inherited constitution or what can be acquired from its experience.

Evaluator ground truth, semantic labels, success/failure labels, fitness, resource identities, hazard identities, privileged coordinates and human-defined task semantics must not enter cognition.

A stable identifier may exist without preassigning its meaning. Observation, hypotheses, imagination and evaluator truth remain distinguishable.

## No global objective injection

Symbiont has no project-wide scalar reward, fitness or utility function. Homeostasis, energy, integrity and physiology are internal state, not a disguised external reward.

The Lab may measure outcomes but must not feed those measurements back into the subject.

## Agency

Actuators begin as opaque channels. Action/effect relations and competences are acquired from experience.

Lab must not secretly translate an intent into semantic commands such as stand, walk, survive or optimise a human objective.

Any innate reflex must be explicitly constitutional and separate from acquired learning.

## Learning and evidence

Learning must depend on subject-available evidence and preserve epistemic origin.

A scientific result may be negative. Negative evidence must not be rewritten or treated as an implementation defect solely because it is inconvenient.

Experiments must be capable of falsification. Criteria do not move after results are observed unless a new version is explicitly opened.

## Genome, reproduction and heredity

Genome belongs to the organism; mutation, recombination, selection, genealogy and offspring orchestration belong to Lab.

A child is a new organism identity.

A child may inherit declared germinal constitution but must not silently inherit the parent's acquired cognition, episodes, learned BodySchema, AgencyModel, private-model corpus/weights or acquired competences.

Transgenerational epigenetics requires an explicit bounded protocol.

## Embodiment and continuity

Symbiont and Body are distinct. Embodiment binds them.

Body destruction or replacement does not necessarily imply organism death. Re-embodiment preserves the same Symbiont and body-independent cognition.

Body-specific evidence may require revalidation when the bodily contract changes; it is not silently erased or reinterpreted.

Normal restore of a DEAD identity is rejected. A reconstruction or clone from historical material, if explicitly allowed, creates a new identity rather than resurrecting the dead one.

## Persistence and provenance

Portable cognitive state and physical Body state remain distinct.

Checkpoint restoration must preserve enough causal state to explain and continue live state. Inconsistent multi-part state is rejected rather than repaired by inventing state.

Lineage, death and reproduction changes must be transactional and replay-testable. Historical scientific results and provenance are append-only evidence.

## Observability

Observation must not change the organism's life.

Telemetry, UI, logging, debugging and evaluator provenance do not feed cognition. Observer ON/OFF must preserve the declared causal-equivalence contract.

The organism must not wait for visual presentation.

## Capacity

Hard CPU, memory, storage, communication and population ceilings remain outside learned control.

The organism may experience bounded internal capacity pressure, but measurement of capacity must remain passive.

Population work must respect carrying-capacity and negative over-capacity tests.

## Real-host safety

Real-host access is explicit, revocable, local, least-privileged and bounded. Consent is live and checked when capability is exercised.

The project does not add arbitrary filesystem traversal, process-content inspection, identifying/user-content collection, credentials, network scanning, peer discovery, privilege escalation, exploitation, stealth/evasion, hidden persistence, autonomous remediation, self-installation or uncontrolled propagation.

Transparent owner-installed foreground/user-service residence is allowed when revocable and bounded.

Any new host permission class, network exchange, persistence boundary or real-world action requires an L4 owner decision.

## Scientific claims

Implementation is not generalisation.

Every scientific claim states scope, evidence and limitations. The canonical claim vocabulary and evidence levels are defined in `docs/roadmap.md`.

## Constitutional change

No agent may rewrite an invariant to legitimise an implementation that already violates it.

The only valid order is:

```text
proposal -> ADR -> owner acceptance -> constitution update -> implementation
```
