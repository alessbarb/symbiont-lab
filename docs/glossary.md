# Glossary of Epistemological and Experimental Terms

## Experimental Hierarchy

- **Protocol:** A defined scientific procedure and measurement methodology (e.g. `attention.causal`, `evidence.second-look`). Independent of software versions.
- **Experiment:** A specific hypothesis-driven investigation bound to concrete parameters, hypotheses, and success criteria (e.g. `attention.causal.v0242-revalidation`).
- **Run:** A single deterministic execution of an experiment or protocol under a single world seed and parameter configuration.
- **Study:** A collection of comparable runs across parameter sweeps and replication seeds.
- **Campaign:** A sequential progression of studies guided by cumulative findings across regimes.
- **Audit:** An explicit empirical verification of the scientific integrity and methodological correctness of the simulator and laboratory apparatus itself.

## Artifact Status Lifecycle

- **WORKING:** Mutable local run or prototype results residing in `.symbiont/`. Not tracked in version control.
- **VALIDATED:** Run or study that has passed all protocol invariants, integrity assertions, and replication criteria.
- **FROZEN:** Formally accepted scientific record archived in `research/`. Immutable baseline for publications and future comparisons.
- **SUPERSEDED:** Historical study preserved in `research/` whose methodological premise was found flawed or refined by a subsequent audit.
