import os
import re

content = open('src/symbiont_lab/cli/organism.py').read()
content = re.sub(r'    source_trust = payload\.get\("source_trust", \{\}\) or \{\}\n', '', content)
content = re.sub(r'    direct_trust = source_trust\.get\("direct", \{\}\) or \{\}\n', '', content)
content = re.sub(r'    for key_hex, rec in direct_trust\.items\(\):\n[\s\S]*?            peers\.append\(\{"id": key_hex, "score": score, "count": count\}\)\n', '', content)
open('src/symbiont_lab/cli/organism.py', 'w').write(content)
