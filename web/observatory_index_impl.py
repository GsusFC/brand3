"""Unified Observatory index.

One row per normalized brand. The row chooses the best available score in this
order: SV9, Magnetism, Brand Audit. Scanner history remains available as count
and links; this module does not mutate scans or scores.
"""


import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import quote

from src.classification.market_taxonomy import GROUPS, canonical_tag
from src.config import BRAND3_DB_PATH
from src.storage.sqlite_store import SQLiteStore
from src.sv9.ranking import domain_from_url
from web.observatory_index_support import (
    _brand_key,
    _compact_date,
    _connect,
    _display_name,
    _find_brand,
    _first_text,
    _float_or_none,
    _int_or_none,
    _json_dict,
    _table_exists,
    _score_compact,
    _slug,
    _split_lines,
    _str_list,
    _timestamp,
    _timestamp_sort,
    _unique_links,
)
from web.observatory_brand_profile import (
    _apply_profile_overrides,
    _cached_or_build_brand_profile,
    _clean_profile_overrides,
    _empty_brand_profile,
    _empty_market_classification,
    _empty_sv9_status,
    _build_recommended_research_pack,
    _build_sv9_status,
    _market_classification_payload,
    _sv9_generate_scan_id,
)

build_recommended_research_pack = _build_recommended_research_pack


SOURCE_PRIORITY = {"sv9": 0, "magnetism": 1, "audit": 2}
ALLOWED_SORTS = {"newest", "score_desc", "score_asc", "scans_desc"}


@dataclass
class ObservatorySource:
    source: str
    score: float | None
    created_at: str
    href: str
    brand_name: str
    url: str
    quadrant: str | None = None
    source_run_id: int | None = None
    sv9_scan_id: int | None = None
    magnetism_scan_id: int | None = None
    audit_token: str | None = None
    status: str | None = None
    canonical_status: str | None = None


@dataclass
class ObservatoryBrand:
    brand_key: str
    display_name: str
    domain: str
    sources: list[ObservatorySource] = field(default_factory=list)
    category: str | None = None
    category_label: str | None = None
    classification_tags: list[str] = field(default_factory=list)
    market_classification: dict[str, Any] = field(default_factory=dict)
    profile_overrides: dict[str, Any] = field(default_factory=dict)

    @property
    def latest_date(self) -> str:
        return max((source.created_at for source in self.sources), default="")

    @property
    def primary(self) -> ObservatorySource:
        return sorted(
            self.sources,
            key=lambda source: (
                SOURCE_PRIORITY.get(source.source, 99),
                -_timestamp_sort(source.created_at),
            ),
        )[0]

    def to_row(self, *, lang: str = "es") -> dict[str, Any]:
        primary = self.primary
        needs_sv9 = primary.source != "sv9"
        brand_ref = self.domain or self.brand_key
        return {
            "brand_key": self.brand_key,
            "display_name": self.display_name,
            "domain": self.domain,
            "brand_href": f"/brand/{quote(brand_ref, safe='')}?lang={lang}",
            "latest_date": self.latest_date,
            "compact_date": _compact_date(self.latest_date),
            "score": primary.score,
            "score_compact": _score_compact(primary.score),
            "score_model": primary.source,
            "quadrant": primary.quadrant or "",
            "category": self.category,
            "category_label": self.category_label,
            "classification_tags": list(self.classification_tags),
            "classification_tag_keys": sorted(
                {_slug(tag) for tag in self.classification_tags if _slug(tag)}
            ),
            "scan_count": len(self.sources),
            "primary_href": primary.href,
            "needs_sv9": needs_sv9,
            "sv9_generate_scan_id": _sv9_generate_scan_id(self.sources) if needs_sv9 else None,
            "legacy_source_run_id": primary.source_run_id if needs_sv9 else None,
        }

    def to_history_rows(self) -> list[dict[str, Any]]:
        rows = []
        for source in sorted(
            self.sources,
            key=lambda item: _timestamp(item.created_at),
            reverse=True,
        ):
            rows.append(
                {
                    "brand_key": self.brand_key,
                    "display_name": self.display_name,
                    "domain": self.domain,
                    "date": _compact_date(source.created_at),
                    "created_at": source.created_at,
                    "score": source.score,
                    "score_compact": _score_compact(source.score),
                    "score_model": source.source,
                    "quadrant": source.quadrant or "",
                    "category": self.category,
                    "category_label": self.category_label,
                    "href": source.href,
                    "source_run_id": source.source_run_id,
                    "sv9_scan_id": source.sv9_scan_id,
                    "magnetism_scan_id": source.magnetism_scan_id,
                    "audit_token": source.audit_token,
                    "status": source.status,
                    "canonical_status": source.canonical_status,
                }
            )
        return rows


