from __future__ import annotations

import argparse
import sys

from symbiont_lab.archive.runs import ExperimentArchive
from symbiont_lab.archive.studies import StudyArchive
from symbiont_lab.studies.campaigns.campaign import analyze_campaign


def build_archive_parser(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="archive_action", required=True)
    list_cmd = sub.add_parser("list", help="List recent archived experiment runs and studies")
    list_cmd.add_argument("--limit", type=int, default=10, help="Max records to list")

    campaign_cmd = sub.add_parser(
        "campaign", help="Assess a Symbiont Lab observer-side research lineage"
    )
    campaign_cmd.add_argument(
        "--study-id", required=True, help="Newest study record ID in the lineage"
    )
    campaign_cmd.add_argument("--archive", default=".symbiont/studies.jsonl")


def run_archive_command(args: argparse.Namespace) -> int:
    if args.archive_action == "list":
        runs = ExperimentArchive().recent(args.limit)
        studies = StudyArchive().recent(args.limit)
        print(f"=== Experiment Runs ({len(runs)}) ===")
        for r in runs:
            print(
                f"[{r.record_id}] {r.created_at} — {r.spec.get('title', 'Untitled')} (source: {r.source})"
            )

        print(f"\n=== Comparative Studies ({len(studies)}) ===")
        for s in studies:
            print(
                f"[{s.record_id}] {s.created_at} — {s.base_spec.get('title', 'Untitled')} (source: {s.source})"
            )
        return 0
    elif args.archive_action == "campaign":
        archive = StudyArchive(args.archive)
        lineage = archive.lineage(args.study_id)
        if not lineage:
            print(f"study ID not found in archive: {args.study_id}", file=sys.stderr)
            return 1

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
        return 0
    return 1
