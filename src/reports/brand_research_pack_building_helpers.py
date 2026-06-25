"""Helper functions for brand research pack building."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from src.reports.brand_research_pack_sources import (
    EntityResolution,
    ResearchSource,
    _classify_entity_type as _classify_entity_type_impl,
    _extract_host as _extract_host_impl,
    _normalize_url as _normalize_url_impl,
    _parent_name_from_root as _parent_name_from_root_impl,
    _resolve_entity_resolution as _resolve_entity_resolution_impl,
    _root_domain as _root_domain_impl,
    _site_role_from_url as _site_role_from_url_impl,
    _source_type_from_url as _source_type_from_url_impl,
    _subdomain as _subdomain_impl,
    _payload_url as _payload_url_impl,
    _str_list as _str_list_impl,
)
from src.reports.brand_research_pack_types import ResearchEvidence
from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import StrategicEvidenceLine
from src.reports.brand_research_pack_building_helpers_support import (
    _attribute_signals,
    _clean_text,
    _concept_signals,
    _filter_values_signals,
    _first_meaningful_text,
    _infer_audience,
    _infer_category as _infer_category_support,
    _infer_outcome,
    _line_texts,
    _lines_text,
    _looks_like_crypto_product,
    _looks_like_page_chrome,
    _looks_like_press_or_founder_text,
    _tone_summary,
    _unique_texts,
)

_normalize_url = _normalize_url_impl
_extract_host = _extract_host_impl
_source_type_from_url = _source_type_from_url_impl
_site_role_from_url = _site_role_from_url_impl
_resolve_entity_resolution = _resolve_entity_resolution_impl
_classify_entity_type = _classify_entity_type_impl
_subdomain = _subdomain_impl
_parent_name_from_root = _parent_name_from_root_impl
_root_domain = _root_domain_impl


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
                "unique_domains": _str_list_impl(summary.get("unique_domains"))[:20],
                "intents": {
                    str(name): {
                        "status": str(item.get("status") or ""),
                        "result_count": int(item.get("result_count") or 0),
                        "unique_domains": _str_list_impl(item.get("unique_domains"))[:20],
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


def _build_evidence_list(
    lines: list[StrategicEvidenceLine],
    *,
    kind: str,
    default_topic: str,
) -> list[ResearchEvidence]:
    evidences: list[ResearchEvidence] = []
    seen: set[tuple[str, str, str]] = set()
    for line in lines:
        source_url = _normalize_url(str(line.url or ""))
        text = str(line.text or "").strip()
        if not text and not source_url:
            continue
        source_type = _evidence_source_type(line, text=text, url=source_url)
        key = (text.lower(), source_url, source_type)
        if key in seen:
            continue
        seen.add(key)
        evidences.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=source_url,
                source_type=source_type,
                source_label=str(line.feature_name or default_topic or ""),
                surface_role=str(line.surface_role or ""),
                entity_scope=str(line.entity_scope or ""),
                topic=str(line.dimension or default_topic or ""),
                confidence="high" if source_url else "medium",
            )
        )
    return evidences


def _evidence_source_type(line: StrategicEvidenceLine, *, text: str, url: str) -> str:
    source_type = str(line.source_type or "").strip()
    if source_type:
        return source_type
    if str(line.surface_role or "").strip() == "noise" or _looks_like_page_chrome(text):
        return "noise"
    if _looks_like_press_or_founder_text(text):
        return "press_or_founder"
    if url:
        return _source_type_from_url_impl(url, brand_domain=str(line.source_domain or ""), text=text)
    return "noise"


def _build_supplemental_context_evidence(
    snapshot: dict[str, Any],
    existing: list[ResearchEvidence],
) -> list[ResearchEvidence]:
    seen = {(item.text.lower(), item.source_url, item.source_type) for item in existing}
    items: list[ResearchEvidence] = []
    for evidence in collect_evidences(snapshot):
        if not evidence.url:
            continue
        source_type = _source_type_from_url(
            evidence.url,
            brand_domain=_extract_host(str((snapshot.get("run") or {}).get("url") or "")),
            text=str(evidence.quote or ""),
            source=str(evidence.source_type or ""),
        )
        kind = "proof" if source_type == "proof_point" else "context" if source_type == "press_or_founder" else "noise"
        text = str(evidence.quote or evidence.url or "").strip()
        key = (text.lower(), _normalize_url(evidence.url), source_type)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            ResearchEvidence(
                text=text or evidence.url,
                kind=kind,
                source_url=_normalize_url(evidence.url),
                source_type=source_type,
                source_label="supplemental_context",
                surface_role="evidence",
                entity_scope="evidence",
                topic=str(evidence.dimension or "context"),
                confidence="medium" if source_type != "noise" else "low",
                notes=[f"Derived from collect_evidences ({evidence.dimension})."],
            )
        )
    return items


def _build_noise_list(rejected: list[dict[str, Any]], web_payload: dict[str, Any]) -> list[ResearchEvidence]:
    noise: list[ResearchEvidence] = []
    for item in rejected:
        text = str(item.get("text") or item.get("quote") or "").strip()
        if not text:
            continue
        noise.append(
            ResearchEvidence(
                text=text,
                kind="noise",
                source_url=_payload_url_impl(web_payload),
                source_type="noise",
                source_label=str(item.get("reason") or "noise"),
                surface_role="noise",
                entity_scope="noise",
                topic=str(item.get("dimension") or "noise"),
                confidence="low",
                notes=_str_list_impl(item.get("notes")),
            )
        )
    return noise


def _build_evidence_from_source_map(
    source_map: dict[str, ResearchSource],
    *,
    allowed_types: set[str],
    kind: str,
) -> list[ResearchEvidence]:
    items: list[ResearchEvidence] = []
    for source in source_map.values():
        if source.source_type not in allowed_types:
            continue
        text = source.title or source.label or source.url
        if not text:
            continue
        items.append(
            ResearchEvidence(
                text=text,
                kind=kind,
                source_url=source.url,
                source_type=source.source_type,
                source_label=source.label or source.source_type,
                surface_role=source.surface_role,
                entity_scope=source.entity_scope,
                topic=source.surface_role or source.entity_scope or kind,
                confidence="high",
                notes=list(source.notes),
            )
        )
    return items


def _infer_category(
    offer: str,
    product_summary: str,
    company_summary: str,
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    resolved: EntityResolution,
) -> str:
    return _infer_category_support(offer, product_summary, company_summary, exa_payload, context_payload, resolved)
