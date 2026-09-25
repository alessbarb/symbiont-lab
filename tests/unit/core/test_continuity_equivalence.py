"""L5.5 — individual persistence and physical continuity.

Formalizes the invariants a ``.symbiont`` checkpoint must satisfy for the
organism to genuinely continue existing across save/load: save/load must be
biologically neutral, restoring must reproduce the same future as never
stopping, restoring must not require a world, and checkpoint lineage must
let two restores of one checkpoint be recognized as a branch.
"""

from __future__ import annotations

import inspect

from symbiont.core.runtime import OrganismRuntime, _canonical_hash


def _fresh(organism_id: str = "continuity-subject") -> OrganismRuntime:
    return OrganismRuntime(
        organism_id=organism_id,
        min_samples=1,
        investigate_ticks=0,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )


def _restore(payload: dict) -> OrganismRuntime:
    return OrganismRuntime.from_checkpoint(
        payload,
        min_samples=1,
        investigate_ticks=0,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )


def test_state_hash_is_stable_across_repeated_queries():
    runtime = _fresh()
    runtime.run(10)
    assert runtime.state_hash() == runtime.state_hash()


def test_state_hash_query_does_not_advance_checkpoint_lineage():
    runtime = _fresh()
    runtime.run(5)
    runtime.state_hash()
    runtime.state_hash()
    first_real_checkpoint = runtime.checkpoint()
    assert first_real_checkpoint["checkpoint_lineage"]["parent_checkpoint_hash"] is None


def test_save_load_is_not_a_biological_event():
    """Guarding save()/load() neutrality (spec §25)."""
    runtime = _fresh()
    runtime.run(10)
    before = runtime.state_hash()

    restored = _restore(runtime.checkpoint())

    assert restored.state_hash() == before


def test_continuity_equivalence_continue_vs_save_then_load_then_continue():
    """The core continuity claim (spec §24): restoring must not be
    distinguishable, in outcome, from never having stopped."""
    baseline = _fresh()
    baseline.run(20)
    checkpoint = baseline.checkpoint()
    baseline.run(20)
    continued_hash = baseline.state_hash()

    restored = _restore(checkpoint)
    restored.run(20)

    assert restored.state_hash() == continued_hash


def test_checkpoint_lineage_chains_across_restore():
    runtime = _fresh()
    runtime.run(5)
    first = runtime.checkpoint()
    assert first["checkpoint_lineage"]["parent_checkpoint_hash"] is None

    restored = _restore(first)
    second = restored.checkpoint()

    assert (
        second["checkpoint_lineage"]["parent_checkpoint_hash"]
        == first["checkpoint_lineage"]["checkpoint_id"]
    )


def test_checkpoint_branching_from_same_parent_is_detectable():
    """Two independent restores of one checkpoint are a branch, not a
    forbidden duplicate (spec §16-17): both trace to the same parent, but
    diverging experience gives them distinct checkpoint identities."""
    runtime = _fresh()
    runtime.run(5)
    shared_checkpoint = runtime.checkpoint()
    parent_id = shared_checkpoint["checkpoint_lineage"]["checkpoint_id"]

    branch_a = _restore(shared_checkpoint)
    branch_b = _restore(shared_checkpoint)
    branch_a.run(3)
    branch_b.homeostasis.integrity = 0.4
    branch_b.run(3)

    a_checkpoint = branch_a.checkpoint()
    b_checkpoint = branch_b.checkpoint()

    assert a_checkpoint["checkpoint_lineage"]["parent_checkpoint_hash"] == parent_id
    assert b_checkpoint["checkpoint_lineage"]["parent_checkpoint_hash"] == parent_id
    assert (
        a_checkpoint["checkpoint_lineage"]["checkpoint_id"]
        != b_checkpoint["checkpoint_lineage"]["checkpoint_id"]
    )


def test_constitution_fingerprint_matches_recomputed_genome_hash():
    runtime = _fresh()
    payload = runtime.checkpoint()
    assert payload["constitution_fingerprint"]["genome_hash"] == _canonical_hash(payload["genome"])


def test_runtime_provenance_records_software_and_schema_version():
    import symbiont
    from symbiont.host.checkpoint import CHECKPOINT_SCHEMA_VERSION

    payload = _fresh().checkpoint()

    assert payload["runtime_provenance"]["software_version"] == symbiont.__version__
    assert payload["runtime_provenance"]["checkpoint_schema_version"] == CHECKPOINT_SCHEMA_VERSION


def test_direct_structural_damage_does_not_touch_cognition_before_any_sensing():
    """BODY-01: no structural fact reaches cognition except through an
    actual perception mechanism. Before any tick runs a sensing pipeline,
    directly damaging the physical body must leave BodySchema/SelfModel
    byte-identical to an undamaged twin."""
    healthy = _fresh(organism_id="lesion-twin")
    injured = _fresh(organism_id="lesion-twin")
    injured.homeostasis.integrity = 0.4

    assert injured.homeostasis.integrity != healthy.homeostasis.integrity
    assert injured.body_schema.export(current_tick=0) == healthy.body_schema.export(current_tick=0)
    assert injured.self_model.export(current_tick=0) == healthy.self_model.export(current_tick=0)


def test_lesion_survives_checkpoint_round_trip():
    runtime = _fresh()
    runtime.homeostasis.integrity = 0.4

    restored = _restore(runtime.checkpoint())

    assert restored.homeostasis.integrity == 0.4


def test_organism_runtime_construction_takes_no_world_reference():
    """World independence (spec §26): the organism must be constructible
    and restorable from a checkpoint without any World in scope."""
    params = inspect.signature(OrganismRuntime.__init__).parameters
    assert not any("world" in name.lower() for name in params)

    from_checkpoint_params = inspect.signature(OrganismRuntime.from_checkpoint).parameters
    assert not any("world" in name.lower() for name in from_checkpoint_params)


def _reproduction_genome():
    import json
    from dataclasses import replace
    from importlib import resources

    from symbiont.cognition.genome import GenomeCodec

    payload = json.loads(
        resources.files("symbiont.cognition").joinpath("defaults/base-genome.json").read_text()
    )
    return replace(GenomeCodec().load(payload), kernel_compatibility=">=0.79")


def test_reproduction_preserves_lineage_across_checkpoint_without_experience():
    """Genealogy (spec §29): a born child's generation/lineage survive a
    checkpoint round-trip, and it never inherits the parent's acquired
    cognitive experience."""
    from symbiont.core.birth_authority import HabitatBirthAuthority

    authority = HabitatBirthAuthority(habitat_id="continuity", capacity=2)
    parent = OrganismRuntime(
        organism_id="lineage-parent",
        genome=_reproduction_genome(),
        birth_authority=authority,
        bootstrap_semantic_senses=False,
        discover_senses=False,
    )
    parent.run(5)
    parent.living_body_state.growth_progress = 1.0

    child = parent.materialize_clonal_bud()
    assert child is not None

    restored_child = _restore(child.checkpoint())

    assert restored_child.generation == parent.generation + 1
    assert restored_child.living_body_state.growth_progress == 0.0
    # The child never ran a tick of its own: no parental experience carried
    # over into its narrative/evidence history.
    assert restored_child.tick_count == 0
    assert restored_child.checkpoint()["narrative_journal"] == []
    assert parent.checkpoint()["narrative_journal"] != []
