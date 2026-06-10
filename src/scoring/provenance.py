"""Read-only score provenance reporting.

This module composes persisted scoring output, replay integrity, reviewed
scores, and feature-level provenance into a single audit-friendly structure.
It does not mutate persisted state and it does not change scoring formulas.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict
from typing import Any

from src.reports.derivation import build_report_base
from src.storage.sqlite_store import SQLiteStore

from .replay import build_score_replay_audit


def build_score_provenance_report(store: SQLiteStore, run_id: int) -> dict[str, Any]:
    snapshot = store.get_run_snapshot(run_id)
    replay = build_score_replay_audit(store, run_id)
    reviewed_score = store.get_reviewed_score(run_id)
    base = build_report_base(snapshot) if snapshot else None

    computed_composite_score = replay.get("persisted_composite")
    if computed_composite_score is None and base:
        computed_composite_score = base.get("evaluation", {}).get("composite_score")

    reviewed_composite_score = (
        reviewed_score.get("reviewed_composite_score")
        if isinstance(reviewed_score, dict)
        else None
    )

    replay_status = str(replay.get("score_integrity") or "unverifiable")
    replay_integrity = {
        "status": replay_status,
        "fingerprint_status": replay.get("fingerprint_status"),
        "drift_type": replay.get("drift_type"),
        "score_values_match_persisted_data": replay.get("score_values_match_persisted_data"),
        "recommended_action": replay.get("recommended_action"),
        "persisted_scoring_state_fingerprint": replay.get("persisted_scoring_state_fingerprint"),
        "current_scoring_state_fingerprint": replay.get("current_scoring_state_fingerprint"),
        "issues": replay.get("issues") or [],
    }

    display_score_source = _display_score_source(
        replay_status,
        computed_composite_score,
        reviewed_composite_score,
    )
    recommended_display_score = _recommended_display_score(
        display_score_source,
        computed_composite_score,
        reviewed_composite_score,
    )

    dimension_breakdown = _dimension_breakdown(base, replay)
    feature_provenance_summary = _feature_provenance_summary(base)
    confidence_summary = _confidence_summary(base)
    fallback_flags = _fallback_flags(base, replay)
    rules_applied = base.get("rules_applied") if base else []
    evidence_refs = _evidence_refs(base, reviewed_score)
    warnings = _warnings(replay, display_score_source, replay_status)
    recommended_action = _recommended_action(
        replay_status,
        replay.get("recommended_action"),
        warnings,
    )

    report = {
        "run_id": run_id,
        "computed_composite_score": computed_composite_score,
        "replay_integrity": replay_integrity,
        "reviewed_score": reviewed_score,
        "recommended_display_score": recommended_display_score,
        "display_score_source": display_score_source,
        "dimension_breakdown": dimension_breakdown,
        "feature_provenance_summary": feature_provenance_summary,
        "confidence_summary": confidence_summary,
        "fallback_flags": fallback_flags,
        "rules_applied": rules_applied,
        "evidence_refs": evidence_refs,
        "warnings": warnings,
        "recommended_action": recommended_action,
    }
    if base:
        report["report_readiness"] = base.get("evaluation", {}).get("readiness") or {}
        report["trust_summary"] = base.get("evaluation", {}).get("trust_summary") or {}
    return report


def _display_score_source(
    replay_status: str,
    computed_composite_score: float | None,
    reviewed_composite_score: float | None,
) -> str:
    if replay_status == "drift_detected":
        return "blocked"
    if computed_composite_score is None and reviewed_composite_score is None:
        return "blocked"
    if reviewed_composite_score is not None:
        return "reviewed"
    return "computed"


def _recommended_display_score(
    display_score_source: str,
    computed_composite_score: float | None,
    reviewed_composite_score: float | None,
) -> float | None:
    if display_score_source == "blocked":
        return None
    if display_score_source == "reviewed":
        return reviewed_composite_score
    return computed_composite_score


def _dimension_breakdown(
    base: dict[str, Any] | None,
    replay: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not base:
        return {}

    replay_dimensions = replay.get("dimensions") or {}
    rules_by_dimension = defaultdict(list)
    for rule_item in base.get("rules_applied") or []:
        dimension_name = rule_item.get("dimension")
        rule = rule_item.get("rule")
        if dimension_name and rule:
            rules_by_dimension[dimension_name].append(rule)

    breakdown: dict[str, dict[str, Any]] = OrderedDict()
    for dim in base.get("dimensions") or []:
        name = dim.get("name")
        if not name:
            continue
        replay_dim = replay_dimensions.get(name) or {}
        evidence = dim.get("evidence") or []
        features = dim.get("features") or []
        breakdown[name] = {
            "score": dim.get("score"),
            "band_letter": dim.get("band_letter"),
            "band_label": dim.get("band_label"),
            "confidence": dim.get("confidence"),
            "confidence_label": dim.get("confidence_label"),
            "confidence_status": dim.get("confidence_status"),
            "coverage": dim.get("coverage"),
            "coverage_label": dim.get("coverage_label"),
            "missing_signals": dim.get("missing_signals") or [],
            "recommended_next_steps": dim.get("recommended_next_steps") or [],
            "feature_count": len(features),
            "evidence_count": len(evidence),
            "feature_sources": sorted(
                {
                    str(feature.get("source") or "")
                    for feature in features
                    if str(feature.get("source") or "").strip()
                }
            ),
            "evidence": evidence,
            "rules_applied": list(rules_by_dimension.get(name) or []),
            "replay": {
                "persisted": replay_dim.get("persisted"),
                "artifact": replay_dim.get("artifact"),
                "recomputed": replay_dim.get("recomputed"),
                "unavailable": bool(replay_dim.get("unavailable")),
                "feature_count": replay_dim.get("feature_count"),
            },
        }
    return breakdown


def _feature_provenance_summary(base: dict[str, Any] | None) -> dict[str, Any]:
    if not base:
        return {}

    summary: dict[str, Any] = {}
    for dim in base.get("dimensions") or []:
        dim_name = dim.get("name")
        if not dim_name:
            continue
        features = dim.get("features") or []
        evidence = dim.get("evidence") or []
        summary[dim_name] = {
            "feature_count": len(features),
            "evidence_count": len(evidence),
            "feature_names": [
                feature.get("name")
                for feature in features
                if feature.get("name")
            ],
            "sources": sorted(
                {
                    str(feature.get("source") or "")
                    for feature in features
                    if str(feature.get("source") or "").strip()
                }
            ),
        }
    return summary


def _confidence_summary(base: dict[str, Any] | None) -> dict[str, Any]:
    if not base:
        return {}

    summary: dict[str, Any] = {}
    for dim in base.get("dimensions") or []:
        dim_name = dim.get("name")
        if not dim_name:
            continue
        summary[dim_name] = {
            "confidence": dim.get("confidence"),
            "confidence_label": dim.get("confidence_label"),
            "confidence_status": dim.get("confidence_status"),
            "coverage": dim.get("coverage"),
            "coverage_label": dim.get("coverage_label"),
            "confidence_reason": dim.get("confidence_reason") or [],
            "confidence_reason_labels": dim.get("confidence_reason_labels") or [],
            "missing_signals": dim.get("missing_signals") or [],
            "recommended_next_steps": dim.get("recommended_next_steps") or [],
        }
    return summary


def _fallback_flags(base: dict[str, Any] | None, replay: dict[str, Any]) -> dict[str, Any]:
    fallback_flags: dict[str, Any] = {
        "replay_unavailable_dimensions": [],
        "replay_neutral_fallback_dimensions": [],
        "readiness_fallback_dimensions": [],
        "missing_high_weight_features": {},
    }

    if base:
        readiness = base.get("evaluation", {}).get("readiness") or {}
        fallback_detected = readiness.get("fallback_detected") or {}
        fallback_flags["readiness_fallback_dimensions"] = sorted(fallback_detected.keys())
        fallback_flags["missing_high_weight_features"] = (
            readiness.get("missing_high_weight_features") or {}
        )

    dimensions = replay.get("dimensions") or {}
    fallback_flags["replay_unavailable_dimensions"] = sorted(
        [name for name, data in dimensions.items() if data.get("unavailable")]
    )
    fallback_flags["replay_neutral_fallback_dimensions"] = sorted(
        {
            str(issue.get("dimension"))
            for issue in replay.get("issues") or []
            if issue.get("code") == "neutral_fallback_dimension" and issue.get("dimension")
        }
    )
    return fallback_flags


def _evidence_refs(
    base: dict[str, Any] | None,
    reviewed_score: dict[str, Any] | None,
) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()

    def add(ref: str | None) -> None:
        ref_text = str(ref or "").strip()
        if not ref_text or ref_text in seen:
            return
        seen.add(ref_text)
        refs.append(ref_text)

    if base:
        for dim in base.get("dimensions") or []:
            for item in dim.get("evidence") or []:
                add(item.get("source_url") or item.get("quote") or item.get("signal"))

    if reviewed_score:
        for ref in reviewed_score.get("evidence_refs") or []:
            add(ref)

    return refs


def _warnings(
    replay: dict[str, Any],
    display_score_source: str,
    replay_status: str,
) -> list[dict[str, Any]]:
    warnings = [issue for issue in (replay.get("issues") or [])]
    if replay_status == "drift_detected":
        warnings.append(
            {
                "code": "display_blocked_due_to_drift",
                "message": "Final score display is blocked because replay integrity is drift_detected.",
                "severity": "error",
            }
        )
    elif replay_status == "unverifiable":
        warnings.append(
            {
                "code": "display_limited_confidence",
                "message": "Replay integrity is unverifiable; display should be treated as limited confidence.",
                "severity": "warning",
            }
        )
    elif display_score_source == "reviewed":
        warnings.append(
            {
                "code": "reviewed_score_display",
                "message": "A reviewed score is available and is used for display.",
                "severity": "info",
            }
        )
    return warnings


def _recommended_action(
    replay_status: str,
    replay_action: str | None,
    warnings: list[dict[str, Any]],
) -> str:
    if replay_status == "drift_detected":
        return "technical_review"
    if replay_status == "unverifiable":
        return "config_check"
    if any(issue.get("severity") == "error" for issue in warnings):
        return "technical_review"
    if replay_action:
        return str(replay_action)
    return "none"
