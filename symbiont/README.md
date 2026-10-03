# Symbiont

The organism. Installable and testable on its own:

```bash
uv venv /tmp/symbiont-alone
uv pip install --python /tmp/symbiont-alone/bin/python ./symbiont pytest
/tmp/symbiont-alone/bin/python -m pytest symbiont/tests -p no:cacheprovider
```

Import package: `symbiont`. Public surface: `symbiont.api`. It imports nothing
from `lab`, `environment`, `modality` or `embodiment`, and no PyBullet, torch,
numpy or PIL.
