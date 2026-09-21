# Repository Guidelines

## Scope

Symbiont Lab is a Python 3.11+ research monorepo containing two decoupled packages:

- **`symbiont`** (Research Subject): cognition, synthetic ecology, simulation and a consent-bound local-host organism runtime.
- **`symbiont_lab`** (Scientific Apparatus): experiments, studies, archive, CLI and passive visualization.

The local-host direction is intentionally developmental: Symbiont may discover bounded, aggregate, read-only signal surfaces, assign them opaque identities, learn their statistical behavior and usefulness, and decide which ones deserve routine attention. Cognition must not be handed platform semantics when it can learn from the signal itself.

## Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

symbiont-lab simulate --hosts 100 --steps 300 --seed 7
symbiont-lab organism run --ticks 20
symbiont-lab organism live
symbiont-lab dashboard --port 8765
python observatory/resident.py --interval 15
```

## Experimental integrity

Ground truth belongs exclusively to the simulator/evaluator. Agents and reasoning may use only observations, local memory, collective reports, coarse fingerprints and derived trust. Evaluator-only metrics must never feed back into organism decisions. `symbiont` must never import or depend upon `symbiont_lab`.

## Safety boundaries

Real-host code is limited to explicit, local, least-privileged, read-only aggregate observation. It must not collect identity or user-content metadata. Autonomous discovery is restricted to vetted observation surfaces and may never broaden itself into arbitrary filesystem traversal, process content inspection, credentials, network scanning, peer discovery or permission seeking.

A **transparent resident lifecycle is allowed** when explicitly installed by the host owner: foreground/user-service execution, bounded periodic checkpoints, clean SIGINT/SIGTERM shutdown and `systemd --user` supervision are in scope. It must never install itself, hide, evade removal, escalate privileges or modify unrelated OS state.

Keep pathogens, reporters and interventions synthetic. Do not introduce network scanning/exchange, propagation, stealth/evasion, exploitation, credential access, quarantine/remediation or autonomous real-world actions. The reasoning layer must not generate or execute real system actions.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
