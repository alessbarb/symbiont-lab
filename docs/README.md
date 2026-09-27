# Symbiont documentation

The canonical scientific description of the current organism starts at **[`docs/symbiont/index.md`](symbiont/index.md)**.

That corpus is written as one connected work: it explains the organism from its epistemic foundations and domain boundaries down to runtime order, causal chains, state ownership, implementation anchors and experimental evidence. It is the recommended entry point for researchers who did not participate in the design of the project.

The rest of `docs/` remains intentionally available because it contains the source material from which the canonical description is maintained:

- `design/` contains specifications, implementation audits and research proposals. A specification records intended design; it must not be read automatically as a statement about current behaviour.
- `explanation/` contains earlier explanatory treatments and the mathematical compendium.
- `adr/` records accepted architectural decisions and their context.
- `methodology/` and `design/experimentation/` describe experimental practice and individual protocols.
- `history/`, `roadmap.md` and `CHANGELOG.md` preserve development history.
- `development/` documents engineering concerns that are useful to maintainers but are not part of the scientific description of the organism.

No historical source has been removed simply because a canonical synthesis now exists. The canonical corpus includes a [`source-map`](symbiont/source-map.md) that accounts for every Markdown source in the current documentation set and indicates the scientific area into which its knowledge belongs.

## Which source should I trust?

Use the following distinction:

| Need | Source |
|---|---|
| Understand how the present organism works | `docs/symbiont/` |
| Verify the exact current implementation | `src/` and tests |
| Understand intended or proposed design | `docs/design/` |
| Evaluate an empirical claim | experiment/study artefacts and their protocol |
| Understand why an architectural decision was made | `docs/adr/` |
| Reconstruct historical evolution | `docs/history/`, roadmap and changelog |

When these sources disagree, the disagreement is scientifically relevant and should be documented rather than silently normalised.
