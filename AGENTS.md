# AGENTS.md

Repository-wide operating contract for intelligent coding agents working on Symbiont Lab. Read this file before any modification.

<!-- BEGIN CANONICAL AGENT CONTRACT -->

## Authority model

Coding agents execute authorised work. They do not choose the scientific direction of the project.

Before modifying the repository, classify the task:

| Level | Authority | Typical work |
| --- | --- | --- |
| L0 | Read-only | inspection, review, audit, proposals |
| L1 | Maintenance | docs, links, formatting, non-semantic test maintenance |
| L2 | Contract-preserving implementation | bug fix or implementation whose desired behaviour is already normative |
| L3 | Scientific mechanism change | cognition, learning, agency, physiology, World experience, experiment mechanism |
| L4 | Constitutional / safety change | host permissions, network, persistence, propagation, evaluator boundary, reproduction authority, global limits |

L3 requires an approved design and, when scientific evidence will be produced, an approved preregistration before implementation or execution. L4 always requires an explicit owner decision and an accepted ADR before implementation.

A passing test, benchmark, experiment or CI run never grants additional authority.

## Mandatory startup sequence

Before editing:

1. inspect the current branch/head and worktree;
2. read this contract, `docs/roadmap.md`, `docs/governance/project-state.toml`, and the nearest relevant README/design/ADR;
3. run `python scripts/agentctl.py status`;
4. classify the change L0-L4 and identify subject/lab/world/observatory/experiment domains;
5. check `docs/governance/active-work.toml` and do not edit the mechanism, protocol, inputs or dependencies of an active scientific run;
6. check `docs/governance/frozen-artifacts.toml`;
7. choose the smallest-authority solution that satisfies the approved contract.

Do not rely on memory from another session as project authority. An owner decision must be present in the current instruction, an accepted ADR, the roadmap, preregistration, project-state metadata, or a committed design record.

## Change discipline

Agents must distinguish implementation defect, apparatus defect, obsolete test, historical compatibility contract, negative scientific result, and new scientific hypothesis.

A red test is not permission to weaken an assertion. A negative result is not a bug. Do not change the organism merely to satisfy a test, experiment, visualization, benchmark, evaluator or UI.

For scientific work, preserve this order:

```text
negative or open result
-> analysis
-> hypothesis
-> design
-> owner approval
-> preregistration
-> implementation
-> campaign
-> interpretation
```

Never skip directly from a negative result to mechanism changes intended to make it positive.

## Protected and frozen material

The following are authority-sensitive:

- `AGENTS.md`, `CLAUDE.md`, `docs/governance/**`, `docs/roadmap.md`;
- accepted ADRs and frozen design/preregistration sections;
- experiment criteria, seeds, horizons, baselines and frozen inputs;
- completed result artefacts and historical audit evidence.

Frozen result artefacts are append-only evidence. Correct an error with a new run, version or provenance note; do not rewrite the old result to match a preferred interpretation.

## Experiment state rules

Experiments move through:

```text
DRAFT -> DESIGN -> PREREGISTERED -> FROZEN -> RUNNING -> COMPLETE -> INTERPRETED
```

While RUNNING, no agent may modify its runner, protocol, frozen inputs, dependencies or relevant subject mechanism.

After PREREGISTERED/FROZEN, seeds, horizon, baselines, success criteria and interpretation rules do not move because of observed results. Held-out or confirmation runs require the explicit authority recorded by the relevant design.

Apparatus repair and hypothesis change must be separated.

## Claims

Use the claim vocabulary from `docs/roadmap.md`.

Do not elevate claims such as `validated`, `causal`, `robust`, `emergent`, `learned`, `closed` or `general` without identifying the evidence level, tested scope and limitations.

## Concurrency

Treat `docs/governance/active-work.toml` as a coordination boundary.

If another session owns a RUNNING campaign, do not modify its protected paths. Read-only inspection is allowed. A work record is not stale merely because time passed; verify that the process/run is actually finished before clearing it.

Default scientific resource policy: one long scientific campaign at a time unless the approved design explicitly requires parallel execution.

## Git and commit rules

Never:

- use destructive reset/clean on work you did not create;
- force-push or rewrite published scientific history;
- stage or overwrite unrelated user/session changes;
- delete negative results;
- squash away provenance needed to understand a scientific result.

Before commit:

1. review the exact diff;
2. run the validation required by `docs/governance/validation-matrix.toml`;
3. run `python scripts/agentctl.py verify`;
4. run `git diff --check`;
5. keep commits logical and auditable.

