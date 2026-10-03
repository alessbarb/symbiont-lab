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
| `modality.host` | read-only, aggregate channels of the machine a process runs on: standard-library surfaces, Linux procfs/sysfs surfaces, portable macOS/Windows surfaces and process telemetry (tick latency, resident memory). They yield the library's own records; whoever couples them to an organism converts them. |
