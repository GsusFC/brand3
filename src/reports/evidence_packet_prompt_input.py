"""Offline prompt-input candidate builder from Evidence Packet v0.

This module does not generate prose and does not integrate with runtime report
generation. It turns an existing Evidence Packet v0 dictionary into a stricter
model-input candidate so the contract can be reviewed before any prompt rollout.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit


VERSION = 0
SOURCE = "evidence_packet_v0"

DIMENSIONS = ("coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad")
INCLUDED_STATUSES = {"ready", "thin"}
EXCLUDED_STATUSES = {"blocked", "abstain"}
REVIEW_STATUS = "review_required"

DISALLOWED_SOURCE_CLASSES = {
    "technical_internal",
    "visual_internal_metric",
    "trust_security",
    "noise",
    "related_unresolved",
    "marketplace_listing",
}

REVIEW_GATED_SOURCE_CLASSES = {
    "related_unresolved",
    "marketplace_listing",
    "trust_security",
}


def build_prompt_input_candidate_v0(packet: dict) -> dict:
    """Build a lab-only prompt input candidate from an Evidence Packet v0 dict."""
    dimensions: dict[str, dict] = {}
    excluded_dimensions: list[dict] = []
    review_required_dimensions: list[dict] = []

    for dimension in DIMENSIONS:
        readiness = (packet.get("dimension_readiness") or {}).get(dimension) or {}
        status = str(readiness.get("status") or "abstain")
        include = status in INCLUDED_STATUSES

        included_evidence = _included_evidence(packet, dimension) if include else []
        excluded_evidence = _excluded_evidence(packet, dimension, included_evidence)
        review_evidence = _review_required_evidence(packet, dimension)
        constraints = _prompt_constraints(dimension, status, included_evidence, readiness, packet)
        abstention_reason = "" if include else _abstention_reason(readiness)

        dimensions[dimension] = {
            "readiness_status": status,
            "include_in_prompt": include,
            "evidence": included_evidence,
            "excluded_evidence": excluded_evidence,
            "review_required_evidence": review_evidence,
            "prompt_constraints": constraints,
            "abstention_reason": abstention_reason,
        }

        if status in EXCLUDED_STATUSES:
            excluded_dimensions.append(
                {
                    "dimension": dimension,
                    "status": status,
                    "reason_codes": list(readiness.get("reason_codes") or []),
                    "reason": abstention_reason,
                }
            )
        elif status == REVIEW_STATUS:
            review_required_dimensions.append(
                {
                    "dimension": dimension,
                    "status": status,
                    "reason_codes": list(readiness.get("reason_codes") or []),
                    "reason": abstention_reason,
                }
            )

    return {
        "version": VERSION,
        "case_id": packet.get("case_id") or "",
        "audit_url": packet.get("audit_url") or "",
        "source": SOURCE,
        "runtime_effect": False,
        "prompt_effect": False,
        "dimensions": dimensions,
        "global_constraints": _global_constraints(),
        "excluded_dimensions": excluded_dimensions,
        "review_required_dimensions": review_required_dimensions,
        "metadata": _metadata(packet, dimensions),
    }


def _included_evidence(packet: dict, dimension: str) -> list[dict]:
    included: list[dict] = []
    for item in packet.get("finding_eligible_evidence") or []:
        if item.get("dimension") != dimension:
            continue
        if not _can_include_evidence(item):
            continue
        included.append(_prompt_evidence(item))
    return _dedupe_included_evidence(included)


def _can_include_evidence(item: dict) -> bool:
    if item.get("eligibility") != "eligible_for_narrative_finding":
        return False
    if not str(item.get("text") or "").strip():
        return False
    if _review_gate_reason(item):
        return False
    if item.get("source_class") in DISALLOWED_SOURCE_CLASSES:
        return False
    return True


def _excluded_evidence(packet: dict, dimension: str, included: list[dict]) -> list[dict]:
    included_keys = {(item.get("text") or "", item.get("url") or "") for item in included}
    excluded: list[dict] = []

    for item in packet.get("evidence_not_eligible_for_findings") or []:
        if item.get("dimension") == dimension:
            excluded.append(_excluded_prompt_evidence(item, item.get("eligibility") or "not_eligible"))

    for item in packet.get("finding_eligible_evidence") or []:
        if item.get("dimension") != dimension:
            continue
        key = (item.get("text") or "", item.get("url") or "")
        if key not in included_keys:
            excluded.append(_excluded_prompt_evidence(item, "excluded_by_prompt_input_contract"))
    return _dedupe(excluded)


def _review_required_evidence(packet: dict, dimension: str) -> list[dict]:
    review: list[dict] = []
    for item in packet.get("evidence_not_eligible_for_findings") or []:
        if item.get("dimension") != dimension:
            continue
        reason = _review_gate_reason(item)
        if reason:
            review.append(_excluded_prompt_evidence(item, reason))
    for item in packet.get("finding_eligible_evidence") or []:
        if item.get("dimension") != dimension:
            continue
        reason = _review_gate_reason(item)
        if reason:
            review.append(_excluded_prompt_evidence(item, reason))
    return _dedupe(review)


def _review_gate_reason(item: dict) -> str:
    eligibility = str(item.get("eligibility") or "")
    source_class = str(item.get("source_class") or "")
    classification_reason = str(item.get("classification_reason") or "")
    if eligibility in {"requires_human_review", "trust_security_review_only"}:
        return eligibility
    if source_class in REVIEW_GATED_SOURCE_CLASSES:
        return "review_gated_source_class"
    if classification_reason.startswith("exa_") and "review" in classification_reason:
        return "exa_review_gated"
    return ""


def _prompt_evidence(item: dict) -> dict:
    return {
        "text": item.get("text") or "",
        "url": item.get("url") or "",
        "source_class": item.get("source_class") or "",
        "feature_name": item.get("feature_name") or "",
        "feature_source": item.get("feature_source") or "",
        "classification_reason": item.get("classification_reason") or "",
        "limits": item.get("limits") or "",
    }


def _excluded_prompt_evidence(item: dict, reason: str) -> dict:
    return {
        **_prompt_evidence(item),
        "exclusion_reason": reason,
    }


def _prompt_constraints(dimension: str, status: str, evidence: list[dict], readiness: dict, packet: dict | None = None) -> list[str]:
    constraints: list[str] = []
    source_classes = {item.get("source_class") or "" for item in evidence}

    constraints.append("Use only included evidence for this dimension.")
    constraints.append("Do not use excluded or review-required evidence.")
    constraints.append("Do not invent strategy, intent, ownership, traction, or entity relationships.")

    if status == "thin":
        constraints.append("Dimension is thin; qualify evidence limits and avoid strong conclusions.")
    if dimension in {"coherencia", "presencia"}:
        constraints.append("Owned claims remain attributed to owned surfaces and are not external validation.")
    if dimension == "percepcion":
        constraints.append("Perception evidence must not be generalized beyond cited sources.")
    if dimension == "vitalidad":
        constraints.append("Temporal evidence supports visible activity, not traction or growth.")
    if "external_third_party" in source_classes:
        constraints.append("External evidence is source-bounded and must be cited.")
    if "repository" in source_classes:
        constraints.append("Repository evidence supports developer activity only, not adoption.")
    if "competitor_comparison" in source_classes:
        constraints.append("Competitor comparison supports only relative positioning distance, not leadership.")
        constraints.append("Do not turn competitor comparison into product superiority, moat, market advantage, customer preference, or strategy.")
    if status in EXCLUDED_STATUSES or status == REVIEW_STATUS:
        constraints.append("Do not generate this dimension.")
    for code in readiness.get("reason_codes") or []:
        if code == "owned_claim_without_external_corroboration":
            constraints.append("Owned claims lack external corroboration; keep attribution visible.")
        elif code == "review_gated_evidence_not_ready":
            constraints.append("Review-gated evidence cannot enter the prompt without manual approval.")

    if packet:
        cross_evidence = packet.get("cross_dimension_evidence") or {}
        candidates = cross_evidence.get("contradiction_candidates") or packet.get("contradiction_candidates") or []
        
        feature_names_in_dimension = {item.get("feature_name") for item in evidence if item.get("feature_name")}
        
        FEATURE_TO_DIMENSION = {
            "messaging_consistency": "coherencia",
            "tone_consistency": "coherencia",
            "visual_consistency": "coherencia",
            "web_presence": "presencia",
            "social_footprint": "presencia",
            "search_visibility": "presencia",
            "site_structure": "presencia",
            "brand_sentiment": "percepcion",
            "positioning_clarity": "diferenciacion",
            "competitor_distance": "diferenciacion",
            "momentum": "vitalidad",
            "content_recency": "vitalidad",
            "publication_cadence": "vitalidad",
        }
        
        for cand in candidates:
            if cand.get("type") == "owned_claim_vs_external_source_mismatch":
                feat = cand.get("feature_name") or ""
                is_associated = (
                    feat in feature_names_in_dimension
                    or FEATURE_TO_DIMENSION.get(feat) == dimension
                )
                if is_associated:
                    constraints.append(
                        f"Warning: Discrepancy detected between owned claims and external sources for feature '{feat}'. "
                        f"Ensure owned claims are clearly framed as self-declarations and NOT mixed with external validation."
                    )

    return _dedupe_strings(constraints)


def _abstention_reason(readiness: dict) -> str:
    reason = str(readiness.get("readiness_reason") or "").strip()
    action = str(readiness.get("recommended_action") or "").strip()
    if reason and action:
        return f"{reason} Recommended action: {action}"
    return reason or action or "Dimension is not ready for prompt use."


def _global_constraints() -> list[str]:
    return [
        "This candidate is lab-only and must not be treated as production prompt input.",
        "Generate no prose from blocked, abstain, or review-required dimensions.",
        "Use cited evidence only; do not fill gaps with general knowledge.",
        "Preserve uncertainty, source attribution, and entity boundaries.",
        "Technical, visual-metric, trust/security, noise, unresolved, and review-gated evidence is excluded unless manually approved outside this artifact.",
    ]


def _metadata(packet: dict, dimensions: dict[str, dict]) -> dict:
    included = [name for name, data in dimensions.items() if data["include_in_prompt"]]
    excluded = [name for name, data in dimensions.items() if not data["include_in_prompt"]]
    included_evidence_count = sum(len(data["evidence"]) for data in dimensions.values())
    excluded_evidence_count = sum(len(data["excluded_evidence"]) for data in dimensions.values())
    review_evidence_count = sum(len(data["review_required_evidence"]) for data in dimensions.values())
    current_inputs = packet.get("dimension_evidence_inputs") or {}
    current_input_counts = {
        dimension: len(current_inputs.get(dimension) or [])
        for dimension in DIMENSIONS
    }
    candidate_input_counts = {
        dimension: len(dimensions[dimension]["evidence"])
        for dimension in DIMENSIONS
    }
    return {
        "llm_required": False,
        "deep_research_required": False,
        "runtime_effect": False,
        "prompt_effect": False,
        "source_packet_version": packet.get("version"),
        "included_dimensions": included,
        "excluded_dimensions": excluded,
        "included_evidence_count": included_evidence_count,
        "excluded_evidence_count": excluded_evidence_count,
        "review_required_evidence_count": review_evidence_count,
        "current_dimension_evidence_input_counts": current_input_counts,
        "candidate_dimension_evidence_input_counts": candidate_input_counts,
        "noise_reduction_by_dimension": {
            dimension: {
                "current_inputs": current_input_counts[dimension],
                "candidate_inputs": candidate_input_counts[dimension],
                "excluded_inputs": max(0, current_input_counts[dimension] - candidate_input_counts[dimension]),
            }
            for dimension in DIMENSIONS
        },
    }


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for item in items:
        key = tuple(sorted(item.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _dedupe_included_evidence(items: list[dict]) -> list[dict]:
    """Collapse low-signal duplicates before prompt use.

    Rules (lab-only, deterministic):
    - Drop exact duplicates.
    - Drop query-param URL variants when canonical URL + highly similar text
      already exists.
    - Drop entries with URL-only text (no substantive observation).
    """
    out: list[dict] = []
    seen_exact: set[tuple] = set()
    kept_by_canonical: dict[str, list[dict]] = defaultdict(list)

    for item in items:
        text = str(item.get("text") or "").strip()
        url = str(item.get("url") or "").strip()
        if _is_url_only_text(text, url):
            continue
        exact_key = tuple(sorted(item.items()))
        if exact_key in seen_exact:
            continue

        canonical = _canonicalize_url(url)
        if canonical and _is_low_signal_query_variant(item, kept_by_canonical.get(canonical, [])):
            continue

        seen_exact.add(exact_key)
        out.append(item)
        if canonical:
            kept_by_canonical[canonical].append(item)
    return _collapse_query_variants(out)


def _canonicalize_url(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _is_url_only_text(text: str, url: str) -> bool:
    if not text:
        return True
    if text == url:
        return True
    lowered = text.lower()
    canonical = _canonicalize_url(url).lower()
    if canonical and lowered == canonical:
        return True
    return False


def _is_low_signal_query_variant(item: dict, kept_for_canonical: list[dict]) -> bool:
    url = str(item.get("url") or "").strip()
    if "?" not in url:
        return False
    text = str(item.get("text") or "").strip()
    if not text:
        return True
    for kept in kept_for_canonical:
        kept_text = str(kept.get("text") or "").strip()
        if _text_similarity(text, kept_text) >= 0.75:
            return True
    return False


def _text_similarity(a: str, b: str) -> float:
    a_tokens = {t for t in a.lower().split() if t}
    b_tokens = {t for t in b.lower().split() if t}
    if not a_tokens or not b_tokens:
        return 0.0
    shared = len(a_tokens & b_tokens)
    base = max(len(a_tokens), len(b_tokens))
    return shared / float(base)


def _collapse_query_variants(items: list[dict]) -> list[dict]:
    by_canonical: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        canonical = _canonicalize_url(str(item.get("url") or "").strip())
        by_canonical[canonical].append(item)

    out: list[dict] = []
    for group in by_canonical.values():
        if len(group) <= 1:
            out.extend(group)
            continue
        canonical_items = [item for item in group if "?" not in str(item.get("url") or "")]
        if not canonical_items:
            out.extend(group)
            continue
        keeper = canonical_items[0]
        out.append(keeper)
        keeper_text = str(keeper.get("text") or "").strip()
        for item in group:
            if item is keeper:
                continue
            item_url = str(item.get("url") or "")
            item_text = str(item.get("text") or "").strip()
            if "?" in item_url and _text_similarity(item_text, keeper_text) >= 0.6:
                continue
            out.append(item)
    return out


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def comparison_payload(packet: dict, candidate: dict) -> dict[str, Any]:
    """Return side-by-side data for review artifacts."""
    return {
        "case_id": packet.get("case_id") or "",
        "current_packet_dimension_evidence_inputs": packet.get("dimension_evidence_inputs") or {},
        "candidate_dimensions": candidate.get("dimensions") or {},
        "excluded_dimensions": candidate.get("excluded_dimensions") or [],
        "review_required_dimensions": candidate.get("review_required_dimensions") or [],
        "reason_codes": {
            dimension: (packet.get("dimension_readiness") or {}).get(dimension, {}).get("reason_codes") or []
            for dimension in DIMENSIONS
        },
    }
