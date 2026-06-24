"""Brand profile composition helpers for the observatory index."""

from __future__ import annotations

import sys
from typing import Any

from src.classification.market_taxonomy import GROUPS, tags_for_group
from src.research.research_pack_facade import (
    build_recommended_research_pack as _build_recommended_research_pack,
)
from src.storage.sqlite_store import SQLiteStore

from web.observatory_brand_profile_data_cache import (
    _brand_profile_source_fingerprint,
    _raw_input_markers_for_runs,
    _load_cached_brand_profile,
    _save_cached_brand_profile,
)
from web.observatory_brand_profile_data_social import (
    _social_label,
    _canonical_social_profile_url,
    _is_social_url,
    _SocialLinkParser,
    _social_links_from_web_payloads,
    _social_links_from_packs,
    _unique_social_links,
)
from web.observatory_brand_profile_data_visual import (
    _LOGO_NOISE_MARKERS,
    _best_logo,
    _build_profile_moodboard,
    _compact_date,
    _collect_visual_signature_logo_candidates,
    _clean_logo_candidate_url,
    _sorted_candidates,
    _sv9_generate_scan_id,
    _visual_signature_payload,
    _visual_signature_scan_from_snapshots,
    _visual_signature_history_from_snapshots,
    _visual_signature_logo_candidates_from_snapshots,
)
from web.observatory_index_support import (
    _display_name,
    _first_text,
    _score_compact,
    _str_list,
    _timestamp,
    _unique_links,
)


BRAND_PROFILE_CACHE_VERSION = "brand-profile-cache-v4"


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
        "moodboard": {"available": False, "images": [], "image_count": 0, "role_counts": {}},
        "visual_signature_scan": {"available": False},
        "visual_signature_history": [],
        "models": [],
        "scan_count": 0,
        "latest_date": "",
        "best_score": None,
        "best_score_compact": "-",
    }


def _empty_market_classification(brand: str) -> dict[str, Any]:
    return {
        "brand_key": brand,
        "available": False,
        "accepted": {group: [] for group in GROUPS},
        "proposed": {group: [] for group in GROUPS},
        "primary_category": "",
        "requires_human_review": False,
        "source": "",
        "updated_at": "",
        "groups": list(GROUPS),
        "options": {group: list(tags_for_group(group)) for group in GROUPS},
    }


def _market_classification_payload(brand: Any) -> dict[str, Any]:
    payload = dict(brand.market_classification or {})
    accepted = payload.get("accepted") if isinstance(payload.get("accepted"), dict) else {}
    proposed = payload.get("proposed") if isinstance(payload.get("proposed"), dict) else {}
    return {
        "brand_key": brand.brand_key,
        "available": bool(payload),
        "accepted": {group: list(accepted.get(group) or []) for group in GROUPS},
        "proposed": {group: list(proposed.get(group) or []) for group in GROUPS},
        "primary_category": str(payload.get("primary_category") or ""),
        "requires_human_review": bool(payload.get("requires_human_review")),
        "source": str(payload.get("source") or ""),
        "updated_at": str(payload.get("updated_at") or ""),
        "groups": list(GROUPS),
        "options": {group: list(tags_for_group(group)) for group in GROUPS},
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


def _clean_profile_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in (
        "name",
        "domain",
        "canonical_url",
        "logo_url",
        "summary",
        "offer",
        "audience",
        "outcome",
        "category",
    ):
        value = str(overrides.get(key) or "").strip()
        if value:
            cleaned[key] = value
    for key in ("official_links", "social_links"):
        value = overrides.get(key)
        if isinstance(value, str):
            items = [line.strip() for line in value.splitlines() if line.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = []
        if items:
            cleaned[key] = items
    return cleaned


def _build_brand_profile(brand: Any, *, db_path: str) -> dict[str, Any]:
    snapshots = _snapshots_for_brand(brand, db_path=db_path)
    packs = [_research_pack_from_snapshot(snapshot) for snapshot in snapshots]
    packs = [pack for pack in packs if pack]
    web_payloads = _web_payloads_from_snapshots(snapshots)
    visual_signature_logo_candidates = _visual_signature_logo_candidates_from_snapshots(snapshots)
    logo_url, logo_source = _best_logo(
        snapshots,
        web_payloads,
        visual_signature_logo_candidates=visual_signature_logo_candidates,
    )
    moodboard = _build_profile_moodboard(
        web_payloads,
        logo_url=logo_url,
        visual_signature_candidates=visual_signature_logo_candidates,
    )
    visual_signature_history = _visual_signature_history_from_snapshots(snapshots)
    visual_signature_scan = visual_signature_history[0] if visual_signature_history else {"available": False}
    primary_pack = packs[0] if packs else {}
    official_links = _unique_links(
        [
            brand.domain and f"https://{brand.domain}",
            *(primary_pack.get("official_urls") or []),
        ]
    )
    analyzed_links = _unique_links(primary_pack.get("analyzed_urls") or [])
    social_links = _unique_social_links(_social_links_from_web_payloads(web_payloads))
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
        "moodboard": moodboard,
        "visual_signature_scan": visual_signature_scan,
        "visual_signature_history": visual_signature_history,
        "models": sorted({source.source for source in brand.sources}),
        "scan_count": len(brand.sources),
        "latest_date": _compact_date(brand.latest_date),
        "best_score": best_score,
        "best_score_compact": _score_compact(best_score),
    }


def _resolve_build_recommended_research_pack():
    facade = sys.modules.get("web.observatory_index")
    patched = getattr(facade, "build_recommended_research_pack", None) if facade else None
    if callable(patched):
        return patched
    return _build_recommended_research_pack


def _apply_profile_overrides(profile: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    if not overrides:
        return profile
    out = dict(profile)
    for key in (
        "name",
        "domain",
        "logo_url",
        "summary",
        "offer",
        "audience",
        "outcome",
        "category",
    ):
        value = overrides.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()
    for key in ("official_links", "social_links"):
        value = overrides.get(key)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if cleaned:
                out[key] = cleaned
    if isinstance(out.get("social_links"), list):
        out["social_links"] = _unique_social_links(out["social_links"])
    if isinstance(out.get("official_links"), list):
        out["official_links"] = _unique_links(out["official_links"])
    if overrides:
        out["manual_override"] = True
    return out


def _cached_or_build_brand_profile(brand: Any, *, db_path: str) -> dict[str, Any]:
    fingerprint = _brand_profile_source_fingerprint(
        brand,
        schema_version=BRAND_PROFILE_CACHE_VERSION,
        db_path=db_path,
    )
    cached = _load_cached_brand_profile(
        brand.brand_key,
        source_fingerprint=fingerprint,
        schema_version=BRAND_PROFILE_CACHE_VERSION,
        db_path=db_path,
    )
    if cached is not None:
        return cached
    profile = _build_brand_profile(brand, db_path=db_path)
    profile = _apply_profile_overrides(profile, brand.profile_overrides)
    _save_cached_brand_profile(
        brand.brand_key,
        profile,
        source_fingerprint=fingerprint,
        schema_version=BRAND_PROFILE_CACHE_VERSION,
        db_path=db_path,
    )
    return profile


def _build_sv9_status(brand: Any) -> dict[str, Any]:
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


def _snapshots_for_brand(brand: Any, *, db_path: str) -> list[dict[str, Any]]:
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
        pack = _resolve_build_recommended_research_pack()(snapshot).pack
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


__all__ = [
    "BRAND_PROFILE_CACHE_VERSION",
    "_build_recommended_research_pack",
    "_build_brand_profile",
    "_brand_profile_source_fingerprint",
    "_cached_or_build_brand_profile",
    "_clean_profile_overrides",
    "_empty_brand_profile",
    "_empty_market_classification",
    "_empty_sv9_status",
    "_market_classification_payload",
    "_resolve_build_recommended_research_pack",
    "_compact_date",
    "_apply_profile_overrides",
    "_snapshots_for_brand",
    "_research_pack_from_snapshot",
    "_web_payloads_from_snapshots",
    "_visual_signature_logo_candidates_from_snapshots",
    "_visual_signature_history_from_snapshots",
    "_visual_signature_scan_from_snapshots",
    "_visual_signature_payload",
    "_sorted_candidates",
    "_build_profile_moodboard",
    "_best_logo",
    "_collect_visual_signature_logo_candidates",
    "_clean_logo_candidate_url",
    "_social_links_from_packs",
    "_social_links_from_web_payloads",
    "_is_social_url",
    "_canonical_social_profile_url",
    "_unique_social_links",
    "_social_label",
    "_profile_evidence_items",
    "_load_cached_brand_profile",
    "_save_cached_brand_profile",
    "_raw_input_markers_for_runs",
    "_build_sv9_status",
    "_sv9_generate_scan_id",
    "_LOGO_NOISE_MARKERS",
    "_SocialLinkParser",
]
