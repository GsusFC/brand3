"""Magenta Circle 7-Layer Reverse Engineering Extractor."""

from __future__ import annotations

import json
import re
from typing import Any

from src.features.llm_analyzer import LLMAnalyzer
from src.reports.canonical_evidence import build_canonical_brand_evidence


class ReverseEngineeringExtractor:
    """dissects a brand's digital presence across 7 specific layers (Magenta Circle framework)."""

    def __init__(self, llm: LLMAnalyzer | None = None):
        self.llm = llm

    def extract(
        self,
        web_markdown: str,
        mentions: list[str],
        visual_signature: dict[str, Any] | None = None,
        brand_name: str = "Unknown Brand",
    ) -> dict[str, Any]:
        """Perform 7-layer reverse engineering audit using LLM if available, otherwise heuristic fallback.

        Layers (Magenta Circle):
        1. Mindspace (Cognitive)
        2. Aetherspace (Relational/Spiritual)
        3. Gamespace (Behavioral)
        4. Envispace (Environment/Design)
        5. Netspace (Structural/Digital)
        6. Tactispace (Conversion)
        7. Ambientspace (Physical)
        """
        web_content = (web_markdown or "").strip()
        mentions_list = mentions or []
        signature = visual_signature or {}

        # 1. Try LLM path first
        if self.llm is not None and getattr(self.llm, "api_key", None):
            try:
                result = self._extract_via_llm(web_content, mentions_list, signature, brand_name)
                if result:
                    return result
            except Exception:
                # Silently fall through to heuristic path on LLM error/timeout
                pass

        # 2. Heuristic fallback path
        return self._extract_via_heuristic(web_content, mentions_list, signature, brand_name)

    def extract_from_audit_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Run Reverse Engineering from the shared Brand Audit evidence bundle."""
        canonical_evidence = build_canonical_brand_evidence(snapshot)
        result = self.extract(
            web_markdown=canonical_evidence.interpreter_text,
            mentions=canonical_evidence.public_mentions,
            visual_signature={"semantics": canonical_evidence.visual_semantics},
            brand_name=canonical_evidence.brand_name,
        )
        result["source"] = "brand_audit_snapshot"
        result["extraction_mode"] = "canonical_snapshot"
        result["canonical_evidence_source"] = "brand_audit_snapshot"
        result["source_run_id"] = canonical_evidence.run_id
        result["canonical_evidence_summary"] = canonical_evidence.to_summary()
        result["limitations"] = canonical_evidence.limitations
        return result

    def _extract_via_llm(
        self,
        web_content: str,
        mentions: list[str],
        visual_signature: dict[str, Any],
        brand_name: str,
    ) -> dict[str, Any] | None:
        """Call Gemini via LLMAnalyzer to extract the 7 layers."""
        # Clean inputs and limit size to avoid hitting context limits
        truncated_web = web_content[:6000]
        
        cleaned_mentions = []
        for i, m in enumerate(mentions[:8], start=1):
            cleaned_m = str(m)[:500].replace("\n", " ").strip()
            if cleaned_m:
                cleaned_mentions.append(f"[{i}] {cleaned_m}")
        mentions_block = "\n---\n".join(cleaned_mentions) if cleaned_mentions else "(no mentions available)"

        # Safe serialization of visual signature without base64 images
        sig_data = {}
        if isinstance(visual_signature, dict):
            for k, v in visual_signature.items():
                if k == "semantics" and isinstance(v, dict):
                    # Keep key vision semantics fields
                    sig_data["vision_semantics"] = v.get("data") or v.get("semantics")
                elif k not in {"screenshot_path", "raw_html", "rendered_html", "screenshot_payload"}:
                    sig_data[k] = v
        sig_block = json.dumps(sig_data, indent=2)

        system_prompt = (
            "You are a master brand strategist and reverse engineering expert specializing in the 'Magenta Circle' "
            "7-layer brand framework. Dissect a brand's digital presence across 7 specific layers using "
            "website copy, public mentions, and visual signature characteristics. "
            "You must be highly analytical and ground all findings in concrete evidence (literal text quotes or "
            "specific visual characteristics). If a layer has no clear signal, mark it as 'not_detected'. "
            "Return ONLY valid JSON."
        )

        user_prompt = f"""Perform a 7-layer Magenta Circle reverse engineering audit on the brand "{brand_name}".

Data Sources:
--- WEBSITE COPY ---
{truncated_web}

--- PUBLIC MENTIONS / REVIEWS ---
{mentions_block}

--- VISUAL SIGNATURE ---
{sig_block}

---

Audit the following 7 layers exactly:
1. mindspace: Cognitive layer. What mental model or category do they own? Do they use a unique owned vocabulary or proprietary technical concepts?
2. aetherspace: Relational/spiritual layer. Do they have a moral mission, intense brand devotion, or a founder mythology/origin story?
3. gamespace: Behavioral mechanics. Are there interactive elements, onboarding loops, micro-conversions, or gamification/reward structures?
4. envispace: Design environment. How consistent and polished is the design? What tokens/patterns are notable?
5. netspace: Structural/digital authority. Are there APIs, bot policies, developer-facing tools, sitemaps, or deep network integrations?
6. tactispace: Tactical conversion. Evaluate CTA clarity, price transparency, checkout friction, and conversion mechanics.
7. ambientspace: Physical/ambient touchpoints. Is there evidence of packaging, offline events, logistics, or physical-world manifestations?

