# Symbiont

The organism. Installable and testable on its own:

```bash
uv venv /tmp/symbiont-alone
uv pip install --python /tmp/symbiont-alone/bin/python ./symbiont pytest
/tmp/symbiont-alone/bin/python -m pytest symbiont/tests -p no:cacheprovider
```

Import package: `symbiont`. Public surface: `symbiont.api`. It has no dependency
on Embodiment, Modality, Environment or Lab, and imports no PyBullet, torch,
numpy or PIL.
