# ADR-0062 — Closed Results Condition One Canonical Organism Profile

- **Status:** Accepted
- **Date:** 2026-10-02
- **Decision owner:** project owner
- **Relates to:** Constitution (Golden Invariant), ADR-0043, `docs/design/core/canonical-organism-profile-v1.md`, `src/symbiont/core/organism_profile.py`
- **Scope:** How scientific results reach organism configuration, and where that configuration is defined. This ADR changes no organism behavior by itself.

## Context

A review of closed results against code defaults found that results were applied
per launcher. The bare constructor, the resident, Physics3D, World and the
integrated habitat each configured the same organism differently: sensory
plasticity and predictor auto-promotion only in Physics3D, interoception absent
in three scopes and enabled in two, semantic senses on in three and off in two.
A result could be "applied" and still not hold for most organisms. One frozen
protocol ran its development stage with an undeclared non-default option.

## Decision

1. There is one canonical organism profile. Every scope builds organisms from it.
2. The profile is versioned. A version is immutable once an experiment has run
   under it; closed experiments stay bound to their version.
3. Only a study arm may deviate from the profile, as an intervention declared in
   its protocol. Launchers may not. A gate fails on undeclared deviations.
4. Only a closed, preregistered, multi-seed confirmatory or held-out result moves
   a value. Exploratory and single-run results are candidates.
5. Every closed result records a configuration consequence in the register:
   adopt, reject, no change with reason, or pending behind named work.
6. The experiment determines the value; a value is never set so that an
   experiment passes. The Golden Invariant is unchanged.
7. The test suite describes the organism as it is now. A change that makes a
   test obsolete cleans it in the same change: the test is migrated to the
   canonical organism if its mechanism still exists, or archived as superseded,
   naming its canonical replacement, outside the canonical run
   (`tests/README.md`, "Superseded tests"). (Owner amendment 2026-10-03.)

## Consequences

- Converging the five current configurations changes the behavior of existing
  launchers. It is done as a new profile version, not by editing the historical
  one, and is classified by `agentctl` on its own.
- Results obtained under an older version are historical for that version and
  are not rewritten.
- The register is owner-approved content: changing a value there is a decision,
  backed by a result, not an implementation detail.

## Alternatives rejected

- **Automatic adoption of any result.** A single run or an exploratory finding
  would reconfigure every organism.
- **Changing constructor defaults in place.** Closed experiments that relied on
  them would silently stop being reproducible.
- **Per-launcher configuration with documentation.** That is the situation this
  ADR ends.
