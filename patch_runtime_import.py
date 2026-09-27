import os

content = open('src/symbiont/core/orchestration/runtime.py').read()
content = content.replace(
    '    SocialRelation,\nfrom ..social.ledger import SocialEvidenceLedger\n',
    ''
)
content = content.replace(
    'from ..social.relations import (',
    'from ..social.ledger import SocialEvidenceLedger\nfrom ..social.relations import ('
)
open('src/symbiont/core/orchestration/runtime.py', 'w').write(content)
