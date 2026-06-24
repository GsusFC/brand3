"""Visual Signature human review builder."""

from __future__ import annotations

from typing import Any

from .visual_signature_data_support import HUMAN_REVIEW_DESIGN_PATH
from .visual_signature_data_support import REVIEW_SEMANTICS_PATH
from .visual_signature_data_support import _as_list
from .visual_signature_data_support import _load_json
from .visual_signature_data_support import _slugify
from .visual_signature_data_support import visual_signature_root
from .visual_signature_human_review_data_capture import _fallback_evidence_for_capture
from .visual_signature_human_review_data_capture import _human_review_active_capture
from .visual_signature_human_review_data_capture import _human_review_queue_item
from .visual_signature_human_review_data_capture import _human_review_source_artifacts
from .visual_signature_human_review_data_capture import _screenshot_variant_payload
from .visual_signature_human_review_data_questions import _human_review_question_groups
from .visual_signature_human_review_data_questions import _human_review_semantic_guidance
from .visual_signature_human_review_data_questions import _question_semantics
from .visual_signature_human_review_data_questions import _humanize_semantic_label
from .visual_signature_human_review_data_questions import _taxonomy_by_id
from .visual_signature_human_review_data_questions import _question_category_id
from .visual_signature_human_review_data_questions import _case_specific_category_id
from .visual_signature_human_review_data_questions import _answer_type_for_question
from .visual_signature_human_review_data_questions import _observation_type_for_question
from .visual_signature_human_review_data_questions import _answer_guidance
from .visual_signature_human_review_data_questions import _confidence_guidance
from .visual_signature_human_review_data_questions import _observation_interpretation_guidance
from .visual_signature_overview_data import _visual_evidence_model
from .visual_signature_display_data import HUMAN_REVIEW_BANNER
from .visual_signature_display_data import HUMAN_REVIEW_GUARDRAILS
from .visual_signature_display_data import HUMAN_REVIEW_INTRO
from .visual_signature_display_data import HUMAN_REVIEW_TITLE
from .visual_signature_display_data import visual_signature_human_review_script_version
from .visual_signature_display_data import visual_signature_nav


def build_human_review_model(brand: str | None = None, lang: str = "es") -> dict[str, Any] | None:
    if lang not in ("es", "en"):
        lang = "es"
    root = visual_signature_root()
    review_queue = _load_json(root / "corpus_expansion" / "review_queue.json") or {}
    pilot = _load_json(root / "corpus_expansion" / "reviewer_workflow_pilot.json") or {}
    design = _load_json(root / "human_review_ui_design.json") or _load_json(HUMAN_REVIEW_DESIGN_PATH) or {}
    semantics = _load_json(REVIEW_SEMANTICS_PATH) or {}
    evidence_model = _visual_evidence_model()
    evidence_items = {item["capture_id"]: item for item in evidence_model["items"]}

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
    if not queue_items:
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

    active_slug = _slugify(brand or "")
    if not active_slug and queue_items:
        active_slug = queue_items[0]["capture_id"]
    active_queue = next((item for item in queue_items if item["capture_id"] == active_slug), None)
    if active_queue is None and queue_items:
        active_queue = queue_items[0]
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
            "summary": {
                "selected": len(queue_items),
                "pending": sum(1 for item in queue_items if item["queue_state"] in {"queued", "needs_additional_evidence"}),
                "needs_additional_evidence": sum(1 for item in queue_items if item["queue_state"] == "needs_additional_evidence"),
                "unresolved": sum(1 for item in queue_items if item["queue_state"] == "unresolved"),
            },
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


__all__ = [
    "build_human_review_model",
    "_human_review_queue_item",
    "_fallback_evidence_for_capture",
    "_human_review_active_capture",
    "_human_review_question_groups",
    "_human_review_semantic_guidance",
    "_human_review_source_artifacts",
    "_screenshot_variant_payload",
    "_question_semantics",
    "_humanize_semantic_label",
    "_taxonomy_by_id",
    "_question_category_id",
    "_case_specific_category_id",
    "_answer_type_for_question",
    "_observation_type_for_question",
    "_answer_guidance",
    "_confidence_guidance",
    "_observation_interpretation_guidance",
]
