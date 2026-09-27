import os

code = open('src/symbiont_lab/cli/capsule.py').read()
code = code.replace("""
from symbiont.core import (
    CapsuleKeyPair,
    SourceTrustModel,
    create_capsule,
    observe_capsule_trust,
    verify_capsule,
)
""", """
from symbiont.core import (
    CapsuleKeyPair,
    create_capsule,
    verify_capsule,
)
""")

# Delete ingest command
import re
code = re.sub(r'    ingest_cmd = sub\.add_parser\([\s\S]*?    \)', '', code)
code = re.sub(r'    if args\.capsule_action == "ingest":[\s\S]*?        return 0\n', '', code)

open('src/symbiont_lab/cli/capsule.py', 'w').write(code)
