from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source-type taxonomy for docs/explanation/concepts/SOURCES.md — shared so a new type added
# to the taxonomy only needs to change in one place.
VALID_TYPES = {"normative", "formal", "implementation", "empirical", "historica"}

# The docs/explanation/concepts/ chapter sequence, in order — shared by every test that needs
# to enumerate or validate the full chapter set.
CHAPTERS = [
    "01-what-is-a-symbiont.md",
    "02-body-and-perception.md",
    "03-cognition-and-plasticity.md",
    "04-attention-and-decision.md",
    "05-physiology.md",
    "06-reproduction-and-lineage.md",
    "07-ecology-and-sociability.md",
    "08-predictive-development.md",
    "09-methodology-and-limitations.md",
]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
