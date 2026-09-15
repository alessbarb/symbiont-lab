import pytest
from symbiont.core.heredity import HeritableGenome
from symbiont.core.inheritance import EpigeneticPrior, CulturalArtifact, InheritanceChannels, mutate_genome

def test_mutation_is_bounded_and_deterministic():
 g=HeritableGenome('g',(('learning_rate',.5),)); a=mutate_genome(g,seed=3); assert a==mutate_genome(g,seed=3); assert 0<=dict(a.loci)['learning_rate']<=1

def test_channels_are_separate_and_bounded():
 c=InheritanceChannels(max_epigenetic=1,max_cultural=1); assert c.add_epigenetic(EpigeneticPrior('x',.2)); assert not c.add_epigenetic(EpigeneticPrior('y',.3)); assert c.add_cultural(CulturalArtifact('k',.4)); assert not c.add_cultural(CulturalArtifact('l',.5))
