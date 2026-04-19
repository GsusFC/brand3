"""
Pure helpers that turn a SQLite run snapshot into the flat context a Jinja2
template can render without further data access. No I/O — tested in isolation.
"""

from __future__ import annotations

import ast
import json
from datetime import datetime
from typing import Any

# REVIEW: D2 — evidence lives in features.raw_value, parsed defensively because
# SQLite stores it via str(dict) (see sqlite_store.py:536), not JSON.
_EVIDENCE_KEYS = ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples")


_BANDS = (
    (20, "F", "critico"),
    (40, "D", "debil"),
    (55, "C", "mixed"),
    (70, "C+", "mixed"),
    (85, "B", "solido"),
    (100, "A", "fuerte"),
)


def slugify(text: str) -> str:
    # REVIEW: D5 — kept local (5 lines) instead of importing from
    # brand_service to avoid pulling in the whole analyze pipeline.
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
    return "-".join(part for part in cleaned.split("-") if part) or "brand"


def band_from_score(score: float | None) -> tuple[str, str]:
    """Map 0-100 to (letter, label). None → ('?', 'n/a')."""
    if score is None:
        return ("?", "n/a")
    for ceiling, letter, label in _BANDS:
        if score < ceiling:
            return (letter, label)
    return ("A", "fuerte")


def ascii_bar(score: float | None, width: int = 20) -> str:
    """Render [███░░░] bar. 5% per block at width=20."""
    if score is None:
        return "[" + "·" * width + "]"
    filled = max(0, min(width, round(score / (100 / width))))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def parse_raw_value(raw: str | None) -> Any:
    """Parse stored raw_value. Tries literal_eval (dict repr), then JSON, then returns as-is."""
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
        pass
    return raw


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def extract_evidence(feature_raw: Any) -> list[dict]:
    """Walk a parsed raw_value dict looking for evidence-like entries.

    Returns a normalized list of {"quote", "source_url", "signal"} dicts.
    """
    if not isinstance(feature_raw, dict):
        return []
    collected: list[dict] = []
    for key in _EVIDENCE_KEYS:
        items = feature_raw.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                quote = _as_str(
                    item.get("quote") or item.get("example") or item.get("text")
                )
                source_url = _as_str(
                    item.get("source_url")
                    or item.get("url")
                    or item.get("source")
                )
                signal = item.get("signal") or item.get("tone") or None
                if quote or source_url:
                    collected.append(
                        {"quote": quote, "source_url": source_url, "signal": signal}
                    )
            elif isinstance(item, str) and item:
                collected.append({"quote": item, "source_url": "", "signal": None})
    return collected


def _verdict_from(feature_raw: Any, band_label: str) -> str:
    if isinstance(feature_raw, dict):
        for key in ("verdict", "summary", "reasoning"):
            value = feature_raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return band_label


def _badge_type_from_band(letter: str) -> str:
    """Map band letter to badge style: ok / warn / neutral."""
    if letter in ("A", "B"):
        return "ok"
    if letter in ("D", "F"):
        return "warn"
    return "neutral"


def _first_nonempty(*values: Any) -> str:
    for v in values:
        s = _as_str(v).strip()
        if s:
            return s
    return ""


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return value if isinstance(value, list) else []


def _format_analysis_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dimension_labels() -> dict[str, str]:
    from ..dimensions import DIMENSIONS

    return {name: name for name in DIMENSIONS}


