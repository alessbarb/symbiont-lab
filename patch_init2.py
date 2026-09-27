import os
import re

init = open('src/symbiont/core/__init__.py').read()

init = re.sub(r'from \.social\.collective import \([^)]+\)', '', init, flags=re.MULTILINE)
init = re.sub(r'from \.social\.trust import .*\n', '', init, flags=re.MULTILINE)
init = re.sub(r'from \.social\.collective_revision import .*\n', '', init, flags=re.MULTILINE)

# Remove exports
exports_to_remove = [
    '"CollectiveMemory",', '"InheritedPrior",', '"OpenQuestion",',
    '"PatternEvidence",', '"SourceTrust",', '"SourceVote",',
    '"SourceTrustModel",', '"TrustSnapshot",', '"agreement_score",', '"observe_capsule_trust",',
    '"RevisionResult",', '"revise_claim",',
    '"collective": "social.collective",',
    '"trust": "social.trust",',
    '"collective_revision": "social.collective_revision",'
]
for exp in exports_to_remove:
    init = init.replace(exp + '\n', '')
    init = init.replace('    ' + exp + '\n', '')

# Insert the new imports after capsule
new_imports = """
from .social.ledger import SocialClaim, SocialEvidenceLedger, SocialQuestion
from .social.source_evidence import SourceEvidenceSample, SourceEvidenceState, SourceEvidenceOutcome
"""
init = init.replace('from .social.capsule import (', new_imports.strip() + '\nfrom .social.capsule import (')

open('src/symbiont/core/__init__.py', 'w').write(init)
