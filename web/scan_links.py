"""Helpers for public scanner navigation links."""

from __future__ import annotations

from typing import Iterable


def lang_query(lang: str) -> str:
    return f"?lang={lang}"


def sv9_scan_id_for_run(source_run_id: object, *, db_path: str) -> int | None:
    if not source_run_id:
        return None
    try:
        from src.sv9.store import Sv9Store

        store = Sv9Store(db_path)
        try:
            scan = store.get_scan_for_run(int(source_run_id))
        finally:
            store.close()
    except Exception:
        return None
    if scan:
        return int(scan["id"])
    return None


def primary_scan_href(scan: dict, *, db_path: str, lang: str = "es") -> str:
    sv9_scan_id = sv9_scan_id_for_run(scan.get("source_run_id"), db_path=db_path)
    if sv9_scan_id:
        return f"/sv9/scan/{sv9_scan_id}{lang_query(lang)}"
    return f"/magnetism-scanner/scan/{scan['id']}{lang_query(lang)}"


def attach_primary_scan_hrefs(scans: Iterable[dict], *, db_path: str, lang: str = "es") -> list[dict]:
    enriched = []
    for scan in scans:
        row = dict(scan)
        row["primary_href"] = primary_scan_href(row, db_path=db_path, lang=lang)
        enriched.append(row)
    return enriched
