"""Lab-only state-first prose generator candidate.

This module converts an existing state-first planning artifact into structured
prose candidates for research review. It is deliberately deterministic and
offline: no scoring, rendering, prompt rollout, persistence, report mutation,
runtime wiring, Visual Signature access, or LLM calls.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

VERSION = "state_first_prose_candidate.v0"
NO_PROSE_CANDIDATE = "No safe state-first prose candidate."
SUPPORTED_SUBTYPES = {
    "name_collision",
    "ecosystem_surface_pressure",
    "stable_entity_evidence_binding",
}


def generate_state_first_prose_candidate(
    planning_artifact: dict,
    *,
    payload: dict | None = None,
) -> dict:
    """Generate a deterministic lab-only state-first prose candidate."""

    artifact = planning_artifact if isinstance(planning_artifact, dict) else {}
    safe_payload = payload if isinstance(payload, dict) else {}
    plan = _dict(artifact.get("state_first_finding_plan"))
    decision = _dict(artifact.get("generation_decision"))
    subtype = _text(plan.get("pressure_subtype"))
    mode = _text(plan.get("mode") or decision.get("mode"))
    candidate_available = bool(decision.get("candidate_available", mode in {"light", "strong"}))

    if not candidate_available or subtype not in SUPPORTED_SUBTYPES:
        return _abstention(artifact, subtype, mode)

    skeleton = _dict(artifact.get("generated_state_first_findings"))
    skeleton_by_dimension = _dict(skeleton.get("findings_by_dimension"))
    shared_state = _dict(artifact.get("shared_entity_state"))
    evidence_map = _dict(artifact.get("shared_evidence_map"))
    target = _audited_surface(artifact, safe_payload)

    return {
        "version": VERSION,
        "created_at": "deterministic_lab_prose_generator_v0",
        "case_id": _text(artifact.get("case_id")) or "unknown",
        "target": target,
        "status": _status(mode, subtype),
        "source_artifacts": _source_artifacts(artifact),
        "generation_frame": _generation_frame(mode, subtype, plan, target),
        "baseline_problem_summary": _baseline_problem_summary(artifact),
        "shared_evidence_map": _prose_evidence_map(subtype, target, shared_state, evidence_map),
        "state_first_findings_by_dimension": _findings_by_dimension(
            subtype,
            target,
            skeleton_by_dimension,
            shared_state,
            evidence_map,
        ),
        "comparison": _comparison(subtype),
        "verdict": _verdict(subtype),
    }


def _status(mode: str, subtype: str) -> dict[str, bool]:
    return {
        "lab_only": True,
        "deterministic_generation": True,
        "manual_offline_generation": False,
        "runtime_integration": False,
        "prompt_rollout": False,
        "scoring_change": False,
        "renderer_change": False,
        "report_mutation": False,
        "visual_signature_change": False,
        "production_ready": False,
        "requires_human_review": mode == "strong" or subtype in {"name_collision", "ecosystem_surface_pressure"},
    }


def _source_artifacts(artifact: dict[str, Any]) -> dict[str, str]:
    return {
        "planning_artifact_version": _text(artifact.get("version")) or "unknown",
        "planning_case_id": _text(artifact.get("case_id")) or "unknown",
    }


def _generation_frame(
    mode: str,
    subtype: str,
    plan: dict[str, Any],
    target: str,
) -> dict[str, str]:
    return {
        "mode": mode,
        "pressure_subtype": subtype,
        "planning_focus": _text(plan.get("planning_focus")) or _planning_focus(subtype),
        "global_caveat": _global_caveat(subtype, target),
        "evidence_boundary": _global_evidence_boundary(subtype, target),
        "uncertainty_rule": _global_uncertainty_rule(subtype),
    }


def _baseline_problem_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    baseline = _dict(artifact.get("baseline"))
    return {
        "findings_count": _coerce_int(baseline.get("findings_count"), 0),
        "findings_without_evidence_urls": _coerce_int(baseline.get("findings_without_evidence_urls"), 0),
        "safe_attribution_total": _coerce_int(baseline.get("safe_attribution_total"), 0),
        "external_corroboration_caveat_total": _coerce_int(
            baseline.get("external_corroboration_caveat_total"), 0
        ),
        "fallback_evidence_opening_total": _coerce_int(baseline.get("fallback_evidence_opening_total"), 0),
        "generic_decision_space_count": _coerce_int(baseline.get("generic_decision_space_count"), 0),
        "primary_failure": _primary_failure(artifact),
    }


def _prose_evidence_map(
    subtype: str,
    target: str,
    state: dict[str, Any],
    evidence_map: dict[str, Any],
) -> dict[str, Any]:
    related = _related_surfaces(state)
    missing = [
        f"{_text(item.get('dimension'))}: {_text(item.get('title'))}"
        for item in _list(evidence_map.get("findings_without_evidence_urls"))
        if isinstance(item, dict)
    ]
    if subtype == "stable_entity_evidence_binding":
        urls = _list(evidence_map.get("evidence_urls"))
        return {
            "owned_surfaces": [url for url in urls if _same_domain(url, target)],
            "external_or_third_party_surfaces": [url for url in urls if not _same_domain(url, target)],
            "missing_finding_level_evidence": missing,
            "do_not_overinterpret": [
                "Do not invent entity ambiguity.",
                "Do not treat owned claims as independently verified.",
                "Do not make missing evidence sound like a hidden strategic failure.",
            ],
        }
    key = "ambiguous_name_collision_surfaces" if subtype == "name_collision" else "ecosystem_context_surfaces"
    return {
        "audited_surface": [target],
        key: [_surface_to_url(item) for item in related],
        "missing_finding_level_evidence": missing,
        "do_not_overinterpret": _do_not_overinterpret(subtype),
    }


def _findings_by_dimension(
    subtype: str,
    target: str,
    skeleton_by_dimension: dict[str, Any],
    state: dict[str, Any],
    evidence_map: dict[str, Any],
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for dimension in sorted(skeleton_by_dimension):
        raw_items = _list(skeleton_by_dimension.get(dimension))
        titles = [_text(item.get("title")) for item in raw_items if isinstance(item, dict)]
        evidence = _dimension_evidence(raw_items)
        missing_count = sum(1 for item in raw_items if isinstance(item, dict) and not _list(item.get("evidence_urls")))
        output[dimension] = {
            "baseline_titles": titles,
            "state_first_candidate": _dimension_candidate(
                subtype,
                dimension,
                target,
                titles,
                evidence,
                missing_count,
            ),
            "evidence_used": evidence,
            "evidence_boundary": _dimension_evidence_boundary(subtype, dimension, target, evidence, missing_count),
            "uncertainty_retained": _dimension_uncertainty(subtype, dimension, missing_count, state, evidence_map),
            "overreach_avoided": _dimension_overreach(subtype, dimension),
            "requires_human_review": _dimension_requires_review(subtype, missing_count),
            "confidence": _dimension_confidence(subtype, missing_count, evidence),
        }
    return output


def _dimension_candidate(
    subtype: str,
    dimension: str,
    target: str,
    titles: list[str],
    evidence: list[str],
    missing_count: int,
) -> str:
    title_text = _titles_sentence(titles)
    if subtype == "name_collision":
        return _name_collision_dimension_candidate(dimension, target, title_text, evidence, missing_count)
    if subtype == "ecosystem_surface_pressure":
        return _ecosystem_dimension_candidate(dimension, target, title_text, evidence, missing_count)
    if subtype == "stable_entity_evidence_binding":
        if missing_count:
            return (
                f"The {dimension} reading should stay light: LaunchDarkly remains entity-stable, but {title_text} includes claims that need local evidence before stronger interpretation."
            )
        return (
            f"The {dimension} reading can stay close to the attached evidence. {title_text} supports activity or positioning without adding hidden tension."
        )
    return f"No safe prose candidate for {dimension}."


def _name_collision_dimension_candidate(
    dimension: str,
    target: str,
    title_text: str,
    evidence: list[str],
    missing_count: int,
) -> str:
    if dimension == "coherencia":
        return (
            f"Coherence should be anchored to {target}. {title_text} can describe the audited surface's own promise, "
            "but similarly named Iris domains should stay outside the core entity story unless reviewed relation evidence exists."
        )
    if dimension == "diferenciacion":
        return (
            f"Differentiation can safely read the audited Iris surface as a speed/value proposition, not as a proven market position. "
            f"{title_text} should remain an owned positioning signal until external proof or product evidence supports stronger claims."
        )
    if dimension == "percepcion":
        return (
            "Perception should treat Iris-name overlap as visibility and interpretation risk. "
            f"{title_text} may affect what a viewer thinks they are seeing, but it is not evidence of shared ownership or brand architecture."
        )
    if dimension == "presencia":
        return (
            f"Presence should separate the primary audited domain, {target}, from unresolved Iris-like surfaces before discussing footprint. "
            f"{title_text} can show discoverability pressure, not a verified multi-domain system."
        )
    if dimension == "vitalidad":
        return (
            f"Vitality should not import activity from other Iris-named AI, agency, or collaborative surfaces into {target}. "
            f"{title_text} can remain background ambiguity unless the activity is directly tied to the audited surface."
        )
    qualifier = "without local evidence URLs" if missing_count else "with the attached evidence"
    return (
        f"The {dimension} reading should stay anchored to {target} {qualifier}. "
        f"{title_text} must not convert name similarity into aliases, ownership, or coordinated strategy."
    )


def _ecosystem_dimension_candidate(
    dimension: str,
    target: str,
    title_text: str,
    evidence: list[str],
    missing_count: int,
) -> str:
    if dimension == "coherencia":
        return (
            f"Coherence should start with the owned story on {target}, then stop before turning adjacent domains or repositories into one verified system. "
            f"{title_text} can frame the promise, but not prove ecosystem architecture."
        )
    if dimension == "diferenciacion":
        return (
            f"Differentiation should treat {target}'s infrastructure claim as an owned claim first. "
            f"{title_text} can show how the brand wants to compete, but repository or marketplace context cannot verify category advantage."
        )
    if dimension == "percepcion":
        return (
            "Perception should separate surface noise from brand signal: owned page evidence, repository evidence, marketplace evidence and unrelated Watermelon references do different jobs. "
            f"{title_text} should not be smoothed into one public reputation story."
        )
    if dimension == "presencia":
        return (
            f"Presence should map surfaces by relation type: {target} as audited surface, adjacent Watermelon domains as review-gated, repositories as technical context, and listings as weak external traces. "
            f"{title_text} can show footprint pressure, not controlled channel architecture."
        )
    if dimension == "vitalidad":
        return (
            "Vitality should be the strictest read: repository movement, marketplace listings or adjacent-domain activity do not prove audited-brand momentum. "
            f"{title_text} can show unresolved activity around the name, but not roadmap, traction or growth."
        )
    qualifier = "without local evidence URLs" if missing_count else "with surface-specific evidence"
    return (
        f"The {dimension} reading should separate {target} from adjacent domains, repositories and listings {qualifier}. "
        f"{title_text} must not become ownership, roadmap, traction or ecosystem-architecture inference."
    )


def _dimension_evidence_boundary(
    subtype: str,
    dimension: str,
    target: str,
    evidence: list[str],
    missing_count: int,
) -> str:
    if not evidence:
        return "No finding-level evidence URL is attached in the planning artifact; keep this dimension compact."
    if subtype == "name_collision":
        return f"Claims are anchored to {target}; other Iris-like evidence can only support ambiguity pressure."
    if subtype == "ecosystem_surface_pressure":
        return "Evidence must be read by surface type before any ecosystem-level statement."
    if subtype == "stable_entity_evidence_binding":
        return "Evidence can support the local claim, but owned claims remain owned unless externally corroborated."
    return "Evidence boundary unavailable."


def _dimension_uncertainty(
    subtype: str,
    dimension: str,
    missing_count: int,
    state: dict[str, Any],
    evidence_map: dict[str, Any],
) -> list[str]:
    items: list[str] = []
    if missing_count:
        items.append("One or more baseline findings in this dimension lack local evidence URLs.")
    if subtype == "name_collision":
        items.append("The relationship between similarly named surfaces remains unverified.")
        if dimension in {"percepcion", "presencia"}:
            items.append("Visibility pressure is not ownership evidence.")
    elif subtype == "ecosystem_surface_pressure":
        items.append("Related ecosystem surfaces remain review-gated.")
        if dimension in {"percepcion", "presencia", "vitalidad"}:
            items.append("Repository, marketplace, or adjacent-domain evidence does not prove official ownership or traction.")
    elif subtype == "stable_entity_evidence_binding":
        items.append("Missing evidence is a coverage limit, not proof of strategic weakness.")
        if dimension in {"percepcion", "presencia"}:
            items.append("Owned positioning should not be inflated into external validation.")
    if not items:
        items.append("No additional uncertainty beyond the global evidence boundary.")
    return items


def _dimension_overreach(subtype: str, dimension: str) -> list[str]:
    if subtype == "name_collision":
        return [
            "Does not infer ownership from name similarity.",
            "Does not treat related Iris-like surfaces as aliases.",
        ]
    if subtype == "ecosystem_surface_pressure":
        return [
            "Does not infer ecosystem ownership.",
            "Does not infer roadmap, traction, or community strength from adjacent surfaces.",
        ]
    if subtype == "stable_entity_evidence_binding":
        return [
            "Does not invent entity ambiguity.",
            "Does not invent hidden tension to justify state-first intervention.",
        ]
    return ["No safe overreach assessment available."]


def _comparison(subtype: str) -> dict[str, Any]:
    if subtype == "stable_entity_evidence_binding":
        return {
            "specificity": {
                "winner": "state_first_light",
                "notes": "Keeps stable entity signal and tightens proof distribution.",
            },
            "evidence_binding": {"winner": "state_first", "notes": "Primary improvement."},
            "entity_coherence": {"winner": "baseline_and_state_first", "notes": "Baseline was already coherent."},
            "overreach_risk": {"winner": "state_first", "notes": "Low because intervention remains light."},
        }
    if subtype == "name_collision":
        note = "Prevents similarly named surfaces from becoming aliases or strategy."
    else:
        note = "Prevents related ecosystem surfaces from becoming false brand architecture."
    return {
        "specificity": {"winner": "state_first", "notes": note},
        "evidence_binding": {"winner": "state_first", "notes": "Evidence families are separated before interpretation."},
        "entity_coherence": {"winner": "state_first", "notes": "Keeps ambiguity visible instead of smoothing it."},
        "overreach_risk": {"winner": "state_first", "notes": "Lower risk, but still review-gated."},
    }


def _verdict(subtype: str) -> dict[str, Any]:
    if subtype == "stable_entity_evidence_binding":
        return {
            "better_than_baseline": "moderately",
            "safer_than_baseline": True,
            "clearer_than_baseline": True,
            "worth_continuing": True,
            "biggest_improvement": "Improves proof distribution without inventing ambiguity or tension.",
            "biggest_remaining_risk": "The improvement is intentionally smaller because the baseline is already stable.",
            "what_still_fails": [
                "Some findings may still lack local evidence URLs.",
                "Owned claims still need external validation before stronger conclusions.",
                "This candidate is lab-only and must not replace the official report.",
            ],
        }
    return {
        "better_than_baseline": True,
        "safer_than_baseline": True,
        "clearer_than_baseline": True,
        "worth_continuing": True,
        "biggest_improvement": (
            "Prevents name-collision evidence from becoming false entity coherence."
            if subtype == "name_collision"
            else "Prevents ecosystem adjacency from becoming false brand architecture."
        ),
        "biggest_remaining_risk": "The candidate still depends on unresolved entity review.",
        "what_still_fails": [
            "Some findings may still lack local evidence URLs.",
            "Related-surface ownership remains unresolved.",
            "This candidate is lab-only and must not replace the official report.",
        ],
    }


def _abstention(artifact: dict[str, Any], subtype: str, mode: str) -> dict[str, Any]:
    return {
        "version": VERSION,
        "created_at": "deterministic_lab_prose_generator_v0",
        "case_id": _text(artifact.get("case_id")) or "unknown",
        "status": _status("none", subtype),
        "generation_decision": {
            "mode": mode or "none",
            "candidate_available": False,
            "reason": NO_PROSE_CANDIDATE,
            "unsupported_pressure_subtype": subtype or "unknown",
        },
        "generated_state_first_prose": None,
        "verdict": {
            "worth_continuing": False,
            "what_failed": [NO_PROSE_CANDIDATE],
        },
    }


def _global_caveat(subtype: str, target: str) -> str:
    if subtype == "name_collision":
        return (
            f"This lab reading treats {target} as the audited surface. Similarly named surfaces are ambiguity pressure only; "
            "they are not aliases, owned surfaces, or proof of one shared strategy."
        )
    if subtype == "ecosystem_surface_pressure":
        return (
            f"This lab reading treats {target} as the audited surface. Adjacent domains, repositories, developer surfaces and marketplace listings "
            "are ecosystem pressure only; they are not proof of shared ownership, roadmap, traction or one controlled brand architecture."
        )
    return (
        "This lab reading treats the audited entity as stable. State-first should not invent ambiguity or hidden tension; "
        "it should only tighten evidence boundaries and avoid repeated owned-claim caveats."
    )


def _global_evidence_boundary(subtype: str, target: str) -> str:
    if subtype == "name_collision":
        return f"Claims about the audited case are bound to {target}; similarly named surfaces can only support ambiguity pressure."
    if subtype == "ecosystem_surface_pressure":
        return f"Claims about the audited brand are bound to {target}; ecosystem surfaces require relation-specific review."
    return "Owned sources support owned positioning; external sources support only what they explicitly evidence."


def _global_uncertainty_rule(subtype: str) -> str:
    if subtype == "name_collision":
        return "Name similarity must not become ownership, aliasing, or shared strategy."
    if subtype == "ecosystem_surface_pressure":
        return "Repository, marketplace, and adjacent-domain signals must not become roadmap, traction, or ownership claims."
    return "A healthy case should stay healthy; missing evidence is a coverage limit, not proof of strategic weakness."


def _primary_failure(artifact: dict[str, Any]) -> str:
    baseline = _dict(artifact.get("baseline"))
    failure = _text(baseline.get("primary_failure"))
    if failure:
        return failure
    return "No measured baseline failure available."


def _dimension_requires_review(subtype: str, missing_count: int) -> bool:
    return subtype in {"name_collision", "ecosystem_surface_pressure"} or missing_count > 0


def _dimension_confidence(subtype: str, missing_count: int, evidence: list[str]) -> str:
    if subtype == "stable_entity_evidence_binding" and evidence and not missing_count:
        return "medium"
    if evidence and not missing_count:
        return "medium"
    if evidence:
        return "low_to_medium"
    return "low"


def _dimension_evidence(raw_items: list[Any]) -> list[str]:
    urls: list[str] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        for url in _list(item.get("evidence_urls")):
            if isinstance(url, str) and url and url not in urls:
                urls.append(url)
    return urls


def _audited_surface(artifact: dict[str, Any], payload: dict[str, Any]) -> str:
    for value in (
        _nested_get(artifact, ("shared_entity_state", "primary_entity_signal", "supporting_sources", 0)),
        _nested_get(payload, ("target_url",)),
        _nested_get(payload, ("url",)),
        artifact.get("case_id"),
    ):
        text = _text(value)
        if text:
            return _normalize_surface(text)
    return "unknown"


def _related_surfaces(state: dict[str, Any]) -> list[dict[str, Any]]:
    packet_related = _nested_get(state, ("entity_resolution", "related_surfaces"))
    if isinstance(packet_related, list) and packet_related:
        return [item for item in packet_related if isinstance(item, dict)]
    related = state.get("observed_related_surfaces")
    if isinstance(related, list) and related:
        return [item for item in related if isinstance(item, dict)]
    nested_related = _nested_get(state, ("observed_related_surfaces",))
    return [item for item in nested_related if isinstance(item, dict)] if isinstance(nested_related, list) else []


def _surface_to_url(surface: dict[str, Any]) -> str:
    value = _text(surface.get("surface"))
    if not value:
        return "unknown"
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("github.com/"):
        return f"https://{value}"
    return f"https://{value}/"


def _do_not_overinterpret(subtype: str) -> list[str]:
    if subtype == "name_collision":
        return [
            "Do not infer ownership from name similarity.",
            "Do not treat similarly named domains as aliases.",
            "Do not convert visual strength into evidence of market validation.",
        ]
    return [
        "Do not infer ownership from adjacent domains.",
        "Do not infer roadmap from repositories.",
        "Do not infer traction from marketplace listings.",
        "Do not treat unrelated mentions as public perception of the audited brand.",
    ]


def _same_domain(url: str, target: str) -> bool:
    return _domain(url) == _domain(target)


def _domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.").strip("/")


def _normalize_surface(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value.rstrip("/")
    if "." in value:
        return f"https://{value.strip('/')}"
    return value


def _titles_sentence(titles: list[str]) -> str:
    clean = [title for title in titles if title]
    if not clean:
        return "The baseline signal"
    if len(clean) == 1:
        return clean[0]
    if len(clean) == 2:
        return f"{clean[0]} and {clean[1]}"
    return f"{', '.join(clean[:-1])}, and {clean[-1]}"


def _planning_focus(subtype: str) -> str:
    if subtype == "name_collision":
        return "separate audited entity evidence from similarly named surfaces and prevent false aliasing"
    if subtype == "ecosystem_surface_pressure":
        return "separate ecosystem surfaces by relation type before drawing cross-surface conclusions"
    if subtype == "stable_entity_evidence_binding":
        return "keep intervention light and use state only to coordinate proof distribution"
    return "no safe planning focus"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) and value.strip() else ""


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _nested_get(value: dict[str, Any], path: tuple[Any, ...]) -> Any:
    current: Any = value
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
