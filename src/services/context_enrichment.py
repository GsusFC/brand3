"""Read-only context enrichment summaries derived from public presence inventory."""

from __future__ import annotations


def _context_enrichment_summary(
    *,
    public_presence_inventory: dict[str, object] | None,
    context_summary: dict[str, object] | None,
) -> dict[str, object]:
    """Derive a read-only context note from the public presence inventory.

    This does not alter raw ContextCollector output or trust status. It only
    explains when existing observed official pages reduce the apparent
    contradiction of a failed homepage pre-scan.
    """
    inventory = public_presence_inventory or {}
    context = context_summary or {}
    raw_context_limited = (
        context.get("status") == "insufficient_data"
        or float(context.get("coverage") or 0.0) == 0.0
    )
    recommended = bool(inventory.get("recommended_evidence_base"))
    if not recommended or not raw_context_limited:
        return {
            "source": "public_presence_inventory",
            "applied": False,
            "reason": "not_applicable",
        }

    limitations = ["raw_context_readiness_unchanged"]
    if context.get("status") == "insufficient_data" or float(context.get("coverage") or 0.0) == 0.0:
        limitations.insert(0, "homepage_pre_scan_unavailable")

    return {
        "source": "public_presence_inventory",
        "applied": True,
        "status": "raw_context_limited_but_public_inventory_available",
        "reason": "official_public_pages_available",
        "official_pages_found": int(inventory.get("official_pages_found") or 0),
        "usable_brand_evidence_pages": int(inventory.get("usable_brand_evidence_pages") or 0),
        "usable_public_perception_pages": int(inventory.get("usable_public_perception_pages") or 0),
        "docs_candidates": int(inventory.get("docs_candidates") or 0),
        "support_candidates": int(inventory.get("support_candidates") or 0),
        "news_or_blog_candidates": int(inventory.get("news_or_blog_candidates") or 0),
        "trust_or_safety_candidates": int(inventory.get("trust_or_safety_candidates") or 0),
        "recommended_evidence_base": recommended,
        "message": "homepage pre-scan limited, but public official pages were detected through existing collectors",
        "limitations": limitations,
    }


def _context_effective_readiness(
    *,
    public_presence_inventory: dict[str, object] | None,
    context_summary: dict[str, object] | None,
) -> dict[str, object]:
    inventory = public_presence_inventory or {}
    context = context_summary or {}
    raw_context_limited = (
        context.get("status") == "insufficient_data"
        or float(context.get("coverage") or 0.0) == 0.0
    )
    if (
        not raw_context_limited
        or not bool(inventory.get("recommended_evidence_base"))
        or int(inventory.get("usable_brand_evidence_pages") or 0) <= 0
    ):
        return {
            "source": "public_presence_inventory",
            "applied": False,
            "reason": "not_applicable",
        }

    return {
        "source": "public_presence_inventory",
        "applied": True,
        "status": "degraded",
        "coverage": 0.45,
        "confidence": 0.45,
        "confidence_reason": ["homepage_unavailable_but_public_inventory_available"],
        "reason": "homepage_unavailable_but_public_inventory_available",
        "official_pages_found": int(inventory.get("official_pages_found") or 0),
        "usable_brand_evidence_pages": int(inventory.get("usable_brand_evidence_pages") or 0),
        "usable_public_perception_pages": int(inventory.get("usable_public_perception_pages") or 0),
        "recommended_evidence_base": True,
        "limitations": [
            "homepage_pre_scan_unavailable",
            "raw_context_readiness_unchanged",
        ],
    }
