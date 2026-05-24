"""Build the offline Brand3 platform dashboard."""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.platform.platform_models import PlatformArtifact
from src.visual_signature.platform.platform_models import PlatformBundle
from src.visual_signature.platform.platform_models import PlatformSection


VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION = "brand3-platform-1"
VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE = "brand3_platform_bundle"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VISUAL_SIGNATURE_ROOT = PROJECT_ROOT / "examples" / "visual_signature"
DEFAULT_SCORING_OUTPUT_ROOT = PROJECT_ROOT / "output"
DEFAULT_OUTPUT_ROOT = DEFAULT_VISUAL_SIGNATURE_ROOT / "platform"

GUARDRAILS = [
    "read-only local navigation surface",
    "Initial Scoring and Visual Signature remain separate layers",
    "no Visual Signature to scoring integration",
    "no scoring logic changes",
    "no rubric dimension changes",
    "no production UI or report impact",
    "no runtime behavior changes",
    "no provider execution",
    "no model training",
    "no runtime mutation enablement",
    "no capture behavior changes",
    "JSON remains source of truth",
    "Markdown remains audit/export",
]


VISUAL_SIGNATURE_ARTIFACT_SPECS = [
    ("capture_manifest", "Capture manifest", "screenshots/capture_manifest.json", "json", True),
    ("dismissal_audit", "Dismissal audit", "screenshots/dismissal_audit.json", "json", True),
    ("screenshots_readme", "Screenshots README", "screenshots/README.md", "markdown", False),
    ("review_queue", "Review queue", "corpus_expansion/review_queue.json", "json", True),
    ("reviewer_workflow_pilot", "Reviewer workflow pilot", "corpus_expansion/reviewer_workflow_pilot.json", "json", True),
    ("reviewer_packet_index", "Reviewer packet index", "corpus_expansion/reviewer_packets/reviewer_packet_index.md", "markdown", False),
    ("reviewer_viewer", "Reviewer viewer", "corpus_expansion/reviewer_viewer/index.html", "html", True),
    ("calibration_manifest", "Calibration manifest", "calibration/calibration_manifest.json", "json", True),
    ("calibration_records", "Calibration records", "calibration/calibration_records.json", "json", True),
    ("calibration_summary", "Calibration summary", "calibration/calibration_summary.json", "json", True),
    ("calibration_reliability_report", "Calibration reliability report", "calibration/calibration_reliability_report.md", "markdown", False),
    ("calibration_readiness", "Calibration readiness", "calibration/calibration_readiness.json", "json", True),
    ("calibration_governance_checkpoint", "Calibration governance checkpoint", "calibration/calibration_governance_checkpoint.md", "markdown", False),
    ("capability_registry", "Capability registry", "governance/capability_registry.json", "json", True),
    ("runtime_policy_matrix", "Runtime policy matrix", "governance/runtime_policy_matrix.json", "json", True),
    ("governance_integrity_report", "Governance integrity report", "governance/governance_integrity_report.json", "json", True),
    ("three_track_validation_plan", "Three-track validation plan", "governance/three_track_validation_plan.json", "json", True),
    ("technical_checkpoint", "Technical checkpoint", "technical_checkpoint.md", "markdown", False),
    ("reliable_visual_perception", "Reliable visual perception", "reliable_visual_perception.md", "markdown", False),
    ("corpus_expansion_manifest", "Corpus expansion manifest", "corpus_expansion/corpus_expansion_manifest.json", "json", True),
    ("pilot_metrics", "Pilot metrics", "corpus_expansion/pilot_metrics.json", "json", True),
    ("corpus_expansion_markdown", "Corpus expansion markdown", "corpus_expansion/corpus_expansion_manifest.md", "markdown", False),
]

