"""
Vitalidad feature extractor.

Measures whether a brand is ALIVE — still publishing, consistently active, and
building momentum according to third parties.

Three features (weights set in src/dimensions.py):
    content_recency       — days since most recent detectable publication
    publication_cadence   — consistency of publishing over the last 12 months
    momentum              — LLM verdict on building/maintaining/declining, with
                            literal quotes as evidence

Data sources: Exa mentions + news (primary), LLM (momentum only).

Unified single-file design: heuristic features + LLM feature live together.
`VitalidadExtractor` accepts an optional `llm` — if absent or unusable, the
`momentum` feature returns a neutral fallback and the other two features still work.
"""

import json
import statistics
from datetime import datetime, timezone
from ..models.brand import FeatureValue
from ..collectors.web_collector import WebData
from ..collectors.exa_collector import ExaData
from .llm_analyzer import LLMAnalyzer


_DATE_FORMATS = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y")


def _parse_exa_date(raw: str) -> datetime | None:
    if not raw or raw == "None":
        return None
    sliced = raw[:10] if len(raw) >= 10 else raw
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(sliced, fmt)
        except ValueError:
            continue
    try:
        return datetime.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _collect_dated_mentions(exa: ExaData | None) -> list[tuple[datetime, str, str]]:
    """Return [(date, url, text)] from mentions+news that have a parseable date."""
    if not exa:
        return []
    out: list[tuple[datetime, str, str]] = []
    for r in exa.mentions + exa.news:
        d = _parse_exa_date(getattr(r, "published_date", "") or "")
        if not d:
            continue
        url = getattr(r, "url", "") or ""
        text = (getattr(r, "text", "") or "") + " " + (getattr(r, "summary", "") or "")
        out.append((d, url, text.strip()))
    return out


