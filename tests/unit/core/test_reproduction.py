from symbiont.core.lineage import HabitatBirthAuthority
from symbiont.core.reproduction import ReproductivePressure, clonal_bud

def test_pressure_requires_persistence_and_bud_consumes_once():
 p=ReproductivePressure(threshold_ticks=2); a=HabitatBirthAuthority(habitat_id='h',capacity=2,resource_budget=2); parent=a.birth(genome_id='g')
 p.observe(viable=True,adaptive=True,capacity_exhausted=True,blocked_growth=True); p.observe(viable=True,adaptive=True,capacity_exhausted=True,blocked_growth=True)
 child=clonal_bud(parent_id=parent.organism_id,genome_id='g',generation=0,authority=a,pressure=p)
 assert child and child.parent_ids==(parent.organism_id,) and p.reserve==0
 assert clonal_bud(parent_id=parent.organism_id,genome_id='g',generation=0,authority=a,pressure=p) is None

def test_denied_birth_does_not_consume_pressure():
 p=ReproductivePressure(threshold_ticks=1); p.observe(viable=True,adaptive=True,capacity_exhausted=True,blocked_growth=True); a=HabitatBirthAuthority(habitat_id='h',capacity=1,resource_budget=1); parent=a.birth(genome_id='g')
 assert clonal_bud(parent_id=parent.organism_id,genome_id='g',generation=0,authority=a,pressure=p) is None and p.reserve==1
