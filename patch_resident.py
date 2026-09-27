import os
import re

content = open('src/symbiont/core/orchestration/resident.py').read()
# Replace the observe_capsule_trust block
content = re.sub(
    r'                observe_capsule_trust\([\s\S]*?capsule=cap,\n                \)\n',
    '',
    content
)
open('src/symbiont/core/orchestration/resident.py', 'w').write(content)
