# CLAUDE.md

Guidance for coding agents working in Symbiont Lab.

## Scope

Symbiont Lab is a Python 3.11+ research prototype evolving from a synthetic ecology into a benevolent digital organism on a **consenting local host**. Real-host capability is deliberately narrow: local, aggregate, read-only and least-privileged.

The project owner has explicitly approved two further boundaries:

1. **developmental sensing** — Symbiont may discover numeric observation surfaces inside bounded, vetted OS virtual interfaces, assign them opaque identities, characterize them statistically, learn their usefulness and select a bounded sensory repertoire without being handed platform semantics;
2. **transparent residence** — Symbiont may run continuously as an ordinary user process, persist bounded abstract checkpoints, recover after restart and be supervised by an explicitly installed `systemd --user` unit. It may never install itself, conceal itself, resist removal, elevate privileges or modify unrelated system state.

Still unconditionally prohibited: network scanning or autonomous peer discovery, propagation, stealth/evasion, exploitation, credential access, arbitrary filesystem traversal, collection of user content or identifying metadata, quarantine/remediation, autonomous host writes/actions, or reasoning that generates/executes real system actions.

## Real perception invariants

- Consent and resource limits are checked continuously.
- Providers may inspect only vetted aggregate observation surfaces; they never expose paths, usernames, command lines, addresses, file contents or other host identity/user content to cognition.
- Cognition consumes normalized readings/percepts, never OS APIs.
- Platform providers never import cognition.
- Candidate signals begin semantically unknown. Meaning/utility should be learned from behavior where possible rather than encoded in sensor names.
- Candidate discovery is bounded; only learned, selected senses enter routine cognition.
- Raw telemetry is not persisted. Checkpoints contain bounded descriptive/learned state only.
- Failure of one provider cannot stop the organism.
- No threat conclusion is made during initial sensory acclimation.
- Observatory remains passive: organism state may flow outward for display; the display does not control cognition.

Stop for an explicit owner decision before adding a new permission class, identifying/user-content collection, network exchange, unbounded overhead, privilege changes or any new real-world action boundary.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab organism run --ticks 20
symbiont-lab organism live
python observatory/resident.py --interval 15
symbiont-lab dashboard --port 8765
```

## Architecture

Two epistemologically decoupled packages live under `src/`:

- **`symbiont`** — organism/research subject: cognition, host boundary, environment and simulation.
- **`symbiont_lab`** — scientific apparatus: experiments, studies, archive, CLI and evaluation.

`observatory/` is a passive local viewer/adapter. **`symbiont` never imports `symbiont_lab` or Observatory.** Ground truth belongs exclusively to evaluator/apparatus and never feeds back into cognition. Preserve the AST dependency tests enforcing these boundaries.

### Host development

`host/contracts.py` defines permission/capability boundaries. `host/providers/` may discover/sample platform surfaces. `host/adaptive.py` is the semantic-free developmental layer: it sees opaque safe candidates, learns statistical usefulness and chooses which become senses. `core/runtime.py` wires selected senses into cognition. `core/resident.py` supplies a visible foreground lifecycle with periodic atomic checkpointing and clean shutdown.

### Deterministic synthetic research

Synthetic experiments continue to use namespaced RNG streams from `environment/rng.py`; ground truth stays evaluator-side. Existing experimental-integrity and historical regression tests remain authoritative. Real-host features must not perturb synthetic same-seed reproducibility.

### Persistent state

Persistent organism state is allowed only as explicit local abstract memory. Use the checkpoint API and atomic writes; never persist raw sensor histories. The provided systemd unit is an owner-installed user service, not self-installing persistence.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
