"""Visual Signature human review builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_signature_data_support import HUMAN_REVIEW_BANNER
from .visual_signature_data_support import HUMAN_REVIEW_DESIGN_PATH
from .visual_signature_data_support import HUMAN_REVIEW_GUARDRAILS
from .visual_signature_data_support import HUMAN_REVIEW_INTRO
from .visual_signature_data_support import HUMAN_REVIEW_TITLE
from .visual_signature_data_support import REVIEW_SEMANTICS_PATH
from .visual_signature_data_support import _as_list
from .visual_signature_data_support import _load_json
from .visual_signature_data_support import _nested
from .visual_signature_data_support import _slugify
from .visual_signature_data_support import _visual_signature_nav
from .visual_signature_data_support import visual_signature_human_review_script_version
from .visual_signature_data_support import visual_signature_root
from .visual_signature_overview_data import _screenshot_variant_payload
from .visual_signature_overview_data import _visual_evidence_model


def build_human_review_model(brand: str | None = None, lang: str = "es") -> dict[str, Any] | None:
    if lang not in ("es", "en"):
        lang = "es"
    root = visual_signature_root()
    review_queue = _load_json(root / "corpus_expansion" / "review_queue.json") or {}
    pilot = _load_json(root / "corpus_expansion" / "reviewer_workflow_pilot.json") or {}
    design = _load_json(HUMAN_REVIEW_DESIGN_PATH) or {}
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
        "nav": _visual_signature_nav(lang, active_section="reviewer"),
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


def _human_review_queue_item(item: dict[str, Any], *, active: bool) -> dict[str, Any]:
    capture_id = _slugify(str(item.get("capture_id") or item.get("brand_name") or ""))
    return {
        "queue_id": item.get("queue_id") or f"queue_{capture_id}",
        "capture_id": capture_id,
        "brand_name": item.get("brand_name") or capture_id.replace("-", " ").title(),
        "category": item.get("category") or "unknown",
        "queue_state": item.get("queue_state") or "queued",
        "confidence_bucket": item.get("confidence_bucket") or "unknown",
        "website_url": item.get("website_url") or "",
        "active": active,
        "href": f"/visual-signature/reviewer/human-review/{capture_id}",
    }


def _fallback_evidence_for_capture(queue_item: dict[str, Any]) -> dict[str, Any]:
    root = visual_signature_root()
    capture_id = queue_item["capture_id"]
    return {
        "brand_name": queue_item["brand_name"],
        "capture_id": capture_id,
        "website_url": queue_item.get("website_url") or "",
        "capture_status": "available",
        "obstruction_type": "unknown",
        "obstruction_severity": "unknown",
        "dismissal_attempted": False,
        "dismissal_successful": False,
        "perceptual_state": "evidence_record",
        "evidence_notes": [],
        "variants": [
            _screenshot_variant_payload("raw viewport", root / "screenshots" / f"{capture_id}.png"),
            _screenshot_variant_payload("clean attempt", root / "screenshots" / f"{capture_id}.clean-attempt.png"),
            _screenshot_variant_payload("full page", root / "screenshots" / f"{capture_id}.full-page.png"),
        ],
    }


def _human_review_active_capture(queue_item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    variants = evidence.get("variants") or []
    raw_variant = next((variant for variant in variants if variant.get("label") == "raw viewport"), None)
    return {
        "queue_id": queue_item["queue_id"],
        "capture_id": queue_item["capture_id"],
        "brand_name": evidence.get("brand_name") or queue_item["brand_name"],
        "category": queue_item.get("category") or "unknown",
        "website_url": evidence.get("website_url") or queue_item.get("website_url") or "",
        "queue_state": queue_item.get("queue_state") or "queued",
        "confidence_bucket": queue_item.get("confidence_bucket") or "unknown",
        "capture_status": evidence.get("capture_status") or "available",
        "perceptual_state": evidence.get("perceptual_state") or "evidence_record",
        "obstruction_type": evidence.get("obstruction_type") or "unknown",
        "obstruction_severity": evidence.get("obstruction_severity") or "unknown",
        "dismissal_attempted": bool(evidence.get("dismissal_attempted")),
        "dismissal_successful": bool(evidence.get("dismissal_successful")),
        "evidence_notes": evidence.get("evidence_notes") or [],
        "variants": variants,
        "primary_variant": raw_variant or (variants[0] if variants else None),
        "evidence_refs": [variant["href"] for variant in variants if variant.get("exists")],
    }


def _human_review_question_groups(
    design: dict[str, Any],
    case_design: dict[str, Any],
    semantics: dict[str, Any],
) -> list[dict[str, Any]]:
    regions = _as_list(_nested(design, "canonical_reviewer_screen", "regions"))
    groups = []
    for region in regions:
        if not isinstance(region, dict) or region.get("id") != "structured_visual_questions":
            continue
        for group in _as_list(region.get("question_groups")):
            if isinstance(group, dict):
                group_name = group.get("name") or "Review questions"
                groups.append(
                    {
                        "name": group_name,
                        "questions": [
                            _question_semantics(str(question), group_name, semantics)
                            for question in _as_list(group.get("questions"))
                        ],
                    }
                )
    default_questions = [str(question) for question in _as_list(case_design.get("default_questions"))]
    if default_questions:
        groups.insert(
            0,
            {
                "name": "Case-specific questions",
                "questions": [
                    _question_semantics(question, "Case-specific questions", semantics)
                    for question in default_questions
                ],
            },
        )
    return groups


def _human_review_semantic_guidance(semantics: dict[str, Any]) -> dict[str, Any]:
    confidence = semantics.get("confidence_semantics") if isinstance(semantics.get("confidence_semantics"), dict) else {}
    observation_vs_interpretation = (
        semantics.get("observation_vs_interpretation")
        if isinstance(semantics.get("observation_vs_interpretation"), dict)
        else {}
    )
    return {
        "source": "review_semantics.json",
        "summary": semantics.get("core_intent")
        or "Reviewer answers are structured human visual perception, not classification alone.",
        "confidence_meaning": confidence.get("meaning")
        or "Confidence means reviewer certainty from available evidence.",
        "confidence_buckets": confidence.get("buckets") if isinstance(confidence.get("buckets"), dict) else {},
        "observation_definition": _nested(observation_vs_interpretation, "observation", "definition")
        or "Observation is tied directly to visible evidence.",
        "interpretation_definition": _nested(observation_vs_interpretation, "interpretation", "definition")
        or "Interpretation derives meaning from observations.",
    }


def _question_semantics(question: str, group_name: str, semantics: dict[str, Any]) -> dict[str, Any]:
    category_id = _question_category_id(question, group_name)
    taxonomy = _taxonomy_by_id(semantics).get(category_id, {})
    answer_type = _answer_type_for_question(question, category_id)
    observation_type = _observation_type_for_question(question, category_id)
    question_id = f"{_slugify(group_name)}__{_slugify(question)}"
    return {
        "id": question_id,
        "text": question,
        "category": taxonomy.get("id") or category_id,
        "category_label": _humanize_semantic_label(taxonomy.get("id") or category_id),
        "category_purpose": taxonomy.get("purpose") or "Evidence-bound visual perception question.",
        "observation_type": observation_type,
        "observation_type_label": _humanize_semantic_label(observation_type),
        "answer_type": answer_type,
        "answer_type_label": _humanize_semantic_label(answer_type),
        "answer_guidance": _answer_guidance(answer_type),
        "confidence_guidance": _confidence_guidance(semantics),
        "observation_interpretation_guidance": _observation_interpretation_guidance(observation_type, semantics),
    }


def _taxonomy_by_id(semantics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in _as_list(semantics.get("question_taxonomy"))
        if isinstance(item, dict) and item.get("id")
    }


def _question_category_id(question: str, group_name: str) -> str:
    text = f"{group_name} {question}".lower()
    if "case-specific" in text:
        return _case_specific_category_id(question)
    if "supplemental" in text or "clean attempt" in text or "full-page" in text or "full page" in text:
        return "supplemental_evidence"
    if "obstruction" in text or "modal" in text or "login" in text or "protected" in text or "affordance" in text:
        return "obstruction"
    if "contradict" in text or "unresolved" in text or "missing" in text or "ambiguous" in text or "more evidence" in text:
        return "contradiction_and_unresolved"
    if "logo" in text or "imagery" in text or "product" in text or "people" in text or "template" in text or "category" in text:
        return "visual_perception"
    if "exist" in text or "available" in text or "usable" in text or "broken" in text or "cropped" in text:
        return "evidence_availability"
    return "evidence_support"


def _case_specific_category_id(question: str) -> str:
    text = question.lower()
    if "clean attempt" in text:
        return "supplemental_evidence"
    if "login" in text or "protected" in text or "modal" in text or "obstruction" in text or "affordance" in text:
        return "obstruction"
    if "more evidence" in text or "queue state" in text or "needed" in text:
        return "contradiction_and_unresolved"
    if "raw viewport" in text or "sufficient" in text:
        return "evidence_availability"
    return "evidence_support"


def _answer_type_for_question(question: str, category_id: str) -> str:
    text = question.lower()
    if category_id in {"evidence_support", "visual_perception", "contradiction_and_unresolved"}:
        return "graded_judgment"
    if "severity" in text or "materially" in text or "reduce" in text or "supported" in text or "appropriate" in text:
        return "graded_judgment"
    return "binary_judgment"


def _observation_type_for_question(question: str, category_id: str) -> str:
    text = question.lower()
    if "broken" in text:
        return "evidence_broken"
    if "missing" in text or "more evidence" in text or "needed" in text:
        return "evidence_missing"
    if "raw viewport" in text or "usable" in text or "sufficient" in text:
        return "viewport_usable"
    if "clean attempt" in text and ("reduce" in text or "change" in text):
        return "clean_attempt_effect_visible"
    if "clean attempt" in text:
        return "clean_attempt_available"
    if "full-page" in text or "full page" in text:
        return "full_page_context_available"
    if "obstruction type" in text or "modal" in text or "login" in text or "protected" in text or "affordance" in text:
        return "obstruction_type_visible"
    if "obstruct" in text or "severity" in text:
        return "obstruction_severity_visible"
    if "infer" in text or "inference" in text:
        return "unsupported_inference_present"
    if "contradict" in text:
        return "claim_contradicted"
    if "supported" in text or "appropriate" in text or "claim" in text:
        return "claim_supported"
    if category_id == "visual_perception":
        if "category" in text:
            return "category_cue_visible"
        if "layout" in text or "template" in text:
            return "layout_trait_visible"
        return "visual_element_present"
    return "claim_supported"


def _answer_guidance(answer_type: str) -> dict[str, str]:
    if answer_type == "binary_judgment":
        return {
            "yes": "visible evidence shows this is present or true",
            "partial": "part of the evidence is visible, but it is incomplete or ambiguous",
            "no": "visible evidence does not show this",
            "uncertain": "the reviewer cannot determine this from the available evidence",
        }
    return {
        "yes": "visible evidence clearly supports the judgment",
        "partial": "visible evidence partly supports it, but the support is incomplete or mixed",
        "no": "visible evidence does not support the judgment",
        "uncertain": "the evidence is too ambiguous, missing, or conflicting to judge",
    }


def _confidence_guidance(semantics: dict[str, Any]) -> str:
    confidence = semantics.get("confidence_semantics") if isinstance(semantics.get("confidence_semantics"), dict) else {}
    buckets = confidence.get("buckets") if isinstance(confidence.get("buckets"), dict) else {}
    low = buckets.get("low", "Evidence is weak, partial, ambiguous, obstructed, or internally inconsistent.")
    high = buckets.get("high", "Evidence clearly supports the answer with minimal ambiguity.")
    return f"Confidence means certainty from evidence. Low: {low} High: {high}"


def _observation_interpretation_guidance(observation_type: str, semantics: dict[str, Any]) -> str:
    observation_vs_interpretation = (
        semantics.get("observation_vs_interpretation")
        if isinstance(semantics.get("observation_vs_interpretation"), dict)
        else {}
    )
    observation_definition = _nested(observation_vs_interpretation, "observation", "definition") or "Observation is tied directly to visible evidence."
    interpretation_definition = _nested(observation_vs_interpretation, "interpretation", "definition") or "Interpretation derives meaning from observations."
    if observation_type in {
        "evidence_available",
        "evidence_missing",
        "evidence_broken",
        "viewport_obstructed",
        "obstruction_type_visible",
        "visual_element_present",
        "visual_element_absent",
        "category_cue_visible",
    }:
        return f"Observation: {observation_definition}"
    return f"Interpretation: {interpretation_definition}"


def _humanize_semantic_label(value: str) -> str:
    return value.replace("_", " ")


def _human_review_source_artifacts(root: Path, active: dict[str, Any]) -> list[dict[str, str]]:
    capture_id = active["capture_id"]
    artifact_paths = [
        ("review_queue.json", root / "corpus_expansion" / "review_queue.json"),
        ("reviewer_workflow_pilot.json", root / "corpus_expansion" / "reviewer_workflow_pilot.json"),
        ("capture_manifest.json", root / "screenshots" / "capture_manifest.json"),
        ("dismissal_audit.json", root / "screenshots" / "dismissal_audit.json"),
        ("phase_one state", root / "phase_one" / "records" / capture_id / "state.json"),
        ("phase_one obstruction", root / "phase_one" / "records" / capture_id / "obstruction.json"),
        ("phase_two review", root / "phase_two" / "records" / capture_id / "reviewed_dataset_eligibility.json"),
    ]
    return [
        {
            "label": label,
            "path": str(path),
            "status": "available" if path.exists() else "missing_or_unknown",
        }
        for label, path in artifact_paths
    ]
