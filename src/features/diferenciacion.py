"""Diferenciacion feature extractor."""

from __future__ import annotations

import re
from collections import Counter

from ..collectors.competitor_collector import CompetitorData
from ..collectors.context_collector import ContextData
from ..collectors.exa_collector import ExaData
from ..collectors.web_collector import WebData
from ..models.brand import FeatureValue
from .authenticity import AI_PHRASES, AI_STRUCTURAL_PATTERNS, AuthenticityAnalyzer
from .llm_analyzer import LLMAnalyzer, llm_failure_reason


GENERIC_FALLBACK_PHRASES = [
    "cutting edge",
    "cutting-edge",
    "seamless",
    "revolutionary",
    "game changer",
    "best in class",
    "world class",
    "world-class",
    "innovative solutions",
    "leading provider",
    "save time",
    "save money",
    "better results",
    "improve efficiency",
    "boost productivity",
    "unlock potential",
    "we help businesses grow",
    "transform",
]

POSITIONING_SIGNALS = [
    "we are",
    "we're",
    "built for",
    "designed for",
    "made for",
    "for teams",
    "for developers",
    "for enterprise",
    "for structured data",
    "the only",
]

PERSONALITY_SIGNALS = {
    "humor": ["joke", "funny", "lol", "haha", "quirky", "weird"],
    "opinionated": ["we believe", "we think", "our take", "the truth is", "we don't"],
    "specific_voice": ["we call it", "our philosophy", "our bet", "our way"],
    "casual": ["hey", "yo", "gonna", "wanna", "tbh", "ngl"],
    "references": ["think of it as", "imagine", "remember when", "you know that feeling"],
}

CORPORATE_SIGNALS = [
    "we are committed to",
    "our mission is to",
    "we strive to",
    "exceed expectations",
    "best-in-class",
    "world-class",
    "we pride ourselves",
    "customer-centric",
    "data-driven",
    "innovative solutions",
    "proven track record",
]

POSITIONING_VERDICTS = {"clear", "diffuse", "generic", "unclear"}
UNIQUENESS_VERDICTS = {
    "highly_unique",
    "moderately_unique",
    "derivative",
    "generic",
    "unclear",
}

POSITIONING_VERDICT_SCORES = {
    "clear": 85.0,
    "diffuse": 55.0,
    "generic": 25.0,
    "unclear": 50.0,
}

UNIQUENESS_VERDICT_SCORES = {
    "highly_unique": 90.0,
    "moderately_unique": 65.0,
    "derivative": 40.0,
    "generic": 25.0,
    "unclear": 50.0,
}


