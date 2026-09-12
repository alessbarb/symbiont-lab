from __future__ import annotations

from symbiont.environment.rng import derive_seed, make_rng_streams
from symbiont.environment.world import make_profiles


def test_streams_are_independent_across_namespaces():
    """Deriving seeds with distinct namespaces must produce distinct values."""
    seed = 12345
    s1 = derive_seed(seed, "profiles")
    s2 = derive_seed(seed, "agents")
    s3 = derive_seed(seed, "schedule")
    assert len({s1, s2, s3}) == 3


def test_reporter_perturbation_does_not_shift_profile_stream():
    """Drawing from reporter stream must leave profile stream bitwise identical."""
    s1 = make_rng_streams(777)
    profiles_a = make_profiles(15, s1.profiles)

    s2 = make_rng_streams(777)
    # Perform various draws from reporters and agents
    for _ in range(50):
        s2.reporters.random()
        s2.agents.uniform(0.0, 1.0)
    profiles_b = make_profiles(15, s2.profiles)

    for pa, pb in zip(profiles_a, profiles_b):
        assert pa.cpu == pb.cpu
        assert pa.network == pb.network
        assert pa.file_changes == pb.file_changes
