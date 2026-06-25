"""Visual Signature overview and screenshot preview builders."""

from __future__ import annotations

from typing import Any

from .visual_signature_data_support import ARTIFACTS
from .visual_signature_data_support import _artifact_payload
from .visual_signature_data_support import _artifacts_for_section
from .visual_signature_data_support import _cards_for_section
from .visual_signature_data_support import _items_for_section
from .visual_signature_display_data import SECTION_INTROS
from .visual_signature_display_data import SECTION_TITLES
from .visual_signature_display_data import visual_signature_guardrails
from .visual_signature_display_data import visual_signature_nav
from .visual_signature_display_data import visual_signature_next_steps
from .visual_signature_overview_capture_data import build_screenshot_preview_model_for_lang
from .visual_signature_overview_capture_data import visual_evidence_model


def build_screenshot_preview_model(filename: str) -> dict[str, Any] | None:
    return build_screenshot_preview_model_for_lang(filename, "es")


def build_visual_signature_model(section: str = "overview", lang: str = "es") -> dict[str, Any]:
    if section not in SECTION_TITLES:
        section = "overview"
    if lang not in ("es", "en"):
        lang = "es"
    artifacts = {key: _artifact_payload(key) for key in ARTIFACTS}
    cards = _cards_for_section(section, artifacts)
    return {
        "section": section,
        "title": SECTION_TITLES[section][lang],
        "intro": SECTION_INTROS[section][lang],
        "nav": visual_signature_nav(lang, active_section=section),
        "guardrails": visual_signature_guardrails(lang),
        "cards": cards,
        "artifacts": _artifacts_for_section(section, artifacts),
        "visual_evidence": visual_evidence_model() if section == "overview" else {"items": [], "summary": {}},
        "records": _items_for_section(section, artifacts),
        "next_steps": visual_signature_next_steps(section, lang),
        "initial_scoring": {
            "href": "/",
            "reports_href": "/reports",
            "note": "Brand3 Scoring remains the existing executable flow. Dimension prose is render-time derived by the current report renderer, not a persisted Visual Signature artifact.",
        },
    }
