import os
import re

content = open('src/symbiont/core/orchestration/runtime.py').read()
content = content.replace(
    'from ..social.relations import RelationLedger, RelationValence, SocialRelation',
    'from ..social.relations import RelationLedger, RelationValence, SocialRelation\nfrom ..social.ledger import SocialEvidenceLedger'
)

# Add it to __init__ arguments
content = re.sub(
    r'        social_resource_ledger: ResourceEvidenceLedger \| None = None,\n',
    '        social_resource_ledger: ResourceEvidenceLedger | None = None,\n        epistemic_ledger: SocialEvidenceLedger | None = None,\n',
    content
)

# Initialize it
content = re.sub(
    r'        self\._social_resource_ledger = \(\n            social_resource_ledger\n            if social_resource_ledger is not None\n            else ResourceEvidenceLedger\(\)\n        \)\n',
    '        self._social_resource_ledger = (\n            social_resource_ledger\n            if social_resource_ledger is not None\n            else ResourceEvidenceLedger()\n        )\n        self._epistemic_ledger = epistemic_ledger if epistemic_ledger is not None else SocialEvidenceLedger()\n',
    content
)

# Pass it to agent assess / observe
content = content.replace(
    'assessment = self._agent.assess(observation)',
    'assessment = self._agent.assess(observation, self._epistemic_ledger)'
)
content = content.replace(
    'assessment = self._agent.observe(self._tick_count, observation)',
    'assessment = self._agent.observe(self._tick_count, observation, self._epistemic_ledger)'
)

# Include in checkpoint
content = content.replace(
    '        payload["social_resource_ledger"] = self._social_resource_ledger.checkpoint()\n',
    '        payload["social_resource_ledger"] = self._social_resource_ledger.checkpoint()\n        # payload["epistemic_ledger"] = self._epistemic_ledger.checkpoint() # TODO\n'
)

open('src/symbiont/core/orchestration/runtime.py', 'w').write(content)
