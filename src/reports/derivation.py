"""
Pure helpers that turn a SQLite run snapshot into the flat context a Jinja2
template can render without further data access. No I/O — tested in isolation.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from urllib.parse import urlparse

from src.reports.editorial_policy import (
    allowed_language_for_dimension_state,
    evidence_language_hint,
    label_dimension_state,
    label_report_mode,
    tone_for_dimension_state,
    tone_for_report_mode,
)
from src.quality.dimension_confidence import dimension_confidence_from_snapshot
from src.quality.evidence_summary import summarize_evidence_records
from src.quality.report_readiness import evaluate_report_readiness
from src.quality.trust import (
    build_trust_summary,
    dimension_status_counts_from_report_dimensions,
    limited_dimensions_from_report_dimensions,
    quality_label,
)

# REVIEW: D2 — evidence lives in features.raw_value, parsed defensively because
# SQLite stores it via str(dict) (see sqlite_store.py:536), not JSON.
_EVIDENCE_KEYS = ("evidence", "quotes", "examples", "messaging_gaps", "tone_examples")

# Narrative pipeline types (phase 1 of fix/report-narrative).
SourceType = Literal[
    "owned",
    "encyclopedic",
    "social",
    "news",
    "changelog",
    "review",
    "other",
]

_DIMENSION_ORDER: tuple[str, ...] = (
    "coherencia",
    "presencia",
    "percepcion",
    "diferenciacion",
    "vitalidad",
)

_ENCYCLOPEDIC_HOSTS = {"wikipedia.org", "crunchbase.com", "pitchbook.com"}
_SOCIAL_HOSTS = {
    "linkedin.com",
    "x.com",
    "twitter.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "github.com",
}
_REVIEW_HOSTS = {"g2.com", "capterra.com", "trustpilot.com", "producthunt.com"}
_NEWS_HOSTS = {
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "forbes.com",
    "bloomberg.com",
    "reuters.com",
    "nytimes.com",
    "washingtonpost.com",
    "ft.com",
    "economist.com",
    "bbc.com",
    "bbc.co.uk",
    "cnn.com",
    "wsj.com",
    "theguardian.com",
    "axios.com",
    "businessinsider.com",
    "venturebeat.com",
    "arstechnica.com",
    "fastcompany.com",
    "elpais.com",
    "elmundo.es",
    "expansion.com",
    "cincodias.elpais.com",
    "eleconomista.es",
    "lavanguardia.com",
}
_CHANGELOG_PATH_MARKERS = ("/changelog", "/releases", "/blog/release", "/release-notes")


@dataclass(frozen=True)
class Evidence:
    """Normalized evidence item extracted from any feature's raw_value."""

    dimension: str
    quote: str | None
    url: str | None
    source_type: SourceType
    source_domain: str | None
    sentiment: str | None
    feature_name: str | None
    extra: dict = field(default_factory=dict)


@dataclass
class DimensionEvidences:
    """One dimension's score + verdict + all evidences belonging to it."""

    dimension: str
    display_name: str
    score: float | None
    verdict: str
    verdict_adjective: str
    evidences: list[Evidence] = field(default_factory=list)


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


def _report_evidence_items_by_dimension(snapshot: dict) -> dict[str, list[dict]]:
    by_dim: dict[str, list[dict]] = {}
    for item in snapshot.get("evidence_items") or []:
        dimension = item.get("dimension_name") or ""
        quote = _as_str(item.get("quote")).strip()
        source_url = _as_str(item.get("url")).strip()
        if not dimension or not (quote or source_url):
            continue
        by_dim.setdefault(dimension, []).append({
            "quote": quote,
            "source_url": source_url,
            "signal": item.get("source") or None,
        })
    return by_dim


