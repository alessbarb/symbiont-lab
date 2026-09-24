import pytest

from symbiont.core.heredity import HeritableGenome, recombine_loci


def test_legacy_heritable_genome_cannot_be_constructed():
    with pytest.raises(TypeError):
        HeritableGenome("legacy", (("learning_rate", 0.1),))


def test_legacy_recombination_cannot_create_parallel_genetics():
    with pytest.raises(TypeError):
        recombine_loci(None, None)
