"""Editorial language policy helpers for report readiness.

These functions are pure mapping helpers. They do not change scoring,
readiness, narrative generation, rendering, prompts, or storage.
"""

from __future__ import annotations

from typing import Any


_REPORT_MODES: dict[str, dict[str, Any]] = {
    "publishable_brand_report": {
        "label": "Publishable brand report",
        "tone": "editorial",
        "allows_strategic_implications": True,
        "allows_recommendations": True,
    },
    "technical_diagnostic": {
        "label": "Technical diagnostic",
        "tone": "cautious",
        "allows_strategic_implications": "limited",
        "allows_recommendations": "limited",
    },
    "insufficient_evidence": {
        "label": "Insufficient evidence",
        "tone": "diagnostic",
        "allows_strategic_implications": False,
        "allows_recommendations": "only_data_requests",
    },
}

_UNKNOWN_REPORT_MODE = {
    "label": "Unknown readiness mode",
    "tone": "cautious",
    "allows_strategic_implications": False,
    "allows_recommendations": "diagnostic_only",
}

_DIMENSION_STATES: dict[str, dict[str, Any]] = {
    "ready": {
        "label": "Ready",
        "language_level": "editorial",
        "may_state_findings": True,
        "may_infer_implications": True,
        "may_recommend": True,
        "signal_role": "supported_signal",
    },
    "observation_only": {
        "label": "Observation only",
        "language_level": "observational",
        "may_state_findings": True,
        "may_infer_implications": "limited",
        "may_recommend": "cautious",
        "signal_role": "limitation",
    },
    "technical_only": {
        "label": "Technical only",
        "language_level": "technical",
        "may_state_findings": "limited",
        "may_infer_implications": False,
        "may_recommend": "diagnostic_only",
        "signal_role": "diagnostic_limitation",
    },
    "not_evaluable": {
        "label": "Not evaluable",
        "language_level": "unavailable",
        "may_state_findings": False,
        "may_infer_implications": False,
        "may_recommend": "data_needed_only",
        "signal_role": "unavailable_signal",
    },
}

_UNKNOWN_DIMENSION_STATE = {
    "label": "Unknown state",
    "language_level": "technical",
    "may_state_findings": False,
    "may_infer_implications": False,
    "may_recommend": "diagnostic_only",
    "signal_role": "diagnostic_limitation",
}

_EVIDENCE_HINTS: dict[str, dict[str, Any]] = {
    "direct": {
        "label": "Direct evidence",
        "can_support_editorial_claims": True,
        "can_support_cautious_observations": True,
        "can_support_diagnostic_notes": True,
        "language": "can support claims",
    },
    "indirect": {
        "label": "Indirect evidence",
        "can_support_editorial_claims": False,
        "can_support_cautious_observations": True,
        "can_support_diagnostic_notes": True,
        "language": "can support cautious observations",
    },
    "weak": {
        "label": "Weak evidence",
        "can_support_editorial_claims": False,
        "can_support_cautious_observations": False,
        "can_support_diagnostic_notes": True,
        "language": "can only support diagnostic notes",
    },
    "off_entity": {
        "label": "Off-entity evidence",
        "can_support_editorial_claims": False,
        "can_support_cautious_observations": False,
        "can_support_diagnostic_notes": True,
        "language": "must not support claims",
    },
    "analysis_note": {
        "label": "Analysis note",
        "can_support_editorial_claims": False,
        "can_support_cautious_observations": False,
        "can_support_diagnostic_notes": True,
        "language": "not evidence, only internal interpretation",
    },
    "fallback": {
        "label": "Fallback value",
        "can_support_editorial_claims": False,
        "can_support_cautious_observations": False,
        "can_support_diagnostic_notes": True,
        "language": "not evidence, only technical explanation",
    },
}

_UNKNOWN_EVIDENCE_HINT = {
    "label": "Unknown evidence type",
    "can_support_editorial_claims": False,
    "can_support_cautious_observations": False,
    "can_support_diagnostic_notes": True,
    "language": "treat as diagnostic only",
}


def label_report_mode(mode: str) -> str:
    return tone_for_report_mode(mode)["label"]


def label_dimension_state(state: str) -> str:
    return tone_for_dimension_state(state)["label"]


def tone_for_report_mode(mode: str) -> dict[str, Any]:
    return dict(_REPORT_MODES.get(mode, _UNKNOWN_REPORT_MODE))


def tone_for_dimension_state(state: str) -> dict[str, Any]:
    return dict(_DIMENSION_STATES.get(state, _UNKNOWN_DIMENSION_STATE))


def allowed_language_for_dimension_state(state: str) -> dict[str, Any]:
    policy = tone_for_dimension_state(state)
    return {
        "language_level": policy["language_level"],
        "may_state_findings": policy["may_state_findings"],
        "may_infer_implications": policy["may_infer_implications"],
        "may_recommend": policy["may_recommend"],
        "signal_role": policy["signal_role"],
    }


def evidence_language_hint(evidence_type: str) -> dict[str, Any]:
    return dict(_EVIDENCE_HINTS.get(evidence_type, _UNKNOWN_EVIDENCE_HINT))
