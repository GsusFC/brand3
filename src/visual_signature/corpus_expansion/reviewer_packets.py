"""Reviewer packet generation for the Visual Signature reviewer workflow pilot."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "corpus_expansion"
DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH = DEFAULT_OUTPUT_ROOT / "reviewer_workflow_pilot.json"
DEFAULT_CAPTURE_MANIFEST_PATH = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "screenshots" / "capture_manifest.json"
DEFAULT_DISMISSAL_AUDIT_PATH = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "screenshots" / "dismissal_audit.json"


def build_reviewer_packets(
    *,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    output_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT / "reviewer_packets"
    pilot_payload = _load_json(reviewer_workflow_pilot_path)
    selected_items = pilot_payload.get("selected_review_queue_items", [])
    packet_rows = [_build_packet_row(item) for item in selected_items]
    packets = {
        "schema_version": "visual-signature-reviewer-packets-1",
        "record_type": "reviewer_packets_index",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pilot_run_id": pilot_payload.get("pilot_run_id"),
        "readiness_scope": pilot_payload.get("readiness_scope"),
        "selected_review_queue_item_ids": [item.get("queue_id") for item in selected_items],
        "packets": packet_rows,
        "notes": [
            "Evidence-only reviewer packets for the reviewer workflow pilot.",
            "No completed review decisions are included.",
            "Do not invent evidence.",
        ],
    }
    return packets


def validate_reviewer_packets(
    *,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    packets_root: str | Path | None = None,
) -> list[str]:
    errors: list[str] = []
    packets_root = Path(packets_root) if packets_root is not None else DEFAULT_OUTPUT_ROOT / "reviewer_packets"
    pilot_payload = _load_json(reviewer_workflow_pilot_path)
    selected_items = pilot_payload.get("selected_review_queue_items", [])
    selected_ids = [item.get("queue_id") for item in selected_items]
    index_path = packets_root / "reviewer_packet_index.md"
    if not index_path.exists():
        errors.append("reviewer_packet_index_missing")
    for item in selected_items:
        packet_path = packets_root / f"{item.get('capture_id')}.md"
        if not packet_path.exists():
            errors.append(f"missing reviewer packet for {item.get('queue_id')}")
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        for queue_id in selected_ids:
            if queue_id not in text:
                errors.append(f"index missing queue_id: {queue_id}")
    return errors


def write_reviewer_packets(
    *,
    reviewer_workflow_pilot_path: str | Path = DEFAULT_REVIEWER_WORKFLOW_PILOT_PATH,
    output_root: str | Path | None = None,
) -> dict[str, str]:
    packets_root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT / "reviewer_packets"
    packets_root.mkdir(parents=True, exist_ok=True)
    pilot_payload = _load_json(reviewer_workflow_pilot_path)
    selected_items = pilot_payload.get("selected_review_queue_items", [])
    packet_index = build_reviewer_packets(reviewer_workflow_pilot_path=reviewer_workflow_pilot_path, output_root=packets_root)

    for item in selected_items:
        packet_path = packets_root / f"{item.get('capture_id')}.md"
        packet_path.write_text(_packet_markdown_for_item(item) + "\n", encoding="utf-8")

    index_path = packets_root / "reviewer_packet_index.md"
    index_path.write_text(_reviewer_packet_index_markdown(packet_index) + "\n", encoding="utf-8")
    return {
        "reviewer_packet_index_md": str(index_path),
        "reviewer_packets_root": str(packets_root),
        **{f"reviewer_packet_{item.get('capture_id')}": str(packets_root / f"{item.get('capture_id')}.md") for item in selected_items},
    }


def _build_packet_row(item: dict[str, Any]) -> dict[str, Any]:
    capture_id = str(item.get("capture_id"))
    source = _capture_source_bundle(capture_id)
    return {
        "queue_id": item.get("queue_id"),
        "capture_id": capture_id,
        "brand_name": item.get("brand_name"),
        "category": item.get("category"),
        "queue_state": item.get("queue_state"),
        "screenshot_paths": source["screenshot_paths"],
        "raw_evidence_refs": source["raw_evidence_refs"],
        "obstruction_summary": source["obstruction_summary"],
        "affordance_summary": source["affordance_summary"],
        "perceptual_state_summary": source["perceptual_state_summary"],
        "mutation_audit_summary": source["mutation_audit_summary"],
        "review_decision_required": "Determine whether this pending item stays queued, needs additional evidence, unresolved, confirmed, or contradicted.",
        "allowed_outcomes": [
            "confirmed",
            "contradicted",
            "unresolved",
            "needs_additional_evidence",
        ],
        "required_fields": [
            "reviewer_id",
            "reviewed_at",
            "review_outcome",
            "notes",
            "evidence_refs",
            "confidence_bucket",
        ],
        "unresolved_guidance": [
            "Leave the item unresolved when evidence is still insufficient.",
            "Keep the queue item pending until a real reviewer completes it.",
        ],
        "contradiction_guidance": [
            "Record contradictions explicitly.",
            "Do not delete or rewrite the original evidence.",
        ],
        "explicit_note": "Do not invent evidence.",
    }


def _capture_source_bundle(capture_id: str) -> dict[str, Any]:
    if capture_id == "allbirds":
        return {
            "screenshot_paths": [
                "examples/visual_signature/screenshots/allbirds.png",
                "examples/visual_signature/screenshots/allbirds.clean-attempt.png",
                "examples/visual_signature/screenshots/allbirds.full-page.png",
            ],
            "raw_evidence_refs": [
                "examples/visual_signature/screenshots/allbirds.png",
                "examples/visual_signature/screenshots/capture_manifest.json",
                "examples/visual_signature/screenshots/dismissal_audit.json",
                "examples/visual_signature/phase_one/records/allbirds/state.json",
                "examples/visual_signature/phase_one/records/allbirds/obstruction.json",
                "examples/visual_signature/phase_one/records/allbirds/mutation_audit.json",
                "examples/visual_signature/phase_one/records/allbirds/dataset_eligibility.json",
                "examples/visual_signature/phase_two/records/allbirds/reviewed_dataset_eligibility.json",
            ],
            "obstruction_summary": "newsletter_modal; blocking; confidence 1.0; exact safe affordance detected; raw evidence remained primary after failed dismissal.",
            "affordance_summary": "One safe-to-dismiss candidate was found: Close -> close_control / safe_to_dismiss. Additional reviewed targets included manage-choices style cookie controls and unrelated chat/header affordances.",
            "perceptual_state_summary": "RAW_STATE -> REVIEW_REQUIRED_STATE -> ELIGIBLE_FOR_SAFE_INTERVENTION -> attempted mutation -> REVIEW_REQUIRED_STATE; raw state preserved, clean attempt supplemental only.",
            "mutation_audit_summary": "Mutation audit present; attempted=true; successful=false; reversible=true; low risk; raw_viewport preserved as primary evidence.",
        }
    if capture_id == "headspace":
        return {
            "screenshot_paths": [
                "examples/visual_signature/screenshots/headspace.png",
                "examples/visual_signature/screenshots/headspace.full-page.png",
            ],
            "raw_evidence_refs": [
                "examples/visual_signature/screenshots/headspace.png",
                "examples/visual_signature/screenshots/capture_manifest.json",
                "examples/visual_signature/screenshots/dismissal_audit.json",
                "examples/visual_signature/phase_one/records/headspace/state.json",
                "examples/visual_signature/phase_one/records/headspace/obstruction.json",
                "examples/visual_signature/phase_one/records/headspace/dataset_eligibility.json",
                "examples/visual_signature/phase_two/records/headspace/reviewed_dataset_eligibility.json",
            ],
            "obstruction_summary": "login_wall; blocking; confidence 1.0; protected_environment_detected; no safe dismissal attempt was allowed.",
            "affordance_summary": "No safe click candidates were discovered. The obstruction was treated as protected and not eligible for dismissal.",
            "perceptual_state_summary": "RAW_STATE -> UNSAFE_MUTATION_BLOCKED; no mutation audit was produced.",
            "mutation_audit_summary": "No mutation audit present because the page was blocked as a login wall / protected environment.",
        }
    return {
        "screenshot_paths": [],
        "raw_evidence_refs": [],
        "obstruction_summary": "No packet mapping defined for this capture.",
        "affordance_summary": "No packet mapping defined for this capture.",
        "perceptual_state_summary": "No packet mapping defined for this capture.",
        "mutation_audit_summary": "No packet mapping defined for this capture.",
    }


def _packet_markdown_for_item(item: dict[str, Any]) -> str:
    source = _capture_source_bundle(str(item.get("capture_id")))
    lines = [
        f"# Reviewer Packet: {item['brand_name']}",
        "",
        "Evidence-only reviewer packet for the Track 1 reviewer workflow pilot.",
        "",
        f"- Queue item ID: `{item['queue_id']}`",
        f"- Brand name: `{item['brand_name']}`",
        f"- Category: `{item['category']}`",
        f"- Queue state: `{item['queue_state']}`",
        "",
        "## Screenshot Paths",
        "",
    ]
    lines.extend(f"- `{path}`" for path in source["screenshot_paths"])
    lines.extend(
        [
            "",
            "## Raw Evidence Refs",
            "",
        ]
    )
    lines.extend(f"- `{ref}`" for ref in source["raw_evidence_refs"])
    lines.extend(
        [
            "",
            "## Obstruction Summary",
            "",
            f"- {source['obstruction_summary']}",
            "",
            "## Affordance Summary",
            "",
            f"- {source['affordance_summary']}",
            "",
            "## Perceptual State Summary",
            "",
            f"- {source['perceptual_state_summary']}",
            "",
            "## Mutation Audit Summary",
            "",
            f"- {source['mutation_audit_summary']}",
            "",
            "## What the Reviewer Must Decide",
            "",
            f"- { 'Determine whether the pending queue item can be completed with a real review outcome.' }",
            "",
            "## Allowed Outcomes",
            "",
        ]
    )
    lines.extend(f"- {outcome}" for outcome in ["confirmed", "contradicted", "unresolved", "needs_additional_evidence"])
    lines.extend(
        [
            "",
            "## Required Fields",
            "",
            "- reviewer_id",
            "- reviewed_at",
            "- review_outcome",
            "- notes",
            "- evidence_refs",
            "- confidence_bucket",
            "",
            "## Unresolved Handling",
            "",
            "- Leave the item unresolved when evidence remains insufficient.",
            "- Keep the queue item pending until a real reviewer completes it.",
            "",
            "## Contradiction Handling",
            "",
            "- Record contradictions explicitly.",
            "- Do not delete or rewrite the original evidence.",
            "",
            "## Explicit Note",
            "",
            "- Do not invent evidence.",
            "",
            "This packet does not contain a completed review decision.",
        ]
    )
    return "\n".join(lines).rstrip()


def _reviewer_packet_index_markdown(index_payload: dict[str, Any]) -> str:
    lines = [
        "# Reviewer Packet Index",
        "",
        "Evidence-only index for the Track 1 reviewer workflow pilot packets.",
        "",
        "- No completed review records are included.",
        "- Do not invent evidence.",
        "",
        "## Packets",
        "",
    ]
    for packet in index_payload["packets"]:
        lines.append(f"- [`{packet['queue_id']}`]({packet['capture_id']}.md) - {packet['brand_name']} ({packet['category']})")
    lines.extend(
        [
            "",
            "## Explicit Note",
            "",
            "- This index is a navigation aid only.",
            "- It does not imply a review outcome.",
        ]
    )
    return "\n".join(lines).rstrip()


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
