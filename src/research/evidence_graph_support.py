"""Private helpers for evidence graph construction."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
import re

from src.research.evidence_graph_sources_support import (
    _dict,
    _edit_distance_at_most,
    _external_entity_boundary_collision,
    _host,
    _identity_token,
    _identity_tokens,
    _is_social,
    _normalize_url,
    _root_domain,
    _source_id,
    _source_type_from_entity_role,
    _str_list,
    _unique,
    _validate,
)


def _graph_gaps(sources: dict[str, Any], claims: list[Any]) -> list[str]:
    source_types = {source.source_type for source in sources.values()}
    claim_types = {claim.claim_type for claim in claims if claim.claim_type != "noise"}
    gaps: list[str] = []
    if not source_types.intersection({"owned_about", "owned_product", "owned_security", "owned_docs", "owned_proof"}):
        gaps.append("No strategic owned subpage evidence is present in the current graph.")
    if not source_types.intersection({"press_founder", "third_party_review", "third_party_context"}):
        gaps.append("No third-party contextual evidence is present in the current graph.")
    if "proof" not in claim_types:
        gaps.append("No explicit proof claims were extracted.")
    if not any(claim.supports_blocks for claim in claims):
        gaps.append("No claims are mapped to Brand3 TLDR blocks.")
    return gaps


def _entity_boundary_warnings(sources: dict[str, Any]) -> list[str]:
    if any(_is_entity_boundary_quarantined_source(source) for source in sources.values()):
        return [
            "entity_boundary_collision: external evidence includes near-name collisions; quarantined from TLDR input."
        ]
    return []


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    audit = (_dict(snapshot.get("run")).get("audit") or {})
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _entity_type(entity_packet: dict[str, Any] | None, input_url: str) -> str:
    if entity_packet:
        architecture = str(entity_packet.get("brand_architecture") or "")
        audited_type = str(entity_packet.get("audited_surface_type") or "")
        if architecture == "single_brand_surface":
            return "company"
        if audited_type in {"product_surface", "product_lab"}:
            return "product"
        if audited_type == "secondary_surface":
            return "sub_brand"
    path = (urlparse(input_url).path or "").lower()
    if any(marker in path for marker in ("/blog", "/news", "/article", "/post")):
        return "content"
    host = _host(input_url)
    root = _root_domain(host)
    if host and root and host != root and not host.startswith("www."):
        return "product"
    return "company" if input_url else "unknown"


def _snapshot_web_url(snapshot: dict[str, Any]) -> str:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "web" and isinstance(raw_input.get("payload"), dict):
            return _normalize_url(str(raw_input["payload"].get("canonical_url") or raw_input["payload"].get("url") or ""))
    return _normalize_url(str(_dict(snapshot.get("run")).get("url") or ""))


def _is_entity_boundary_quarantined_source(source: Any) -> bool:
    return source.source_type == "noise" and any(
        str(note).startswith("entity_boundary_collision") for note in source.notes
    )


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _shadow_sources_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_input in snapshot.get("raw_inputs") or []:
        if raw_input.get("source") != "parallel_shadow":
            continue
        payload = raw_input.get("payload")
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        intents = payload.get("intents") if isinstance(payload.get("intents"), dict) else {}
        rows.append(
            {
                "provider": str(payload.get("provider") or "parallel"),
                "mode": str(payload.get("mode") or ""),
                "status": str(payload.get("status") or ""),
                "result_total": int(summary.get("result_total") or 0),
                "unique_domain_count": int(summary.get("unique_domain_count") or 0),
                "unique_domains": _str_list(summary.get("unique_domains"))[:20],
                "intents": {
                    str(name): {
                        "status": str(item.get("status") or ""),
                        "result_count": int(item.get("result_count") or 0),
                        "unique_domains": _str_list(item.get("unique_domains"))[:20],
                        "results": _shadow_results(item.get("results"))[:5],
                    }
                    for name, item in intents.items()
                    if isinstance(item, dict)
                },
                "notes": [
                    "Shadow provider only; not used for scoring, TLDR claims, proof points, or recommendations."
                ],
            }
        )
    return rows


def _shadow_results(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url:
            continue
        rows.append(
            {
                "url": url,
                "title": str(item.get("title") or url),
                "excerpt": str(item.get("excerpt") or ""),
            }
        )
    return rows
