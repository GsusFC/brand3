"""SV9 public ranking: deterministic, zero LLM (design doc section 13).

Hard rules:
- One entry per domain: the most recent complete scan.
- Only complete scans (no not_evaluated components) and only the current
  rubric version — scores across rubric versions are not comparable.
- Percentile per primary-category cohort, and only when the cohort reaches
  MIN_COHORT_FOR_PERCENTILE; below that it is omitted without apologising.
- Plain-text domain only; exclusion flag covers internal tests and takedowns.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
import json

from src.sv9.categories import (
    CATEGORIES,
    MIN_COHORT_FOR_PERCENTILE,
    category_label,
    suggest_category,
)
from src.sv9.rubric import LEGACY_MODEL_LABEL, MODEL_LABEL, RUBRIC_VERSION
from src.sv9.store import Sv9Store


def domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    raw = str(url).strip()
    if "//" not in raw:
        raw = f"https://{raw}"
    host = urlparse(raw).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or None


def build_ranking(
    store: Sv9Store,
    *,
    category: str | None = None,
    rubric_version: str = RUBRIC_VERSION,
) -> dict[str, Any]:
    """Build the ranking model: entries, cohort counts, and taxonomy.

    Migration window (prompt técnico step 8): scans from earlier rubric
    versions are not convertible but stay in the ranking, labelled
    model = 'v2', until they are re-scanned with the current model. The newest
    scan per domain wins, so a re-scan automatically supersedes the v2 entry.
    Percentiles are only computed within the current-rubric cohort, because
    scores across rubric versions are not comparable.
    """
    scans = store.conn.execute(
        """
        SELECT id, brand_name, url, source_run_id, brand3_score, created_at,
               rubric_version, needs_review, reliability_status, reliability_reason_codes_json
        FROM sv9_scans
        WHERE is_complete = 1
        ORDER BY created_at DESC, id DESC
        """,
    ).fetchall()

    categories_by_domain = store.get_brand_categories()
    niche_by_run = _predicted_niches(store)

    entries_by_domain: dict[str, dict[str, Any]] = {}
    for scan in scans:
        domain = domain_from_url(scan["url"]) or domain_from_url(scan["brand_name"])
        if not domain or domain in entries_by_domain:
            continue  # newest scan per domain wins (rows arrive newest-first)
        assignment = categories_by_domain.get(domain) or {}
        if assignment.get("exclude_from_ranking"):
            continue
        confirmed = assignment.get("primary_category")
        suggested = suggest_category(niche_by_run.get(scan["source_run_id"]))
        primary = confirmed or suggested
        is_current = scan["rubric_version"] == rubric_version
        try:
            reliability_reason_codes = json.loads(scan["reliability_reason_codes_json"] or "[]")
        except json.JSONDecodeError:
            reliability_reason_codes = []
        canonical_status = (
            "canonical"
            if scan["reliability_status"] == "reliable" and not scan["needs_review"]
            else ("non_canonical" if scan["reliability_status"] in {"usable", "shadow"} else "invalid")
        )
        canonical_reason_codes = list(reliability_reason_codes)
        if canonical_status != "canonical":
            if not scan["needs_review"] and scan["reliability_status"] == "reliable":
                canonical_reason_codes.append("invalid_scan_state")
            elif scan["reliability_status"] == "usable":
                canonical_reason_codes.append("usable_not_canonical")
            elif scan["reliability_status"] == "shadow":
                canonical_reason_codes.append("shadow_not_canonical")
            else:
                canonical_reason_codes.append("invalid_scan_state")
        canonical_reason_codes = list(dict.fromkeys(canonical_reason_codes))
        entries_by_domain[domain] = {
            "domain": domain,
            "scan_id": scan["id"],
            "brand_name": scan["brand_name"],
            "brand3_score": scan["brand3_score"],
            "scanned_at": scan["created_at"],
            "rubric_version": scan["rubric_version"],
            "model": MODEL_LABEL if is_current else LEGACY_MODEL_LABEL,
            "is_current_model": is_current,
            "needs_rescan": not is_current,
            "category": primary,
            "category_label": category_label(primary),
            "category_source": "confirmada" if confirmed else ("sugerida" if suggested else None),
            "secondary": assignment.get("secondary") or [],
            "reliability_status": scan["reliability_status"] or "shadow",
            "reliability_reason_codes": reliability_reason_codes,
            "canonical_status": canonical_status,
            "canonical_reason_codes": canonical_reason_codes,
            "is_canonical": canonical_status == "canonical",
        }

    entries = sorted(
        entries_by_domain.values(),
        key=lambda e: (-e["brand3_score"], e["scanned_at"]),
    )

    # Cohort counts and percentiles are restricted to the current model: a v2
    # score has no comparable cohort.
    current_entries = [e for e in entries if e["is_current_model"]]
    cohort_counts: dict[str, int] = {}
    for entry in current_entries:
        if entry["category"]:
            cohort_counts[entry["category"]] = cohort_counts.get(entry["category"], 0) + 1

    for position, entry in enumerate(entries, start=1):
        entry["position"] = position
        entry["percentile"] = (
            _cohort_percentile(entry, current_entries, cohort_counts)
            if entry["is_current_model"]
            else None
        )

    if category:
        entries = [e for e in entries if e["category"] == category]

    return {
        "entries": entries,
        "total": len(entries_by_domain),
        "legacy_count": sum(1 for e in entries_by_domain.values() if not e["is_current_model"]),
        "cohort_counts": cohort_counts,
        "taxonomy": [
            {"key": key, "label": spec["label"], "count": cohort_counts.get(key, 0)}
            for key, spec in CATEGORIES.items()
        ],
        "min_cohort": MIN_COHORT_FOR_PERCENTILE,
        "rubric_version": rubric_version,
        "active_category": category,
    }


def _cohort_percentile(
    entry: dict[str, Any],
    entries: list[dict[str, Any]],
    cohort_counts: dict[str, int],
) -> int | None:
    """Share of the primary-category cohort this entry scores above."""
    key = entry["category"]
    if not key or cohort_counts.get(key, 0) < MIN_COHORT_FOR_PERCENTILE:
        return None
    cohort = [e for e in entries if e["category"] == key]
    below = sum(1 for e in cohort if e["brand3_score"] < entry["brand3_score"])
    return round(100 * below / len(cohort))


def _predicted_niches(store: Sv9Store) -> dict[int, str | None]:
    """Legacy V5 niche prediction per run, for category suggestions.

    The runs table lives in the shared DB but may be absent in isolated test
    databases; suggestions then simply do not happen.
    """
    try:
        rows = store.conn.execute(
            "SELECT id, predicted_niche FROM runs WHERE predicted_niche IS NOT NULL"
        ).fetchall()
    except Exception:
        return {}
    return {int(row["id"]): row["predicted_niche"] for row in rows}
