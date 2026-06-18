#!/usr/bin/env python3
"""Compare current Exa acquisition against a typed Exa vNext query plan.

Lab-only. This does not feed production collectors, scoring, prompts,
persistence, or Scanner output.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.collectors.exa_collector import ExaCollector
from src.config import EXA_API_KEY
from src.research.exa_vnext_bakeoff import (
    default_cases,
    load_cases_from_evidence_report,
    load_cases_from_file,
    run_exa_vnext_bakeoff,
    write_exa_vnext_bakeoff_outputs,
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cases = _load_cases(args)
    if args.limit:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No cases available for Exa vNext bakeoff.")

    if not args.dry_plan and not EXA_API_KEY:
        raise SystemExit("EXA_API_KEY not set. Use --dry-plan to inspect the query plan without API calls.")

    collector = ExaCollector(api_key=EXA_API_KEY or "dry-plan")
    payload = run_exa_vnext_bakeoff(
        cases,
        collector=collector,
        results_per_request=args.results,
        dry_plan=args.dry_plan,
    )
    write_exa_vnext_bakeoff_outputs(payload, args.output_dir)
    summary = payload["summary"]["variants"]
    print(f"Wrote {args.output_dir / 'exa_vnext_bakeoff.json'}")
    print(f"Wrote {args.output_dir / 'exa_vnext_bakeoff.md'}")
    for variant, row in summary.items():
        print(
            "variant={variant} results={results} accepted={accepted} review={review} rejected={rejected} "
            "accepted_rate={accepted_rate:.1%} rejected_rate={rejected_rate:.1%} shadow_empty={shadow_empty}".format(
                variant=variant,
                results=row.get("result_count", 0),
                accepted=row.get("accepted", 0),
                review=row.get("review_required", 0),
                rejected=row.get("rejected", 0),
                accepted_rate=float(row.get("accepted_rate") or 0),
                rejected_rate=float(row.get("rejected_rate") or 0),
                shadow_empty=row.get("shadow_empty_exclusion_count", 0),
            )
        )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases-file", type=Path, help="JSON list of cases or object with cases/rows.")
    parser.add_argument(
        "--from-evidence-report",
        type=Path,
        default=Path("out/evidence_vnext/latest_batch_2026_06_17.json"),
        help="Use rows from an evidence vNext report as bakeoff cases.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--results", type=int, default=5)
    parser.add_argument("--dry-plan", action="store_true", help="Write planned queries without calling Exa.")
    parser.add_argument("--output-dir", type=Path, default=Path("out/exa_vnext_bakeoff"))
    return parser.parse_args(argv)


def _load_cases(args: argparse.Namespace):
    if args.cases_file:
        return load_cases_from_file(args.cases_file)
    if args.from_evidence_report and args.from_evidence_report.exists():
        return load_cases_from_evidence_report(args.from_evidence_report, limit=args.limit)
    return default_cases()


if __name__ == "__main__":
    raise SystemExit(main())
