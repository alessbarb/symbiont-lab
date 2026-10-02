---
name: scientific-investigation
description: Investigate organism behavior, causal anomalies, and state phenomena to determine what can be strictly supported by empirical evidence, actively seeking disconfirming evidence and declaring inconclusive when hypotheses cannot be distinguished.
---

# Symbiont Scientific Investigation Skill

## Purpose

Investigate questions, anomalies, regressions, state divergences, and observed phenomena across Symbiont, its embodiment, and its environment to determine **what can be strictly supported by the available evidence**.

The objective is not to write speculative explanations, make architectural excuses, or rationalize unexpected behavior.

The objective is to establish an empirical, evidence-grounded determination of what actually happened, what causal mechanisms produced the phenomenon, which hypotheses are ruled out, and which uncertainties remain unresolved.

---

# Operating Contract

When this skill is active, the agent MUST:

1. **Establish the exact scope of the question** before investigating;
2. **Identify the exact subject identity, revision, checkpoint, seeds, and execution context** being investigated;
3. **Reconstruct observable state and causal history** from primary evidence (checkpoints, journal traces, logs, test artifacts, AST, and code) rather than documentation claims;
4. **Formulate competing/rival hypotheses** rather than assuming a single plausible narrative;
5. **Actively seek disconfirming evidence against the preferred hypothesis** before accepting any explanation;
6. **Distinguish strictly between what is directly observed, what is causally inferred, and what is hypothesized**;
7. **Apply the exit rule for indistinguishability:** if available evidence cannot decisively discriminate between rival hypotheses, the report MUST conclude **INCONCLUSIVE**, explicitly rejecting the urge to pick the "most intuitive" or "most reasonable" explanation;
8. **Preserve negative and anomalous findings** as legitimate scientific findings rather than software bugs to hide or explain away;
9. **Identify the concrete missing empirical discriminator** that would be required to distinguish between remaining hypotheses.

The agent MUST NOT:

- declare a claim as "truth" when it is only consistent with the evidence;
- adopt a single hypothesis without formulating and testing alternative explanations;
- stop investigating as soon as an explanation "makes sense";
- treat class names, variable names, or comments as evidence of what runtime code actually does;
- treat documentation or roadmap goals as evidence of runtime reality;
- modify the organism or its state merely to make an investigation easier or to force an expected result;
- silently reconcile contradictory data points;
- treat a Graphify knowledge graph or code index as primary evidence (they are heuristic navigation aids, not empirical truth);
- choose an explanation based on aesthetic preference, cognitive plausibility, or developer intention.

---

# Normative Language

- **MUST / MUST NOT**: Mandatory operational invariant. Deviation is a breach of the scientific investigation protocol.
- **SHOULD / SHOULD NOT**: Default empirical practice. Deviation requires explicit justification grounded in available evidence.
- **MAY**: Optional investigatory technique to be used when context warrants.

---

# Use This Skill When

Use this skill when tasked with answering empirical or causal questions about the organism, including:

- investigating unexpected or anomalous organism behavior;
- investigating why a capability, concept, or memory disappeared or altered (e.g., across re-embodiment, checkpoint restoration, or tick horizon);
- determining whether genuine learning, causal attribution, or adaptation occurred versus baseline correlation or sensorimotor artifact;
- tracing the origin and causal provenance of a specific cognitive, physical, or sensory state;
- analyzing divergence between two seeds, two runs, or two checkpoint generations;
- evaluating whether an observed phenomenon originates in `src/symbiont` (subject), `src/symbiont_lab` (apparatus), `src/symbiont_world` (environment), or `observatory` (instrumentation);
- auditing a claimed capability against actual runtime execution traces;
- resolving contradictions between empirical runs and documented expectations.

---

# Do Not Use This Skill When

Do not use this skill as the primary workflow for:

- designing and running prospective formal experimental campaigns (use `scientific-experiment`);
- writing and restructuring canonical repository documentation (use `scientific-documentation`);
- profiling CPU/memory bottlenecks and benchmark limits (use `performance-investigation`);
- general routine coding, refactoring, or bug-fixing where no empirical scientific question is being investigated;
- publishing and governance enforcement (handled universally by `agentctl` and `AGENTS.md`).

---

# Core Investigation Workflow

```text
                  FORMULATE QUESTION
                          │
                          ▼
               ESTABLISH EVIDENCE SCOPE
          (Revision, Identity, Seeds, Ticks)
                          │
                          ▼
               RECONSTRUCT PHENOMENON
           (State, Journal, Traces, Code)
                          │
                          ▼
            FORMULATE COMPETING HYPOTHESES
               [ H1 ]    [ H2 ]    [ H3 ]
                          │
                          ▼
          SEEK DISCONFIRMING EVIDENCE
          (Active attempt to falsify each,
            especially the favored one)
                          │
                          ▼
              EVALUATE DISCRIMINATION
             /                      \
   Evidence discriminates     Evidence cannot discriminate
           │                                 │
           ▼                                 ▼
   SUPPORTED EXPLANATION              INCONCLUSIVE
   (with uncertainty & bounds)     (state missing discriminator)
```

---

## Phase 1: Formulate the Empirical Question

A scientific investigation must begin with an unambiguous, bounded question.

1. State the observable phenomenon:
   - What was observed?
   - In what artifact, log, checkpoint, or metric was it observed?
2. Avoid question-begging formulations:
   - *Poor:* "Why does learning fail in tick 500?" (assumes learning was expected or that failure is the correct description).
   - *Good:* "What causal chain accounts for the transition of the predictor weights to zero between tick 450 and 520?"

