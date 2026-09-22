# Prospective Agency v1 (L8)

Status: implementation in progress.

## Scientific question

Can an embodied Symbiont choose among actions it discovered itself by using its
private world model to predict consequences and by preferring only consequences
that its own experience associated with lower physiological disequilibrium?

A positive result requires causal improvement over matched controls. Reaching a
laboratory resource once is not sufficient evidence.

## Non-goals

L8 does not provide:

- resource identity, coordinates, direction or distance;
- locomotion, gait, anatomy or target labels;
- experimenter reward;
- inverse kinematics or hand-authored motor sequences;
- a world-model-generated action vocabulary;
- multistep planning in v1.

## Architectural boundary

The causal stack is:

```text
SensorimotorLearner
    discovers what the organism can reproducibly do
        ↓
CognitiveGraph
    admits an opaque primitive readout under ordinary structural scarcity
        ↓
Private SLM
    predicts an opaque consequence for an admitted action
        ↓
OutcomeValueLedger
    estimates historical endogenous value of that consequence
        ↓
ProspectiveAgency
    chooses or abstains
        ↓
OrganismRuntime
    executes through SensorimotorLearner
        ↓
environment/body
    supplies the real consequence
```

No module under `symbiont/agency` may import `symbiont_lab` or
`symbiont_world`. Evaluator-only metrics such as resource distance and
resource progress may be observed by the laboratory but never enter
prospective selection.

## Action candidates

A v1 candidate is an opaque motor primitive.

A primitive may be considered only when:

1. SensorimotorLearner currently classifies it as a competence.
2. Its primitive readout has actually been admitted into CognitiveGraph.
3. No primitive is already being executed atomically.

Sensorimotor competence alone is insufficient. Prospective agency cannot bypass
cognitive structural admission.

Candidate order is deterministic and bounded. Controllability remains a local
competence gate; it is not converted into prospective utility.

## Private causal action tokens

Observed primitive execution is represented as:

```text
action.primitive.<opaque-digest>
```

The digest is acquired by the organism and contains no anatomical or task
semantics.

Ordinary non-primitive motor activity retains:

```text
action.motor.composite
```

The same action token used in observed private experience is used for
counterfactual inference.

## Counterfactual inference

Only an ACTIVE private model may govern prospective choice. SHADOW models never
do.

Counterfactual inference is non-mutating:

```text
current private context
+ candidate action token
    ↓
ACTIVE Private SLM
    ↓
predicted opaque outcome
```

A counterfactual prediction:

- is not an ExperienceRecord;
- is not training evidence;
- does not mutate the experience ledger;
- cannot directly change model state.

The current context uses the same private token vocabulary as observed training
episodes. L8 must not query the model using evaluator-only or separately
invented cognition-only tokens.

## Endogenous outcome value

The organism maintains a bounded OutcomeValueLedger.

For an independently observed action consequence:

```text
observed opaque outcome at t
        ↓
future physiological disequilibrium at t+h
        ↓
value = deviation(t) - deviation(t+h)
```

Positive values mean the observed consequence was historically followed by
improved internal viability. Negative values mean deterioration.

Current horizons are bounded and discounted:

- +4 ticks: 1.00
- +16 ticks: 0.85
- +64 ticks: 0.65
- +256 ticks: 0.40

Critical invariant: predicted outcomes never receive learning credit merely
because they were predicted. Value learning is scheduled only from independently
observed outcomes after real actions.

The ledger is bounded to 256 opaque outcome entries and uses online sufficient
statistics.

## Deliberation

For each admitted candidate, L8 obtains:

- predicted outcome;
- private-model confidence;
- historical value estimate for that outcome;
- value confidence derived from real samples.

P0 utility is deliberately simple and auditable:

```text
utility =
    mean endogenous outcome value
    × value confidence
    × model confidence
```

The policy may abstain because of:

- no candidate;
- no ACTIVE model;
- no value evidence;
- insufficient prediction confidence;
- insufficient decision margin;
- exhausted bounded query budget;
- terminal physiology.

Abstention falls back to the pre-existing cognitive/babbling path.

## Metabolic cost

Prospective inference is not free.

The constitutional PhysiologyConfig defines a bounded query cost and a maximum
candidate count. Cost is charged inside the organism runtime and contains no
task-specific term.

## Execution and persistence

ProspectiveAgency chooses only an opaque primitive id. It never emits actuator
vectors.

SensorimotorLearner remains the sole authority that maps primitive identity to
its learned temporal motor sequence.

An already-started primitive remains atomic and completes before a new
prospective deliberation.

## Checkpoint semantics

Persist:

- OutcomeValueLedger;
- prospective-agency schema/version;
- constitutional limits through normal physiology configuration.

Do not persist:

- pending counterfactual queries;
- incomplete deliberation;
- pending delayed value traces;
- private causal frame crossing a restart.

A schema/root mismatch fails closed. An individually corrupt bounded
OutcomeValueLedger entry may be skipped while preserving valid entries.

## Telemetry

Physics3D may expose, passively:

- prospective decision reason;
- candidate/query count;
- selected opaque primitive id;
- predicted opaque outcome;
- model confidence;
- learned outcome value and confidence;
- value sample count;
- decision margin;
- deliberation metabolic cost;
- number of known outcome-value entries;
- prospective motor-origin count.

These fields never feed back into the organism.

## Experimental controls

The preregistered comparison set for v1 is:

1. full prospective agency;
2. no-counterfactual control;
3. shuffled-model-action control;
4. shuffled-outcome-value control;
5. babbling-only control.

World/body/physics duration and matched seeds must remain identical within each
comparison block.

## Falsification gates

### Gate A — readiness

At least one competence must receive a primitive readout and become a legal L8
candidate.

### Gate B — counterfactual discrimination

In one current context, at least two admitted actions must be capable of
producing distinguishable model predictions or confidence/value estimates.

### Gate C — grounded value

Outcome value must appear only after real observed consequences and subsequent
physiological change. Counterfactual-only trials must leave value unchanged.

### Gate D — endogenous choice

Changing only organism-owned current context or physiological state may change
prospective selection without evaluator input.

### Gate E — causal benefit

Across preregistered seeds, the full condition must show better future
homeostatic outcome than shuffled/no-counterfactual controls. Mere extra motor
activity does not satisfy this gate.

### Gate F — embodied ecological effect

Only after A-E pass may Physics3D evaluate external measures such as survival,
contact or resource acquisition. Those measures remain evaluator-side.

### Gate G — readaptation

After an externally imposed ecological relocation/change, behaviour must
readapt from sensed consequences rather than rely on hidden coordinates or a
fixed target policy.

## v1 depth

Prospective Agency v1 is one-step only.

No rollout tree, MCTS, trajectory search or multistep planner is part of L8 v1.
Depth greater than one requires a separate preregistered extension after v1
passes causal controls.

## Claims explicitly not supported

Even a successful L8 v1 would not by itself establish consciousness, general
intelligence, symbolic planning, human-like intention, or understanding of
"food", "walking", "distance" or "survival".

It would establish a narrower falsifiable claim: an organism-owned learned
world model and organism-owned physiological value can causally influence
selection among organism-discovered actions without evaluator semantics.
