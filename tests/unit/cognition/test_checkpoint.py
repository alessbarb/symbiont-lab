from __future__ import annotations

import copy

import pytest

from symbiont.cognition.checkpoint import export_genome_checkpoint, restore_genome_checkpoint
from symbiont.cognition.genome import GenomeCodec, GenomeError
from symbiont.cognition.limits import KernelLimits
from tests.unit.cognition.test_genome import VALID_PAYLOAD

_RUNNING_VERSION = (0, 55, 0)


def test_none_genome_round_trips_to_none():
    assert export_genome_checkpoint(None) is None
    assert (
        restore_genome_checkpoint(
            None, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION
        )
        is None
    )


def test_valid_genome_round_trips_exactly():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    restored = restore_genome_checkpoint(
        payload, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION
    )
    assert restored == genome
    assert restored.genome_hash == genome.genome_hash


def test_exported_payload_carries_genome_hash():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    assert payload["genome_hash"] == genome.genome_hash


def test_tampered_payload_is_rejected_on_restore():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    tampered = copy.deepcopy(payload)
    tampered["plasticity"]["eligibility_decay"] = 0.01
    with pytest.raises(GenomeError):
        restore_genome_checkpoint(
            tampered, kernel_limits=KernelLimits(), running_version=_RUNNING_VERSION
        )


def test_restore_rejects_a_genome_that_no_longer_satisfies_kernel_limits():
    genome = GenomeCodec().load(VALID_PAYLOAD)
    payload = export_genome_checkpoint(genome)
    with pytest.raises(GenomeError):
        restore_genome_checkpoint(
            payload, kernel_limits=KernelLimits(max_nodes=1), running_version=_RUNNING_VERSION
        )
