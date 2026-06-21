#!/usr/bin/env python3
"""Capture local PNG screenshots for Visual Signature vision calibration."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.visual_signature.capture.runner import DEFAULT_INPUT  # noqa: E402
from src.visual_signature.capture.runner import DEFAULT_MANIFEST  # noqa: E402
from src.visual_signature.capture.runner import DEFAULT_OUTPUT_DIR  # noqa: E402
from src.visual_signature.capture.runner import CaptureBrand  # noqa: E402
from src.visual_signature.capture.runner import CaptureFn  # noqa: E402
from src.visual_signature.capture.runner import CaptureResult  # noqa: E402
from src.visual_signature.capture.runner import DISMISSAL_TARGET_SELECTOR  # noqa: E402
from src.visual_signature.capture.runner import _attempt_obstruction_dismissal  # noqa: E402
from src.visual_signature.capture.runner import _attempt_obstruction_dismissal_with_discovery  # noqa: E402
from src.visual_signature.capture.runner import _all_diagnostic_targets  # noqa: E402
from src.visual_signature.capture.runner import _attribute_value  # noqa: E402
from src.visual_signature.capture.runner import _affordance_count  # noqa: E402
from src.visual_signature.capture.runner import _affordance_distribution  # noqa: E402
from src.visual_signature.capture.runner import _affordance_evidence_for_element  # noqa: E402
from src.visual_signature.capture.runner import _affordance_id  # noqa: E402
from src.visual_signature.capture.runner import _affordance_localization_evidence_for_element  # noqa: E402
from src.visual_signature.capture.runner import _build_dismissal_audit  # noqa: E402
from src.visual_signature.capture.runner import _capture_result_to_dict  # noqa: E402
from src.visual_signature.capture.runner import _clean_attempt_quality_distribution  # noqa: E402
from src.visual_signature.capture.runner import _coerce_dict_or_none  # noqa: E402
from src.visual_signature.capture.runner import _coerce_transition_list  # noqa: E402
from src.visual_signature.capture.runner import _contains_phrase  # noqa: E402
from src.visual_signature.capture.runner import _derived_capture_path  # noqa: E402
from src.visual_signature.capture.runner import _dismissal_audit_markdown  # noqa: E402
from src.visual_signature.capture.runner import _dismissal_context_type  # noqa: E402
from src.visual_signature.capture.runner import _dismissal_eligibility  # noqa: E402
from src.visual_signature.capture.runner import _dismissal_patterns_for_type  # noqa: E402
from src.visual_signature.capture.runner import _dismissal_skip_note  # noqa: E402
from src.visual_signature.capture.runner import _discover_dismissal_targets  # noqa: E402
from src.visual_signature.capture.runner import _element_intersects_current_viewport  # noqa: E402
from src.visual_signature.capture.runner import _element_label  # noqa: E402
from src.visual_signature.capture.runner import _element_localization_snapshot  # noqa: E402
from src.visual_signature.capture.runner import _find_dismissal_candidate  # noqa: E402
from src.visual_signature.capture.runner import _float_or_none  # noqa: E402
from src.visual_signature.capture.runner import _format_percent  # noqa: E402
from src.visual_signature.capture.runner import _has_cookie_consent_signal  # noqa: E402
from src.visual_signature.capture.runner import _int_or_none  # noqa: E402
from src.visual_signature.capture.runner import _is_concise_dismissal_label  # noqa: E402
from src.visual_signature.capture.runner import _is_safe_dismissal_candidate_fields  # noqa: E402
from src.visual_signature.capture.runner import _invoke_capture_fn  # noqa: E402
from src.visual_signature.capture.runner import _localization_context_terms  # noqa: E402
from src.visual_signature.capture.runner import _match_dismissal_pattern  # noqa: E402
from src.visual_signature.capture.runner import _material_viewport_change  # noqa: E402
from src.visual_signature.capture.runner import _normalize_capture_type  # noqa: E402
from src.visual_signature.capture.runner import _normalize_label  # noqa: E402
from src.visual_signature.capture.runner import _prepare_perceptual_state_machine  # noqa: E402
from src.visual_signature.capture.runner import _rate  # noqa: E402
from src.visual_signature.capture.runner import _rejection_reason  # noqa: E402
from src.visual_signature.capture.runner import _severity_distribution  # noqa: E402
from src.visual_signature.capture.runner import _severity_rank  # noqa: E402
from src.visual_signature.capture.runner import _should_attempt_obstruction_dismissal  # noqa: E402
from src.visual_signature.capture.runner import _should_record_rejected_click_target  # noqa: E402
from src.visual_signature.capture.runner import _snapshot_for_path  # noqa: E402
from src.visual_signature.capture.runner import _split_context_tokens  # noqa: E402
from src.visual_signature.capture.runner import _string_distribution  # noqa: E402
from src.visual_signature.capture.runner import _target_distribution  # noqa: E402
from src.visual_signature.capture.runner import _transition_reason_distribution  # noqa: E402
from src.visual_signature.capture.runner import _visible_obstruction_dom_snapshot  # noqa: E402
from src.visual_signature.capture.runner import _write_json  # noqa: E402
from src.visual_signature.capture.runner import capture_screenshots  # noqa: E402
from src.visual_signature.capture.runner import load_capture_brands  # noqa: E402
from src.visual_signature.capture.runner import main  # noqa: E402
from src.visual_signature.perception import PerceptualStateMachine  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
