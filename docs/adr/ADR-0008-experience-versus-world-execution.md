# ADR-0008: Experience versus World Execution (ADR-EW-001)

## Status

Accepted

## Context

*Experience & World Architecture Specification v1* (`docs/design/observability/symbiont-lab-experience-and-world-architecture-specification-v1.md`, and its gap analysis `…-v1-spec.md`) states the governing principle *Experience acquires capability. World integrates capability.* Before this decision the Lab launched every Physics3D run with the same undifferentiated `Physics3DLaunchSpec`. It could not say whether a run was a protected acquisition or a full-consequence World, and it recorded no termination reason.

## Decision

1. **Run kind (gap decision D1).** Every Lab run has exactly one `RunKind`:
   `acquisition.embodiment`, `acquisition.vision`, `world.challenge`, `world.open`.
   The kind is a Lab/apparatus concept (`symbiont_lab.experience`). It is never cognition-visible: it does not enter the organism checkpoint, the `EmbodimentContract` or any signal.
2. **Run definition.** A versioned, immutable `RunDefinition` names the kind, the environment recipe and the observer-only scientific purpose. Challenge Worlds add observer-only *situations*, which are regions or conditions with a stated purpose. Situation identifiers, purposes and definition identifiers never reach the engine: the engine receives only the environment recipe name.
3. **Acquisition protection (gap decision D2).** Acquisition runs *terminate before irreversible viability loss*; they do not repair the body invisibly. The protected boundary is the physiological onset of severe resource pressure (`VitalState.AGONIZING` or physiological `DORMANT`), which precedes `DEAD`. Crossing it ends the run with `protected_recovery`, and the causal checkpoint stays coherent. The policy only stops the run. It never modifies action choice, reward, evidence or relation confidence. If a body dies inside an acquisition run anyway (pressure jumping straight to unrecoverable), the run ends `body_non_viable` and the manifest records a protection breach. The breach is never masked.
4. **World consequence completeness.** World runs apply no protection. Body death ends the run with `body_non_viable`. The canonical runtime closes the `EmbodimentEpisode` with `BODY_DEATH` and persists the Symbiont as dormant. No replacement body appears during the same run; re-embodiment is a new run with a fresh body and a new embodiment epoch.
5. **Termination taxonomy.** Every run records one reason, chosen from `time_budget_reached`, `evidence_window_complete`, `operator_stop`, `experimental_condition_complete`, `protected_recovery`, `technical_failure` (acquisition) and `body_non_viable`, `world_duration_complete`, `operator_stop`, `technical_failure` (World). `won` and `lost` are not lifecycle states.
6. **Default.** A launch payload with no definition keeps the exact pre-ADR semantics: an open World run with no protection, in which death already ended the loop.
7. **Vision is not launchable** until a causal `VisualApparatus` exists (ADR-EW-004, pending). The catalog marks it unavailable and the launch path rejects it.

## Consequences

- The Lab can state truthfully whether it is executing an Embodiment acquisition or a World run. Symbiont's causal behaviour is unchanged.
- The protection check reads only `Tick3D.alive` and the physiological vital state, both of which are computed on every causal tick whether or not observation is enabled.
- Researcher purposes stay in run manifests (observer apparatus) and never in organism state.

## Introduced in

Milestone EW-A.