SCORING_ARTIFACT_SPECS = [
    ("scoring_output_root", "Scoring output root", "output", "directory", False),
    ("scoring_reports_root", "Scoring reports root", "output/reports", "directory", False),
    ("brand3_sqlite", "Brand3 SQLite store", "data/brand3.sqlite3", "sqlite", False),
    ("brand3_legacy_db", "Brand3 legacy DB", "data/brand3.db", "sqlite", False),
    ("scoring_dimensions_source", "Scoring rubric dimensions source", "src/dimensions.py", "python", False),
]


def build_platform_bundle(
    *,
    output_root: str | Path | None = None,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> dict[str, Any]:
    output_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    visual_signature_root = Path(visual_signature_root)
    scoring_output_root = Path(scoring_output_root)
    artifacts = _build_artifacts(
        output_root=output_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    artifact_map = {artifact.key: artifact for artifact in artifacts}
    json_map = {
        artifact.key: (
            _load_json_if_exists(_absolute_artifact_path(artifact, visual_signature_root, scoring_output_root))
            if artifact.artifact_type == "json"
            else None
        )
        for artifact in artifacts
    }
    scoring_summary = _build_scoring_summary(scoring_output_root=scoring_output_root, output_root=output_root)

    sections = [
        _brand3_overview_section(artifact_map, json_map, scoring_summary),
        _initial_scoring_section(artifact_map, scoring_summary),
        _visual_signature_section(artifact_map, json_map),
        _captures_section(artifact_map, json_map, output_root=output_root, visual_signature_root=visual_signature_root),
        _reviewer_section(artifact_map, json_map, output_root=output_root, visual_signature_root=visual_signature_root),
        _calibration_section(artifact_map, json_map),
        _governance_section(artifact_map, json_map),
        _corpus_expansion_section(artifact_map, json_map, output_root=output_root, visual_signature_root=visual_signature_root),
    ]
    missing_required = [artifact.key for artifact in artifacts if artifact.required and not artifact.exists]
    platform_status = "ready" if not missing_required else "degraded"
    navigation = [{"key": section.key, "label": section.title} for section in sections]
    next_steps = [
        "Inspect Initial Scoring and Visual Signature separately; do not use this platform as a scoring integration layer.",
        "Review pending queue items in the Reviewer Workflow section.",
        "Use calibration readiness block reasons to decide the next evidence collection target.",
        "Keep governance checks green before any broader corpus or provider pilot work.",
        "Treat this platform as navigation only; update source JSON/Markdown through existing generators.",
    ]
    bundle = PlatformBundle(
        schema_version=VISUAL_SIGNATURE_PLATFORM_SCHEMA_VERSION,
        record_type=VISUAL_SIGNATURE_PLATFORM_RECORD_TYPE,
        generated_at=datetime.now(timezone.utc).isoformat(),
        platform_status=platform_status,
        guardrails=GUARDRAILS,
        artifacts=artifacts,
        sections=sections,
        navigation=navigation,
        next_steps=next_steps,
        notes=[
            "Static/local dashboard generated from existing Brand3 scoring and Visual Signature artifacts.",
            "Initial Scoring and Visual Signature remain conceptually and technically separated.",
            "The platform does not create reviews, mutate captures, call providers, recompute scores, or affect production reports.",
        ],
    )
    return bundle.to_dict()


def validate_platform_bundle(
    *,
    platform_root: str | Path,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> list[str]:
    platform_root = Path(platform_root)
    errors: list[str] = []
    for filename in ("index.html", "platform.css", "platform.js"):
        if not (platform_root / filename).exists():
            errors.append(f"missing platform file: {filename}")

    payload = build_platform_bundle(
        output_root=platform_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    required_missing = [
        artifact["key"]
        for artifact in payload["artifacts"]
        if artifact["required"] and not artifact["exists"]
    ]
    if required_missing:
        errors.append(f"missing required source artifacts: {', '.join(required_missing)}")

    sections = {section["title"] for section in payload["sections"]}
    for title in ("Brand3 Overview", "Initial Scoring", "Visual Signature", "Captures", "Reviewer Workflow", "Calibration", "Governance", "Corpus Expansion"):
        if title not in sections:
            errors.append(f"missing section: {title}")
    return errors


def write_platform_bundle(
    *,
    output_root: str | Path | None = None,
    visual_signature_root: str | Path = DEFAULT_VISUAL_SIGNATURE_ROOT,
    scoring_output_root: str | Path = DEFAULT_SCORING_OUTPUT_ROOT,
) -> dict[str, str]:
    platform_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    platform_root.mkdir(parents=True, exist_ok=True)
    payload = build_platform_bundle(
        output_root=platform_root,
        visual_signature_root=visual_signature_root,
        scoring_output_root=scoring_output_root,
    )
    _write_text(platform_root / "index.html", _render_index_html(payload))
    _write_text(platform_root / "platform.css", _platform_css())
    _write_text(platform_root / "platform.js", _platform_js())
    return {
        "platform_root": str(platform_root),
        "platform_index_html": str(platform_root / "index.html"),
        "platform_css": str(platform_root / "platform.css"),
        "platform_js": str(platform_root / "platform.js"),
    }


def _build_artifacts(*, output_root: Path, visual_signature_root: Path, scoring_output_root: Path) -> list[PlatformArtifact]:
    artifacts: list[PlatformArtifact] = []
    for key, label, relative_path, artifact_type, required in SCORING_ARTIFACT_SPECS:
        absolute_path = PROJECT_ROOT / relative_path
        artifacts.append(
            PlatformArtifact(
                key=key,
                label=label,
                path=_to_output_relative_path(absolute_path, output_root=output_root),
                artifact_type=artifact_type,
                required=required,
                exists=absolute_path.exists(),
                summary=_filesystem_summary(absolute_path, artifact_type=artifact_type),
            )
        )
    if scoring_output_root != DEFAULT_SCORING_OUTPUT_ROOT:
        custom_scoring_paths = {
            "scoring_output_root": scoring_output_root,
            "scoring_reports_root": scoring_output_root / "reports",
        }
        artifacts = [
            PlatformArtifact(
                key=artifact.key,
                label=artifact.label,
                path=_to_output_relative_path(custom_scoring_paths[artifact.key], output_root=output_root),
                artifact_type=artifact.artifact_type,
                required=False,
                exists=custom_scoring_paths[artifact.key].exists(),
                summary=_filesystem_summary(custom_scoring_paths[artifact.key], artifact_type=artifact.artifact_type),
            )
            if artifact.key in custom_scoring_paths
            else artifact
            for artifact in artifacts
        ]
    for key, label, relative_path, artifact_type, required in VISUAL_SIGNATURE_ARTIFACT_SPECS:
        absolute_path = visual_signature_root / relative_path
        payload = _load_json_if_exists(absolute_path) if artifact_type == "json" else None
        artifacts.append(
            PlatformArtifact(
                key=key,
                label=label,
                path=_to_output_relative_path(absolute_path, output_root=output_root),
                artifact_type=artifact_type,
                required=required,
                exists=absolute_path.exists(),
                record_type=_safe_get(payload, "record_type"),
                generated_at=_safe_get(payload, "generated_at") or _safe_get(payload, "checked_at") or _safe_get(payload, "completed_at"),
                summary=_artifact_summary(payload),
            )
        )
    return artifacts


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


def _visual_signature_section(artifact_map: dict[str, PlatformArtifact], json_map: dict[str, dict[str, Any] | None]) -> PlatformSection:
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


def _filesystem_summary(path: Path, *, artifact_type: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.is_dir():
        return {
            "artifact_type": artifact_type,
            "file_count": sum(1 for child in path.rglob("*") if child.is_file()),
        }
    return {
        "artifact_type": artifact_type,
        "size_bytes": path.stat().st_size,
    }


def _artifact_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    keys = (
        "schema_version",
        "record_type",
        "generated_at",
        "checked_at",
        "completed_at",
        "status",
        "readiness_status",
        "validation_status",
        "record_count",
        "total",
        "ok",
        "error",
        "capability_count",
        "policy_count",
        "pilot_status",
        "current_capture_count",
        "reviewed_capture_count",
        "target_capture_count",
    )
    return {key: payload[key] for key in keys if key in payload}


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


def _absolute_artifact_path(artifact: PlatformArtifact, visual_signature_root: Path, scoring_output_root: Path) -> Path:
    if artifact.key == "scoring_output_root":
        return scoring_output_root
    if artifact.key == "scoring_reports_root":
        return scoring_output_root / "reports"
    for key, _label, relative_path, _type, _required in SCORING_ARTIFACT_SPECS:
        if key == artifact.key:
            return PROJECT_ROOT / relative_path
    for key, _label, relative_path, _type, _required in VISUAL_SIGNATURE_ARTIFACT_SPECS:
        if key == artifact.key:
            return visual_signature_root / relative_path
    return visual_signature_root / artifact.path


def _render_index_html(payload: dict[str, Any]) -> str:
    embedded = html.escape(json.dumps(payload, ensure_ascii=False), quote=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Brand3 Platform</title>
  <link rel="stylesheet" href="./platform.css">
</head>
<body>
  <div id="app" class="page">
    <pre class="term-head"><span class="prompt">❯</span> brand3-platform <span class="hl-accent">--mode</span> local <span class="dim">· read-only · separated layers</span></pre>
    <hr class="rule">
    <section class="static-skeleton">
      <h1 class="page-title">Brand3 Platform</h1>
      <p class="intro-copy">Loading local Brand3 scoring and Visual Signature artifacts. This static shell stays readable if JavaScript fails.</p>
      <div class="guardrail-banner">Read-only local navigation surface. No scoring changes, rubric changes, production UI changes, provider calls, or runtime mutation enablement.</div>
    </section>
    <script id="platform-data" type="application/json">{embedded}</script>
  </div>
  <script src="./platform.js" defer></script>
</body>
</html>
"""


def _platform_css() -> str:
    return """
@import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap");

:root {
  color-scheme: light;
  --bg: #eeeeee;
  --surface: #f5f5f5;
  --surface-2: #eeeeee;
  --surface-3: #e9e9e9;
  --border: #e4e4e4;
  --text: #161616;
  --muted: #77736d;
  --soft: #9a958e;
  --accent: #ef490d;
  --success: #5f745c;
  --warning: #b7792b;
  --danger: #b84f3f;
  --font-mono: "JetBrains Mono", monospace;
}

* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
  margin: 0;
  padding: 0;
  background:
    repeating-linear-gradient(135deg, rgba(22, 22, 22, 0.018) 0 1px, transparent 1px 7px),
    var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: geometricPrecision;
  font-feature-settings: "liga" 0, "calt" 0;
}
a { color: inherit; text-decoration: underline; text-decoration-color: rgba(239, 73, 13, 0.58); text-underline-offset: 3px; }
a:hover { color: var(--accent); }
button, input, select, textarea { font: inherit; }
.page {
  width: min(1440px, calc(100% - 48px));
  min-height: calc(100vh - 48px);
  margin: 24px auto;
  background: rgba(245, 245, 245, 0.94);
  border: 1px solid var(--border);
  box-shadow: 0 10px 32px rgba(22, 22, 22, 0.035);
}
.term-head {
  min-height: 44px;
  display: flex;
  align-items: center;
  margin: 0;
  padding: 0 28px;
  border-bottom: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.76);
  font-size: 12px;
  white-space: pre-wrap;
}
.prompt, .hl-accent { color: var(--accent); font-weight: 700; }
.dim, .small { color: var(--muted); }
.rule { border: 0; border-top: 1px solid var(--border); margin: 0; }
.rule-thin { border: 0; border-top: 1px dashed var(--border); margin: 24px 0; }
section { padding: 28px; }
.page-title { max-width: 860px; margin: 0 0 16px; font-size: 26px; line-height: 1.18; }
.intro-copy { margin: 0 0 20px; color: var(--muted); }
.platform-shell {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 0;
}
.left-nav {
  border-right: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.42);
  padding: 20px;
  position: sticky;
  top: 0;
  min-height: calc(100vh - 94px);
}
.nav-title { margin: 0 0 14px; font-size: 12px; text-transform: uppercase; }
.nav-button {
  width: 100%;
  display: block;
  text-align: left;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  padding: 9px 10px;
  margin: 0 0 8px;
  cursor: pointer;
}
.nav-button.active { border-color: var(--accent); color: var(--accent); }
.main-content { min-width: 0; }
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 18px;
  margin: 0 0 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-head .label { font-size: 12px; font-weight: 700; text-transform: uppercase; }
.section-head .tag { color: var(--soft); font-size: 12px; text-align: right; }
.guardrail-banner {
  border: 1px dashed var(--accent);
  background: rgba(242, 222, 212, 0.42);
  color: var(--text);
  padding: 12px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.card {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 16px;
}
.card h3, .card h4 { margin: 0 0 10px; font-size: 13px; }
.badge-line, .artifact-list, .screenshot-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.badge {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  padding: 4px 8px;
  font-size: 12px;
}
.badge.ok { color: var(--success); border-color: rgba(95, 116, 92, 0.4); }
.badge.warn { color: var(--warning); border-color: rgba(183, 121, 43, 0.4); }
.badge.bad { color: var(--danger); border-color: rgba(184, 79, 63, 0.4); }
.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}
.metric {
  border: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.56);
  padding: 10px;
  min-width: 0;
}
.metric .k { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
.metric .v { overflow-wrap: anywhere; }
.items {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}
.item-card {
  border: 1px solid var(--border);
  background: rgba(245, 245, 245, 0.65);
  padding: 12px;
}
.item-title { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-weight: 700; }
.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.screenshot-tile {
  border: 1px solid var(--border);
  background: #fff;
  text-decoration: none;
  color: inherit;
}
.screenshot-tile img {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
  border-bottom: 1px solid var(--border);
}
.screenshot-tile span { display: block; padding: 6px 8px; font-size: 12px; color: var(--muted); }
details {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 12px;
  margin-top: 14px;
}
summary { cursor: pointer; font-weight: 700; }
pre.raw-json {
  white-space: pre-wrap;
  overflow: auto;
  max-height: 360px;
  background: #fafafa;
  border: 1px solid var(--border);
  padding: 12px;
}
.footer {
  margin-top: 0;
  padding: 18px 28px 24px;
  border-top: 1px solid var(--border);
  background: rgba(238, 238, 238, 0.7);
  color: var(--muted);
  font-size: 12px;
}
.kv { display: grid; grid-template-columns: 160px 1fr; row-gap: 4px; column-gap: 14px; }
.kv .k { color: var(--accent); }
.kv .v { color: var(--text); }
.footer-note, .footer-cursor { margin-top: 12px; }
.cursor { display: inline-block; width: 7px; height: 14px; background: var(--accent); vertical-align: -2px; animation: blink 1.05s steps(1, end) infinite; margin-left: 4px; }
@keyframes blink { 0%, 55% { opacity: 1; } 56%, 100% { opacity: 0; } }
@media (max-width: 1100px) {
  .platform-shell { grid-template-columns: 1fr; }
  .left-nav { position: static; min-height: 0; border-right: 0; border-bottom: 1px solid var(--border); }
  .dashboard-grid, .screenshot-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 720px) {
  .page { width: min(100% - 32px, 760px); margin-top: 16px; }
  section { padding: 18px; }
  .dashboard-grid, .metric-grid, .screenshot-grid { grid-template-columns: 1fr; }
}
""".strip()


def _platform_js() -> str:
    return """
(function () {
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function asArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function badgeClass(value) {
    const text = String(value || "").toLowerCase();
    if (["ready", "valid", "ok", "confirmed", "reviewed", "governed"].some((token) => text.includes(token))) return "ok";
    if (["missing", "error", "failed"].some((token) => text.includes(token))) return "bad";
    return "warn";
  }

  function renderValue(value) {
    if (value === null || value === undefined || value === "") return "n/a";
    if (Array.isArray(value)) {
      if (!value.length) return "none";
      if (value.every((item) => item === null || ["string", "number", "boolean"].includes(typeof item))) {
        return value.map(escapeHtml).join("<br>");
      }
      return `<pre class="raw-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    }
    if (typeof value === "object") return `<pre class="raw-json">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
    if (typeof value === "string" && isLocalArtifactPath(value)) {
      return `<a href="${escapeHtml(value)}" target="_blank" rel="noreferrer">${escapeHtml(value)}</a>`;
    }
    return escapeHtml(value);
  }

  function isLocalArtifactPath(value) {
    return /^(\\.\\.\\/|\\.\\/|[\\w.-]+\\/).+\\.(json|html|md|png|jpg|jpeg|sqlite3|db)$/i.test(value);
  }

  const dataNode = document.getElementById("platform-data");
  const app = document.getElementById("app");

  try {
    if (!dataNode || !app) throw new Error("platform data or root missing");
    const data = JSON.parse(dataNode.textContent || "{}");
    const sections = asArray(data.sections);
    let activeKey = sections[0] && sections[0].key || "brand3-overview";
    const artifactMap = Object.fromEntries(asArray(data.artifacts).map((artifact) => [artifact.key, artifact]));

    function render() {
      const active = sections.find((section) => section.key === activeKey) || sections[0];
      app.innerHTML = `
        <pre class="term-head"><span class="prompt">❯</span> brand3-platform <span class="hl-accent">--status</span> ${escapeHtml(data.platform_status)} <span class="dim">· read-only · separated layers</span></pre>
        <hr class="rule">
        <div class="platform-shell">
          <nav class="left-nav">
            <h2 class="nav-title">Brand3 Platform</h2>
            ${asArray(data.navigation).map((item) => `<button class="nav-button ${item.key === active.key ? "active" : ""}" data-section="${escapeHtml(item.key)}">${escapeHtml(item.label)}</button>`).join("")}
            <div class="guardrail-banner small">No provider calls · no scoring changes · no rubric changes · no runtime mutation enablement.</div>
          </nav>
          <main class="main-content">${renderSection(active)}</main>
        </div>
        <hr class="rule">
        <footer class="footer">
          <div class="kv">
            <span class="k">engine</span>    <span class="v">brand3 local platform</span>
            <span class="k">about</span>     <span class="v">read-only dashboard · separated layers · JSON source of truth · Markdown audit/export</span>
          </div>
          <div class="small footer-note">${escapeHtml(asArray(data.notes)[0] || "Static local dashboard.")}</div>
          <div class="footer-cursor"><span class="prompt">❯</span> _<span class="cursor"></span></div>
        </footer>
      `;
      app.querySelectorAll("[data-section]").forEach((button) => {
        button.addEventListener("click", () => {
          activeKey = button.getAttribute("data-section");
          render();
        });
      });
    }

    function renderSection(section) {
      return `
        <section id="${escapeHtml(section.key)}">
          <div class="section-head">
            <span class="label">${escapeHtml(section.title)}</span>
            <span class="tag">// ${escapeHtml(section.status)}</span>
          </div>
          <h1 class="page-title">${escapeHtml(section.title)}</h1>
          <p class="intro-copy">${escapeHtml(section.summary)}</p>
          <div class="badge-line">
            <span class="badge ${badgeClass(section.status)}">${escapeHtml(section.status)}</span>
            ${asArray(section.badges).map((badge) => `<span class="badge">${escapeHtml(badge)}</span>`).join("")}
          </div>
          ${section.key === "brand3-overview" ? renderGuardrails() : ""}
          ${renderMetrics(section.metrics)}
          ${renderItems(section)}
          ${renderArtifacts(section.artifact_keys)}
          ${renderNextSteps(section)}
          <details>
            <summary>Advanced / debug</summary>
            <pre class="raw-json">${escapeHtml(JSON.stringify(section, null, 2))}</pre>
          </details>
        </section>
      `;
    }

    function renderGuardrails() {
      return `
        <div class="dashboard-grid" style="margin-top:14px;">
          ${asArray(data.guardrails).map((guardrail) => `<div class="card"><h3>${escapeHtml(guardrail)}</h3><div class="small">enforced as local platform scope</div></div>`).join("")}
        </div>
      `;
    }

    function renderMetrics(metrics) {
      const entries = Object.entries(metrics || {});
      if (!entries.length) return "";
      return `<div class="metric-grid">${entries.map(([key, value]) => `<div class="metric"><div class="k">${escapeHtml(key)}</div><div class="v">${renderValue(value)}</div></div>`).join("")}</div>`;
    }

    function renderItems(section) {
      const items = asArray(section.items);
      if (!items.length) return "";
      return `<div class="items">${items.map((item) => renderItem(section.key, item)).join("")}</div>`;
    }

    function renderItem(sectionKey, item) {
      const title = item.brand_name || item.capability_id || item.queue_id || item.capture_id || "item";
      const status = item.queue_state || item.perceptual_state || item.agreement || item.maturity_state || item.review_outcome || "record";
      return `
        <div class="item-card">
          <div class="item-title"><span>${escapeHtml(title)}</span><span class="badge ${badgeClass(status)}">${escapeHtml(status)}</span></div>
          <div class="metric-grid">${Object.entries(item).filter(([key]) => !["screenshots"].includes(key)).slice(0, 8).map(([key, value]) => `<div class="metric"><div class="k">${escapeHtml(key)}</div><div class="v">${renderValue(value)}</div></div>`).join("")}</div>
          ${sectionKey === "captures" ? renderScreenshots(item.screenshots) : ""}
        </div>
      `;
    }

    function renderScreenshots(screenshots) {
      const rows = asArray(screenshots);
      if (!rows.length) return "";
      return `<div class="screenshot-grid">${rows.map((shot) => `<a class="screenshot-tile" href="${escapeHtml(shot.path)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(shot.path)}" alt="${escapeHtml(shot.label)} screenshot"><span>${escapeHtml(shot.label)}</span></a>`).join("")}</div>`;
    }

    function renderArtifacts(keys) {
      const artifacts = asArray(keys).map((key) => artifactMap[key]).filter(Boolean);
      if (!artifacts.length) return "";
      return `
        <details>
          <summary>Source artifacts</summary>
          <div class="artifact-list" style="margin-top:12px;">
            ${artifacts.map((artifact) => `<a class="badge ${artifact.exists ? "ok" : "bad"}" href="${escapeHtml(artifact.path)}" target="_blank" rel="noreferrer">${escapeHtml(artifact.label)}</a>`).join("")}
          </div>
        </details>
      `;
    }

    function renderNextSteps(section) {
      const steps = [...asArray(section.next_steps)];
      if (section.key === "brand3-overview") steps.push(...asArray(data.next_steps));
      if (!steps.length) return "";
      return `<div class="card" style="margin-top:14px;"><h3>What to do next</h3>${steps.map((step) => `<div class="small">- ${escapeHtml(step)}</div>`).join("")}</div>`;
    }

    render();
  } catch (error) {
    if (app) {
      app.innerHTML = `<section><h1>Brand3 Platform failed to load</h1><pre class="raw-json">${escapeHtml(error && error.stack ? error.stack : String(error))}</pre></section>`;
    }
    if (typeof console !== "undefined" && console.error) console.error(error);
  }
})();
""".strip()


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else {"items": payload}


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _to_output_relative_path(path: str | Path, *, output_root: str | Path) -> str:
    output_root = Path(output_root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return os.path.relpath(candidate.resolve(), output_root)


def _safe_get(payload: dict[str, Any] | None, key: str) -> Any:
    return payload.get(key) if isinstance(payload, dict) else None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "unknown"