class VitalidadExtractor:
    """Extract vitalidad features."""

    def __init__(self, llm: LLMAnalyzer | None = None):
        # REVIEW: constructor opcional. Si llm=None, `momentum` devuelve
        # fallback heurístico (score 50). Decisión D3 en REVIEW_NOTES.md.
        self.llm = llm

    def extract(self, web: WebData = None, exa: ExaData = None) -> dict[str, FeatureValue]:
        dated = _collect_dated_mentions(exa)
        return {
            "content_recency": self._content_recency(dated),
            "publication_cadence": self._publication_cadence(dated),
            "momentum": self._momentum(exa, dated),
        }

    # ── content_recency ────────────────────────────────────────────────

    def _content_recency(self, dated: list[tuple[datetime, str, str]]) -> FeatureValue:
        """Days since most recent publication. Scale tuned for brand audits."""
        if not dated:
            raw = json.dumps({
                "most_recent_date": None,
                "days_ago": None,
                "evidence_url": None,
                "reason": "no_dates_found",
            })
            return FeatureValue(
                "content_recency", 30.0,
                raw_value=raw, confidence=0.3, source="none",
            )

        most_recent_date, most_recent_url, _ = max(dated, key=lambda t: t[0])
        days_ago = (datetime.now() - most_recent_date).days

        if days_ago <= 7:
            score = 100.0
        elif days_ago <= 30:
            score = 85.0
        elif days_ago <= 90:
            score = 65.0
        elif days_ago <= 180:
            score = 40.0
        elif days_ago <= 365:
            score = 20.0
        else:
            score = 10.0

        raw = json.dumps({
            "most_recent_date": most_recent_date.strftime("%Y-%m-%d"),
            "days_ago": days_ago,
            "evidence_url": most_recent_url or None,
        })
        return FeatureValue(
            "content_recency", score,
            raw_value=raw, confidence=0.7, source="exa",
        )

    # ── publication_cadence ────────────────────────────────────────────

    def _publication_cadence(self, dated: list[tuple[datetime, str, str]]) -> FeatureValue:
        """Consistency of publishing in the last 12 months."""
        cutoff = datetime.now() - _days(365)
        recent = sorted([(d, u) for d, u, _ in dated if d >= cutoff], key=lambda t: t[0])

        evidence = [
            {"date": d.strftime("%Y-%m-%d"), "url": u or None}
            for d, u in recent[-3:]
        ]

        if len(recent) < 2:
            raw = json.dumps({
                "dates_found": len(recent),
                "mean_gap_days": None,
                "gap_stddev_days": None,
                "evidence": evidence,
                "reason": "insufficient_dates_12m",
            })
            return FeatureValue(
                "publication_cadence", 20.0,
                raw_value=raw, confidence=0.4, source="exa",
            )

        gaps = [
            (recent[i][0] - recent[i - 1][0]).days
            for i in range(1, len(recent))
        ]
        mean_gap = statistics.mean(gaps)
        gap_stddev = statistics.pstdev(gaps) if len(gaps) >= 2 else 0.0

        if len(recent) <= 4:
            if mean_gap < 30:
                score = 90.0
            elif mean_gap < 90:
                score = 70.0
            elif mean_gap < 180:
                score = 50.0
            else:
                score = 30.0
        else:
            # 5+ datapoints: start from a confident base and penalise irregularity.
            score = 80.0
            # stddev of 0 → +10; stddev >= mean → -20 (erratic bursts).
            if mean_gap > 0:
                ratio = min(gap_stddev / mean_gap, 1.0)
                score += (1 - ratio) * 10 - ratio * 20
            score = max(40.0, min(score, 95.0))

        raw = json.dumps({
            "dates_found": len(recent),
            "mean_gap_days": round(mean_gap, 1),
            "gap_stddev_days": round(gap_stddev, 1),
            "evidence": evidence,
        })
        return FeatureValue(
            "publication_cadence", round(score, 1),
            raw_value=raw, confidence=0.7, source="exa",
        )

    # ── momentum (LLM) ─────────────────────────────────────────────────

    def _momentum(
        self,
        exa: ExaData | None,
        dated: list[tuple[datetime, str, str]],
    ) -> FeatureValue:
        """LLM verdict with literal quotes from last ~6 months of mentions."""
        if self.llm is None or not getattr(self.llm, "api_key", None):
            raw = json.dumps({
                "reason": "llm_unavailable",
                "note": "Requires LLMAnalyzer with api_key to compute momentum.",
            })
            return FeatureValue(
                "momentum", 50.0,
                raw_value=raw, confidence=0.3, source="heuristic_fallback",
            )

        cutoff = datetime.now() - _days(180)
        recent = [
            {
                "text": text,
                "url": url,
                "published_date": d.strftime("%Y-%m-%d"),
            }
            for d, url, text in dated
            if d >= cutoff and text
        ]

        if not recent:
            raw = json.dumps({
                "reason": "no_recent_mentions_6m",
                "note": "No dated mentions in the last 6 months to analyse.",
            })
            return FeatureValue(
                "momentum", 50.0,
                raw_value=raw, confidence=0.3, source="heuristic_fallback",
            )

        brand_name = getattr(exa, "brand_name", "") if exa else ""
        try:
            result = self.llm.analyze_momentum(recent, brand_name)
        except Exception as exc:  # defensive: any LLM error → fallback
            raw = json.dumps({
                "reason": "llm_error",
                "error": str(exc)[:200],
            })
            return FeatureValue(
                "momentum", 50.0,
                raw_value=raw, confidence=0.3, source="heuristic_fallback",
            )

        if not isinstance(result, dict) or "momentum_score" not in result:
            raw = json.dumps({
                "reason": "llm_invalid_response",
                "got": type(result).__name__,
            })
            return FeatureValue(
                "momentum", 50.0,
                raw_value=raw, confidence=0.3, source="heuristic_fallback",
            )

        verdict = result.get("verdict", "unclear")
        try:
            score = float(result.get("momentum_score", 50))
        except (TypeError, ValueError):
            raw = json.dumps({
                "reason": "llm_invalid_response",
                "got": type(result.get("momentum_score")).__name__,
            })
            return FeatureValue(
                "momentum", 50.0,
                raw_value=raw, confidence=0.3, source="heuristic_fallback",
            )
        score = max(0.0, min(score, 100.0))
        confidence = 0.5 if verdict == "unclear" else 0.85

        raw = json.dumps({
            "verdict": verdict,
            "reasoning": (result.get("reasoning") or "")[:500],
            "evidence": (result.get("evidence") or [])[:3],
        })
        return FeatureValue(
            "momentum", score,
            raw_value=raw, confidence=confidence, source="llm",
        )


def _days(n: int):
    from datetime import timedelta
    return timedelta(days=n)
