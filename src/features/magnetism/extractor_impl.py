"""Extractor for the Brand3 Magnetism Scanner.

The scanner is intentionally evidence-first: the LLM extracts layer signals, while
TLDR blocks and scores are derived in code from those signals.
"""

from __future__ import annotations

import json
from typing import Any

from src.config import BRAND3_MAGNETISM_EXTRACTOR_WEB_CHAR_LIMIT
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.extractor_derivation_impl import MagnetismExtractorDerivationMixin
from src.features.magnetism.extractor_heuristics import (
    extract_via_heuristic as _heuristic_extract_via_heuristic,
)
from src.features.magnetism.extractor_runtime_impl import MagnetismExtractorRuntimeMixin
from src.features.magnetism.extractor_constants import (
    LEGACY_DIRECT_DEPRECATION,
    LEGACY_DIRECT_EXTRACTION_MODE,
    LEGACY_DIRECT_SOURCE,
)


class MagnetismExtractor(MagnetismExtractorRuntimeMixin, MagnetismExtractorDerivationMixin):
    """Extract Magenta Circle signals and derive Brand3 TLDR outputs."""

    def __init__(
        self,
        llm: LLMAnalyzer | None = None,
        *,
        analyst_llm: LLMAnalyzer | None = None,
        system_reading_llm: LLMAnalyzer | None = None,
    ):
        self.llm = llm
        self.analyst_llm = analyst_llm if analyst_llm is not None else llm
        self.system_reading_llm = system_reading_llm if system_reading_llm is not None else llm

    def _mark_legacy_direct_result(self, result: dict[str, Any], source_provider: str) -> None:
        result["source"] = LEGACY_DIRECT_SOURCE
        result["extraction_mode"] = LEGACY_DIRECT_EXTRACTION_MODE
        result["direct_source_provider"] = source_provider
        result["canonical_evidence_source"] = None
        result["llm_model_roles"] = self._llm_model_roles()
        result["deprecation"] = dict(LEGACY_DIRECT_DEPRECATION)

    def _llm_model_roles(self) -> dict[str, str | None]:
        return {
            "magnetism_extractor": getattr(self.llm, "model", None),
            "magnetism_analyst": getattr(self.analyst_llm, "model", None),
            "magnetism_system_reading": getattr(self.system_reading_llm, "model", None),
        }

    def _extract_via_llm(
        self,
        web_markdown: str,
        visual_semantics: dict[str, Any],
        brand_name: str,
        url: str,
    ) -> dict[str, Any] | None:
        """Ask the LLM only for grounded layer signals, not final strategy."""
        truncated_web = web_markdown[:BRAND3_MAGNETISM_EXTRACTOR_WEB_CHAR_LIMIT]
        visual_data = {}
        if isinstance(visual_semantics, dict):
            visual_data = visual_semantics.get("data") or visual_semantics.get("semantics") or {}

        system_prompt = (
            "You are an evidence extraction engine for FLOC* Brand3. "
            "Your job is to identify literal brand signals for the Magenta Circle. "
            "Do not write strategic recommendations. Do not infer resource allocation, founder intent, "
            "management priorities, or decision space. If evidence is missing, mark it as not_detected. "
            "Return valid JSON only."
        )

        user_prompt = f"""Analyze the brand "{brand_name}" from the provided sources.

URL: {url}

WEB CONTENT:
---
{truncated_web}
---

VISUAL SEMANTICS:
---
{json.dumps(visual_data, ensure_ascii=False, indent=2)}
---

Extract signals for the 7 Magenta Circle layers. For each layer:
- finding: one concise observation strictly supported by evidence, or null.
- evidence: one literal quote from web content or one exact visual attribute, or null.
- detected: true only when evidence directly supports the finding.
- confidence: "high", "medium", "low", or "insufficient".

Layer questions:
- mindspace / Which: central emotion, mantra, war cry, or magnetic phrase.
- aetherspace / Why: purpose beyond the product.
- gamespace / Who: personality or archetype.
- envispace / How: visual and conceptual brand idea.
- netspace / When: concrete value proposition and exchange of value.
- tactispace / Where: mission and vision signals.
- ambientspace / What: values and attributes demonstrated in context.

Rules:
- Use evidence, not plausible consultancy language.
- If a layer is weak or absent, set finding=null, evidence=null, detected=false, confidence="insufficient".
- Do not produce scores, recommendations, quadrants, or action plans.
- Do not use phrases like "management teams", "founders typically", "decision space", "should", or "could prioritize".
- Do not use page chrome as brand evidence: navigation labels, menus, breadcrumbs, headers, footers, copyright, legal links, cookie banners, language selectors, login/sign-up buttons, or generic CTAs.
- Do not treat isolated blog/feed/news card titles as mission, vision, values, personality, or value proposition unless the quoted text explicitly states the brand's own purpose, offer, audience, outcome, mission, vision, or values.
- If the strongest available text is page chrome or generic interface copy, mark the layer as not_detected.

Return exactly this JSON shape:
{{
  "brand_name": "{brand_name}",
  "url": "{url}",
  "magenta_circle": {{
    "mindspace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "aetherspace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "gamespace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "envispace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "netspace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "tactispace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}},
    "ambientspace": {{"finding": null, "evidence": null, "detected": false, "confidence": "insufficient"}}
  }}
}}
"""
        parsed = self.llm._call_json(system_prompt, user_prompt)
        if not isinstance(parsed, dict) or not parsed:
            return None

        parsed["fallback_used"] = False
        parsed["url"] = url
        parsed["brand_name"] = brand_name
        return self._normalize_analysis(parsed)

    def _extract_via_heuristic(
        self,
        web_markdown: str,
        visual_semantics: dict[str, Any],
        brand_name: str,
        url: str,
        collector_error: str = "",
        content_distillation_summary: dict[str, Any] | None = None,
        strategic_evidence_packet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fallback extractor that marks only directly matched signals as detected."""
        return _heuristic_extract_via_heuristic(
            web_markdown=web_markdown,
            visual_semantics=visual_semantics,
            brand_name=brand_name,
            url=url,
            collector_error=collector_error,
            content_distillation_summary=content_distillation_summary,
            strategic_evidence_packet=strategic_evidence_packet,
            sentences_fn=self._sentences,
            first_matching_sentence_fn=self._first_matching_sentence,
            heuristic_finding_fn=self._heuristic_finding,
            is_testimonial_evidence_fn=self._is_testimonial_evidence,
            normalize_analysis_fn=self._normalize_analysis,
        )
