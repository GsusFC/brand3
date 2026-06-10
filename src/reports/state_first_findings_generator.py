"""Lab-only state-first findings generator candidate.

This module is deliberately offline. It creates diagnostic candidate artifacts
for state-first narrative research. It does not score, render, persist, mutate
report payloads, call LLMs, or participate in runtime report generation.
"""

from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlparse

VERSION = "state_first_findings_generator.v0"
NO_CANDIDATE = "No safe state-first generation candidate."


def generate_state_first_findings_candidate(
    payload: dict,
    *,
    payload_diagnostic: dict,
    render_diagnostic: dict,
    entity_state: dict,
    snapshot: dict | None = None,
) -> dict:
    """Build a lab-only state-first findings candidate artifact.

    The function is deterministic around safety checks and intervention mode.
    The produced findings are research candidates, not report prose.
    """

    safe_payload = payload if isinstance(payload, dict) else {}
    safe_payload_diagnostic = payload_diagnostic if isinstance(payload_diagnostic, dict) else {}
    safe_render_diagnostic = render_diagnostic if isinstance(render_diagnostic, dict) else {}
    safe_entity_state = entity_state if isinstance(entity_state, dict) else {}
    safe_snapshot = snapshot if isinstance(snapshot, dict) else {}

    findings = _flatten_findings(safe_payload.get("findings_by_dimension"))
    payload_metrics = _metrics_from_payload_diagnostic(safe_payload_diagnostic)
    visible_metrics = _metrics_from_render_diagnostic(safe_render_diagnostic)
    state_body = _state_body(safe_entity_state)

    preconditions_passed, preconditions_failed = _preconditions(
        safe_payload,
        findings,
        payload_metrics,
        visible_metrics,
        safe_entity_state,
        state_body,
    )
    mode, reason = _select_mode(findings, payload_metrics, visible_metrics, state_body, preconditions_failed)
    candidate_available = mode in {"light", "strong"} and not preconditions_failed
    pressure_profile = _pressure_profile(findings, payload_metrics, visible_metrics, state_body)
    intervention_reasons = _intervention_reasons(
        mode,
        findings,
        payload_metrics,
        visible_metrics,
        state_body,
        pressure_profile,
        preconditions_failed,
    )

    blocked_reasons = list(preconditions_failed)
    if mode == "none" and reason not in blocked_reasons:
        blocked_reasons.append(reason)

    baseline = _baseline_summary(findings, payload_metrics, visible_metrics)
    evidence_map = _shared_evidence_map(findings)
    uncertainty_model = _global_uncertainty_model(mode, state_body, evidence_map)
    planning_profile = _planning_profile(mode, state_body, pressure_profile)
    finding_plan = _finding_plan(
        mode,
        state_body,
        payload_metrics,
        visible_metrics,
        planning_profile,
    )
    generated = (
        _generated_candidate_findings(mode, findings, evidence_map, state_body, planning_profile)
        if candidate_available
        else None
    )

    return {
        "version": VERSION,
        "created_at": "deterministic_offline_generator_v0",
        "case_id": _case_id(safe_payload, safe_snapshot, safe_entity_state),
        "status": _status(),
        "input_artifacts": _input_artifacts(
            safe_payload,
            safe_payload_diagnostic,
            safe_render_diagnostic,
            safe_entity_state,
            safe_snapshot,
        ),
        "generation_decision": {
            "mode": mode,
            "candidate_available": candidate_available,
            "reason": reason,
            "blocked_reasons": blocked_reasons,
            "preconditions_passed": preconditions_passed,
            "preconditions_failed": preconditions_failed,
            "intervention_reasons": intervention_reasons,
            "pressure_profile": pressure_profile,
        },
        "baseline": baseline,
        "shared_entity_state": _shared_entity_state(state_body),
        "shared_evidence_map": evidence_map,
        "global_uncertainty_model": uncertainty_model,
        "state_first_finding_plan": finding_plan,
        "generated_state_first_findings": generated,
        "comparison": _comparison(mode, baseline, state_body),
        "verdict": _verdict(mode, candidate_available, blocked_reasons),
    }


def _status() -> dict[str, bool]:
    return {
        "lab_only": True,
        "runtime_integration": False,
        "prompt_rollout": False,
        "scoring_change": False,
        "renderer_change": False,
        "report_mutation": False,
        "visual_signature_change": False,
        "production_ready": False,
    }


def _input_artifacts(
    payload: dict[str, Any],
    payload_diagnostic: dict[str, Any],
    render_diagnostic: dict[str, Any],
    entity_state: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_narrative_payload": _input_record(bool(payload), payload.get("source")),
        "payload_diagnostic": _input_record(bool(payload_diagnostic), payload_diagnostic.get("status")),
        "render_diagnostic": _input_record(bool(render_diagnostic), render_diagnostic.get("status")),
        "entity_narrative_state": _input_record(bool(entity_state), entity_state.get("version")),
        "snapshot_metadata": _input_record(bool(snapshot), snapshot.get("source")),
    }


