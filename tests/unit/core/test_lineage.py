from symbiont.core.lineage import HabitatBirthAuthority

def test_capacity_and_release_are_transactional():
 a=HabitatBirthAuthority(habitat_id='h',capacity=1,resource_budget=2)
 root=a.birth(genome_id='g',resource_units=1); assert root
 assert a.birth(genome_id='g2') is None
 d=a.death(root.organism_id); assert d and a.resource_budget==2
 child=a.birth(genome_id='g2'); assert child and child.parent_ids==()

def test_checkpoint_round_trip():
 a=HabitatBirthAuthority(habitat_id='h',capacity=2,resource_budget=2); r=a.birth(genome_id='g')
 b=HabitatBirthAuthority.from_checkpoint(a.checkpoint()); assert b.live_ids==(r.organism_id,)
