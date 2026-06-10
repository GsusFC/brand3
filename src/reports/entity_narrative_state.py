"""Offline EntityNarrativeState builder for Brand3 report diagnostics.

This module is intentionally pure and offline. It compiles composition-state
signals from existing report narrative payloads and Narrative Harness
diagnostics. It does not call LLMs, mutate payloads, score, render, persist, or
participate in runtime report generation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse

VERSION = "entity_narrative_state.v0"

COUNT_LEVELS = (
    (0, "inactive"),
    (2, "low"),
    (7, "moderate"),
)


def build_entity_narrative_state(
    payload: dict,
    *,
    payload_diagnostic: dict | None = None,
    render_diagnostic: dict | None = None,
    snapshot: dict | None = None,
) -> dict:
    """Build a deterministic offline EntityNarrativeState candidate.

    The return value is a JSON-like dict. It is a diagnostic composition state,
    not report prose, scoring, rendering, or runtime behavior.
    """

    safe_payload = payload if isinstance(payload, dict) else {}
    safe_payload_diagnostic = payload_diagnostic if isinstance(payload_diagnostic, dict) else {}
    safe_render_diagnostic = render_diagnostic if isinstance(render_diagnostic, dict) else {}
    safe_snapshot = snapshot if isinstance(snapshot, dict) else {}

    findings = _flatten_findings(safe_payload.get("findings_by_dimension"))
    payload_metrics = _metrics_from_payload_diagnostic(safe_payload_diagnostic)
    visible_metrics = _metrics_from_render_diagnostic(safe_render_diagnostic)

    brand = _first_text(
        _nested_get(safe_snapshot, ("brand", "name")),
        safe_snapshot.get("brand_name"),
        safe_snapshot.get("brand"),
        _nested_get(safe_payload_diagnostic, ("input_metadata", "brand")),
        safe_payload.get("brand"),
    )
    url = _first_text(
        safe_snapshot.get("url"),
        safe_snapshot.get("target_url"),
        _nested_get(safe_snapshot, ("brand", "url")),
        safe_payload.get("url"),
    )
    primary = _primary_surface(url, findings)
    related_surfaces = _observed_related_surfaces(safe_snapshot, primary)
    finding_count = _int_metric(payload_metrics, "findings_count", len(findings))
    findings_without_urls = _int_metric(
        payload_metrics,
        "findings_without_evidence_urls",
        _count_findings_without_evidence(findings),
    )
    safe_attribution_phrase_counts = _dict_metric(
        payload_metrics,
        "safe_attribution_phrase_counts",
    )
    safe_attribution_total = _int_metric(
        payload_metrics,
        "safe_attribution_total",
        sum(safe_attribution_phrase_counts.values()),
    )
    observation_families = _dict_metric(
        payload_metrics,
        "observation_repetition_family_counts",
    )
    visible_observation_families = _dict_metric(
        visible_metrics,
        "observation_repetition_family_counts",
    )
    generic_phrase_counts = _dict_metric(payload_metrics, "generic_phrase_counts")
    sentence_opening_counts = _dict_metric(payload_metrics, "sentence_opening_counts")
    visible_repeated_openings = _dict_metric(
        visible_metrics,
        "repeated_sentence_opening_counts",
    )
    generic_decision_count = int(
        generic_phrase_counts.get("teams in this position typically", 0)
    )
    visible_decision_space_count = _int_metric(
        visible_metrics,
        "visible_decision_space_count",
        0,
    )

    state = {
        "primary_entity_signal": _primary_entity_signal(brand, url, primary),
        "entity_aliases": _entity_aliases(primary, related_surfaces),
        "owned_claim_density": _owned_claim_density(
            safe_attribution_total,
            safe_attribution_phrase_counts,
            bool(payload_metrics),
        ),
        "repeated_opener_budget": _repeated_opener_budget(
            sentence_opening_counts,
            visible_repeated_openings,
            bool(payload_metrics or visible_metrics),
        ),
        "fallback_language_budget": _fallback_language_budget(
            observation_families,
            visible_observation_families,
            bool(payload_metrics or visible_metrics),
        ),
        "evidence_url_coverage": _evidence_url_coverage(
            findings,
            finding_count,
            findings_without_urls,
            visible_metrics,
            bool(payload_metrics or findings),
        ),
        "decision_space_mode": _decision_space_mode(
            generic_decision_count,
            visible_decision_space_count,
            bool(visible_metrics),
        ),
    }

    source_summary = _source_ownership_summary(safe_snapshot, findings_without_urls)
    if source_summary:
        state["source_ownership_summary"] = source_summary

    attribution_budget = _attribution_budget(safe_attribution_total, bool(payload_metrics))
    if attribution_budget["status"] != "inactive":
        state["attribution_budget"] = attribution_budget

    caveat_budget = _corroboration_caveat_budget(
        observation_families,
        visible_observation_families,
        bool(payload_metrics or visible_metrics),
    )
    if caveat_budget["status"] != "inactive":
        state["corroboration_caveat_budget"] = caveat_budget

    primary_tension = _primary_tension(safe_payload)
    if primary_tension:
        state["primary_tension"] = primary_tension

    state["contradiction_candidates"] = []

    compression_candidates = _compression_candidates(
        findings,
        generic_decision_count,
        findings_without_urls,
        safe_attribution_total,
    )
    if compression_candidates:
        state["compression_candidates"] = compression_candidates

    return {
        "version": VERSION,
        "status": _status(),
        "metadata": {
            "brand": brand or "unknown",
            "url": url or "unknown",
            "generated_at": "deterministic_offline_builder_v0",
            "created_from": [
                "report_narrative_payload",
                "payload_level_narrative_harness_diagnostic",
                "render_aware_narrative_harness_diagnostic",
                "optional_snapshot_or_base_dossier_metadata",
            ],
            "case_family": _case_family(state),
        },
        "inputs": {
            "report_narrative_payload": _input_record(True, safe_payload.get("source")),
            "payload_diagnostic": _input_record(bool(payload_metrics), safe_payload_diagnostic.get("status")),
            "render_aware_diagnostic": _input_record(bool(visible_metrics), safe_render_diagnostic.get("status")),
            "snapshot_or_base_dossier": _input_record(bool(safe_snapshot), safe_snapshot.get("source")),
        },
        "state": state,
        "derivation": _derivation_notes(),
        "limitations": _limitations(safe_snapshot, payload_metrics, visible_metrics),
    }


def _status() -> dict[str, bool]:
    return {
        "experimental": True,
        "offline_only": True,
        "runtime_enabled": False,
        "used_by_scoring": False,
        "used_by_prompts": False,
        "used_by_rendering": False,
        "persisted_report_narrative": False,
        "llm_generated": False,
    }


def _input_record(available: bool, source_id: Any = None) -> dict[str, Any]:
    return {
        "available": available,
        "source_id": str(source_id) if source_id else "unknown",
        "notes": "used for deterministic offline state compilation" if available else "not provided",
    }


def _flatten_findings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    findings: list[dict[str, Any]] = []
    for dimension, raw_items in value.items():
        if not isinstance(raw_items, list):
            continue
        for index, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            evidence_urls = [
                str(url).strip()
                for url in (item.get("evidence_urls") or [])
                if isinstance(url, str) and url.strip()
            ]
            findings.append(
                {
                    "dimension": str(dimension),
                    "index": index,
                    "title": _text(item.get("title")),
                    "observation": _text(item.get("observation") or item.get("prose")),
                    "implication": _text(item.get("implication")),
                    "typical_decision": _text(item.get("typical_decision")),
                    "evidence_urls": evidence_urls,
                }
            )
    return findings


def _metrics_from_payload_diagnostic(value: dict[str, Any]) -> dict[str, Any]:
    metrics = value.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _metrics_from_render_diagnostic(value: dict[str, Any]) -> dict[str, Any]:
    metrics = value.get("visible_render_metrics")
    return metrics if isinstance(metrics, dict) else {}


def _primary_entity_signal(brand: str | None, url: str | None, primary: str) -> dict[str, Any]:
    label = brand or primary or "unknown"
    explicit_sources = [source for source in (url, primary) if source]
    has_explicit_anchor = bool(brand or url or primary)
    return {
        "label": label,
        "confidence": "medium" if has_explicit_anchor else "unknown",
        "supporting_sources": explicit_sources,
        "uncertainty": (
            "Entity anchor derived from explicit metadata or evidence URL domain only."
            if has_explicit_anchor
            else "No explicit entity metadata or URL was available."
        ),
        "requires_human_review": True,
    }


def _entity_aliases(primary: str, related_surfaces: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "primary": primary or "unknown",
        "observed_related_surfaces": related_surfaces,
        "needs_review": any(
            surface.get("requires_human_review") is True for surface in related_surfaces
        ),
        "confidence": "medium" if primary else "unknown",
    }


def _owned_claim_density(total: int, phrase_counts: dict[str, int], has_metrics: bool) -> dict[str, Any]:
    return {
        "level": _count_level(total) if has_metrics else "unknown",
        "safe_attribution_total": total,
        "phrase_counts": phrase_counts,
        "source": "payload_diagnostic.metrics.safe_attribution_*" if has_metrics else "unknown",
    }


def _repeated_opener_budget(
    payload_openings: dict[str, int],
    visible_openings: dict[str, int],
    has_metrics: bool,
) -> dict[str, Any]:
    observed = dict(Counter(payload_openings) + Counter(visible_openings))
    tracked = {
        phrase: count
        for phrase, count in sorted(observed.items())
        if count >= 3
    }
    status = "unknown"
    if has_metrics:
        status = "over_budget" if tracked else "within_budget"
    return {
        "status": status,
        "max_same_opening": 2,
        "tracked_openings": list(tracked.keys()),
        "observed_counts": tracked,
        "source": "payload_and_render_diagnostics" if has_metrics else "unknown",
    }


def _fallback_language_budget(
    payload_families: dict[str, Any],
    visible_families: dict[str, Any],
    has_metrics: bool,
) -> dict[str, Any]:
    family = _merge_family(
        payload_families.get("fallback_evidence_opening_repetition"),
        visible_families.get("fallback_evidence_opening_repetition"),
    )
    total = int(family.get("total", 0))
    mode = "unknown"
    if has_metrics:
        mode = "fallback_like_repetition" if total else "inactive"
    return {
        "mode": mode,
        "fallback_mode": False,
        "fallback_like_repetition": total > 0,
        "phrase_counts": family.get("phrases", {}),
        "source": "observation_repetition_family_metrics" if has_metrics else "unknown",
    }


def _evidence_url_coverage(
    findings: list[dict[str, Any]],
    finding_count: int,
    findings_without_urls: int,
    visible_metrics: dict[str, Any],
    has_source: bool,
) -> dict[str, Any]:
    covered = max(finding_count - findings_without_urls, 0)
    ratio = covered / finding_count if finding_count else None
    affected = sorted(
        {
            finding["dimension"]
            for finding in findings
            if not finding.get("evidence_urls")
        }
    )
    return {
        "finding_count": finding_count,
        "findings_without_evidence_urls": findings_without_urls,
        "coverage_level": _coverage_level(ratio) if has_source else "unknown",
        "visible_evidence_link_count": _int_metric(
            visible_metrics,
            "visible_evidence_chip_link_count",
            0,
        ),
        "affected_dimensions": affected,
        "source": "payload_and_render_diagnostics" if has_source else "unknown",
    }


def _decision_space_mode(
    generic_decision_count: int,
    visible_decision_space_count: int,
    has_render_metrics: bool,
) -> dict[str, Any]:
    if generic_decision_count <= 0 and visible_decision_space_count <= 0:
        mode = "not_applicable_empty"
    elif generic_decision_count >= 3 and visible_decision_space_count == 0:
        mode = "hidden_generic"
    elif generic_decision_count >= 3:
        mode = "compressed_candidate"
    elif visible_decision_space_count > 0:
        mode = "show"
    else:
        mode = "unknown"
    return {
        "mode": mode,
        "generic_decision_count": generic_decision_count,
        "visible_decision_space_count": visible_decision_space_count,
        "render_suppression_observed": has_render_metrics and generic_decision_count > visible_decision_space_count,
        "advisory_only": True,
    }


def _source_ownership_summary(
    snapshot: dict[str, Any],
    findings_without_urls: int,
) -> dict[str, Any] | None:
    owned = _first_int(
        snapshot.get("owned_evidence_total"),
        _nested_get(snapshot, ("discovery", "owned_evidence_total")),
        _nested_get(snapshot, ("evidence", "owned")),
    )
    third_party = _first_int(
        snapshot.get("third_party_evidence_total"),
        _nested_get(snapshot, ("discovery", "third_party_evidence_total")),
        _nested_get(snapshot, ("evidence", "third_party")),
    )
    evidence_total = _first_int(
        snapshot.get("evidence_total"),
        _nested_get(snapshot, ("discovery", "evidence_total")),
        _nested_get(snapshot, ("evidence", "total")),
    )
    if owned is None and third_party is None and evidence_total is None and findings_without_urls == 0:
        return None
    return {
        "method": "metrics_from_snapshot" if any(value is not None for value in (owned, third_party, evidence_total)) else "unknown",
        "owned_or_self_description": {
            "count_estimate": owned if owned is not None else "unknown",
            "confidence": "medium" if owned is not None else "unknown",
            "sources": [],
            "notes": "Used only when explicit snapshot evidence totals are provided.",
        },
        "third_party_or_external_assessment": {
            "count_estimate": third_party if third_party is not None else "unknown",
            "confidence": "medium" if third_party is not None else "unknown",
            "sources": [],
            "notes": "Used only when explicit snapshot evidence totals are provided.",
        },
        "technical_or_configuration": {
            "count_estimate": "unknown",
            "confidence": "unknown",
            "sources": [],
            "notes": "No source classifier is implemented in v0.",
        },
        "uncited_or_missing_evidence_url": {
            "count_estimate": findings_without_urls,
            "confidence": "high",
            "sources": [],
            "notes": "Derived from finding-level evidence URL coverage.",
        },
    }


def _attribution_budget(total: int, has_metrics: bool) -> dict[str, Any]:
    if not has_metrics or total == 0:
        status = "inactive"
    elif total > 2:
        status = "over_budget"
    else:
        status = "within_budget"
    return {
        "status": status,
        "max_repeated_safe_attribution": 2,
        "observed_safe_attribution_total": total,
        "global_caveat_preferred": status == "over_budget",
        "source": "payload_diagnostic.metrics.safe_attribution_total" if has_metrics else "unknown",
    }


def _corroboration_caveat_budget(
    payload_families: dict[str, Any],
    visible_families: dict[str, Any],
    has_metrics: bool,
) -> dict[str, Any]:
    family = _merge_family(
        payload_families.get("external_corroboration_caveat_repetition"),
        visible_families.get("external_corroboration_caveat_repetition"),
    )
    total = int(family.get("total", 0))
    if not has_metrics or total == 0:
        status = "inactive"
    elif total > 2:
        status = "over_budget"
    else:
        status = "within_budget"
    return {
        "status": status,
        "observed_caveat_total": total,
        "global_caveat_preferred": status == "over_budget",
        "phrase_counts": family.get("phrases", {}),
        "source": "observation_repetition_family_metrics" if has_metrics else "unknown",
    }


def _primary_tension(payload: dict[str, Any]) -> dict[str, Any] | None:
    tension = _text(payload.get("tensions_prose"))
    if not tension:
        return None
    return {
        "summary": tension,
        "source": "payload_tension",
        "confidence": "low",
        "requires_human_review": True,
    }


def _compression_candidates(
    findings: list[dict[str, Any]],
    generic_decision_count: int,
    findings_without_urls: int,
    safe_attribution_total: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if generic_decision_count >= 3:
        candidates.append(
            {
                "finding_id": "typical_decision",
                "reason": "generic decision-space phrase exceeds v0 budget",
                "suggested_only": True,
            }
        )
    if safe_attribution_total >= 3:
        candidates.append(
            {
                "finding_id": "safe_attribution",
                "reason": "safe attribution repetition exceeds v0 budget",
                "suggested_only": True,
            }
        )
    if findings_without_urls:
        dimensions = sorted(
            {
                finding["dimension"]
                for finding in findings
                if not finding.get("evidence_urls")
            }
        )
        candidates.append(
            {
                "finding_id": "evidence_url_coverage",
                "reason": f"{findings_without_urls} findings lack evidence URLs",
                "affected_dimensions": dimensions,
                "suggested_only": True,
            }
        )
    return candidates


def _derivation_notes() -> dict[str, Any]:
    return {
        "deterministic_counts": [
            "findings",
            "findings_without_evidence_urls",
            "safe_attribution_phrase_counts",
            "repeated_opening_counts",
            "observation_repetition_family_counts",
            "generic_decision_space_phrase_counts",
            "visible_evidence_link_counts",
        ],
        "estimated_fields_require": ["method", "confidence", "notes"],
        "unknown_policy": "preserve uncertainty rather than filling fields for completeness",
        "never_infer": [
            "strategic intention",
            "audience psychology",
            "market archetype",
            "entity ownership from name similarity",
            "visual confidence as evidentiary confidence",
            "report prose rewrites",
        ],
    }


def _limitations(
    snapshot: dict[str, Any],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
) -> list[str]:
    limitations = [
        "Offline diagnostic state only; not used by runtime, scoring, prompts, rendering, or persisted report payloads.",
        "Review-gated fields are not promoted to facts.",
    ]
    if not snapshot:
        limitations.append("No snapshot/base dossier metadata was provided; source ownership remains limited or unknown.")
    if not payload_metrics:
        limitations.append("No payload-level diagnostic metrics were provided; metric-derived fields may be unknown.")
    if not visible_metrics:
        limitations.append("No render-aware diagnostic metrics were provided; visible-render state may be unknown.")
    return limitations


def _case_family(state: dict[str, Any]) -> str:
    aliases = state["entity_aliases"]["observed_related_surfaces"]
    owned = state["owned_claim_density"]["level"]
    fallback = state["fallback_language_budget"]["mode"]
    if aliases:
        return "multi_surface_or_entity_review"
    if owned in {"moderate", "high"}:
        return "owned_claim_repetition"
    if fallback == "fallback_like_repetition":
        return "fallback_language_repetition"
    return "baseline_or_low_pressure"


def _count_level(value: int) -> str:
    if value == 0:
        return "inactive"
    if value <= 2:
        return "low"
    if value <= 7:
        return "moderate"
    return "high"


def _coverage_level(ratio: float | None) -> str:
    if ratio is None:
        return "unknown"
    if ratio >= 0.8:
        return "strong"
    if ratio >= 0.4:
        return "mixed"
    return "weak"


def _merge_family(first: Any, second: Any) -> dict[str, Any]:
    total = 0
    phrases: Counter[str] = Counter()
    for item in (first, second):
        if not isinstance(item, dict):
            continue
        total = max(total, _coerce_int(item.get("total"), 0))
        raw_phrases = item.get("phrases")
        if isinstance(raw_phrases, dict):
            for phrase, count in raw_phrases.items():
                phrases[str(phrase)] = max(phrases[str(phrase)], _coerce_int(count, 0))
    return {"total": total, "phrases": dict(phrases)}


def _observed_related_surfaces(
    snapshot: dict[str, Any],
    primary: str,
) -> list[dict[str, Any]]:
    raw_surfaces = snapshot.get("observed_related_surfaces")
    if not raw_surfaces:
        raw_surfaces = _nested_get(snapshot, ("entity_resolution", "related_surfaces"))
    if not isinstance(raw_surfaces, list):
        return []

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in raw_surfaces:
        normalized = _normalize_related_surface(item)
        if not normalized:
            continue
        surface = normalized["surface"]
        if surface == primary or surface in seen:
            continue
        seen.add(surface)
        out.append(normalized)
    return out[:20]


def _normalize_related_surface(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    surface = _surface(_text(value.get("surface")))
    if not surface:
        return None
    relation_type = _text(value.get("relation_type")) or "unknown"
    confidence = _text(value.get("confidence")) or "unknown"
    source = _text(value.get("source")) or "unknown"
    evidence = value.get("evidence")
    normalized: dict[str, Any] = {
        "surface": surface,
        "relation_type": relation_type,
        "evidence": [
            str(item).strip()
            for item in evidence
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(evidence, list)
        else [],
        "confidence": confidence,
        "requires_human_review": value.get("requires_human_review") is True,
        "source": source,
    }
    notes = _text(value.get("notes"))
    if notes:
        normalized["notes"] = notes
    return normalized


def _primary_surface(url: str | None, findings: list[dict[str, Any]]) -> str:
    if url:
        domain = _domain(url)
        if domain:
            return domain
    for evidence_url in _evidence_urls(findings):
        domain = _domain(evidence_url)
        if domain:
            return domain
    return "unknown"


def _evidence_urls(findings: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for finding in findings:
        urls.extend(finding.get("evidence_urls") or [])
    return urls


def _count_findings_without_evidence(findings: list[dict[str, Any]]) -> int:
    return sum(1 for finding in findings if not finding.get("evidence_urls"))


def _surface(value: str) -> str:
    if "://" in value:
        return _domain(value)
    return value.strip().lower().removeprefix("www.")


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.")


def _dict_metric(metrics: dict[str, Any], key: str) -> dict[str, Any]:
    value = metrics.get(key)
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        if isinstance(raw_value, dict):
            out[str(raw_key)] = raw_value
        else:
            out[str(raw_key)] = _coerce_int(raw_value, 0)
    return out


def _int_metric(metrics: dict[str, Any], key: str, default: int) -> int:
    return _coerce_int(metrics.get(key), default)


def _coerce_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _first_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _text(value)
        if text:
            return text
    return None


def _text(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) and value.strip() else ""


def _nested_get(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
