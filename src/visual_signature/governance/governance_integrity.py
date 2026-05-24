"""Evidence-only governance integrity checks for Visual Signature."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.calibration.readiness_models import ReadinessScope
from src.visual_signature.governance.capability_models import validate_capability_registry
from src.visual_signature.governance.runtime_policy_models import validate_runtime_policy_matrix_payload


GOVERNANCE_INTEGRITY_SCHEMA_VERSION = "visual-signature-governance-integrity-1"
GOVERNANCE_SCOPE = "visual_signature"

VALID_READINESS_SCOPES: tuple[ReadinessScope, ...] = (
    "broader_corpus_use",
    "provider_pilot_use",
    "human_review_scaling",
    "production_runtime",
    "scoring_integration",
    "model_training",
)


def check_governance_integrity(
    *,
    capability_registry_path: str | Path,
    runtime_policy_matrix_path: str | Path,
    calibration_readiness_path: str | Path,
    calibration_governance_checkpoint_path: str | Path,
    technical_checkpoint_path: str | Path,
    reliable_visual_perception_path: str | Path,
) -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat()
    checked_artifacts = {
        "capability_registry": str(capability_registry_path),
        "runtime_policy_matrix": str(runtime_policy_matrix_path),
        "calibration_readiness": str(calibration_readiness_path),
        "calibration_governance_checkpoint": str(calibration_governance_checkpoint_path),
        "technical_checkpoint": str(technical_checkpoint_path),
        "reliable_visual_perception": str(reliable_visual_perception_path),
    }

    errors: list[str] = []
    warnings: list[str] = []

    capability_payload = _load_json(capability_registry_path)
    runtime_policy_payload = _load_json(runtime_policy_matrix_path)
    calibration_readiness_payload = _load_json(calibration_readiness_path)
    calibration_governance_checkpoint_text = Path(calibration_governance_checkpoint_path).read_text(encoding="utf-8")
    technical_checkpoint_text = Path(technical_checkpoint_path).read_text(encoding="utf-8")
    reliable_visual_perception_text = Path(reliable_visual_perception_path).read_text(encoding="utf-8")

    capability_errors = validate_capability_registry(capability_payload)
    if capability_errors:
        errors.extend(f"capability_registry:{entry}" for entry in capability_errors)

    runtime_policy_errors = validate_runtime_policy_matrix_payload(runtime_policy_payload)
    if runtime_policy_errors:
        errors.extend(f"runtime_policy_matrix:{entry}" for entry in runtime_policy_errors)

    if calibration_readiness_payload.get("readiness_scope") not in VALID_READINESS_SCOPES:
        errors.append(f"invalid readiness scope: {calibration_readiness_payload.get('readiness_scope')!r}")

    if calibration_readiness_payload.get("status") not in {"ready", "not_ready"}:
        errors.append(f"invalid readiness status: {calibration_readiness_payload.get('status')!r}")

    if calibration_readiness_payload.get("readiness_scope") != "broader_corpus_use":
        errors.append("calibration readiness scope must be broader_corpus_use")

    if "readiness_scope" not in calibration_readiness_payload:
        errors.append("calibration readiness is missing readiness_scope")

    if not calibration_readiness_payload.get("bundle_valid", False):
        errors.append("calibration readiness bundle must validate true")

    if not calibration_readiness_payload.get("summary_count_consistency", False):
        errors.append("calibration readiness summary_count_consistency must be true")

    if calibration_readiness_payload.get("source_corpus_manifest_path"):
        source_corpus_manifest_path = Path(calibration_readiness_payload["source_corpus_manifest_path"])
        if not source_corpus_manifest_path.exists():
            errors.append(f"missing source corpus manifest: {source_corpus_manifest_path}")

    _check_registry_consistency(capability_payload, runtime_policy_payload, errors)
    _check_readiness_scope_alignment(calibration_readiness_payload, runtime_policy_payload, errors)
    _check_doc_references(calibration_governance_checkpoint_text, technical_checkpoint_text, reliable_visual_perception_text, warnings, errors)
    _check_doc_language(calibration_governance_checkpoint_text, technical_checkpoint_text, reliable_visual_perception_text, warnings)

    status = "valid" if not errors else "invalid"
    return {
        "schema_version": GOVERNANCE_INTEGRITY_SCHEMA_VERSION,
        "record_type": "governance_integrity_report",
        "checked_at": checked_at,
        "readiness_scope": calibration_readiness_payload.get("readiness_scope"),
        "readiness_status": calibration_readiness_payload.get("status"),
        "status": status,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checked_artifacts": checked_artifacts,
        "notes": [
            "Evidence-only governance integrity check.",
            "No scoring, rubric dimensions, production UI, production reports, runtime behavior, or capture behavior are modified.",
        ],
    }


def write_governance_integrity_report(
    *,
    output_root: str | Path | None = None,
    capability_registry_path: str | Path,
    runtime_policy_matrix_path: str | Path,
    calibration_readiness_path: str | Path,
    calibration_governance_checkpoint_path: str | Path,
    technical_checkpoint_path: str | Path,
    reliable_visual_perception_path: str | Path,
) -> dict[str, str]:
    root = Path(output_root) if output_root is not None else Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "governance"
    root.mkdir(parents=True, exist_ok=True)
    report = check_governance_integrity(
        capability_registry_path=capability_registry_path,
        runtime_policy_matrix_path=runtime_policy_matrix_path,
        calibration_readiness_path=calibration_readiness_path,
        calibration_governance_checkpoint_path=calibration_governance_checkpoint_path,
        technical_checkpoint_path=technical_checkpoint_path,
        reliable_visual_perception_path=reliable_visual_perception_path,
    )
    json_path = root / "governance_integrity_report.json"
    md_path = root / "governance_integrity_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(governance_integrity_report_markdown(report) + "\n", encoding="utf-8")
    return {
        "governance_integrity_report_json": str(json_path),
        "governance_integrity_report_md": str(md_path),
    }


def governance_integrity_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Governance Integrity Check",
        "",
        "Evidence-only governance consistency check for Visual Signature artifacts.",
        "",
        f"- Readiness scope: `{report.get('readiness_scope')}`",
        f"- Readiness status: `{report.get('readiness_status')}`",
        f"- Status: `{report['status']}`",
        f"- Checked at: {report['checked_at']}",
        f"- Error count: {report['error_count']}",
        f"- Warning count: {report['warning_count']}",
        "",
        "## Checked Artifacts",
        "",
    ]
    for key, value in report["checked_artifacts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Errors",
            "",
        ]
    )
    if report["errors"]:
        lines.extend(f"- {error}" for error in report["errors"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Enforced Invariants",
            "",
            "- All runtime policy capability IDs exist in the capability registry.",
            "- All readiness scopes are valid known scopes.",
            "- Capability allowed and prohibited scopes do not overlap.",
            "- production_enabled is false for every capability.",
            "- scoring_impact is false for every capability.",
            "- production_runtime blocks runtime mutation.",
            "- The runtime policy matrix does not silently allow prohibited scopes.",
            "- Governance docs reference both the capability registry and runtime policy matrix.",
            "- Calibration readiness remains scope-qualified, not generic.",
            "- Governance docs retain evidence-only / no scoring / no production implication language.",
        ]
    )
    return "\n".join(lines).rstrip()


def _check_registry_consistency(
    capability_payload: dict[str, Any],
    runtime_policy_payload: dict[str, Any],
    errors: list[str],
) -> None:
    capability_ids = {entry["capability_id"] for entry in capability_payload.get("capabilities", [])}
    for entry in runtime_policy_payload.get("capabilities", []):
        capability_id = entry.get("capability_id")
        if capability_id not in capability_ids:
            errors.append(f"runtime policy references unknown capability_id: {capability_id}")
        if set(entry.get("allowed_scopes", [])) & set(entry.get("prohibited_scopes", [])):
            errors.append(f"runtime policy entry has overlapping scopes: {capability_id}")
        if entry.get("production_enabled"):
            errors.append(f"runtime policy capability is production enabled: {capability_id}")
        if entry.get("runtime_mutation"):
            errors.append(f"runtime policy capability allows runtime mutation: {capability_id}")
        if entry.get("scoring_impact"):
            errors.append(f"runtime policy capability has scoring impact: {capability_id}")
        if set(entry.get("scope_policies", {}).keys()) != set(VALID_READINESS_SCOPES):
            errors.append(f"runtime policy capability does not cover all valid scopes: {capability_id}")
    runtime_mutation_policy = runtime_policy_payload.get("runtime_mutation_policy", {})
    if runtime_mutation_policy.get("scope_policies", {}).get("production_runtime") != "blocked":
        errors.append("production_runtime must block runtime mutation")
    for entry in runtime_policy_payload.get("capabilities", []):
        capability_id = entry.get("capability_id")
        scope_policies = entry.get("scope_policies", {})
        for scope in set(entry.get("prohibited_scopes", [])):
            if scope_policies.get(scope) == "allowed":
                errors.append(f"runtime policy allows prohibited scope: {capability_id}:{scope}")


def _check_readiness_scope_alignment(
    calibration_readiness_payload: dict[str, Any],
    runtime_policy_payload: dict[str, Any],
    errors: list[str],
) -> None:
    readiness_scope = calibration_readiness_payload.get("readiness_scope")
    runtime_scopes = set(runtime_policy_payload.get("runtime_mutation_policy", {}).get("scope_policies", {}).keys())
    for entry in runtime_policy_payload.get("capabilities", []):
        runtime_scopes.update(entry.get("scope_policies", {}).keys())
    if readiness_scope not in runtime_scopes:
        errors.append(f"readiness scope not represented in runtime policy scopes: {readiness_scope!r}")


def _check_doc_references(
    calibration_governance_checkpoint_text: str,
    technical_checkpoint_text: str,
    reliable_visual_perception_text: str,
    warnings: list[str],
    errors: list[str],
) -> None:
    docs = {
        "calibration_governance_checkpoint": calibration_governance_checkpoint_text,
        "technical_checkpoint": technical_checkpoint_text,
        "reliable_visual_perception": reliable_visual_perception_text,
    }
    for doc_name, text in docs.items():
        if "capability_registry.md" not in text:
            warnings.append(f"{doc_name} missing capability_registry.md reference")
        if "runtime_policy_matrix.md" not in text:
            warnings.append(f"{doc_name} missing runtime_policy_matrix.md reference")
        if not _contains_any(text, ("evidence-only", "evidence preserving", "evidence-preserving")):
            warnings.append(f"{doc_name} missing evidence-only language")
        if not _contains_any(text, ("no scoring", "not a scoring system", "outside scoring", "does not modify scoring")):
            warnings.append(f"{doc_name} missing no-scoring language")
        if not _contains_any(text, ("no production", "does not imply production", "production approval", "production readiness")):
            warnings.append(f"{doc_name} missing no-production language")

    if not _contains_any(calibration_governance_checkpoint_text, ("governance metadata only", "governance metadata")):
        warnings.append("calibration_governance_checkpoint missing governance metadata language")


def _check_doc_language(
    calibration_governance_checkpoint_text: str,
    technical_checkpoint_text: str,
    reliable_visual_perception_text: str,
    warnings: list[str],
) -> None:
    if "readiness is scope-dependent" not in calibration_governance_checkpoint_text.lower():
        warnings.append("calibration_governance_checkpoint missing scope-dependent readiness language")
    if not _contains_any(technical_checkpoint_text, ("capability existence does not imply runtime approval", "existence does not imply runtime approval")):
        warnings.append("technical_checkpoint missing runtime approval disclaimer")
    if not _contains_any(reliable_visual_perception_text, ("capability existence does not imply runtime approval", "existence does not imply runtime approval")):
        warnings.append("reliable_visual_perception missing runtime approval disclaimer")


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = " ".join(text.lower().split())
    return any(phrase in lowered for phrase in phrases)


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
