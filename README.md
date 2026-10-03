# Symbiont Lab

## Experimental Artificial Life & Digital Organism Research

> What happens if software is not told what its world means, but is instead given bounded ways to sense, act, learn, remember and revise what it believes through experience?

Symbiont Lab is a research monorepo for a persistent digital organism and the scientific apparatus used to study it.

The project is currently in a **remediation and validation phase**, not in an open-ended capability-expansion phase.

## Current scientific state

The project-planning index is [`docs/roadmap.md`](docs/roadmap.md); the
scientific programme is governed separately in
[`docs/methodology/research-programme.md`](docs/methodology/research-programme.md).
The machine-readable project state is
[`docs/governance/project-state.toml`](docs/governance/project-state.toml).

| Programme | Current state |
| --- | --- |
| Experimental Organism v1 | frozen historical subject |
| Visual Acquisition D1-v2 | active immediate gate; development run in progress |
| Promotion Stability v1 | design data complete; confirmation paused |
| Scientific Infrastructure A1-A4 | next P0 work |
| E8 Label Invariance | P0 experimental-integrity failure; remediation required |
| Apparatus validity A5-A7 | P1 before causal redesign |
| Embodied Agency E1-E6 | negative falsification battery |
| General causal-agency model B0 | not started |
| Heredity E7 | positive bounded result; permanent regression |
| Re-embodiment | implemented; robustness/reacclimation remain research concerns |
| Culture / grounding | closed in bounded experimental scope; generalisation not established |
| Symbiont World | maintenance / experimental substrate only |
| New population capability work | blocked by Individual Readiness Gate |
| OOD / Sim-to-Real | future research; not demonstrated |
| AGI | not a roadmap milestone |

A capability being implemented does not establish scientific generalisation. A completed experiment remains bounded by its preregistered conditions.

## What Symbiont is

Symbiont is the **research subject**: a persistent organism-like software system whose internal state, sensing, cognition, learning, physiology, memory, agency and acquired models evolve over a lifetime under explicit limits.

The core scientific boundary is:

```text
World / Body / host phenomena
        |
        v
bounded opaque sensory surfaces
        |
        v
Symbiont experience and acquired structure
        |
        v
passive outward observation
        |
        v
Lab / Observatory / evaluator truth
```

Evaluator knowledge does not flow back into the subject.

## What Symbiont is not

The project does not claim that Symbiont is biologically alive, conscious, sentient or generally intelligent.

It is not a host-monitoring agent with biological terminology, a reinforcement-learning system with one global reward, an autonomous permission-seeking host agent, or a population platform whose complexity substitutes for unresolved individual causal competence.

AGI, consciousness, culture and Sim-to-Real are possible future interpretations of evidence, not development milestones.

## Architecture

The repository is five domains, each its own distribution in one uv workspace:

| Domain | Import package | Responsibility |
| --- | --- | --- |
| `symbiont/` | `symbiont` | the organism / research subject |
| `embodiment/` | `embodiment` | couplings between the organism and a concrete form of existence |
| `modality/` | `modality` | signal channels; no cognitive meaning |
| `environment/` | `environment` | external laws, dynamics and ground truth |
| `lab/` | `lab` | composition, experiments, studies, observation, analysis |

Normative dependency rule, enforced by
`tests/experimental_integrity/test_five_domain_architecture.py`:

```text
symbiont    -X-> lab, environment, modality, embodiment
environment -X-> symbiont, lab, modality, embodiment
modality    -X-> symbiont, embodiment, environment, lab
embodiment  -X-> lab

lab -> may depend on everything
```

Ground truth belongs to Lab/evaluator and must never become organism cognition.

## Scientific method

Software verification and scientific evidence are separate.

- `tests/` verifies software, contracts, boundaries and regressions;
- `tests/experiments/` verifies protocol/runner mechanics;
- `experiments/` contains explicit scientific campaigns;
- `research/` contains audits, interpretation and evidence;
- negative results are retained and are not rewritten when later work changes the mechanism.

