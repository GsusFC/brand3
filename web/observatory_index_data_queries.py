"""Persistence and query helpers for Observatory index brand collection."""

from __future__ import annotations

import sqlite3

from src.classification.market_taxonomy import GROUPS
from src.sv9.ranking import domain_from_url

from web.observatory_index_data_model import ObservatoryBrand, ObservatorySource
from web.observatory_index_support import (
    _brand_key,
    _connect,
    _display_name,
    _float_or_none,
    _int_or_none,
    _json_dict,
    _slug,
    _table_exists,
)


def _add_sv9_sources(
    brands: dict[str, ObservatoryBrand],
    conn: sqlite3.Connection,
    *,
    lang: str,
) -> None:
    if not _table_exists(conn, "sv9_scans"):
        return
    rows = conn.execute(
        """
        SELECT id, brand_name, url, source_run_id, brand3_score, created_at
        FROM sv9_scans
        WHERE is_complete = 1
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    for row in rows:
        source = ObservatorySource(
            source="sv9",
            score=_float_or_none(row["brand3_score"]),
            created_at=row["created_at"] or "",
            href=f"/sv9/scan/{row['id']}?lang={lang}",
            brand_name=row["brand_name"] or "",
            url=row["url"] or "",
            source_run_id=_int_or_none(row["source_run_id"]),
            sv9_scan_id=_int_or_none(row["id"]),
        )
        _brand_for_source(brands, source).sources.append(source)


def _add_magnetism_sources(
    brands: dict[str, ObservatoryBrand],
    conn: sqlite3.Connection,
    *,
    lang: str,
) -> None:
    if not _table_exists(conn, "magnetism_scans"):
        return
    rows = conn.execute(
        """
        SELECT
          id,
          COALESCE(
            CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.brand_name') END,
            brand_name
          ) AS brand_name,
          COALESCE(
            CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.url') END,
            url
          ) AS url,
          COALESCE(
            CASE
              WHEN json_valid(raw_payload)
              THEN json_extract(raw_payload, '$.magnetism_score')
            END,
            magnetism_score
          ) AS magnetism_score,
          COALESCE(
            CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.quadrant') END,
            quadrant
          ) AS quadrant,
          COALESCE(
            CASE WHEN json_valid(raw_payload) THEN json_extract(raw_payload, '$.source_run_id') END,
            source_run_id
          ) AS source_run_id,
          created_at
        FROM magnetism_scans
        WHERE status = 'ready'
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    for row in rows:
        source = ObservatorySource(
            source="magnetism",
            score=_float_or_none(row["magnetism_score"]),
            created_at=row["created_at"] or "",
            href=f"/magnetism-scanner/scan/{row['id']}?lang={lang}",
            brand_name=row["brand_name"] or "",
            url=row["url"] or "",
            quadrant=row["quadrant"],
            source_run_id=_int_or_none(row["source_run_id"]),
            magnetism_scan_id=_int_or_none(row["id"]),
        )
        _brand_for_source(brands, source).sources.append(source)


def _add_audit_sources(
    brands: dict[str, ObservatoryBrand],
    conn: sqlite3.Connection,
    *,
    lang: str,
) -> None:
    if not (_table_exists(conn, "web_requests") and _table_exists(conn, "runs")):
        return
    rows = conn.execute(
        """
        SELECT w.token, w.url, w.brand_slug, w.completed_at, w.run_id,
               r.brand_name, r.composite_score
        FROM web_requests w
        LEFT JOIN runs r ON r.id = w.run_id
        WHERE w.status = 'ready'
          AND w.is_public = 1
          AND w.takedown_requested = 0
          AND w.run_id IS NOT NULL
        ORDER BY w.completed_at DESC
        """
    ).fetchall()
    for row in rows:
        brand_name = row["brand_name"] or row["brand_slug"] or ""
        source = ObservatorySource(
            source="audit",
            score=_float_or_none(row["composite_score"]),
            created_at=row["completed_at"] or "",
            href=f"/r/{row['token']}?lang={lang}",
            brand_name=brand_name,
            url=row["url"] or "",
            source_run_id=_int_or_none(row["run_id"]),
            audit_token=row["token"],
        )
        _brand_for_source(brands, source).sources.append(source)


def _attach_classifications(brands: dict[str, ObservatoryBrand], *, db_path: str) -> None:
    with _connect(db_path) as conn:
        if not _table_exists(conn, "brand_market_classifications"):
            return
        rows = conn.execute(
            """
            SELECT brand_key, classification_json, source, requires_human_review, updated_at
            FROM brand_market_classifications
            """
        ).fetchall()
    for row in rows:
        brand = brands.get(str(row["brand_key"] or "").lower())
        if brand is None:
            continue
        payload = _json_dict(row["classification_json"])
        payload["source"] = row["source"] or ""
        payload["requires_human_review"] = bool(row["requires_human_review"])
        payload["updated_at"] = row["updated_at"] or ""
        payload.setdefault("accepted", {group: [] for group in GROUPS})
        payload.setdefault("proposed", {group: [] for group in GROUPS})
        brand.market_classification = payload
        accepted = payload.get("accepted") if isinstance(payload.get("accepted"), dict) else {}
        tags = []
        for group_tags in accepted.values():
            if isinstance(group_tags, list):
                tags.extend(str(tag) for tag in group_tags)
        brand.classification_tags = tags
        primary_category = str(payload.get("primary_category") or "")
        brand.category_label = primary_category if primary_category in tags else (tags[0] if tags else None)
        brand.category = _slug(brand.category_label) if brand.category_label else None


def _attach_profile_overrides(brands: dict[str, ObservatoryBrand], *, db_path: str) -> None:
    with _connect(db_path) as conn:
        if not _table_exists(conn, "brand_profiles"):
            return
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(brand_profiles)").fetchall()
        }
        logo_expr = "logo_url" if "logo_url" in columns else "NULL AS logo_url"
        overrides_expr = (
            "profile_overrides_json"
            if "profile_overrides_json" in columns
            else "'{}' AS profile_overrides_json"
        )
        updated_by_expr = "updated_by" if "updated_by" in columns else "NULL AS updated_by"
        rows = conn.execute(
            f"""
            SELECT brand_key, display_name, domain, canonical_url, {logo_expr},
                   {overrides_expr}, {updated_by_expr}, updated_at
            FROM brand_profiles
            """
        ).fetchall()
    for row in rows:
        brand_key = str(row["brand_key"] or "").lower()
        brand = brands.get(brand_key)
        if brand is None and row["domain"]:
            brand = brands.get(str(row["domain"]).lower())
        if brand is None:
            continue

        overrides = _json_dict(row["profile_overrides_json"])
        if row["display_name"]:
            brand.display_name = str(row["display_name"])
            overrides.setdefault("name", str(row["display_name"]))
        if row["domain"]:
            brand.domain = str(row["domain"]).lower()
            overrides.setdefault("domain", brand.domain)
        if row["canonical_url"]:
            overrides.setdefault("canonical_url", str(row["canonical_url"]))
            overrides.setdefault("official_links", [str(row["canonical_url"])])
        if row["logo_url"]:
            overrides.setdefault("logo_url", str(row["logo_url"]))
        if overrides.get("category"):
            brand.category_label = str(overrides["category"])
            brand.category = _slug(brand.category_label) if brand.category_label else None
        if overrides:
            overrides["updated_at"] = row["updated_at"] or ""
            overrides["updated_by"] = row["updated_by"] or ""
        brand.profile_overrides = overrides


def _brand_for_source(
    brands: dict[str, ObservatoryBrand],
    source: ObservatorySource,
) -> ObservatoryBrand:
    key = _brand_key(source.url, source.brand_name)
    brand = brands.get(key)
    if brand is None:
        brand = ObservatoryBrand(
            brand_key=key,
            display_name=_display_name(source.brand_name, source.url),
            domain=domain_from_url(source.url) or key,
        )
        brands[key] = brand
    return brand


__all__ = [
    "_add_sv9_sources",
    "_add_magnetism_sources",
    "_add_audit_sources",
    "_attach_classifications",
    "_attach_profile_overrides",
    "_brand_for_source",
]