def _input_record(available: bool, source_id: Any) -> dict[str, Any]:
    return {
        "available": available,
        "source_id": str(source_id) if source_id else "unknown",
    }


def _preconditions(
    payload: dict[str, Any],
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    entity_state: dict[str, Any],
    state_body: dict[str, Any],
) -> tuple[list[str], list[str]]:
    checks = {
        "report_narrative_payload_exists": bool(payload),
        "at_least_one_finding_exists": bool(findings),
        "payload_diagnostic_exists_or_can_be_built_offline": bool(payload_metrics),
        "render_diagnostic_exists_or_can_be_built_offline": bool(visible_metrics),
        "entity_narrative_state_exists": bool(entity_state),
        "entity_narrative_state_status_is_offline_lab_only": _is_offline_state(entity_state),
        "meaningful_evidence_map_can_be_built": _has_meaningful_evidence_map(findings),
        "unresolved_ambiguity_is_explicit_not_inferred": _ambiguity_is_explicit_or_absent(state_body),
        "related_surfaces_are_explicit_or_reviewed": _related_surfaces_are_reviewed(state_body),
        "every_generated_finding_can_state_an_evidence_boundary": bool(findings),
    }
    passed = [name for name, ok in checks.items() if ok]
    failed = [name for name, ok in checks.items() if not ok]
    return passed, failed


def _select_mode(
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    state: dict[str, Any],
    failed: list[str],
) -> tuple[str, str]:
    if failed:
        return "none", NO_CANDIDATE

    if _strong_pressure(state, payload_metrics, visible_metrics):
        return "strong", "baseline risks false coherence or unresolved entity ambiguity"

    if _light_pressure(findings, payload_metrics, visible_metrics, state):
        return "light", "state-first can improve evidence boundaries without heavy rewrite"

    return "none", "baseline appears coherent enough; only stylistic improvement is available"


def _strong_pressure(
    state: dict[str, Any],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
) -> bool:
    aliases = _dict(state.get("entity_aliases"))
    related = _related_surfaces(state)
    if isinstance(related, list) and related:
        return True
    if aliases.get("needs_review") is True:
        return True
    contradictions = state.get("contradiction_candidates")
    if isinstance(contradictions, list) and contradictions:
        return True
    return False


def _light_pressure(
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    state: dict[str, Any],
) -> bool:
    if _findings_without_urls(payload_metrics, findings) > 0:
        return True
    if _fallback_total(payload_metrics, visible_metrics) > 0:
        return True
    if _safe_attribution_total(payload_metrics) > 0:
        return True
    decision = _dict(state.get("decision_space_mode"))
    return str(decision.get("mode") or decision.get("recommended_mode") or "") in {
        "hidden_generic",
        "compressed_candidate",
    }


def _pressure_profile(
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, str]:
    aliases = _dict(state.get("entity_aliases"))
    related = _related_surfaces(state)
    related_count = len(related) if isinstance(related, list) else 0
    entity_needs_review = aliases.get("needs_review") is True
    primary_signal = _dict(state.get("primary_entity_signal"))
    primary_text = " ".join(
        _text(value)
        for value in (
            primary_signal.get("label"),
            primary_signal.get("uncertainty"),
        )
    ).lower()
    explicit_entity_boundary = entity_needs_review or any(
        token in primary_text for token in ("ambiguous", "mixed", "overlap")
    )
    findings_without = _findings_without_urls(payload_metrics, findings)
    finding_count = _int_metric(payload_metrics, "findings_count", len(findings))
    missing_ratio = findings_without / finding_count if finding_count else 0
    caveat_total = _caveat_total(payload_metrics, visible_metrics)
    fallback_total = _fallback_total(payload_metrics, visible_metrics)
    owned_total = _safe_attribution_total(payload_metrics)
    generic_decision_total = _generic_decision_count(payload_metrics)
    if generic_decision_total == 0:
        decision = _dict(state.get("decision_space_mode"))
        generic_decision_total = _coerce_int(
            decision.get("generic_decision_count")
            or _nested_get(decision, ("basis", "payload_teams_in_this_position_typically_count")),
            0,
        )
    visual_pressure = _visual_or_perceptual_pressure(state, findings)

    return {
        "entity_boundary": "high" if explicit_entity_boundary else "inactive",
        "related_surface_pressure": _count_pressure(related_count, low=1, medium=3, high=5),
        "evidence_binding": _ratio_pressure(missing_ratio),
        "caveat_inflation": _count_pressure(caveat_total, low=1, medium=4, high=10),
        "fallback_repetition": _count_pressure(fallback_total, low=1, medium=4, high=8),
        "owned_claim_repetition": _count_pressure(owned_total, low=1, medium=4, high=10),
        "generic_decision_space": _count_pressure(generic_decision_total, low=1, medium=4, high=8),
        "visual_or_perceptual_overreach": visual_pressure,
        "healthy_case_restraint": _healthy_case_restraint(
            explicit_entity_boundary,
            related_count,
            caveat_total,
            fallback_total,
            owned_total,
            findings_without,
            finding_count,
        ),
    }