def _dedupe_report_evidence(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for item in items:
        key = (
            _as_str(item.get("quote")).strip(),
            _as_str(item.get("source_url")).strip(),
        )
        if not key[0] and not key[1]:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


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
    return {
        "coherencia": "Coherence",
        "presencia": "Presence",
        "percepcion": "Perception",
        "diferenciacion": "Differentiation",
        "vitalidad": "Vitality",
    }


def build_report_base(snapshot: dict, theme: str = "dark") -> dict:
    """Turn the snapshot returned by SQLiteStore.get_run_snapshot into a
    structured base dossier for report rendering.

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
    confidence_by_dim = dimension_confidence_from_snapshot(snapshot)
    persisted_evidence_by_dim = _report_evidence_items_by_dimension(snapshot)

    dimensions_ctx: list[dict] = []
    all_rules_applied: list[dict] = []

    for dim_name in known_dim_order:
        score_row = score_by_dim.get(dim_name) or {}
        score = score_row.get("score")
        insights = _parse_json_list(score_row.get("insights_json"))
        rules_applied = _parse_json_list(score_row.get("rules_json"))
        letter, label = band_from_score(score)
        dim_features = features_by_dim.get(dim_name, [])
        dim_confidence = confidence_by_dim.get(dim_name) or {}

        # Pull evidence from all features, capped for visual budget
        evidence_collected: list[dict] = []
        for feat in dim_features:
            evidence_collected.extend(feat["evidence"])
        evidence_collected.extend(persisted_evidence_by_dim.get(dim_name, []))
        evidence_collected = _dedupe_report_evidence(evidence_collected)[:6]

        # Verdict fallback: first insight; else band label
        verdict_text = _first_nonempty(
            insights[0] if insights else None,
            label,
        )

        for rule in rules_applied:
            all_rules_applied.append({"dimension": dim_name, "rule": rule})

        short_verdict, verdict_adjective = derive_verdict(score)
        dimensions_ctx.append({
            "name": dim_name,
            "display_name": _load_dimension_labels().get(dim_name, dim_name),
            "score": score,
            "score_display": "n/a" if score is None else f"{score:.0f}",
            "bar": ascii_bar(score),
            "band_letter": letter,
            "band_label": label,
            "badge_type": _badge_type_from_band(letter),
            "verdict": verdict_text,
            "short_verdict": short_verdict,
            "verdict_adjective": verdict_adjective,
            "observations": insights,
            "features": dim_features,
            "evidence": evidence_collected,
            "coverage": dim_confidence.get("coverage", 0.0),
            "coverage_label": quality_label(float(dim_confidence.get("coverage") or 0.0)),
            "confidence": dim_confidence.get("confidence", 0.0),
            "confidence_label": quality_label(float(dim_confidence.get("confidence") or 0.0)),
            "confidence_status": dim_confidence.get("status", "insufficient_data"),
            "confidence_reason": dim_confidence.get("confidence_reason", []),
            "confidence_reason_labels": _confidence_reason_labels(
                dim_confidence.get("confidence_reason", [])
            ),
            "missing_signals": dim_confidence.get("missing_signals", []),
            "recommended_next_steps": dim_confidence.get("recommended_next_steps", []),
            # Phase 3 placeholder — filled in by narrative pipeline in phase 4.
            "findings": [],
            "has_data": score is not None,
        })

    context_readiness = _context_readiness_from_snapshot(snapshot)
    evidence_summary = summarize_evidence_records(
        snapshot.get("features") or [],
        evidence_items=snapshot.get("evidence_items") or [],
    )
    readiness = evaluate_report_readiness(**_readiness_inputs_from_snapshot(
        snapshot,
        evidence_summary=evidence_summary,
        confidence_summary=confidence_by_dim,
    ))
    readiness = _annotate_readiness_diagnostics(
        snapshot,
        readiness,
        context_readiness=context_readiness,
    )
    cost_policy = _cost_policy_from_snapshot(snapshot)
    dimension_status_counts = dimension_status_counts_from_report_dimensions(dimensions_ctx)

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

    # Defensive data_quality — replaces the legacy "unknown" sentinel.
    data_quality = derive_data_quality(snapshot)

    # Terminal-head lines
    term_lines: list[dict] = []
    term_lines.append({
        "level": "ok",
        "text": f"loaded run_id={run.get('id')} · profile={profile} · source={profile_source or 'unknown'}",
    })
    if data_quality:
        level = "warn" if data_quality in ("degraded", "insufficient") else "ok"
        term_lines.append({"level": level, "text": f"data_quality: {data_quality}"})
    term_lines.append({"level": "ok", "text": "rendering report ..."})

    # Deterministic synthesis fallback — overridden by LLM output in the
    # renderer when an analyzer is configured. Honest about missing score.
    scored_dims = [d for d in dimensions_ctx if d["score"] is not None]
    if composite is None:
        synthesis_head = f"{brand_name}: global score unavailable for this run."
    else:
        synthesis_head = (
            f"{brand_name} scores {composite:.0f}/100 (band {band_letter})."
        )
    if scored_dims:
        top = max(scored_dims, key=lambda d: d["score"])
        bottom = min(scored_dims, key=lambda d: d["score"])
        synthesis_prose = (
            f"{synthesis_head} "
            f"Strongest dimension: {top['display_name']} ({top['score']:.0f}/100). "
            f"Weakest dimension: {bottom['display_name']} ({bottom['score']:.0f}/100). "
            f"Data quality: {data_quality}."
        )
    else:
        synthesis_prose = (
            f"{synthesis_head} "
            f"Per-dimension scores unavailable for this run. "
            f"Data quality: {data_quality}."
        )

    # Sources grouped for §5 collapsible list.
    sources_grouped, all_sources = _group_sources(snapshot)

    # Global band verdict.
    _, band_adjective = derive_verdict(composite)
    trust_summary = build_trust_summary(
        data_quality=data_quality,
        context_summary=context_readiness,
        evidence_summary=evidence_summary,
        dimension_status_counts=dimension_status_counts,
        limited_dimensions=limited_dimensions_from_report_dimensions(dimensions_ctx),
    )

    return {
        "theme": theme,
        "brand": {
            "name": brand_name,
            "url": url,
            "domain": _extract_domain(url),
            "analysis_date": analysis_date,
            "profile": profile,
            "profile_source": profile_source,
            "data_quality": data_quality,
        },
        "evaluation": {
            "composite_score": composite,
            "composite_display": "n/a" if composite is None else f"{composite:.0f}",
            "band_letter": band_letter,
            "band_label": band_label,
            "band_adjective": band_adjective,
            "data_quality": data_quality,
            "composite_reliable": data_quality == "good" and composite is not None,
            "partial_score": composite is None or data_quality != "good",
            "context_readiness": context_readiness,
            "evidence_summary": evidence_summary,
            "cost_policy": cost_policy,
            "dimension_status_counts": dimension_status_counts,
            "overall_status": trust_summary["overall_status"],
            "overall_status_label": trust_summary["overall_status_label"],
            "overall_reason": trust_summary["overall_reason"],
            "overall_reason_label": trust_summary["overall_reason_label"],
            "trust_summary": trust_summary,
            "readiness": readiness,
        },
        "dimensions": dimensions_ctx,
        "rules_applied": all_rules_applied,
        "narrative": {
            "legacy_summary": synthesis_prose,
            "summary": synthesis_prose,
            "synthesis_prose": synthesis_prose,
            "tensions_prose": None,  # Narrative layer wires this in later.
        },
        "sources": {
            "grouped": sources_grouped,
            "all": all_sources,
        },
        "audit": {
            "engine": "brand3 v0.1.0",
            "profile": f"{profile}" + (f" · source={profile_source}" if profile_source else ""),
            "fingerprint": fingerprint or "n/a",
            "runtime": (
                f"{runtime_seconds:.2f}s" if isinstance(runtime_seconds, (int, float)) else "n/a"
            ),
            "report_id": f"rpt_{run.get('id') or 0:06d}",
        },
        "ui": {
            "theme": theme,
            "term_lines": term_lines,
            "show_readiness_diagnostic": False,
        },
    }


def build_report_context_from_base(base: dict) -> dict:
    """Adapt the structured base dossier into the legacy flat template context.

    This preserves template compatibility while letting the app/report stack
    converge on a single dossier contract.
    """
    brand = base["brand"]
    evaluation = base["evaluation"]
    narrative = base["narrative"]
    sources = base["sources"]
    audit = base["audit"]
    ui = base["ui"]
    readiness = evaluation.get("readiness") or {}
    editorial_policy = _editorial_policy_from_readiness(readiness)
    presentation_policy = _presentation_policy_from_readiness(readiness)
    return {
        "theme": ui["theme"],
        "term_lines": ui["term_lines"],
        "brand": brand,
        "score": {
            "global": evaluation["composite_score"],
            "global_display": evaluation["composite_display"],
            "band_letter": evaluation["band_letter"],
            "band_label": evaluation["band_label"],
            "band_adjective": evaluation["band_adjective"],
        },
        "summary": narrative["summary"],
        "legacy_summary": narrative["legacy_summary"],
        "synthesis_prose": narrative["synthesis_prose"],
        "tensions_prose": narrative["tensions_prose"],
        "sources_grouped": sources["grouped"],
        "all_sources": sources["all"],
        "dimensions": base["dimensions"],
        "rules_applied": base["rules_applied"],
        "footer": audit,
        # Expose the richer dossier parts too so non-template consumers can
        # reuse the same object without reconstructing them.
        "evaluation": evaluation,
        "context_readiness": evaluation.get("context_readiness") or {},
        "evidence_summary": evaluation.get("evidence_summary") or {},
        "readiness": readiness,
        "editorial_policy": editorial_policy,
        "presentation_policy": presentation_policy,
        "cost_policy": evaluation.get("cost_policy") or {},
        "trust_summary": evaluation.get("trust_summary") or {},
        "narrative": narrative,
        "sources": sources,
        "audit": audit,
        "ui": ui,
    }


def _presentation_policy_from_readiness(readiness: dict) -> dict:
    mode = readiness.get("report_mode") or ""
    dimension_states = readiness.get("dimension_states") or {}
    is_publishable = mode == "publishable_brand_report"
    is_technical_diagnostic = mode == "technical_diagnostic"
    is_insufficient_evidence = mode == "insufficient_evidence"

    if is_publishable:
        headline = "Publishable brand report"
        allow_editorial_conclusions = True
        allow_strategic_recommendations = True
    elif is_technical_diagnostic:
        headline = "Technical diagnostic"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False
    elif is_insufficient_evidence:
        headline = "Insufficient evidence"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False
    else:
        headline = "Unclassified report"
        allow_editorial_conclusions = False
        allow_strategic_recommendations = False

    return {
        "report_mode": mode,
        "is_publishable": is_publishable,
        "is_technical_diagnostic": is_technical_diagnostic,
        "is_insufficient_evidence": is_insufficient_evidence,
        "headline": headline,
        "summary": readiness.get("diagnostic_summary") or "",
        "allow_editorial_conclusions": allow_editorial_conclusions,
        "allow_strategic_recommendations": allow_strategic_recommendations,
        "dimension_presentation": {
            name: _dimension_presentation_policy(
                state,
                report_mode=mode,
                allow_editorial_conclusions=allow_editorial_conclusions,
            )
            for name, state in dimension_states.items()
        },
    }


def _dimension_presentation_policy(
    state: str,
    *,
    report_mode: str,
    allow_editorial_conclusions: bool,
) -> dict:
    if state == "not_evaluable":
        language_mode = "blocked"
    elif state == "observation_only":
        language_mode = "observational"
    elif report_mode == "technical_diagnostic" or state == "technical_only":
        language_mode = "technical_only"
    elif state == "ready" and allow_editorial_conclusions:
        language_mode = "editorial"
    elif state == "ready":
        language_mode = "technical_only"
    else:
        language_mode = "blocked"

    return {
        "state": state,
        "allow_strong_claims": (
            allow_editorial_conclusions
            and state == "ready"
            and language_mode == "editorial"
        ),
        "language_mode": language_mode,
    }


def build_report_context(snapshot: dict, theme: str = "dark") -> dict:
    """Backward-compatible wrapper used by existing tests and callers."""
    return build_report_context_from_base(build_report_base(snapshot, theme=theme))


def _editorial_policy_from_readiness(readiness: dict) -> dict:
    mode = readiness.get("report_mode") or ""
    dimension_states = readiness.get("dimension_states") or {}
    return {
        "report_mode": mode,
        "report_mode_label": label_report_mode(mode),
        "report_tone": tone_for_report_mode(mode),
        "dimension_policies": {
            name: {
                "state": state,
                "state_label": label_dimension_state(state),
                "tone": tone_for_dimension_state(state),
                "allowed_language": allowed_language_for_dimension_state(state),
            }
            for name, state in dimension_states.items()
        },
        "evidence_policy": {
            evidence_type: evidence_language_hint(evidence_type)
            for evidence_type in (
                "direct",
                "indirect",
                "weak",
                "off_entity",
                "analysis_note",
                "fallback",
            )
        },
    }


def _readiness_features_from_snapshot(snapshot: dict) -> dict[str, list[dict]]:
    by_dimension: dict[str, list[dict]] = {}
    for feature in snapshot.get("features") or []:
        dimension_name = feature.get("dimension_name") or ""
        if not dimension_name:
            continue
        by_dimension.setdefault(dimension_name, []).append({
            "feature_name": feature.get("feature_name"),
            "value": feature.get("value"),
            "confidence": feature.get("confidence"),
            "source": feature.get("source") or "",
            "raw_value": feature.get("raw_value"),
        })
    return by_dimension


def _readiness_inputs_from_snapshot(
    snapshot: dict,
    *,
    evidence_summary: dict,
    confidence_summary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build evaluator inputs from DB-like or processed report snapshots."""
    return {
        "scores": _readiness_scores_from_snapshot(snapshot),
        "evidence_summary": _readiness_evidence_summary_from_snapshot(
            snapshot,
            fallback=evidence_summary,
        ),
        "confidence_summary": _readiness_confidence_from_snapshot(
            snapshot,
            fallback=confidence_summary,
        ),
        "features_by_dimension": _readiness_features_from_snapshot(snapshot),
    }


def _annotate_readiness_diagnostics(
    snapshot: dict,
    readiness: dict,
    *,
    context_readiness: dict,
) -> dict:
    annotated = dict(readiness)
    input_limitations = list(annotated.get("input_limitations") or [])
    warnings = list(annotated.get("warnings") or [])

    if _is_legacy_score_only_snapshot(snapshot):
        if "legacy_score_only_snapshot" not in input_limitations:
            input_limitations.append("legacy_score_only_snapshot")
        warning = "readiness_requires_evidence_and_confidence_metadata"
        if warning not in warnings:
            warnings.append(warning)

    annotated["input_limitations"] = input_limitations
    annotated["warnings"] = warnings
    annotated["diagnostic_summary"] = _readiness_diagnostic_summary(
        annotated,
        context_readiness=context_readiness,
    )
    return annotated


def _readiness_diagnostic_summary(readiness: dict, *, context_readiness: dict) -> str:
    mode = readiness.get("report_mode") or "unknown"
    dimension_states = readiness.get("dimension_states") or {}
    not_evaluable = _dimensions_with_state(dimension_states, "not_evaluable")
    technical_only = _dimensions_with_state(dimension_states, "technical_only")
    observation_only = _dimensions_with_state(dimension_states, "observation_only")
    blockers = readiness.get("blockers") or []
    input_limitations = readiness.get("input_limitations") or []

    if "legacy_score_only_snapshot" in input_limitations:
        return (
            "This is a legacy score-only snapshot. Readiness cannot be evaluated "
            "because the file lacks evidence and confidence metadata."
        )

    if mode == "publishable_brand_report":
        if observation_only:
            return (
                "This report has enough evidence and confidence for editorial use. "
                f"Some dimensions remain observation-only: {', '.join(observation_only)}."
            )
        return "This report has enough evidence and confidence for editorial use."

    if mode == "technical_diagnostic":
        reasons: list[str] = []
        if "unsupported_editorial_synthesis" in blockers:
            reasons.append("unsupported editorial synthesis is blocked")
        if technical_only:
            reasons.append(f"technical-only dimensions: {', '.join(technical_only)}")
        if not_evaluable:
            reasons.append(f"not-evaluable dimensions: {', '.join(not_evaluable)}")
        if observation_only:
            reasons.append(f"observation-only dimensions: {', '.join(observation_only)}")
        if _context_is_limited(context_readiness):
            reasons.append("context readiness is limited")
        if not reasons:
            reasons.append("core dimensions lack enough supported evidence or confidence")
        return (
            "Technical diagnostic: the report can show scores and technical signals, "
            "but should not be treated as a publishable brand report because "
            + "; ".join(reasons)
            + "."
        )

    if mode == "insufficient_evidence":
        if not_evaluable:
            return (
                "Insufficient evidence: multiple dimensions are not evaluable "
                f"({', '.join(not_evaluable)})."
            )
        if _context_is_limited(context_readiness):
            return "Insufficient evidence: context readiness is limited."
        return "Insufficient evidence: required evidence or confidence metadata is missing."

    return "Readiness could not be classified from the available metadata."


def _dimensions_with_state(dimension_states: dict, state: str) -> list[str]:
    return [
        name
        for name, value in dimension_states.items()
        if value == state
    ]


def _context_is_limited(context_readiness: dict) -> bool:
    return (context_readiness or {}).get("status") in {"degraded", "insufficient_data"}


def _is_legacy_score_only_snapshot(snapshot: dict) -> bool:
    dimensions = snapshot.get("dimensions")
    has_dimension_scores = isinstance(dimensions, dict) and any(
        name in dimensions for name in _DIMENSION_ORDER
    )
    if not has_dimension_scores:
        return False
    if snapshot.get("run") or snapshot.get("scores"):
        return False
    if snapshot.get("features") or snapshot.get("evidence_items"):
        return False
    if isinstance(snapshot.get("evidence_summary"), dict):
        return False
    if _looks_dimension_keyed(snapshot.get("confidence_summary")):
        return False
    if _looks_dimension_keyed(snapshot.get("dimension_confidence")):
        return False
    return True


def _readiness_scores_from_snapshot(snapshot: dict) -> dict[str, Any]:
    rows = snapshot.get("scores") or []
    if rows:
        return {
            row.get("dimension_name"): row.get("score")
            for row in rows
            if isinstance(row, dict) and row.get("dimension_name")
        }

    dimensions = snapshot.get("dimensions")
    if isinstance(dimensions, dict):
        return {
            dimension_name: score
            for dimension_name, score in dimensions.items()
            if dimension_name in _DIMENSION_ORDER
        }
    if isinstance(dimensions, list):
        scores: dict[str, Any] = {}
        for dimension in dimensions:
            if not isinstance(dimension, dict):
                continue
            name = dimension.get("name") or dimension.get("id") or dimension.get("dimension_name")
            if name:
                scores[name] = dimension.get("score")
        return scores
    return {}


def _readiness_evidence_summary_from_snapshot(snapshot: dict, *, fallback: dict) -> dict:
    existing = snapshot.get("evidence_summary")
    if isinstance(existing, dict):
        return existing
    return fallback


def _readiness_confidence_from_snapshot(
    snapshot: dict,
    *,
    fallback: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    confidence = snapshot.get("confidence_summary")
    if _looks_dimension_keyed(confidence):
        return _readiness_confidence_without_feature_penalty(snapshot, confidence)

    dimension_confidence = snapshot.get("dimension_confidence")
    if _looks_dimension_keyed(dimension_confidence):
        return _readiness_confidence_without_feature_penalty(snapshot, dimension_confidence)

    return fallback


def _readiness_confidence_without_feature_penalty(
    snapshot: dict,
    confidence: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if snapshot.get("features") or "dimensions" not in snapshot:
        return confidence

    sanitized: dict[str, dict[str, Any]] = {}
    for dimension_name, value in confidence.items():
        if isinstance(value, dict):
            sanitized[dimension_name] = dict(value)
            sanitized[dimension_name]["missing_signals"] = []
        else:
            sanitized[dimension_name] = value
    return sanitized


def _looks_dimension_keyed(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(key in value and isinstance(value.get(key), dict) for key in _DIMENSION_ORDER)


def _context_readiness_from_snapshot(snapshot: dict) -> dict:
    raw_inputs = snapshot.get("raw_inputs") or []
    payload = None
    for item in reversed(raw_inputs):
        if item.get("source") == "context":
            payload = item.get("payload") or {}
            break
    if not isinstance(payload, dict):
        return {
            "available": False,
            "status": "insufficient_data",
            "coverage_label": "baja",
            "confidence_label": "baja",
            "message": "No context pre-scan was stored for this run.",
        }

    coverage = float(payload.get("coverage") or 0.0)
    confidence = float(payload.get("confidence") or 0.0)
    if coverage < 0.3:
        status = "insufficient_data"
    elif confidence < 0.6:
        status = "degraded"
    else:
        status = "good"
    return {
        "available": True,
        "status": status,
        "context_score": payload.get("context_score"),
        "coverage": coverage,
        "confidence": confidence,
        "coverage_label": quality_label(coverage),
        "confidence_label": quality_label(confidence),
        "robots_found": bool(payload.get("robots_found")),
        "sitemap_found": bool(payload.get("sitemap_found")),
        "sitemap_url_count": int(payload.get("sitemap_url_count") or 0),
        "llms_txt_found": bool(payload.get("llms_txt_found")),
        "llms_full_found": bool(payload.get("llms_full_found")),
        "ai_plugin_found": bool(payload.get("ai_plugin_found")),
        "schema_types": payload.get("schema_types") or [],
        "key_pages": payload.get("key_pages") or {},
        "avg_words": int(payload.get("avg_words") or 0),
        "avg_internal_links": int(payload.get("avg_internal_links") or 0),
        "confidence_reason": payload.get("confidence_reason") or [],
        "opportunities": payload.get("opportunities") or [],
    }


def _cost_policy_from_snapshot(snapshot: dict) -> dict:
    run = snapshot.get("run") or {}
    raw_inputs = snapshot.get("raw_inputs") or []
    raw_sources = sorted({
        item.get("source")
        for item in raw_inputs
        if isinstance(item, dict) and item.get("source")
    })
    skipped: dict[str, str] = {}
    if run.get("use_llm") in (0, False):
        skipped["llm"] = "disabled_by_request"
    elif run.get("llm_used") in (0, False):
        skipped["llm"] = "not_used"
    if run.get("use_social") in (0, False):
        skipped["social"] = "disabled_by_request"
    elif run.get("social_scraped") in (0, False):
        skipped["social"] = "not_scraped"
    return {
        "available": bool(raw_sources or skipped),
        "raw_input_sources": raw_sources,
        "persisted_raw_inputs": len(raw_inputs),
        "skipped": skipped,
    }


def _confidence_reason_labels(reasons: list[str]) -> list[str]:
    labels = [_confidence_reason_label(reason) for reason in reasons]
    return [label for label in labels if label]


def _confidence_reason_label(reason: str) -> str:
    labels = {
        "low_coverage": "",
        "low_feature_confidence": "confianza baja en señales",
        "no_evidence": "sin evidencia directa",
        "insufficient_data_quality": "calidad de datos insuficiente",
        "context_low_coverage": "pre-scan contextual limitado",
    }
    return labels.get(reason, reason.replace("_", " "))


# Source grouping helpers — consumed by both build_report_context and the
# standalone narrative pipeline.

_SOURCE_GROUP_ORDER: tuple[tuple[str, str], ...] = (
    ("owned", "Owned"),
    ("encyclopedic", "Encyclopedic"),
    ("news", "News"),
    ("social", "Social"),
    ("review", "Reviews"),
    ("changelog", "Changelog"),
    ("other", "Other"),
)


def _group_sources(snapshot: dict) -> tuple[dict[str, list[str]], list[str]]:
    """Group unique evidence URLs by source_type, preserving spec order."""
    evidences = collect_evidences(snapshot)
    buckets: dict[str, list[str]] = {key: [] for key, _ in _SOURCE_GROUP_ORDER}
    seen: set[str] = set()
    all_urls: list[str] = []
    for ev in evidences:
        if not ev.url or ev.url in seen:
            continue
        seen.add(ev.url)
        all_urls.append(ev.url)
        buckets.setdefault(ev.source_type, []).append(ev.url)

    # Return labelled dict in spec order, dropping empty buckets.
    grouped: dict[str, list[str]] = {}
    for key, label in _SOURCE_GROUP_ORDER:
        urls = buckets.get(key) or []
        if urls:
            grouped[label] = urls
    return grouped, all_urls


# ---------------------------------------------------------------------------
# Narrative pipeline (phase 1 of fix/report-narrative)
# ---------------------------------------------------------------------------


def _extract_domain(url: str | None) -> str | None:
    if not url or not isinstance(url, str):
        return None
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return None
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _host_suffix_match(host: str, needle: str) -> bool:
    return host == needle or host.endswith("." + needle)


def _infer_source_type(url: str | None, brand_domain: str | None) -> SourceType:
    """Classify a URL into SourceType. Brand-owned check wins over all others."""
    host = _extract_domain(url)
    if not host:
        return "other"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        path = (urlparse(url).path or "").lower() if url else ""
        if any(marker in path for marker in _CHANGELOG_PATH_MARKERS):
            return "changelog"
        return "owned"
    for candidate in _ENCYCLOPEDIC_HOSTS:
        if _host_suffix_match(host, candidate):
            return "encyclopedic"
    for candidate in _SOCIAL_HOSTS:
        if _host_suffix_match(host, candidate):
            return "social"
    for candidate in _REVIEW_HOSTS:
        if _host_suffix_match(host, candidate):
            return "review"
    path = (urlparse(url).path or "").lower() if url else ""
    if any(marker in path for marker in _CHANGELOG_PATH_MARKERS):
        return "changelog"
    for candidate in _NEWS_HOSTS:
        if _host_suffix_match(host, candidate):
            return "news"
    return "other"


def _build_evidence(
    dimension: str,
    feature_name: str | None,
    quote: str | None,
    url: str | None,
    sentiment: str | None,
    brand_domain: str | None,
    extra: dict | None = None,
) -> Evidence | None:
    """Build an Evidence, enforcing "must have quote or url" gate."""
    q = (quote or "").strip() or None
    u = (url or "").strip() or None
    if u and not (u.startswith("http://") or u.startswith("https://")):
        u = None
    if not q and not u:
        return None
    source_type = _infer_source_type(u, brand_domain)
    return Evidence(
        dimension=dimension,
        quote=q,
        url=u,
        source_type=source_type,
        source_domain=_extract_domain(u),
        sentiment=(sentiment or None),
        feature_name=feature_name,
        extra=extra or {},
    )


def _iter_feature_evidences(
    dimension: str,
    feature_name: str | None,
    raw: Any,
    brand_domain: str | None,
) -> list[Evidence]:
    """Walk a parsed raw_value and emit Evidence objects.

    Handles the observed shapes across the 20 features:
      - evidence: [{quote, source_url, signal}]         (brand_sentiment)
      - evidence: [{quote, signal}]                      (positioning_clarity)
      - evidence: [{url, title, snippet}]                (search_visibility)
      - evidence: [{date, url}]                          (publication_cadence)
      - examples: [{source, quote}]                      (tone_consistency)
      - evidence_url: "https://..."                      (content_recency)
      - evidence_snippet: "..."                          (web_presence)
      - evidence_snippets: ["...", "..."]                (content_authenticity)
    Dicts without a quote AND without a URL are dropped.
    """
    if not isinstance(raw, dict):
        return []

    out: list[Evidence] = []

    def add(
        quote: str | None = None,
        url: str | None = None,
        sentiment: str | None = None,
        extra: dict | None = None,
    ) -> None:
        ev = _build_evidence(
            dimension=dimension,
            feature_name=feature_name,
            quote=quote,
            url=url,
            sentiment=sentiment,
            brand_domain=brand_domain,
            extra=extra,
        )
        if ev is not None:
            out.append(ev)

    for key in _EVIDENCE_KEYS:
        items = raw.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                quote = item.get("quote") or item.get("snippet") or item.get("text") or item.get("example")
                url = item.get("source_url") or item.get("url")
                sentiment = item.get("signal") or item.get("sentiment") or item.get("tone")
                extra = {k: v for k, v in item.items() if k in ("title", "date", "source")}
                add(quote=quote, url=url, sentiment=sentiment, extra=extra)
            elif isinstance(item, str) and item.strip():
                add(quote=item)

    single_url = raw.get("evidence_url")
    if isinstance(single_url, str):
        add(url=single_url)

    single_quote = raw.get("evidence_snippet")
    if isinstance(single_quote, str):
        add(quote=single_quote)

    snippets = raw.get("evidence_snippets")
    if isinstance(snippets, list):
        for s in snippets:
            if isinstance(s, str) and s.strip():
                add(quote=s)

    insights = raw.get("evidence_insights")
    if isinstance(insights, list):
        for s in insights:
            if isinstance(s, str) and s.strip():
                add(quote=s)

    return out


def collect_evidences(snapshot: dict) -> list[Evidence]:
    """Extract normalized Evidence items from every feature in a run snapshot.

    Input: the dict returned by `SQLiteStore.get_run_snapshot(run_id)` —
    the same shape consumed by `build_report_context`.
    """
    run = snapshot.get("run") or {}
    brand_url = run.get("url") or (run.get("brand_profile") or {}).get("url") or ""
    brand_domain = _extract_domain(brand_url) if brand_url else None

    evidences: list[Evidence] = []
    for feat in snapshot.get("features") or []:
        dim = feat.get("dimension_name") or ""
        if not dim:
            continue
        parsed = parse_raw_value(feat.get("raw_value"))
        evidences.extend(
            _iter_feature_evidences(
                dimension=dim,
                feature_name=feat.get("feature_name"),
                raw=parsed,
                brand_domain=brand_domain,
            )
        )
    for item in snapshot.get("evidence_items") or []:
        dimension = item.get("dimension_name") or ""
        if not dimension:
            continue
        ev = _build_evidence(
            dimension=dimension,
            feature_name=item.get("feature_name"),
            quote=item.get("quote"),
            url=item.get("url"),
            sentiment=None,
            brand_domain=brand_domain,
            extra={
                "source": item.get("source"),
                "confidence": item.get("confidence"),
                "freshness_days": item.get("freshness_days"),
            },
        )
        if ev is not None:
            evidences.append(ev)
    return evidences


def derive_verdict(score: float | None) -> tuple[str, str]:
    """Map a dimension score to (short_verdict, adjective) for narrative UI.

    Thresholds:
      >= 80  solid     · cohesive
      >= 65  mixed     · mostly-solid
      >= 50  mixed     · uneven
      >= 35  weak      · fragmented
      <  35  very weak · broken
      None   n/a       · unknown
    """
    if score is None:
        return ("n/a", "unknown")
    if score >= 80:
        return ("solid", "cohesive")
    if score >= 65:
        return ("mixed", "mostly-solid")
    if score >= 50:
        return ("mixed", "uneven")
    if score >= 35:
        return ("weak", "fragmented")
    return ("very weak", "broken")


def group_by_dimension(
    evidences: list[Evidence],
    snapshot: dict,
) -> list[DimensionEvidences]:
    """Bucket evidences by dimension and attach score + verdict.

    Output is a list of 5 DimensionEvidences in fixed order
    (coherencia, presencia, percepcion, diferenciacion, vitalidad).
    Dimensions with no evidences still appear with `evidences=[]`.
    """
    by_dim: dict[str, list[Evidence]] = {d: [] for d in _DIMENSION_ORDER}
    for ev in evidences:
        if ev.dimension in by_dim:
            by_dim[ev.dimension].append(ev)

    score_by_dim: dict[str, float | None] = {}
    for row in snapshot.get("scores") or []:
        name = row.get("dimension_name")
        if name in by_dim:
            score_by_dim[name] = row.get("score")

    result: list[DimensionEvidences] = []
    for name in _DIMENSION_ORDER:
        score = score_by_dim.get(name)
        short, adj = derive_verdict(score)
        result.append(
            DimensionEvidences(
                dimension=name,
                display_name=_load_dimension_labels().get(name, name),
                score=score,
                verdict=short,
                verdict_adjective=adj,
                evidences=by_dim[name],
            )
        )
    return result


def derive_data_quality(snapshot: dict) -> str:
    """Defensive data_quality calculator — never returns 'unknown'.

    Order of checks:
      1. Run-level field already set to a valid value → use it.
      2. llm_used=False in the run → insufficient.
      3. >40% features marked heuristic/fallback → degraded.
      4. web_presence evidence_snippet under 200 chars → degraded.
      5. otherwise → good.
    """
    run = snapshot.get("run") or {}
    explicit = run.get("data_quality")
    if isinstance(explicit, str) and explicit in ("good", "degraded", "insufficient"):
        return explicit

    llm_used = run.get("llm_used")
    if llm_used in (0, False):
        return "insufficient"

    features = snapshot.get("features") or []
    if not features:
        return "insufficient"

    heuristic_like = 0
    web_presence_snippet_len: int | None = None
    for feat in features:
        source = (feat.get("source") or "").lower()
        if "heuristic" in source or "fallback" in source:
            heuristic_like += 1
        if feat.get("feature_name") == "web_presence":
            parsed = parse_raw_value(feat.get("raw_value"))
            if isinstance(parsed, dict):
                snippet = parsed.get("evidence_snippet") or ""
                if isinstance(snippet, str):
                    web_presence_snippet_len = len(snippet)

    if heuristic_like / len(features) > 0.4:
        return "degraded"

    if web_presence_snippet_len is not None and web_presence_snippet_len < 200:
        return "degraded"

    return "good"
