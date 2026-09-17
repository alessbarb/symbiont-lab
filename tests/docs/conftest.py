from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source-type taxonomy for docs/web/FUENTES.md — shared so a new type added
# to the taxonomy only needs to change in one place.
VALID_TYPES = {"normative", "formal", "implementation", "empirical", "historica"}

# The docs/web/ chapter sequence, in order — shared by every test that needs
# to enumerate or validate the full chapter set.
CHAPTERS = [
    "01-que-es-un-symbiont.md",
    "02-cuerpo-y-percepcion.md",
    "03-cognicion-y-plasticidad.md",
    "04-atencion-y-decision.md",
    "05-fisiologia.md",
    "06-reproduccion-y-linaje.md",
    "07-ecologia-y-sociabilidad.md",
    "08-desarrollo-predictivo.md",
    "09-metodologia-y-limites.md",
]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
