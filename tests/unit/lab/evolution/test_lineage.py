from __future__ import annotations

import pytest

from symbiont_lab.evolution.lineage import LineageArchive, LineageRecord


def _record(genome_id: str, parent_ids: tuple[str, ...] = (), generation: int = 0) -> LineageRecord:
    return LineageRecord(
        genome_id=genome_id,
        parent_ids=parent_ids,
        genome_hash=f"hash-{genome_id}",
        created_at_generation=generation,
    )


def test_record_and_retrieve_a_single_entry():
    archive = LineageArchive()
    archive.record(_record("root"))
    assert archive.ancestors_of("root") == ()


def test_duplicate_genome_id_is_rejected():
    archive = LineageArchive()
    archive.record(_record("root"))
    with pytest.raises(ValueError):
        archive.record(_record("root"))


def test_ancestors_of_walks_transitive_chain():
    archive = LineageArchive()
    archive.record(_record("grandparent", generation=0))
    archive.record(_record("parent", parent_ids=("grandparent",), generation=1))
    archive.record(_record("child", parent_ids=("parent",), generation=2))

    ancestors = archive.ancestors_of("child")
    assert [entry.genome_id for entry in ancestors] == ["parent", "grandparent"]


def test_dangling_parent_id_is_rejected():
    archive = LineageArchive()
    with pytest.raises(ValueError):
        archive.record(_record("child", parent_ids=("never-recorded",)))


def test_self_referential_parent_is_rejected():
    archive = LineageArchive()
    with pytest.raises(ValueError):
        archive.record(_record("root", parent_ids=("root",)))


def test_cyclic_parent_chain_is_rejected_as_a_dangling_parent():
    # "a" -> "b" -> "a" requires "b" to exist before "a" does, which the
    # missing-parent check above already forbids -- rejecting dangling
    # parents subsumes direct cycle rejection for the public API.
    archive = LineageArchive()
    with pytest.raises(ValueError):
        archive.record(_record("a", parent_ids=("b",)))


def test_would_create_cycle_detects_an_indirect_cycle():
    # Exercises _would_create_cycle directly for a longer (A->B->C->A)
    # shape, since record()'s missing-parent gate now always intercepts
    # a genuinely cyclic attempt before this check would ever fire via
    # the public API -- this is what the adversarial audit specifically
    # asked to confirm still works.
    archive = LineageArchive()
    archive.record(_record("a"))
    archive.record(_record("b", parent_ids=("a",)))
    archive.record(_record("c", parent_ids=("b",)))
    assert archive._would_create_cycle("a", ("c",)) is True


def test_export_and_restore_round_trips():
    archive = LineageArchive()
    archive.record(_record("root"))
    archive.record(_record("child", parent_ids=("root",), generation=1))

    payload = archive.export()
    restored = LineageArchive.restore(payload)

    assert [entry.genome_id for entry in restored.ancestors_of("child")] == ["root"]
