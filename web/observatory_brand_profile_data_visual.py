"""Visual-signature and visual content helpers for brand profiles."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse
from typing import Any

from src.features.magnetism.moodboard import MAX_MOODBOARD_IMAGES, extract_moodboard_images

from web.observatory_index_support import _float_or_none, _timestamp


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


def _sv9_generate_scan_id(sources: list[Any]) -> int | None:
    for source in sources:
        if source.source == "magnetism" and source.magnetism_scan_id and source.source_run_id:
            return source.magnetism_scan_id
    return None


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
    resolved = base_url and urlparse(base_url) and urljoin(base_url, candidate) or candidate
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


def _compact_date(value: str | None) -> str:
    from web.observatory_index_support import _compact_date as _base_compact_date

    return _base_compact_date(value)


__all__ = [
    "_LOGO_NOISE_MARKERS",
    "_best_logo",
    "_build_profile_moodboard",
    "_collect_visual_signature_logo_candidates",
    "_clean_logo_candidate_url",
    "_visual_signature_history_from_snapshots",
    "_visual_signature_logo_candidates_from_snapshots",
    "_visual_signature_payload",
    "_visual_signature_scan_from_snapshots",
    "_sv9_generate_scan_id",
    "_sorted_candidates",
    "_compact_date",
]
