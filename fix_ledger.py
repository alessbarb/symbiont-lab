import os

content = open('src/symbiont/core/social/ledger.py').read()
# Extract the open_questions method
import re
match = re.search(r'(    def open_questions\(self\) -> list\[SocialQuestion\]:.*)', content, re.DOTALL)
if match:
    method = match.group(1)
    content = content.replace(method, '')
    
    # Insert it before SocialQuestion
    content = content.replace('@dataclass(slots=True, frozen=True)\nclass SocialQuestion:', method + '\n@dataclass(slots=True, frozen=True)\nclass SocialQuestion:')
    open('src/symbiont/core/social/ledger.py', 'w').write(content)
