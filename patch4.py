import os
eng = open('src/symbiont/simulation/engine.py').read()
eng = eng.replace('        meta = metacognition.assess', '        meta = metacognition.assess')
# let's just see where it failed and rewrite the line
lines = eng.split('\n')
for i, line in enumerate(lines):
    if 'meta = metacognition.assess(step_assessments, ledger)' in line:
        lines[i] = '        meta = metacognition.assess(step_assessments, ledger)'
open('src/symbiont/simulation/engine.py', 'w').write('\n'.join(lines))
