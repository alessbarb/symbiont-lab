# Modality

A self-contained library of signal channels. A modality describes signal
structure, sampling and transport. It carries no cognitive meaning, and it has
no dependency on Symbiont, Embodiment, Environment or Lab.

Import package: `modality`. Enforced by
`tests/experimental_integrity/test_five_domain_architecture.py`; checked alone by
`modality/tests`.

| Module | Contents |
|---|---|
| `modality.vision` | square receptor array: bounded luminance per opaque receptor, plus receptor adjacency. The link that carries it, the mount pose and the receptor ids are supplied by the caller. |