Strict Rules:
- Under "evidence", provide only literal quotes from the website copy/mentions or exact visual attributes from the visual signature.
- If there is no clear signal or evidence for a layer, set "status" to "not_detected", "findings" to "No clear signal detected in the provided sources.", and "evidence" to []. Do NOT hallucinate.
- Return a JSON object with this exact shape:
{{
  "mindspace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": ["literal quote or visual attribute"]
  }},
  "aetherspace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": ["literal quote or visual attribute"]
  }},
  "gamespace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": []
  }},
  "envispace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": []
  }},
  "netspace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": []
  }},
  "tactispace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": []
  }},
  "ambientspace": {{
    "status": "detected" | "not_detected",
    "findings": "analysis...",
    "evidence": []
  }}
}}
"""
        parsed = self.llm._call_json(system_prompt, user_prompt)
        if not isinstance(parsed, dict) or not parsed:
            return None

        return self._normalize_layers(parsed, brand_name, fallback_used=False)

    def _extract_via_heuristic(
        self,
        web_content: str,
        mentions: list[str],
        visual_signature: dict[str, Any],
        brand_name: str,
    ) -> dict[str, Any]:
        """Perform heuristic matching to extract 7 layers when LLM is unavailable."""
        text_corpus = (web_content + "\n" + "\n".join(mentions)).lower()

        # Define heuristic matching rules
        layer_keywords = {
            "mindspace": ["framework", "architecture", "protocol", "paradigm", "engine", "proprietary", "patented", "methodology"],
            "aetherspace": ["mission", "vision", "our founder", "story", "we believe", "purpose", "values", "manifesto"],
            "gamespace": ["points", "gamif", "onboard", "reward", "interactive", "badge", "level", "step", "quest"],
            "envispace": ["design", "theme", "palette", "color", "font", "typography", "layout", "visual", "consistent"],
            "netspace": ["api", "developer", "documentation", "integration", "github", "crawler", "bot", "webhooks"],
            "tactispace": ["pricing", "buy", "checkout", "pricing plan", "subscribe", "cta", "get started", "demo"],
            "ambientspace": ["package", "shipping", "physical", "store", "event", "offline", "unboxing", "delivery"]
        }

        # Find sentences in the text to act as evidence
        sentences = re.split(r'[.!?\n]+', web_content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        parsed: dict[str, Any] = {}

        for layer, keywords in layer_keywords.items():
            matches = [kw for kw in keywords if kw in text_corpus]
            evidence = []
            
            # Find up to 2 sentences that contain any of the matching keywords
            if matches:
                for s in sentences:
                    s_low = s.lower()
                    if any(kw in s_low for kw in matches):
                        evidence.append(s)
                        if len(evidence) >= 2:
                            break

            # Check envispace specific details from visual signature
            if layer == "envispace" and visual_signature:
                visual_details = []
                semantics = visual_signature.get("semantics") or {}
                sem_data = semantics.get("data") if isinstance(semantics, dict) else None
                if isinstance(sem_data, dict):
                    style = sem_data.get("aesthetic_style")
                    mood = sem_data.get("visual_mood")
                    polish = sem_data.get("visual_polish_score")
                    if style and style != "not_detected":
                        visual_details.append(f"Aesthetic Style: {style}")
                    if mood and mood != "not_detected":
                        visual_details.append(f"Visual Mood: {mood}")
                    if polish is not None:
                        visual_details.append(f"Visual Polish Score: {polish}/10")
                if visual_details:
                    evidence.extend(visual_details)
                    matches.append("visual_signature")

            if matches:
                findings = (
                    f"Heuristic audit indicates signals for this layer. "
                    f"Detected brand markers related to: {', '.join(matches[:4])}."
                )
                parsed[layer] = {
                    "status": "detected",
                    "findings": findings,
                    "evidence": evidence
                }
            else:
                parsed[layer] = {
                    "status": "not_detected",
                    "findings": "No clear signal detected in the provided sources.",
                    "evidence": []
                }

        return self._normalize_layers(parsed, brand_name, fallback_used=True)

    def _normalize_layers(self, raw: dict[str, Any], brand_name: str, fallback_used: bool) -> dict[str, Any]:
        """Ensure all 7 layers match the exact contract and compute metadata."""
        layers = ["mindspace", "aetherspace", "gamespace", "envispace", "netspace", "tactispace", "ambientspace"]
        normalized: dict[str, Any] = {}
        detected_count = 0

        for layer in layers:
            raw_layer = raw.get(layer)
            if not isinstance(raw_layer, dict):
                # Put a default empty layer if missing
                raw_layer = {}

            status = str(raw_layer.get("status") or "not_detected").strip().lower()
            if status not in {"detected", "not_detected"}:
                status = "not_detected"

            findings = str(raw_layer.get("findings") or "").strip()
            if not findings:
                findings = "No clear signal detected in the provided sources." if status == "not_detected" else "Signal detected."

            raw_evidence = raw_layer.get("evidence")
            evidence = []
            if isinstance(raw_evidence, list):
                evidence = [str(ev).strip() for ev in raw_evidence if ev]

            if status == "detected":
                detected_count += 1

            normalized[layer] = {
                "status": status,
                "findings": findings,
                "evidence": evidence
            }

        return {
            "brand_name": brand_name,
            "layers_detected_count": detected_count,
            "fallback_used": fallback_used,
            "layers": normalized
        }
