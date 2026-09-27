import os
run = open('src/symbiont/core/orchestration/runtime.py').read()
run = run.replace('from ..social.trust import SourceTrustModel\n', '')
run = run.replace('SourceTrustModel', 'object') # Quick hack if it's used
open('src/symbiont/core/orchestration/runtime.py', 'w').write(run)
