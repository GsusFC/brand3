"""Unified Observatory index.

One row per normalized brand. The row chooses the best available score in this
order: SV9, Magnetism, Brand Audit. Scanner history remains available as count
and links; this module does not mutate scans or scores.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from src.config import BRAND3_DB_PATH
from src.sv9.ranking import domain_from_url


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

    def to_row(self) -> dict[str, Any]:
        primary = self.primary
        needs_sv9 = primary.source != "sv9"
        return {
            "brand_key": self.brand_key,
            "display_name": self.display_name,
            "domain": self.domain,
            "latest_date": self.latest_date,
            "compact_date": _compact_date(self.latest_date),
            "score": primary.score,
            "score_compact": _score_compact(primary.score),
            "score_model": primary.source,
            "quadrant": primary.quadrant or "",
            "category": self.category,
            "category_label": self.category_label,
            "classification_tags": list(self.classification_tags),
            "scan_count": len(self.sources),
            "primary_href": primary.href,
            "needs_sv9": needs_sv9,
            "sv9_generate_scan_id": _sv9_generate_scan_id(self.sources) if needs_sv9 else None,
            "legacy_source_run_id": primary.source_run_id if needs_sv9 else None,
        }


def build_observatory_index(
    *,
    db_path: str = BRAND3_DB_PATH,
    query: str | None = None,
    sort: str = "newest",
    category: str | None = None,
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
    rows = [brand.to_row() for brand in brands.values() if brand.sources]
    rows = _filter_rows(rows, query=query)
    categories = _category_options(rows)
    rows = _filter_rows(rows, category=category)
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
        "categories": categories,
    }


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
            "SELECT brand_key, classification_json FROM brand_market_classifications"
        ).fetchall()
    for row in rows:
        brand = brands.get(str(row["brand_key"] or "").lower())
        if brand is None:
            continue
        payload = _json_dict(row["classification_json"])
        accepted = payload.get("accepted") if isinstance(payload.get("accepted"), dict) else {}
        tags = []
        for group_tags in accepted.values():
            if isinstance(group_tags, list):
                tags.extend(str(tag) for tag in group_tags)
        brand.classification_tags = tags
        brand.category_label = str(payload.get("primary_category") or "") or (
            tags[0] if tags else None
        )
        brand.category = _slug(brand.category_label) if brand.category_label else None


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
    return out


def _category_options(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    options = {}
    for row in rows:
        key = row.get("category")
        label = row.get("category_label")
        if key and label:
            options[str(key)] = {"label": str(label)}
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


def _display_name(name: str, url: str) -> str:
    raw = (name or "").strip()
    if raw and not _looks_like_domain(raw):
        return _titleize(raw)
    domain = domain_from_url(url or raw)
    if domain:
        return _titleize(domain.split(".", 1)[0])
    return _titleize(raw or "unknown")


def _looks_like_domain(value: str) -> bool:
    return "." in value or "/" in value or "://" in value


def _titleize(value: str) -> str:
    text = value.replace("-", " ").replace("_", " ").strip()
    return " ".join(
        part.upper() if len(part) <= 3 and part.isalpha() else part.capitalize()
        for part in text.split()
    )


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


def _sv9_generate_scan_id(sources: list[ObservatorySource]) -> int | None:
    for source in sources:
        if source.source == "magnetism" and source.magnetism_scan_id and source.source_run_id:
            return source.magnetism_scan_id
    return None


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
