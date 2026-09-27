import os
import re

content = open('src/symbiont/core/orchestration/resident.py').read()
content = re.sub(r'            for cap in peer_capsules:[\s\S]*?        except Exception:', '            for cap in peer_capsules:\n                pass\n        except Exception:', content)
open('src/symbiont/core/orchestration/resident.py', 'w').write(content)
