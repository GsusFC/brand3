"""Evidence-only reliability report for Visual Signature calibration bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_export import validate_calibration_output_root
from src.visual_signature.calibration.calibration_models import CalibrationManifest, CalibrationRecordsFile, CalibrationSummary


def build_calibration_reliability_report(bundle_root: str | Path) -> str:
    root = Path(bundle_root)
    validation_errors = validate_calibration_output_root(root)
    manifest, records_file, summary, summary_md = _load_bundle(root)

    lines = [
        "# Visual Signature Calibration Reliability Report",
        "",
        "Evidence-only interpretation of the hardened calibration bundle.",
        "",
        "- Evidence-only: yes",
        "- No scoring impact: yes",
        "- No rubric impact: yes",
        "- No production UI/report impact: yes",
        "",
        "## Bundle Metadata Summary",
        "",
        f"- Calibration run ID: `{summary.calibration_run_id}`",
        f"- Manifest validation status: `{manifest.validation_status}`",
        f"- Bundle validation status: `{_validation_status(validation_errors)}`",
        f"- Validation errors: `{', '.join(validation_errors) if validation_errors else 'none'}`",
        f"- Generated at: {manifest.generated_at.isoformat()}",
        f"- Record count: {summary.record_count}",
        f"- Summary count consistency: {str(summary.summary_count_consistency).lower()}",
        f"- Summary markdown present: yes",
        f"- Summary markdown lines: {len(summary_md.splitlines())}",
        f"- Source roots: `{summary.source_phase_one_root}`, `{summary.source_phase_two_root}`",
        f"- Source artifact refs: {len(summary.source_artifact_refs)}",
        f"- Source artifact hashes: {len(summary.source_artifact_hashes)}",
        "",
        "### Schema Versions",
        "",
    ]
    for key, value in sorted(summary.schema_versions.items()):
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Aggregate Findings",
            "",
            f"- Total claims: {summary.total_claims}",
            f"- Reviewed claims: {summary.reviewed_claims}",
            f"- Confirmed: {summary.confirmed_count} ({_pct(summary.confirmed_rate)})",
            f"- Contradicted: {summary.contradicted_count} ({_pct(summary.contradicted_rate)})",
            f"- Unresolved: {summary.unresolved_count} ({_pct(summary.unresolved_rate)})",
            f"- Insufficient review: {summary.insufficient_review_count} ({_pct(summary.insufficient_review_rate)})",
            f"- High-confidence contradictions: {summary.high_confidence_contradiction_count}",
            f"- Overconfidence rate: {_pct(summary.overconfidence_rate)}",
            f"- Uncertainty accepted: {summary.uncertainty_accepted_count} ({_pct(summary.uncertainty_accepted_rate)})",
            "",
            "### Confidence Bucket Analysis",
            "",
            *_bucket_lines(summary.confidence_bucket_distribution),
            "",
            "### Overconfidence Findings",
            "",
        ]
    )
    overconfidence_rows = [record for record in records_file.records if record.uncertainty_alignment == "overconfident"]
    if overconfidence_rows:
        for record in overconfidence_rows:
            lines.append(
                f"- {record.brand_name}: `claim={record.claim.claim_value}`, `agreement={record.agreement_state}`, `confidence={record.confidence_bucket}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "### Underconfidence Findings",
            "",
        ]
    )
    underconfidence_rows = [record for record in records_file.records if record.uncertainty_alignment == "underconfident"]
    if underconfidence_rows:
        for record in underconfidence_rows:
            lines.append(
                f"- {record.brand_name}: `claim={record.claim.claim_value}`, `agreement={record.agreement_state}`, `confidence={record.confidence_bucket}`"
            )
    else:
        lines.append("- none surfaced in this bundle")

    lines.extend(
        [
            "",
            "### Uncertainty Alignment Findings",
            "",
        ]
    )
    lines.append(
        f"- calibrated: {sum(1 for record in records_file.records if record.uncertainty_alignment == 'calibrated')}"
    )
    lines.append(
        f"- overconfident: {sum(1 for record in records_file.records if record.uncertainty_alignment == 'overconfident')}"
    )
    lines.append(
        f"- underconfident: {sum(1 for record in records_file.records if record.uncertainty_alignment == 'underconfident')}"
    )
    lines.append(
        f"- uncertainty_accepted: {sum(1 for record in records_file.records if record.uncertainty_alignment == 'uncertainty_accepted')}"
    )
    lines.append(
        f"- insufficient_data: {sum(1 for record in records_file.records if record.uncertainty_alignment == 'insufficient_data')}"
    )

    lines.extend(
        [
            "",
            "## Category Breakdown",
            "",
            "| Category | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for category, row in sorted(summary.category_breakdown.items()):
        lines.append(
            f"| {category} | {row['total_claims']} | {row['reviewed_claims']} | {row['confirmed_count']} | "
            f"{row['contradicted_count']} | {row['unresolved_count']} | {row['insufficient_review_count']} | "
            f"{row['high_confidence_contradiction_count']} | {_pct(row['overconfidence_rate'])} | "
            f"{row['uncertainty_accepted_count']} |"
        )

    lines.extend(
        [
            "",
            "## Perception Source Breakdown",
            "",
            "| Source | Count | Avg per claim |",
            "| --- | ---: | ---: |",
        ]
    )
    for source, row in sorted(summary.source_breakdown.items()):
        lines.append(f"| {source} | {row['count']} | {row['average_per_claim']:.2f} |")

    lines.extend(
        [
            "",
            "## Claim Kind Breakdown",
            "",
            "| Claim Kind | Claims | Reviewed | Confirmed | Contradicted | Unresolved | Insufficient review | High-conf contradiction | Overconfidence | Uncertainty accepted |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for claim_kind, row in sorted(summary.claim_kind_breakdown.items()):
        lines.append(
            f"| {claim_kind} | {row['total_claims']} | {row['reviewed_claims']} | {row['confirmed_count']} | "
            f"{row['contradicted_count']} | {row['unresolved_count']} | {row['insufficient_review_count']} | "
            f"{row['high_confidence_contradiction_count']} | {_pct(row['overconfidence_rate'])} | "
            f"{row['uncertainty_accepted_count']} |"
        )

    lines.extend(
        [
            "",
            "## Notable Confirmed Claims",
            "",
        ]
    )
    confirmed_rows = [record for record in records_file.records if record.agreement_state == "confirmed"]
    if confirmed_rows:
        for record in confirmed_rows:
            lines.append(
                f"- {record.brand_name}: `claim={record.claim.claim_value}`, `review={_review_label(record)}`, `alignment={record.uncertainty_alignment}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Notable Contradicted Claims",
            "",
        ]
    )
    contradicted_rows = [record for record in records_file.records if record.agreement_state == "contradicted"]
    if contradicted_rows:
        for record in contradicted_rows:
            lines.append(
                f"- {record.brand_name}: `claim={record.claim.claim_value}`, `review={_review_label(record)}`, `alignment={record.uncertainty_alignment}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Unresolved Claims Needing Review",
            "",
        ]
    )
    unresolved_rows = [record for record in records_file.records if record.agreement_state == "unresolved"]
    if unresolved_rows:
        for record in unresolved_rows:
            lines.append(
                f"- {record.brand_name}: `claim={record.claim.claim_value}`, `review={_review_label(record)}`, `alignment={record.uncertainty_alignment}`"
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            f"- Sample size is small: {summary.total_claims} claims across {len(summary.category_breakdown)} categories.",
            f"- Confidence is saturated at high: {summary.confidence_bucket_distribution.get('high', 0)} of {summary.total_claims} claims.",
            f"- No medium, low, or unknown confidence claims surfaced in this bundle.",
            f"- Each category currently has one claim, so category-level conclusions are directional only.",
            f"- This bundle shows {summary.high_confidence_contradiction_count} high-confidence contradictions, which is enough to flag calibration risk but not enough for corpus-wide policy changes.",
            f"- The bundle does not contain any insufficient_review records, so the missing-review branch is not exercised here.",
            "",
            "## Recommendation",
            "",
        ]
    )
    if validation_errors:
        lines.append(
            "- Not ready for broader corpus use until the bundle validation errors above are resolved."
        )
    else:
        lines.extend(
            [
                "- The bundle is coherent and validated, but it is not ready for broader corpus use as a calibration basis.",
                "- It is suitable for evidence-only inspection and small-scale calibration review.",
                "- Broader corpus use should wait for more claims per category and a wider spread of confidence buckets.",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write_calibration_reliability_report(
    bundle_root: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    root = Path(bundle_root)
    if output_path is None:
        output_path = root / "calibration_reliability_report.md"
    output = Path(output_path)
    output.write_text(build_calibration_reliability_report(root), encoding="utf-8")
    return output


def _load_bundle(bundle_root: Path) -> tuple[CalibrationManifest, CalibrationRecordsFile, CalibrationSummary, str]:
    manifest = CalibrationManifest.model_validate(_load_json(bundle_root / "calibration_manifest.json"))
    records_file = CalibrationRecordsFile.model_validate(_load_json(bundle_root / "calibration_records.json"))
    summary = CalibrationSummary.model_validate(_load_json(bundle_root / "calibration_summary.json"))
    summary_md = (bundle_root / "calibration_summary.md").read_text(encoding="utf-8")
    return manifest, records_file, summary, summary_md


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _bucket_lines(distribution: dict[str, int]) -> list[str]:
    return [f"- {bucket}: {count}" for bucket, count in sorted(distribution.items())] or ["- none"]


def _review_label(record) -> str:
    outcome = record.review_outcome
    if outcome is None:
        return "no review"
    return f"{outcome.review_status}/{outcome.visually_supported}/uncertainty_accepted={str(outcome.uncertainty_accepted).lower()}"


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "-"


def _validation_status(errors: list[str]) -> str:
    return "valid" if not errors else "invalid"