Permission to edit does not automatically imply permission to run a campaign, push, merge or reinterpret its result.

## Stop conditions

Stop and request an owner decision before:

- changing a hypothesis, threshold, seed set, horizon, baseline or success criterion;
- executing held-out or confirmation data without recorded approval;
- reopening a PAUSED, BLOCKED or UNSCHEDULED programme;
- moving responsibility across Symbiont/Lab/World boundaries;
- introducing a new organism capability;
- changing lifecycle, heredity, reproduction or re-embodiment semantics;
- adding host permissions, user-content access, identifying metadata, arbitrary file or process inspection, network exchange, credentials, hidden persistence, propagation, autonomous real-world action or new permission classes;
- weakening evaluator/subject separation or introducing global reward/fitness;
- altering project priorities or skipping a roadmap gate.

## Host safety

Real-host access remains explicit, revocable, local, least-privileged and bounded. Consent is checked at use time, not treated as a one-time installation event.

Agents must not add identity or user-content collection, arbitrary filesystem traversal, process-content inspection, credential access, network scanning/peer discovery, autonomous network exchange, privilege escalation, exploitation, stealth/evasion, hidden persistence, autonomous remediation, self-installation or uncontrolled propagation.

CPU, memory, storage, communication and population ceilings remain outside learned control. Reproduction never means covert self-propagation.

<!-- END CANONICAL AGENT CONTRACT -->

## Normative architectural invariants

These are binding constraints, not recommendations or a claim that the current
implementation already complies. Existing violations are architectural debt,
not precedents or exceptions. A passing test, experiment, benchmark, or CI run
never authorizes a violation. Changes to these constraints require an explicit
architecture decision approved by the project owner. Keep this entire section
identical in `AGENTS.md` and `CLAUDE.md`.

### 1. Ontological boundaries

1. **Symbiont is the subject.** `src/symbiont/` must contain only state, capabilities, and processes belonging to the organism.
2. **Lab is the apparatus.** `src/symbiont_lab/` owns experimentation, reproduction, evolution, evaluation, external instrumentation, and scientific orchestration.
3. **World is the world.** `src/symbiont_world/` owns external laws, opportunities, and dynamics, never cognition or internal organism knowledge.
4. Symbiont must not import `symbiont_lab`.
5. Symbiont must not import `symbiont_world`.
6. World must not import `symbiont` or `symbiont_lab`.
7. Lab is the only layer authorized to connect World and Symbiont.
8. Refactoring must not erase these boundaries to simplify dependencies.

### 2. Own state versus external knowledge

9. Symbiont may know only what is available through its constitution or experience.
10. The organism must not receive experimental ground truth.
11. It must not receive evaluator-produced labels such as `correct`, `target`, `fitness`, `success`, `dangerous`, `desired`, `expected`, or equivalents.
12. Laboratory IDs, coordinates, names, or categories must not become internal cognitive semantics.
13. Discovered semantics must arise from experience, regularities, and observable relations.
14. A signal identifier may be stable, but its meaning must not be preassigned.
15. Lab may know experimental truth; Symbiont must not receive that privileged knowledge.

### 3. No imposed global reward or objective

16. Symbiont must not have a global reward, utility, or fitness function directing its behavior.
17. A global weighted sum for action selection must not be introduced.
18. Explicit goals such as walking, standing up, surviving, exploring, or being efficient must not be added without an approved specification deriving them from internal mechanisms.
19. Homeostasis, integrity, energy, and other bodily variables are internal states, not a disguised global reward.
20. Lab may measure outcomes; those measurements must not feed back into subject decisions.

### 4. Action and agency

21. Symbiont must not be born knowing what an action means.
22. Actuators must initially be opaque channels.
23. Action-to-effect relations must be acquired through experience.
24. A `MotorPrimitive` must not automatically count as a competence.
25. A competence requires acquired evidence and consolidation under its contract.
26. Intentions must not be translated into semantic external commands.
27. Lab must not tell the organism to stand up, walk, or perform equivalent semantic tasks through a hidden interface.
28. Any innate reflex must be explicitly justified as inherited constitution and kept separate from acquired learning.
29. A satisfaction policy must not be changed solely to make an experiment pass.

### 5. Prospection and imagination

30. Private prospection belongs to the organism.
31. The prospective selector must not receive evaluator metrics.
32. An imagined prediction must not directly train its own value as if it had occurred.
33. Outcome/value learning must come from actually observed episodes.
34. A hypothesis, prediction, or internal simulation must remain epistemically distinguishable from an observation.
35. Imagination must not fabricate causal evidence.

