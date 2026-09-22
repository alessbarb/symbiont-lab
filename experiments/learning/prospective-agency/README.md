# Prospective Agency v1 causal controls

This experiment is the first causal validation stage for L8.

It deliberately separates **mechanism validity** from **embodied ecological
success**. The laboratory constructs a tiny opaque contingency with three
opaque acquired-action identities and three opaque outcomes. ProspectiveAgency
never receives the hidden evaluator mapping or evaluator-side future-value
score.

The five matched conditions are:

1. `full` — correct action→outcome model and learned outcome value;
2. `no_counterfactual` — no model-based action is selected;
3. `shuffled_model` — action identities are remapped to the wrong predicted outcomes;
4. `shuffled_value` — outcome-value correspondence is remapped;
5. `babbling_only` — seeded action choice independent from model/value evidence.

The mechanism gate asks whether the full L8 pathway selects the action whose
real hidden consequence has the best physiological value, whether choice
changes when only opaque context changes, and whether breaking either causal
link removes the advantage.

Passing this experiment does **not** demonstrate resource seeking, locomotion,
planning, consciousness or useful behavior in Physics3D. It establishes only
that the prospective agency mechanism is causally wired as specified.

Run through pytest:

```bash
pytest -q tests/integration/studies/test_prospective_agency_controls.py
```

The next stage is an embodied matched-condition study using the same five
conditions after a Physics3D subject naturally satisfies L8 readiness.
