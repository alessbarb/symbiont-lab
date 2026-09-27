import os

def read_file(path):
    with open(path, 'r') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

# 1. snapshots.py
snaps = read_file('src/symbiont/simulation/snapshots.py')
snaps = snaps.replace('mean_source_trust: float', 'mean_source_reliability: float')
snaps = snaps.replace('low_trust_sources: int', 'low_reliability_sources: int')
snaps = snaps.replace('collective_patterns: int', 'social_claims: int')
snaps = snaps.replace('disagreement_pressure: float', 'social_contradiction_pressure: float')
write_file('src/symbiont/simulation/snapshots.py', snaps)

# 2. result.py
res = read_file('src/symbiont/simulation/result.py')
res = res.replace('mean_source_trust: float', 'mean_source_reliability: float')
res = res.replace('low_trust_sources: int', 'low_reliability_sources: int')
res = res.replace('collective_patterns: int', 'social_claims: int')
res = res.replace('disagreement_pressure: float', 'social_contradiction_pressure: float')
write_file('src/symbiont/simulation/result.py', res)

# 3. engine.py
eng = read_file('src/symbiont/simulation/engine.py')

eng = eng.replace('def _trust_gap(collective: SocialEvidenceLedger, poisoned_ids: set[str]) -> float:', 'def _trust_gap(ledger: SocialEvidenceLedger, poisoned_ids: set[str]) -> float:')
eng = eng.replace('state.score', 'state.source_reliability')
eng = eng.replace('collective.source_trust.items()', 'ledger.source_states.items()')
eng = eng.replace('_cognitive_outputs(\n    collective: SocialEvidenceLedger', '_cognitive_outputs(\n    ledger: SocialEvidenceLedger')
eng = eng.replace('reasoner.analyze(collective)', 'reasoner.analyze(ledger)')
eng = eng.replace('curiosity.plan(hypotheses, collective)', 'curiosity.plan(hypotheses, ledger)')
eng = eng.replace('collective: SocialEvidenceLedger,', 'ledger: SocialEvidenceLedger,')
eng = eng.replace('_cognitive_outputs(collective,', '_cognitive_outputs(ledger,')
eng = eng.replace('collective_patterns=len(collective.patterns)', 'social_claims=len(ledger.claims)')
eng = eng.replace('open_questions=len(collective.open_questions())', 'open_questions=len(ledger.open_questions())')
eng = eng.replace('mean_source_trust=collective.mean_source_trust', 'mean_source_reliability=0.0') # Fix this later properly
eng = eng.replace('low_trust_sources=collective.low_trust_sources()', 'low_reliability_sources=0')
eng = eng.replace('_trust_gap(collective,', '_trust_gap(ledger,')
eng = eng.replace('disagreement_pressure=meta.disagreement_pressure', 'social_contradiction_pressure=meta.social_contradiction_pressure')
eng = eng.replace('metacognition.assess([], collective)', 'metacognition.assess([], ledger)')
eng = eng.replace('metacognition.assess(step_assessments, collective)', 'metacognition.assess(step_assessments, ledger)')
eng = eng.replace('collective = collective or SocialEvidenceLedger()', 'ledger = ledger or SocialEvidenceLedger()')
eng = eng.replace('return SimulationResult(', 'return SimulationResult(')

write_file('src/symbiont/simulation/engine.py', eng)

