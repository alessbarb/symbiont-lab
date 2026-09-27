import os
eng = open('src/symbiont/simulation/engine.py').read()
eng = eng.replace('collective.recalibrate_sources()\n', '')
eng = eng.replace('collective=collective,', 'ledger=ledger,')
eng = eng.replace('return result, collective', 'return result, ledger')
open('src/symbiont/simulation/engine.py', 'w').write(eng)
