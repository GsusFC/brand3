"""Brand profile helpers for service-layer payloads."""

from __future__ import annotations

from urllib.parse import urlparse

from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "brand"


def _derive_brand_profile(brand_name: str | None, url: str | None) -> dict[str, object]:
    parsed = urlparse(url if url and "://" in url else f"https://{url}" if url else "")
    domain = (parsed.netloc or parsed.path or "").strip().lower() or None
    if domain and domain.startswith("www."):
        domain = domain[4:]
    logo_key = _slugify(brand_name) if brand_name else None
    if not logo_key and domain:
        logo_key = _slugify(domain.split(".")[0])
    return {
        "name": brand_name,
        "domain": domain,
        "logo_key": logo_key,
        "logo_url": None,
    }


def _build_brand_profile(
    brand_name: str | None,
    url: str | None,
    store: SQLiteStore | None = None,
) -> dict[str, object]:
    should_close = False
    if store is None:
        try:
            store = SQLiteStore(BRAND3_DB_PATH)
            should_close = True
        except Exception:
            return _derive_brand_profile(brand_name, url)
    try:
        return store.get_brand_profile(brand_name, url)
    except Exception:
        return _derive_brand_profile(brand_name, url)
    finally:
        if should_close:
            store.close()