class DiferenciacionExtractor:
    """Extract diferenciacion features."""

    def __init__(self, llm: LLMAnalyzer = None):
        self.llm = llm

    def extract(
        self,
        web: WebData = None,
        exa: ExaData = None,
        competitor_webs: list[WebData] = None,
        competitor_data: CompetitorData = None,
        screenshot_url: str = None,
        context: ContextData = None,
    ) -> dict[str, FeatureValue]:
        return {
            "positioning_clarity": self._positioning_clarity(web, competitor_data),
            "uniqueness": self._uniqueness(web, competitor_data),
            "competitor_distance": self._competitor_distance(
                web, exa, competitor_webs, competitor_data
            ),
            "content_authenticity": self._content_authenticity(web, exa, screenshot_url),
            "brand_personality": self._brand_personality(web, exa, screenshot_url),
            "content_depth_signal": self._content_depth_signal(context),
        }

    def _content_depth_signal(self, context: ContextData = None) -> FeatureValue:
        if not context:
            return FeatureValue("content_depth_signal", 0.0, raw_value={"reason": "no_context_scan"}, confidence=0.0, source="context")
        depth_pages = [
            name for name in ("blog", "docs", "faq", "case_studies", "changelog")
            if context.key_pages.get(name)
        ]
        score = min(100.0, 35.0 + len(depth_pages) * 10.0 + (10.0 if context.avg_words >= 500 else 0.0))
        return FeatureValue(
            "content_depth_signal",
            score,
            raw_value={
                "depth_pages": depth_pages,
                "avg_words": context.avg_words,
                "missing_signals": [
                    name for name in ("blog", "docs", "faq", "case_studies", "changelog")
                    if not context.key_pages.get(name)
                ],
            },
            confidence=context.confidence,
            source="context",
        )

    @staticmethod
    def _content(web: WebData = None) -> str:
        return (web.markdown_content or "") if web and not web.error else ""

    @staticmethod
    def _brand_name(web: WebData = None) -> str:
        if not web:
            return "Unknown"
        return web.title or web.url or "Unknown"

    @staticmethod
    def _sentence_count(content: str) -> int:
        chunks = re.split(r"[.!?\n]+", content)
        substantial = [chunk for chunk in chunks if len(chunk.split()) >= 3]
        return max(len(substantial), 1)

    @staticmethod
    def _reconcile_verdict_score(
        raw_score: float,
        verdict: str,
        mapping: dict[str, float],
    ) -> float:
        target = mapping[verdict]
        # LLM verdicts are semantically more stable than the scalar the model emits.
        # Preserve reasonable scores, but neutralise `unclear` and correct
        # pathological low values like clear→8 or unclear→0.
        if verdict == "unclear":
            return target
        if raw_score <= 10:
            return target
        if target >= 50 and raw_score < 25:
            return target
        return raw_score

    @staticmethod
    def _tokenize_terms(text: str) -> list[str]:
        return re.findall(r"\b[a-z]{4,}\b", text.lower())

    @staticmethod
    def _top_terms(text: str, limit: int = 10) -> list[str]:
        stopwords = {
            "this", "that", "with", "from", "your", "their", "have", "will", "into",
            "built", "teams", "enterprise", "developers", "platform", "product",
            "company", "brand", "help", "helps", "using", "data", "more",
        }
        counts = Counter(
            term for term in DiferenciacionExtractor._tokenize_terms(text)
            if term not in stopwords
        )
        return [term for term, _ in counts.most_common(limit)]

    @staticmethod
    def _clean_positioning_evidence(items) -> list[dict]:
        cleaned = []
        if not isinstance(items, list):
            return cleaned
        for item in items:
            if not isinstance(item, dict):
                continue
            quote = item.get("quote")
            signal = item.get("signal")
            if not isinstance(quote, str) or not quote.strip():
                continue
            if signal not in {"clear", "generic", "aspirational"}:
                continue
            cleaned.append({"quote": quote.strip(), "signal": signal})
        return cleaned

    @staticmethod
    def _clean_string_list(items, limit: int = 20) -> list[str]:
        """Keep only non-empty strings from an LLM-returned list. Malformed → dropped."""
        if not isinstance(items, list):
            return []
        out: list[str] = []
        for item in items:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            if len(out) >= limit:
                break
        return out

    def _positioning_fallback(self, web: WebData = None, reason: str = "llm_unavailable") -> FeatureValue:
        content = self._content(web).lower()
        if not content:
            return FeatureValue(
                "positioning_clarity",
                50.0,
                raw_value={"reason": reason, "signals_detected": []},
                confidence=0.4,
                source="heuristic_fallback",
            )

        signals = [signal for signal in POSITIONING_SIGNALS if signal in content]
        score = min(25.0 + (len(signals) * 12), 85.0)
        return FeatureValue(
            "positioning_clarity",
            score,
            raw_value={"reason": reason, "signals_detected": signals},
            confidence=0.4,
            source="heuristic_fallback",
        )

    def _positioning_clarity(
        self, web: WebData = None, competitor_data: CompetitorData = None
    ) -> FeatureValue:
        content = self._content(web)
        if not content:
            return self._positioning_fallback(web, reason="llm_unavailable")

        if not self.llm:
            return self._positioning_fallback(web, reason="llm_unavailable")

        competitor_snippets = []
        if competitor_data:
            for competitor in competitor_data.competitors[:3]:
                snippet = ""
                if competitor.web_data and competitor.web_data.markdown_content:
                    snippet = competitor.web_data.markdown_content[:400]
                if snippet:
                    competitor_snippets.append(
                        f"{competitor.name}: {snippet}"
                    )
        result = self.llm.analyze_positioning_clarity(
            content,
            self._brand_name(web),
            competitor_snippets,
        )
        verdict = result.get("verdict")
        if verdict not in POSITIONING_VERDICTS:
            return self._positioning_fallback(
                web,
                reason=llm_failure_reason(self.llm, "llm_invalid_verdict"),
            )

        confidence = 0.5 if verdict == "unclear" else 0.85
        cleaned_evidence = self._clean_positioning_evidence(result.get("evidence"))
        raw_value = {
            "verdict": verdict,
            "stated_position": result.get("stated_position") or "",
            "target_audience": result.get("target_audience") or "",
            "differentiator_claimed": result.get("differentiator_claimed") or "",
            "evidence": cleaned_evidence[:3],
            "reasoning": result.get("reasoning") or "",
        }
        if not cleaned_evidence:
            confidence = min(confidence, 0.5)
            raw_value["reason"] = "llm_partial_evidence"

        score = result.get("clarity_score")
        if not isinstance(score, (int, float)):
            return self._positioning_fallback(web, reason="llm_invalid_score")

        score = self._reconcile_verdict_score(
            max(0.0, min(float(score), 100.0)),
            verdict,
            POSITIONING_VERDICT_SCORES,
        )

        return FeatureValue(
            "positioning_clarity",
            score,
            raw_value=raw_value,
            confidence=confidence,
            source="llm",
        )

    def _uniqueness_fallback(self, web: WebData = None, reason: str = "llm_unavailable") -> FeatureValue:
        content = self._content(web).lower()
        sentence_count = self._sentence_count(content)
        generic_hits = [phrase for phrase in GENERIC_FALLBACK_PHRASES if phrase in content]
        ratio = len(generic_hits) / sentence_count if sentence_count else 0.0
        score = max(0.0, min(100.0 - (ratio * 60.0), 100.0))
        return FeatureValue(
            "uniqueness",
            score,
            raw_value={
                "reason": reason,
                "ratio": round(ratio, 3),
                "generic_hits": generic_hits,
                "sentence_count": sentence_count,
            },
            confidence=0.4,
            source="heuristic_fallback",
        )

    def _uniqueness(
        self, web: WebData = None, competitor_data: CompetitorData = None
    ) -> FeatureValue:
        content = self._content(web)
        if not content:
            return self._uniqueness_fallback(web, reason="llm_unavailable")
        if not self.llm:
            return self._uniqueness_fallback(web, reason="llm_unavailable")

        competitor_snippets = []
        if competitor_data:
            for competitor in competitor_data.competitors[:3]:
                snippet = ""
                if competitor.web_data and competitor.web_data.markdown_content:
                    snippet = competitor.web_data.markdown_content[:300]
                if snippet:
                    competitor_snippets.append(f"{competitor.name}: {snippet}")
        result = self.llm.analyze_uniqueness(
            content,
            self._brand_name(web),
            competitor_snippets,
        )
        verdict = result.get("verdict")
        if verdict not in UNIQUENESS_VERDICTS:
            return self._uniqueness_fallback(
                web,
                reason=llm_failure_reason(self.llm, "llm_invalid_verdict"),
            )

        score = result.get("uniqueness_score")
        if not isinstance(score, (int, float)):
            return self._uniqueness_fallback(web, reason="llm_invalid_score")

        unique_phrases = self._clean_string_list(result.get("unique_phrases"))
        generic_phrases = self._clean_string_list(result.get("generic_phrases"))
        brand_vocabulary = self._clean_string_list(result.get("brand_vocabulary"))
        competitor_overlap = self._clean_string_list(result.get("competitor_overlap_signals"))

        raw_value: dict = {
            "verdict": verdict,
            "unique_phrases": unique_phrases,
            "generic_phrases": generic_phrases,
            "brand_vocabulary": brand_vocabulary,
            "competitor_overlap_signals": competitor_overlap,
            "reasoning": result.get("reasoning") or "",
        }

        # verdict="unclear" degrades on its own. For other verdicts, if all four
        # evidence lists are empty the LLM gave no citable evidence; degrade.
        confidence = 0.5 if verdict == "unclear" else 0.85
        has_evidence = any((unique_phrases, generic_phrases, brand_vocabulary, competitor_overlap))
        if not has_evidence and verdict != "unclear":
            confidence = 0.5
            raw_value["reason"] = "llm_partial_evidence"

        score = self._reconcile_verdict_score(
            max(0.0, min(float(score), 100.0)),
            verdict,
            UNIQUENESS_VERDICT_SCORES,
        )

        return FeatureValue(
            "uniqueness",
            score,
            raw_value=raw_value,
            confidence=confidence,
            source="llm",
        )

    def _competitor_distance(
        self,
        web: WebData = None,
        exa: ExaData = None,
        competitor_webs: list[WebData] = None,
        competitor_data: CompetitorData = None,
    ) -> FeatureValue:
        content = self._content(web)
        if competitor_data and competitor_data.comparisons:
            comparisons = competitor_data.comparisons
            avg_distance = competitor_data.avg_distance
            closest = min(comparisons, key=lambda item: item.overall_distance)
            farthest = max(comparisons, key=lambda item: item.overall_distance)
            brand_unique_terms = []
            for comparison in comparisons:
                brand_unique_terms.extend(comparison.brand_unique_terms[:5])
            raw_value = {
                "avg_distance": round(avg_distance, 3),
                "closest_competitor": {
                    "name": closest.competitor_name,
                    "distance": round(closest.overall_distance, 3),
                },
                "most_different": {
                    "name": farthest.competitor_name,
                    "distance": round(farthest.overall_distance, 3),
                },
                "competitors_analyzed": len(comparisons),
                "brand_unique_terms": list(dict.fromkeys(brand_unique_terms))[:10],
                "similarity_threshold_crossed": avg_distance < 0.3,
            }
            return FeatureValue(
                "competitor_distance",
                round(avg_distance * 100.0, 1),
                raw_value=raw_value,
                confidence=0.8,
                source="competitor_web_comparison",
            )

        terms = self._top_terms(content, limit=10)
        return FeatureValue(
            "competitor_distance",
            50.0,
            raw_value={
                "avg_distance": 0.5,
                "closest_competitor": None,
                "most_different": None,
                "competitors_analyzed": 0,
                "brand_unique_terms": terms,
                "similarity_threshold_crossed": False,
            },
            confidence=0.3,
            source="heuristic_fallback",
        )

    def _auth_result(
        self, web: WebData = None, exa: ExaData = None, screenshot_url: str = None
    ):
        analyzer = AuthenticityAnalyzer()
        return analyzer.analyze(web, exa, screenshot_url)

    def _content_authenticity(
        self, web: WebData = None, exa: ExaData = None, screenshot_url: str = None
    ) -> FeatureValue:
        result = self._auth_result(web, exa, screenshot_url)
        content = self._content(web)
        text = content.lower()
        ai_pattern_hits = [phrase for phrase in AI_PHRASES if phrase in text][:5]
        structural_hits = [
            pattern for pattern in AI_STRUCTURAL_PATTERNS if re.search(pattern, text)
        ][:5]
        sentences = [s.strip() for s in re.split(r"[.!?]+", content) if len(s.strip()) > 20]
        uniformity_penalty = 0.0
        if len(sentences) > 5:
            lengths = [len(s.split()) for s in sentences[:30]]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((length - avg_len) ** 2 for length in lengths) / len(lengths)
            uniformity_penalty = round(max(0.0, (50 - variance) / 50) * 20, 2)

        verdict = "human"
        if result.content_authenticity < 45:
            verdict = "likely_ai"
        elif result.content_authenticity < 75:
            verdict = "mixed"

        raw_value = {
            "ai_pattern_hits": ai_pattern_hits,
            "structural_hits": structural_hits,
            "uniformity_penalty": uniformity_penalty,
            "authenticity_verdict": verdict,
            "evidence_snippets": (result.insights or [])[:3],
        }
        return FeatureValue(
            "content_authenticity",
            result.content_authenticity,
            raw_value=raw_value,
            confidence=result.confidence,
            source="content_analysis",
        )

    def _brand_personality(
        self, web: WebData = None, exa: ExaData = None, screenshot_url: str = None
    ) -> FeatureValue:
        result = self._auth_result(web, exa, screenshot_url)
        text = self._content(web).lower()
        signals_detected = {
            name: any(signal in text for signal in signals)
            for name, signals in PERSONALITY_SIGNALS.items()
        }
        corporate_signals_count = sum(1 for signal in CORPORATE_SIGNALS if signal in text)
        verdict = "mild"
        if result.brand_personality >= 75:
            verdict = "strong"
        elif result.brand_personality < 40:
            verdict = "corporate_default" if corporate_signals_count else "absent"

        return FeatureValue(
            "brand_personality",
            result.brand_personality,
            raw_value={
                "personality_score": result.brand_personality,
                "signals_detected": signals_detected,
                "corporate_signals_count": corporate_signals_count,
                "verdict": verdict,
            },
            confidence=result.confidence,
            source="content_analysis",
        )
