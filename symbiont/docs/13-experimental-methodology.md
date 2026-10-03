# Experimental methodology

Symbiont is not scientifically useful merely because it is complex. Its mechanisms have to be studied under controls that distinguish learning from drift, causality from correlation and organism behaviour from evaluator interpretation.

## Reproducibility first

An experiment should identify at least the code revision, configuration, seed, world, body, organism checkpoint, run length, intervention, metrics and stopping rule. If a result depends on a specific body contract or a particular historical checkpoint, that dependency belongs in the record.

## Pre-registration and release gates

Several current studies use preregistered criteria and explicit gates. This is good practice because it prevents a post-hoc metric from being selected only after a run happens to look interesting. A gate should say what observation would count as support, what would count against the hypothesis and what conditions make the run uninterpretable.

## Baselines and ablations

Learning claims should be compared against meaningful baselines. For predictive utility this may include persistence, mean or zero baselines. For action it may include unreconciled proposals, passive controls or plasticity-disabled conditions. Ablations should remove one causal mechanism at a time where possible.

## Causal integrity

The laboratory should never provide privileged information to the subject simply to make an experiment easier. Ground truth, evaluator labels and future outcomes must remain isolated unless the experiment intentionally exposes a corresponding signal through a declared channel.

## Negative results

A run that fails to establish a claimed advantage is scientifically useful. Documentation should preserve that distinction instead of rewriting the feature description as if success had been demonstrated. Existing agency audits are a good model: they distinguish implemented mechanism, observed outcome and causal claim.

## Longitudinal experiments

For re-embodiment, development and cultural transmission, one run is rarely enough. The unit of analysis may be a history spanning bodies, checkpoints or generations. Causal provenance and stable state identity are therefore experimental infrastructure, not merely debugging aids.

### Principal sources

- `docs/methodology/README.md`
- `docs/design/experimentation/*`
- `src/symbiont_lab/experiments/*`
- `src/symbiont_lab/evaluation/*`
- `src/symbiont_lab/kernel_characterization/*`
