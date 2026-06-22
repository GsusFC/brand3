"""Utility helpers for observatory index assembly.

These helpers are intentionally internal and remain prefixed with underscore to
allow the main implementation to stay focused on orchestration.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from typing import Any

from src.sv9.ranking import domain_from_url


def _json_dict(value: object) -> dict[str, Any]:
    try:
        payload = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _split_lines(value: str) -> list[str]:
    return [
        line.strip()
        for line in str(value or "").replace(",", "\n").splitlines()
        if line.strip()
    ]


def _first_text(*values: Any) -> str:
    for value in values:
        text = _clean_profile_text(value)
        if text:
            return text
    return ""


def _clean_profile_text(value: Any, *, limit: int = 420) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"Source:\s*https?://\S+\s*#\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    boundary = max(
        text.rfind(". ", 0, limit),
        text.rfind(" — ", 0, limit),
        text.rfind(" - ", 0, limit),
    )
    if boundary < 160:
        boundary = limit
    return text[:boundary].rstrip(" .,-—") + "..."


def _str_list(raw: Any, *, limit: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for value in raw:
        text = str(value or "").strip()
        if text:
            out.append(text[:180])
        if len(out) >= limit:
            break
    return out


def _unique_links(values: list[Any]) -> list[str]:
    from urllib.parse import urlparse

    out = []
    seen = set()
    for value in values:
        url = str(value or "").strip()
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        normalized = url.split("#", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _brand_key(url: str, name: str) -> str:
    domain = domain_from_url(url)
    if domain:
        return domain
    text = (name or url or "unknown").strip().lower()
    if "." in text:
        maybe_domain = domain_from_url(text)
        if maybe_domain:
            return maybe_domain
    return _slug(text) or "unknown"


def _find_brand(
    brands: dict[str, Any],
    value: str,
) -> Any | None:
    raw = (value or "").strip().lower()
    if not raw:
        return None
    candidates = {raw}
    domain = domain_from_url(raw)
    if domain:
        candidates.add(domain)
        candidates.add(domain.split(".", 1)[0])
    if "." in raw:
        parts = raw.split(".")
        if len(parts) >= 2:
            candidates.add(parts[-2])
    slug = _slug(raw)
    if slug:
        candidates.add(slug)

    for candidate in candidates:
        if candidate in brands:
            return brands[candidate]
    for brand in brands.values():
        domain_root = brand.domain.split(".", 1)[0] if brand.domain else ""
        if brand.brand_key in candidates or domain_root in candidates:
            return brand
        if _slug(brand.display_name) in candidates:
            return brand
    return None


def _looks_like_domain(value: str) -> bool:
    return "." in value or "/" in value or "://" in value


def _titleize(value: str) -> str:
    text = value.replace("-", " ").replace("_", " ").strip()
    return " ".join(
        part.upper() if len(part) <= 3 and part.isalpha() else part.capitalize()
        for part in text.split()
    )


def _display_name(name: str, url: str) -> str:
    raw = (name or "").strip()
    if raw and not _looks_like_domain(raw):
        return _titleize(raw)
    domain = domain_from_url(url or raw)
    if domain:
        return _titleize(domain.split(".", 1)[0])
    return _titleize(raw or "unknown")


def _timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00").replace(" ", "T")
        ).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _timestamp_sort(value: str | None) -> float:
    dt = _timestamp(value)
    if dt == datetime.min:
        return 0.0
    return dt.timestamp()


def _compact_date(value: str | None) -> str:
    dt = _timestamp(value)
    if dt == datetime.min:
        return ""
    return dt.strftime("%y/%m/%d")


def _score_compact(value: float | None) -> str:
    if value is None:
        return "n/a"
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _slug(value: str | None) -> str:
    text = str(value or "").strip().lower()
    out = []
    previous_dash = False
    for char in text:
        if char.isalnum():
            out.append(char)
            previous_dash = False
        elif not previous_dash:
            out.append("-")
            previous_dash = True
    return "".join(out).strip("-")
