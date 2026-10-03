from __future__ import annotations

from .conftest import REPO_ROOT

# NOTE: symbiont/src/symbiont/core/cognition/host_self_model.py is deliberately excluded: an unrelated
# main-branch refactor (RecencyClass moved to symbiont.core.foundation.epistemic)
# removed the docstring that carried this citation entirely, so there is
# nothing left in that file to point at any docs/design/ path.
CITING_FILES = [
    "symbiont/src/symbiont/core/foundation/weight_stability.py",
    "symbiont/src/symbiont/host/consolidated_baseline.py",
    "symbiont/src/symbiont/core/cognition/consolidation.py",
    "lab/tests/smoke/test_cli.py",
    "symbiont/tests/unit/host/test_checkpoint.py",
]


def test_all_citing_files_point_at_the_merged_design_doc():
    for rel_path in CITING_FILES:
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "docs/design/cognicion-y-plasticidad.md" in text, (
            f"{rel_path} does not cite the merged design doc"
        )
        assert "docs/design/biological-memory-consolidation.md" not in text, (
            f"{rel_path} still cites the old (deleted) design doc path"
        )
