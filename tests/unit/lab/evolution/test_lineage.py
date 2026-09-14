from __future__ import annotations

import pytest

from symbiont_lab.evolution.lineage import LineageArchive, LineageRecord


def _record(genome_id: str, parent_ids: tuple[str, ...] = (), generation: int = 0) -> LineageRecord:
    return LineageRecord(
        genome_id=genome_id, parent_ids=parent_ids, genome_hash=f"hash-{genome_id}", created_at_generation=generation
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


def test_self_referential_parent_is_rejected():
    archive = LineageArchive()
    with pytest.raises(ValueError):
        archive.record(_record("root", parent_ids=("root",)))


def test_cyclic_parent_chain_is_rejected():
    archive = LineageArchive()
    archive.record(_record("a", parent_ids=("b",)))
    with pytest.raises(ValueError):
        archive.record(_record("b", parent_ids=("a",)))


def test_export_and_restore_round_trips():
    archive = LineageArchive()
    archive.record(_record("root"))
    archive.record(_record("child", parent_ids=("root",), generation=1))

    payload = archive.export()
    restored = LineageArchive.restore(payload)

    assert [entry.genome_id for entry in restored.ancestors_of("child")] == ["root"]