def _intervention_reasons(
    mode: str,
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    state: dict[str, Any],
    profile: dict[str, str],
    failed: list[str],
) -> list[str]:
    if failed:
        return [f"blocked:{item}" for item in failed]

    reasons: list[str] = []
    if profile["entity_boundary"] in {"medium", "high"}:
        reasons.append("entity_boundary_risk")
    if profile["related_surface_pressure"] in {"low", "medium", "high"}:
        reasons.append("related_surface_review_required")
    if profile["owned_claim_repetition"] in {"medium", "high"}:
        reasons.append("owned_claim_repetition")
    if profile["caveat_inflation"] in {"medium", "high"}:
        reasons.append("external_corroboration_caveat_inflation")
    if profile["fallback_repetition"] in {"medium", "high"}:
        reasons.append("fallback_repetition")
    if profile["evidence_binding"] in {"low", "medium", "high"}:
        reasons.append("missing_finding_level_evidence")
    if profile["generic_decision_space"] in {"medium", "high"}:
        reasons.append("generic_decision_space")
    if profile["visual_or_perceptual_overreach"] in {"medium", "high"}:
        reasons.append("visual_or_perceptual_overreach")
    if mode == "light" and profile["healthy_case_restraint"] in {"medium", "high"}:
        reasons.append("stable_entity_restraint")
    if mode == "none":
        if _has_thin_payload(findings, payload_metrics):
            reasons.append("thin_payload_restraint")
        if not reasons:
            reasons.append("no_meaningful_state_first_gain")

    return _dedupe(reasons)


def _baseline_summary(
    findings: list[dict[str, Any]],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "findings_count": _int_metric(payload_metrics, "findings_count", len(findings)),
        "dimensions_present": sorted({finding["dimension"] for finding in findings}),
        "findings_without_evidence_urls": _findings_without_urls(payload_metrics, findings),
        "safe_attribution_total": _safe_attribution_total(payload_metrics),
        "external_corroboration_caveat_total": _caveat_total(payload_metrics, visible_metrics),
        "fallback_evidence_opening_total": _fallback_total(payload_metrics, visible_metrics),
        "generic_decision_space_count": _generic_decision_count(payload_metrics),
        "primary_failure": _primary_failure(payload_metrics, visible_metrics),
    }


def _shared_entity_state(state: dict[str, Any]) -> dict[str, Any]:
    aliases = _dict(state.get("entity_aliases"))
    related = _related_surfaces(state)
    return {
        "primary_entity_signal": state.get("primary_entity_signal") or "unknown",
        "entity_ambiguity_status": (
            "review_gated" if aliases.get("needs_review") is True else "not_explicit"
        ),
        "related_surfaces": related if isinstance(related, list) else [],
        "observed_related_surfaces": related if isinstance(related, list) else [],
        "owned_claim_density": state.get("owned_claim_density") or {},
        "evidence_url_coverage": state.get("evidence_url_coverage") or {},
        "active_budgets": _active_budgets(state),
        "primary_tension": state.get("primary_tension") or None,
    }


def _shared_evidence_map(findings: list[dict[str, Any]]) -> dict[str, Any]:
    urls = _evidence_urls(findings)
    domains = Counter(_domain(url) for url in urls if _domain(url))
    missing = [
        {
            "dimension": finding["dimension"],
            "title": finding["title"],
        }
        for finding in findings
        if not finding["evidence_urls"]
    ]
    return {
        "evidence_urls": sorted(set(urls)),
        "evidence_domains": dict(sorted(domains.items())),
        "findings_without_evidence_urls": missing,
        "evidence_that_must_not_be_overinterpreted": _overinterpretation_warnings(urls),
        "coverage_note": (
            "finding-level evidence gaps are present" if missing else "all findings include evidence URLs"
        ),
    }


def _global_uncertainty_model(
    mode: str,
    state: dict[str, Any],
    evidence_map: dict[str, Any],
) -> dict[str, Any]:
    aliases = _dict(state.get("entity_aliases"))
    has_related = bool(_related_surfaces(state))
    return {
        "can_state_as_observation": [
            "baseline findings and attached evidence URLs can be inspected",
            "finding-level evidence gaps can be counted",
            "payload and render diagnostics can identify repetition families",
        ],
        "can_state_as_interpretation": [
            "state-first may classify the case as none, light, or strong intervention",
            "state-first may centralize global caveats when diagnostics show repetition",
        ],
        "must_remain_uncertain": _uncertain_items(has_related, evidence_map),
        "requires_human_review": [
            "entity-related surfaces" if has_related else "none explicit in state",
        ],
        "must_not_infer": [
            "ownership from name similarity",
            "strategic intent from surface signals alone",
            "market validation from owned claims",
            "public reputation from isolated external trust pages",
            "visual confidence as evidentiary confidence",
        ],
        "mode_constraint": _mode_constraint(mode),
    }


