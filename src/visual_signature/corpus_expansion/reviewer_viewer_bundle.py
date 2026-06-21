"""Bundle builders for the Visual Signature reviewer workflow pilot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.corpus_expansion.reviewer_packets import build_reviewer_packets
from src.visual_signature.corpus_expansion.reviewer_packets import validate_reviewer_packets
from src.visual_signature.versions import REVIEWER_VIEWER_SCHEMA_VERSION


REVIEWER_VIEWER_RECORD_TYPE = "reviewer_viewer_bundle"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_viewer"
DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_workflow_pilot.json"
DEFAULT_REVIEW_QUEUE_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "review_queue.json"
DEFAULT_CAPTURE_MANIFEST_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DEFAULT_DISMISSAL_AUDIT_PATH = PROJECT_ROOT / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"
DEFAULT_PACKETS_ROOT = PROJECT_ROOT / "examples" / "visual_signature" / "corpus_expansion" / "reviewer_packets"


def build_reviewer_viewer_bundle(
    *,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    pilot_payload = _load_json(reviewer_workflow_pilot_path)
    review_queue_payload = _load_json(review_queue_path)
    capture_manifest_payload = _load_json(capture_manifest_path)
    dismissal_audit_payload = _load_json(dismissal_audit_path)
    packets_payload = build_reviewer_packets(reviewer_workflow_pilot_path=reviewer_workflow_pilot_path, output_root=packets_root)
    packet_rows = packets_payload["packets"]

    selected_ids = pilot_payload.get("selected_review_queue_item_ids", [])
    queue_item_map = {item.get("queue_id"): item for item in review_queue_payload.get("queue_items", [])}
    packet_map = {packet["queue_id"]: packet for packet in packet_rows}
    capture_map = {entry.get("brand_name"): entry for entry in capture_manifest_payload.get("results", [])}
    dismissal_map = {entry.get("brand_name"): entry for entry in dismissal_audit_payload.get("results", [])}

    packets: list[dict[str, Any]] = []
    for queue_id in selected_ids:
        packet = packet_map.get(queue_id)
        queue_item = queue_item_map.get(queue_id, {})
        if not packet:
            continue
        capture_id = str(packet["capture_id"])
        packet_markdown_path = Path(packets_root) / f"{capture_id}.md"
        capture_entry = capture_map.get(str(packet["brand_name"]), {})
        dismissal_entry = dismissal_map.get(str(packet["brand_name"]))
        packets.append(
            {
                "queue_id": queue_id,
                "capture_id": capture_id,
                "brand_name": packet["brand_name"],
                "category": packet["category"],
                "queue_state": packet["queue_state"],
                "confidence_bucket": queue_item.get("confidence_bucket"),
                "screenshot_paths": [_to_viewer_relative_path(path, viewer_root=output_root) for path in packet["screenshot_paths"]],
                "raw_evidence_refs": [_to_viewer_relative_path(path, viewer_root=output_root) for path in packet["raw_evidence_refs"]],
                "obstruction_summary": packet["obstruction_summary"],
                "affordance_summary": packet["affordance_summary"],
                "perceptual_state_summary": packet["perceptual_state_summary"],
                "mutation_audit_summary": packet["mutation_audit_summary"],
                "packet_markdown_path": _to_viewer_relative_path(packet_markdown_path, viewer_root=output_root),
                "capture_manifest_entry": _summarize_capture_entry(capture_entry, viewer_root=output_root),
                "dismissal_audit_entry": _summarize_dismissal_entry(dismissal_entry),
                "review_instructions": list(pilot_payload.get("review_instructions", [])),
                "required_reviewer_fields": list(pilot_payload.get("required_reviewer_fields", [])),
                "allowed_review_outcomes": list(pilot_payload.get("allowed_review_outcomes", [])),
                "unresolved_handling": list(pilot_payload.get("unresolved_handling", [])),
                "contradiction_handling": list(pilot_payload.get("contradiction_handling", [])),
                "reviewer_coverage_requirements": list(pilot_payload.get("reviewer_coverage_requirements", [])),
                "explicit_note": "Do not invent evidence.",
                "review_draft": {
                    "reviewer_id": "",
                    "review_outcome": "unresolved",
                    "confidence_bucket": "unknown",
                    "notes": "",
                },
            }
        )

    payload = {
        "schema_version": REVIEWER_VIEWER_SCHEMA_VERSION,
        "record_type": REVIEWER_VIEWER_RECORD_TYPE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "readiness_scope": pilot_payload.get("readiness_scope", "human_review_scaling"),
        "pilot_run_id": pilot_payload.get("pilot_run_id"),
        "pilot_status": pilot_payload.get("pilot_status"),
        "review_queue_path": _to_viewer_relative_path(review_queue_path, viewer_root=output_root),
        "reviewer_workflow_pilot_path": _to_viewer_relative_path(reviewer_workflow_pilot_path, viewer_root=output_root),
        "capture_manifest_path": _to_viewer_relative_path(capture_manifest_path, viewer_root=output_root),
        "dismissal_audit_path": _to_viewer_relative_path(dismissal_audit_path, viewer_root=output_root),
        "reviewer_packets_root": _to_viewer_relative_path(Path(packets_root), viewer_root=output_root),
        "packet_count": len(packets),
        "selected_review_queue_item_ids": selected_ids,
        "packets": packets,
        "navigation_help": [
            "Use the left rail to switch queue items.",
            "Use the decision form for local draft notes only.",
            "No draft is persisted to disk.",
            "Do not invent evidence.",
        ],
        "non_goals": [
            "no scoring integration",
            "no runtime enablement",
            "no production UI integration",
            "no provider execution",
            "no model-training integration",
            "no capture behavior changes",
        ],
        "source_artifacts": [
            _to_viewer_relative_path(reviewer_workflow_pilot_path, viewer_root=output_root),
            _to_viewer_relative_path(review_queue_path, viewer_root=output_root),
            _to_viewer_relative_path(capture_manifest_path, viewer_root=output_root),
            _to_viewer_relative_path(dismissal_audit_path, viewer_root=output_root),
            _to_viewer_relative_path(Path(packets_root) / "allbirds.md", viewer_root=output_root),
            _to_viewer_relative_path(Path(packets_root) / "headspace.md", viewer_root=output_root),
        ],
        "notes": [
            "Evidence-only local reviewer viewer.",
            "Scope separation and readiness semantics are preserved.",
        ],
    }
    return payload


def validate_reviewer_viewer_bundle(
    *,
    viewer_root: str | Path,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
) -> list[str]:
    viewer_root = Path(viewer_root)
    errors: list[str] = []
    required_files = ["index.html", "viewer.css", "viewer.js"]
    for name in required_files:
        if not (viewer_root / name).exists():
            errors.append(f"missing viewer file: {name}")

    packet_errors = validate_reviewer_packets(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        packets_root=packets_root,
    )
    errors.extend(packet_errors)
    if packet_errors:
        return errors

    payload = build_reviewer_viewer_bundle(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        review_queue_path=review_queue_path,
        capture_manifest_path=capture_manifest_path,
        dismissal_audit_path=dismissal_audit_path,
        packets_root=packets_root,
        output_root=viewer_root,
    )
    if payload["packet_count"] != len(payload["packets"]):
        errors.append("packet_count does not match packet list length")
    if set(payload["selected_review_queue_item_ids"]) != {packet["queue_id"] for packet in payload["packets"]}:
        errors.append("selected_review_queue_item_ids do not match packets")
    if any(packet["queue_state"] not in {"queued", "needs_additional_evidence"} for packet in payload["packets"]):
        errors.append("viewer includes non-pending queue states")
    for packet in payload["packets"]:
        packet_path = Path(packet["packet_markdown_path"])
        resolved_packet_path = viewer_root / packet_path
        if not resolved_packet_path.exists():
            errors.append(f"missing packet markdown: {packet['packet_markdown_path']}")
        else:
            packet_markdown = _read_text(resolved_packet_path)
            if "Do not invent evidence." not in packet_markdown:
                errors.append(f"packet missing evidence warning: {packet['queue_id']}")
        if not packet["screenshot_paths"]:
            errors.append(f"packet missing screenshot paths: {packet['queue_id']}")
    return errors


def write_reviewer_viewer_bundle(
    *,
    output_root: str | Path | None = None,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    capture_manifest_path: str | Path = DEFAULT_CAPTURE_MANIFEST_PATH,
    dismissal_audit_path: str | Path = DEFAULT_DISMISSAL_AUDIT_PATH,
    packets_root: str | Path = DEFAULT_PACKETS_ROOT,
) -> dict[str, str]:
    from src.visual_signature.corpus_expansion.reviewer_viewer_render import _render_index_html
    from src.visual_signature.corpus_expansion.reviewer_viewer_render import _viewer_css
    from src.visual_signature.corpus_expansion.reviewer_viewer_render import _viewer_js

    viewer_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    viewer_root.mkdir(parents=True, exist_ok=True)
    packet_errors = validate_reviewer_packets(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        packets_root=packets_root,
    )
    if packet_errors:
        raise ValueError(f"reviewer packet validation failed: {packet_errors}")
    payload = build_reviewer_viewer_bundle(
        reviewer_workflow_pilot_path=reviewer_workflow_pilot_path,
        review_queue_path=review_queue_path,
        capture_manifest_path=capture_manifest_path,
        dismissal_audit_path=dismissal_audit_path,
        packets_root=packets_root,
        output_root=viewer_root,
    )
    _write_text(viewer_root / "index.html", _render_index_html(payload))
    _write_text(viewer_root / "viewer.css", _viewer_css())
    _write_text(viewer_root / "viewer.js", _viewer_js())
    return {
        "viewer_root": str(viewer_root),
        "viewer_index_html": str(viewer_root / "index.html"),
        "viewer_css": str(viewer_root / "viewer.css"),
        "viewer_js": str(viewer_root / "viewer.js"),
    }


def _load_json(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError:
        return {}


def _read_text(path: str | Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _to_viewer_relative_path(path: str | Path, *, viewer_root: str | Path) -> str:
    path = Path(path)
    viewer_root = Path(viewer_root)
    candidate = path
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return os.path.relpath(candidate.resolve(), viewer_root)


def _summarize_capture_entry(entry: dict[str, Any] | None, *, viewer_root: str | Path) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {"status": "missing_or_unknown"}
    summary = dict(entry)
    for key in ("raw_screenshot_path", "clean_attempt_screenshot_path", "secondary_screenshot_path", "screenshot_path"):
        if key in summary and summary[key]:
            summary[key] = _to_viewer_relative_path(summary[key], viewer_root=viewer_root)
    return summary


def _summarize_dismissal_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {"status": "missing_or_unknown"}
    return dict(entry)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
