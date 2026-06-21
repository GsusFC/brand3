"""Evidence candidate extraction for offline packets."""

from __future__ import annotations

import ast
import json
from typing import Any


def build_evidence_candidates(snapshot: dict) -> list[dict]:
    candidates: list[dict] = []
    for feature in snapshot.get("features") or []:
        raw = _parse_raw_value(feature.get("raw_value"))
        base = {
            "origin": "feature",
            "dimension": feature.get("dimension_name") or "",
            "feature_name": feature.get("feature_name") or "",
            "feature_source": feature.get("source") or "",
            "feature_confidence": feature.get("confidence"),
        }
        candidates.extend(_candidates_from_raw(raw, base))

    for item in snapshot.get("evidence_items") or []:
        candidates.append(
            {
                "origin": "evidence_item",
                "dimension": item.get("dimension_name") or "",
                "feature_name": item.get("feature_name") or "",
                "feature_source": item.get("source") or "",
                "feature_confidence": item.get("confidence"),
                "text": str(item.get("quote") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "raw_key": "evidence_item",
            }
        )
    return [candidate for candidate in candidates if candidate.get("text") or candidate.get("url")]


def _parse_raw_value(raw: Any) -> Any:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        return raw
    stripped = raw.strip()
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        pass
    try:
        return json.loads(stripped)
    except (ValueError, TypeError):
        return raw


def _candidates_from_raw(raw: Any, base: dict) -> list[dict]:
    if not isinstance(raw, dict):
        return []
    if (
        str(base.get("dimension") or "") == "diferenciacion"
        and str(base.get("feature_source") or "") == "competitor_web_comparison"
    ):
        return _competitor_comparison_candidates(raw, base)

    out: list[dict] = []

    def add(*, text: str = "", url: str = "", raw_key: str, extra: dict | None = None) -> None:
        text = " ".join(str(text or "").split())
        url = str(url or "").strip()
        if text or url:
            out.append({**base, "text": text, "url": url, "raw_key": raw_key, "extra": extra or {}})

    for key in ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples"):
        items = raw.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                text = item.get("quote") or item.get("snippet") or item.get("text") or item.get("example") or item.get("title") or ""
                source_value = item.get("source") or ""
                source_url = source_value if _is_http_url(source_value) else ""
                url = item.get("source_url") or item.get("url") or source_url
                add(text=text, url=url, raw_key=key, extra={k: v for k, v in item.items() if k not in {"quote", "snippet", "text", "example", "title", "source_url", "url", "source"}})
            elif isinstance(item, str):
                add(text=item, raw_key=key)

    for gap in raw.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        self_says = str(gap.get("self_says") or "").strip()
        third_party = str(gap.get("third_party_says") or "").strip()
        url = str(gap.get("source_url") or gap.get("url") or "").strip()
        if self_says:
            add(text=self_says, raw_key="gap_self_says", extra={"gap_url": url})
        if third_party or url:
            add(text=third_party, url=url, raw_key="gap_third_party_says")

    evidence_url = raw.get("evidence_url")
    evidence_snippet = raw.get("evidence_snippet")
    if isinstance(evidence_url, str) and isinstance(evidence_snippet, str):
        add(text=evidence_snippet, url=evidence_url, raw_key="evidence_snippet")
    elif isinstance(evidence_url, str):
        add(url=evidence_url, raw_key="evidence_url")
    elif isinstance(evidence_snippet, str):
        add(text=evidence_snippet, raw_key="evidence_snippet")
    for snippet in raw.get("evidence_snippets") or []:
        if isinstance(snippet, str):
            add(text=snippet, raw_key="evidence_snippets")
    for insight in raw.get("evidence_insights") or []:
        if isinstance(insight, str):
            add(text=insight, raw_key="evidence_insights")

    for platform in raw.get("platforms") or []:
        if isinstance(platform, dict):
            add(
                text=f"{platform.get('name') or 'social'} profile candidate",
                url=platform.get("url") or "",
                raw_key="platforms",
                extra={"verified": platform.get("verified"), "followers": platform.get("followers")},
            )
    return out


def _competitor_comparison_candidates(raw: dict, base: dict) -> list[dict]:
    candidates: list[dict] = []
    avg_distance = raw.get("avg_distance")
    competitors_analyzed = raw.get("competitors_analyzed")
    source_url = "snapshot://feature/competitor_web_comparison"

    def add(label: str, payload: dict, relation: str) -> None:
        name = str(payload.get("name") or "").strip()
        distance = payload.get("distance")
        if not name or distance is None:
            return
        text = (
            f"Existing Brand3 competitor comparison identifies {name} as the audited brand's {label} "
            f"with measured distance {distance}; avg_distance={avg_distance}; "
            f"competitors_analyzed={competitors_analyzed}."
        )
        candidates.append(
            {
                **base,
                "text": text,
                "url": source_url,
                "raw_key": f"competitor_{relation}",
                "extra": {
                    "competitor_name": name,
                    "distance": distance,
                    "avg_distance": avg_distance,
                    "competitors_analyzed": competitors_analyzed,
                    "limits": (
                        "Snapshot comparison can support relative positioning distance only; "
                        "it does not prove superiority, product quality, adoption, customer choice, "
                        "durable defensibility, or planning direction."
                    ),
                },
            }
        )

    closest = raw.get("closest_competitor")
    if isinstance(closest, dict):
        add("closest measured competitor", closest, "closest")
    most_different = raw.get("most_different")
    if isinstance(most_different, dict):
        add("most different measured competitor", most_different, "most_different")
    return candidates


def _is_http_url(value: Any) -> bool:
    candidate = str(value or "").strip()
    return candidate.startswith("http://") or candidate.startswith("https://")
