"""Unified Observatory index.

One row per normalized brand. The row chooses the best available score in this
order: SV9, Magnetism, Brand Audit. Scanner history remains available as count
and links; this module does not mutate scans or scores.
"""

from __future__ import annotations

import json
import re
import sqlite3
from html.parser import HTMLParser
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

from src.config import BRAND3_DB_PATH
from src.features.magnetism.moodboard import extract_moodboard_images
from src.research.research_pack_facade import build_recommended_research_pack
from src.storage.sqlite_store import SQLiteStore
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
    rows = [brand.to_row(lang=lang) for brand in brands.values() if brand.sources]
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


def build_observatory_brand_history(
    brand: str,
    *,
    db_path: str = BRAND3_DB_PATH,
    lang: str = "es",
) -> dict[str, Any]:
    """Build unified history for one brand/domain."""
    brands = _load_brand_sources(db_path=db_path, lang=lang)
    _attach_classifications(brands, db_path=db_path)
    match = _find_brand(brands, brand)
    if match is None:
        return {
            "brand_key": brand,
            "display_name": _display_name(brand, brand),
            "domain": brand,
            "category_label": None,
            "profile": _empty_brand_profile(brand),
            "sv9_status": _empty_sv9_status(),
            "rows": [],
        }
    return {
        "brand_key": match.brand_key,
        "display_name": match.display_name,
        "domain": match.domain,
        "category_label": match.category_label,
        "profile": _build_brand_profile(match, db_path=db_path),
        "sv9_status": _build_sv9_status(match),
        "rows": match.to_history_rows(),
    }


def _empty_brand_profile(brand: str) -> dict[str, Any]:
    return {
        "name": _display_name(brand, brand),
        "domain": brand,
        "logo_url": "",
        "logo_source": "",
        "summary": "",
        "offer": "",
        "audience": "",
        "outcome": "",
        "category": "",
        "official_links": [],
        "analyzed_links": [],
        "social_links": [],
        "proof_points": [],
        "evidence_gaps": [],
        "confidence_notes": [],
        "models": [],
        "scan_count": 0,
        "latest_date": "",
        "best_score": None,
        "best_score_compact": "-",
    }


def _empty_sv9_status() -> dict[str, Any]:
    return {
        "available": False,
        "score": None,
        "score_compact": "-",
        "href": "",
        "date": "",
        "generate_scan_id": None,
        "source_run_id": None,
    }


def _build_brand_profile(brand: ObservatoryBrand, *, db_path: str) -> dict[str, Any]:
    snapshots = _snapshots_for_brand(brand, db_path=db_path)
    packs = [_research_pack_from_snapshot(snapshot) for snapshot in snapshots]
    packs = [pack for pack in packs if pack]
    web_payloads = _web_payloads_from_snapshots(snapshots)
    logo_url, logo_source = _best_logo(snapshots, web_payloads)
    primary_pack = packs[0] if packs else {}
    official_links = _unique_links(
        [
            brand.domain and f"https://{brand.domain}",
            *(primary_pack.get("official_urls") or []),
        ]
    )
    analyzed_links = _unique_links(primary_pack.get("analyzed_urls") or [])
    social_links = _unique_social_links(
        [
            *_social_links_from_packs(packs),
            *_social_links_from_web_payloads(web_payloads),
        ]
    )
    proof_points = _profile_evidence_items(primary_pack.get("proof_points"), limit=3)
    evidence_gaps = _str_list(primary_pack.get("evidence_gaps"), limit=4)
    confidence_notes = _str_list(primary_pack.get("confidence_notes"), limit=4)
    scores = [source.score for source in brand.sources if source.score is not None]
    best_score = max(scores) if scores else None
    return {
        "name": brand.display_name,
        "domain": brand.domain,
        "logo_url": logo_url,
        "logo_source": logo_source,
        "summary": _first_text(
            primary_pack.get("product_summary"),
            primary_pack.get("company_summary"),
            primary_pack.get("declared_purpose"),
        ),
        "offer": _first_text(primary_pack.get("offer")),
        "audience": _first_text(primary_pack.get("audience")),
        "outcome": _first_text(primary_pack.get("outcome")),
        "category": brand.category_label or _first_text(primary_pack.get("category")),
        "official_links": official_links[:6],
        "analyzed_links": analyzed_links[:6],
        "social_links": social_links[:8],
        "proof_points": proof_points,
        "evidence_gaps": evidence_gaps,
        "confidence_notes": confidence_notes,
        "models": sorted({source.source for source in brand.sources}),
        "scan_count": len(brand.sources),
        "latest_date": _compact_date(brand.latest_date),
        "best_score": best_score,
        "best_score_compact": _score_compact(best_score),
    }


