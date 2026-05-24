"""Console formatting for discovery metadata."""

from __future__ import annotations


def format_discovery_summary(result: dict) -> list[str]:
    entity = _section(result, "entity_discovery")
    plan = _section(result, "discovery_search_plan")
    preview = _section(result, "discovery_evidence_preview")
    trust_basis = _section(result, "discovery_trust_basis")
    calibration_hint = _section(result, "discovery_calibration_hint")
    if _empty_sections(entity, plan, preview):
        return []

    mode = _mode(entity, plan)
    lines = [
        "--- Discovery ---",
        f"Entity: {_entity_name(entity)}",
        f"Primary entity: {_text(plan, 'primary_entity')}",
        f"Mode: {mode}",
        f"Search scope: {_search_scope_label(mode)}",
        f"Evidence preview: {_preview_status(preview)}",
        f"Owned evidence: {int(preview.get('owned_results_count') or 0)}",
        f"Third-party evidence: {int(preview.get('third_party_results_count') or 0)}",
    ]
    lines.extend(_top_domain_lines(preview))
    lines.extend(_limitation_lines(preview))
    lines.extend(_trust_basis_lines(trust_basis))
    lines.extend(_calibration_hint_lines(calibration_hint))
    return lines


def _section(result: dict, key: str) -> dict:
    value = result.get(key)
    return value if isinstance(value, dict) else {}


def _empty_sections(*sections: dict) -> bool:
    return not any(sections)


def _mode(entity: dict, plan: dict) -> str:
    return str(plan.get("analysis_mode") or entity.get("analysis_scope") or "url_only")


def _entity_name(entity: dict) -> str:
    return _text(entity, "entity_name", "canonical_brand_name", "input_name")


def _text(source: dict, *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value:
            return str(value)
    return "Unknown"


def _preview_status(preview: dict) -> str:
    return "recommended" if preview.get("recommended_to_use_for_scoring") else "insufficient"


def _top_domain_lines(preview: dict) -> list[str]:
    top_domains = preview.get("top_domains") or []
    return [f"Top domains: {', '.join(str(domain) for domain in top_domains[:5])}"] if top_domains else []


def _limitation_lines(preview: dict) -> list[str]:
    limitations = preview.get("limitations") or []
    if not limitations or preview.get("recommended_to_use_for_scoring"):
        return []
    return [f"Limitations: {', '.join(str(item) for item in limitations)}"]


def _trust_basis_lines(trust_basis: dict) -> list[str]:
    if not trust_basis:
        return []
    return [
        f"Evidence basis: {trust_basis.get('basis') or 'url_only'}",
        f"Basis note: {trust_basis.get('user_message') or ''}",
    ]


def _calibration_hint_lines(calibration_hint: dict) -> list[str]:
    if not calibration_hint:
        return []
    profile = calibration_hint.get("recommended_profile") or "base"
    reason = calibration_hint.get("reason") or "unknown"
    return [f"Calibration hint: {profile} ({reason})"]


def _search_scope_label(mode: str) -> str:
    labels = {
        "product_with_parent": "product + parent company",
        "company_brand": "company brand",
        "ecosystem_or_protocol": "ecosystem/protocol",
        "url_only": "url only",
    }
    return labels.get(mode, mode.replace("_", " "))