### 6. Learning

36. Learning must depend on evidence available to the subject.
37. Lab-produced labels must not enter private training.
38. The same representation must not simultaneously be treated as a prediction and an observation.
39. Model updates must preserve the epistemic origin of data.
40. A parameter change alone must not be called learning without an associated observable or falsifiable property.
41. Claims of predictive learning must compare predictive usefulness against appropriate baselines.
42. Experiments must not redefine organism behavior to obtain the expected result.

### 7. Genome

43. **The Genome belongs to the organism.**
44. `GenomeSchema`, genetic expression, and germline state may belong to `symbiont`.
45. The genome defines capabilities and constraints, not acquired knowledge.
46. A child may inherit genetic constitution.
47. A child must not inherit learned cognition.
48. Episodes, acquired memory, concepts, learned BodySchema, learned AgencyModel, and acquired motor competences must not be inherited.
49. Transgenerational epigenetics requires an explicit, bounded protocol.
50. `birth_expression` must correctly represent the effective state at birth.
51. Genotype and genealogy must remain distinct concepts.
52. `genotype_hash` identifies genetic content, not kinship or experimental identity.

### 8. Evolution and reproduction

53. **An individual must not reproduce itself.**
54. Symbiont must not execute population selection.
55. Symbiont must not execute fitness evaluation.
56. Symbiont must not decide which offspring to create.
57. Mutation operators belong to Lab.
58. Recombination operators belong to Lab.
59. Offspring creation and orchestration belong to Lab.
60. Population lineage and genealogy belong to Lab.
61. Lab may consume a `Genome`; the `Genome` must not import or depend on the evolutionary engine.
62. Genetic state and evolutionary operators must remain distinct responsibilities.
63. An evolutionary implementation must not remain inside `symbiont` merely because it manipulates `Genome` objects.

### 9. Embodiment

64. Symbiont and Body must remain distinct entities.
65. Embodiment is the binding between them.
66. Organism identity must not depend on a specific Body.
67. Destruction or replacement of a Body must not necessarily imply Symbiont death.
68. A Symbiont may become `dormant/suspended` and be reembodied.
69. Physical Body state must not be confused with portable cognitive state.
70. Body-specific knowledge must be revalidated after reembodiment when the bodily contract changes.
71. A competence acquired for one embodiment must not automatically gain authority in another.
72. Reembodiment must not erase body-independent cognition without an explicit reason.
73. Reembodiment must not silently reinterpret incompatible bodily evidence.

### 10. Portable state versus physical state

74. The portable Symbiont checkpoint is authoritative for its cognitive state.
75. The Body checkpoint contains the physical state of the embodiment.
76. Both must support coherent persistence without conflating their state.
77. Loss of the physical server must not destroy the most recent cognitive state.
78. A checkpoint inconsistent across ticks must be rejected, not repaired by inventing state.
79. Schema migrations must never silently reinterpret incompatible evidence.

### 11. Causal provenance

80. Every relevant state change must be explainable in terms of why it exists.
81. Subject causality belongs to the subject.
82. Internal `CausalProvenance` must remain distinct from experimental provenance.
83. Symbiont may retain a bounded causal frontier of its own state.
84. Durable causal history may reside in Lab.
85. Provenance flow toward Lab must be outward-only.
86. Observing provenance must never modify organism decisions.
87. Checkpoint restoration must preserve enough causality to continue explaining live state.
88. Equal final state is insufficient if causal history needed to distinguish how it arose has been lost.

### 12. Capacity and limits

89. Memory and storage limits are part of the organism's reality.
90. `CapacityPressure` may belong to the subject.
91. Measuring occupancy, evictions, or relearning must not alter the policy being measured.
92. Capacity instrumentation must be passive.
93. An observational metric must never accidentally become a decision signal.
94. Memory eviction does not authorize Lab to reinject the lost item.

### 13. Observability

95. **Observation must not change the organism's life.**
96. Observer ON and Observer OFF must preserve causal equivalence within defined limits.
97. Telemetry must not flow back into cognition.
98. Observatory must remain passive.
99. UI, telemetry, logging, and debugging must not introduce additional signals to the organism.
100. Observation cost must be decoupled from the vital loop as far as possible.
101. Visual presentation may drop frames; the organism's life must not stop to wait for it.
102. Instrumentation must distinguish scientific apparatus cost from the organism's own cost.

### 14. Determinism and seeds

