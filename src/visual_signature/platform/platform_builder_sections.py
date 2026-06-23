"""Section builders for Visual Signature local platform payload."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.visual_signature.platform.platform_builder_constants import (
    GUARDRAILS,
    VISUAL_SIGNATURE_ARTIFACT_SPECS,
)
from src.visual_signature.platform.platform_models import PlatformArtifact
from src.visual_signature.platform.platform_models import PlatformSection
from src.visual_signature.platform.platform_builder_utils import _as_list
from src.visual_signature.platform.platform_builder_utils import _artifact_summary
from src.visual_signature.platform.platform_builder_utils import _safe_get
from src.visual_signature.platform.platform_builder_utils import _slugify
from src.visual_signature.platform.platform_builder_utils import _to_output_relative_path
from src.visual_signature.platform.platform_builder_utils import _load_json_if_exists
from src.visual_signature.platform.platform_builder_constants import PROJECT_ROOT


def build_sections(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
    scoring_summary: dict[str, Any],
    *,
    output_root: Path,
    visual_signature_root: Path,
) -> list[PlatformSection]:
    return [
        _brand3_overview_section(artifact_map, json_map, scoring_summary),
        _initial_scoring_section(artifact_map, scoring_summary),
        _visual_signature_section(artifact_map, json_map),
        _captures_section(
            artifact_map,
            json_map,
            output_root=output_root,
            visual_signature_root=visual_signature_root,
        ),
        _reviewer_section(
            artifact_map,
            json_map,
            output_root=output_root,
            visual_signature_root=visual_signature_root,
        ),
        _calibration_section(artifact_map, json_map),
        _governance_section(artifact_map, json_map),
        _corpus_expansion_section(
            artifact_map,
            json_map,
            output_root=output_root,
            visual_signature_root=visual_signature_root,
        ),
    ]


def _build_scoring_summary(*, scoring_output_root: Path, output_root: Path) -> dict[str, Any]:
    json_files = sorted(scoring_output_root.glob("*.json"), key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True) if scoring_output_root.exists() else []
    report_files = _discover_scoring_reports(scoring_output_root=scoring_output_root, output_root=output_root)
    score_items: list[dict[str, Any]] = []
    brands: set[str] = set()
    for path in json_files[:24]:
        payload = _load_json_if_exists(path)
        if not isinstance(payload, dict):
            continue
        item = _score_item_from_payload(payload, path=path, output_root=output_root)
        brands.add(str(item.get("brand_name") or path.stem))
        score_items.append(item)
    return {
        "output_count": len(json_files),
        "report_count": len(report_files),
        "brand_count": len(brands),
        "latest_outputs": [item.get("source_path") for item in score_items[:8]],
        "latest_reports": report_files[:8],
        "latest_report": report_files[0]["path"] if report_files else None,
        "score_items": score_items[:12],
    }


def _score_item_from_payload(payload: dict[str, Any], *, path: Path, output_root: Path) -> dict[str, Any]:
    dimensions = payload.get("dimensions") if isinstance(payload.get("dimensions"), dict) else {}
    composite_score = payload.get("composite_score", payload.get("score"))
    return {
        "brand_name": payload.get("brand") or _safe_get(payload.get("brand_profile"), "name") or path.stem,
        "url": payload.get("url") or _safe_get(payload.get("brand_profile"), "domain"),
        "composite_score": composite_score,
        "composite_reliable": payload.get("composite_reliable"),
        "data_quality": payload.get("data_quality"),
        "calibration_profile": payload.get("calibration_profile"),
        "dimension_scores": dimensions,
        "source_path": _to_output_relative_path(path, output_root=output_root),
    }


def _discover_scoring_reports(*, scoring_output_root: Path, output_root: Path) -> list[dict[str, Any]]:
    reports_root = scoring_output_root / "reports"
    if not reports_root.exists():
        return []
    report_paths = sorted(
        [*reports_root.glob("*/*/report.light.html"), *reports_root.glob("*/*/report.html")],
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    reports = []
    for path in report_paths[:24]:
        reports.append(
            {
                "brand_name": path.parents[1].name,
                "report_variant": path.stem,
                "path": _to_output_relative_path(path, output_root=output_root),
            }
        )
    return reports


def _scoring_dimensions_summary() -> list[dict[str, Any]]:
    try:
        from src.dimensions import DIMENSIONS
    except Exception:
        return []
    rows = []
    for key, dimension in DIMENSIONS.items():
        features = dimension.get("features", {}) if isinstance(dimension, dict) else {}
        rows.append(
            {
                "dimension": key,
                "description": dimension.get("description"),
                "weight": dimension.get("weight"),
                "feature_count": len(features),
                "rules": dimension.get("rules", []),
            }
        )
    return rows


def _brand3_overview_section(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
    scoring_summary: dict[str, Any],
) -> PlatformSection:
    present = sum(1 for artifact in artifact_map.values() if artifact.exists)
    required_missing = [artifact.label for artifact in artifact_map.values() if artifact.required and not artifact.exists]
    calibration_readiness = json_map.get("calibration_readiness") or {}
    governance_integrity = json_map.get("governance_integrity_report") or {}
    status = "degraded" if required_missing else "ready"
    return PlatformSection(
        key="brand3-overview",
        title="Brand3 Overview",
        status=status,
        summary="Unified local Brand3 dashboard for Initial Scoring artifacts and Visual Signature artifacts, kept as separate read-only layers.",
        badges=[
            f"{present}/{len(artifact_map)} artifacts discovered",
            f"scoring outputs: {scoring_summary.get('output_count', 0)}",
            f"visual signature: {calibration_readiness.get('status', 'unknown')}",
            f"governance: {governance_integrity.get('status', 'unknown')}",
        ],
        artifact_keys=["scoring_output_root", "scoring_reports_root", "scoring_dimensions_source", "technical_checkpoint", "reliable_visual_perception"],
        metrics={
            "required_missing": required_missing,
            "separation_principle": "Initial Scoring is displayed read-only; Visual Signature remains evidence-only and has no scoring impact.",
            "guardrail_count": len(GUARDRAILS),
            "latest_scoring_report": scoring_summary.get("latest_report"),
            "latest_visual_signature_checkpoint": _latest_existing_artifact(["technical_checkpoint", "calibration_governance_checkpoint"], artifact_map),
        },
        next_steps=[
            "Use Initial Scoring for existing score/report inspection only.",
            "Use Visual Signature sections for capture, review, calibration, governance, and corpus evidence only.",
            "Keep all source edits in the existing generators and artifact files, not in this platform payload.",
        ],
    )


def _initial_scoring_section(artifact_map: dict[str, PlatformArtifact], scoring_summary: dict[str, Any]) -> PlatformSection:
    has_outputs = bool(scoring_summary.get("output_count") or scoring_summary.get("report_count"))
    dimensions = _scoring_dimensions_summary()
    return PlatformSection(
        key="initial-scoring",
        title="Initial Scoring",
        status="ready" if has_outputs else "missing_artifacts",
        summary="Read-only view of existing Brand3 initial scoring outputs, reports, rubric dimensions, and score summaries.",
        badges=[
            f"outputs: {scoring_summary.get('output_count', 0)}",
            f"reports: {scoring_summary.get('report_count', 0)}",
            f"rubric dimensions: {len(dimensions)}",
            "read-only",
        ],
        artifact_keys=["scoring_output_root", "scoring_reports_root", "brand3_sqlite", "brand3_legacy_db", "scoring_dimensions_source"],
        metrics={
            "brand_count": scoring_summary.get("brand_count", 0),
            "latest_outputs": scoring_summary.get("latest_outputs", []),
            "latest_reports": scoring_summary.get("latest_reports", []),
            "rubric_dimensions": dimensions,
            "data_rule": "Existing scoring artifacts are displayed without recomputation or mutation.",
        },
        items=scoring_summary.get("score_items", []),
        next_steps=[
            "Open linked scoring reports/files for source detail.",
            "Keep scoring logic, rubric dimensions, and production reports unchanged.",
            "Regenerate scoring artifacts only through existing scoring scripts when that is explicitly intended.",
        ],
    )


def _visual_signature_section(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
) -> PlatformSection:
    visual_artifact_keys = {key for key, *_rest in VISUAL_SIGNATURE_ARTIFACT_SPECS}
    present = sum(1 for key in visual_artifact_keys if artifact_map.get(key) and artifact_map[key].exists)
    required_missing = [artifact_map[key].label for key in visual_artifact_keys if artifact_map.get(key) and artifact_map[key].required and not artifact_map[key].exists]
    calibration_readiness = json_map.get("calibration_readiness") or {}
    corpus_manifest = json_map.get("corpus_expansion_manifest") or {}
    governance_integrity = json_map.get("governance_integrity_report") or {}
    status = "degraded" if required_missing else "ready"
    return PlatformSection(
        key="visual-signature",
        title="Visual Signature",
        status=status,
        summary="Current Visual Signature status: raw evidence preserved, local-only review surface, no scoring impact.",
        badges=[
            f"{present}/{len(visual_artifact_keys)} artifacts discovered",
            f"calibration: {calibration_readiness.get('status', 'unknown')}",
            f"corpus: {corpus_manifest.get('readiness_status', 'unknown')}",
            f"governance: {governance_integrity.get('status', 'unknown')}",
        ],
        artifact_keys=["technical_checkpoint", "reliable_visual_perception", "calibration_readiness", "governance_integrity_report"],
        metrics={
            "required_missing": required_missing,
            "guardrail_count": len(GUARDRAILS),
            "raw_evidence_preservation": "raw screenshots and manifests remain source artifacts; clean attempts are displayed only when available",
            "scoring_impact": "none",
            "latest_checkpoint": _latest_existing_artifact(["technical_checkpoint", "calibration_governance_checkpoint"], artifact_map),
        },
        next_steps=[
            "Open Captures to inspect raw and full-page screenshots.",
            "Open Reviewer Workflow for pending queue items.",
            "Open Governance before considering any broader validation work.",
        ],
    )


def _captures_section(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
    *,
    output_root: Path,
    visual_signature_root: Path,
) -> PlatformSection:
    capture_manifest = json_map.get("capture_manifest") or {}
    dismissal_audit = json_map.get("dismissal_audit") or {}
    items = []
    for entry in _as_list(capture_manifest.get("results")):
        brand = str(entry.get("brand_name") or entry.get("capture_id") or "unknown")
        capture_id = str(entry.get("capture_id") or _slugify(brand))
        raw_path = _capture_path(entry.get("raw_screenshot_path") or entry.get("screenshot_path"), output_root=output_root, visual_signature_root=visual_signature_root)
        clean_path = _capture_path(entry.get("clean_attempt_screenshot_path"), output_root=output_root, visual_signature_root=visual_signature_root)
        full_page_path = _full_page_path(capture_id, output_root=output_root, visual_signature_root=visual_signature_root)
        items.append(
            {
                "brand_name": brand,
                "capture_id": capture_id,
                "perceptual_state": entry.get("perceptual_state"),
                "dismissal_attempted": entry.get("dismissal_attempted"),
                "dismissal_successful": entry.get("dismissal_successful"),
                "dismissal_eligibility": entry.get("dismissal_eligibility"),
                "obstruction": _obstruction_summary(entry),
                "screenshots": [
                    item
                    for item in (
                        {"label": "raw", "path": raw_path},
                        {"label": "clean attempt", "path": clean_path},
                        {"label": "full page", "path": full_page_path},
                    )
                    if item["path"]
                ],
            }
        )
    return PlatformSection(
        key="captures",
        title="Captures",
        status="ready" if capture_manifest else "missing",
        summary="Capture manifest, screenshots, obstruction state, and dismissal audit.",
        badges=[
            f"ok: {capture_manifest.get('ok', 0)}",
            f"errors: {capture_manifest.get('error', 0)}",
            f"dismissal success: {dismissal_audit.get('dismissal_success_rate', 'unknown')}",
        ],
        artifact_keys=["capture_manifest", "dismissal_audit", "screenshots_readme"],
        metrics={
            "total": capture_manifest.get("total"),
            "attempt_dismiss_obstructions": capture_manifest.get("attempt_dismiss_obstructions"),
            "state_distribution": dismissal_audit.get("state_distribution", {}),
            "before_severity_distribution": dismissal_audit.get("before_severity_distribution", {}),
        },
        items=items,
        next_steps=["Review full-page screenshots first, then compare raw vs clean attempts where present."],
    )


def _reviewer_section(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
    *,
    output_root: Path,
    visual_signature_root: Path,
) -> PlatformSection:
    queue = json_map.get("review_queue") or {}
    pilot = json_map.get("reviewer_workflow_pilot") or {}
    queue_items = _as_list(queue.get("queue_items"))
    selected_ids = set(_as_list(pilot.get("selected_review_queue_item_ids")))
    items = []
    for item in queue_items:
        queue_id = item.get("queue_id")
        if queue_id in selected_ids or item.get("queue_state") in {"queued", "needs_additional_evidence"}:
            packet_path = visual_signature_root / "corpus_expansion" / "reviewer_packets" / f"{item.get('capture_id')}.md"
            items.append(
                {
                    "queue_id": queue_id,
                    "brand_name": item.get("brand_name"),
                    "category": item.get("category"),
                    "queue_state": item.get("queue_state"),
                    "confidence_bucket": item.get("confidence_bucket"),
                    "selected_for_pilot": queue_id in selected_ids,
                    "packet_path": _to_output_relative_path(packet_path, output_root=output_root) if packet_path.exists() else None,
                }
            )
    return PlatformSection(
        key="reviewer-workflow",
        title="Reviewer Workflow",
        status=pilot.get("pilot_status", "unknown"),
        summary="Human reviewer queue, workflow pilot, reviewer packets, and embedded viewer entry point.",
        badges=[
            f"selected: {pilot.get('selected_review_queue_item_count', len(selected_ids))}",
            f"pending states: {sum(1 for item in queue_items if item.get('queue_state') in {'queued', 'needs_additional_evidence'})}",
        ],
        artifact_keys=["review_queue", "reviewer_workflow_pilot", "reviewer_packet_index", "reviewer_viewer"],
        metrics={
            "queue_state_distribution": queue.get("queue_state_distribution", {}),
            "selected_review_queue_item_ids": list(selected_ids),
            "reviewer_viewer_path": artifact_map["reviewer_viewer"].path,
        },
        items=items,
        next_steps=["Open the embedded reviewer viewer for item-level review, then record real review outputs only through the approved workflow."],
    )


def _calibration_section(artifact_map: dict[str, PlatformArtifact], json_map: dict[str, dict[str, Any] | None]) -> PlatformSection:
    manifest = json_map.get("calibration_manifest") or {}
    summary = json_map.get("calibration_summary") or {}
    readiness = json_map.get("calibration_readiness") or {}
    items = []
    for claim in _as_list(summary.get("reviewed_claims"))[:12]:
        items.append(
            {
                "brand_name": claim.get("brand_name"),
                "category": claim.get("category"),
                "claim_kind": claim.get("claim_kind"),
                "agreement": claim.get("agreement"),
                "confidence_bucket": claim.get("confidence_bucket"),
            }
        )
    return PlatformSection(
        key="calibration",
        title="Calibration",
        status=readiness.get("status", manifest.get("validation_status", "unknown")),
        summary="Calibration manifest, records, summary, reliability report, and readiness status.",
        badges=[
            f"records: {manifest.get('record_count', summary.get('record_count', 'unknown'))}",
            f"reviewed: {readiness.get('reviewed_claims', summary.get('reviewed_claims', 'unknown'))}",
            f"bundle valid: {readiness.get('bundle_valid', 'unknown')}",
        ],
        artifact_keys=["calibration_manifest", "calibration_records", "calibration_summary", "calibration_reliability_report", "calibration_readiness", "calibration_governance_checkpoint"],
        metrics={
            "confirmed_rate": summary.get("confirmed_rate"),
            "contradiction_rate": readiness.get("contradiction_rate", summary.get("contradicted_rate")),
            "overconfidence_rate": readiness.get("overconfidence_rate", summary.get("overconfidence_rate")),
            "block_reasons": readiness.get("block_reasons", []),
            "recommendation": readiness.get("recommendation"),
        },
        items=items,
        next_steps=["Address readiness block reasons before treating calibration as broader-corpus ready."],
    )


def _governance_section(artifact_map: dict[str, PlatformArtifact], json_map: dict[str, dict[str, Any] | None]) -> PlatformSection:
    registry = json_map.get("capability_registry") or {}
    matrix = json_map.get("runtime_policy_matrix") or {}
    integrity = json_map.get("governance_integrity_report") or {}
    plan = json_map.get("three_track_validation_plan") or {}
    items = []
    for capability in _as_list(registry.get("capabilities"))[:12]:
        items.append(
            {
                "capability_id": capability.get("capability_id"),
                "layer": capability.get("layer"),
                "maturity_state": capability.get("maturity_state"),
                "evidence_status": capability.get("evidence_status"),
                "production_enabled": capability.get("production_enabled", False),
            }
        )
    return PlatformSection(
        key="governance",
        title="Governance",
        status=integrity.get("status", "unknown"),
        summary="Capability registry, runtime policy matrix, integrity report, and three-track validation plan.",
        badges=[
            f"capabilities: {registry.get('capability_count', matrix.get('capability_count', 'unknown'))}",
            f"policies: {matrix.get('policy_count', 'unknown')}",
            f"errors: {integrity.get('error_count', 'unknown')}",
            f"warnings: {integrity.get('warning_count', 'unknown')}",
        ],
        artifact_keys=["capability_registry", "runtime_policy_matrix", "governance_integrity_report", "three_track_validation_plan", "technical_checkpoint", "reliable_visual_perception"],
        metrics={
            "readiness_status": integrity.get("readiness_status"),
            "recommended_order": plan.get("recommended_order", []),
            "global_constraints": plan.get("global_constraints", []),
            "runtime_mutation_policy": matrix.get("runtime_mutation_policy", {}),
        },
        items=items,
        next_steps=["Keep production_enabled false for every capability until separate governance changes explicitly approve otherwise."],
    )


def _corpus_expansion_section(
    artifact_map: dict[str, PlatformArtifact],
    json_map: dict[str, dict[str, Any] | None],
    *,
    output_root: Path,
    visual_signature_root: Path,
) -> PlatformSection:
    manifest = json_map.get("corpus_expansion_manifest") or {}
    queue = json_map.get("review_queue") or {}
    metrics = json_map.get("pilot_metrics") or {}
    pilot = json_map.get("reviewer_workflow_pilot") or {}
    items = []
    for item in _as_list(queue.get("queue_items")):
        items.append(
            {
                "queue_id": item.get("queue_id"),
                "brand_name": item.get("brand_name"),
                "category": item.get("category"),
                "queue_state": item.get("queue_state"),
                "review_outcome": item.get("review_outcome"),
            }
        )
    return PlatformSection(
        key="corpus-expansion",
        title="Corpus Expansion",
        status=manifest.get("readiness_status", queue.get("readiness_status", "unknown")),
        summary="Corpus expansion manifest, review queue, pilot metrics, reviewer workflow pilot, and packet exports.",
        badges=[
            f"captures: {manifest.get('current_capture_count', queue.get('current_capture_count', 'unknown'))}/{manifest.get('target_capture_count', queue.get('target_capture_count', 'unknown'))}",
            f"reviewed: {manifest.get('reviewed_capture_count', queue.get('reviewed_capture_count', 'unknown'))}",
            f"reviewer coverage: {manifest.get('reviewer_coverage', 'unknown')}",
        ],
        artifact_keys=["corpus_expansion_manifest", "pilot_metrics", "review_queue", "reviewer_workflow_pilot", "reviewer_packet_index", "corpus_expansion_markdown"],
        metrics={
            "queue_state_distribution": manifest.get("queue_state_distribution", queue.get("queue_state_distribution", {})),
            "confidence_distribution": manifest.get("confidence_distribution", queue.get("confidence_distribution", {})),
            "category_distribution": manifest.get("category_distribution", queue.get("category_distribution", {})),
            "known_limitations": manifest.get("known_limitations", []),
            "pilot_status": pilot.get("pilot_status"),
            "pilot_metrics": _artifact_summary(metrics),
        },
        items=items,
        next_steps=["Increase category depth and reviewed captures before using this as anything beyond a pilot scaffold."],
    )


def _obstruction_summary(entry: dict[str, Any]) -> dict[str, Any]:
    obstruction = entry.get("after_obstruction") or entry.get("obstruction") or {}
    if not isinstance(obstruction, dict):
        obstruction = {}
    return {
        "present": obstruction.get("present"),
        "severity": obstruction.get("severity"),
        "type": obstruction.get("type") or obstruction.get("obstruction_type"),
        "confidence": obstruction.get("confidence"),
    }


def _capture_path(value: Any, *, output_root: Path, visual_signature_root: Path) -> str | None:
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return _to_output_relative_path(path, output_root=output_root) if path.exists() else None


def _full_page_path(capture_id: str, *, output_root: Path, visual_signature_root: Path) -> str | None:
    path = visual_signature_root / "screenshots" / f"{capture_id}.full-page.png"
    return _to_output_relative_path(path, output_root=output_root) if path.exists() else None


def _latest_existing_artifact(keys: list[str], artifact_map: dict[str, PlatformArtifact]) -> str | None:
    for key in keys:
        artifact = artifact_map.get(key)
        if artifact and artifact.exists:
            return artifact.path
    return None
