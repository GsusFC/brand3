"""Assembly helpers for the Visual Signature human review page model."""

from __future__ import annotations

from typing import Any

from .visual_signature_data_support import _as_list
from .visual_signature_data_support import _load_json
from .visual_signature_data_support import _slugify
from .visual_signature_data_support import visual_signature_root
from .visual_signature_display_data import HUMAN_REVIEW_BANNER
from .visual_signature_display_data import HUMAN_REVIEW_GUARDRAILS
from .visual_signature_display_data import HUMAN_REVIEW_INTRO
from .visual_signature_display_data import HUMAN_REVIEW_TITLE
from .visual_signature_display_data import visual_signature_human_review_script_version
from .visual_signature_display_data import visual_signature_nav
from .visual_signature_human_review_data_capture import _fallback_evidence_for_capture
from .visual_signature_human_review_data_capture import _human_review_active_capture
from .visual_signature_human_review_data_capture import _human_review_queue_item
from .visual_signature_human_review_data_capture import _human_review_source_artifacts
from .visual_signature_human_review_data_questions import _human_review_question_groups
from .visual_signature_human_review_data_questions import _human_review_semantic_guidance
from .visual_signature_overview_capture_data import visual_evidence_model


def build_human_review_model_for_lang(
    *,
    brand: str | None,
    lang: str,
    design_path,
    semantics_path,
) -> dict[str, Any] | None:
    if lang not in ("es", "en"):
        lang = "es"
    root = visual_signature_root()
    review_queue = _load_json(root / "corpus_expansion" / "review_queue.json") or {}
    pilot = _load_json(root / "corpus_expansion" / "reviewer_workflow_pilot.json") or {}
    design = _load_json(root / "human_review_ui_design.json") or _load_json(design_path) or {}
    semantics = _load_json(semantics_path) or {}
    evidence_items = {item["capture_id"]: item for item in visual_evidence_model()["items"]}

    queue_items = build_queue_items(review_queue, pilot, evidence_items)
    active_queue = select_active_queue(queue_items, brand=brand)
    if active_queue is None:
        return None

    for item in queue_items:
        item["active"] = item["capture_id"] == active_queue["capture_id"]

    active_evidence = evidence_items.get(active_queue["capture_id"]) or _fallback_evidence_for_capture(active_queue)
    active_capture = _human_review_active_capture(active_queue, active_evidence)
    first_cases = design.get("first_cases") if isinstance(design.get("first_cases"), dict) else {}
    case_design = first_cases.get(active_capture["capture_id"], {}) if isinstance(first_cases, dict) else {}

    return {
        "title": HUMAN_REVIEW_TITLE[lang],
        "intro": HUMAN_REVIEW_INTRO[lang],
        "nav": visual_signature_nav(lang, active_section="reviewer"),
        "guardrails": HUMAN_REVIEW_GUARDRAILS[lang],
        "banner": HUMAN_REVIEW_BANNER[lang],
        "queue": {
            "items": queue_items,
            "summary": queue_summary(queue_items),
        },
        "active": active_capture,
        "question_groups": _human_review_question_groups(design, case_design, semantics),
        "semantic_guidance": _human_review_semantic_guidance(semantics),
        "outcomes": ["confirmed", "contradicted", "unresolved", "insufficient_review"],
        "confidence_buckets": ["unknown", "low", "medium", "high"],
        "status_mapping": ["approved", "rejected", "needs_more_evidence"],
        "case_guidance": {
            "primary_tasks": _as_list(case_design.get("primary_reviewer_task")),
            "ui_emphasis": _as_list(case_design.get("ui_emphasis")),
        },
        "record_preview_fields": [
            "reviewer_id",
            "queue_id",
            "capture_id",
            "review_outcome",
            "confidence_bucket",
            "question_answers",
            "notes",
            "evidence_refs",
        ],
        "source_artifacts": _human_review_source_artifacts(root, active_capture),
        "script_version": visual_signature_human_review_script_version(),
    }


def build_queue_items(review_queue: dict[str, Any], pilot: dict[str, Any], evidence_items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    selected_ids = set(_as_list(pilot.get("selected_review_queue_item_ids")))
    queue_items = []
    for item in _as_list(review_queue.get("queue_items")):
        if not isinstance(item, dict):
            continue
        capture_id = str(item.get("capture_id") or "")
        if capture_id not in {"headspace", "allbirds"}:
            continue
        if selected_ids and str(item.get("queue_id") or "") not in selected_ids:
            continue
        queue_items.append(_human_review_queue_item(item, active=False))

    queued_capture_ids = {item["capture_id"] for item in queue_items}
    for capture_id in ("headspace", "allbirds"):
        if capture_id in queued_capture_ids or capture_id not in evidence_items:
            continue
        evidence = evidence_items[capture_id]
        queue_items.append(
            {
                "queue_id": f"queue_{capture_id}",
                "capture_id": capture_id,
                "brand_name": evidence["brand_name"],
                "category": "unknown",
                "queue_state": "queued",
                "confidence_bucket": "unknown",
                "website_url": evidence.get("website_url") or "",
                "active": False,
                "href": f"/visual-signature/reviewer/human-review/{capture_id}",
            }
        )

    queue_items.sort(key=lambda item: 0 if item["capture_id"] == "headspace" else 1)
    if queue_items:
        return queue_items

    for capture_id in ("headspace", "allbirds"):
        evidence = evidence_items.get(capture_id)
        if evidence:
            queue_items.append(
                {
                    "queue_id": f"queue_{capture_id}",
                    "capture_id": capture_id,
                    "brand_name": evidence["brand_name"],
                    "category": "unknown",
                    "queue_state": "queued",
                    "confidence_bucket": "unknown",
                    "website_url": evidence.get("website_url") or "",
                    "active": False,
                    "href": f"/visual-signature/reviewer/human-review/{capture_id}",
                }
            )
    return queue_items


def select_active_queue(queue_items: list[dict[str, Any]], *, brand: str | None) -> dict[str, Any] | None:
    active_slug = _slugify(brand or "")
    if not active_slug and queue_items:
        active_slug = queue_items[0]["capture_id"]
    active_queue = next((item for item in queue_items if item["capture_id"] == active_slug), None)
    if active_queue is not None:
        return active_queue
    return queue_items[0] if queue_items else None


def queue_summary(queue_items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "selected": len(queue_items),
        "pending": sum(1 for item in queue_items if item["queue_state"] in {"queued", "needs_additional_evidence"}),
        "needs_additional_evidence": sum(1 for item in queue_items if item["queue_state"] == "needs_additional_evidence"),
        "unresolved": sum(1 for item in queue_items if item["queue_state"] == "unresolved"),
    }