def _build_sv9_status(brand: ObservatoryBrand) -> dict[str, Any]:
    sv9_sources = [source for source in brand.sources if source.source == "sv9"]
    if sv9_sources:
        source = sorted(sv9_sources, key=lambda item: _timestamp(item.created_at), reverse=True)[0]
        return {
            "available": True,
            "score": source.score,
            "score_compact": _score_compact(source.score),
            "href": source.href,
            "date": _compact_date(source.created_at),
            "generate_scan_id": None,
            "source_run_id": source.source_run_id,
        }
    generate_scan_id = _sv9_generate_scan_id(brand.sources)
    source_run_id = None
    for source in brand.sources:
        if source.magnetism_scan_id == generate_scan_id:
            source_run_id = source.source_run_id
            break
    return {
        "available": False,
        "score": None,
        "score_compact": "-",
        "href": "",
        "date": "",
        "generate_scan_id": generate_scan_id,
        "source_run_id": source_run_id,
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


def _snapshots_for_brand(brand: ObservatoryBrand, *, db_path: str) -> list[dict[str, Any]]:
    run_ids = []
    seen_ids = set()
    for source in sorted(brand.sources, key=lambda item: _timestamp(item.created_at), reverse=True):
        if not source.source_run_id or source.source_run_id in seen_ids:
            continue
        seen_ids.add(source.source_run_id)
        run_ids.append(source.source_run_id)
    if not run_ids:
        return []
    store = SQLiteStore(db_path)
    try:
        snapshots = []
        for run_id in run_ids[:5]:
            snapshot = store.get_run_snapshot(run_id)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots
    finally:
        store.close()


def _research_pack_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    try:
        pack = build_recommended_research_pack(snapshot).pack
    except Exception:
        return {}
    if hasattr(pack, "to_dict") and callable(pack.to_dict):
        payload = pack.to_dict()
        return payload if isinstance(payload, dict) else {}
    return pack if isinstance(pack, dict) else {}


def _web_payloads_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads = []
    for snapshot in snapshots:
        for item in reversed(snapshot.get("raw_inputs") or []):
            if item.get("source") == "web" and isinstance(item.get("payload"), dict):
                payloads.append(item["payload"])
                break
    return payloads


def _best_logo(
    snapshots: list[dict[str, Any]],
    web_payloads: list[dict[str, Any]],
) -> tuple[str, str]:
    for snapshot in snapshots:
        profile = ((snapshot.get("run") or {}).get("brand_profile") or {})
        logo_url = str(profile.get("logo_url") or "").strip()
        if logo_url:
            return logo_url, "brand_profile"
        logo_url = str((snapshot.get("run") or {}).get("brand_logo_url") or "").strip()
        if logo_url:
            return logo_url, "run"
    for payload in web_payloads:
        for image in extract_moodboard_images(payload):
            if image.get("role") == "logo" and image.get("url"):
                return str(image["url"]), "owned_html"
    return "", ""


def _social_links_from_packs(packs: list[dict[str, Any]]) -> list[str]:
    urls = []
    for pack in packs:
        urls.extend(pack.get("official_urls") or [])
        urls.extend(pack.get("analyzed_urls") or [])
        source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
        for source in source_map.values():
            if isinstance(source, dict):
                urls.append(str(source.get("url") or ""))
    return [url for url in urls if _is_social_url(url)]


def _social_links_from_web_payloads(payloads: list[dict[str, Any]]) -> list[str]:
    urls = []
    for payload in payloads:
        html = str(payload.get("html") or "")
        if html:
            parser = _SocialLinkParser()
            try:
                parser.feed(html)
            except Exception:
                pass
            urls.extend(parser.urls)
        markdown = str(payload.get("markdown_content") or "")
        urls.extend(_urls_from_text(markdown))
    return [url for url in urls if _is_social_url(url)]


class _SocialLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {name: (value or "") for name, value in attrs}
        href = attr_map.get("href", "")
        if href:
            self.urls.append(href)


def _urls_from_text(text: str) -> list[str]:
    out = []
    for raw in str(text or "").replace(")", " ").replace("]", " ").split():
        if raw.startswith(("http://", "https://")):
            out.append(raw.strip(".,;\"'"))
    return out


def _is_social_url(url: str) -> bool:
    host = urlparse(str(url or "")).netloc.lower()
    host = host.removeprefix("www.")
    social_hosts = (
        "linkedin.com",
        "x.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "github.com",
        "facebook.com",
        "threads.net",
    )
    return any(host == marker or host.endswith(f".{marker}") for marker in social_hosts)


def _unique_social_links(urls: list[str]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for url in _unique_links(urls):
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"label": _social_label(host), "url": url, "host": host})
    return out


def _social_label(host: str) -> str:
    if "linkedin.com" in host:
        return "LinkedIn"
    if host == "x.com" or "twitter.com" in host:
        return "X"
    if "instagram.com" in host:
        return "Instagram"
    if "youtube.com" in host:
        return "YouTube"
    if "tiktok.com" in host:
        return "TikTok"
    if "github.com" in host:
        return "GitHub"
    if "facebook.com" in host:
        return "Facebook"
    if "threads.net" in host:
        return "Threads"
    return host


def _unique_links(values: list[Any]) -> list[str]:
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


def _profile_evidence_items(raw: Any, *, limit: int) -> list[dict[str, str]]:
    out = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text[:220],
                "source_url": str(item.get("source_url") or "").strip(),
                "confidence": str(item.get("confidence") or "").strip(),
            }
        )
        if len(out) >= limit:
            break
    return out


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
    boundary = max(text.rfind(". ", 0, limit), text.rfind(" — ", 0, limit), text.rfind(" - ", 0, limit))
    if boundary < 160:
        boundary = limit
    return text[:boundary].rstrip(" .,-—") + "..."


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


def _find_brand(
    brands: dict[str, ObservatoryBrand],
    value: str,
) -> ObservatoryBrand | None:
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
