"""Lab-side causal chain queries over a provenance journal (Causal Provenance v1 §6)."""

from __future__ import annotations

from symbiont.provenance import CausalEvent, CausalRef, ProvenanceLog
from symbiont_lab.cli.main import main
from symbiont_lab.observation.provenance_journal import (
    ProvenanceIndex,
    ProvenanceJournal,
    render_tree,
)

PULSE = CausalRef("commitment", "c1")
VERSION = CausalRef("footprint_version", "footprint.x@v1")
COMPETENCE = CausalRef("competence", "p1")
INTENT = CausalRef("intent", "i1")


def _journal(tmp_path):
    journal = ProvenanceJournal(tmp_path / "provenance.jsonl")
    log = ProvenanceLog()
    log.subscribe(journal.append)
    for tick, (domain, operation, subject, causes) in enumerate(
        [
            ("footprint", "version", VERSION, (PULSE,)),
            ("competence", "ground", COMPETENCE, (VERSION,)),
            ("intention", "form", INTENT, (COMPETENCE,)),
            ("intention", "satisfied", INTENT, (INTENT, CausalRef("commitment", "c9"))),
        ]
    ):
        log.emit(
            CausalEvent(
                tick=tick,
                domain=domain,
                operation=operation,
                subject=subject,
                caused_by=causes,
                produced=(subject,),
                rule="r",
            )
        )
    return journal


def test_index_answers_why_down_to_pulses(tmp_path):
    index = ProvenanceIndex.load(_journal(tmp_path))
    assert index.summary()["intention.satisfied"] == 1
    assert [e.operation for e in index.find(domain="intention")] == ["form", "satisfied"]
    tree = index.why(COMPETENCE)
    assert tree["event"]["operation"] == "ground"
    (version,) = tree["causes"]
    assert version["ref"] == VERSION.payload()
    assert version["causes"][0] == {"ref": PULSE.payload(), "root": True}
    assert index.reaches(COMPETENCE, "commitment")
    assert "  commitment:c1  [root]" in "\n".join(render_tree(index.why(VERSION)))


def test_repeated_refs_are_expanded_once(tmp_path):
    index = ProvenanceIndex.load(_journal(tmp_path))
    tree = index.why(INTENT)  # the satisfied intent is caused by its own formation
    assert tree["causes"][0].get("repeated") is True


def test_cli_why_and_summary(tmp_path, capsys):
    journal = _journal(tmp_path)
    try:
        main(["provenance", "why", str(journal.path), "competence", "p1"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "competence:p1  <- competence.ground" in out and "commitment:c1  [root]" in out
    try:
        main(["provenance", "summary", str(journal.path)])
    except SystemExit as exc:
        assert exc.code == 0
    assert "footprint.version" in capsys.readouterr().out