def build_report_context(snapshot: dict, theme: str = "dark") -> dict:
    """Turn the snapshot returned by SQLiteStore.get_run_snapshot into a flat
    template-friendly dict.

    Expected snapshot shape:
      {
        "run":   {id, brand_name, url, composite_score, calibration_profile,
                  started_at, completed_at, run_duration_seconds,
                  audit: {...}, brand_profile: {...}, summary},
        "scores":      [{dimension_name, score, insights_json, rules_json}, ...],
        "features":    [{dimension_name, feature_name, value, raw_value,
                        confidence, source}, ...],
        "annotations": [...],
      }
    """
    run = snapshot.get("run") or {}
    scores = snapshot.get("scores") or []
    features = snapshot.get("features") or []

    # Index features by dimension
    features_by_dim: dict[str, list[dict]] = {}
    for feat in features:
        dim = feat.get("dimension_name") or ""
        parsed = parse_raw_value(feat.get("raw_value"))
        enriched = {
            "name": feat.get("feature_name"),
            "value": feat.get("value"),
            "confidence": feat.get("confidence"),
            "source": feat.get("source") or "",
            "raw": parsed,
            "evidence": extract_evidence(parsed),
            "verdict": _verdict_from(parsed, ""),
        }
        features_by_dim.setdefault(dim, []).append(enriched)

    # Build per-dimension blocks
    known_dim_order = list(_load_dimension_labels().keys())
    score_by_dim = {row.get("dimension_name"): row for row in scores}

    dimensions_ctx: list[dict] = []
    all_rules_applied: list[dict] = []

    for dim_name in known_dim_order:
        score_row = score_by_dim.get(dim_name) or {}
        score = score_row.get("score")
        insights = _parse_json_list(score_row.get("insights_json"))
        rules_applied = _parse_json_list(score_row.get("rules_json"))
        letter, label = band_from_score(score)
        dim_features = features_by_dim.get(dim_name, [])

        # Pull evidence from all features, capped for visual budget
        evidence_collected: list[dict] = []
        for feat in dim_features:
            evidence_collected.extend(feat["evidence"])
        evidence_collected = evidence_collected[:4]

        # Verdict fallback: first insight; else band label
        verdict_text = _first_nonempty(
            insights[0] if insights else None,
            label,
        )

        for rule in rules_applied:
            all_rules_applied.append({"dimension": dim_name, "rule": rule})

        dimensions_ctx.append({
            "name": dim_name,
            "score": score,
            "score_display": "n/a" if score is None else f"{score:.0f}",
            "bar": ascii_bar(score),
            "band_letter": letter,
            "band_label": label,
            "badge_type": _badge_type_from_band(letter),
            "verdict": verdict_text,
            "observations": insights,
            "features": dim_features,
            "evidence": evidence_collected,
            "has_data": score is not None,
        })

    # Header + footer
    composite = run.get("composite_score")
    band_letter, band_label = band_from_score(composite)
    brand_name = run.get("brand_name") or (run.get("brand_profile") or {}).get("name") or "brand"
    url = run.get("url") or ""
    profile = run.get("calibration_profile") or "base"
    profile_source = run.get("profile_source") or ""
    analysis_date = _format_analysis_date(
        run.get("completed_at") or run.get("started_at")
    )

    audit = run.get("audit") or {}
    fingerprint = audit.get("scoring_state_fingerprint") or ""

    runtime_seconds = run.get("run_duration_seconds")
    data_quality = _first_nonempty(
        run.get("data_quality"),
        audit.get("data_quality"),
    )

    # Terminal-head lines
    term_lines: list[dict] = []
    term_lines.append({
        "level": "ok",
        "text": f"loaded run_id={run.get('id')} · profile={profile} · source={profile_source or 'unknown'}",
    })
    if data_quality:
        level = "warn" if data_quality in ("partial", "insufficient") else "ok"
        term_lines.append({"level": level, "text": f"data_quality: {data_quality}"})
    term_lines.append({"level": "ok", "text": "rendering report ..."})

    summary_text = _first_nonempty(
        run.get("summary"),
        # Fallback to concatenated top insights
        " ".join(
            d["observations"][0]
            for d in dimensions_ctx
            if d["observations"] and d["score"] is not None
        ),
    )

    context = {
        "theme": theme,
        "term_lines": term_lines,
        "brand": {
            "name": brand_name,
            "url": url,
            "analysis_date": analysis_date,
            "profile": profile,
            "profile_source": profile_source,
            "data_quality": data_quality or "unknown",
        },
        "score": {
            "global": composite,
            "global_display": "n/a" if composite is None else f"{composite:.0f}",
            "band_letter": band_letter,
            "band_label": band_label,
        },
        "summary": summary_text,
        "dimensions": dimensions_ctx,
        "rules_applied": all_rules_applied,
        "footer": {
            "engine": "brand3 v0.1.0",
            "profile": f"{profile}" + (f" · source={profile_source}" if profile_source else ""),
            "fingerprint": fingerprint or "n/a",
            "runtime": (
                f"{runtime_seconds:.2f}s" if isinstance(runtime_seconds, (int, float)) else "n/a"
            ),
            "report_id": f"rpt_{run.get('id') or 0:06d}",
        },
    }
    return context
