"""Lab-side causal chain queries over a provenance journal (Causal Provenance v1 §6)."""

from __future__ import annotations

from lab.cli.main import main
from lab.observation.provenance_journal import (
    ProvenanceIndex,
    ProvenanceJournal,
    render_tree,
)
from symbiont.provenance import CausalEvent, CausalRef, ProvenanceLog

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


def test_lifecycle_refs_explain_through_their_formation(tmp_path):
    index = ProvenanceIndex.load(_journal(tmp_path))
    tree = index.why(INTENT)  # latest event is "satisfied"; causes span form..satisfied
    assert tree["event"]["operation"] == "satisfied"
    assert [cause["ref"] for cause in tree["causes"]] == [
        COMPETENCE.payload(),
        CausalRef("commitment", "c9").payload(),
    ]
    assert index.reaches(INTENT, "footprint_version")
    assert PULSE in index.ancestors(INTENT)
    assert _journal(tmp_path / "again").ancestors(INTENT) == index.ancestors(INTENT)


def test_repeated_refs_are_expanded_once(tmp_path):
    journal = _journal(tmp_path)
    log = ProvenanceLog()
    log.subscribe(journal.append)
    binding = CausalRef("binding", "b1")  # reaches VERSION directly and via COMPETENCE
    log.emit(
        CausalEvent(
            tick=9,
            domain="action",
            operation="bind",
            subject=binding,
            caused_by=(COMPETENCE, VERSION),
            produced=(binding,),
            rule="r",
        )
    )
    tree = ProvenanceIndex.load(journal).why(binding)
    via_competence, direct = tree["causes"]
    assert via_competence["causes"][0]["ref"] == VERSION.payload()
    assert "repeated" not in via_competence["causes"][0]
    assert direct["ref"] == VERSION.payload() and direct["repeated"] is True


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
