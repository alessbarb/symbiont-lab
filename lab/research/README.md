# Scientific evidence registry

`research/` is the repository's record of what was asked, run, observed and may
legitimately be concluded. It is not a second implementation package and it is
not a source of organism behaviour.

> Nothing executable lives under `research/`. Nothing under `research/` defines
> organism behavior. `research/` records what was asked, what was run, what was
> observed and what may legitimately be concluded.

## Repository boundaries

```text
docs/             architecture, design decisions and methodology
src/symbiont/     research subject / organism
src/symbiont_lab/ scientific apparatus and executable study code
experiments/      executable specifications, preregistrations and runners
research/         frozen evidence, audits, discovery records and QA
observatory/      passive observation
```

`research/` code that historically lived in this tree has been moved to
`src/symbiont_lab/studies/`. Historical reports may retain the paths used by the
original run; current code and tests must use the apparatus package.

## Evidence lifecycle

1. **Protocol** — define question, matrix, seeds, metrics and validity criteria.
2. **Execution** — write mutable run data to `.symbiont/runs/` or another
   explicitly disposable location.
3. **Study record** — preserve the executed protocol, result, manifest and
   limitations under `studies/`.
4. **Audit** — attack a claim or implementation independently under `audits/`.
5. **Discovery** — keep unconfirmed candidate phenomena separate from claims.

## Directory map

- [`studies/`](studies/) — scientific study records and frozen outcomes, grouped
  by research programme.
- [`audits/current/`](audits/current/) — current adversarial audits.
- [`audits/historical/`](audits/historical/) — commit-pinned historical audits;
  do not aggregate them into current evidence.
- [`discovery/`](discovery/) — observations that require independent follow-up.
- [`qa/`](qa/) — apparatus and Observatory validation records.
- [`protocols/`](protocols/) — research-method guidance and legacy protocol index.
- [`STATUS.md`](STATUS.md) — concise current evidence index.

## Epistemic statuses

Study records should distinguish implementation from evidence. Recommended
statuses are:

```text
PLANNED PREREGISTERED RUNNING DISCOVERY PARTIAL SUPPORTED NEGATIVE
INCONCLUSIVE SUPERSEDED FROZEN
```

A capability can be implemented while its evidence is negative or inconclusive.
Do not promote discovery observations to confirmed claims using the same data.
