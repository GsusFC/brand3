"""Evidence-only reviewer workflow pilot for Visual Signature corpus expansion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.visual_signature.corpus_expansion.corpus_expansion_models import (
    CORPUS_EXPANSION_REVIEW_QUEUE_SCHEMA_VERSION,
    CorpusExpansionQueueState,
)


REVIEWER_WORKFLOW_PILOT_SCHEMA_VERSION = "visual-signature-reviewer-workflow-pilot-1"
REVIEWER_WORKFLOW_PILOT_RECORD_TYPE = "reviewer_workflow_pilot"
REVIEWER_WORKFLOW_SCOPE = "human_review_scaling"
PENDING_QUEUE_STATES: tuple[CorpusExpansionQueueState, ...] = (
    "queued",
    "needs_additional_evidence",
)
ALLOWED_REVIEW_OUTCOMES: tuple[str, ...] = (
    "confirmed",
    "contradicted",
    "unresolved",
    "needs_additional_evidence",
)

DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[3] / "examples" / "visual_signature" / "corpus_expansion"
DEFAULT_REVIEW_QUEUE_PATH = DEFAULT_OUTPUT_ROOT / "review_queue.json"
DEFAULT_PILOT_METRICS_PATH = DEFAULT_OUTPUT_ROOT / "pilot_metrics.json"
DEFAULT_CORPUS_EXPANSION_MANIFEST_PATH = DEFAULT_OUTPUT_ROOT / "corpus_expansion_manifest.json"


def build_reviewer_workflow_pilot(
    *,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    pilot_metrics_path: str | Path = DEFAULT_PILOT_METRICS_PATH,
    corpus_expansion_manifest_path: str | Path = DEFAULT_CORPUS_EXPANSION_MANIFEST_PATH,
    pilot_run_id: str | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    review_queue_path = Path(review_queue_path)
    pilot_metrics_path = Path(pilot_metrics_path)
    corpus_expansion_manifest_path = Path(corpus_expansion_manifest_path)

    review_queue_payload = _load_json(review_queue_path)
    pilot_metrics_payload = _load_json(pilot_metrics_path)
    corpus_expansion_manifest_payload = _load_json(corpus_expansion_manifest_path)

    selected_queue_items = _select_pending_queue_items(review_queue_payload.get("queue_items", []))
    selected_item_ids = [item["queue_id"] for item in selected_queue_items]
    pending_distribution = _count_distribution(item["queue_state"] for item in selected_queue_items)

    payload = {
        "schema_version": REVIEWER_WORKFLOW_PILOT_SCHEMA_VERSION,
        "record_type": REVIEWER_WORKFLOW_PILOT_RECORD_TYPE,
        "pilot_run_id": pilot_run_id or review_queue_payload.get("pilot_run_id") or "visual-signature-reviewer-workflow-pilot-1",
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "readiness_scope": REVIEWER_WORKFLOW_SCOPE,
        "pilot_status": "pending",
        "source_artifacts": [
            str(review_queue_path),
            str(pilot_metrics_path),
            str(corpus_expansion_manifest_path),
        ],
        "source_summaries": {
            "review_queue": {
                "schema_version": review_queue_payload.get("schema_version"),
                "record_type": review_queue_payload.get("record_type"),
                "current_capture_count": review_queue_payload.get("current_capture_count"),
                "reviewed_capture_count": review_queue_payload.get("reviewed_capture_count"),
                "queue_state_distribution": review_queue_payload.get("queue_state_distribution", {}),
            },
            "pilot_metrics": {
                "schema_version": pilot_metrics_payload.get("schema_version"),
                "record_type": pilot_metrics_payload.get("record_type"),
                "current_capture_count": pilot_metrics_payload.get("current_capture_count"),
                "reviewed_capture_count": pilot_metrics_payload.get("reviewed_capture_count"),
                "queue_state_distribution": pilot_metrics_payload.get("queue_state_distribution", {}),
            },
            "corpus_expansion_manifest": {
                "schema_version": corpus_expansion_manifest_payload.get("schema_version"),
                "record_type": corpus_expansion_manifest_payload.get("record_type"),
                "current_capture_count": corpus_expansion_manifest_payload.get("current_capture_count"),
                "reviewed_capture_count": corpus_expansion_manifest_payload.get("reviewed_capture_count"),
                "queue_state_distribution": corpus_expansion_manifest_payload.get("queue_state_distribution", {}),
            },
        },
        "selected_review_queue_item_count": len(selected_queue_items),
        "selected_review_queue_item_ids": selected_item_ids,
        "selected_review_queue_items": selected_queue_items,
        "review_instructions": [
            "Review only the pending items selected in this pilot artifact.",
            "Do not fabricate completed decisions.",
            "Preserve unresolved cases when evidence remains insufficient.",
            "Record contradictions explicitly instead of flattening them.",
            "Keep queue items pending until a reviewer actually completes them.",
        ],
        "required_reviewer_fields": [
            "reviewer_id",
            "reviewed_at",
            "review_outcome",
            "notes",
            "evidence_refs",
            "confidence_bucket",
        ],
        "allowed_review_outcomes": list(ALLOWED_REVIEW_OUTCOMES),
        "unresolved_handling": [
            "Unresolved items remain unresolved and are not promoted to reviewed.",
            "Unresolved items must retain evidence references and reviewer notes.",
        ],
        "contradiction_handling": [
            "Contradictions must be recorded explicitly.",
            "Contradictions do not imply removal of the original queue item.",
        ],
        "reviewer_coverage_requirements": [
            "Each selected queue item must be assigned to a reviewer before any outcome is recorded.",
            "Selected items should reach 100% assignment coverage before the pilot is treated as usable.",
            "No completed review record may be generated without explicit reviewer identity and timestamp.",
        ],
        "block_conditions": [
            "synthetic review decisions",
            "completed review records generated in the pilot artifact",
            "selected items with non-pending queue states",
            "missing source review queue artifact",
            "missing source corpus expansion metrics or manifest",
        ],
        "success_criteria": [
            "pilot artifact preserves only pending queue items",
            "review instructions and required fields are explicit",
            "allowed outcomes are constrained and evidence-only",
            "validation rejects any fake completed review record",
            "selected items can be handed to reviewers without mutating source data",
        ],
        "queue_state_distribution": pending_distribution,
        "notes": [
            "Evidence-only reviewer workflow pilot.",
            "No scoring, runtime behavior, production UI, or production reports are modified.",
            "No provider calls are run.",
            "No fake review decisions are generated.",
        ],
    }

    return payload


def validate_reviewer_workflow_pilot_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != REVIEWER_WORKFLOW_PILOT_SCHEMA_VERSION:
        errors.append(f"invalid schema_version: {payload.get('schema_version')!r}")
    if payload.get("record_type") != REVIEWER_WORKFLOW_PILOT_RECORD_TYPE:
        errors.append(f"invalid record_type: {payload.get('record_type')!r}")
    if payload.get("readiness_scope") != REVIEWER_WORKFLOW_SCOPE:
        errors.append(f"invalid readiness_scope: {payload.get('readiness_scope')!r}")
    selected_items = payload.get("selected_review_queue_items", [])
    selected_ids = [item.get("queue_id") for item in selected_items]
    if len(selected_ids) != len(set(selected_ids)):
        errors.append("selected_review_queue_item_ids must be unique")
    if payload.get("selected_review_queue_item_count") != len(selected_items):
        errors.append("selected_review_queue_item_count does not match selected_review_queue_items length")
    if set(payload.get("selected_review_queue_item_ids", [])) != set(selected_ids):
        errors.append("selected_review_queue_item_ids must match selected_review_queue_items")
    for item in selected_items:
        if item.get("queue_state") not in PENDING_QUEUE_STATES:
            errors.append(f"selected item is not pending: {item.get('queue_id')!r}")
        if item.get("review_outcome") is not None:
            errors.append(f"selected item contains completed review_outcome: {item.get('queue_id')!r}")
        if item.get("reviewer_id") is not None or item.get("reviewed_at") is not None:
            errors.append(f"selected item contains completed review metadata: {item.get('queue_id')!r}")
    if payload.get("pilot_status") != "pending":
        errors.append(f"pilot_status must be pending: {payload.get('pilot_status')!r}")
    if not payload.get("review_instructions"):
        errors.append("review_instructions must not be empty")
    if not payload.get("required_reviewer_fields"):
        errors.append("required_reviewer_fields must not be empty")
    if not payload.get("allowed_review_outcomes"):
        errors.append("allowed_review_outcomes must not be empty")
    if "reviewer_id" not in payload.get("required_reviewer_fields", []):
        errors.append("reviewer_id must be a required reviewer field")
    if "review_outcome" not in payload.get("required_reviewer_fields", []):
        errors.append("review_outcome must be a required reviewer field")
    if not set(payload.get("allowed_review_outcomes", [])) >= {"confirmed", "contradicted", "unresolved"}:
        errors.append("allowed_review_outcomes must include confirmed, contradicted, and unresolved")
    if payload.get("queue_state_distribution", {}).get("reviewed", 0) != 0:
        errors.append("reviewer workflow pilot must not generate completed review records")
    if payload.get("queue_state_distribution", {}).get("queued", 0) + payload.get("queue_state_distribution", {}).get("needs_additional_evidence", 0) != len(selected_items):
        errors.append("queue_state_distribution must reflect selected pending items only")
    return errors


def reviewer_workflow_pilot_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Visual Signature Reviewer Workflow Pilot",
        "",
        "Evidence-only governance artifact for the reviewer workflow validation pilot.",
        "",
        "- Evidence-only: yes",
        "- Governance-only: yes",
        "- No scoring impact: yes",
        "- No runtime enablement: yes",
        "- No provider execution enablement: yes",
        "- No fake review decisions: yes",
        "",
        f"- Pilot run ID: `{payload['pilot_run_id']}`",
        f"- Generated at: {payload['generated_at']}",
        f"- Readiness scope: `{payload['readiness_scope']}`",
        f"- Pilot status: `{payload['pilot_status']}`",
        f"- Selected queue items: {payload['selected_review_queue_item_count']}",
        "",
        "## Pilot Scope",
        "",
        "- review queue usability",
        "- reviewer decisions",
        "- unresolved handling",
        "- contradiction handling",
        "- reviewer coverage",
        "- review consistency",
        "",
        "## Selected Review Queue Items",
        "",
    ]
    for item in payload["selected_review_queue_items"]:
        lines.extend(
            [
                f"- `{item['queue_id']}`",
                f"  - capture_id: `{item['capture_id']}`",
                f"  - brand_name: `{item['brand_name']}`",
                f"  - queue_state: `{item['queue_state']}`",
                f"  - confidence_bucket: `{item['confidence_bucket']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Review Instructions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["review_instructions"])
    lines.extend(
        [
            "",
            "## Required Reviewer Fields",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["required_reviewer_fields"])
    lines.extend(
        [
            "",
            "## Allowed Review Outcomes",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["allowed_review_outcomes"])
    lines.extend(
        [
            "",
            "## Unresolved Handling",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["unresolved_handling"])
    lines.extend(
        [
            "",
            "## Contradiction Handling",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["contradiction_handling"])
    lines.extend(
        [
            "",
            "## Reviewer Coverage Requirements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["reviewer_coverage_requirements"])
    lines.extend(
        [
            "",
            "## Block Conditions",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["block_conditions"])
    lines.extend(
        [
            "",
            "## Success Criteria",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["success_criteria"])
    lines.extend(
        [
            "",
            "## Explicit Non-Goals",
            "",
            "- no scoring integration",
            "- no runtime enablement",
            "- no model training",
            "- no production UI/report changes",
            "- no capture behavior changes",
            "",
            "This pilot keeps all review decisions pending or queued.",
            "It does not imply production readiness.",
        ]
    )
    return "\n".join(lines).rstrip()


def write_reviewer_workflow_pilot(
    *,
    output_root: str | Path | None = None,
    review_queue_path: str | Path = DEFAULT_REVIEW_QUEUE_PATH,
    pilot_metrics_path: str | Path = DEFAULT_PILOT_METRICS_PATH,
    corpus_expansion_manifest_path: str | Path = DEFAULT_CORPUS_EXPANSION_MANIFEST_PATH,
) -> dict[str, str]:
    root = Path(output_root) if output_root is not None else DEFAULT_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    payload = build_reviewer_workflow_pilot(
        review_queue_path=review_queue_path,
        pilot_metrics_path=pilot_metrics_path,
        corpus_expansion_manifest_path=corpus_expansion_manifest_path,
    )
    errors = validate_reviewer_workflow_pilot_payload(payload)
    if errors:
        raise ValueError("invalid reviewer workflow pilot: " + "; ".join(errors))

    json_path = root / "reviewer_workflow_pilot.json"
    md_path = root / "reviewer_workflow_pilot.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(reviewer_workflow_pilot_markdown(payload) + "\n", encoding="utf-8")
    return {
        "reviewer_workflow_pilot_json": str(json_path),
        "reviewer_workflow_pilot_md": str(md_path),
    }


def _select_pending_queue_items(queue_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in queue_items:
        if item.get("queue_state") in PENDING_QUEUE_STATES:
            selected.append(
                {
                    "queue_id": item.get("queue_id"),
                    "capture_id": item.get("capture_id"),
                    "brand_name": item.get("brand_name"),
                    "website_url": item.get("website_url"),
                    "category": item.get("category"),
                    "queue_state": item.get("queue_state"),
                    "confidence_bucket": item.get("confidence_bucket"),
                    "evidence_refs": list(item.get("evidence_refs", [])),
                    "notes": list(item.get("notes", [])),
                }
            )
    return selected


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _count_distribution(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))
