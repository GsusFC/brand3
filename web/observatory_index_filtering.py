"""Filtering and sorting helpers for Observatory index rows."""

from __future__ import annotations

from typing import Any

from web.observatory_index_support import _slug, _timestamp

ALLOWED_SORTS = {"newest", "score_desc", "score_asc", "scans_desc"}


def filter_observatory_rows(
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


def category_options(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    options = {}
    for row in rows:
        key = row.get("category")
        label = row.get("category_label")
        if key and label:
            options[str(key)] = {"label": str(label)}
    return dict(sorted(options.items(), key=lambda item: item[1]["label"].lower()))


def tag_options(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
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


def sort_observatory_rows(rows: list[dict[str, Any]], *, sort: str) -> list[dict[str, Any]]:
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
    return sorted(rows, key=lambda row: _timestamp(row.get("latest_date")), reverse=True)
