import os

eng = open('src/symbiont/simulation/engine.py').read()
eng = eng.replace('def _trust_gap', '''def _mean_reliability(ledger: SocialEvidenceLedger) -> float:
    states = ledger.source_states.values()
    return sum(s.source_reliability for s in states) / len(states) if states else 0.0

def _low_rel_sources(ledger: SocialEvidenceLedger) -> int:
    return sum(1 for s in ledger.source_states.values() if s.source_reliability < 0.4)

def _trust_gap''')
eng = eng.replace('mean_source_reliability=0.0,', 'mean_source_reliability=_mean_reliability(ledger),')
eng = eng.replace('low_reliability_sources=0,', 'low_reliability_sources=_low_rel_sources(ledger),')
eng = eng.replace('collective: SocialEvidenceLedger | None = None', 'ledger: SocialEvidenceLedger | None = None')
eng = eng.replace(') -> tuple[SimulationResult, SocialEvidenceLedger]:', ') -> tuple[SimulationResult, SocialEvidenceLedger]:')

open('src/symbiont/simulation/engine.py', 'w').write(eng)
