"""Shared text/URL helpers for Brand Research Pack source modeling."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from src.reports.derivation import collect_evidences
from src.reports.entity_research_packet import entity_scope_for_url, surface_role_for_url


def _clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = text.strip(" -|•*")
    return text


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


def _looks_like_page_chrome(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in ("navigation", "menu", "footer", "header", "feed", "article prediction", "page chrome", "breadcrumbs", "sign in", "log in", "top of page"))


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


def _primary_web_text(payload: dict[str, Any]) -> str:
    markdown = str(payload.get("markdown_content") or payload.get("content") or "").strip()
    if not markdown:
        return ""
    primary = markdown.split("\n---\n", 1)[0]
    lines = [_clean_text(line) for line in primary.splitlines()]
    for index, line in enumerate(lines):
        if not line or _looks_like_page_chrome(line):
            continue
        if len(line) >= 24 or any(mark in line for mark in (".", ",", ":", "?", "!", " is ", " are ")):
            return _clean_text(" ".join(lines[index:]))
    return _clean_text(primary)


def _confidence_notes(
    *,
    resolved,
    source_map,
    proof_points,
    founder_or_press_context,
    web_payload,
    entity_packet,
) -> list[str]:
    notes = list(resolved.notes)
    if resolved.parent_brand:
        notes.append(f"Parent brand detected: {resolved.parent_brand}.")
    if resolved.entity_type in {"product", "sub_brand"} and resolved.surface_role == "product_surface":
        notes.append("Treat the input as a product surface, not as the whole company brand.")
    if not proof_points:
        notes.append("No direct proof-point evidence surfaced in the snapshot.")
    if not founder_or_press_context:
        notes.append("No founder or press context surfaced in the snapshot.")
    if web_payload and not _primary_web_text(web_payload):
        notes.append("Web payload did not provide a clean primary page text block.")
    owned_count = sum(1 for source in source_map.values() if source.source_type.startswith("owned"))
    if owned_count:
        notes.append(f"{owned_count} owned source(s) were retained in the pack.")
    if entity_packet and entity_packet.get("limitations"):
        notes.extend(str(item) for item in entity_packet.get("limitations") if str(item).strip())
    return _unique_texts(notes)


def _evidence_gaps(
    *,
    company_summary: str,
    product_summary: str,
    offer: str,
    audience: str,
    outcome: str,
    proof_points: list[Any],
    mission: str,
    official_urls: list[str],
) -> list[str]:
    gaps = []
    if not offer:
        gaps.append("No clear offer sentence was extracted.")
    if not audience:
        gaps.append("Audience remains thin or absent.")
    if not outcome:
        gaps.append("Outcome language remains thin or absent.")
    if not mission:
        gaps.append("Mission/purpose language remains thin or absent.")
    if not proof_points:
        gaps.append("No proof-point evidence was retained.")
    if not company_summary and not product_summary:
        gaps.append("No usable homepage or summary sentence was extracted.")
    if len(official_urls) <= 1:
        gaps.append("Only one official URL was retained; parent context may still be incomplete.")
    return gaps


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _entity_packet(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") == "entity_research_packet" and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    run = snapshot.get("run") or {}
    audit = run.get("audit") if isinstance(run.get("audit"), dict) else {}
    packet = audit.get("entity_research_packet") if isinstance(audit, dict) else None
    return packet if isinstance(packet, dict) else None


def _payload_for_source(raw_inputs: list[dict[str, Any]], source: str) -> dict[str, Any]:
    for raw_input in reversed(raw_inputs):
        if raw_input.get("source") == source and isinstance(raw_input.get("payload"), dict):
            return raw_input["payload"]
    return {}


def _payload_url(payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            return _normalize_url(value)
    return ""


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


def _root_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


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


def _web_urls(payload: dict[str, Any], *, fallback: str = "") -> list[str]:
    urls = []
    for key in ("canonical_url", "url", "page_url", "input_url"):
        value = str(payload.get(key) or "").strip()
        if value:
            urls.append(_normalize_url(value))
    for value in payload.get("owned_fallback_urls") or []:
        if isinstance(value, str) and value.strip():
            urls.append(_normalize_url(value))
    if not urls and fallback:
        urls.append(_normalize_url(fallback))
    return _unique_texts(urls)


def _social_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for value in payload.get("profiles_found") or []:
        if isinstance(value, str) and value.strip():
            urls.append(_normalize_url(value))
    return _unique_texts(urls)


def _competitor_urls(payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in payload.get("competitors") or []:
        if isinstance(item, dict):
            value = str(item.get("url") or "").strip()
            if value:
                urls.append(_normalize_url(value))
    return _unique_texts(urls)


def _validate_entity_type(value: str) -> None:
    if value not in {
        "company",
        "brand",
        "product",
        "sub_brand",
        "campaign",
        "content",
        "unknown",
    }:
        raise ValueError("entity_type must be one of ['brand', 'campaign', 'company', 'content', 'product', 'sub_brand', 'unknown']")
