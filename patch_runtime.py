import re

content = open('src/symbiont/core/orchestration/runtime.py').read()
content = re.sub(r'^\s*source_trust: object \| None = None,\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*self._source_trust = source_trust if source_trust is not None else object\(\)\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*@property\n\s*def source_trust\(self\) -> object:\n\s*return self._source_trust\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*payload\["source_trust"\] = self._source_trust.export_checkpoint\(\)\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*source_trust = \(\n\s*object.from_checkpoint\(normalized\["source_trust"\]\)\n\s*if normalized.get\("source_trust"\)\n\s*else object\(\)\n\s*\)\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^\s*source_trust=source_trust,\n', '', content, flags=re.MULTILINE)
open('src/symbiont/core/orchestration/runtime.py', 'w').write(content)
