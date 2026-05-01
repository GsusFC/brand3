"""
Percepción feature extractor.

Measures how people talk about the brand.

Four features (weights set in src/dimensions.py):
    brand_sentiment   — LLM verdict on overall sentiment + controversy flag,
                        with literal quotes as evidence
    mention_volume    — heuristic, how much coverage exists
    sentiment_trend   — LLM (or heuristic fallback): is sentiment improving
                        or declining over time?
    review_quality    — heuristic, presence and nature of review platforms

Unified single-file design. LLM-first where it matters (sentiment, trend);
heuristic for purely structural signals (volume, review presence).
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

from ..models.brand import FeatureValue
from ..collectors.context_collector import ContextData
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .llm_analyzer import LLMAnalyzer, llm_failure_reason


_VALID_SENTIMENT_VERDICTS = frozenset({"positive", "mixed", "negative", "unclear"})
_VALID_SENTIMENT_SIGNALS = frozenset({"positive", "negative", "neutral"})
_CONTROVERSY_CAP = 35.0
_SENTIMENT_VERDICT_SCORES = {
    "positive": 80.0,
    "mixed": 55.0,
    "negative": 25.0,
    "unclear": 50.0,
}

POSITIVE_WORDS = frozenset({
    "excellent", "amazing", "outstanding", "great", "fantastic", "wonderful",
    "love", "best", "impressive", "innovative", "reliable", "trusted",
    "recommend", "quality", "exceptional", "superb", "brilliant",
    "perfect", "top", "leading", "popular", "successful", "growing",
    "award", "winner", "breakthrough", "powerful", "efficient",
})

NEGATIVE_WORDS = frozenset({
    "terrible", "awful", "worst", "horrible", "disappointing", "poor",
    "broken", "scam", "fraud", "complaint", "lawsuit", "controversy",
    "failed", "failure", "declining", "bankrupt", "layoff", "fired",
    "hack", "breach", "leak", "crash", "down", "outage", "bug",
    "overpriced", "expensive", "slow", "unreliable", "unresponsive",
    "toxic", "misleading", "deceptive", "ripoff", "rip off",
})

CONTROVERSY_PHRASES = (
    "filed a lawsuit", "class action", "facing lawsuit", "sued by",
    "under investigation", "federal investigation", "doj investigation",
    "fined by", "regulatory action", "sec charges",
    "data breach", "security breach", "privacy violation",
    "major scandal", "controversy surrounding", "backlash over",
    "accused of fraud", "allegations of", "charged with",
    "forced to lay off", "mass layoffs", "company collapse",
    "criminal charges", "indicted", "convicted of",
    "consumer complaints", "fda warning", "product recall",
)

_PROFESSIONAL_REVIEW_PLATFORMS = {
    "trustpilot.com", "g2.com", "capterra.com",
    "glassdoor.com", "producthunt.com",
}
_CONSUMER_REVIEW_PLATFORMS = {
    "yelp.com", "google.com/maps", "appstore", "play store", "reviews.io",
}
_ALL_REVIEW_PLATFORMS = _PROFESSIONAL_REVIEW_PLATFORMS | _CONSUMER_REVIEW_PLATFORMS


def _clean_sentiment_evidence(raw_evidence) -> tuple[list[dict], bool]:
    if not isinstance(raw_evidence, list):
        return [], raw_evidence is not None
    cleaned: list[dict] = []
    dropped_any = False
    for item in raw_evidence:
        if not isinstance(item, dict):
            dropped_any = True
            continue
        quote = item.get("quote")
        url = item.get("source_url")
        signal = item.get("signal")
        if not isinstance(quote, str) or not quote.strip():
            dropped_any = True
            continue
        if not isinstance(url, str):
            dropped_any = True
            continue
        if signal not in _VALID_SENTIMENT_SIGNALS:
            dropped_any = True
            continue
        cleaned.append({
            "quote": quote.strip(),
            "source_url": url,
            "signal": signal,
        })
    return cleaned, dropped_any


def _clean_string_list(items, limit: int = 10) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        if len(out) >= limit:
            break
    return out


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _reconcile_verdict_score(raw_score: float, verdict: str) -> float:
    target = _SENTIMENT_VERDICT_SCORES[verdict]
    if verdict == "unclear":
        return target
    if raw_score <= 10:
        return target
    if target >= 50 and raw_score < 25:
        return target
    return raw_score


def _parse_published_date(value: str) -> datetime | None:
    if not value or value == "None":
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate).replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    return None


def _mention_payload(results) -> list[dict]:
    out: list[dict] = []
    for r in results:
        text = (getattr(r, "text", "") or "") + " " + (getattr(r, "summary", "") or "")
        out.append({
            "url": getattr(r, "url", "") or "",
            "title": getattr(r, "title", "") or "",
            "text": text.strip(),
        })
    return out


class PercepcionExtractor:
    """Extract percepción features from third-party mentions and coverage."""

    def __init__(self, llm: LLMAnalyzer | None = None):
        # REVIEW: llm opcional. Sin LLM, brand_sentiment y sentiment_trend
        # caen en heurística normalizada por total de palabras.
        self.llm = llm

    def extract(self, web: WebData = None, exa: ExaData = None, context: ContextData = None) -> dict[str, FeatureValue]:
        features = {
            "brand_sentiment": self._brand_sentiment(exa),
            "mention_volume": self._mention_volume(exa),
            "sentiment_trend": self._sentiment_trend(exa),
            "review_quality": self._review_quality(exa),
        }
        if context is not None:
            features["review_surface"] = self._review_surface(context)
        return features

    def _review_surface(self, context: ContextData = None) -> FeatureValue:
        if not context:
            return FeatureValue("review_surface", 0.0, raw_value={"reason": "no_context_scan"}, confidence=0.0, source="context")
        has_review_schema = "Review" in context.schema_types or "AggregateRating" in context.schema_types
        has_reviews_page = bool(context.key_pages.get("reviews"))
        missing = []
        if not has_reviews_page:
            missing.append("reviews_page")
        if not has_review_schema:
            missing.append("review_schema")
        return FeatureValue(
            "review_surface",
            65.0 if (has_review_schema or has_reviews_page) else 35.0,
            raw_value={
                "reviews_page": has_reviews_page,
                "review_schema": has_review_schema,
                "missing_signals": missing,
            },
            confidence=context.confidence,
            source="context",
        )

    # ── brand_sentiment (LLM-first, absorbs controversy) ───────────────

    def _brand_sentiment(self, exa: ExaData | None) -> FeatureValue:
        if not exa or not exa.mentions:
            return FeatureValue(
                "brand_sentiment", 50.0,
                raw_value={"reason": "no_mentions"},
                confidence=0.3, source="none",
            )

        if self.llm is not None and getattr(self.llm, "api_key", None):
            mentions = _mention_payload(exa.mentions + exa.news)
            try:
                result = self.llm.analyze_brand_sentiment(
                    mentions, exa.brand_name or "",
                )
            except Exception as exc:
                return self._sentiment_heuristic(
                    exa, reason="llm_error", extra={"error": str(exc)[:200]},
                )

            if not isinstance(result, dict) or "sentiment_score" not in result:
                return self._sentiment_heuristic(
                    exa, reason=llm_failure_reason(self.llm, "llm_invalid_response"),
                    extra={"got": type(result).__name__},
                )

            verdict = result.get("verdict", "unclear")
            if verdict not in _VALID_SENTIMENT_VERDICTS:
                return self._sentiment_heuristic(
                    exa, reason="llm_invalid_verdict",
                    extra={"got": str(verdict)[:50]},
                )

            try:
                score = float(result.get("sentiment_score", 50))
            except (TypeError, ValueError):
                return self._sentiment_heuristic(
                    exa, reason="llm_invalid_response",
                    extra={"got": type(result.get("sentiment_score")).__name__},
                )
            score = max(0.0, min(score, 100.0))
            score = _reconcile_verdict_score(score, verdict)

            controversy_raw = result.get("controversy_detected")
            if isinstance(controversy_raw, bool):
                controversy = controversy_raw
                controversy_type_warning = None
            else:
                controversy = False
                controversy_type_warning = type(controversy_raw).__name__

            original_score = score
            if controversy:
                score = min(score, _CONTROVERSY_CAP)

            evidence, dropped_evidence = _clean_sentiment_evidence(result.get("evidence"))
            partial_evidence = bool(mentions) and (
                dropped_evidence or (not evidence and verdict != "unclear")
            )
            confidence = 0.5 if (verdict == "unclear" or partial_evidence) else 0.85

            raw_payload: dict = {
                "verdict": verdict,
                "overall_tone": (result.get("overall_tone") or "")[:300],
                "positive_themes": _clean_string_list(result.get("positive_themes")),
                "negative_themes": _clean_string_list(result.get("negative_themes")),
                "evidence": evidence[:4],
                "controversy_detected": controversy,
                "controversy_details": (result.get("controversy_details") or None) if controversy else None,
                "controversy_cap_applied": controversy and score < original_score,
                "reasoning": (result.get("reasoning") or "")[:500],
            }
            if raw_payload["controversy_cap_applied"]:
                raw_payload["capped_from_score"] = round(original_score, 1)
            if controversy_type_warning:
                raw_payload["controversy_detected_type_warning"] = controversy_type_warning
            if partial_evidence:
                raw_payload["reason"] = "llm_partial_evidence"

            return FeatureValue(
                "brand_sentiment", score,
                raw_value=raw_payload,
                confidence=confidence, source="llm",
            )

        return self._sentiment_heuristic(exa, reason="llm_unavailable")

    @staticmethod
    def _sentiment_heuristic(
        exa: ExaData,
        reason: str,
        extra: dict | None = None,
    ) -> FeatureValue:
        all_text = " ".join(
            ((r.text or "") + " " + (r.summary or "")).lower()
            for r in exa.mentions + exa.news
        )
        total_words = len(all_text.split()) or 1
        pos_count = sum(1 for w in POSITIVE_WORDS if w in all_text)
        neg_count = sum(1 for w in NEGATIVE_WORDS if w in all_text)

        pos_ratio = pos_count / total_words
        neg_ratio = neg_count / total_words
        net = pos_ratio - neg_ratio
        # Compressed to avoid runaway scores for long corpora with few markers.
        score = 50.0 + max(-50.0, min(50.0, net * 5000.0))
        score = max(0.0, min(score, 100.0))

        controversy_hits = [p for p in CONTROVERSY_PHRASES if p in all_text]
        if controversy_hits:
            score = min(score, _CONTROVERSY_CAP)

        raw = {
            "reason": reason,
            "pos_count": pos_count,
            "neg_count": neg_count,
            "total_words": total_words,
            "controversy_phrases_found": controversy_hits[:5],
            "fallback_score": round(score, 1),
        }
        if extra:
            raw.update(extra)
        return FeatureValue(
            "brand_sentiment", score,
            raw_value=raw,
            confidence=0.4, source="heuristic_fallback",
        )

    # ── mention_volume (heuristic) ─────────────────────────────────────

    @staticmethod
    def _mention_volume(exa: ExaData | None) -> FeatureValue:
        if not exa:
            return FeatureValue(
                "mention_volume", 10.0,
                raw_value={
                    "reason": "no_exa_data",
                    "total_mentions": 0,
                    "mentions_count": 0,
                    "news_count": 0,
                    "volume_tier": "none",
                    "top_domains": [],
                },
                confidence=0.4, source="none",
            )

        mentions_count = len(exa.mentions)
        news_count = len(exa.news)
        total = mentions_count + news_count

        if total >= 15:
            score = 95.0; tier = "very_high"
        elif total >= 10:
            score = 80.0; tier = "high"
        elif total >= 5:
            score = 60.0; tier = "moderate"
        elif total >= 3:
            score = 40.0; tier = "low"
        elif total >= 1:
            score = 25.0; tier = "minimal"
        else:
            score = 10.0; tier = "none"

        domain_counter: Counter = Counter()
        for r in exa.mentions + exa.news:
            domain = _extract_domain(getattr(r, "url", None))
            if domain:
                domain_counter[domain] += 1
        top_domains = [d for d, _ in domain_counter.most_common(3)]

        return FeatureValue(
            "mention_volume", score,
            raw_value={
                "total_mentions": total,
                "mentions_count": mentions_count,
                "news_count": news_count,
                "volume_tier": tier,
                "top_domains": top_domains,
            },
            confidence=0.7, source="exa",
        )

    # ── sentiment_trend (LLM-first if enough data, heuristic otherwise) ─

    def _sentiment_trend(self, exa: ExaData | None) -> FeatureValue:
        if not exa or not exa.mentions:
            return FeatureValue(
                "sentiment_trend", 50.0,
                raw_value={"reason": "no_mentions"},
                confidence=0.3, source="none",
            )

        dated: list[tuple[datetime, object]] = []
        for r in exa.mentions + exa.news:
            d = _parse_published_date(getattr(r, "published_date", "") or "")
            if d is not None:
                dated.append((d, r))

        if len(dated) < 4:
            return FeatureValue(
                "sentiment_trend", 50.0,
                raw_value={
                    "reason": "insufficient_dated_mentions",
                    "dated_count": len(dated),
                },
                confidence=0.1, source="exa",
            )

        dated.sort(key=lambda item: item[0])
        results = [r for _, r in dated]
        mid = len(results) // 2
        older, newer = results[:mid], results[mid:]

        # LLM path: reuse analyze_brand_sentiment on each half.
        if self.llm is not None and getattr(self.llm, "api_key", None):
            brand_name = getattr(exa, "brand_name", "") or ""
            try:
                older_result = self.llm.analyze_brand_sentiment(
                    _mention_payload(older), brand_name,
                )
                newer_result = self.llm.analyze_brand_sentiment(
                    _mention_payload(newer), brand_name,
                )
            except Exception as exc:
                return self._trend_heuristic(
                    older, newer, dated_count=len(dated),
                    reason="llm_error", extra={"error": str(exc)[:200]},
                )

            older_score = _safe_score(older_result)
            newer_score = _safe_score(newer_result)
            if older_score is None or newer_score is None:
                return self._trend_heuristic(
                    older, newer, dated_count=len(dated),
                    reason=llm_failure_reason(self.llm, "llm_invalid_response"),
                )

            delta = newer_score - older_score
            raw_score = max(0.0, min(50.0 + delta, 100.0))
            trend = (
                "improving" if delta > 5
                else "declining" if delta < -5
                else "stable"
            )
            trend_score = {
                "improving": 75.0,
                "stable": 55.0,
                "declining": 30.0,
            }[trend]
            score = trend_score if raw_score <= 10 else raw_score
            return FeatureValue(
                "sentiment_trend", score,
                raw_value={
                    "dated_count": len(dated),
                    "older_score": round(older_score, 1),
                    "newer_score": round(newer_score, 1),
                    "delta": round(delta, 1),
                    "trend": trend,
                    "method": "llm",
                },
                confidence=0.75, source="llm",
            )

        return self._trend_heuristic(older, newer, dated_count=len(dated),
                                     reason="llm_unavailable")

    @staticmethod
    def _trend_heuristic(
        older, newer, dated_count: int,
        reason: str, extra: dict | None = None,
    ) -> FeatureValue:
        def ratio(results) -> float:
            text = " ".join(((r.text or "") + " " + (r.summary or "")).lower() for r in results)
            words = len(text.split()) or 1
            pos = sum(1 for w in POSITIVE_WORDS if w in text)
            neg = sum(1 for w in NEGATIVE_WORDS if w in text)
            return ((pos - neg) / words) if words else 0.0

        older_ratio = ratio(older)
        newer_ratio = ratio(newer)
        delta_ratio = newer_ratio - older_ratio
        score = 50.0 + max(-50.0, min(50.0, delta_ratio * 5000.0))
        score = max(0.0, min(score, 100.0))
        trend = (
            "improving" if delta_ratio > 0.002
            else "declining" if delta_ratio < -0.002
            else "stable"
        )
        raw = {
            "reason": reason,
            "dated_count": dated_count,
            "older_ratio": round(older_ratio, 4),
            "newer_ratio": round(newer_ratio, 4),
            "delta": round(delta_ratio, 4),
            "trend": trend,
            "method": "heuristic_fallback",
        }
        if extra:
            raw.update(extra)
        return FeatureValue(
            "sentiment_trend", score,
            raw_value=raw,
            confidence=0.5, source="heuristic_fallback",
        )

    # ── review_quality (heuristic) ─────────────────────────────────────

    @staticmethod
    def _review_quality(exa: ExaData | None) -> FeatureValue:
        if not exa:
            return FeatureValue(
                "review_quality", 30.0,
                raw_value={
                    "reason": "no_exa_data",
                    "platforms_with_reviews": [],
                    "total_review_results": 0,
                    "has_professional_reviews": False,
                    "has_consumer_reviews": False,
                    "review_signal": "absent",
                },
                confidence=0.3, source="none",
            )

        by_platform: dict[str, list[str]] = {}
        for r in exa.mentions:
            url = (getattr(r, "url", "") or "").lower()
            for platform in _ALL_REVIEW_PLATFORMS:
                if platform in url:
                    by_platform.setdefault(platform, []).append(getattr(r, "url", "") or "")
                    break

        total_review_results = sum(len(urls) for urls in by_platform.values())
        platforms_with_reviews = [
            {"domain": p, "count": len(urls), "sample_urls": urls[:2]}
            for p, urls in sorted(by_platform.items(), key=lambda kv: -len(kv[1]))
        ]
        has_professional = any(p in _PROFESSIONAL_REVIEW_PLATFORMS for p in by_platform)
        has_consumer = any(p in _CONSUMER_REVIEW_PLATFORMS for p in by_platform)

        if not platforms_with_reviews:
            total_mentions = len(exa.mentions) + len(exa.news)
            if total_mentions >= 5:
                score = 50.0; confidence = 0.2
            elif total_mentions >= 1:
                score = 40.0; confidence = 0.25
            else:
                score = 30.0; confidence = 0.3
            return FeatureValue(
                "review_quality", score,
                raw_value={
                    "reason": "no_review_platforms",
                    "platforms_with_reviews": [],
                    "total_review_results": 0,
                    "has_professional_reviews": False,
                    "has_consumer_reviews": False,
                    "review_signal": "absent",
                    "total_mentions": total_mentions,
                },
                confidence=confidence, source="exa",
            )

        # Score: 40 base + 15 per tier covered, bounded at 100.
        score = 40.0
        if has_professional:
            score += 30.0
        if has_consumer:
            score += 15.0
        score += min(total_review_results * 5, 25)
        score = min(score, 100.0)

        if score >= 80:
            signal = "strong"
        elif score >= 60:
            signal = "moderate"
        else:
            signal = "weak"

        return FeatureValue(
            "review_quality", score,
            raw_value={
                "platforms_with_reviews": platforms_with_reviews,
                "total_review_results": total_review_results,
                "has_professional_reviews": has_professional,
                "has_consumer_reviews": has_consumer,
                "review_signal": signal,
            },
            confidence=0.65, source="exa",
        )


def _safe_score(result) -> float | None:
    """Extract sentiment_score from an analyze_brand_sentiment response, or None."""
    if not isinstance(result, dict):
        return None
    verdict = result.get("verdict")
    if verdict not in _VALID_SENTIMENT_VERDICTS:
        return None
    try:
        return max(0.0, min(float(result.get("sentiment_score", 50)), 100.0))
    except (TypeError, ValueError):
        return None
