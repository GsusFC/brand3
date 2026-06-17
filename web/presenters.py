"""Small view helpers shared across web routes (bands, bars, formatting)."""

from __future__ import annotations

from datetime import datetime

from src.reports.derivation import ascii_bar, band_from_score


def enrich_row(row: dict) -> dict:
    """Add `band`, `band_letter`, `bar`, `score_display` fields for templates."""
    composite = row.get("composite")
    letter, label = band_from_score(composite)
    row["band_letter"] = letter
    row["band"] = f"{letter} · {label}"
    row["bar"] = ascii_bar(composite, width=20)
    row["score_display"] = "n/a" if composite is None else f"{composite:.1f}"
    row["score_compact"] = "n/a" if composite is None else f"{composite:.0f}"
    row["date"] = _short_date(row.get("completed_at"))
    row["compact_date"] = _compact_date(row.get("completed_at"))
    return row


def enrich(rows: list[dict]) -> list[dict]:
    return [enrich_row(dict(r)) for r in rows]


def _short_date(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        dt = datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return value
    return dt.strftime("%Y-%m-%d")


def _compact_date(value: str | None) -> str:
    if not value:
        return "n/a"
    try:
        dt = datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return value
    return dt.strftime("%y/%m/%d")
