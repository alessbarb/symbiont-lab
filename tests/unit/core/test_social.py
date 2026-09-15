from symbiont.core.social import RelationLedger, RelationValence

def test_relation_valence_is_evidence_based():
 l=RelationLedger(); assert l.observe("a","b",benefit=2).valence is RelationValence.POSITIVE; assert l.observe("a","b",cost=3).valence is RelationValence.NEGATIVE

def test_engine_supports_exchange_and_finite_competition():
 from symbiont.core.interactions import EcologicalResourcePool
 from symbiont.core.social import SocialInteractionEngine
 e=SocialInteractionEngine(EcologicalResourcePool({"food":1.0}))
 assert e.exchange("a","b","food",0.4).granted == 0.4
 out=e.compete([("a","food",0.8),("b","food",0.8)])
 assert sum(x.granted for x in out) == 0.6
