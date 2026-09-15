from symbiont.core.social import RelationLedger, RelationValence

def test_relation_valence_is_evidence_based():
 l=RelationLedger(); assert l.observe("a","b",benefit=2).valence is RelationValence.POSITIVE; assert l.observe("a","b",cost=3).valence is RelationValence.NEGATIVE