def _finding_plan(
    mode: str,
    state: dict[str, Any],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    planning_profile: dict[str, str],
) -> dict[str, Any]:
    return {
        "mode": mode,
        "pressure_subtype": planning_profile["pressure_subtype"],
        "planning_focus": planning_profile["planning_focus"],
        "coordination_rules": _coordination_rules(
            mode,
            state,
            payload_metrics,
            visible_metrics,
            planning_profile,
        ),
        "dimension_roles": {
            "coherencia": "entity coherence and evidence-bound story consistency",
            "diferenciacion": "owned positioning versus externally supported differentiation",
            "percepcion": "visible perception signals without reputation inflation",
            "presencia": "owned and external surface footprint with entity boundaries",
            "vitalidad": "activity signals without growth or roadmap overclaiming",
        },
        "caveat_strategy": _caveat_strategy(planning_profile),
        "evidence_binding_strategy": _evidence_binding_strategy(planning_profile),
        "overreach_suppression_rules": [
            "no generic Decision Space",
            "no inferred ownership",
            "no inferred category leadership",
            "no synthetic depth for thin payloads",
            "no artificial tension for healthy cases",
            *_extra_overreach_rules(planning_profile),
        ],
    }


def _generated_candidate_findings(
    mode: str,
    findings: list[dict[str, Any]],
    evidence_map: dict[str, Any],
    state: dict[str, Any],
    planning_profile: dict[str, str],
) -> dict[str, Any]:
    global_caveat = _global_caveat(mode, state, evidence_map, planning_profile)
    by_dimension: dict[str, list[dict[str, Any]]] = {}
    for dimension in sorted({finding["dimension"] for finding in findings}):
        dimension_findings = [finding for finding in findings if finding["dimension"] == dimension]
        by_dimension[dimension] = [
            _candidate_from_baseline_finding(mode, item)
            for item in dimension_findings[:2]
        ]
    return {
        "generation_type": "deterministic_lab_candidate_skeleton",
        "global_caveat": global_caveat,
        "findings_by_dimension": by_dimension,
    }


def _candidate_from_baseline_finding(mode: str, finding: dict[str, Any]) -> dict[str, Any]:
    evidence_urls = finding["evidence_urls"]
    missing_note = None if evidence_urls else "No finding-level evidence URL is attached in the baseline payload."
    return {
        "dimension": finding["dimension"],
        "title": finding["title"] or "State-first candidate finding",
        "finding": _candidate_finding_text(mode, finding, bool(evidence_urls)),
        "evidence_urls": evidence_urls,
        "missing_evidence_note": missing_note,
        "confidence": "medium" if evidence_urls else "low_to_medium",
        "uncertainty_note": _uncertainty_note(mode, bool(evidence_urls)),
        "requires_human_review": mode == "strong" or not evidence_urls,
        "source_baseline_index": finding["index"],
    }


def _candidate_finding_text(mode: str, finding: dict[str, Any], has_evidence: bool) -> str:
    title = finding["title"] or "This finding"
    if mode == "strong":
        prefix = "State-first candidate keeps this finding bounded by entity and evidence constraints."
    else:
        prefix = "State-first candidate keeps this finding light and evidence-bound."
    if has_evidence:
        return f"{prefix} Baseline signal: {title}. The evidence can support observation, but not unsupported strategic expansion."
    return f"{prefix} Baseline signal: {title}. Because the baseline lacks a finding-level evidence URL, the candidate should stay compact."