---

## Phase 2: Establish Evidence Scope and Provenance

Before inspecting code or data, fix the observational boundaries:

1. **Subject Identity:** Organism ID, genome hash, generation.
2. **Embodiment State:** Body type, active sensors, active actuators.
3. **Temporal Horizon:** Starting tick, terminal tick, sample frequency.
4. **Environment / Seed:** Exact seed(s), world parameters, boundary conditions.
5. **Code Revision:** Git commit hash at which the evidence was produced.
6. **Artifact Provenance:** Verify that the logs, checkpoints, or metrics were produced by the stated code and conditions without manual tampering or uncommitted modifications.

---

## Phase 3: Reconstruct Phenomenon and Observable State

Reconstruct what happened strictly from primary artifacts:

1. **State Inspection:**
   - Inspect checkpoint state directly (deserialized fields, shapes, tensor values, discrete indicators).
   - Verify continuous versus discontinuous changes across the horizon.
2. **Event & Journal Traces:**
   - Check organism sensory input at relevant ticks.
   - Check motor commands output at relevant ticks.
   - Check internal signals (homeostatic variables, prospective predictions, prediction errors).
3. **Execution Path Verification:**
   - Follow the execution path in the corresponding code revision.
   - Use Graphify (`graphify query`, `graphify path`) strictly as a heuristic guide to locate candidate components; then inspect source files directly.
   - Distinguish code that was actually executed from dead branches or fallback paths.

---

## Phase 4: Formulate Competing Hypotheses

Never proceed with a single hypothesis. Explicitly formulate at least two mutually exclusive or distinct mechanisms:

- **$H_0$ (Baseline / Artifact):** The phenomenon is an artifact of measurement, seed contingency, default initialization, zero-clamping, numerical underflow, or apparatus timing.
- **$H_1$ (Candidate Mechanism A):** The phenomenon is caused by mechanism $A$ (specify exact causal pathway and interacting variables).
- **$H_2$ (Candidate Mechanism B):** The phenomenon is caused by mechanism $B$ (specify exact causal pathway and interacting variables).

---

## Phase 5: Active Falsification of the Favored Hypothesis

This is the central discipline of the skill.

1. Identify which hypothesis is currently favored or seems most intuitive.
2. Ask: **"If this favored hypothesis were FALSE, what evidence would prove it?"**
3. Actively search for that disconfirming evidence:
   - Does a counterexample exist in another seed or tick range?
   - Did the supposed cause occur *after* the effect?
   - Was the supposed mechanism bypassed by a short-circuit, exception handler, or threshold clamp?
   - Is the observed change statistically indistinguishable from uncoupled noise or random walk?
4. If disconfirming evidence is found, reject or revise the hypothesis immediately. Do not rescue it with ad-hoc auxiliary assumptions unless those assumptions are independently tested.

---

## Phase 6: Discrimination and Exit Rules

Evaluate whether the available evidence can decisively discriminate between the remaining hypotheses:

### Rule 1: The Discrimination Standard
An explanation is **supported** if and only if:
1. Direct primary evidence supports its causal pathway; AND
2. The competing hypotheses are actively contradicted by empirical evidence; AND
3. The claim does not violate any constitutional invariant.

### Rule 2: The Inconclusive Exit Rule
If the available evidence is compatible with more than one competing hypothesis, and the data at hand cannot differentiate between them:
- The investigation **MUST conclude INCONCLUSIVE**.
- The agent **MUST NOT** pick the "most probable", "cleanest", or "intended" explanation.
- The agent **MUST** define the **missing empirical discriminator**: the exact test, probe, counterfactual execution, or telemetry that would be required to break the tie.

---

# Structure of an Investigation Report

When reporting the results of an investigation, format the report with these explicit sections:

```markdown
# Scientific Investigation: [Concise Title]

## 1. Empirical Question
- Exact question being addressed.
- Scope, organism identity, commit revision, and seeds investigated.

## 2. Reconstructed State & Evidence
- Primary evidence inspected (checkpoints, journal traces, metrics).
- Observable facts directly grounded in evidence (with exact line/tick/artifact references).

## 3. Competing Hypotheses Considered
- H0: [Baseline / Artifact]
- H1: [Mechanism A]
- H2: [Mechanism B]

## 4. Falsification & Evidence Analysis
- Tests/checks applied to disconfirm each hypothesis.
- Disconfirming evidence observed against H_x.
- Concordant evidence observed for H_y.

## 5. Conclusion & Determination
- [SUPPORTED: H_y] OR [INCONCLUSIVE].
- Exact degree of empirical support.
- If INCONCLUSIVE: specify why evidence cannot discriminate and what missing discriminator is needed.

## 6. Uncertainty & Boundary Conditions
- Limitations of current evidence scope.
- Unexamined seeds, ticks, or dimensions.
- Constitutional or ontological boundaries affected (if any).
```

---

# Epistemic Boundaries and Invariants

1. **Evidence vs. Intention:** What the original developer intended a class or function to do is historical context, never evidence of what it actually did.
2. **Evaluator Leakage:** In any investigation into organism knowledge or learning, verify that evaluator ground truth from `symbiont_lab` did not leak into the subject's state (Constitution §2).
3. **No Retrospective Rescuing:** A hypothesis that failed to predict the observed data is falsified for that scope. Do not rewrite its definitions after the fact without marking it as a new, distinct hypothesis.
4. **Reproducibility Check:** When making a claim about a deterministic trajectory, confirm whether running the same seed with the same initial state produces identical state traces (Constitution §14).