def build_observatory_index(
    *,
    db_path: str = BRAND3_DB_PATH,
    query: str | None = None,
    sort: str = "newest",
    category: str | None = None,
    tag: str | None = None,
    page: int = 1,
    per_page: int = 25,
    lang: str = "es",
) -> dict[str, Any]:
    """Build the paginated, deduped Observatory model."""
    sort = sort if sort in ALLOWED_SORTS else "newest"
    page = max(1, int(page or 1))
    per_page = max(1, int(per_page or 25))

    brands = _load_brand_sources(db_path=db_path, lang=lang)
    _attach_classifications(brands, db_path=db_path)
    _attach_profile_overrides(brands, db_path=db_path)
    rows = [brand.to_row(lang=lang) for brand in brands.values() if brand.sources]
    rows = _filter_rows(rows, query=query)
    categories = _category_options(rows)
    tags = _tag_options(rows)
    rows = _filter_rows(rows, category=category, tag=_slug(tag or ""))
    rows = _sort_rows(rows, sort=sort)

    total = len(rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page
    return {
        "rows": rows[offset : offset + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "query": query or "",
        "sort": sort,
        "category": category,
        "tag": _slug(tag or ""),
        "categories": categories,
        "tags": tags,
    }


def build_observatory_brand_history(
    brand: str,
    *,
    db_path: str = BRAND3_DB_PATH,
    lang: str = "es",
) -> dict[str, Any]:
    """Build unified history for one brand/domain."""
    brands = _load_brand_sources(db_path=db_path, lang=lang)
    _attach_classifications(brands, db_path=db_path)
    _attach_profile_overrides(brands, db_path=db_path)
    match = _find_brand(brands, brand)
    if match is None:
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
    return {
        "brand_key": match.brand_key,
        "display_name": match.display_name,
        "domain": match.domain,
        "category_label": match.category_label,
        "profile": _cached_or_build_brand_profile(match, db_path=db_path),
        "market_classification": _market_classification_payload(match),
        "sv9_status": _build_sv9_status(match),
        "rows": match.to_history_rows(),
    }


def save_brand_profile_overrides(
    brand: str,
    overrides: dict[str, Any],
    *,
    db_path: str = BRAND3_DB_PATH,
    updated_by: str = "",
) -> str:
    """Persist human overrides for a brand profile and return its brand key."""
    brands = _load_brand_sources(db_path=db_path, lang="es")
    _attach_profile_overrides(brands, db_path=db_path)
    match = _find_brand(brands, brand)
    brand_key = match.brand_key if match is not None else _slug(brand.lower()) or brand.lower()
    display_name = _first_text(overrides.get("name"), match.display_name if match else _display_name(brand, brand))
    domain = _first_text(overrides.get("domain"), match.domain if match else brand)
    canonical_url = _first_text(
        overrides.get("canonical_url"),
        (overrides.get("official_links") or [""])[0] if isinstance(overrides.get("official_links"), list) else "",
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


def save_brand_market_classification(
    brand: str,
    form_values: dict[str, Any],
    *,
    db_path: str = BRAND3_DB_PATH,
    updated_by: str = "",
) -> str:
    """Persist manually accepted market classification tags for a brand."""
    brands = _load_brand_sources(db_path=db_path, lang="es")
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


def _load_brand_sources(*, db_path: str, lang: str) -> dict[str, ObservatoryBrand]:
    brands: dict[str, ObservatoryBrand] = {}
    with _connect(db_path) as conn:
        _add_sv9_sources(brands, conn, lang=lang)
        _add_magnetism_sources(brands, conn, lang=lang)
        _add_audit_sources(brands, conn, lang=lang)
    return brands


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
        brand.category_label = primary_category if primary_category in tags else (
            tags[0] if tags else None
        )
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


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[dict[str, Any]]:
    out = rows
    q = (query or "").strip().lower()
    if q:
        out = [
            row
            for row in out
            if q in " ".join(
                str(part or "")
                for part in (
                    row.get("display_name"),
                    row.get("domain"),
                    row.get("category_label"),
                    " ".join(row.get("classification_tags") or []),
                    row.get("score_model"),
                )
            ).lower()
        ]
    if category:
        out = [row for row in out if row.get("category") == category]
    if tag:
        out = [row for row in out if tag in (row.get("classification_tag_keys") or [])]
    return out


def _category_options(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    options = {}
    for row in rows:
        key = row.get("category")
        label = row.get("category_label")
        if key and label:
            options[str(key)] = {"label": str(label)}
    return dict(sorted(options.items(), key=lambda item: item[1]["label"].lower()))


def _tag_options(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    for row in rows:
        labels = row.get("classification_tags") or []
        for label in labels:
            key = _slug(str(label))
            if not key or not label:
                continue
            item = options.setdefault(str(key), {"label": str(label), "count": 0})
            item["count"] = int(item["count"]) + 1
    return dict(sorted(options.items(), key=lambda item: item[1]["label"].lower()))


def _sort_rows(rows: list[dict[str, Any]], *, sort: str) -> list[dict[str, Any]]:
    if sort == "score_desc":
        return sorted(
            rows,
            key=lambda row: (
                row.get("score") is None,
                -float(row.get("score") or 0),
                row["latest_date"],
            ),
        )
    if sort == "score_asc":
        return sorted(
            rows,
            key=lambda row: (
                row.get("score") is None,
                float(row.get("score") or 0),
                row["latest_date"],
            ),
        )
    if sort == "scans_desc":
        return sorted(
            rows,
            key=lambda row: (-int(row.get("scan_count") or 0), row["latest_date"]),
        )
    return sorted(rows, key=lambda row: _timestamp(row["latest_date"]), reverse=True)
