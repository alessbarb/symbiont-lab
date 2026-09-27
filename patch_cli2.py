import os
import re

code = open('src/symbiont_lab/cli/capsule.py').read()
code = re.sub(r'    ingest_cmd\.add_argument\([\s\S]*?    \)\n', '', code)
open('src/symbiont_lab/cli/capsule.py', 'w').write(code)
