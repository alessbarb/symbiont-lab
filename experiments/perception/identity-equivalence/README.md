# Identity Sensory Bridge Equivalence

Checks that an identity receptor preserves the historical value path before adaptive claims are considered.

Protocol: `perception.identity-equivalence`.

Run:

```bash
symbiont-lab experiment run experiments/perception/identity-equivalence/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
