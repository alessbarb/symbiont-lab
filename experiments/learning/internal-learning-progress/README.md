# L7.6 — Internal learning-progress validity

This study validates the signal that the organism is allowed to use for replay
stopping.

For each replay dose, the trainer exposes two strictly separated measurements:

- **private validation loss** — computed from the organism's own observed causal
  experience reserved from replay updates; this may be returned to the organism;
- **evaluator test loss** — computed from the untouched test split and never
  exposed to the organism.

The study asks whether *changes* in the private validation loss predict changes
in evaluator test loss across replay doses.

Run:

```bash
symbiont-lab experiment run experiments/learning/internal-learning-progress/experiment.toml
```

A positive result licenses private validation progress as an internal stopping
signal. It does not license exposing test loss or evaluator decisions.
