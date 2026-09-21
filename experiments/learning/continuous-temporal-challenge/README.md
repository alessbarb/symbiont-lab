# Continuous temporal mechanism challenge

This study evaluates the sparse ESN + NLMS challenger on a bounded continuous
stream with a deterministic regime shift.

It is intentionally separate from the token-based private-model study. The
purpose is to avoid giving the ESN an artificial discrete representation or
forcing GRU/Transformer token assumptions onto continuous dynamics.

Metrics include pre-shift gain, early post-shift damage, late post-shift gain,
adaptation recovery, and learned/fixed parameter counts.

No result from this study automatically grants the ESN any privileged role in
the organism.
