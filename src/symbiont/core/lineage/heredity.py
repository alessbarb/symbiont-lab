"""Removed Genome-v1 heredity surface.

Genome v2 is the only genetic representation. Historical callers receive a
fail-fast error instead of creating a second heritable state object.
"""
from __future__ import annotations

from typing import NoReturn

_ALLOWED_LOCI = frozenset()


def HeritableGenome(*args, **kwargs) -> NoReturn:
    raise TypeError(
        "HeritableGenome was removed by Genome v2; use symbiont.genetics.Genome"
    )


def recombine_loci(*args, **kwargs) -> NoReturn:
    raise TypeError(
        "recombine_loci was removed by Genome v2; use "
        "symbiont.genetics.recombine_genomes"
    )


__all__ = ["HeritableGenome", "recombine_loci"]
