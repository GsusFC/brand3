"""Data loading and hydration for Observatory index views."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.classification.market_taxonomy import GROUPS, canonical_tag
from src.storage.sqlite_store import SQLiteStore

from web.observatory_brand_profile import (
    _build_sv9_status,
    _cached_or_build_brand_profile,
    _clean_profile_overrides,
    _empty_brand_profile,
    _empty_market_classification,
    _empty_sv9_status,
    _market_classification_payload,
)
from web.observatory_index_data_model import ObservatoryBrand
from web.observatory_index_data_queries import (
    _add_audit_sources,
    _add_magnetism_sources,
    _add_sv9_sources,
    _attach_classifications,
    _attach_profile_overrides,
    _brand_for_source,
)
from web.observatory_index_support import (
    _connect,
    _display_name,
    _find_brand,
    _first_text,
    _slug,
    _split_lines,
)


def load_observatory_brands(
    *, db_path: str, lang: str = "es"
) -> dict[str, ObservatoryBrand]:
    brands: dict[str, ObservatoryBrand] = {}
    with _connect(db_path) as conn:
        _add_sv9_sources(brands, conn, lang=lang)
        _add_magnetism_sources(brands, conn, lang=lang)
        _add_audit_sources(brands, conn, lang=lang)
    return brands


def brand_row_to_profile_data(
    brands: dict[str, ObservatoryBrand],
    *,
    db_path: str,
) -> None:
    _attach_classifications(brands, db_path=db_path)
    _attach_profile_overrides(brands, db_path=db_path)


def build_brand_history_payload(brand: ObservatoryBrand, *, db_path: str) -> dict[str, Any]:
    return {
        "brand_key": brand.brand_key,
        "display_name": brand.display_name,
        "domain": brand.domain,
        "category_label": brand.category_label,
        "profile": _cached_or_build_brand_profile(brand, db_path=db_path),
        "market_classification": _market_classification_payload(brand),
        "sv9_status": _build_sv9_status(brand),
        "rows": brand.to_history_rows(),
    }


def blank_brand_history_payload(brand: str) -> dict[str, Any]:
    return {
        "brand_key": brand,
        "display_name": _display_name(brand, brand),
        "domain": brand,
        "category_label": None,
        "profile": _empty_brand_profile(brand),
        "market_classification": _empty_market_classification(brand),
        "sv9_status": _empty_sv9_status(),
        "rows": [],
    }


def persist_brand_profile(
    brand: str,
    overrides: dict[str, Any],
    *,
    db_path: str,
    updated_by: str = "",
) -> str:
    brands = load_observatory_brands(db_path=db_path, lang="es")
    _attach_profile_overrides(brands, db_path=db_path)
    match = _find_brand(brands, brand)

    brand_key = match.brand_key if match is not None else _slug(brand.lower()) or brand.lower()
    display_name = _first_text(
        overrides.get("name"),
        match.display_name if match else _display_name(brand, brand),
    )
    domain = _first_text(overrides.get("domain"), match.domain if match else brand)
    canonical_url = _first_text(
        overrides.get("canonical_url"),
        (overrides.get("official_links") or [""])[0]
        if isinstance(overrides.get("official_links"), list)
        else "",
        f"https://{domain}" if domain else "",
    )

    cleaned = _clean_profile_overrides(overrides)
    now = datetime.now().isoformat()
    store = SQLiteStore(db_path)
    try:
        store.conn.execute(
            """
            INSERT INTO brand_profiles (
                brand_key, display_name, domain, canonical_url, logo_url,
                profile_overrides_json, updated_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_key) DO UPDATE SET
                display_name=excluded.display_name,
                domain=excluded.domain,
                canonical_url=excluded.canonical_url,
                logo_url=excluded.logo_url,
                profile_overrides_json=excluded.profile_overrides_json,
                updated_by=excluded.updated_by,
                updated_at=excluded.updated_at
            """,
            (
                brand_key,
                display_name,
                domain,
                canonical_url,
                cleaned.get("logo_url") or None,
                json.dumps(cleaned, ensure_ascii=True, sort_keys=True),
                updated_by or None,
                now,
                now,
            ),
        )
        store.conn.commit()
    finally:
        store.close()
    return brand_key


def persist_market_classification(
    brand: str,
    form_values: dict[str, Any],
    *,
    db_path: str,
    updated_by: str = "",
) -> str:
    brands = load_observatory_brands(db_path=db_path, lang="es")
    match = _find_brand(brands, brand)
    brand_key = match.brand_key if match is not None else _slug(brand.lower()) or brand.lower()

    accepted = {}
    tags = []
    for group in GROUPS:
        raw_values = form_values.get(group)
        values = raw_values if isinstance(raw_values, list) else _split_lines(str(raw_values or ""))
        group_tags = []
        for value in values:
            canonical = canonical_tag(group, value)
            if canonical is None or canonical in group_tags:
                continue
            group_tags.append(canonical)
            tags.append(
                {
                    "group": group,
                    "tag": canonical,
                    "confidence": "high",
                    "status": "accepted",
                    "evidence_text": "Manual Brand3 review.",
                    "source_url": "",
                    "classifier": "manual",
                    "reason_codes": ["manual_review"],
                }
            )
        accepted[group] = group_tags

    primary_category = str(form_values.get("primary_category") or "").strip()
    if primary_category and not any(
        primary_category in group_tags for group_tags in accepted.values()
    ):
        primary_category = ""
    if not primary_category:
        for group in ("sector_industry", "technology_capability", "business_model"):
            if accepted.get(group):
                primary_category = accepted[group][0]
                break

    payload = {
        "version": "brand3_market_classification_v0_1",
        "brand_key": brand_key,
        "requires_human_review": False,
        "primary_category": primary_category,
        "accepted": accepted,
        "proposed": {group: [] for group in GROUPS},
        "tags": tags,
        "updated_by": updated_by,
    }
    confidence = "high" if tags else "low"
    now = datetime.now().isoformat()

    store = SQLiteStore(db_path)
    try:
        store.conn.execute(
            """
            INSERT INTO brand_market_classifications (
                brand_key, classification_json, confidence, source,
                requires_human_review, updated_at
            )
            VALUES (?, ?, ?, 'manual_review', 0, ?)
            ON CONFLICT(brand_key) DO UPDATE SET
                classification_json=excluded.classification_json,
                confidence=excluded.confidence,
                source=excluded.source,
                requires_human_review=excluded.requires_human_review,
                updated_at=excluded.updated_at
            """,
            (
                brand_key,
                json.dumps(payload, ensure_ascii=True, sort_keys=True),
                confidence,
                now,
            ),
        )
        store.conn.commit()
    finally:
        store.close()
    return brand_key


__all__ = [
    "ObservatoryBrand",
    "load_observatory_brands",
    "brand_row_to_profile_data",
    "build_brand_history_payload",
    "blank_brand_history_payload",
    "persist_brand_profile",
    "persist_market_classification",
    "_add_sv9_sources",
    "_add_magnetism_sources",
    "_add_audit_sources",
    "_attach_classifications",
    "_attach_profile_overrides",
    "_brand_for_source",
]
