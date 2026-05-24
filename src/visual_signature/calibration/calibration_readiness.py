"""Readiness gate for broader Visual Signature calibration corpus use."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.calibration_export import validate_calibration_output_root
from src.visual_signature.calibration.calibration_models import (
    CalibrationManifest,
    CalibrationRecordsFile,
    CalibrationSummary,
)
from src.visual_signature.calibration.readiness_models import (
    CALIBRATION_READINESS_SCHEMA_VERSION,
    CoverageStats,
    ReadinessResult,
    ReadinessScope,
    ReadinessStatus,
    ReadinessThresholds,
    validate_readiness_result,
)
from src.visual_signature.phase_zero.models import PHASE_ZERO_TAXONOMY_VERSION


DEFAULT_READINESS_THRESHOLDS = ReadinessThresholds(
    minimum_total_claims=15,
    minimum_reviewed_claims=15,
    minimum_categories=3,
    minimum_claims_per_category=3,
    minimum_confidence_buckets=3,
    maximum_contradiction_rate=0.25,
    maximum_high_confidence_contradictions=1,
    maximum_unresolved_rate=0.25,
)

STANDARD_CONFIDENCE_BUCKETS = ("low", "medium", "high", "unknown")
DEFAULT_READINESS_SCOPE: ReadinessScope = "broader_corpus_use"


def build_calibration_readiness(
    bundle_root: str | Path,
    *,
    corpus_manifest_path: str | Path | None = None,
    thresholds: ReadinessThresholds | None = None,
    readiness_scope: ReadinessScope = DEFAULT_READINESS_SCOPE,
) -> ReadinessResult:
    root = Path(bundle_root)
    threshold_model = thresholds or DEFAULT_READINESS_THRESHOLDS
    scope_thresholds = _thresholds_for_scope(readiness_scope, threshold_model)
    validation_errors = validate_calibration_output_root(root)
    manifest, records_file, summary = _load_bundle(root)
    corpus_manifest, corpus_manifest_ref = _load_corpus_manifest(corpus_manifest_path)

    record_count = summary.record_count if summary is not None else records_file.record_count if records_file is not None else 0
    reviewed_claims = summary.reviewed_claims if summary is not None else _reviewed_claims(records_file)
    contradiction_rate = summary.contradicted_rate if summary is not None else 0.0
    unresolved_rate = summary.unresolved_rate if summary is not None else 0.0
    overconfidence_rate = summary.overconfidence_rate if summary is not None else 0.0
    category_coverage = _category_coverage(summary, records_file, scope_thresholds.minimum_claims_per_category)
    confidence_bucket_coverage = _confidence_bucket_coverage(records_file, scope_thresholds.minimum_confidence_buckets)
    category_count = sum(1 for row in category_coverage.values() if row.count > 0)
    confidence_bucket_count = sum(1 for row in confidence_bucket_coverage.values() if row.count > 0)
    high_confidence_contradictions = summary.high_confidence_contradiction_count if summary is not None else 0

    block_reasons: list[str] = []
    warning_reasons: list[str] = []

    if readiness_scope != DEFAULT_READINESS_SCOPE:
        warning_reasons.append(f"unsupported_scope:{readiness_scope}")
        warning_reasons.append("unsupported_scopes_do_not_reuse_broader_corpus_use_thresholds")

    if validation_errors:
        block_reasons.append("bundle_validation_failed")
    if summary is not None and summary.summary_count_consistency is not True:
        block_reasons.append("summary_count_inconsistent")

    if record_count < threshold_model.minimum_total_claims:
        block_reasons.append("small_sample_size")
    if reviewed_claims < threshold_model.minimum_reviewed_claims:
        block_reasons.append("insufficient_reviewed_claims")
    if category_count < threshold_model.minimum_categories:
        block_reasons.append("insufficient_category_depth")
    if any(row.count < threshold_model.minimum_claims_per_category for row in category_coverage.values() if row.count > 0):
        block_reasons.append("insufficient_category_depth")
    if confidence_bucket_count < threshold_model.minimum_confidence_buckets:
        block_reasons.append("insufficient_confidence_spread")
    if contradiction_rate > threshold_model.maximum_contradiction_rate:
        block_reasons.append("contradiction_rate_too_high")
    if high_confidence_contradictions > threshold_model.maximum_high_confidence_contradictions:
        block_reasons.append("high_confidence_contradictions_too_high")
    if unresolved_rate > threshold_model.maximum_unresolved_rate:
        block_reasons.append("unresolved_rate_too_high")

    if corpus_manifest_ref is None:
        warning_reasons.append("corpus_manifest_missing")
    elif corpus_manifest is not None:
        corpus_categories = corpus_manifest.get("categories") if isinstance(corpus_manifest, dict) else []
        if isinstance(corpus_categories, list) and corpus_categories:
            corpus_category_count = len(corpus_categories)
            if category_count < corpus_category_count:
                warning_reasons.append(
                    f"corpus_category_coverage_limited:{category_count}/{corpus_category_count}"
                )
        corpus_minimums = corpus_manifest.get("minimums") if isinstance(corpus_manifest, dict) else {}
        if isinstance(corpus_minimums, dict) and corpus_minimums:
            warning_reasons.append("corpus_manifest_loaded")

    status: ReadinessStatus = "ready" if not block_reasons else "not_ready"
    recommendation = (
        "Proceed with broader corpus use under the current calibration thresholds."
        if status == "ready"
        else "Hold broader corpus use until sample size, category depth, and confidence spread improve."
    )
    if validation_errors:
        recommendation = "Fix bundle validation errors before re-evaluating readiness."

    result = ReadinessResult(
        schema_version=CALIBRATION_READINESS_SCHEMA_VERSION,
        taxonomy_version=PHASE_ZERO_TAXONOMY_VERSION,
        record_type="calibration_readiness",
        readiness_scope=readiness_scope,
        calibration_run_id=str(summary.calibration_run_id if summary is not None else manifest.calibration_run_id if manifest is not None else "unknown"),
        checked_at=datetime.now(timezone.utc),
        status=status,
        block_reasons=_unique(block_reasons),
        warning_reasons=_unique(warning_reasons),
        bundle_valid=not validation_errors,
        validation_errors=list(validation_errors),
        source_corpus_manifest_path=corpus_manifest_ref,
        summary_count_consistency=bool(summary.summary_count_consistency if summary is not None else False),
        record_count=record_count,
        reviewed_claims=reviewed_claims,
        category_coverage=category_coverage,
        confidence_bucket_coverage=confidence_bucket_coverage,
        contradiction_rate=contradiction_rate,
        unresolved_rate=unresolved_rate,
        overconfidence_rate=overconfidence_rate,
        minimum_thresholds_used=threshold_model,
        recommendation=recommendation,
        notes=_notes(
            validation_errors,
            corpus_manifest,
            threshold_model,
            category_count,
            confidence_bucket_count,
            readiness_scope,
        ),
    )
    return result


def write_calibration_readiness(
    bundle_root: str | Path,
    *,
    corpus_manifest_path: str | Path | None = None,
    output_json_path: str | Path | None = None,
    output_md_path: str | Path | None = None,
    thresholds: ReadinessThresholds | None = None,
    readiness_scope: ReadinessScope = DEFAULT_READINESS_SCOPE,
) -> dict[str, str]:
    root = Path(bundle_root)
    readiness = build_calibration_readiness(
        root,
        corpus_manifest_path=corpus_manifest_path,
        thresholds=thresholds,
        readiness_scope=readiness_scope,
    )
    output_json = Path(output_json_path) if output_json_path is not None else root / "calibration_readiness.json"
    output_md = Path(output_md_path) if output_md_path is not None else root / "calibration_readiness.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(readiness.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_md.write_text(calibration_readiness_markdown(readiness) + "\n", encoding="utf-8")
    return {"calibration_readiness_json": str(output_json), "calibration_readiness_md": str(output_md)}


def calibration_readiness_markdown(result: ReadinessResult) -> str:
    lines = [
        "# Visual Signature Calibration Readiness",
        "",
        "Evidence-only readiness gate for broader calibration corpus use.",
        "",
        "- Evidence-only: yes",
        "- No scoring impact: yes",
        "- No rubric impact: yes",
        "- No production UI/report impact: yes",
        "- Missing review is insufficient_review: yes",
        "- Unclear review is unresolved: yes",
        "",
        "## Bundle Metadata",
        "",
        f"- Calibration run ID: `{result.calibration_run_id}`",
        f"- Checked at: {result.checked_at.isoformat()}",
        f"- Scope evaluated: `{result.readiness_scope}`",
        f"- Status: `{result.status}`",
        f"- Bundle valid: {str(result.bundle_valid).lower()}",
        f"- Summary count consistency: {str(result.summary_count_consistency).lower()}",
        f"- Record count: {result.record_count}",
        f"- Reviewed claims: {result.reviewed_claims}",
        f"- Source corpus manifest: `{result.source_corpus_manifest_path or 'missing'}`",
        "",
        "### Thresholds Used",
        "",
        f"- Minimum total claims: {result.minimum_thresholds_used.minimum_total_claims}",
        f"- Minimum reviewed claims: {result.minimum_thresholds_used.minimum_reviewed_claims}",
        f"- Minimum categories: {result.minimum_thresholds_used.minimum_categories}",
        f"- Minimum claims per category: {result.minimum_thresholds_used.minimum_claims_per_category}",
        f"- Minimum confidence buckets: {result.minimum_thresholds_used.minimum_confidence_buckets}",
        f"- Maximum contradiction rate: {_pct(result.minimum_thresholds_used.maximum_contradiction_rate)}",
        f"- Maximum high-confidence contradictions: {result.minimum_thresholds_used.maximum_high_confidence_contradictions}",
        f"- Maximum unresolved rate: {_pct(result.minimum_thresholds_used.maximum_unresolved_rate)}",
        "",
        "### Scope Note",
        "",
        "- This `ready` / `not_ready` result applies only to the scope above.",
        "- It does not imply production readiness, scoring readiness, runtime readiness, provider-pilot readiness, or model-training readiness.",
        "- Unsupported scopes are reported via warnings and do not silently reuse broader corpus thresholds.",
        "",
        "## Summary Metrics",
        "",
        f"- Contradiction rate: {_pct(result.contradiction_rate)}",
        f"- Unresolved rate: {_pct(result.unresolved_rate)}",
        f"- Overconfidence rate: {_pct(result.overconfidence_rate)}",
        "",
        "## Block Reasons",
        "",
    ]
    if result.block_reasons:
        lines.extend(f"- {reason}" for reason in result.block_reasons)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Warning Reasons",
            "",
        ]
    )
    if result.warning_reasons:
        lines.extend(f"- {reason}" for reason in result.warning_reasons)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Category Coverage",
            "",
            "| Category | Claims | Reviewed | Share | Min required | Meets minimum |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for category, row in sorted(result.category_coverage.items()):
        lines.append(
            f"| {category} | {row.count} | {row.reviewed_count} | {_pct(row.share)} | {row.minimum_required} | {str(row.meets_minimum).lower()} |"
        )

    lines.extend(
        [
            "",
            "## Confidence Bucket Coverage",
            "",
            "| Bucket | Claims | Reviewed | Share | Min required | Meets minimum |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for bucket, row in sorted(result.confidence_bucket_coverage.items()):
        lines.append(
            f"| {bucket} | {row.count} | {row.reviewed_count} | {_pct(row.share)} | {row.minimum_required} | {str(row.meets_minimum).lower()} |"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- {result.recommendation}",
            "",
            "## Notes",
            "",
        ]
    )
    if result.notes:
        lines.extend(f"- {note}" for note in result.notes)
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip()


def validate_calibration_readiness_result(payload: dict[str, Any]) -> list[str]:
    return validate_readiness_result(payload)


def _load_bundle(root: Path) -> tuple[CalibrationManifest | None, CalibrationRecordsFile | None, CalibrationSummary | None]:
    manifest = _load_model(root / "calibration_manifest.json", CalibrationManifest)
    records_file = _load_model(root / "calibration_records.json", CalibrationRecordsFile)
    summary = _load_model(root / "calibration_summary.json", CalibrationSummary)
    return manifest, records_file, summary


def _load_model(path: Path, model) -> Any | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return model.model_validate(payload)


def _load_corpus_manifest(path: str | Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if path is None:
        default_path = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "calibration_corpus" / "corpus_manifest.json"
        if not default_path.exists():
            return None, None
        path = default_path
    corpus_path = Path(path)
    if not corpus_path.exists():
        return None, _display_path(corpus_path)
    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None, _display_path(corpus_path)


def _category_coverage(
    summary: CalibrationSummary | None,
    records_file: CalibrationRecordsFile | None,
    minimum_required: int,
) -> dict[str, CoverageStats]:
    if summary is not None:
        source = summary.category_breakdown
    elif records_file is not None:
        source = _category_counts_from_records(records_file)
    else:
        source = {}
    total = sum(row.get("total_claims", 0) for row in source.values())
    if total <= 0:
        return {}
    coverage: dict[str, CoverageStats] = {}
    for category, row in sorted(source.items()):
        count = int(row.get("total_claims", 0))
        reviewed_count = int(row.get("reviewed_claims", 0))
        coverage[category] = CoverageStats(
            count=count,
            share=round(count / total, 3) if total else 0.0,
            meets_minimum=count >= minimum_required,
            minimum_required=minimum_required,
            reviewed_count=reviewed_count,
        )
    return coverage


def _category_counts_from_records(records_file: CalibrationRecordsFile) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for record in records_file.records:
        row = counts.setdefault(record.category, {"total_claims": 0, "reviewed_claims": 0})
        row["total_claims"] += 1
        if record.review_outcome is not None:
            row["reviewed_claims"] += 1
    return counts


def _confidence_bucket_coverage(
    records_file: CalibrationRecordsFile | None,
    minimum_required: int,
) -> dict[str, CoverageStats]:
    counts = {bucket: 0 for bucket in STANDARD_CONFIDENCE_BUCKETS}
    reviewed_counts = {bucket: 0 for bucket in STANDARD_CONFIDENCE_BUCKETS}
    if records_file is not None:
        total = len(records_file.records)
        for record in records_file.records:
            bucket = str(record.confidence_bucket or "unknown")
            if bucket not in counts:
                counts[bucket] = 0
                reviewed_counts[bucket] = 0
            counts[bucket] += 1
            if record.review_outcome is not None:
                reviewed_counts[bucket] += 1
    else:
        total = 0
    total = total or sum(counts.values())
    if total <= 0:
        total = 1
    return {
        bucket: CoverageStats(
            count=count,
            share=round(count / total, 3) if total else 0.0,
            meets_minimum=count >= 1,
            minimum_required=1,
            reviewed_count=reviewed_counts.get(bucket, 0),
        )
        for bucket, count in sorted(counts.items())
    }


def _reviewed_claims(records_file: CalibrationRecordsFile | None) -> int:
    if records_file is None:
        return 0
    return sum(1 for record in records_file.records if record.review_outcome is not None)


def _notes(
    validation_errors: list[str],
    corpus_manifest: dict[str, Any] | None,
    thresholds: ReadinessThresholds,
    category_count: int,
    confidence_bucket_count: int,
    readiness_scope: ReadinessScope,
) -> list[str]:
    notes = [
        "Evidence-only readiness gate.",
        "No scoring, rubric dimensions, production reports, or UI are modified.",
        f"Scope evaluated: {readiness_scope}",
        "Bundle validation must pass before readiness can be positive.",
        f"Observed categories: {category_count}",
        f"Observed confidence buckets: {confidence_bucket_count}",
        f"Validation errors: {len(validation_errors)}",
    ]
    if corpus_manifest is not None:
        corpus_categories = corpus_manifest.get("categories")
        if isinstance(corpus_categories, list):
            notes.append(f"Corpus manifest categories: {len(corpus_categories)}")
        corpus_minimums = corpus_manifest.get("minimums")
        if isinstance(corpus_minimums, dict) and corpus_minimums.get("broader_calibration_interpretable_records") is not None:
            notes.append(
                "Corpus manifest broader calibration target: "
                f"{corpus_minimums.get('broader_calibration_interpretable_records')}"
            )
    notes.append(
        "Thresholds are conservative and intended to block broader corpus use until sample size and spread improve."
    )
    return notes


def _thresholds_for_scope(scope: ReadinessScope, thresholds: ReadinessThresholds) -> ReadinessThresholds:
    if scope != DEFAULT_READINESS_SCOPE:
        return thresholds
    return thresholds


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _display_path(path: Path) -> str:
    project_root = Path(__file__).resolve().parents[3]
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def _pct(value: float) -> str:
    return f"{value:.0%}"
