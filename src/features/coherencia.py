"""
Coherencia feature extractor.

Measures whether messaging, visual identity and tone are CONSISTENT across
the brand's touchpoints.

Four features (weights set in src/dimensions.py):
    visual_consistency         — AI-vision judgement on design consistency
    messaging_consistency      — LLM verdict on self vs third-party narrative
    tone_consistency           — LLM verdict on tone match across surfaces
    cross_channel_coherence    — heuristic structural cross-linking signal

Unified single-file design: heuristic features + LLM features live together.
`CoherenciaExtractor` accepts an optional `llm`. If absent (or LLM fails /
returns malformed shape) the LLM-driven features fall back to heuristic.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ..models.brand import FeatureValue
from ..collectors.context_collector import ContextData
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .llm_analyzer import LLMAnalyzer, llm_failure_reason
from .visual_analyzer import VisualAnalyzer


_VALID_MESSAGING_VERDICTS = frozenset({"aligned", "partial_gap", "divergent", "unclear"})
_VALID_TONE_GAPS = frozenset({"none", "mild", "strong"})

_MESSAGING_VERDICT_SCORES = {
    "aligned": 80.0,
    "partial_gap": 55.0,
    "divergent": 30.0,
    "unclear": 50.0,
}

_TONE_GAP_SCORES = {
    "none": 80.0,
    "mild": 60.0,
    "strong": 30.0,
}

CATEGORY_SUFFIXES = (
    "platform", "tool", "service", "solution", "app", "software",
    "infrastructure", "model", "models", "system", "systems",
    "engine", "engines", "lab", "labs", "layer", "protocol",
)

CATEGORY_STOPWORDS = frozenset({
    "that", "this", "with", "from", "your", "their", "about",
    "have", "been", "will", "more", "also", "can", "each",
    "making", "using", "used", "built", "designed", "made",
    "real", "world", "better", "next", "infinite", "predictions",
    "prediction", "teams", "company", "companies",
})

_SOCIAL_HOSTS = {
    "twitter.com": "twitter",
    "x.com": "twitter",
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "youtube.com": "youtube",
    "tiktok.com": "tiktok",
    "github.com": "github",
}


def _clean_messaging_gaps(raw_gaps) -> tuple[list[dict], bool]:
    """Filter malformed gaps out of the LLM response.

    Each valid gap is a dict with string fields `self_says`, `third_party_says`,
    `source_url`. Malformed items are dropped silently. Returns (cleaned, dropped_any).
    """
    if not isinstance(raw_gaps, list):
        return [], True
    cleaned: list[dict] = []
    dropped_any = False
    for item in raw_gaps:
        if not isinstance(item, dict):
            dropped_any = True
            continue
        self_says = item.get("self_says")
        third_says = item.get("third_party_says")
        source_url = item.get("source_url")
        if not isinstance(self_says, str) or not isinstance(third_says, str):
            dropped_any = True
            continue
        if not isinstance(source_url, str):
            dropped_any = True
            continue
        cleaned.append({
            "self_says": self_says,
            "third_party_says": third_says,
            "source_url": source_url,
        })
    return cleaned, dropped_any


def _clean_tone_examples(raw_examples) -> tuple[list[dict], bool]:
    """Filter malformed tone examples. Returns (cleaned, dropped_any)."""
    if not isinstance(raw_examples, list):
        return [], raw_examples is not None
    cleaned = []
    dropped_any = False
    for item in raw_examples:
        if not isinstance(item, dict):
            dropped_any = True
            continue
        source = item.get("source")
        quote = item.get("quote")
        marker = item.get("tone_marker")
        if source not in {"web", "mention"}:
            dropped_any = True
            continue
        if not isinstance(quote, str) or not isinstance(marker, str):
            dropped_any = True
            continue
        cleaned.append({"source": source, "quote": quote, "tone_marker": marker})
    return cleaned, dropped_any


def _reconcile_llm_score(raw_score: float, label: str, mapping: dict[str, float]) -> float:
    target = mapping[label]
    if label == "unclear":
        return target
    if raw_score <= 10:
        return target
    if target >= 50 and raw_score < 25:
        return target
    return raw_score


def _extract_domains_from_web(web: WebData) -> set[str]:
    domains: set[str] = set()
    for candidate in (web.url, getattr(web, "canonical_url", "")):
        if not candidate:
            continue
        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        host = (parsed.netloc or parsed.path or "").lower().strip("/")
        if host.startswith("www."):
            host = host[4:]
        if host:
            domains.add(host)
    for domain in getattr(web, "alternate_domains", []) or []:
        normalized = (domain or "").lower().strip("/")
        if normalized.startswith("www."):
            normalized = normalized[4:]
        if normalized:
            domains.add(normalized)
    return domains


class CoherenciaExtractor:
    """Extract coherencia features."""

    def __init__(
        self,
        llm: LLMAnalyzer | None = None,
        visual_analyzer: VisualAnalyzer | None = None,
        skip_visual_analysis: bool = False,
    ):
        # REVIEW: llm es opcional; cuando falta, messaging_consistency y
        # tone_consistency caen en heurística. skip_visual_analysis fuerza
        # fallback para visual (modo benchmark).
        self.llm = llm
        self.visual_analyzer = visual_analyzer or VisualAnalyzer()
        self.skip_visual_analysis = skip_visual_analysis

    def extract(
        self,
        web: WebData = None,
        exa: ExaData = None,
        context: ContextData = None,
        screenshot_url: str | None = None,
    ) -> dict[str, FeatureValue]:
        features = {
            "visual_consistency": self._visual_consistency(web, screenshot_url=screenshot_url),
            "messaging_consistency": self._messaging_consistency(web, exa),
            "tone_consistency": self._tone_consistency(web, exa),
            "cross_channel_coherence": self._cross_channel_coherence(web, exa),
        }
        if context is not None:
            features["structured_identity"] = self._structured_identity(context)
        return features

    def _structured_identity(self, context: ContextData = None) -> FeatureValue:
        if not context:
            return FeatureValue("structured_identity", 0.0, raw_value={"reason": "no_context_scan"}, confidence=0.0, source="context")
        signals = []
        if "Organization" in context.schema_types:
            signals.append("organization_schema")
        if "Person" in context.schema_types:
            signals.append("person_schema")
        if context.key_pages.get("about"):
            signals.append("about_page")
        score = min(100.0, 30.0 + len(signals) * 20.0)
        return FeatureValue(
            "structured_identity",
            score,
            raw_value={"signals_detected": signals, "schema_types": context.schema_types, "key_pages": context.key_pages},
            confidence=context.confidence,
            source="context",
        )

    # ── visual_consistency ─────────────────────────────────────────────

    def _visual_consistency(self, web: WebData | None, screenshot_url: str | None = None) -> FeatureValue:
        if not web or web.error:
            return FeatureValue(
                "visual_consistency", 0.0,
                raw_value={
                    "reason": "no_web_data",
                    "has_screenshot": False,
                    "design_quality_score": None,
                    "colors_detected": [],
                    "typography_consistent": None,
                    "evidence_insights": [],
                },
                confidence=0.3, source="none",
            )

        brand_name = web.title or ""

        if self.skip_visual_analysis:
            score, signals = self._visual_heuristic(web)
            return FeatureValue(
                "visual_consistency", score,
                raw_value={
                    "reason": "visual_analysis_skipped",
                    "heuristic_score_used": True,
                    "heuristic_signals": signals,
                    "has_screenshot": False,
                    "design_quality_score": None,
                    "colors_detected": [],
                    "typography_consistent": None,
                    "evidence_insights": [],
                },
                confidence=0.25, source="web_scrape_heuristic",
            )

        if screenshot_url:
            metadata = {
                "title": web.title,
                "description": getattr(web, "meta_description", ""),
                "url": web.url,
            }
            result = self.visual_analyzer.analyze_screenshot(screenshot_url, brand_name, metadata)
        elif web.screenshot_path and web.screenshot_path.startswith("http"):
            result = self.visual_analyzer.analyze_screenshot(web.screenshot_path, brand_name)
        else:
            result = self.visual_analyzer.analyze_url(web.url, brand_name)

        if result.error:
            score, signals = self._visual_heuristic(web)
            return FeatureValue(
                "visual_consistency", score,
                raw_value={
                    "reason": "visual_analysis_error",
                    "error": str(result.error)[:120],
                    "heuristic_score_used": True,
                    "heuristic_signals": signals,
                    "has_screenshot": False,
                    "design_quality_score": None,
                    "colors_detected": [],
                    "typography_consistent": None,
                    "evidence_insights": [],
                },
                confidence=0.3, source="web_scrape_heuristic",
            )

        details = result.details or {}
        colors = list(details.get("dominant_colors", []))[:6]
        style = details.get("style", "unknown")
        method = details.get("method", "unknown")
        typography_consistent = details.get("typography_consistent")
        insights = list(details.get("insights", []) or [])[:3]

        return FeatureValue(
            "visual_consistency", float(result.overall_score),
            raw_value={
                "has_screenshot": True,
                "design_quality_score": float(result.overall_score),
                "logo_detected": bool(getattr(result, "logo_detected", False)),
                "colors_detected": colors,
                "style": style,
                "method": method,
                "typography_consistent": typography_consistent,
                "evidence_insights": insights,
            },
            confidence=result.confidence, source="visual_analysis",
        )

    @staticmethod
    def _visual_heuristic(web: WebData) -> tuple[float, list[str]]:
        content = (web.markdown_content or "").lower()
        signals: list[str] = []
        score = 40.0
        if web.title and len(web.title) > 0:
            score += 20
            signals.append("brand_in_header")
        if any(s in content for s in ("style guide", "brand guidelines", "logo")):
            score += 10
            signals.append("style_mentions")
        return min(score, 100.0), signals

    # ── messaging_consistency (LLM-first) ──────────────────────────────

    def _messaging_consistency(
        self, web: WebData | None, exa: ExaData | None,
    ) -> FeatureValue:
        if not web:
            return FeatureValue(
                "messaging_consistency", 0.0,
                raw_value={"reason": "no_web_data"},
                confidence=0.3, source="none",
            )

        # Try LLM path first when available.
        if self.llm is not None and getattr(self.llm, "api_key", None):
            mentions = self._exa_mentions_payload(exa, limit=8)
            try:
                result = self.llm.analyze_messaging_consistency(
                    web.markdown_content or "",
                    mentions,
                    exa.brand_name if exa else (web.title or "unknown"),
                )
            except Exception as exc:
                return self._messaging_heuristic(
                    web, exa,
                    reason="llm_error",
                    extra={"error": str(exc)[:200]},
                )

            if not isinstance(result, dict) or "consistency_score" not in result:
                return self._messaging_heuristic(
                    web, exa,
                    reason=llm_failure_reason(self.llm, "llm_invalid_response"),
                    extra={"got": type(result).__name__},
                )

            verdict = result.get("verdict", "unclear")
            if verdict not in _VALID_MESSAGING_VERDICTS:
                return self._messaging_heuristic(
                    web, exa,
                    reason="llm_invalid_verdict",
                    extra={"got": str(verdict)[:50]},
                )

            try:
                score = float(result.get("consistency_score", 50))
            except (TypeError, ValueError):
                return self._messaging_heuristic(
                    web, exa,
                    reason="llm_invalid_response",
                    extra={"got": type(result.get("consistency_score")).__name__},
                )
            score = max(0.0, min(score, 100.0))

            cleaned_gaps, _dropped_any = _clean_messaging_gaps(result.get("gaps"))

            had_mentions = bool(mentions)
            partial_evidence = had_mentions and not cleaned_gaps and verdict in {"partial_gap", "divergent"}
            confidence = 0.5 if (verdict == "unclear" or partial_evidence) else 0.85

            aligned_themes = result.get("aligned_themes") or []
            if isinstance(aligned_themes, list):
                aligned_themes = [t for t in aligned_themes if isinstance(t, str)][:6]
            else:
                aligned_themes = []

            raw_payload: dict = {
                "verdict": verdict,
                "self_category": (result.get("self_category") or "")[:200],
                "third_party_category": (result.get("third_party_category") or "")[:200],
                "aligned_themes": aligned_themes,
                "gaps": cleaned_gaps[:3],
                "reasoning": (result.get("reasoning") or "")[:500],
            }
            if partial_evidence:
                raw_payload["reason"] = "llm_partial_evidence"

            score = _reconcile_llm_score(score, verdict, _MESSAGING_VERDICT_SCORES)

            return FeatureValue(
                "messaging_consistency", score,
                raw_value=raw_payload,
                confidence=confidence, source="llm",
            )

        # No LLM → heuristic path.
        return self._messaging_heuristic(web, exa, reason="llm_unavailable")

    def _messaging_heuristic(
        self,
        web: WebData,
        exa: ExaData | None,
        reason: str,
        extra: dict | None = None,
    ) -> FeatureValue:
        category_signals = self._extract_category_signals(web)
        heuristic: dict = {"category_signals": category_signals[:5]}

        if not category_signals:
            raw = {"reason": reason, "heuristic_signals": heuristic,
                   "note": "no clear category positioning found"}
            if extra:
                raw.update(extra)
            return FeatureValue(
                "messaging_consistency", 35.0,
                raw_value=raw,
                confidence=0.4, source="heuristic_fallback",
            )

        if not exa or not exa.mentions:
            raw = {"reason": reason, "heuristic_signals": heuristic,
                   "note": "no third-party mentions available"}
            if extra:
                raw.update(extra)
            return FeatureValue(
                "messaging_consistency", 55.0,
                raw_value=raw,
                confidence=0.4, source="heuristic_fallback",
            )

        exa_text = " ".join(
            ((r.text or "") + " " + (r.title or "")).lower()[:500]
            for r in exa.mentions[:8]
        )
        matches = 0
        matched_signals: list[str] = []
        for signal in category_signals:
            key_words = self._signal_keywords(signal)
            if len(key_words) >= 2 and sum(1 for w in key_words if w in exa_text) >= 2:
                matches += 1
                matched_signals.append(signal)
            elif key_words and any(w in exa_text for w in key_words[:2]):
                matches += 1
                matched_signals.append(signal)

        ratio = matches / len(category_signals) if category_signals else 0.0
        score = min(40.0 + (ratio * 60.0), 100.0)
        heuristic.update({
            "matched_signals": matched_signals[:5],
            "match_ratio": round(ratio, 2),
        })
        raw = {"reason": reason, "heuristic_signals": heuristic}
        if extra:
            raw.update(extra)
        return FeatureValue(
            "messaging_consistency", score,
            raw_value=raw,
            confidence=0.4, source="heuristic_fallback",
        )

    # ── tone_consistency (LLM-first) ───────────────────────────────────

    def _tone_consistency(
        self, web: WebData | None, exa: ExaData | None,
    ) -> FeatureValue:
        if not web:
            return FeatureValue(
                "tone_consistency", 0.0,
                raw_value={"reason": "no_web_data"},
                confidence=0.3, source="none",
            )

        if self.llm is not None and getattr(self.llm, "api_key", None):
            snippets = self._exa_mentions_payload(exa, limit=5)
            try:
                result = self.llm.analyze_tone_consistency(
                    web.markdown_content or "",
                    snippets,
                    exa.brand_name if exa else (web.title or "unknown"),
                )
            except Exception as exc:
                return self._tone_heuristic(web, reason="llm_error",
                                            extra={"error": str(exc)[:200]})

            if not isinstance(result, dict) or "tone_consistency_score" not in result:
                return self._tone_heuristic(web, reason=llm_failure_reason(self.llm, "llm_invalid_response"),
                                            extra={"got": type(result).__name__})

            gap_signal = result.get("gap_signal", "none")
            if gap_signal not in _VALID_TONE_GAPS:
                return self._tone_heuristic(web, reason="llm_invalid_gap_signal",
                                            extra={"got": str(gap_signal)[:50]})

            try:
                score = float(result.get("tone_consistency_score", 55))
            except (TypeError, ValueError):
                return self._tone_heuristic(web, reason="llm_invalid_response",
                                            extra={"got": type(result.get("tone_consistency_score")).__name__})
            score = max(0.0, min(score, 100.0))

            cleaned, dropped_any = _clean_tone_examples(result.get("examples"))
            partial_evidence = bool(snippets) and (
                (not cleaned and (gap_signal != "none" or dropped_any))
                or (dropped_any and not cleaned)
            )
            confidence = 0.5 if (gap_signal == "none" and not snippets) or partial_evidence else 0.85

            raw_payload: dict = {
                "gap_signal": gap_signal,
                "self_tone": (result.get("self_tone") or "")[:200],
                "third_party_tone": (result.get("third_party_tone") or "")[:200],
                "examples": cleaned[:3],
                "reasoning": (result.get("reasoning") or "")[:500],
            }
            if partial_evidence:
                raw_payload["reason"] = "llm_partial_evidence"

            score = _reconcile_llm_score(score, gap_signal, _TONE_GAP_SCORES)

            return FeatureValue(
                "tone_consistency", score,
                raw_value=raw_payload,
                confidence=confidence, source="llm",
            )

        return self._tone_heuristic(web, reason="llm_unavailable")

    @staticmethod
    def _tone_heuristic(
        web: WebData, reason: str, extra: dict | None = None,
    ) -> FeatureValue:
        content = (web.markdown_content or "").lower()
        formal_signals = ("furthermore", "therefore", "consequently", "regarding",
                          "herein", "aforementioned", "pursuant")
        informal_signals = ("hey", "awesome", "cool", "gonna", "wanna",
                            "let's go", "!", "🔥", "💪")
        formal_count = sum(1 for s in formal_signals if s in content)
        informal_count = sum(1 for s in informal_signals if s in content)

        if formal_count > 3 and informal_count > 3:
            score = 35.0
        elif formal_count > 0 or informal_count > 0:
            score = 70.0
        else:
            score = 55.0

        raw = {
            "reason": reason,
            "heuristic_signals": {
                "formal_markers": formal_count,
                "informal_markers": informal_count,
            },
        }
        if extra:
            raw.update(extra)
        return FeatureValue(
            "tone_consistency", score,
            raw_value=raw,
            confidence=0.4, source="heuristic_fallback",
        )

    # ── cross_channel_coherence (heuristic) ────────────────────────────

    def _cross_channel_coherence(
        self, web: WebData | None, exa: ExaData | None,
    ) -> FeatureValue:
        if not web:
            return FeatureValue(
                "cross_channel_coherence", 0.0,
                raw_value={"reason": "no_web_data"},
                confidence=0.3, source="none",
            )

        content = (web.markdown_content or "").lower()
        brand_domains = _extract_domains_from_web(web)

        social_platforms = sorted({
            platform for host, platform in _SOCIAL_HOSTS.items() if host in content
        })
        has_social_links = bool(social_platforms)

        has_contact = any(s in content for s in (
            "contact", "email", "@", "phone", "address",
        ))
        has_touchpoint = any(s in content for s in (
            "request demo", "book a demo", "get in touch", "talk to sales",
            "join waitlist", "waitlist", "apply", "your request has been received",
            "we will be in touch", "secure your place", "sign up", "sign in",
            "log in", "get started", "join the movement", "support the movement",
            "become a member", "create your petition", "create movement",
            "create petition", "support this cause",
        ))
        has_owned_surface = any(s in content for s in (
            "/docs", " docs", "/blog", " blog", "/about", " about",
            "/careers", " careers", "/privacy", "privacy policy", "terms",
            "/manifest", "manifest", "/search", "search?q=",
        ))

        brand_url_mentioned = False
        if exa and exa.mentions:
            for r in exa.mentions:
                url = (r.url or "").lower()
                if any(domain in url for domain in brand_domains):
                    brand_url_mentioned = True
                    break

        score = 20.0 if web.title else 10.0
        if has_social_links:
            score += 25
        if has_contact:
            score += 20
        if has_touchpoint:
            score += 20
        if has_owned_surface:
            score += 10
        if brand_url_mentioned:
            score += 15

        return FeatureValue(
            "cross_channel_coherence", min(score, 100.0),
            raw_value={
                "has_social_links": has_social_links,
                "has_contact": has_contact,
                "has_touchpoint": has_touchpoint,
                "has_owned_surface": has_owned_surface,
                "brand_url_mentioned_in_exa": brand_url_mentioned,
                "brand_domains": sorted(brand_domains),
                "social_platforms_detected": social_platforms,
            },
            confidence=0.7, source="web_scrape+exa",
        )

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _exa_mentions_payload(exa: ExaData | None, limit: int) -> list[dict]:
        if not exa or not exa.mentions:
            return []
        payload: list[dict] = []
        for r in exa.mentions[:limit]:
            payload.append({
                "url": r.url or "",
                "title": r.title or "",
                "text": (r.text or "") or (r.summary or ""),
            })
        return payload

    def _extract_category_signals(self, web: WebData) -> list[str]:
        signals: list[str] = []
        hero_lines: list[str] = []
        for line in (web.markdown_content or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("!["):
                continue
            if stripped.startswith("[") and "](" in stripped:
                continue
            if len(stripped) < 8:
                continue
            hero_lines.append(stripped.lower())
            if len(hero_lines) >= 12:
                break

        descriptive_lines: list[str] = []
        for idx, line in enumerate(hero_lines):
            if idx == 0 and len(hero_lines) > 1:
                continue
            descriptive_lines.append(line)
        candidate_text = " ".join(descriptive_lines[:5])

        patterns = [
            rf'([a-z][\w-]*(?:\s+[a-z][\w-]*){{0,5}})\s+(?:{"|".join(CATEGORY_SUFFIXES)})\s+for\b',
            rf'(?:pre-trained|open-source|enterprise-grade|deterministic|frontier)?\s*([a-z][\w-]*(?:\s+[a-z][\w-]*){{0,5}})\s+(?:{"|".join(CATEGORY_SUFFIXES)})\b',
            r'([a-z][\w-]*(?:\s+[a-z][\w-]*){0,6})\s+for\s+[a-z][\w-]*(?:\s+[a-z][\w-]*){0,6}',
        ]
        for pattern in patterns:
            signals.extend(match.strip()[:60] for match in re.findall(pattern, candidate_text))

        for line in hero_lines:
            if any(suffix in line for suffix in CATEGORY_SUFFIXES):
                signals.append(line[:80])

        deduped: list[str] = []
        seen: set = set()
        for signal in signals:
            normalized = " ".join(signal.split())
            normalized = re.sub(r"^[^a-z]+", "", normalized)
            if not normalized:
                continue
            keyword_tuple = tuple(self._signal_keywords(normalized))
            if normalized in seen or keyword_tuple in seen:
                continue
            if not keyword_tuple:
                continue
            deduped.append(normalized)
            seen.add(normalized)
            seen.add(keyword_tuple)
        return deduped[:6]

    @staticmethod
    def _signal_keywords(signal: str) -> list[str]:
        words = re.findall(r"[a-z][a-z0-9-]+", signal.lower())
        keywords: list[str] = []
        for word in words:
            if len(word) <= 3:
                continue
            if word in CATEGORY_STOPWORDS:
                continue
            keywords.append(word)
        return keywords[:4]
