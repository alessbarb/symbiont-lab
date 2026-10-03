"""Explicit laboratory orchestration; organisms never construct descendants.

This adapter reads inherited constitution from the current runtime. It never
copies the parent's checkpoint, learned graph, models, or experience.
"""

from __future__ import annotations

from typing import Any

from lab.reproduction.authority import HabitatBirthAuthority
from symbiont.cognition.birth import load_base_graph
from symbiont.core.embodiment.metabolism import MetabolicLedger
from symbiont.core.embodiment.physiology import LivingBodyState
from symbiont.core.orchestration.runtime import OrganismRuntime
from symbiont.modeling.culture import SocialEvidenceLedger
from symbiont.modeling.runtime import ModeledOrganismRuntime
from symbiont.modeling.sequences import SequenceGroundingLedger
from symbiont.modeling.symbols import SymbolGroundingLedger


def materialize_clonal_bud(
    parent: OrganismRuntime,
    *,
    authority: HabitatBirthAuthority,
    body_schema: Any = None,
) -> OrganismRuntime | None:
    """Materialize one asexual descendant from conserved parental energy.

    Readiness is purely physiological.  No cognitive topology, learned
    competence, blocked growth, reward or evaluator score participates.
    World/habitat authority may deny materialization, but cannot create
    readiness.
    """
    if (
        parent._genome is None
        or not parent._ontogeny.reproductively_ready()
        or not _birth_surfaces_available(parent)
    ):
        return None

    child_genome_id = parent._genome.genome_id
    record = authority.birth(
        genome_id=child_genome_id,
        parent_ids=(parent._organism_id,),
        generation=parent._generation + 1,
    )
    if record is None:
        return None

    birth_energy = parent._ontogeny.reproduction_energy()
    child_genome = parent._genome
    child_state = LivingBodyState(
        energy_reserve=birth_energy,
        max_energy=parent._living_body_state.max_energy,
        growth_progress=0.0,
        senescence=0.0,
    )
    parent_metabolism = parent._metabolism.snapshot()
    parent_metabolism_checkpoint = parent._metabolism.checkpoint()
    child_metabolism = MetabolicLedger(
        capacity=dict(parent_metabolism.capacity),
        replenishment=dict(parent_metabolism_checkpoint["replenishment"]),
        physiology_config=parent._physiology_config,
        body_state=child_state,
    )
    graph = load_base_graph(kernel_limits=parent._kernel_limits)

    modeled = isinstance(parent, ModeledOrganismRuntime)
    model_kwargs: dict[str, Any] = {}
    if modeled:
        model_kwargs = {
            "body_schema": body_schema,
            "model_request_base_cost": parent._model_request_base_cost,
            "model_storage_scale": parent._model_storage_scale,
            "cultural_policy_seed": parent._cultural_policy.seed,
            "cultural_policy_config": parent._cultural_policy.config,
            "symbol_policy_seed": parent._symbol_policy.seed,
            "symbol_space": parent._symbol_policy.symbol_space,
            "symbol_grounding_ledger": SymbolGroundingLedger(record.organism_id),
            "sequence_grounding_ledger": SequenceGroundingLedger(record.organism_id),
            "sequence_max_length": parent._sequence_max_length,
            "social_evidence_ledger": SocialEvidenceLedger(record.organism_id),
        }
    elif body_schema is not None:
        authority.death(record.organism_id)
        raise ValueError("body_schema requires a modeled parent")
    runtime_type = type(parent) if modeled else OrganismRuntime
    try:
        child = runtime_type(
            **model_kwargs,
            attention_budget=parent._attention_budget,
            investigate_ticks=parent._investigate_ticks,
            conflict_z=2.0 if modeled else parent._conflict_z,
            min_samples=5 if modeled else parent._min_samples,
            discover_senses=parent._discover_senses,
            bootstrap_semantic_senses=parent._bootstrap_semantic_senses,
            sensory_system=parent._sensory_system.germinal_copy(),
            genome=child_genome,
            mutation_seed=parent._mutation_seed + parent._generation + 1,
            epigenetic_priors=parent._epigenetic_priors,
            epigenetic_decay=parent._epigenetic_decay,
            kernel_limits=parent._kernel_limits,
            cognitive_graph=graph,
            host_lifecycle=parent._lifecycle.fork_for_child(),
            persist_replay_state=parent._persist_replay_state,
            physiology_config=parent._physiology_config,
            metabolism=child_metabolism,
            living_body_state=child_state,
            organism_id=record.organism_id,
            generation=record.generation,
            social_habitat=None,
            resource_habitats=parent._resource_habitats,
            explicit_metabolism=parent._explicit_metabolism,
            social_exchange_quantum=parent._social_exchange_quantum,
            social_exchange_cost=parent._social_exchange_cost,
            interoception_enabled=parent._interoception_enabled,
            interoception_mode=parent._interoception_mode,
            **(
                {}
                if modeled
                else {
                    "actuation_enabled": parent._actuation_enabled,
                    "motor_selection_threshold": parent._action_domain.selection_threshold,
                }
            ),
        )
    except Exception:
        authority.death(record.organism_id)
        raise

    # Conservation boundary: the child's initial physical energy is exactly
    # the energy removed from the parent.  No birth-energy minting.
    parent._metabolism.charge("maintenance", birth_energy)

    if parent._social_habitat is not None:
        child.join_social_habitat(parent._social_habitat)
    if isinstance(child, ModeledOrganismRuntime) and (
        child.model_registry.records
        or child.experience_ledger.records
        or child.experience_archive.records
        or child.symbol_grounding_ledger.exposures
        or child.symbol_grounding_ledger.associations
        or child.sequence_grounding_ledger.exposures
        or child.sequence_grounding_ledger.associations
    ):
        raise RuntimeError("acquired model/experience inheritance invariant violated")
    return child


def _birth_surfaces_available(parent: OrganismRuntime) -> bool:
    """Preflight external carrying-capacity surfaces only.

    Physical birth energy is transferred from the parent. Shared habitat
    resource quantities are not a second reproductive currency.
    """
    surfaces = list(parent._resource_habitats.values())
    if parent._habitat is not None:
        surfaces.append(parent._habitat)
    return all(surface.snapshot().population < surface.capacity for surface in surfaces)