def _comparison(mode: str, baseline: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    candidate = mode in {"light", "strong"}
    return {
        "specificity": _comparison_result(candidate, "improves only if evidence boundaries become more explicit"),
        "evidence_binding": _comparison_result(candidate, "primary expected improvement"),
        "entity_coherence": _comparison_result(mode == "strong", "strong mode only; light mode should not invent entity ambiguity"),
        "caveat_discipline": _comparison_result(candidate, "caveats may be compressed but must remain visible"),
        "uncertainty_preservation": _comparison_result(candidate, "required for any acceptable candidate"),
        "overreach_risk": {
            "risk_level": "medium" if mode == "strong" else "low_to_medium" if mode == "light" else "not_applicable",
            "notes": "Fluent prose could hide uncertainty if this skeleton becomes a prose generator too early.",
        },
        "baseline_primary_failure": baseline["primary_failure"],
        "state_pressure": _state_pressure_summary(state),
    }


def _verdict(mode: str, candidate_available: bool, blocked_reasons: list[str]) -> dict[str, Any]:
    if not candidate_available:
        return {
            "better_than_baseline": False,
            "safer_than_baseline": True,
            "clearer_than_baseline": False,
            "worth_continuing": False,
            "biggest_improvement": "abstention prevents unsafe or merely stylistic generation",
            "biggest_remaining_risk": "no candidate was generated",
            "what_failed": blocked_reasons,
        }
    return {
        "better_than_baseline": "candidate_for_review",
        "safer_than_baseline": "candidate_for_review",
        "clearer_than_baseline": "candidate_for_review",
        "worth_continuing": True,
        "biggest_improvement": (
            "strong mode coordinates entity/evidence uncertainty"
            if mode == "strong"
            else "light mode improves evidence discipline without overstructuring"
        ),
        "biggest_remaining_risk": "candidate skeleton is not production prose and still needs human review",
        "what_failed": [
            "v0 does not prove automated prose quality",
            "v0 does not fix missing evidence URLs",
            "v0 is lab-only and not report-ready",
        ],
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
            findings.append(
                {
                    "dimension": str(dimension),
                    "index": index,
                    "title": _text(item.get("title")),
                    "observation": _text(item.get("observation") or item.get("prose")),
                    "implication": _text(item.get("implication")),
                    "typical_decision": _text(item.get("typical_decision")),
                    "evidence_urls": [
                        str(url).strip()
                        for url in (item.get("evidence_urls") or [])
                        if isinstance(url, str) and url.strip()
                    ],
                }
            )
    return findings


def _metrics_from_payload_diagnostic(value: dict[str, Any]) -> dict[str, Any]:
    metrics = value.get("metrics")
    return metrics if isinstance(metrics, dict) else {}


def _metrics_from_render_diagnostic(value: dict[str, Any]) -> dict[str, Any]:
    metrics = value.get("visible_render_metrics")
    return metrics if isinstance(metrics, dict) else {}


def _state_body(entity_state: dict[str, Any]) -> dict[str, Any]:
    state = entity_state.get("state")
    return state if isinstance(state, dict) else entity_state


def _is_offline_state(entity_state: dict[str, Any]) -> bool:
    status = _dict(entity_state.get("status"))
    if status.get("offline_only") is True:
        return True
    if status.get("runtime_enabled") is False and status.get("used_by_scoring") is False:
        return True
    if status.get("mode") == "offline_fixture":
        return True
    return False


def _has_meaningful_evidence_map(findings: list[dict[str, Any]]) -> bool:
    return bool(findings)


def _ambiguity_is_explicit_or_absent(state: dict[str, Any]) -> bool:
    aliases = _dict(state.get("entity_aliases"))
    related = _related_surfaces(state)
    if isinstance(related, list) and related:
        return aliases.get("needs_review") is True
    primary_tension = _dict(state.get("primary_tension"))
    return primary_tension.get("requires_human_review") in {True, None} or not primary_tension


def _related_surfaces_are_reviewed(state: dict[str, Any]) -> bool:
    aliases = _dict(state.get("entity_aliases"))
    related = _related_surfaces(state)
    if not isinstance(related, list) or not related:
        return True
    for surface in related:
        if not isinstance(surface, dict):
            return False
        source = str(surface.get("source") or "")
        relation_type = str(surface.get("relation_type") or "")
        if source:
            if source not in {"manual_review", "entity_discovery", "deterministic_domain_rule"}:
                return False
            if surface.get("requires_human_review") is not True and source != "deterministic_domain_rule":
                return False
            continue
        if relation_type not in {
            "same_root_surface",
            "ambiguous_name_match",
            "repository",
            "marketplace_listing",
        }:
            return False
        if surface.get("requires_human_review") is not True and relation_type != "same_root_surface":
            return False
    return True


def _active_budgets(state: dict[str, Any]) -> dict[str, Any]:
    active: dict[str, Any] = {}
    for key in (
        "attribution_budget",
        "corroboration_caveat_budget",
        "repeated_opener_budget",
        "fallback_language_budget",
        "decision_space_mode",
    ):
        value = state.get(key)
        if isinstance(value, dict):
            active[key] = value
    return active


def _primary_failure(payload_metrics: dict[str, Any], visible_metrics: dict[str, Any]) -> str:
    if _safe_attribution_total(payload_metrics) >= 3 and _caveat_total(payload_metrics, visible_metrics) >= 3:
        return "repeated owned-claim and corroboration caveats fragment the findings"
    if _fallback_total(payload_metrics, visible_metrics) >= 3:
        return "fallback evidence openings repeat across findings"
    if _int_metric(payload_metrics, "findings_without_evidence_urls", 0) > 0:
        return "some findings are not locally evidence-bound"
    return "no major measured narrative failure"


def _overinterpretation_warnings(urls: list[str]) -> list[str]:
    warnings: list[str] = []
    domains = {_domain(url) for url in urls}
    if any("github.com" in domain for domain in domains):
        warnings.append("repository evidence does not prove official roadmap or ownership")
    if any("producthunt.com" in domain for domain in domains):
        warnings.append("marketplace profile does not prove traction")
    if any("scamadviser" in domain or "joesandbox" in domain for domain in domains):
        warnings.append("external trust/security pages do not prove broad public perception")
    return warnings


def _uncertain_items(has_related: bool, evidence_map: dict[str, Any]) -> list[str]:
    items = [
        "whether baseline evidence is sufficient for stronger strategic interpretation",
    ]
    if has_related:
        items.append("whether related surfaces belong to the audited entity")
    if evidence_map["findings_without_evidence_urls"]:
        items.append("whether under-evidenced findings should be rewritten or withheld")
    return items


def _mode_constraint(mode: str) -> str:
    if mode == "strong":
        return "govern findings with explicit shared uncertainty before dimension prose"
    if mode == "light":
        return "improve evidence boundaries without adding artificial tension"
    return "do not generate state-first prose"


def _planning_profile(
    mode: str,
    state: dict[str, Any],
    pressure_profile: dict[str, str],
) -> dict[str, str]:
    subtype = _pressure_subtype(mode, state, pressure_profile)
    planning_focus = {
        "entity_boundary_collision": "resolve nothing; keep the mixed entity frame explicit before writing dimension findings",
        "name_collision": "separate audited entity evidence from similarly named surfaces and prevent false aliasing",
        "ecosystem_surface_pressure": "separate ecosystem surfaces by relation type before drawing cross-surface conclusions",
        "stable_entity_evidence_binding": "keep intervention light and use state only to coordinate proof distribution",
        "fallback_compression": "centralize fallback evidence language and avoid repeating thin-source openings",
        "abstention": "do not generate; no safe state-first candidate exists",
        "generic_state_first_pressure": "coordinate evidence and uncertainty without adding new strategic claims",
    }.get(subtype, "coordinate evidence and uncertainty without adding new strategic claims")
    extra_rules = {
        "entity_boundary_collision": "no false entity merge",
        "name_collision": "no name-collision inflation|no visual confidence as evidentiary confidence",
        "ecosystem_surface_pressure": "no ecosystem ownership inference|no roadmap inference from repositories or marketplace profiles",
        "stable_entity_evidence_binding": "no invented hidden problem",
        "fallback_compression": "no synthetic depth for fallback evidence",
    }.get(subtype, "")
    return {
        "pressure_subtype": subtype,
        "planning_focus": planning_focus,
        "extra_overreach_rules": extra_rules,
    }


def _pressure_subtype(
    mode: str,
    state: dict[str, Any],
    profile: dict[str, str],
) -> str:
    if mode == "none":
        return "abstention"

    relation_types = _related_surface_relation_types(state)
    if mode == "strong":
        if relation_types and all(item == "ambiguous_name_match" for item in relation_types):
            return "name_collision"
        if any(
            item in relation_types
            for item in (
                "adjacent_domain",
                "developer_surface",
                "repository_surface",
                "marketplace_profile",
                "product_surface",
            )
        ):
            return "ecosystem_surface_pressure"
        if profile.get("entity_boundary") in {"medium", "high"}:
            return "entity_boundary_collision"
        return "generic_state_first_pressure"

    if mode == "light":
        if profile.get("fallback_repetition") in {"low", "medium", "high"} and profile.get("owned_claim_repetition") == "inactive":
            return "fallback_compression"
        if profile.get("healthy_case_restraint") in {"medium", "high"}:
            return "stable_entity_evidence_binding"
        return "generic_state_first_pressure"

    return "generic_state_first_pressure"


def _related_surface_relation_types(state: dict[str, Any]) -> list[str]:
    related = _related_surfaces(state)
    if not isinstance(related, list):
        return []
    return [
        str(surface.get("relation_type"))
        for surface in related
        if isinstance(surface, dict) and surface.get("relation_type")
    ]


def _related_surfaces(state: dict[str, Any]) -> list[dict[str, Any]]:
    packet_related = _nested_get(state, ("entity_resolution", "related_surfaces"))
    if isinstance(packet_related, list) and packet_related:
        return [item for item in packet_related if isinstance(item, dict)]
    aliases = _dict(state.get("entity_aliases"))
    legacy_related = aliases.get("observed_related_surfaces")
    if isinstance(legacy_related, list) and legacy_related:
        return [item for item in legacy_related if isinstance(item, dict)]
    nested_related = _nested_get(state, ("observed_related_surfaces",))
    if isinstance(nested_related, list) and nested_related:
        return [item for item in nested_related if isinstance(item, dict)]
    return []


def _caveat_strategy(planning_profile: dict[str, str]) -> str:
    subtype = planning_profile["pressure_subtype"]
    if subtype == "name_collision":
        return "state the name-collision caveat once, then keep findings bounded without repeating it"
    if subtype == "ecosystem_surface_pressure":
        return "state ecosystem-surface uncertainty once, then separate local evidence from cross-surface inference"
    if subtype == "entity_boundary_collision":
        return "state mixed-entity uncertainty once, then avoid repeated ownership and corroboration caveats"
    if subtype == "fallback_compression":
        return "compress fallback evidence openings into one global limitation, do not delete the limitation"
    if subtype == "stable_entity_evidence_binding":
        return "keep caveats local to proof gaps; do not create a global entity caveat"
    return "compress global caveats, do not delete uncertainty"


def _evidence_binding_strategy(planning_profile: dict[str, str]) -> str:
    subtype = planning_profile["pressure_subtype"]
    if subtype == "ecosystem_surface_pressure":
        return "bind each finding to its own surface and evidence URL before making any ecosystem-level statement"
    if subtype == "name_collision":
        return "bind claims only to the audited domain unless a reviewed related surface explicitly supports local ambiguity"
    if subtype == "entity_boundary_collision":
        return "separate owned, external, and adjacent-surface evidence before writing entity-level conclusions"
    if subtype == "fallback_compression":
        return "mark missing evidence URLs explicitly and avoid repeating fallback source phrasing in every finding"
    return "every candidate finding must carry evidence URLs or an explicit missing-evidence note"


def _extra_overreach_rules(planning_profile: dict[str, str]) -> list[str]:
    raw = planning_profile.get("extra_overreach_rules", "")
    return [item for item in raw.split("|") if item]


def _coordination_rules(
    mode: str,
    state: dict[str, Any],
    payload_metrics: dict[str, Any],
    visible_metrics: dict[str, Any],
    planning_profile: dict[str, str],
) -> list[str]:
    rules = [
        "do not use scores as evidence",
        "do not write generic Decision Space",
        "keep observation and interpretation separate",
    ]
    subtype = planning_profile["pressure_subtype"]
    if mode == "strong":
        rules.append("state entity uncertainty once before dimension findings")
    if subtype == "entity_boundary_collision":
        rules.append("separate mixed entity surfaces before dimension interpretation")
        rules.append("do not merge adjacent brands or crawled surfaces into one strategy")
    if subtype == "name_collision":
        rules.append("treat similarly named surfaces as collision pressure only")
        rules.append("do not convert name similarity into aliases")
    if subtype == "ecosystem_surface_pressure":
        rules.append("separate product, developer, repository, and marketplace surfaces")
        rules.append("do not treat ecosystem adjacency as verified ownership")
    if mode == "light":
        rules.append("avoid heavy rewrite and preserve stable entity signal")
    if subtype == "stable_entity_evidence_binding":
        rules.append("use state-first only to coordinate proof distribution")
    if subtype == "fallback_compression":
        rules.append("centralize fallback language and avoid repeating evidence-pool openings")
    if _caveat_total(payload_metrics, visible_metrics) > 0:
        rules.append("compress repeated caveats without deleting uncertainty")
    if _safe_attribution_total(payload_metrics) > 0:
        rules.append("treat owned claims as positioning, not proof")
    if _dict(state.get("entity_aliases")).get("needs_review") is True:
        rules.append("keep related surfaces review-gated")
    return rules


def _global_caveat(
    mode: str,
    state: dict[str, Any],
    evidence_map: dict[str, Any],
    planning_profile: dict[str, str],
) -> str:
    subtype = planning_profile["pressure_subtype"]
    if subtype == "entity_boundary_collision":
        return "State-first reading keeps the mixed entity frame visible and does not merge adjacent brand surfaces into one strategy."
    if subtype == "name_collision":
        return "State-first reading treats similarly named surfaces as name-collision pressure, not aliases, ownership, or proof of shared strategy."
    if subtype == "ecosystem_surface_pressure":
        return "State-first reading treats related ecosystem surfaces as review-gated context, not as proof that one entity controls every surface."
    if subtype == "stable_entity_evidence_binding":
        return "State-first reading keeps the entity stable and uses the state only to coordinate proof distribution and local evidence limits."
    if subtype == "fallback_compression":
        return "State-first reading keeps the entity stable and centralizes fallback evidence language instead of repeating it across findings."
    if mode == "strong":
        return "State-first reading centralizes entity and evidence uncertainty before dimension-level findings."
    if evidence_map["findings_without_evidence_urls"]:
        return "State-first reading keeps the entity stable and treats missing finding-level evidence as a local coverage limit."
    return "State-first reading stays light because the baseline does not require a strong intervention."


def _uncertainty_note(mode: str, has_evidence: bool) -> str:
    if not has_evidence:
        return "This candidate must remain limited because the baseline finding lacks a local evidence URL."
    if mode == "strong":
        return "This candidate remains review-gated where entity or source ownership is unresolved."
    return "This candidate should stay light and avoid adding artificial tension."


def _comparison_result(active: bool, notes: str) -> dict[str, Any]:
    return {
        "candidate_improves": active,
        "notes": notes,
    }


def _state_pressure_summary(state: dict[str, Any]) -> str:
    aliases = _dict(state.get("entity_aliases"))
    if aliases.get("needs_review") is True:
        return "entity ambiguity pressure"
    owned = _dict(state.get("owned_claim_density"))
    if owned.get("level") in {"moderate", "high"}:
        return "owned-claim repetition pressure"
    fallback = _dict(state.get("fallback_language_budget"))
    if fallback.get("fallback_like_repetition") is True:
        return "fallback repetition pressure"
    return "low explicit state pressure"


def _count_pressure(value: int, *, low: int, medium: int, high: int) -> str:
    if value <= 0:
        return "inactive"
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    if value >= low:
        return "low"
    return "inactive"


def _ratio_pressure(value: float) -> str:
    if value <= 0:
        return "inactive"
    if value >= 0.45:
        return "high"
    if value >= 0.25:
        return "medium"
    return "low"


def _visual_or_perceptual_pressure(
    state: dict[str, Any],
    findings: list[dict[str, Any]],
) -> str:
    text = " ".join(
        [
            _text(_dict(state.get("primary_entity_signal")).get("label")),
            _text(_dict(state.get("primary_tension")).get("summary")),
            " ".join(finding.get("title", "") for finding in findings),
            " ".join(finding.get("observation", "") for finding in findings),
        ]
    ).lower()
    if any(token in text for token in ("visual", "perceptual", "aesthetic", "motion", "brand identity")):
        return "medium"
    return "unknown"


def _healthy_case_restraint(
    explicit_entity_boundary: bool,
    related_count: int,
    caveat_total: int,
    fallback_total: int,
    owned_total: int,
    findings_without: int,
    finding_count: int,
) -> str:
    if explicit_entity_boundary or related_count:
        return "low"
    if finding_count <= 0:
        return "unknown"
    if caveat_total or fallback_total or owned_total or findings_without:
        return "high"
    return "medium"


def _has_thin_payload(findings: list[dict[str, Any]], payload_metrics: dict[str, Any]) -> bool:
    finding_count = _int_metric(payload_metrics, "findings_count", len(findings))
    evidence_count = len(_evidence_urls(findings))
    return finding_count <= 1 or evidence_count <= 1


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _case_id(payload: dict[str, Any], snapshot: dict[str, Any], entity_state: dict[str, Any]) -> str:
    explicit = _first_text(
        payload.get("case_id"),
        snapshot.get("case_id"),
        _nested_get(entity_state, ("metadata", "case_id")),
        _nested_get(entity_state, ("metadata", "brand")),
        snapshot.get("brand_name"),
        snapshot.get("brand"),
        payload.get("brand"),
    )
    return _slug(explicit or "unknown")


def _evidence_urls(findings: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    for finding in findings:
        urls.extend(finding.get("evidence_urls") or [])
    return urls


def _findings_without_urls(payload_metrics: dict[str, Any], findings: list[dict[str, Any]]) -> int:
    return _int_metric(
        payload_metrics,
        "findings_without_evidence_urls",
        sum(1 for finding in findings if not finding["evidence_urls"]),
    )


def _safe_attribution_total(payload_metrics: dict[str, Any]) -> int:
    return _int_metric(payload_metrics, "safe_attribution_total", 0)


def _generic_decision_count(payload_metrics: dict[str, Any]) -> int:
    phrases = _dict(payload_metrics.get("generic_phrase_counts"))
    return _coerce_int(phrases.get("teams in this position typically"), 0)


def _caveat_total(payload_metrics: dict[str, Any], visible_metrics: dict[str, Any]) -> int:
    return max(
        _family_total(payload_metrics, "external_corroboration_caveat_repetition"),
        _family_total(visible_metrics, "external_corroboration_caveat_repetition"),
    )


def _fallback_total(payload_metrics: dict[str, Any], visible_metrics: dict[str, Any]) -> int:
    return max(
        _family_total(payload_metrics, "fallback_evidence_opening_repetition"),
        _family_total(visible_metrics, "fallback_evidence_opening_repetition"),
    )


def _family_total(metrics: dict[str, Any], family_name: str) -> int:
    families = _dict(metrics.get("observation_repetition_family_counts"))
    family = _dict(families.get(family_name))
    return _coerce_int(family.get("total"), 0)


def _int_metric(metrics: dict[str, Any], key: str, default: int) -> int:
    return _coerce_int(metrics.get(key), default)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.")


def _text(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) and value.strip() else ""


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _text(value)
        if text:
            return text
    return None


def _nested_get(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _slug(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .replace("/", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )
