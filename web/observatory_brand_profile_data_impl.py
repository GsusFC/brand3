"""Brand profile composition helpers for the observatory index."""

from __future__ import annotations

import json
from datetime import datetime
from html.parser import HTMLParser
import sys
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from src.classification.market_taxonomy import GROUPS, tags_for_group
from src.features.magnetism.moodboard import MAX_MOODBOARD_IMAGES, extract_moodboard_images
from src.research.research_pack_facade import (
    build_recommended_research_pack as _build_recommended_research_pack,
)
from src.storage.sqlite_store import SQLiteStore

from web.observatory_index_support import (
    _connect,
    _first_text,
    _display_name,
    _float_or_none,
    _json_dict,
    _score_compact,
    _slug,
    _str_list,
    _table_exists,
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
    # Only owned-page anchors are reliable enough for public profile social links.
    # Research packs/search results frequently include unresolved or name-collision
    # social candidates; those belong in evidence review, not in the public profile.
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
    fingerprint = _brand_profile_source_fingerprint(brand, db_path=db_path)
    cached = _load_cached_brand_profile(
        brand.brand_key,
        source_fingerprint=fingerprint,
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
        db_path=db_path,
    )
    return profile


def _brand_profile_source_fingerprint(brand: Any, *, db_path: str) -> str:
    run_ids = sorted({int(source.source_run_id) for source in brand.sources if source.source_run_id is not None})
    raw_input_markers = _raw_input_markers_for_runs(run_ids, db_path=db_path)
    payload = {
        "version": BRAND_PROFILE_CACHE_VERSION,
        "brand_key": brand.brand_key,
        "display_name": brand.display_name,
        "domain": brand.domain,
        "category": brand.category,
        "category_label": brand.category_label,
        "classification_tags": sorted(brand.classification_tags),
        "profile_overrides": brand.profile_overrides,
        "sources": [
            {
                "source": source.source,
                "score": source.score,
                "created_at": source.created_at,
                "href": source.href,
                "brand_name": source.brand_name,
                "url": source.url,
                "quadrant": source.quadrant,
                "source_run_id": source.source_run_id,
                "sv9_scan_id": source.sv9_scan_id,
                "magnetism_scan_id": source.magnetism_scan_id,
                "audit_token": source.audit_token,
            }
            for source in sorted(
                brand.sources,
                key=lambda item: (
                    item.source,
                    item.source_run_id or 0,
                    item.sv9_scan_id or 0,
                    item.magnetism_scan_id or 0,
                    item.audit_token or "",
                    item.created_at,
                ),
            )
        ],
        "raw_inputs": raw_input_markers,
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _raw_input_markers_for_runs(run_ids: list[int], *, db_path: str) -> list[dict[str, Any]]:
    if not run_ids:
        return []
    with _connect(db_path) as conn:
        if not _table_exists(conn, "raw_inputs"):
            return []
        placeholders = ",".join("?" for _ in run_ids)
        rows = conn.execute(
            f"""
            SELECT run_id, COUNT(*) AS input_count, MAX(id) AS max_id,
                   MAX(created_at) AS latest_input_at
            FROM raw_inputs
            WHERE run_id IN ({placeholders})
            GROUP BY run_id
            ORDER BY run_id ASC
            """,
            run_ids,
        ).fetchall()
    return [
        {
            "run_id": int(row["run_id"]),
            "input_count": int(row["input_count"] or 0),
            "max_id": int(row["max_id"] or 0),
            "latest_input_at": row["latest_input_at"] or "",
        }
        for row in rows
    ]


def _load_cached_brand_profile(
    brand_key: str,
    *,
    source_fingerprint: str,
    db_path: str,
) -> dict[str, Any] | None:
    store = SQLiteStore(db_path)
    try:
        row = store.conn.execute(
            """
            SELECT profile_json
            FROM brand_profile_cache
            WHERE brand_key = ?
              AND schema_version = ?
              AND source_fingerprint = ?
            """,
            (brand_key, BRAND_PROFILE_CACHE_VERSION, source_fingerprint),
        ).fetchone()
    finally:
        store.close()
    if not row:
        return None
    profile = _json_dict(row["profile_json"])
    return profile or None


def _save_cached_brand_profile(
    brand_key: str,
    profile: dict[str, Any],
    *,
    source_fingerprint: str,
    db_path: str,
) -> None:
    now = datetime.now().isoformat()
    store = SQLiteStore(db_path)
    try:
        store.conn.execute(
            """
            INSERT INTO brand_profile_cache (
                brand_key, schema_version, source_fingerprint,
                profile_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(brand_key) DO UPDATE SET
                schema_version=excluded.schema_version,
                source_fingerprint=excluded.source_fingerprint,
                profile_json=excluded.profile_json,
                updated_at=excluded.updated_at
            """,
            (
                brand_key,
                BRAND_PROFILE_CACHE_VERSION,
                source_fingerprint,
                json.dumps(profile, ensure_ascii=True, sort_keys=True),
                now,
                now,
            ),
        )
        store.conn.commit()
    finally:
        store.close()


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


def _best_logo(
    snapshots: list[dict[str, Any]],
    web_payloads: list[dict[str, Any]],
    *,
    visual_signature_logo_candidates: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    for snapshot in snapshots:
        profile = ((snapshot.get("run") or {}).get("brand_profile") or {})
        logo_url = str(profile.get("logo_url") or "").strip()
        if logo_url:
            return logo_url, "brand_profile"
        logo_url = str((snapshot.get("run") or {}).get("brand_logo_url") or "").strip()
        if logo_url:
            return logo_url, "run"
    for candidate in _sorted_candidates(visual_signature_logo_candidates or []):
        logo_url = str(candidate.get("url") or "").strip()
        if logo_url:
            return logo_url, "visual_signature"
    for payload in web_payloads:
        for image in extract_moodboard_images(payload):
            if image.get("role") == "logo" and image.get("url"):
                return str(image["url"]), "owned_html"
    return "", ""


def _build_profile_moodboard(
    web_payloads: list[dict[str, Any]],
    *,
    logo_url: str = "",
    visual_signature_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    images: list[dict[str, Any]] = []
    seen = set()
    if logo_url:
        parsed = urlparse(logo_url)
        images.append({"url": logo_url, "role": "logo", "alt": "", "host": parsed.netloc})
        seen.add(logo_url)
    for candidate in visual_signature_candidates or []:
        if candidate.get("role") != "logo":
            continue
        url = str(candidate.get("url") or "").strip()
        if not url or url in seen:
            continue
        parsed = urlparse(url)
        images.append({"url": url, "role": "logo", "alt": str(candidate.get("alt") or "")[:160], "host": parsed.netloc})
        seen.add(url)
    for payload in web_payloads:
        for image in extract_moodboard_images(payload):
            url = str(image.get("url") or "")
            if not url or url in seen:
                continue
            seen.add(url)
            images.append(image)
            if len(images) >= MAX_MOODBOARD_IMAGES:
                break
        if len(images) >= MAX_MOODBOARD_IMAGES:
            break
    role_counts: dict[str, int] = {}
    for image in images:
        role = str(image.get("role") or "content")
        role_counts[role] = role_counts.get(role, 0) + 1
    return {
        "available": bool(images),
        "images": images,
        "image_count": len(images),
        "role_counts": role_counts,
    }


_LOGO_NOISE_MARKERS = (
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "facebook.com/tr",
    "/pixel",
    "1x1",
    "spacer",
    "transparent.gif",
)


def _visual_signature_payload(item_payload: Any) -> dict[str, Any] | None:
    if not isinstance(item_payload, dict):
        return None
    if isinstance(item_payload.get("raw_visual_signature_payload"), dict):
        return item_payload.get("raw_visual_signature_payload")
    if "assets" in item_payload or "logo" in item_payload or "website_url" in item_payload:
        return item_payload
    return None


def _clean_logo_candidate_url(raw_url: str, *, base_url: str = "") -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("data:"):
        return ""
    resolved = urljoin(base_url, candidate) if base_url else candidate
    parsed = urlparse(resolved)
    if parsed.scheme not in ("http", "https"):
        return ""
    resolved = resolved.split("#", 1)[0]
    lowered = resolved.lower()
    if any(marker in lowered for marker in _LOGO_NOISE_MARKERS):
        return ""
    return resolved


def _collect_visual_signature_logo_candidates(payload: dict[str, Any], *, base_url: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
    for role, source_key in ("logo", "logo_image_candidates"), ("icon", "icon_candidates"):
        for item in assets.get(source_key) or []:
            if not isinstance(item, dict):
                continue
            url = _clean_logo_candidate_url(str(item.get("url") or ""), base_url=base_url)
            if not url:
                continue
            candidates.append(
                {
                    "url": url,
                    "role": role,
                    "alt": str(item.get("alt") or "")[:160],
                    "confidence": _float_or_none(item.get("confidence")) if not isinstance(item.get("confidence"), (int, float)) else float(item.get("confidence")),
                    "source": str(item.get("source") or "visual_signature"),
                }
            )

    logo = payload.get("logo") if isinstance(payload.get("logo"), dict) else {}
    for item in logo.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        url = _clean_logo_candidate_url(str(item.get("url") or ""), base_url=base_url)
        if not url:
            continue
        candidates.append(
            {
                "url": url,
                "role": "logo",
                "alt": str(item.get("alt") or "")[:160],
                "confidence": _float_or_none(item.get("confidence")) if not isinstance(item.get("confidence"), (int, float)) else float(item.get("confidence")),
                "source": str(item.get("source") or "visual_signature"),
            }
        )
    return candidates


def _sorted_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[tuple[int, float, int], dict[str, Any]]] = []
    for index, item in enumerate(items):
        role = str(item.get("role") or "")
        role_rank = 0 if role == "logo" else 1 if role == "icon" else 2
        confidence = _float_or_none(item.get("confidence"))
        if confidence is None:
            confidence = 0.1 if role == "icon" else 0.2
        candidates.append(((role_rank, -float(confidence), index), item))
    candidates.sort(key=lambda entry: entry[0])
    return [item for _key, item in candidates]


def _visual_signature_logo_candidates_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for snapshot in snapshots:
        for item in reversed(snapshot.get("raw_inputs") or []):
            if item.get("source") != "visual_signature":
                continue
            payload = _visual_signature_payload(item.get("payload"))
            if not isinstance(payload, dict):
                continue
            base_url = str(
                payload.get("analyzed_url")
                or payload.get("website_url")
                or (snapshot.get("run") or {}).get("url")
                or ""
            )
            for candidate in _collect_visual_signature_logo_candidates(payload, base_url=base_url):
                if candidate["url"] in seen:
                    continue
                seen.add(candidate["url"])
                candidates.append(candidate)
    return _sorted_candidates(candidates)


def _visual_signature_scan_from_snapshots(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    history = _visual_signature_history_from_snapshots(snapshots)
    return history[0] if history else {"available": False}


def _visual_signature_history_from_snapshots(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for snapshot in snapshots:
        run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}
        run_id = int(run.get("id") or 0) if run.get("id") is not None else None
        for item in reversed(snapshot.get("raw_inputs") or []):
            if item.get("source") != "visual_signature" or not isinstance(item.get("payload"), dict):
                continue
            payload = item["payload"]
            scan = payload.get("visual_signature_scan")
            if not isinstance(scan, dict) or scan.get("schema_version") != "visual-signature-scan-v1":
                continue
            created_at = item.get("created_at") or run.get("completed_at") or ""
            history.append(
                {
                    "available": True,
                    "run_id": run_id,
                    "created_at": created_at,
                    "date": _compact_date(created_at),
                    **scan,
                }
            )
    history.sort(key=lambda item: _timestamp(str(item.get("created_at") or "")), reverse=True)
    return history


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
    return [
        canonical
        for canonical in (_canonical_social_profile_url(url) for url in urls)
        if canonical
    ]


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


def _canonical_social_profile_url(url: str) -> str | None:
    raw = str(url or "").strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if not host or not _is_social_url(raw):
        return None
    segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
    lower = [segment.lower() for segment in segments]

    if "linkedin.com" in host:
        if len(lower) >= 2 and lower[0] in {"company", "school", "showcase"}:
            return raw
        return None

    if host == "x.com" or host.endswith(".x.com") or "twitter.com" in host:
        if lower[:2] == ["intent", "user"] or lower[:2] == ["intent", "follow"]:
            screen_name = (parse_qs(parsed.query).get("screen_name") or [""])[0].strip()
            if screen_name:
                return f"https://x.com/{screen_name.lstrip('@')}"
        if len(lower) == 1 and lower[0] not in {"home", "intent", "i", "share", "search"}:
            return raw
        return None

    if "instagram.com" in host or "threads.net" in host:
        if len(lower) == 1 and lower[0] not in {
            "about",
            "explore",
            "p",
            "reel",
            "stories",
            "tv",
        }:
            return raw
        return None

    if "youtube.com" in host:
        if len(segments) == 1 and segments[0].startswith("@"):
            return raw
        if len(lower) >= 2 and lower[0] in {"channel", "c", "user"}:
            return raw
        return None

    if "tiktok.com" in host:
        if len(segments) == 1 and segments[0].startswith("@"):
            return raw
        return None

    if "github.com" in host:
        if len(lower) == 1 and lower[0] not in {
            "about",
            "collections",
            "events",
            "features",
            "login",
            "marketplace",
            "topics",
        }:
            return raw
        return None

    if "facebook.com" in host:
        if len(lower) == 1 and lower[0] not in {
            "events",
            "groups",
            "login",
            "marketplace",
            "pages",
            "plugins",
            "share",
            "sharer",
            "watch",
        }:
            return raw
        return None

    return None


def _unique_social_links(urls: list[str]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for url in _unique_links(urls):
        canonical = _canonical_social_profile_url(url)
        if not canonical:
            continue
        url = canonical
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


def _compact_date(value: str | None) -> str:
    from web.observatory_index_support import _compact_date as _base_compact_date

    return _base_compact_date(value)


def _sv9_generate_scan_id(sources: list[Any]) -> int | None:
    for source in sources:
        if source.source == "magnetism" and source.magnetism_scan_id and source.source_run_id:
            return source.magnetism_scan_id
    return None


__all__ = [
    "BRAND_PROFILE_CACHE_VERSION",
    "_build_recommended_research_pack",
    "_build_brand_profile",
    "_brand_profile_source_fingerprint",
    "_cached_or_build_brand_profile",
    "_clean_profile_overrides",
    "_compact_date",
    "_empty_brand_profile",
    "_empty_market_classification",
    "_empty_sv9_status",
    "_market_classification_payload",
    "_resolve_build_recommended_research_pack",
    "_apply_profile_overrides",
    "_snapshots_for_brand",
    "_research_pack_from_snapshot",
    "_web_payloads_from_snapshots",
    "_visual_signature_logo_candidates_from_snapshots",
    "_visual_signature_scan_from_snapshots",
    "_visual_signature_history_from_snapshots",
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
