"""Visual Signature human review builder."""

from __future__ import annotations

from typing import Any

from .visual_signature_data_support import HUMAN_REVIEW_DESIGN_PATH
from .visual_signature_data_support import REVIEW_SEMANTICS_PATH
from .visual_signature_human_review_data_capture import _fallback_evidence_for_capture
from .visual_signature_human_review_data_capture import _human_review_active_capture
from .visual_signature_human_review_data_capture import _human_review_queue_item
from .visual_signature_human_review_data_capture import _human_review_source_artifacts
from .visual_signature_human_review_data_capture import _screenshot_variant_payload
from .visual_signature_human_review_data_model import build_human_review_model_for_lang
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


def build_human_review_model(brand: str | None = None, lang: str = "es") -> dict[str, Any] | None:
    return build_human_review_model_for_lang(
        brand=brand,
        lang=lang,
        design_path=HUMAN_REVIEW_DESIGN_PATH,
        semantics_path=REVIEW_SEMANTICS_PATH,
    )


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
