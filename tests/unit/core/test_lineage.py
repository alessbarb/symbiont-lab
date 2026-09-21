from symbiont.core.lineage import HabitatBirthAuthority


def test_capacity_and_release_are_transactional():
    authority = HabitatBirthAuthority(habitat_id="h", capacity=1)
    root = authority.birth(genome_id="g")
    assert root
    assert authority.birth(genome_id="g2") is None

    death = authority.death(root.organism_id)
    assert death is not None
    assert authority.live_ids == ()

    child = authority.birth(genome_id="g2")
    assert child is not None
    assert child.parent_ids == ()


def test_checkpoint_round_trip():
    authority = HabitatBirthAuthority(habitat_id="h", capacity=2)
    root = authority.birth(genome_id="g")
    restored = HabitatBirthAuthority.from_checkpoint(authority.checkpoint())
    assert restored.live_ids == (root.organism_id,)
    assert restored.lineage_records == authority.lineage_records