103. The same seed, initial state, and conditions must produce the same trajectory under deterministic contracts.
104. Determinism must not be interpreted as requiring all seeds to behave identically.
105. A mechanical test must not require a particular scientific outcome solely because it historically occurred with that seed.
106. Small limits used by fast tests must not become biological requirements.
107. Scientific experiments must respect their preregistered budgets and horizons.
108. Changing organism dynamics to make a seed pass again requires evidence, not convenience.

### 15. Experimentation

109. An experiment must clearly distinguish its mechanical contract, scientific protocol, and scientific result.
110. Unit tests may verify plumbing and determinism, but must not turn contingent experimental results into architectural invariants.
111. A scientific conclusion must not be encoded as truth before it is demonstrated.
112. Studies must declare seeds, horizon, conditions, baselines, and interpretation criteria.
113. A seed that cannot be tested must be allowed to report `not_testable`; a result must not be forced.
114. Ablations must change only the variable they claim to isolate.
115. A control arm must not receive information unavailable to the experimental arm.
116. Evaluator ground truth may be used to measure, never to help the subject solve the task.
117. Experiments must be capable of falsifying the hypothesis.

### 16. Integrity tests

118. Boundary tests must protect architectural properties, not incidental function names.
119. Literal string searches must not be used when AST, introspection, or behavior can prove the actual contract.
120. Renaming a function must not invalidate an epistemological test.
121. A test made obsolete by a legitimate refactor must be updated; legacy architecture must not be restored to satisfy it.
122. Compatibility shims must not be added solely to preserve old internal tests.
123. Tests preventing epistemic contamination take priority over implementation convenience.
124. Green CI never justifies violating an invariant.

### 17. APIs and ownership

125. Each responsibility must have one canonical owner.
126. A CLI is an adapter; it must not take back lifecycle ownership when that belongs to the engine.
127. Old private APIs must not be reexported without explicitly approved public compatibility.
128. Facades must not duplicate implementation.
129. A capability must not have two sources of truth.
130. When refactoring moves ownership, tests must follow the new owner.

### 18. Private SLM

131. The Private SLM belongs cognitively to the organism even when Lab provides its execution substrate.
132. Lab may provide compute, storage, or scheduling.
133. Lab must not provide the private model with answers, labels, or privileged semantics.
134. Experience used to train it must originate from the organism.
135. Private SLM predictions are private hypotheses, not ground truth.
136. `SHADOW`, `ACTIVE`, and other deployment states must not alter this boundary.
137. Training infrastructure and model state must remain distinct responsibilities.
138. Lab physically executing training does not make the resulting knowledge Lab knowledge.

### 19. Self-model and bodily knowledge

139. BodySchema must be acquired from experience.
140. A visual Body model in the UI must not leak into organism knowledge.
141. The organism must not receive a labeled skeleton, named body parts, or anatomical coordinates without an explicitly specified innate capability.
142. Observer visualization may use ground truth to compare `known vs actual`, but the two layers must remain separate.
143. What is known by Symbiont must come exclusively from internal evidence.
144. What is real according to Lab must be visually and structurally identified as evaluator truth.

### 20. World and perception

145. Adding objects to the world must not imply that Symbiont can distinguish them.
146. Before attributing a perceptual capability, sensor information sufficiency must be checked.
147. The world provides phenomena, not categories.
148. Object identity, permanence, spatiality, and source must be acquired, not assumed.
149. Simulator coordinates must not directly enter cognition as a spatial representation.
150. An internal world representation must be built from available sensory relations.

### 21. Persistence and continuity

151. Restoration must continue the same individual when the contract specifies it.
152. Restoration must not fabricate absent memories.
153. Reembodiment and reproduction must remain ontologically distinct operations.
154. A child is a new organism.
155. A reembodied Symbiont remains the same organism.
156. Copying cognitive state to a child is prohibited.
157. Copying cognitive state to the same organism during restoration is permitted when it belongs to its canonical checkpoint.
158. Identifiers must preserve this distinction.

### 22. Golden rules for agents

> **Never change the organism merely to satisfy a test, experiment, visualization, benchmark, evaluator or UI. First determine whether the failing expectation is an invariant of the organism, an apparatus contract, or an obsolete assertion.**

> **When in doubt, information flows from World → sensory boundary → Symbiont, and from Symbiont → passive observation → Lab. Evaluator knowledge never flows back into the subject.**

> **Inherited constitution belongs to the organism. Evolutionary operators acting on organisms belong to the Lab.**

