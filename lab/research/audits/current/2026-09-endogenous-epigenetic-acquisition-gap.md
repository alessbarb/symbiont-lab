# P0 finding — acquired epigenetic inheritance has no endogenous source

Status: **confirmed, open**

Baseline: `f5bf57579ab3724f91216e37b8c0c6045944132b`

## What is now functional

Canonical genotype -> phenotype expression is wired for the currently supported
operative loci:

```text
SymbiontGenome.learning_rate
  + GermlineState mark
        ↓
Symbiont.learning_rate
        ↓
SensorimotorModel.learning_rate

SymbiontGenome.exploration_rate
  + GermlineState mark
        ↓
Symbiont.exploration_rate
```

Therefore genetic mutation/recombination and inherited epigenetic marks can now
change the actual cognitive phenotype.

## Remaining gap

There is still no endogenous lifetime process that changes a regulable
expression state and then captures that change into `GermlineState`.

Repository facts:

- `GermlineState.capture_acquired_variation()` exists;
- it is exercised by unit tests;
- the canonical `Symbiont` lifecycle does not call it;
- `learning_rate` and `exploration_rate` are currently expressed at birth
  and remain fixed during ordinary lifetime execution;
- therefore a canonical organism cannot yet autonomously generate a new
  epigenetic mark from its own lived experience.

## Consequence

The architecture currently supports:

```text
genetic inheritance                 YES
epigenetic mark transmission        YES
epigenetic mark phenotypic effect   YES
endogenous acquired mark creation   NO
```

So claims of Lamarck-like acquired inheritance are premature in the canonical
embodied runtime.

## Constraint on remediation

Do **not** call `capture_acquired_variation()` periodically with unchanged
constructor values merely to make the path execute.

A valid remediation first needs a legitimate internal regulatory mechanism that
can alter expression during lifetime without World/Lab semantics or evaluator
fitness signals.

Candidate scientific mechanism:

```text
experienced internal prediction dynamics
        ↓
bounded metaplastic regulation
        ↓
persistent expression shift
        ↓
germline capture
```

but this mechanism must be designed and falsified independently; it must not be
introduced as an ad-hoc way to make inheritance tests pass.
