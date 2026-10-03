from __future__ import annotations

import pytest

from symbiont.cognition.birth import load_base_genome
from symbiont.cognition.genome import GenomeError, MotorGenes
from symbiont.cognition.limits import KernelLimits


def test_genome_v2_has_no_motor_genes():
    genome = load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=(0, 80, 0),
    )
    assert not hasattr(genome, "motor")


def test_motor_genes_constructor_fails_fast():
    with pytest.raises(GenomeError):
        MotorGenes(
            slot_count=3,
            basal_cost=0.1,
            initial_health=0.9,
            execution_threshold=0.4,
        )


def test_body_properties_do_not_participate_in_genotype_hash():
    genome = load_base_genome(
        kernel_limits=KernelLimits(),
        running_version=(0, 80, 0),
    )
    assert genome.genotype_hash
    assert "motor" not in genome.__dataclass_fields__
