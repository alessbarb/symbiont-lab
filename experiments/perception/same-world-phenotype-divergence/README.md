# Same-World Sensory Phenotype Divergence

Measures convergence or divergence among organisms exposed to the same world without privileging either outcome.

Protocol: `perception.same-world-phenotype-divergence`.

Run:

```bash
symbiont-lab experiment run experiments/perception/same-world-phenotype-divergence/experiment.toml
```

The evaluator may characterize outputs after they exist, but target labels,
expected roles and acceptance criteria never enter the organism.

No `results.json` is committed until a real execution completes. A negative,
null or convergent outcome remains a valid result.
