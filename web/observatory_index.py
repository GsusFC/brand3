"""Unified Observatory index.

One row per normalized brand. The row chooses the best available score in this
order: SV9, Magnetism, Brand Audit. Scanner history remains available as count
and links; this module does not mutate scans or scores.
"""

from __future__ import annotations

from typing import Any

from src.config import BRAND3_DB_PATH
from web.observatory_brand_profile import _build_recommended_research_pack
from web.observatory_index_data import (
    brand_row_to_profile_data,
    blank_brand_history_payload,
    build_brand_history_payload,
    load_observatory_brands,
    persist_brand_profile,
    persist_market_classification,
)
from web.observatory_index_filtering import (
    ALLOWED_SORTS,
    category_options,
    filter_observatory_rows,
    sort_observatory_rows,
    tag_options,
)
from web.observatory_index_support import _find_brand, _slug

build_recommended_research_pack = _build_recommended_research_pack


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

    brands = load_observatory_brands(db_path=db_path, lang=lang)
    brand_row_to_profile_data(brands, db_path=db_path)
    rows = [brand.to_row(lang=lang) for brand in brands.values() if brand.sources]

    rows = filter_observatory_rows(rows, query=query)
    categories = category_options(rows)
    tags = tag_options(rows)
    tag_slug = _slug(tag or "")
    rows = filter_observatory_rows(rows, category=category, tag=tag_slug)
    rows = sort_observatory_rows(rows, sort=sort)

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
        "tag": tag_slug,
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
    brands = load_observatory_brands(db_path=db_path, lang=lang)
    brand_row_to_profile_data(brands, db_path=db_path)
    match = _find_brand(brands, brand)
    if match is None:
        return blank_brand_history_payload(brand)
    return build_brand_history_payload(match, db_path=db_path)


def save_brand_profile_overrides(
    brand: str,
    overrides: dict[str, Any],
    *,
    db_path: str = BRAND3_DB_PATH,
    updated_by: str = "",
) -> str:
    """Persist human overrides for a brand profile and return its brand key."""
    return persist_brand_profile(
        brand,
        overrides,
        db_path=db_path,
        updated_by=updated_by,
    )


def save_brand_market_classification(
    brand: str,
    form_values: dict[str, Any],
    *,
    db_path: str = BRAND3_DB_PATH,
    updated_by: str = "",
) -> str:
    """Persist manually accepted market classification tags for a brand."""
    return persist_market_classification(
        brand,
        form_values,
        db_path=db_path,
        updated_by=updated_by,
    )
