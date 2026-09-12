from __future__ import annotations

import argparse

from .campaign import analyze_campaign
from .study_archive import StudyArchive


def main() -> None:
    parser = argparse.ArgumentParser(description="Assess a Symbiont Lab observer-side research lineage")
    parser.add_argument("--study-id", required=True, help="Newest study record ID in the lineage")
    parser.add_argument("--archive", default=".symbiont/studies.jsonl")
    args = parser.parse_args()

    archive = StudyArchive(args.archive)
    lineage = archive.lineage(args.study_id)
    if not lineage:
        parser.error(f"study ID not found in archive: {args.study_id}")

    assessment = analyze_campaign(lineage)
    print("SYMBIONT LAB — research campaign")
    print(f"root:       {assessment.root_record_id}")
    print(f"current:    {assessment.current_record_id}")
    print(f"studies:    {assessment.studies}")
    print(f"parameter:  {assessment.parameter}")
    print(f"status:     {assessment.status}")
    print(f"confidence: {assessment.latest_confidence:.0%}")
    print(f"span:       {assessment.initial_span:.4f} -> {assessment.latest_span:.4f}")
    print()
    print(assessment.summary)

    print("\nLineage")
    for record in reversed(lineage):
        study = record.study
        baseline = dict(study.get("baseline", {})).get("parameter_value", "?")
        variant = dict(study.get("variant", {})).get("parameter_value", "?")
        print(
            f"  {record.record_id} parent={record.parent_record_id or '-'} "
            f"{study.get('parameter', '?')} {baseline}->{variant} "
            f"{study.get('title', '')}"
        )

    if assessment.proposal is None:
        print("\nNo follow-up study is recommended for this campaign state.")
    else:
        proposal = assessment.proposal
        print("\nResearcher-approved next comparison")
        print(
            f"  {proposal.parameter}: {proposal.baseline:.4f} -> {proposal.variant:.4f} "
            f"with ~{proposal.recommended_seed_count} paired seeds"
        )
        print(f"  parent: {proposal.parent_record_id}")
        print(f"  {proposal.rationale}")
        print("  This is a proposal only; nothing is launched automatically.")


if __name__ == "__main__":
    main()
