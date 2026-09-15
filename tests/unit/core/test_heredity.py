import pytest
from symbiont.core.heredity import HeritableGenome, recombine_loci

def test_recombine_declared_loci_deterministically():
 a=HeritableGenome('a',(('learning_rate',.1),)); b=HeritableGenome('b',(('learning_rate',.8),('forgetting_rate',.2)))
 c=recombine_loci(a,b); assert dict(c.loci)=={'learning_rate':.1,'forgetting_rate':.2}
 assert recombine_loci(a,b).identity==c.identity

def test_unknown_locus_rejected():
 with pytest.raises(ValueError): HeritableGenome('a',(('permission',1),))
