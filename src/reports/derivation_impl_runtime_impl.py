"""
Pure helpers that turn a SQLite run snapshot into the flat context a Jinja2
template can render without further data access. No I/O — tested in isolation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

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
from src.reports.derivation_support import (
    _badge_type_from_band,
    _build_evidence,
    _cost_policy_from_snapshot,
    _dedupe_report_evidence,
    _DIMENSION_LABELS,
    _DIMENSION_ORDER,
    _EVIDENCE_KEYS,
    _extract_domain,
    _first_nonempty,
    _group_sources,
    _host_suffix_match,
    _infer_source_type,
    _load_dimension_labels,
    _parse_json_list,
    _report_evidence_items_by_dimension,
    _SOURCE_GROUP_ORDER,
    SourceType,
    _unique,
    _verdict_from,
    _iter_feature_evidences,
)
from src.reports.derivation_readiness import (
    _annotate_readiness_diagnostics,
    _confidence_reason_labels,
    _context_readiness_from_snapshot,
    _effective_context_readiness_for_trust,
    _editorial_policy_from_readiness,
    _format_analysis_date,
    _owned_content_capture_from_snapshot,
    _presentation_policy_from_readiness,
    _readiness_inputs_from_snapshot,
    parse_raw_value,
    _as_str,
)


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
    known_dim_order = list(_DIMENSION_LABELS)
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
            "display_name": _DIMENSION_LABELS.get(dim_name, dim_name),
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
    owned_content_capture = _owned_content_capture_from_snapshot(
        snapshot,
        evidence_summary=evidence_summary,
    )
    context_readiness = {
        **context_readiness,
        "owned_content_capture": owned_content_capture,
    }
    effective_context_readiness = _effective_context_readiness_for_trust(
        context_readiness,
        owned_content_capture=owned_content_capture,
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
    persisted_readiness = ((snapshot.get("run") or {}).get("audit") or {}).get("report_readiness")
    if isinstance(persisted_readiness, dict):
        readiness = persisted_readiness
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
    executive_analysis_v2 = (
        audit.get("executive_analysis_v2")
        if isinstance(audit.get("executive_analysis_v2"), dict)
        else {}
    )
    executive_analysis_v2_translations = (
        audit.get("executive_analysis_v2_translations")
        if isinstance(audit.get("executive_analysis_v2_translations"), dict)
        else {}
    )

    runtime_seconds = run.get("run_duration_seconds")
    run_id = run.get("id")

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
    sources_grouped, all_sources = _group_sources(snapshot, collect_evidences)

    # Global band verdict.
    _, band_adjective = derive_verdict(composite)
    trust_summary = build_trust_summary(
        data_quality=data_quality,
        context_summary=effective_context_readiness,
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
            "owned_content_capture": owned_content_capture,
            "effective_context_readiness": effective_context_readiness,
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
            "executive_analysis_v2": executive_analysis_v2,
            "executive_analysis_v2_translations": executive_analysis_v2_translations,
            "runtime": (
                f"{runtime_seconds:.2f}s" if isinstance(runtime_seconds, (int, float)) else "n/a"
            ),
            "report_id": f"rpt_{run.get('id') or 0:06d}",
            "run_id": run_id,
        },
        "ui": {
            "theme": theme,
            "term_lines": term_lines,
            "show_readiness_diagnostic": (
                readiness.get("report_mode") != "publishable_brand_report"
            ),
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
        "owned_content_capture": evaluation.get("owned_content_capture") or {},
        "effective_context_readiness": evaluation.get("effective_context_readiness") or {},
        "evidence_summary": evaluation.get("evidence_summary") or {},
        "readiness": readiness,
        "editorial_policy": editorial_policy,
        "presentation_policy": presentation_policy,
        "cost_policy": evaluation.get("cost_policy") or {},
        "trust_summary": evaluation.get("trust_summary") or {},
        "executive_analysis_v2": audit.get("executive_analysis_v2") or {},
        "executive_analysis_v2_translations": audit.get("executive_analysis_v2_translations") or {},
        "narrative": narrative,
        "sources": sources,
        "audit": audit,
        "ui": ui,
    }


def build_report_context(snapshot: dict, theme: str = "dark") -> dict:
    """Backward-compatible wrapper used by existing tests and callers."""
    return build_report_context_from_base(build_report_base(snapshot, theme=theme))


def build_report_readiness_from_snapshot(snapshot: dict) -> dict:
    """Return the report readiness contract for a run snapshot."""
    return build_report_base(snapshot).get("evaluation", {}).get("readiness") or {}


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
                display_name=_DIMENSION_LABELS.get(name, name),
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
