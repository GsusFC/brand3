"""Manifest and bundle helpers for the Visual Signature corpus expansion pilot."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.corpus_expansion.corpus_expansion_models import (
    CORPUS_EXPANSION_MANIFEST_SCHEMA_VERSION,
    CorpusExpansionManifest,
    CorpusExpansionMetrics,
    CorpusExpansionReadinessAssessment,
    CorpusExpansionReviewQueue,
    validate_corpus_expansion_manifest_payload,
)
from src.visual_signature.corpus_expansion.corpus_metrics import (
    assess_corpus_expansion_readiness,
    build_corpus_expansion_metrics,
    corpus_expansion_metrics_markdown,
    validate_corpus_expansion_metrics,
)
from src.visual_signature.corpus_expansion.corpus_review_queue import (
    build_corpus_expansion_review_queue,
    review_queue_items_to_dicts,
    validate_corpus_expansion_review_queue,
    write_review_queue,
)
from src.visual_signature.corpus_expansion.corpus_sampling import build_default_corpus_expansion_seed


DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "corpus_expansion"


def build_corpus_expansion_manifest(
    queue: CorpusExpansionReviewQueue,
    metrics: CorpusExpansionMetrics,
    assessment: CorpusExpansionReadinessAssessment | None = None,
    *,
    pilot_run_id: str | None = None,
    generated_at: datetime | None = None,
) -> CorpusExpansionManifest:
    assessment = assessment or assess_corpus_expansion_readiness(metrics)
    known_limitations = list(metrics.known_limitations)
    if assessment.block_reasons:
        known_limitations.extend(
            [
                "Readiness is not yet broad enough for reviewed-corpus expansion.",
                *[f"Block reason: {reason}" for reason in assessment.block_reasons],
            ]
        )
    return CorpusExpansionManifest(
        schema_version=CORPUS_EXPANSION_MANIFEST_SCHEMA_VERSION,
        record_type="corpus_expansion_manifest",
        pilot_run_id=pilot_run_id or queue.pilot_run_id,
        generated_at=generated_at or datetime.now(timezone.utc),
        target_capture_count=metrics.target_capture_count,
        current_capture_count=metrics.current_capture_count,
        reviewed_capture_count=metrics.reviewed_capture_count,
        category_distribution=dict(metrics.category_distribution),
        confidence_distribution=dict(metrics.confidence_distribution),
        queue_state_distribution=dict(metrics.queue_state_distribution),
        contradiction_rate=metrics.contradiction_rate,
        unresolved_rate=metrics.unresolved_rate,
        reviewer_coverage=metrics.reviewer_coverage,
        readiness_scope=metrics.readiness_scope,
        readiness_status=assessment.readiness_status,
        known_limitations=known_limitations,
        metrics_file="pilot_metrics.json",
        review_queue_file="review_queue.json",
        notes=[
            "Evidence-only governance manifest.",
            "Capability presence in the corpus expansion pipeline does not imply production approval.",
            "Readiness is scope-dependent and separate from scoring, runtime, and training.",
        ],
    )


def build_corpus_expansion_manifest_markdown(
    manifest: CorpusExpansionManifest,
    metrics: CorpusExpansionMetrics,
    assessment: CorpusExpansionReadinessAssessment | None = None,
) -> str:
    assessment = assessment or assess_corpus_expansion_readiness(metrics)
    lines = [
        "# Visual Signature Corpus Expansion Manifest",
        "",
        "Evidence-only governance manifest for the reviewed-corpus expansion pilot.",
        "",
        "- Evidence-only: yes",
        "- Governance-only: yes",
        "- No scoring impact: yes",
        "- No runtime enablement: yes",
        "- No model-training enablement: yes",
        "",
        f"- Pilot run ID: `{manifest.pilot_run_id}`",
        f"- Generated at: {manifest.generated_at.isoformat()}",
        f"- Readiness scope: `{manifest.readiness_scope}`",
        f"- Readiness status: `{manifest.readiness_status}`",
        f"- Target capture count: {manifest.target_capture_count}",
        f"- Current capture count: {manifest.current_capture_count}",
        f"- Reviewed capture count: {manifest.reviewed_capture_count}",
        f"- Reviewer coverage: {_pct(manifest.reviewer_coverage)}",
        f"- Contradiction rate: {_pct(manifest.contradiction_rate)}",
        f"- Unresolved rate: {_pct(manifest.unresolved_rate)}",
        "",
        "## Current State",
        "",
        f"- This pilot is sized for 20-50 reviewed captures.",
        f"- Current reviewed captures: {manifest.reviewed_capture_count}",
        f"- Current total captures: {manifest.current_capture_count}",
        f"- Readiness remains `not_ready` until the reviewed corpus is expanded.",
        "",
        "## Category Distribution",
        "",
        "| Category | Count |",
        "| --- | ---: |",
    ]
    for category, count in sorted(manifest.category_distribution.items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(
        [
            "",
            "## Confidence Distribution",
            "",
            "| Bucket | Count |",
            "| --- | ---: |",
        ]
    )
    for bucket, count in sorted(manifest.confidence_distribution.items()):
        lines.append(f"| {bucket} | {count} |")
    lines.extend(
        [
            "",
            "## Readiness Thresholds",
            "",
            f"- Scope evaluated: `{assessment.readiness_scope}`",
            "- This result applies only to the evaluated scope.",
            "- It does not imply production, scoring, runtime, provider-pilot, or model-training readiness.",
        ]
    )
    if assessment.block_reasons:
        lines.extend(["", "## Block Reasons", ""])
        lines.extend(f"- {reason}" for reason in assessment.block_reasons)
    if assessment.warning_reasons:
        lines.extend(["", "## Warning Reasons", ""])
        lines.extend(f"- {reason}" for reason in assessment.warning_reasons)
    lines.extend(
        [
            "",
            "## Governance Notes",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in manifest.notes)
    lines.extend(
        [
            "",
            "## Current Limitations",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in manifest.known_limitations)
    return "\n".join(lines).rstrip()


def write_corpus_expansion_bundle(
    *,
    output_root: str | Path | None = None,
    pilot_run_id: str = "visual-signature-corpus-expansion-pilot-1",
    generated_at: datetime | None = None,
    target_capture_count: int = 20,
    seed_items: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    bundle_generated_at = generated_at or datetime.now(timezone.utc)
    queue = build_corpus_expansion_review_queue(
        pilot_run_id=pilot_run_id,
        generated_at=bundle_generated_at,
        target_capture_count=target_capture_count,
        seed_items=seed_items or build_default_corpus_expansion_seed(),
    )
    metrics = build_corpus_expansion_metrics(queue, target_capture_count=target_capture_count, generated_at=bundle_generated_at)
    assessment = assess_corpus_expansion_readiness(metrics)
    queue = queue.model_copy(update={"readiness_status": assessment.readiness_status})
    metrics = metrics.model_copy(update={"readiness_status": assessment.readiness_status})
    manifest = build_corpus_expansion_manifest(queue, metrics, assessment, pilot_run_id=pilot_run_id, generated_at=bundle_generated_at)

    outputs = {
        "corpus_expansion_manifest_json": str(root / "corpus_expansion_manifest.json"),
        "corpus_expansion_manifest_md": str(root / "corpus_expansion_manifest.md"),
        "review_queue_json": str(root / "review_queue.json"),
        "pilot_metrics_json": str(root / "pilot_metrics.json"),
    }

    write_review_queue(queue, outputs["review_queue_json"])
    _write_json(outputs["pilot_metrics_json"], metrics.model_dump(mode="json"))
    _write_json(outputs["corpus_expansion_manifest_json"], manifest.model_dump(mode="json"))
    Path(outputs["corpus_expansion_manifest_md"]).write_text(
        build_corpus_expansion_manifest_markdown(manifest, metrics, assessment) + "\n",
        encoding="utf-8",
    )
    return outputs


def assess_corpus_expansion_bundle(root: str | Path) -> CorpusExpansionReadinessAssessment:
    root = Path(root)
    errors = validate_corpus_expansion_bundle(root)
    if errors:
        return CorpusExpansionReadinessAssessment(
            schema_version="visual-signature-corpus-expansion-readiness-1",
            record_type="corpus_expansion_readiness",
            pilot_run_id="invalid-bundle",
            readiness_status="not_ready",
            block_reasons=["bundle_validation_failed", *errors],
            warning_reasons=[],
            thresholds_used={},
        )

    metrics = CorpusExpansionMetrics.model_validate(_load_json(root / "pilot_metrics.json"))
    return assess_corpus_expansion_readiness(metrics)


def validate_corpus_expansion_bundle(root: str | Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    manifest_path = root / "corpus_expansion_manifest.json"
    manifest_md_path = root / "corpus_expansion_manifest.md"
    queue_path = root / "review_queue.json"
    metrics_path = root / "pilot_metrics.json"
    for path, label in (
        (manifest_path, "manifest_missing"),
        (manifest_md_path, "manifest_md_missing"),
        (queue_path, "review_queue_missing"),
        (metrics_path, "pilot_metrics_missing"),
    ):
        if not path.exists():
            errors.append(label)
    if errors:
        return errors

    manifest_payload = _load_json(manifest_path)
    metrics_payload = _load_json(metrics_path)
    queue_payload = _load_json(queue_path)

    manifest_errors = validate_corpus_expansion_manifest_payload(manifest_payload)
    metrics_errors = validate_corpus_expansion_metrics(metrics_payload)
    queue_errors = validate_corpus_expansion_review_queue(queue_payload)
    errors.extend(f"manifest:{item}" for item in manifest_errors)
    errors.extend(f"metrics:{item}" for item in metrics_errors)
    errors.extend(f"queue:{item}" for item in queue_errors)
    if errors:
        return list(dict.fromkeys(errors))

    manifest = CorpusExpansionManifest.model_validate(manifest_payload)
    metrics = CorpusExpansionMetrics.model_validate(metrics_payload)
    queue = CorpusExpansionReviewQueue.model_validate(queue_payload)

    if manifest.pilot_run_id != metrics.pilot_run_id or manifest.pilot_run_id != queue.pilot_run_id:
        errors.append("pilot_run_id_mismatch")
    if manifest.target_capture_count != metrics.target_capture_count or manifest.target_capture_count != queue.target_capture_count:
        errors.append("target_capture_count_mismatch")
    if manifest.current_capture_count != metrics.current_capture_count or manifest.current_capture_count != queue.current_capture_count:
        errors.append("current_capture_count_mismatch")
    if manifest.reviewed_capture_count != metrics.reviewed_capture_count or manifest.reviewed_capture_count != queue.reviewed_capture_count:
        errors.append("reviewed_capture_count_mismatch")
    if manifest.category_distribution != metrics.category_distribution:
        errors.append("category_distribution_mismatch")
    if manifest.confidence_distribution != metrics.confidence_distribution:
        errors.append("confidence_distribution_mismatch")
    if manifest.queue_state_distribution != metrics.queue_state_distribution or manifest.queue_state_distribution != queue.queue_state_distribution:
        errors.append("queue_state_distribution_mismatch")
    if manifest.contradiction_rate != metrics.contradiction_rate:
        errors.append("contradiction_rate_mismatch")
    if manifest.unresolved_rate != metrics.unresolved_rate:
        errors.append("unresolved_rate_mismatch")
    if manifest.reviewer_coverage != metrics.reviewer_coverage:
        errors.append("reviewer_coverage_mismatch")
    if manifest.readiness_scope != metrics.readiness_scope or manifest.readiness_scope != queue.readiness_scope:
        errors.append("readiness_scope_mismatch")
    if manifest.readiness_status != metrics.readiness_status or manifest.readiness_status != queue.readiness_status:
        errors.append("readiness_status_mismatch")
    if metrics.reviewed_capture_count > metrics.current_capture_count:
        errors.append("metrics_reviewed_exceeds_total")
    if not 0.0 <= metrics.contradiction_rate <= 1.0:
        errors.append("metrics_contradiction_rate_out_of_bounds")
    if not 0.0 <= metrics.unresolved_rate <= 1.0:
        errors.append("metrics_unresolved_rate_out_of_bounds")
    if not 0.0 <= metrics.reviewer_coverage <= 1.0:
        errors.append("metrics_reviewer_coverage_out_of_bounds")
    if sum(metrics.category_distribution.values()) != metrics.current_capture_count:
        errors.append("metrics_category_distribution_mismatch")
    if sum(metrics.confidence_distribution.values()) != metrics.current_capture_count:
        errors.append("metrics_confidence_distribution_mismatch")
    if sum(metrics.queue_state_distribution.values()) != metrics.current_capture_count:
        errors.append("metrics_queue_state_distribution_mismatch")
    if len(queue.queue_items) != queue.current_capture_count:
        errors.append("queue_item_count_mismatch")
    reviewed_count = sum(1 for item in queue.queue_items if item.queue_state == "reviewed")
    if reviewed_count != queue.reviewed_capture_count:
        errors.append("queue_reviewed_count_mismatch")
    for index, item in enumerate(queue.queue_items, start=1):
        item_errors = validate_corpus_expansion_review_queue_item(item.model_dump(mode="json"))
        if item_errors:
            errors.extend(f"queue_item_{index}:{entry}" for entry in item_errors)
    return list(dict.fromkeys(errors))


def validate_corpus_expansion_manifest(payload: dict[str, Any]) -> list[str]:
    return validate_corpus_expansion_manifest_payload(payload)


def validate_corpus_expansion_review_queue_item(payload: dict[str, Any]) -> list[str]:
    from src.visual_signature.corpus_expansion.corpus_expansion_models import validate_corpus_expansion_queue_item

    return validate_corpus_expansion_queue_item(payload)


def _write_json(path: str | Path, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pct(value: float) -> str:
    return f"{value:.0%}"
