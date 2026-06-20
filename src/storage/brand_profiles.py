"""Brand profile helpers for SQLite persistence rows."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def slugify(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    slug = "-".join(part for part in cleaned.split("-") if part)
    return slug or None


def infer_logo_key(brand_name: str | None, domain: str | None) -> str | None:
    brand_slug = slugify(brand_name)
    if brand_slug:
        return brand_slug
    if not domain:
        return None
    root = domain.split(".")[0]
    return slugify(root)


def build_brand_profile(
    brand_name: str | None,
    url: str | None,
    logo_url: str | None = None,
) -> dict[str, Any]:
    domain = extract_domain(url)
    return {
        "name": brand_name,
        "domain": domain,
        "logo_key": infer_logo_key(brand_name, domain),
        "logo_url": logo_url,
    }


def brand_profile_from_record(
    record: dict[str, Any],
    *,
    name_field: str = "brand_name",
    url_field: str = "url",
    domain_field: str = "brand_domain",
    logo_key_field: str = "brand_logo_key",
    logo_url_field: str = "brand_logo_url",
) -> dict[str, Any]:
    profile = build_brand_profile(
        record.get(name_field),
        record.get(url_field),
        record.get(logo_url_field),
    )
    if record.get(domain_field):
        profile["domain"] = record[domain_field]
    if record.get(logo_key_field):
        profile["logo_key"] = record[logo_key_field]
    if record.get(logo_url_field):
        profile["logo_url"] = record[logo_url_field]
    return profile
