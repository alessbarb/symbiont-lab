from symbiont_world.rng import derive_world_rng, derive_world_seed


def test_same_seed_and_namespace_reproduce_the_same_sequence():
    a = derive_world_rng(101, "topology.founder-placement")
    b = derive_world_rng(101, "topology.founder-placement")
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]


def test_different_namespaces_are_independent_streams():
    a = derive_world_rng(101, "topology.founder-placement")
    b = derive_world_rng(101, "resolution.simultaneous-intent")
    assert [a.random() for _ in range(5)] != [b.random() for _ in range(5)]


def test_different_seeds_diverge():
    assert derive_world_seed(101, "fields") != derive_world_seed(102, "fields")
