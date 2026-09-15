from symbiont.core.heredity import HeritableGenome
from symbiont.core.lineage import HabitatBirthAuthority
from symbiont.core.reproduction import paired_reproduce

def test_paired_reproduction_requires_two_live_parents():
 a=HabitatBirthAuthority(habitat_id='h',capacity=3,resource_budget=3); p1=a.birth(genome_id='a'); p2=a.birth(genome_id='b')
 child=paired_reproduce(parent_a=p1.organism_id,parent_b=p2.organism_id,genome_a=HeritableGenome('a',(('learning_rate',.1),)),genome_b=HeritableGenome('b',(('learning_rate',.2),)),generation=0,authority=a)
 assert child and child.parent_ids==(p1.organism_id,p2.organism_id)
 assert paired_reproduce(parent_a=p1.organism_id,parent_b=p1.organism_id,genome_a=HeritableGenome('a'),genome_b=HeritableGenome('a'),generation=0,authority=a) is None
