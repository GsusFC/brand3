"""Helpers for Visual Signature human review semantic/question guidance."""

from __future__ import annotations

from typing import Any

from .visual_signature_data_support import _as_list
from .visual_signature_data_support import _nested
from .visual_signature_data_support import _slugify


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


__all__ = [
    "_human_review_question_groups",
    "_human_review_semantic_guidance",
    "_question_semantics",
    "_taxonomy_by_id",
    "_question_category_id",
    "_case_specific_category_id",
    "_answer_type_for_question",
    "_observation_type_for_question",
    "_answer_guidance",
    "_confidence_guidance",
    "_observation_interpretation_guidance",
    "_humanize_semantic_label",
]

