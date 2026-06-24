"""Domain models used by observatory index data loading and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote
from typing import Any

from web.observatory_index_support import (
    _compact_date,
    _score_compact,
    _slug,
    _timestamp_sort,
)

SOURCE_PRIORITY = {"sv9": 0, "magnetism": 1, "audit": 2}


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
            key=lambda item: _timestamp_sort(item.created_at),
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


def _sv9_generate_scan_id(sources: list[Any]) -> int | None:
    for source in sources:
        if source.source == "magnetism" and source.magnetism_scan_id and source.source_run_id:
            return source.magnetism_scan_id
    return None


__all__ = [
    "SOURCE_PRIORITY",
    "ObservatorySource",
    "ObservatoryBrand",
]
