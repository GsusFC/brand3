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


def _first_meaningful_text(*candidates: str) -> str:
    for candidate in candidates:
        text = _clean_text(candidate)
        if text:
            return text
    return ""


def _lines_text(lines: Iterable[StrategicEvidenceLine]) -> str:
    return _first_meaningful_text(*(_line.text for _line in lines if _line.text))


def _line_texts(lines: Iterable[StrategicEvidenceLine]) -> list[str]:
    return [_clean_text(line.text) for line in lines if _clean_text(line.text)]


def _tone_summary(lines: list[StrategicEvidenceLine], fallback: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    return fallback


def _infer_audience(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    if offer:
        lowered = offer.lower()
        if "for " in lowered:
            return offer
    return summary


def _infer_outcome(lines: list[StrategicEvidenceLine], offer: str, summary: str) -> str:
    text = _lines_text(lines)
    if text:
        return text
    if offer:
        return offer
    return summary


def _concept_signals(*texts: str) -> list[str]:
    signals: list[str] = []
    for text in texts:
        cleaned = _clean_text(text)
        if not cleaned:
            continue
        if cleaned not in signals:
            signals.append(cleaned)
    return signals[:8]


def _attribute_signals(texts: list[str], snapshot: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    for text in texts:
        cleaned = _clean_text(text)
        if cleaned and cleaned not in signals:
            signals.append(cleaned)
    for item in collect_evidences(snapshot):
        if item.feature_name and item.feature_name not in signals:
            signals.append(item.feature_name)
    return signals[:12]


def _infer_category(
    offer: str,
    product_summary: str,
    company_summary: str,
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    resolved: EntityResolution,
) -> str:
    for text in (offer, product_summary, company_summary, resolved.resolved_entity):
        low = str(text or "").lower()
        if "platform" in low:
            return "platform"
        if "crypto" in low or "token" in low:
            return "crypto"
        if "ai" in low or "llm" in low:
            return "ai"
        if "payments" in low or "billing" in low:
            return "fintech"
    if exa_payload.get("news"):
        return "market_context"
    if context_payload.get("homepage_status"):
        return str(context_payload.get("homepage_status") or "unknown")
    return "unknown"


def _looks_like_crypto_product(text: str) -> bool:
    low = str(text or "").lower()
    return any(marker in low for marker in ("crypto", "token", "wallet", "defi", "web3"))


def _looks_like_page_chrome(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in ("navigation", "menu", "footer", "header", "feed", "article prediction", "page chrome", "breadcrumbs", "sign in", "log in", "top of page")
    )


def _looks_like_press_or_founder_text(text: str) -> bool:
    low = text.lower()
    return any(
        marker in low
        for marker in (
            "founder",
            "founders",
            "press",
            "interview",
            "announc",
            "launch",
            "raised",
            "raises",
            "exit",
            "acquisition",
            "acquired",
        )
    )


def _filter_values_signals(lines: list[StrategicEvidenceLine]) -> list[str]:
    values: list[str] = []
    for line in lines:
        text = _clean_text(line.text)
        if not text:
            continue
        if text not in values:
            values.append(text)
    return values


def _clean_text(value: str) -> str:
    text = str(value or "").strip()
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = " ".join(text.split())
    return text.strip(" -|•*")


def _unique_texts(values: list[str] | tuple[str, ...] | Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(str(value or ""))
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _normalize_url(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    return f"{parsed.scheme or 'https'}://{host}{path}".rstrip("/")


def _extract_host(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("@")[-1].split(":")[0].lower()
    return host[4:] if host.startswith("www.") else host


def _source_type_from_url(url: str, *, brand_domain: str, text: str = "", source: str = "") -> str:
    normalized = _normalize_url(url)
    host = _extract_host(normalized)
    text_low = (text or "").lower()
    path = (urlparse(normalized).path or "").lower()
    if source == "social" or host.endswith(("linkedin.com", "x.com", "twitter.com", "instagram.com", "youtube.com", "tiktok.com", "facebook.com", "github.com")):
        return "social"
    if brand_domain and (host == brand_domain or host.endswith("." + brand_domain)):
        role = _site_role_from_url(normalized)
        if role == "owned_official":
            return "owned_official"
        return role
    if any(marker in text_low for marker in ("founder", "founders", "interview", "press", "announc", "launch", "raises", "raised", "acquired", "acquisition")):
        return "press_or_founder"
    if any(marker in text_low for marker in ("testimonial", "testimonials", "customer", "customers", "client", "clients", "trusted by", "used by", "case study", "case studies", "review", "reviews", "proof")):
        return "proof_point"
    if any(marker in path for marker in ("/customers", "/client", "/case", "/stories", "/reviews", "/testimonials")):
        return "proof_point"
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/feed", "/resources")):
        return "noise"
    return "noise"


def _site_role_from_url(url: str) -> str:
    parsed = urlparse(_normalize_url(url))
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if path == "/":
        return "owned_official"
    if any(marker in path for marker in ("/about", "/mission", "/manifesto", "/team", "/company", "/story", "/principles")):
        return "owned_about"
    if any(marker in path for marker in ("/privacy", "/security", "/trust", "/legal", "/terms", "/compliance")):
        return "owned_security_trust"
    if any(marker in path for marker in ("/product", "/products", "/platform", "/solution", "/solutions", "/app", "/pricing", "/plans", "/demo", "/beta", "/lab", "/natureos")):
        return "owned_product"
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/feed", "/resources")):
        return "noise"
    if any(marker in path for marker in ("/customers", "/clients", "/case", "/stories", "/reviews", "/testimonials", "/casos", "/opiniones")):
        return "proof_point"
    return "owned_official"


def _resolve_entity_resolution(
    *,
    input_url: str,
    brand_name: str,
    run: dict[str, Any],
    entity_packet: dict[str, Any] | None,
    web_payload: dict[str, Any],
    exa_payload: dict[str, Any],
    context_payload: dict[str, Any],
    social_payload: dict[str, Any],
    strategic_packet,
) -> EntityResolution:
    host = _extract_host(input_url)
    root = _root_domain(host)
    subdomain = _subdomain(host, root)
    parent_brand = ""
    notes: list[str] = []
    if entity_packet:
        parent_brand = str(entity_packet.get("parent_brand") or "").strip()
        if parent_brand:
            notes.append("Parent brand reused from entity research packet.")
        if entity_packet.get("limitations"):
            notes.extend(str(item) for item in entity_packet.get("limitations") if str(item).strip())
    if not parent_brand and root and subdomain and subdomain not in {"www", "m"}:
        parent_brand = _parent_name_from_root(root)
        notes.append("Parent brand inferred from subdomain/root domain relationship.")

    resolved_name = (
        str((entity_packet or {}).get("entity_name") or "").strip()
        or str((entity_packet or {}).get("product_name") or "").strip()
        or str((entity_packet or {}).get("canonical_brand_name") or "").strip()
        or str(run.get("brand_name") or "").strip()
        or _parent_name_from_root(root)
        or input_url
    )
    entity_type = _classify_entity_type(
        input_url=input_url,
        brand_name=brand_name,
        entity_packet=entity_packet,
        web_payload=web_payload,
    )

    surface_role = "audited_surface"
    entity_scope = "audited_surface"
    if parent_brand and entity_type in {"product", "sub_brand"}:
        entity_scope = "product_surface"
        surface_role = "product_surface"
    if entity_type == "content":
        entity_scope = "content_surface"
        surface_role = "content_surface"
    if entity_type == "campaign":
        entity_scope = "campaign_surface"
        surface_role = "campaign_surface"

    confidence = "medium"
    if entity_packet and str(entity_packet.get("confidence") or "").strip():
        confidence = str(entity_packet.get("confidence") or "medium")
    elif parent_brand and entity_type in {"product", "sub_brand"}:
        confidence = "medium"
    elif entity_type == "company":
        confidence = "medium"
    else:
        confidence = "low"

    canonical_url = (
        _payload_url_impl(web_payload)
        or _normalize_url(str(run.get("url") or ""))
        or input_url
    )
    if exa_payload.get("news"):
        notes.append("External news evidence available; keep it in founder_or_press_context, not tone.")
    if context_payload.get("homepage_status"):
        notes.append(f"Context scan status={context_payload.get('homepage_status')}.")
    if social_payload and social_payload.get("profiles_found"):
        notes.append("Social profiles were collected in the audit snapshot.")
    if strategic_packet.warnings:
        notes.extend(str(item) for item in strategic_packet.warnings if str(item).strip())

    return EntityResolution(
        resolved_entity=resolved_name,
        entity_type=entity_type,
        canonical_url=canonical_url,
        parent_brand=parent_brand,
        surface_role=surface_role,
        entity_scope=entity_scope,
        confidence=confidence,
        notes=_unique_texts(notes),
    )


def _classify_entity_type(
    *,
    input_url: str,
    brand_name: str,
    entity_packet: dict[str, Any] | None,
    web_payload: dict[str, Any],
) -> str:
    if entity_packet:
        architecture = str(entity_packet.get("brand_architecture") or "")
        audited_type = str(entity_packet.get("audited_surface_type") or "")
        if architecture == "single_brand_surface":
            return "company"
        if audited_type in {"product_surface", "product_lab"}:
            return "product"
        if audited_type == "secondary_surface":
            return "sub_brand"
        if str(entity_packet.get("parent_brand") or ""):
            return "product"

    host = _extract_host(input_url)
    root = _root_domain(host)
    subdomain = _subdomain(host, root)
    path = (urlparse(input_url).path or "").lower()
    if any(marker in path for marker in ("/blog", "/news", "/press", "/article", "/post", "/resources")):
        return "content"
    if any(marker in path for marker in ("/campaign", "/promo", "/launch", "/event", "/sale")):
        return "campaign"
    if subdomain and subdomain not in {"www", "m"}:
        return "product"
    if root and (brand_name or root):
        return "company"
    return "unknown"


def _subdomain(host: str, root: str) -> str:
    if not host or not root or host == root:
        return ""
    suffix = f".{root}"
    if not host.endswith(suffix):
        return ""
    return host[: -len(suffix)].split(".")[-1]


def _parent_name_from_root(root: str) -> str:
    if not root:
        return ""
    label = root.split(".")[0]
    return label.replace("-", " ").title()


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])