Current embodiment evidence includes a unified falsification battery:

- E1 Yoked External Causation — H1 not supported;
- E2 Tool / Body Distinction — H1 not supported;
- E3 Temporal Causality — H1 not supported;
- E4 Causal Revision — H1 not supported;
- E5 Somatic Correlation Trap — H1 not supported;
- E6 Hidden Common Cause — H1 not supported;
- E7 Heredity Leakage — no learned-state leakage observed in tested scope;
- E8 Label Invariance — fails and is an open P0 integrity issue.

These results define the next causal research problem; they are not defects to edit away.

## Re-embodiment and identity

A Body is not a Symbiont. Changing or destroying a Body does not automatically destroy the organism.

Re-embodiment must preserve body-independent cognitive state. Body-specific knowledge may become uncertain and require revalidation; it must not be silently erased or reinterpreted.

A descendant is a new organism identity. Learned parental cognition is not germline inheritance.

## Host safety boundary

Real-host code is explicit, revocable, local, least-privileged and bounded.

It must not introduce arbitrary filesystem traversal, process-content inspection, credentials, network scanning/exchange, stealth/evasion, exploitation, hidden persistence, privilege escalation, self-installation, uncontrolled propagation or autonomous real-world remediation.

A transparent owner-installed resident lifecycle is allowed. Hard CPU, memory, storage, communication and population ceilings remain outside learned control.

## Agent governance

Intelligent coding agents are constrained by a repository governance layer:

- [Constitution](docs/governance/constitution.md)
- [Agent policy](docs/governance/agent-policy.md)
- [Decision gates](docs/governance/decision-gates.md)
- [Project state](docs/governance/project-state.toml)
- [Frozen artefacts](docs/governance/frozen-artifacts.toml)
- [Active work](docs/governance/active-work.toml)
- [Validation matrix](docs/governance/validation-matrix.toml)

Before modifying the repository, agents must read `AGENTS.md` or `CLAUDE.md` and run:

```bash
python scripts/agentctl.py status
python scripts/agentctl.py verify
```

Agents execute authorised work. They do not choose the scientific direction.

## Repository map

| Path | Purpose |
| --- | --- |
| `symbiont/` | research subject |
| `embodiment/` | bodies, apparatus adapters, re-embodiment |
| `modality/` | signal channels |
| `environment/` | world |
| `lab/src/lab/` | apparatus |
| `lab/src/lab/observatory/` | passive observation back-end |
| `lab/experiments/` | scientific campaigns |
| `lab/research/` | evidence and interpretation |
| `tests/` | mechanical verification |
| `migration/` | record of the move to this layout |
| `docs/design/` | designs and preregistrations |
| `docs/adr/` | architectural decisions |
| `docs/history/` | historical record |
| `docs/governance/` | repository and agent authority |

## Development

Python 3.12+:

```bash
uv sync --extra dev --extra physics3d
uv run pytest
```

Useful validation layers:

```bash
pytest tests/unit tests/docs tests/smoke
pytest -o addopts= tests/integration tests/experimental_integrity
pytest -o addopts= tests/contract tests/experiments
ruff check symbiont/src environment/src modality/src embodiment/src lab/src tests
ruff format --check symbiont/src environment/src modality/src embodiment/src lab/src tests
python scripts/agentctl.py verify
```

Scientific campaigns are explicit commands. They do not belong in the default developer loop.

## Core documentation

- [Technical architecture](docs/architecture.md)
- [Project roadmap](docs/roadmap.md)
- [Scientific programme](docs/methodology/research-programme.md)
- [Historical roadmap log](docs/history/roadmap-log.md)

## Documentation authority

Use this order when documents conflict:

1. accepted constitutional/ADR decisions;
2. current project planning in `docs/roadmap.md`, scientific direction in
   `docs/methodology/research-programme.md`, and governance project state;
3. frozen preregistration/design for the specific experiment;
4. current implementation contracts;
5. research interpretation;
6. historical documentation.

Historical results remain evidence for their original scope; they do not override current architectural authority.
