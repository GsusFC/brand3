"""SV9 ranking categories: open draft taxonomy, editable as data.

Design doc section 13: the taxonomy is a deliberately unfinished draft that
grows with real scans — it lives here as data so editing it never touches the
engine. One primary category per brand (defines the percentile cohort and the
ranking position) plus up to two secondary ones (filters/context).

Assignment flow: the machine suggests (mapped from the legacy V5 niche
classifier already persisted per run — zero LLM calls), a human confirms.
A new category is born only when ~10 scans would use it; evaluated by hand
until there is volume.
"""

from __future__ import annotations

TAXONOMY_VERSION = "sv9-categorias-v0.1-draft"

# Percentiles only mean something against a cohort: below this, the ranking
# shows position and category but omits the percentile without apologising.
MIN_COHORT_FOR_PERCENTILE = 20

# Draft seed (design doc section 13). status=draft until the team settles it.
CATEGORIES: dict[str, dict[str, str]] = {
    "ia": {"label": "IA", "status": "draft"},
    "web3_crypto": {"label": "Web3 / Crypto", "status": "draft"},
    "devtools_infra": {"label": "DevTools / Infra", "status": "draft"},
    "saas_b2b": {"label": "SaaS B2B", "status": "draft"},
    "fintech": {"label": "Fintech", "status": "draft"},
    "ecommerce_dtc": {"label": "E-commerce / DTC", "status": "draft"},
    "marketplace_plataforma": {"label": "Marketplace / Plataforma", "status": "draft"},
    "servicios_agencia": {"label": "Servicios / Agencia", "status": "draft"},
    "media_comunidad": {"label": "Media / Comunidad", "status": "draft"},
    "edtech": {"label": "EdTech", "status": "draft"},
    "salud_wellness": {"label": "Salud / Wellness", "status": "draft"},
    "consumo_fisico": {"label": "Consumo físico", "status": "draft"},
}

# Legacy V5 niche classifier output -> suggested category. The classifier's
# vocabulary is AI-heavy; anything unknown simply yields no suggestion.
NICHE_TO_CATEGORY: dict[str, str] = {
    "frontier_ai": "ia",
    "enterprise_ai": "ia",
    "physical_ai": "ia",
    "physical_ai_data": "ia",
    "ai_research_lab": "ia",
    "model_lab": "ia",
    "chip_ai": "ia",
    "ai_governance": "ia",
    "agent_tooling": "devtools_infra",
    "llm_framework": "devtools_infra",
    "engineering_validation": "devtools_infra",
    "productivity_addon": "saas_b2b",
    "community_platform": "media_comunidad",
    "workforce_marketplace": "marketplace_plataforma",
    "startup_studio": "servicios_agencia",
}


def category_label(key: str | None) -> str | None:
    if key and key in CATEGORIES:
        return CATEGORIES[key]["label"]
    return None


def suggest_category(predicted_niche: str | None) -> str | None:
    if not predicted_niche:
        return None
    return NICHE_TO_CATEGORY.get(str(predicted_niche).strip().lower())


assert all(NICHE_TO_CATEGORY[k] in CATEGORIES for k in NICHE_TO_CATEGORY), \
    "Every niche suggestion must map to a real category"
