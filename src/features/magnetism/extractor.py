"""Extractor for the Brand3 Magnetism Scanner.

The scanner is intentionally evidence-first: the LLM extracts layer signals, while
TLDR blocks and scores are derived in code from those signals.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from src.collectors.web_collector import WebCollector
from src.config import (
    BRAND3_BRAND_RESEARCH_GRAPH_PACK,
    BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT,
    BRAND3_MAGNETISM_EXTRACTOR_WEB_CHAR_LIMIT,
    BRAND3_MAGNETISM_RESEARCH_PACK_TLDR,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.features.magnetism.block_interpreters import (
    TLDR_BLOCK_INTERPRETER_SPECS,
    accepted_block_evidence,
    block_evidence_candidates,
    interpret_tldr_block,
    strategic_packet_candidate_priority,
    strategic_packet_candidates,
)
from src.features.magnetism.content_distiller import ContentDistiller
from src.features.magnetism.analyst_tldr import run_analyst_tldr_pass
from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.reports.derivation import collect_evidences
from src.reports.brand_context_brief import build_brand_context_brief
from src.reports.canonical_evidence import build_canonical_brand_evidence
from src.reports.strategic_evidence_packet import StrategicEvidencePacket
from src.research.contextdev_research_pack_dry_run import build_contextdev_research_pack_dry_run
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph
from src.visual_signature.vision.multimodal_analyzer import analyze_visual_semantics

LAYER_KEYS = [
    "mindspace",
    "aetherspace",
    "gamespace",
    "envispace",
    "netspace",
    "tactispace",
    "ambientspace",
]

LAYER_DEFINITIONS = {
    "mindspace": {
        "question": "Which",
        "description": "central emotion, mantra, war cry, or magnetic phrase",
        "tldr": ["magnetism"],
    },
    "aetherspace": {
        "question": "Why",
        "description": "purpose beyond the product",
        "tldr": ["core_purpose"],
    },
    "gamespace": {
        "question": "Who",
        "description": "brand personality and archetype",
        "tldr": ["personality"],
    },
    "envispace": {
        "question": "How",
        "description": "visual and conceptual brand idea",
        "tldr": ["brand_idea"],
    },
    "netspace": {
        "question": "When",
        "description": "concrete value proposition and exchange of value",
        "tldr": ["value_proposition"],
    },
    "tactispace": {
        "question": "Where",
        "description": "mission and vision signals",
        "tldr": ["mission", "vision"],
    },
    "ambientspace": {
        "question": "What",
        "description": "values and attributes demonstrated in context",
        "tldr": ["attributes", "values"],
    },
}

TLDR_KEYS = [
    "core_purpose",
    "magnetism",
    "value_proposition",
    "personality",
    "brand_idea",
    "attributes",
    "values",
    "mission",
    "vision",
]

LAYER_TO_TLDR = {
    "aetherspace": ["core_purpose"],
    "mindspace": ["magnetism"],
    "netspace": ["value_proposition"],
    "gamespace": ["personality"],
    "envispace": ["brand_idea"],
    "ambientspace": ["attributes", "values"],
    "tactispace": ["mission", "vision"],
}

TLDR_TO_LAYER = {
    block: layer for layer, blocks in LAYER_TO_TLDR.items() for block in blocks
}

CANONICAL_EXTRACTION_MODE = "canonical_snapshot"
LEGACY_DIRECT_EXTRACTION_MODE = "legacy_direct"
LEGACY_DIRECT_SOURCE = "direct_magnetism_legacy"
LEGACY_DIRECT_DEPRECATION = {
    "status": "deprecated",
    "replacement": "extract_from_audit_snapshot",
    "reason": (
        "Brand Audit owns acquisition; Magnetism should interpret "
        "CanonicalBrandEvidence from a persisted snapshot."
    ),
}

TLDR_BLOCK_CONTRACT = {
    "core_purpose": {
        "question": "Why does this brand appear to exist beyond the product?",
        "evidence_scope": ["aetherspace", "mindspace", "ambientspace"],
        "source_signal": "Essence",
        "source_signal_path": "Essence → Core Purpose",
        "source_layer": "aetherspace",
    },
    "magnetism": {
        "question": "What phrase or tension best concentrates the brand's magnetic energy?",
        "evidence_scope": ["mindspace", "netspace", "aetherspace"],
        "source_signal": "Emotions",
        "source_signal_path": "Emotions → Magnetism",
        "source_layer": "mindspace",
    },
    "value_proposition": {
        "question": "What does the brand offer, to whom, and what changes for that audience?",
        "evidence_scope": ["netspace", "tactispace", "ambientspace"],
        "source_signal": "Exchange",
        "source_signal_path": "Exchange → Value Proposition",
        "source_layer": "netspace",
    },
    "personality": {
        "question": "What personality does the brand perform through tone, vocabulary, behavior, and visual expression?",
        "evidence_scope": ["gamespace", "mindspace", "netspace", "ambientspace"],
        "source_signal": "Voice",
        "source_signal_path": "Voice → Personality",
        "source_layer": "gamespace",
    },
    "brand_idea": {
        "question": "What conceptual idea connects strategy, category, and expression?",
        "evidence_scope": ["envispace", "mindspace", "aetherspace", "netspace"],
        "source_signal": "Expression",
        "source_signal_path": "Expression → Brand Idea",
        "source_layer": "envispace",
    },
    "attributes": {
        "question": "Which three attributes does the brand describe or demonstrate consistently?",
        "evidence_scope": ["ambientspace", "netspace", "mindspace"],
        "source_signal": "Context / Beliefs",
        "source_signal_path": "Context / Beliefs → Attributes",
        "source_layer": "ambientspace",
    },
    "values": {
        "question": "Which three values does the brand appear to defend through what it says and does?",
        "evidence_scope": ["ambientspace", "aetherspace", "tactispace"],
        "source_signal": "Context / Beliefs",
        "source_signal_path": "Context / Beliefs → Values",
        "source_layer": "ambientspace",
    },
    "mission": {
        "question": "What does the brand concretely do today?",
        "evidence_scope": ["tactispace", "netspace", "aetherspace"],
        "source_signal": "Action / Direction",
        "source_signal_path": "Action / Direction → Mission",
        "source_layer": "tactispace",
    },
    "vision": {
        "question": "What future or category change does the brand appear to be building toward?",
        "evidence_scope": ["tactispace", "aetherspace", "mindspace"],
        "source_signal": "Action / Direction",
        "source_signal_path": "Action / Direction → Vision",
        "source_layer": "tactispace",
    },
}

STRATEGIC_TLDR_BLOCKS = {"core_purpose", "personality", "brand_idea", "values", "vision"}
PERFORMED_TLDR_BLOCKS = {"personality", "attributes", "values"}
DECLARATIVE_TLDR_BLOCKS = {"core_purpose", "magnetism", "value_proposition", "mission"}

GENERIC_MAGNETISM_TERMS = {
    "empower",
    "empowering",
    "future",
    "innovation",
    "innovative",
    "transform",
    "transforming",
    "leverage",
    "leading",
    "platform",
    "solution",
    "seamless",
    "unlock",
    "elevate",
}

SPECIFICITY_TERMS = {
    "api",
    "ai",
    "athlete",
    "athletes",
    "wealth",
    "banking",
    "developer",
    "protocol",
    "capital",
    "data",
    "security",
    "compliance",
    "automation",
    "workflow",
    "infrastructure",
    "advisors",
    "founders",
    "teams",
    "marathon",
    "maraton",
    "performance",
    "sport",
    "sports",
    "training",
}


class MagnetismExtractor:
    """Extract Magenta Circle signals and derive Brand3 TLDR outputs."""

    def __init__(self, llm: LLMAnalyzer | None = None):
        self.llm = llm

    def extract(
        self,
        url: str | None,
        manual_text: str | None = None,
        brand_name: str | None = None,
    ) -> dict[str, Any]:
        """Legacy direct acquisition path for ad-hoc/debug Magnetism scans.

        Production Brand3 lenses should use extract_from_audit_snapshot() so Brand
        Audit remains the single canonical acquisition pipeline.
        """
        url_str = (url or "").strip()
        manual_str = (manual_text or "").strip()
        brand_name = brand_name or self._infer_brand_name(url_str)

        web_markdown = ""
        screenshot_path = None
        temp_screenshot_path = None
        web_collector_error = ""
        source_provider = "manual_evidence" if manual_str else "direct_input"
        content_distillation_summary: dict[str, Any] | None = None

        if url_str:
            try:
                collector = WebCollector()
                web_data = collector.scrape(url_str)
                web_markdown = web_data.markdown_content or ""
                screenshot_path = web_data.screenshot_path
                web_collector_error = web_data.error
                source_provider = web_data.content_source or ("web_collector" if web_markdown else "web_collector_empty")

                if not screenshot_path:
                    try:
                        from src.services.brand_service import _take_playwright_screenshot

                        normalized_url = url_str if "://" in url_str else f"https://{url_str}"
                        shot_res = _take_playwright_screenshot(normalized_url)
                        if "screenshot_path" in shot_res:
                            screenshot_path = shot_res["screenshot_path"]
                            temp_screenshot_path = screenshot_path
                    except Exception as exc:
                        print(f"  Warning: Playwright screenshot failed: {exc}")
            except Exception as exc:
                web_collector_error = str(exc)

        if manual_str:
            web_markdown = manual_str
            source_provider = "manual_evidence"

        if web_markdown:
            distilled = ContentDistiller().distill(
                web_markdown,
                source_url=url_str or "manual",
                source_provider=source_provider,
            )
            content_distillation_summary = distilled.to_summary()
            if distilled.selected_text:
                web_markdown = distilled.selected_text

        visual_semantics = {"status": "not_detected", "data": {}}
        if screenshot_path:
            try:
                visual_semantics = analyze_visual_semantics(screenshot_path, brand_name)
            except Exception:
                visual_semantics = {"status": "unavailable", "data": {}}

        try:
            if self.llm is not None and getattr(self.llm, "api_key", None):
                try:
                    result = self._extract_via_llm(
                        web_markdown, visual_semantics, brand_name, url_str or "manual"
                    )
                    if result:
                        if content_distillation_summary:
                            result["content_distillation_summary"] = content_distillation_summary
                        self._mark_legacy_direct_result(result, source_provider)
                        return result
                except Exception:
                    pass

            result = self._extract_via_heuristic(
                web_markdown,
                visual_semantics,
                brand_name,
                url_str or "manual",
                web_collector_error,
                content_distillation_summary,
            )
            self._mark_legacy_direct_result(result, source_provider)
            return result
        finally:
            if temp_screenshot_path:
                try:
                    if os.path.exists(temp_screenshot_path):
                        os.remove(temp_screenshot_path)
                except Exception:
                    pass

    def extract_from_audit_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Build a Magnetism scan from an existing Brand Audit run snapshot.

        This is the preferred integration path: Brand Audit owns collection,
        evidence normalization, confidence, and degraded-state handling.
        """
        canonical_evidence = build_canonical_brand_evidence(snapshot)
        research_pack, evidence_graph_summary = self._build_research_pack(snapshot)
        contextdev_candidate_summary = self._contextdev_candidate_summary_from_snapshot(snapshot)
        brand_name = canonical_evidence.brand_name
        url = canonical_evidence.url
        strategic_packet = canonical_evidence.strategic_packet
        evidence_text = canonical_evidence.interpreter_text
        visual_semantics = canonical_evidence.visual_semantics
        evidence_packet_summary = canonical_evidence.to_summary()

        if self.llm is not None and getattr(self.llm, "api_key", None):
            try:
                result = self._extract_via_llm(evidence_text, visual_semantics, brand_name, url)
                if result:
                    packet_dict = strategic_packet.to_dict()
                    result["source_run_id"] = canonical_evidence.run_id
                    result["source"] = "brand_audit_snapshot"
                    result["extraction_mode"] = CANONICAL_EXTRACTION_MODE
                    result["canonical_evidence_source"] = "brand_audit_snapshot"
                    result["limitations"].extend(canonical_evidence.limitations)
                    result["evidence_packet_summary"] = evidence_packet_summary
                    if evidence_graph_summary:
                        result["evidence_graph_summary"] = evidence_graph_summary
                        result["research_pack_source"] = "evidence_graph"
                    else:
                        result["research_pack_source"] = "snapshot_builder"
                    result["strategic_evidence_packet"] = packet_dict
                    self._enrich_layers_from_strategic_packet(result["magenta_circle"], packet_dict)
                    brand_context_brief = build_brand_context_brief(
                        brand_name=brand_name,
                        url=url,
                        layers=result["magenta_circle"],
                        strategic_packet=packet_dict,
                    ).to_dict()
                    result["brand_context_brief"] = brand_context_brief
                    result["tldr_brand3"] = self._derive_tldr(result["magenta_circle"], packet_dict, brand_context_brief)
                    self._apply_tldr_generation_flow(
                        result=result,
                        brand_name=brand_name,
                        url=url,
                        packet_dict=packet_dict,
                        brand_context_brief=brand_context_brief,
                        research_pack=research_pack,
                        contextdev_candidate_summary=contextdev_candidate_summary,
                    )
                    result.setdefault("tldr_generation_mode", "legacy_code")
                    result["metrics"] = self._derive_metrics(result["magenta_circle"], result["tldr_brand3"])
                    result["diagnosis"] = self._derive_diagnosis(result["magenta_circle"], result["metrics"])
                    result["system_reading"] = self._derive_system_reading(
                        result["tldr_brand3"],
                        result["magenta_circle"],
                        result["metrics"],
                        evidence_packet_summary,
                    )
                    return result
            except Exception:
                pass

        result = self._extract_via_heuristic(
            evidence_text,
            visual_semantics,
            brand_name,
            url,
            collector_error="",
            strategic_evidence_packet=strategic_packet.to_dict(),
        )
        result["source_run_id"] = canonical_evidence.run_id
        result["source"] = "brand_audit_snapshot"
        result["extraction_mode"] = CANONICAL_EXTRACTION_MODE
        result["canonical_evidence_source"] = "brand_audit_snapshot"
        result["limitations"].extend(canonical_evidence.limitations)
        result["evidence_packet_summary"] = evidence_packet_summary
        if evidence_graph_summary:
            result["evidence_graph_summary"] = evidence_graph_summary
            result["research_pack_source"] = "evidence_graph"
        else:
            result["research_pack_source"] = "snapshot_builder"
        packet_dict = strategic_packet.to_dict()
        result["strategic_evidence_packet"] = packet_dict
        brand_context_brief = build_brand_context_brief(
            brand_name=brand_name,
            url=url,
            layers=result["magenta_circle"],
            strategic_packet=packet_dict,
        ).to_dict()
        result["brand_context_brief"] = brand_context_brief
        result["tldr_brand3"] = self._derive_tldr(result["magenta_circle"], packet_dict, brand_context_brief)
        self._apply_tldr_generation_flow(
            result=result,
            brand_name=brand_name,
            url=url,
            packet_dict=packet_dict,
            brand_context_brief=brand_context_brief,
            research_pack=research_pack,
            contextdev_candidate_summary=contextdev_candidate_summary,
        )
        result.setdefault("tldr_generation_mode", "legacy_code")
        result["metrics"] = self._derive_metrics(result["magenta_circle"], result["tldr_brand3"])
        result["diagnosis"] = self._derive_diagnosis(result["magenta_circle"], result["metrics"])
        result["system_reading"] = self._derive_system_reading(
            result["tldr_brand3"],
            result["magenta_circle"],
            result["metrics"],
            evidence_packet_summary,
        )
        return result

    @staticmethod
    def _build_research_pack(snapshot: dict[str, Any]) -> tuple[Any, dict[str, Any] | None]:
        if not BRAND3_BRAND_RESEARCH_GRAPH_PACK:
            return build_brand_research_pack_from_snapshot(snapshot), None
        graph = build_evidence_graph_from_snapshot(snapshot)
        return build_brand_research_pack_from_graph(graph), graph.summary()

    def _apply_tldr_generation_flow(
        self,
        *,
        result: dict[str, Any],
        brand_name: str,
        url: str,
        packet_dict: dict[str, Any],
        brand_context_brief: dict[str, Any],
        research_pack: Any | None = None,
        contextdev_candidate_summary: dict[str, Any] | None = None,
    ) -> None:
        result["research_pack"] = research_pack.to_dict() if hasattr(research_pack, "to_dict") else research_pack
        self._apply_contextdev_visual_enrichment_shadow(
            result=result,
            research_pack=research_pack,
            candidate_summary=contextdev_candidate_summary,
        )
        if BRAND3_MAGNETISM_RESEARCH_PACK_TLDR:
            self._apply_research_pack_tldr(
                result=result,
                brand_name=brand_name,
                url=url,
                packet_dict=packet_dict,
                brand_context_brief=brand_context_brief,
                research_pack=research_pack,
            )
            return

    @staticmethod
    def _contextdev_candidate_summary_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
        summary = snapshot.get("contextdev_candidate_summary")
        if isinstance(summary, dict):
            return summary

        contextdev = snapshot.get("contextdev")
        if isinstance(contextdev, dict):
            summary = contextdev.get("candidate_summary")
            if isinstance(summary, dict):
                return summary
        return None

    @staticmethod
    def _apply_contextdev_visual_enrichment_shadow(
        *,
        result: dict[str, Any],
        research_pack: Any | None,
        candidate_summary: dict[str, Any] | None,
    ) -> None:
        if not BRAND3_CONTEXTDEV_VISUAL_ENRICHMENT:
            return

        if research_pack is None:
            result["contextdev_visual_enrichment_shadow"] = {
                "status": "skipped",
                "reason": "missing_research_pack",
            }
            return

        if not isinstance(candidate_summary, dict):
            result["contextdev_visual_enrichment_shadow"] = {
                "status": "skipped",
                "reason": "missing_candidate_summary",
            }
            return

        try:
            dry_run = build_contextdev_research_pack_dry_run(
                research_pack,
                candidate_summary,
            ).to_dict()
        except Exception as exc:
            result["contextdev_visual_enrichment_shadow"] = {
                "status": "error",
                "reason": str(exc),
            }
            return

        enriched_pack = dry_run.get("enriched_pack", {})
        if not isinstance(enriched_pack, dict):
            enriched_pack = {}
        result["contextdev_visual_enrichment_shadow"] = {
            "status": "evaluated",
            "version": dry_run.get("version"),
            "field_updates": dry_run.get("field_updates") or [],
            "promotion_report": dry_run.get("promotion_report") or {},
            "enriched_pack_delta": {
                "visual_or_conceptual_signals": enriched_pack.get("visual_or_conceptual_signals", []),
                "product_summary": enriched_pack.get("product_summary"),
                "confidence_notes": enriched_pack.get("confidence_notes", []),
            },
        }

    def _apply_research_pack_tldr(
        self,
        *,
        result: dict[str, Any],
        brand_name: str,
        url: str,
        packet_dict: dict[str, Any],
        brand_context_brief: dict[str, Any],
        research_pack: Any | None = None,
    ) -> None:
        current_tldr = result.get("tldr_brand3")
        if not isinstance(current_tldr, dict):
            return

        if self.llm is None or not getattr(self.llm, "api_key", None):
            result["legacy_tldr_brand3"] = current_tldr
            result["tldr_generation_mode"] = "legacy_fallback_no_llm"
            result.setdefault("warnings", []).append(
                "Analyst Pass disabled because no LLM API key is available; legacy TLDR preserved."
            )
            return

        try:
            run = run_analyst_tldr_pass(
                llm=self.llm,
                brand_name=brand_name,
                url=url,
                research_pack=research_pack or brand_context_brief,
                current_tldr=current_tldr,
            )
        except Exception as exc:
            result["legacy_tldr_brand3"] = current_tldr
            result["tldr_generation_mode"] = "legacy_fallback_llm_error"
            result.setdefault("warnings", []).append(f"Analyst Pass failed; legacy TLDR preserved. error={exc}")
            return

        result["legacy_tldr_brand3"] = current_tldr
        result["analyst_tldr_raw"] = run.get("raw") or {}
        result["analyst_tldr_validated"] = run.get("validated") or {}
        result["analyst_tldr_analysis_error"] = run.get("analysis_error")

        if run.get("analysis_error"):
            result["tldr_generation_mode"] = "legacy_fallback_llm_error"
            warning = run["analysis_error"].get("detail") if isinstance(run["analysis_error"], dict) else "Analyst Pass failed."
            result.setdefault("warnings", []).append(f"Analyst Pass fallback: {warning}")
            result["tldr_brand3"] = current_tldr
            result["tldr_strategy"] = {
                "mode": "llm_analyst_pass_fallback",
                "validation_notes": [],
                "validation_warnings": [],
                "degraded_fields": [],
            }
            return

        validated = run.get("validated") if isinstance(run.get("validated"), dict) else {}
        tldr = validated.get("tldr_brand3") if isinstance(validated, dict) else {}
        if not isinstance(tldr, dict) or not tldr:
            result["tldr_generation_mode"] = "legacy_fallback_llm_error"
            result.setdefault("warnings", []).append("Analyst Pass returned no usable TLDR; legacy TLDR preserved.")
            result["tldr_brand3"] = current_tldr
            return

        result["tldr_brand3"] = tldr
        result["tldr_generation_mode"] = "analyst_pass_validated"
        result["tldr_strategy"] = {
            "mode": "llm_analyst_pass",
            "prompt_version": validated.get("prompt_version"),
            "validation_notes": validated.get("validation_notes") or [],
            "validation_warnings": validated.get("validation_warnings") or [],
            "degraded_fields": validated.get("degraded_fields") or [],
        }

    @staticmethod
    def _mark_legacy_direct_result(result: dict[str, Any], source_provider: str) -> None:
        result["source"] = LEGACY_DIRECT_SOURCE
        result["extraction_mode"] = LEGACY_DIRECT_EXTRACTION_MODE
        result["direct_source_provider"] = source_provider
        result["canonical_evidence_source"] = None
        result["deprecation"] = dict(LEGACY_DIRECT_DEPRECATION)

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
        sentences = self._sentences(web_markdown)

        keyword_signals = {
            "mindspace": ["just do it", "mantra", "belief", "earn", "fight", "inspire", "proprietary", "framework", "paradigm", "new model", "new paradigm", "únete", "unete", "nuevo modelo"],
            "aetherspace": ["mission", "purpose", "why", "founded", "exists", "values", "manifesto", "inspirar", "inspire", "regenerativo", "circular", "medio ambiente", "sostenible"],
            "gamespace": ["voice", "tone", "playful", "bold", "rebel", "sage", "creator", "trusted"],
            "envispace": ["design", "visual", "aesthetic", "palette", "typography", "minimal", "brutalist"],
            "netspace": ["value", "api", "developer", "automation", "platform", "infrastructure", "financial services", "servicios financieros", "accept payments", "aceptar pagos", "billing", "facturación", "product development", "planning and building", "teams and agents", "integration", "sdk", "innovadores", "productos innovadores", "soluciones", "ingredientes activos", "materias primas", "servicios ambientales"],
            "tactispace": ["creamos", "we create", "we build", "we provide", "mission", "vision", "roadmap", "future", "new model", "new paradigm", "misión", "vision", "visión", "futuro", "nuevo modelo"],
            "ambientspace": ["values", "trusted", "secure", "simple", "transparent", "offline", "event", "support", "performance", "custom agents", "ai agents", "prioritization", "okr planning", "growth tracking", "maratón", "maraton", "atletas", "athletes", "regenerativo", "circular", "sostenible", "sostenibles", "medio ambiente", "mediterráneo"],
        }

        layers: dict[str, Any] = {}
        for layer, keywords in keyword_signals.items():
            evidence = self._first_matching_sentence(sentences, keywords)
            finding = None
            detected = evidence is not None
            confidence = "medium" if detected else "insufficient"

            if layer == "tactispace" and evidence and self._is_testimonial_evidence(evidence):
                evidence = None
                detected = False
                confidence = "insufficient"

            if detected:
                finding = self._heuristic_finding(layer, evidence or "")

            if layer == "envispace" and isinstance(visual_semantics, dict):
                sem = visual_semantics.get("data") or {}
                style = sem.get("aesthetic_style")
                mood = sem.get("visual_mood")
                if style and not detected:
                    evidence = f"Visual style: {style}"
                    finding = f"Visual signature detected as {style}."
                    detected = True
                    confidence = "low"
                elif style and mood and detected:
                    finding = f"{finding} Visual analysis also reports {style} with a {mood} mood."

            layers[layer] = {
                "finding": finding,
                "evidence": evidence,
                "detected": detected,
                "confidence": confidence,
            }

        payload = {
            "brand_name": brand_name,
            "url": url,
            "magenta_circle": layers,
            "fallback_used": True,
        }
        if content_distillation_summary:
            payload["content_distillation_summary"] = content_distillation_summary
        if strategic_evidence_packet:
            payload["strategic_evidence_packet"] = strategic_evidence_packet
        normalized = self._normalize_analysis(payload)
        if collector_error:
            normalized["limitations"].append(f"Web collection fallback: {collector_error}")
        return normalized

    def _normalize_analysis(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize old and new extractor outputs into the canonical scanner schema."""
        normalized: dict[str, Any] = {
            "brand_name": str(raw.get("brand_name") or "Unknown Brand"),
            "url": str(raw.get("url") or ""),
            "analyzed_at": str(raw.get("analyzed_at") or datetime.now(timezone.utc).isoformat()),
            "fallback_used": bool(raw.get("fallback_used", False)),
            "limitations": [],
        }

        normalized["magenta_circle"] = self._normalize_layers(raw.get("magenta_circle") or raw.get("layers") or {})
        self._enrich_layers_from_legacy_text(raw, normalized["magenta_circle"])
        strategic_packet = raw.get("strategic_evidence_packet") if isinstance(raw.get("strategic_evidence_packet"), dict) else None
        if strategic_packet:
            self._enrich_layers_from_strategic_packet(normalized["magenta_circle"], strategic_packet)
        brand_context_brief = raw.get("brand_context_brief") if isinstance(raw.get("brand_context_brief"), dict) else None
        if not brand_context_brief:
            brand_context_brief = build_brand_context_brief(
                brand_name=normalized["brand_name"],
                url=normalized["url"],
                layers=normalized["magenta_circle"],
                strategic_packet=strategic_packet,
            ).to_dict()
        normalized["brand_context_brief"] = brand_context_brief
        normalized["tldr_brand3"] = self._derive_tldr(normalized["magenta_circle"], strategic_packet, brand_context_brief)
        if strategic_packet:
            normalized["strategic_evidence_packet"] = strategic_packet
        for key in (
            "research_pack",
            "analyst_tldr_raw",
            "analyst_tldr_validated",
            "analyst_tldr_analysis_error",
            "tldr_generation_mode",
            "legacy_tldr_brand3",
            "tldr_strategy",
        ):
            if key in raw:
                normalized[key] = raw[key]
        normalized["metrics"] = self._derive_metrics(normalized["magenta_circle"], normalized["tldr_brand3"])
        normalized["diagnosis"] = self._derive_diagnosis(normalized["magenta_circle"], normalized["metrics"])
        if isinstance(raw.get("content_distillation_summary"), dict):
            normalized["content_distillation_summary"] = raw["content_distillation_summary"]
        normalized["evidence_packet_summary"] = self._derive_evidence_packet_summary(normalized)
        normalized["system_reading"] = self._derive_system_reading(
            normalized["tldr_brand3"],
            normalized["magenta_circle"],
            normalized["metrics"],
            normalized["evidence_packet_summary"],
        )

        self._add_legacy_fields(normalized)
        return normalized

    def ensure_tldr_v03_contract(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Upgrade persisted scans that already have metrics/TLDR but predate the v0.3 block contract."""
        tldr = payload.get("tldr_brand3")
        layers = payload.get("magenta_circle")
        if not isinstance(tldr, dict) or not isinstance(layers, dict):
            return payload

        upgraded: dict[str, Any] = {}
        changed = False
        for key in TLDR_KEYS:
            layer_key = TLDR_TO_LAYER[key]
            block = tldr.get(key)
            if not isinstance(block, dict):
                block = self._empty_tldr_block(key, layer_key)
                changed = True
            if not self._has_tldr_v03_contract(block):
                changed = True
            upgraded[key] = self._with_tldr_contract(key, block, layers)

        if changed:
            payload = dict(payload)
            payload["tldr_brand3"] = upgraded
            self._add_legacy_fields(payload)
        if "evidence_packet_summary" not in payload:
            payload = dict(payload)
            payload["evidence_packet_summary"] = self._derive_evidence_packet_summary(payload)
        if "content_distillation_summary" not in payload:
            payload = dict(payload)
            payload["content_distillation_summary"] = None
        if "system_reading" not in payload:
            payload = dict(payload)
            payload["system_reading"] = self._derive_system_reading(
                payload["tldr_brand3"],
                layers,
                payload.get("metrics") or {},
                (
                    payload.get("evidence_packet_summary")
                    if isinstance(payload.get("evidence_packet_summary"), dict)
                    else None
                ),
            )
        return payload

    @staticmethod
    def _has_tldr_v03_contract(block: dict[str, Any]) -> bool:
        required = {
            "block",
            "question",
            "evidence_scope",
            "source_signal",
            "source_signal_path",
            "source_layer",
            "observations",
            "answer",
            "claim_type",
            "reasoning",
            "evidence_used",
            "counter_evidence",
            "human_review_recommended",
        }
        return required.issubset(block.keys())

    def _normalize_layers(self, raw_layers: dict[str, Any]) -> dict[str, Any]:
        layers: dict[str, Any] = {}
        for layer in LAYER_KEYS:
            raw_layer = raw_layers.get(layer) or {}

            old_evidence = raw_layer.get("evidence")
            evidence = self._normalize_evidence(old_evidence)
            finding = raw_layer.get("finding")
            if finding is None:
                finding = raw_layer.get("findings")
            finding = self._clean_optional_string(finding)

            detected_raw = raw_layer.get("detected")
            status_raw = str(raw_layer.get("status") or "").strip().lower()
            detected = bool(detected_raw) if isinstance(detected_raw, bool) else status_raw == "detected"
            if not detected and (finding or evidence):
                detected = status_raw != "not_detected"

            if not detected:
                finding = None
                evidence = None

            if layer == "tactispace" and finding and "cta" in finding.lower():
                finding = None
                evidence = None
                detected = False

            confidence = str(raw_layer.get("confidence") or "").strip().lower()
            if confidence not in {"high", "medium", "low", "insufficient"}:
                confidence = "medium" if detected else "insufficient"

            layers[layer] = {
                "finding": finding,
                "evidence": evidence,
                "detected": detected,
                "confidence": confidence,
                # Compatibility fields used by existing templates/tests.
                "status": "detected" if detected else "not_detected",
                "findings": finding or "No clear signal detected in the provided sources.",
                "evidence_list": [evidence] if evidence else [],
            }
        return layers

    def _enrich_layers_from_strategic_packet(
        self,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any],
    ) -> None:
        """Project normalized Brand Audit evidence groups onto Magenta layers.

        Brand Audit owns collection and normalization. This step keeps the
        Magenta Circle aligned with the same evidence packet used by TLDR blocks
        instead of relying only on keyword hits over serialized text.
        """
        groups = strategic_packet.get("groups") if isinstance(strategic_packet, dict) else {}
        if not isinstance(groups, dict):
            return

        layer_group_map = {
            "mindspace": ["hero_claims"],
            "netspace": ["product_offer", "outcome", "audience"],
            "gamespace": ["personality_tone"],
            "ambientspace": ["values_language"],
        }
        for layer_key, group_names in layer_group_map.items():
            if layers.get(layer_key, {}).get("detected"):
                continue
            item = self._first_packet_item(groups, group_names)
            if not item:
                continue
            evidence = item["text"]
            confidence = self._packet_layer_confidence(layer_key, groups, item.get("group"))
            self._set_layer_from_packet(layers, layer_key, evidence, confidence)

        if not layers.get("tactispace", {}).get("detected"):
            tactispace_evidence = self._first_accepted_tactispace_packet_evidence(strategic_packet)
            if tactispace_evidence:
                self._set_layer_from_packet(layers, "tactispace", tactispace_evidence, "medium")

    @staticmethod
    def _first_packet_item(
        groups: dict[str, Any],
        group_names: list[str],
    ) -> dict[str, str] | None:
        candidates: list[dict[str, str]] = []
        for group in group_names:
            for item in groups.get(group) or []:
                if not isinstance(item, dict):
                    continue
                text = MagnetismExtractor._clean_evidence_phrase(str(item.get("text") or ""))
                if not text or MagnetismExtractor._is_navigation_noise(text):
                    continue
                candidates.append({
                    "text": text,
                    "group": group,
                    "source_type": str(item.get("source_type") or ""),
                    "feature_name": str(item.get("feature_name") or ""),
                })
        if not candidates:
            return None
        return sorted(candidates, key=strategic_packet_candidate_priority)[0]

    def _first_accepted_tactispace_packet_evidence(self, strategic_packet: dict[str, Any]) -> str | None:
        for key in ("mission", "vision"):
            spec = TLDR_BLOCK_INTERPRETER_SPECS[key]
            candidates = strategic_packet_candidates(
                key,
                spec,
                strategic_packet,
                str(TLDR_TO_LAYER.get(key, "netspace")),
            )
            accepted = accepted_block_evidence(key, spec, candidates)
            if accepted:
                return accepted[0]["text"]
        return None

    @staticmethod
    def _packet_layer_confidence(
        layer_key: str,
        groups: dict[str, Any],
        primary_group: str | None,
    ) -> str:
        if layer_key == "netspace":
            has_offer = bool(groups.get("product_offer"))
            has_outcome = bool(groups.get("outcome"))
            if has_offer and has_outcome:
                return "high"
            if has_offer or primary_group in {"outcome", "audience"}:
                return "medium"
            return "low"
        return "medium"

    def _set_layer_from_packet(
        self,
        layers: dict[str, Any],
        layer_key: str,
        evidence: str,
        confidence: str,
    ) -> None:
        finding = self._heuristic_finding(layer_key, evidence)
        layers[layer_key] = {
            "finding": finding,
            "evidence": evidence,
            "detected": True,
            "confidence": confidence,
            "status": "detected",
            "findings": finding,
            "evidence_list": [evidence],
        }

    def _derive_tldr(
        self,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any] | None = None,
        brand_context_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tldr: dict[str, Any] = {}
        for key in TLDR_KEYS:
            layer_key = TLDR_TO_LAYER[key]
            layer = layers[layer_key]

            if key in TLDR_BLOCK_INTERPRETER_SPECS:
                interpreted = self._interpret_tldr_block_from_spec(key, layers, strategic_packet, brand_context_brief)
                tldr[key] = self._with_tldr_contract(key, interpreted or self._empty_tldr_block(key, layer_key), layers)
                continue

            content: Any = self._tldr_content_from_layer(layer) if layer["detected"] else None
            evidence = self._evidence_list(layer.get("evidence")) if layer["detected"] else []
            confidence = layer.get("confidence") if layer["detected"] else "insufficient"
            mode = self._default_tldr_mode(key, layer)
            rationale = self._default_tldr_rationale(key, mode)
            if content and evidence:
                content, mode, rationale = self._apply_block_specific_content_rules(
                    key, content, evidence, mode, rationale
                )

            if key == "personality" and not content:
                personality = self._derive_personality_block(layers)
                if personality:
                    tldr[key] = self._with_tldr_contract(key, personality, layers)
                    continue

            if key == "brand_idea" and not content:
                brand_idea = self._derive_brand_idea_block(layers)
                if brand_idea:
                    tldr[key] = self._with_tldr_contract(key, brand_idea, layers)
                    continue

            if key in {"attributes", "values"} and (content or evidence or layer["detected"]):
                attribute_text = self._joined_layer_evidence(
                    layers, ["ambientspace", "aetherspace", "netspace", "mindspace"]
                )
                seed_content = "" if content is None else str(content)
                content = self._extract_three_terms(" ".join([attribute_text, seed_content, *evidence]), key)
                if not content:
                    content = None

            block = {
                "content": content,
                "detected": bool(content),
                "mode": mode if content else "not_detected",
                "confidence": confidence if content else "insufficient",
                "evidence": evidence if content else [],
                "rationale": rationale if content else "Insufficient evidence to articulate this block responsibly.",
                "source_layers": [layer_key],
                "human_review_recommended": False,
            }
            tldr[key] = self._with_tldr_contract(key, block, layers)
        return tldr

    def _interpret_tldr_block_from_spec(
        self,
        key: str,
        layers: dict[str, Any],
        strategic_packet: dict[str, Any] | None = None,
        brand_context_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        spec = TLDR_BLOCK_INTERPRETER_SPECS[key]
        candidates = block_evidence_candidates(
            key,
            spec,
            layers,
            strategic_packet,
            TLDR_TO_LAYER[key],
            brand_context_brief,
        )
        return interpret_tldr_block(
            key,
            spec,
            candidates,
            layers,
            TLDR_TO_LAYER[key],
        )

    @staticmethod
    def _is_testimonial_evidence(text: str) -> bool:
        low = text.strip().lower()
        return low.startswith((">", "“", "\"")) or " nos ofrece " in low or " customer " in low

    @staticmethod
    def _empty_tldr_block(key: str, layer_key: str) -> dict[str, Any]:
        return {
            "content": None,
            "detected": False,
            "mode": "not_detected",
            "confidence": "insufficient",
            "evidence": [],
            "rationale": "Insufficient evidence to articulate this block responsibly.",
            "source_layers": [layer_key],
            "human_review_recommended": False,
        }

    def _with_tldr_contract(
        self,
        key: str,
        block: dict[str, Any],
        layers: dict[str, Any],
    ) -> dict[str, Any]:
        """Upgrade a TLDR block to the v0.3 epistemic contract while preserving legacy keys."""
        contract = TLDR_BLOCK_CONTRACT[key]
        detected = bool(block.get("detected"))
        evidence_used = self._evidence_list(block.get("evidence") or block.get("evidence_used"))
        confidence = self._normalize_tldr_confidence(block.get("confidence"), detected)
        mode = str(block.get("mode") or ("not_detected" if not detected else "interpreted_from_discourse"))
        if not detected:
            mode = "not_detected"

        claim_type = str(block.get("claim_type") or self._infer_claim_type(key, mode, detected))
        observations = block.get("observations")
        if not isinstance(observations, list) or not observations:
            observations = self._observations_for_block(key, evidence_used, block.get("content"))

        counter_evidence = block.get("counter_evidence")
        if not isinstance(counter_evidence, list):
            counter_evidence = []
        if not counter_evidence:
            counter_evidence = self._default_counter_evidence(key, claim_type, detected, layers)

        human_review = bool(block.get("human_review_recommended"))
        if self._should_recommend_human_review(key, claim_type, mode, confidence, detected, evidence_used):
            human_review = True

        answer = block.get("answer")
        if answer is None:
            answer = block.get("content")

        upgraded = dict(block)
        upgraded.update(
            {
                "block": key,
                "question": contract["question"],
                "evidence_scope": contract["evidence_scope"],
                "source_signal": contract["source_signal"],
                "source_signal_path": contract["source_signal_path"],
                "source_layer": contract["source_layer"],
                "observations": observations,
                "answer": answer,
                "claim_type": claim_type,
                "mode": mode,
                "confidence": confidence,
                "reasoning": block.get("reasoning") or block.get("rationale"),
                "evidence_used": evidence_used,
                "counter_evidence": counter_evidence,
                "human_review_recommended": human_review,
                # Compatibility aliases used by current templates/tests.
                "content": block.get("content"),
                "evidence": evidence_used,
                "rationale": block.get("rationale") or block.get("reasoning"),
            }
        )
        return upgraded

    @staticmethod
    def _normalize_tldr_confidence(value: Any, detected: bool) -> str:
        confidence = str(value or "").strip().lower()
        if confidence in {"high", "medium", "low"}:
            return confidence
        return "low" if not detected else "medium"

    @staticmethod
    def _infer_claim_type(key: str, mode: str, detected: bool) -> str:
        if not detected:
            return "absent"
        if mode in {"literal", "compressed"} and key in DECLARATIVE_TLDR_BLOCKS:
            return "declared"
        if key in PERFORMED_TLDR_BLOCKS:
            return "performed"
        return "inferred"

    @staticmethod
    def _observations_for_block(key: str, evidence_used: list[str], content: Any) -> list[str]:
        observations: list[str] = []
        if evidence_used:
            observations.append(f"Uses {len(evidence_used)} traceable evidence item(s) selected for {key}.")
        if content:
            observations.append("Produces a bounded Brand3 articulation from the selected evidence.")
        if not observations:
            observations.append("No sufficient public evidence was selected for this block.")
        return observations

    @staticmethod
    def _default_counter_evidence(
        key: str,
        claim_type: str,
        detected: bool,
        layers: dict[str, Any],
    ) -> list[str]:
        if not detected:
            return ["No sufficient public evidence was found for this TLDR block."]
        if claim_type == "inferred":
            return ["The brand does not explicitly declare this exact Brand3 articulation in the available evidence."]
        if key in STRATEGIC_TLDR_BLOCKS and not layers.get(TLDR_TO_LAYER[key], {}).get("detected"):
            return ["The primary Magenta Circle layer for this block is weak or absent."]
        return []

    @staticmethod
    def _should_recommend_human_review(
        key: str,
        claim_type: str,
        mode: str,
        confidence: str,
        detected: bool,
        evidence_used: list[str],
    ) -> bool:
        if not detected:
            return False
        if mode == "needs_human_review":
            return True
        if key in STRATEGIC_TLDR_BLOCKS and claim_type == "inferred":
            return confidence == "low" or len(evidence_used) < 2
        return False

    def _derive_metrics(self, layers: dict[str, Any], tldr: dict[str, Any]) -> dict[str, Any]:
        magnetism_text = tldr["magnetism"].get("content") or ""
        magnetism_breakdown = self._magnetism_phrase_breakdown(str(magnetism_text))
        phrase_score = self._weighted_score(
            magnetism_breakdown,
            {
                "originality": 0.30,
                "specificity": 0.25,
                "memorability": 0.25,
                "verifiable_promise": 0.20,
            },
        )
        internal_layers = ["mindspace", "aetherspace", "envispace"]
        internal_detected = {
            "mindspace": layers["mindspace"]["detected"],
            "aetherspace": layers["aetherspace"]["detected"],
            "envispace": layers["envispace"]["detected"] or bool(tldr["brand_idea"].get("detected")),
        }
        internal_score = round(
            sum(100 if internal_detected[layer] else 0 for layer in internal_layers)
            / len(internal_layers)
        )
        magnetism_score = round((phrase_score * 0.55) + (internal_score * 0.45))

        completeness = round(
            sum(1 for block in tldr.values() if block.get("detected")) / len(TLDR_KEYS) * 100
        )
        semantic_alignment = self._semantic_alignment_score(layers)
        absence_of_contradiction = self._absence_of_contradiction_score(tldr)
        coherence_score = round(
            (completeness * 0.40)
            + (semantic_alignment * 0.40)
            + (absence_of_contradiction * 0.20)
        )

        quadrant = self._quadrant(magnetism_score, coherence_score)
        return {
            "magnetism_score": self._clamp(magnetism_score),
            "magnetism_tier": self._magnetism_tier(magnetism_score),
            "magnetism_breakdown": magnetism_breakdown,
            "coherence_score": self._clamp(coherence_score),
            "coherence_tier": self._coherence_tier(coherence_score),
            "coherence_breakdown": {
                "completeness": self._clamp(completeness),
                "semantic_alignment": self._clamp(semantic_alignment),
                "absence_of_contradiction": self._clamp(absence_of_contradiction),
            },
            "quadrant": quadrant,
        }

    def _derive_diagnosis(self, layers: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
        detected = [layer for layer, value in layers.items() if value["detected"]]
        missing = [layer for layer, value in layers.items() if not value["detected"]]
        detected_count = len(detected)

        headline = (
            f"Marca con {detected_count}/7 capas detectadas: magnetismo {metrics['magnetism_tier'].lower()} "
            f"y coherencia {metrics['coherence_tier'].lower()}."
        )
        observations = [
            f"Capas detectadas: {', '.join(detected) if detected else 'ninguna'}.",
            f"Capas sin evidencia suficiente: {', '.join(missing) if missing else 'ninguna'}.",
            "El diagnostico se limita a senales observables; no incluye recomendaciones estrategicas no validadas.",
        ]
        if detected_count <= 5:
            observations.append(
                "Si el score baja, puede deberse a cobertura insuficiente de evidencia publica, no necesariamente a debilidad estrategica de la marca."
            )
        return {"headline": headline, "key_observations": observations}

    def _derive_evidence_packet_summary(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Summarize the shared evidence basis without embedding a second report."""
        source = str(payload.get("source") or "")
        url = str(payload.get("url") or "")
        if source == "brand_audit_snapshot":
            source_key = "brand_audit_snapshot"
            source_label = "Brand Audit evidence packet"
            evidence_basis = "Shared Brand Audit snapshot reused by Magnetism lenses."
        elif url == "manual" or not url:
            source_key = "manual_evidence"
            source_label = "Manual evidence packet"
            evidence_basis = "Manual evidence provided for this scan."
        else:
            source_key = "direct_web_scan"
            source_label = "Direct web evidence packet"
            evidence_basis = "Direct web scan evidence collected for this Magnetism run."

        layers = payload.get("magenta_circle") or {}
        detected_signal_count = sum(1 for layer in layers.values() if isinstance(layer, dict) and layer.get("detected"))
        layer_evidence_count = sum(
            1
            for layer in layers.values()
            if isinstance(layer, dict) and (layer.get("evidence") or layer.get("evidence_list"))
        )
        distillation = payload.get("content_distillation_summary")
        selected_count = 0
        quality_score = None
        if isinstance(distillation, dict):
            selected_count = int(distillation.get("selected_count") or 0)
            quality_score = distillation.get("quality_score")
        return {
            "source": source_key,
            "source_label": source_label,
            "evidence_basis": evidence_basis,
            "detected_signal_count": detected_signal_count,
            "total_signal_count": len(LAYER_KEYS),
            "layer_evidence_count": layer_evidence_count,
            "distilled_evidence_count": selected_count,
            "distillation_quality_score": quality_score,
            "value_policy": "Only TLDR-relevant evidence is surfaced in this view; raw extraction remains upstream.",
            "proof_support": {
                "status": "not_detected",
                "count": 0,
                "evidence": [],
                "reading": "No public proof signals were available in this evidence packet.",
            },
        }

    @staticmethod
    def _brand_audit_evidence_packet_summary(
        snapshot: dict[str, Any],
        strategic_packet: StrategicEvidencePacket | None = None,
    ) -> dict[str, Any]:
        evidences = collect_evidences(snapshot)
        raw_inputs = snapshot.get("raw_inputs") or []
        sources = sorted({str(item.get("source")) for item in raw_inputs if item.get("source")})
        run = snapshot.get("run") or {}
        audit = run.get("audit") or {}
        data_quality = audit.get("data_quality") or run.get("data_quality")
        summary = {
            "source": "brand_audit_snapshot",
            "source_label": "Brand Audit evidence packet",
            "evidence_basis": "Shared Brand Audit snapshot reused by Magnetism lenses.",
            "run_id": run.get("id"),
            "raw_input_count": len(raw_inputs),
            "evidence_item_count": len(snapshot.get("evidence_items") or []),
            "derived_evidence_count": len(evidences),
            "feature_count": len(snapshot.get("features") or []),
            "sources": sources,
            "data_quality": data_quality,
            "value_policy": "Brand Audit owns collection; Magnetism only interprets the shared evidence packet.",
        }
        if strategic_packet is not None:
            strategic_summary = strategic_packet.to_summary()
            proof_lines = strategic_packet.groups.get("proof_points", [])
            summary["strategic_group_counts"] = strategic_summary.get("group_counts")
            summary["strategic_source_counts"] = strategic_summary.get("source_counts")
            summary["strategic_rejected_count"] = strategic_summary.get("rejected_count")
            summary["strategic_warnings"] = strategic_summary.get("warnings")
            summary["value_policy"] = strategic_summary.get("value_policy") or summary["value_policy"]
            summary["proof_support"] = {
                "status": "observed" if proof_lines else "not_detected",
                "count": len(proof_lines),
                "evidence": [line.to_dict() for line in proof_lines[:3]],
                "reading": (
                    "Observed public proof signals can support credibility, but they do not define mission, "
                    "personality, values, or brand idea."
                    if proof_lines
                    else "No public proof signals were available in the strategic evidence packet."
                ),
            }
        return summary

    @staticmethod
    def _derive_system_reading(
        tldr: dict[str, Any],
        layers: dict[str, Any],
        metrics: dict[str, Any],
        evidence_packet_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Derive concise reverse-engineering outputs inside TLDR instead of a parallel report."""
        def detected(block_name: str) -> bool:
            block = tldr.get(block_name) or {}
            return bool(block.get("detected") or block.get("answer") or block.get("content"))

        tensions: list[str] = []
        questions: list[str] = []

        value_detected = detected("value_proposition")
        magnetism_score = int(metrics.get("magnetism_score") or 0)
        weak_layers = [key for key, layer in layers.items() if isinstance(layer, dict) and not layer.get("detected")]
        detected_block_count = sum(1 for key in TLDR_KEYS if detected(key))
        limited_evidence_coverage = len(weak_layers) >= 2 or detected_block_count <= 7

        if value_detected and not detected("personality"):
            tensions.append(
                "The offer is functionally visible, but the brand voice/personality is not yet observable from the evidence."
            )
            questions.append(
                "Should the buyer remember operational utility, trust, ambition, or a sharper point of view?"
            )

        if value_detected and not detected("brand_idea"):
            tensions.append(
                "The product logic is clearer than the larger brand idea connecting category, expression, and point of view."
            )
            questions.append(
                "What category belief or metaphor should make the offer easier to recognize and repeat?"
            )

        if value_detected and not detected("mission") and not detected("vision"):
            tensions.append(
                "The current offer is clearer than the brand's operating mission or future direction."
            )
            questions.append(
                "What does the company explicitly do today, and what future change is it building toward?"
            )

        if value_detected and magnetism_score and magnetism_score < 70:
            tensions.append(
                "The offer has usable evidence, but the magnetic hook may not yet create strong first-screen memory."
            )
            questions.append(
                "Which phrase or tension should a buyer retain after the first visit?"
            )

        if limited_evidence_coverage:
            tensions.insert(
                0,
                "Some score pressure comes from limited public evidence coverage, not necessarily from strategic weakness in the brand itself."
            )
            questions.insert(
                0,
                "Which missing internal or public evidence should be supplied before treating the score as a strategic verdict?"
            )

        if not tensions:
            if len(weak_layers) >= 4:
                tensions.append(
                    "The scan has limited observable signal coverage, so strategic conclusions should stay provisional."
                )
                questions.append(
                    "Which missing signals should be supplied by internal materials before using this as strategy?"
                )

        proof_support = (
            evidence_packet_summary.get("proof_support")
            if isinstance(evidence_packet_summary, dict)
            and isinstance(evidence_packet_summary.get("proof_support"), dict)
            else None
        )
        if proof_support and proof_support.get("status") == "observed":
            credibility_support = {
                "status": "observed",
                "count": int(proof_support.get("count") or 0),
                "evidence": proof_support.get("evidence") or [],
                "reading": proof_support.get("reading")
                or "Observed public proof signals support credibility without defining the brand strategy.",
            }
        else:
            credibility_support = {
                "status": "not_detected",
                "count": 0,
                "evidence": [],
                "reading": "No public proof signals were available for a separate credibility reading.",
            }

        return {
            "strategic_tensions": tensions[:3],
            "validation_questions": questions[:3],
            "credibility_support": credibility_support,
            "derived_from": "TLDR Brand3 blocks and Magenta signal coverage",
        }

    def _add_legacy_fields(self, payload: dict[str, Any]) -> None:
        """Keep current storage/routes/templates working while the UI migrates."""
        metrics = payload["metrics"]
        diagnosis = payload["diagnosis"]
        tldr = payload["tldr_brand3"]

        payload["magnetism_score"] = metrics["magnetism_score"]
        payload["coherence_score"] = metrics["coherence_score"]
        payload["quadrant"] = metrics["quadrant"]
        payload["executive_headline"] = diagnosis["headline"]
        payload["observations"] = diagnosis["key_observations"][:3]
        payload["tldr_grid"] = {
            "niche": self._legacy_value(tldr["core_purpose"]),
            "value_proposition": self._legacy_value(tldr["value_proposition"]),
            "target_audience": "(no detectado)",
            "friction": "(no detectado)",
            "uniqueness": self._legacy_value(tldr["brand_idea"]),
            "primary_cta": self._legacy_value(tldr["mission"]),
            "core_promise": self._legacy_value(tldr["magnetism"]),
            "behavioral_hook": self._legacy_value(tldr["vision"]),
            "tone": self._legacy_value(tldr["personality"]),
        }
        payload["score_breakdown"] = {
            "magnetism": {
                "emotional_appeal": metrics["magnetism_breakdown"]["memorability"],
                "functional_differentiation": metrics["magnetism_breakdown"]["specificity"],
                "narrative_gravitas": metrics["magnetism_breakdown"]["originality"],
                "assessment": "Derived from detected internal layers and the literal magnetism phrase.",
            },
            "coherence": {
                "visual_identity": metrics["coherence_breakdown"]["semantic_alignment"],
                "tactical_alignment": metrics["coherence_breakdown"]["completeness"],
                "message_consistency": metrics["coherence_breakdown"]["absence_of_contradiction"],
                "assessment": "Derived from TLDR completeness, critical layer pairs, and contradiction checks.",
            },
        }

    @staticmethod
    def _brand_audit_evidence_text(snapshot: dict[str, Any]) -> str:
        evidences = collect_evidences(snapshot)
        preferred = [
            ev for ev in evidences
            if str(ev.source_type) in {"owned", "social"}
        ]
        evidence_source = preferred or evidences

        lines: list[str] = []
        seen: set[str] = set()
        for ev in evidence_source:
            quote = MagnetismExtractor._clean_evidence_phrase(str(ev.quote or ""))
            if not quote or MagnetismExtractor._is_unusable_audit_quote(quote):
                continue
            key = quote.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {quote}")
            if len(lines) >= 80:
                break

        if lines:
            return '\n'.join(lines)

        # Last-resort fallback: owned web raw input often contains markdown.
        for raw_input in reversed(snapshot.get("raw_inputs") or []):
            if raw_input.get("source") != "web":
                continue
            payload = raw_input.get("payload") or {}
            markdown = payload.get("markdown_content") or payload.get("content") or ""
            if markdown:
                return str(markdown)[:8000]
        return ""

    @staticmethod
    def _is_unusable_audit_quote(value: str) -> bool:
        low = value.lower().strip()
        if low.startswith(("http://", "https://")):
            return True
        if len(value) < 6:
            return True
        if any(marker in low for marker in ("; evidence=", "source_type=", "dimension=", "feature=")):
            return True
        if any(marker in low for marker in ("/news/", "graphql api", "product roadmap", "__next_data__")):
            return True
        return False

    @staticmethod
    def _visual_semantics_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        for raw_input in reversed(snapshot.get("raw_inputs") or []):
            if raw_input.get("source") != "visual_signature":
                continue
            payload = raw_input.get("payload") or {}
            semantics = payload.get("semantics")
            if semantics:
                return {"status": "detected", "data": semantics}
            if payload.get("signature", {}).get("semantics"):
                return {"status": "detected", "data": payload["signature"]["semantics"]}
        return {"status": "not_detected", "data": {}}

    @staticmethod
    def _snapshot_limitations(snapshot: dict[str, Any]) -> list[str]:
        limitations: list[str] = []
        run = snapshot.get("run") or {}
        audit = run.get("audit") or {}
        data_quality = audit.get("data_quality") or run.get("data_quality")
        if data_quality:
            limitations.append(f"Brand Audit data quality: {data_quality}")
        if not snapshot.get("evidence_items") and not snapshot.get("features"):
            limitations.append("Brand Audit snapshot has no persisted feature evidence.")
        return limitations

    @staticmethod
    def _evidence_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if value:
            return [str(value).strip()]
        return []

    @staticmethod
    def _default_tldr_mode(key: str, layer: dict[str, Any]) -> str:
        finding = str(layer.get("finding") or "")
        if not layer.get("detected"):
            return "not_detected"
        if finding and not finding.startswith("Detected "):
            return "interpreted_from_discourse"
        if key in {"magnetism", "value_proposition", "mission"}:
            return "compressed"
        return "interpreted_from_discourse"

    @staticmethod
    def _default_tldr_rationale(key: str, mode: str) -> str:
        if mode == "compressed":
            return f"The {key} block is compressed from direct evidence."
        if mode == "literal":
            return f"The {key} block is directly stated in the evidence."
        if mode == "interpreted_from_discourse":
            return f"The {key} block is articulated from observed discourse signals."
        return "Insufficient evidence to articulate this block responsibly."

    @staticmethod
    def _apply_block_specific_content_rules(
        key: str,
        content: Any,
        evidence: list[str],
        mode: str,
        rationale: str,
    ) -> tuple[Any, str, str]:
        """Keep declarative blocks grounded in quoted evidence instead of LLM paraphrase."""
        if key in {"magnetism", "value_proposition"}:
            return evidence[0], "compressed", f"The {key} block is compressed from direct evidence."
        if key == "core_purpose":
            return (
                evidence[0],
                "interpreted_from_discourse",
                "The core_purpose block is a Brand3 hypothesis constrained to the available purpose signal.",
            )
        return content, mode, rationale

    def _derive_personality_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"])
        if not text:
            return None
        low = text.lower()
        sage = any(term in low for term in ("funcional", "materias primas", "biorremediación", "bioremediation", "technical", "infrastructure", "api"))
        caregiver = any(term in low for term in ("regenerativo", "medio ambiente", "salud", "nutrition", "nutrición", "sostenible", "sostenibles"))
        creator = any(term in low for term in ("creamos", "create", "formulaciones", "ingredients", "ingredientes", "materias primas"))
        hero = any(term in low for term in ("just do it", "atletas", "athletes", "maratón", "marathon", "performance", "inspirar", "inspire"))
        if not any((sage, caregiver, creator, hero)):
            return None
        traits = []
        if hero:
            traits.append("Hero")
        if sage:
            traits.append("Applied Sage")
        if caregiver:
            traits.append("Caregiver")
        if creator:
            traits.append("scientific Creator")
        content = self._compose_personality_content(traits)
        evidence = self._first_layer_evidences(layers, ["netspace", "aetherspace", "ambientspace", "mindspace"], limit=3)
        return {
            "content": content,
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "medium" if len(evidence) >= 2 else "low",
            "evidence": evidence,
            "rationale": "The personality is inferred from repeated discourse patterns, not from a declared personality statement.",
            "source_layers": ["gamespace", "netspace", "ambientspace"],
            "human_review_recommended": False,
        }

    def _derive_brand_idea_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["mindspace", "aetherspace", "netspace", "ambientspace"])
        low = text.lower()
        if any(term in low for term in ("just do it", "atletas", "athletes")) and any(
            term in low for term in ("innovadores", "performance", "maratón", "marathon", "productos")
        ):
            evidence = self._first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=3)
            return {
                "content": "Action-led athletic performance for every athlete.",
                "detected": True,
                "mode": "interpreted_from_discourse",
                "confidence": "medium" if len(evidence) >= 2 else "low",
                "evidence": evidence,
                "rationale": "The brand idea is articulated from the action mantra, athlete purpose, and performance-product context.",
                "source_layers": ["envispace", "mindspace", "aetherspace", "netspace"],
                "human_review_recommended": False,
            }
        if not ("macroalgas" in low and ("regenerativo" in low or "medio ambiente" in low)):
            return None
        evidence = self._first_layer_evidences(layers, ["mindspace", "aetherspace", "netspace"], limit=2)
        return {
            "content": "Mediterranean biotech translated into a regenerative industrial identity.",
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "low",
            "evidence": evidence,
            "rationale": "The idea connects Mediterranean origin, biotech material, industry, and environmental regeneration; visual evidence is still needed.",
            "source_layers": ["envispace", "mindspace", "aetherspace"],
            "human_review_recommended": False,
        }

    def _derive_mission_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(
            layers, ["tactispace", "netspace", "aetherspace", "ambientspace", "mindspace"]
        )
        sentences = self._sentences(text)
        evidence = self._first_matching_sentence(sentences, ["creamos", "we create", "we build", "we provide"])
        if not evidence:
            return None
        return {
            "content": evidence,
            "detected": True,
            "mode": "compressed",
            "confidence": "medium",
            "evidence": [evidence],
            "rationale": "The evidence states a present-tense operating activity.",
            "source_layers": ["tactispace", "netspace"],
            "human_review_recommended": False,
        }

    def _derive_vision_block(self, layers: dict[str, Any]) -> dict[str, Any] | None:
        text = self._joined_layer_evidence(layers, ["mindspace", "aetherspace", "ambientspace"])
        sentences = self._sentences(text)
        evidence = self._first_matching_sentence(sentences, ["nuevo modelo", "future", "vision", "futuro"])
        if not evidence:
            return None
        return {
            "content": "A regenerative industrial model built around the potential of Mediterranean macroalgae."
            if "macroalgas" in evidence.lower()
            else evidence,
            "detected": True,
            "mode": "interpreted_from_discourse",
            "confidence": "medium",
            "evidence": [evidence],
            "rationale": "The evidence points to a future category model rather than only a current offer.",
            "source_layers": ["tactispace", "mindspace"],
            "human_review_recommended": False,
        }

    @staticmethod
    def _compose_personality_content(traits: list[str]) -> str:
        if not traits:
            return ""
        if len(traits) == 1:
            return traits[0]
        if len(traits) == 2:
            return f"{traits[0]} with {traits[1]} traits."
        return f"{traits[0]} with {traits[1]} and {traits[2]} traits."

    @staticmethod
    def _joined_layer_evidence(layers: dict[str, Any], layer_keys: list[str]) -> str:
        values: list[str] = []
        for key in layer_keys:
            layer = layers.get(key) or {}
            if layer.get("evidence"):
                values.append(str(layer["evidence"]))
            if layer.get("finding"):
                values.append(str(layer["finding"]))
        return "\n".join(values)

    @staticmethod
    def _first_layer_evidences(layers: dict[str, Any], layer_keys: list[str], limit: int) -> list[str]:
        evidence: list[str] = []
        for key in layer_keys:
            layer_evidence = layers.get(key, {}).get("evidence")
            if layer_evidence and layer_evidence not in evidence:
                evidence.append(str(layer_evidence))
            if len(evidence) >= limit:
                break
        return evidence

    def _enrich_layers_from_legacy_text(self, raw: dict[str, Any], layers: dict[str, Any]) -> None:
        if raw.get("metrics") or raw.get("tldr_brand3"):
            return

        text_parts: list[str] = []
        for layer in (raw.get("magenta_circle") or {}).values():
            evidence = layer.get("evidence") if isinstance(layer, dict) else None
            if isinstance(evidence, list):
                text_parts.extend(str(item) for item in evidence if item)
            elif evidence:
                text_parts.append(str(evidence))
        for value in (raw.get("tldr_grid") or {}).values():
            if value:
                text_parts.append(str(value))

        text = "\n".join(text_parts)
        if not text.strip():
            return

        sentences = self._sentences(text)
        keyword_signals = {
            "mindspace": ["únete", "unete", "nuevo modelo", "new model", "new paradigm", "mantra", "proprietary", "framework", "paradigm"],
            "aetherspace": ["regenerativo", "circular", "medio ambiente", "sostenible", "purpose", "mission", "manifesto"],
            "netspace": ["soluciones", "ingredientes activos", "materias primas", "servicios ambientales", "cosmética", "nutracéutica", "biorremediación", "api", "infrastructure", "financial services", "servicios financieros", "product development", "planning and building", "teams and agents"],
            "ambientspace": ["regenerativo", "circular", "sostenible", "sostenibles", "medio ambiente", "mediterráneo", "transparent", "secure"],
        }
        for layer, keywords in keyword_signals.items():
            if layers[layer]["detected"]:
                continue
            evidence = self._first_matching_sentence(sentences, keywords)
            if not evidence:
                continue
            finding = self._heuristic_finding(layer, evidence)
            layers[layer].update(
                {
                    "finding": finding,
                    "evidence": evidence,
                    "detected": True,
                    "confidence": "low",
                    "status": "detected",
                    "findings": finding,
                    "evidence_list": [evidence],
                }
            )

    @staticmethod
    def _infer_brand_name(url_str: str) -> str:
        if not url_str:
            return "Manual Upload Brand"
        parsed = urlparse(url_str if "://" in url_str else f"https://{url_str}")
        host = parsed.netloc or parsed.path
        if host.startswith("www."):
            host = host[4:]
        return host.split(".")[0].capitalize()

    @staticmethod
    def _sentences(text: str) -> list[str]:
        raw_segments = [s.strip() for s in re.split(r"[.!?\n]+", text or "") if len(s.strip()) > 5]
        segments: list[str] = []
        for segment in raw_segments:
            if len(segment) <= 320:
                segments.append(segment)
                continue
            cuts = re.split(
                r"(?=\b(?:Macroalgas|Soluciones|Únete|Unete|Ingredientes|Creamos|Servicios|Nuestras)\b)",
                segment,
            )
            segments.extend(cut.strip() for cut in cuts if len(cut.strip()) > 10)
        return segments

    @staticmethod
    def _first_matching_sentence(sentences: list[str], keywords: list[str]) -> str | None:
        for keyword in keywords:
            for sentence in sentences:
                if MagnetismExtractor._is_navigation_noise(sentence):
                    continue
                low = sentence.lower()
                if MagnetismExtractor._contains_keyword(low, keyword):
                    return MagnetismExtractor._trim_evidence(sentence, keyword)
        return None

    @staticmethod
    def _heuristic_finding(layer: str, evidence: str) -> str:
        description = LAYER_DEFINITIONS[layer]["description"]
        return f"Detected {description}: {evidence[:180]}"

    @staticmethod
    def _tldr_content_from_layer(layer: dict[str, Any]) -> str | None:
        finding = MagnetismExtractor._clean_optional_string(layer.get("finding"))
        evidence = MagnetismExtractor._clean_optional_string(layer.get("evidence"))
        if finding and not finding.startswith("Detected "):
            return finding
        return evidence or finding

    @staticmethod
    def _contains_keyword(text: str, keyword: str) -> bool:
        escaped = re.escape(keyword.lower())
        if " " in keyword:
            return re.search(escaped, text, flags=re.IGNORECASE) is not None
        return re.search(rf"(?<![A-Za-zÀ-ÿ0-9]){escaped}(?![A-Za-zÀ-ÿ0-9])", text, flags=re.IGNORECASE) is not None

    @staticmethod
    def _trim_evidence(sentence: str, keyword: str, max_chars: int = 260) -> str:
        sentence = " ".join(sentence.split())
        if len(sentence) <= max_chars:
            return MagnetismExtractor._clean_evidence_phrase(sentence)
        match = re.search(re.escape(keyword), sentence, flags=re.IGNORECASE)
        if not match:
            return MagnetismExtractor._clean_evidence_phrase(sentence[:max_chars].rstrip())
        start = max(0, match.start() - 80)
        end = min(len(sentence), start + max_chars)
        trimmed = sentence[start:end].strip()
        if start > 0:
            trimmed = f"...{trimmed}"
        if end < len(sentence):
            trimmed = f"{trimmed}..."
        return MagnetismExtractor._clean_evidence_phrase(trimmed)

    @staticmethod
    def _clean_evidence_phrase(value: str) -> str:
        cleaned = " ".join(value.split()).strip(" -•*	")
        for marker in (" Contáctanos", " Contacto", " Nuestras soluciones", " Main Menu"):
            idx = cleaned.find(marker)
            if idx > 40:
                cleaned = cleaned[:idx].strip()
        return cleaned

    @staticmethod
    def _is_navigation_noise(value: str) -> bool:
        low = value.lower().strip()
        if low.startswith("main menu"):
            return True
        nav_tokens = ("contacto", "contáctanos", "menu", "menú", "alternar menú")
        return len(value) < 120 and sum(1 for token in nav_tokens if token in low) >= 2

    @staticmethod
    def _normalize_evidence(value: Any) -> str | None:
        if isinstance(value, list):
            for item in value:
                cleaned = MagnetismExtractor._clean_optional_string(item)
                if cleaned:
                    return cleaned
            return None
        return MagnetismExtractor._clean_optional_string(value)

    @staticmethod
    def _clean_optional_string(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned or cleaned.lower() in {"none", "null", "no clear signal detected in the provided sources."}:
            return None
        return cleaned

    @staticmethod
    def _extract_three_terms(text: str, key: str) -> list[str] | None:
        preferred = {
            "attributes": [
                "regenerativo",
                "circular",
                "sostenible",
                "medio ambiente",
                "mediterráneo",
                "funcional",
                "transparente",
                "trust",
                "security",
                "seguro",
                "real-time control",
                "centralised",
                "centralized",
                "performance",
                "innovative",
                "athletic",
                "action-oriented",
                "developer-first",
                "secure",
                "pragmatic",
                "ai-native",
                "practical",
                "editorial",
                "experimental",
            ],
            "values": [
                "regenerativo",
                "circular",
                "sostenibilidad",
                "medio ambiente",
                "transparencia",
                "claridad",
                "confianza",
                "trust",
                "security",
                "inspiration",
                "inspiración",
                "inclusivity",
                "innovation",
                "innovación",
                "fairness",
                "transparency",
                "customer empathy",
                "developer empathy",
            ],
        }
        found: list[str] = []
        low = text.lower()
        if key == "attributes":
            if any(term in low for term in ("maratón", "maraton", "athlete", "athletes", "atletas")):
                found.extend(["performance", "athletic"])
            if any(term in low for term in ("devs", "developers", "builders", "ship", "deploy", "run any code")):
                found.append("developer-first")
            if any(term in low for term in ("security", "secure", "sandboxes", "isolated", "isolation", "private networking", "encryption", "untrusted code")):
                found.append("secure")
            if any(term in low for term in ("pay only", "actual usage", "based on usage", "down to the second", "waive", "refund", "unintended charges")):
                found.append("pragmatic")
            if any(term in low for term in ("custom agents", "ai agents", "artificial intelligence", "edge of ai")):
                found.extend(["ai-native", "practical"])
            if any(term in low for term in ("newsletter", "write for you", "media company", "question")):
                found.append("editorial")
            if any(term in low for term in ("incubate", "foundry", "experiment", "what comes next")):
                found.append("experimental")
            if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
                found.append("innovative")
        if key == "values":
            if any(term in low for term in ("inspirar", "inspire", "inspiration")):
                found.append("inspiration")
            if any(term in low for term in ("todo tipo de atletas", "all types of athletes")):
                found.append("inclusivity")
            if any(term in low for term in ("waive", "refund", "unintended charges", "unexpected", "weird on your bill")):
                found.append("fairness")
            if any(term in low for term in ("based on usage", "pay only", "actual cpu", "actual usage", "billing", "down to the second")):
                found.append("transparency")
            if any(term in low for term in ("tell us", "we would love to work with you", "we have engineers", "support customers", "devs", "developers")):
                found.append("developer empathy")
            if any(term in low for term in ("innovadores", "innovative", "innovación", "innovation")):
                found.append("innovation")
        found = list(dict.fromkeys(found))
        if len(found) >= 3:
            return found[:3]
        for term in preferred.get(key, []):
            if term in low and term not in found:
                found.append(term)
            if len(found) == 3:
                return found

        if key in {"attributes", "values"}:
            return found[:3] if found else None

        candidates = re.split(r"[,;/]| and | y ", text)
        terms: list[str] = []
        for candidate in candidates:
            cleaned = re.sub(r"[^A-Za-zÀ-ÿ0-9 -]", "", candidate).strip().lower()
            words = [w for w in cleaned.split() if len(w) > 2]
            if not words:
                continue
            term = words[-1]
            if term not in terms:
                terms.append(term)
            if len(terms) == 3:
                break
        if len(terms) < 3 and key == "attributes":
            terms.extend([term for term in ["specific", "observable", "grounded"] if term not in terms])
        if len(terms) < 3 and key == "values":
            terms.extend([term for term in ["clarity", "proof", "consistency"] if term not in terms])
        return terms[:3] if terms else None

    @staticmethod
    def _magnetism_phrase_breakdown(text: str) -> dict[str, int]:
        if not text:
            return {
                "originality": 0,
                "specificity": 0,
                "memorability": 0,
                "verifiable_promise": 0,
            }

        words = re.findall(r"[A-Za-z0-9]+", text.lower())
        word_count = len(words)
        generic_hits = sum(1 for word in words if word in GENERIC_MAGNETISM_TERMS)
        specific_hits = sum(1 for word in words if word in SPECIFICITY_TERMS)
        has_number = bool(re.search(r"\d", text))
        has_action = bool(re.search(r"\b(build|do|earn|save|ship|reduce|automate|protect|find|create|launch|inspire)\b", text.lower()))
        is_short_imperative = 2 <= word_count <= 4 and has_action

        originality = 92 if is_short_imperative else 85 - (generic_hits * 14)
        specificity = 35 + min(specific_hits * 18, 55) + (10 if has_number else 0)
        if is_short_imperative:
            specificity = max(specificity, 62)
        memorability = 95 if is_short_imperative else 80 if 2 <= word_count <= 8 else 58 if word_count <= 14 else 35
        verifiable = 45 + (25 if has_action else 0) + (20 if has_number or specific_hits >= 2 else 0)
        if is_short_imperative:
            verifiable = max(verifiable, 75)
        return {
            "originality": MagnetismExtractor._clamp(originality),
            "specificity": MagnetismExtractor._clamp(specificity),
            "memorability": MagnetismExtractor._clamp(memorability),
            "verifiable_promise": MagnetismExtractor._clamp(verifiable),
        }

    @staticmethod
    def _semantic_alignment_score(layers: dict[str, Any]) -> int:
        pairs = [
            ("mindspace", "gamespace"),
            ("aetherspace", "tactispace"),
            ("netspace", "ambientspace"),
        ]
        scores = []
        for left, right in pairs:
            left_detected = layers[left]["detected"]
            right_detected = layers[right]["detected"]
            if left_detected and right_detected:
                scores.append(85)
            elif left_detected or right_detected:
                scores.append(45)
            else:
                scores.append(55)

        envispace_bonus = 10 if layers["envispace"]["detected"] else -10
        return MagnetismExtractor._clamp(round(sum(scores) / len(scores)) + envispace_bonus)

    @staticmethod
    def _absence_of_contradiction_score(tldr: dict[str, Any]) -> int:
        values_text = " ".join(
            str(block.get("content") or "") for block in tldr.values() if block.get("content")
        ).lower()
        contradiction_pairs = [
            ("playful", "institutional"),
            ("rebel", "compliance"),
            ("simple", "configurable"),
            ("premium", "cheap"),
        ]
        penalties = sum(1 for a, b in contradiction_pairs if a in values_text and b in values_text)
        return MagnetismExtractor._clamp(92 - penalties * 18)

    @staticmethod
    def _weighted_score(scores: dict[str, int], weights: dict[str, float]) -> int:
        return round(sum(scores[key] * weight for key, weight in weights.items()))

    @staticmethod
    def _quadrant(magnetism_score: int, coherence_score: int) -> str:
        high_magnetism = magnetism_score >= 70
        high_coherence = coherence_score >= 70
        if high_magnetism and high_coherence:
            return "Premium brand · no necesita ayuda"
        if high_magnetism and not high_coherence:
            return "Eslogan sin estructura · peligrosa"
        if not high_magnetism and high_coherence:
            return "Bien pensada sin alma comercial"
        return "Marca sin escribir · target FLOC*"

    @staticmethod
    def _magnetism_tier(score: int) -> str:
        if score >= 85:
            return "Magnetic"
        if score >= 70:
            return "Memorable"
        return "Forgettable"

    @staticmethod
    def _coherence_tier(score: int) -> str:
        if score >= 80:
            return "Aligned"
        if score >= 50:
            return "Functional"
        return "Fragmented"

    @staticmethod
    def _legacy_value(block: dict[str, Any]) -> str:
        value = block.get("content")
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value or "(no detectado)")

    @staticmethod
    def _clamp(value: int | float) -> int:
        return max(0, min(100, int(round(value))))
