"""Visual Signature evidence contract for downstream scoring consumers.

This contract is evidence-only. It exposes traceable visual observations and
tile-level signals, but it does not compute or modify SV9 scores.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.visual_signature._internal.utils import dict_or_empty as _dict
from src.visual_signature._internal.utils import float_or_none as _float_or_none
from src.visual_signature._internal.utils import unique as _unique
from src.visual_signature.versions import VISUAL_SIGNATURE_EVIDENCE_VERSION

VISUAL_TILE_IDS = (
    "coherencia.C6",
    "brand_idea.I1",
    "brand_idea.I2",
    "brand_idea.I3",
    "brand_idea.I6",
    "brand_idea.I7",
    "brand_idea.I8",
    "brand_idea.I9",
    "core_purpose.PR8",
    "magnetism.MG1",
    "magnetism.MG5",
    "magnetism.MG7",
)


def build_visual_signature_evidence_v1(
    visual_signature_payload: dict[str, Any] | None,
    *,
    screenshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable Visual Signature evidence packet consumed by SV9 shadow mode."""

    payload = visual_signature_payload if isinstance(visual_signature_payload, dict) else {}
    screenshot = _screenshot_payload(payload, screenshot_payload)
    obstruction = _capture_obstruction(payload)
    capture = _capture_contract(payload, screenshot=screenshot, obstruction=obstruction)
    identity = _identity_contract(payload)
    visual_system = _visual_system_contract(payload)
    first_impression = _first_impression_contract(payload, capture)
    copy_visual_alignment = _copy_visual_alignment_contract(payload, capture)
    limitations = _limitations(payload, capture)
    fingerprint = _fingerprint_contract(payload, capture, screenshot)
    tile_signals = _tile_signals(
        payload,
        capture=capture,
        identity=identity,
        visual_system=visual_system,
        first_impression=first_impression,
        copy_visual_alignment=copy_visual_alignment,
    )
    return {
        "schema_version": VISUAL_SIGNATURE_EVIDENCE_VERSION,
        "fingerprint": fingerprint,
        "capture": capture,
        "identity": identity,
        "visual_system": visual_system,
        "first_impression": first_impression,
        "copy_visual_alignment": copy_visual_alignment,
        "tile_signals": tile_signals,
        "limitations": limitations,
    }


def _screenshot_payload(payload: dict[str, Any], screenshot_payload: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(screenshot_payload, dict):
        return dict(screenshot_payload)
    vision = _dict(payload.get("vision"))
    screenshot = _dict(vision.get("screenshot"))
    if screenshot:
        return screenshot
    capture = _dict(payload.get("capture"))
    return capture


def _capture_contract(
    payload: dict[str, Any],
    *,
    screenshot: dict[str, Any],
    obstruction: dict[str, Any],
) -> dict[str, Any]:
    available = bool(
        screenshot.get("available")
        or screenshot.get("path")
        or screenshot.get("screenshot_url")
        or _dict(payload.get("assets")).get("screenshot_available")
    )
    quality = str(screenshot.get("quality") or ("usable" if available else "missing"))
    variant = _capture_variant(screenshot)
    first_fold_evaluable = _first_fold_evaluable(obstruction, available=available, quality=quality)
    status = _capture_status(
        available=available,
        quality=quality,
        obstruction=obstruction,
        first_fold_evaluable=first_fold_evaluable,
    )
    return {
        "status": status,
        "available": available,
        "quality": quality,
        "capture_variant": variant,
        "first_fold_evaluable": first_fold_evaluable,
        "viewport": _viewport(screenshot),
        "url_requested": str(payload.get("website_url") or ""),
        "url_final": str(screenshot.get("page_url") or payload.get("analyzed_url") or payload.get("website_url") or ""),
        "captured_at": str(screenshot.get("captured_at") or _dict(payload.get("acquisition")).get("acquired_at") or ""),
        "path": str(screenshot.get("path") or screenshot.get("screenshot_url") or ""),
        "obstruction": obstruction,
    }


def _capture_variant(screenshot: dict[str, Any]) -> str:
    selected = str(screenshot.get("selected_capture_variant") or screenshot.get("capture_variant") or screenshot.get("capture_type") or "")
    if selected in {"viewport", "full_page", "clean_attempt", "blocked"}:
        return selected
    if str(screenshot.get("quality") or "") == "blocked":
        return "blocked"
    return "unknown"


def _viewport(screenshot: dict[str, Any]) -> dict[str, int | None]:
    viewport = _dict(screenshot.get("viewport"))
    return {
        "width": _int_or_none(screenshot.get("width") or viewport.get("width")),
        "height": _int_or_none(screenshot.get("height") or viewport.get("height")),
    }


def _capture_obstruction(payload: dict[str, Any]) -> dict[str, Any]:
    vision = _dict(payload.get("vision"))
    acquisition = _dict(payload.get("acquisition"))
    raw = _dict(vision.get("viewport_obstruction")) or _dict(acquisition.get("viewport_obstruction"))
    if not raw:
        return {"present": False, "type": "none", "severity": "none", "first_impression_valid": True}
    return {
        "present": bool(raw.get("present")),
        "type": str(raw.get("type") or "unknown"),
        "severity": str(raw.get("severity") or "unknown"),
        "coverage_ratio": _float_or_none(raw.get("coverage_ratio"), digits=3),
        "first_impression_valid": bool(raw.get("first_impression_valid", True)),
        "confidence": _float_or_none(raw.get("confidence"), digits=3),
        "signals": [str(item) for item in raw.get("signals") or []][:12],
    }


def _first_fold_evaluable(obstruction: dict[str, Any], *, available: bool, quality: str) -> bool:
    if not available or quality in {"missing", "blocked", "poor"}:
        return False
    if obstruction.get("present") and obstruction.get("first_impression_valid") is False:
        return False
    if obstruction.get("severity") == "blocking":
        return False
    return True


def _capture_status(
    *,
    available: bool,
    quality: str,
    obstruction: dict[str, Any],
    first_fold_evaluable: bool,
) -> str:
    if not available:
        return "missing"
    if obstruction.get("present") and (obstruction.get("severity") == "blocking" or not first_fold_evaluable):
        return "blocked"
    if quality in {"missing", "blocked"}:
        return "blocked"
    if quality in {"poor", "partial"} or not first_fold_evaluable:
        return "limited"
    return "usable"


def _identity_contract(payload: dict[str, Any]) -> dict[str, Any]:
    logo = _dict(payload.get("logo"))
    candidates = logo.get("candidates") if isinstance(logo.get("candidates"), list) else []
    ordered = [_logo_candidate(item) for item in candidates if isinstance(item, dict)]
    ordered = sorted(ordered, key=lambda item: item["confidence"], reverse=True)
    return {
        "logo_detected": bool(logo.get("logo_detected")),
        "favicon_detected": bool(logo.get("favicon_detected")),
        "textual_brand_mark_detected": bool(logo.get("textual_brand_mark_detected")),
        "primary_location": str(logo.get("primary_location") or "unknown"),
        "candidates": ordered[:8],
        "confidence": _score01(logo.get("confidence")),
    }


def _logo_candidate(item: dict[str, Any]) -> dict[str, Any]:
    location = str(item.get("location") or "unknown")
    source = str(item.get("source") or "unknown")
    url = item.get("url")
    role = "real_logo" if location in {"header", "nav"} and url else "favicon" if location == "metadata" else "text_or_unknown"
    return {
        "url": str(url) if url else None,
        "text": str(item.get("text")) if item.get("text") else None,
        "alt": str(item.get("alt")) if item.get("alt") else None,
        "location": location,
        "source": source,
        "role": role,
        "confidence": _score01(item.get("confidence")),
        "reason": _logo_reason(location, source, role),
    }


def _logo_reason(location: str, source: str, role: str) -> str:
    if role == "real_logo":
        return f"logo candidate appears in {location}"
    if role == "favicon":
        return "candidate comes from metadata favicon"
    return f"candidate comes from {source}"


def _visual_system_contract(payload: dict[str, Any]) -> dict[str, Any]:
    colors = _dict(payload.get("colors"))
    typography = _dict(payload.get("typography"))
    layout = _dict(payload.get("layout"))
    components = _dict(payload.get("components"))
    consistency = _dict(payload.get("consistency"))
    return {
        "palette": {
            "dominant_colors": _string_list(colors.get("dominant_colors"))[:8],
            "accent_candidates": _string_list(colors.get("accent_candidates"))[:6],
            "palette_complexity": str(colors.get("palette_complexity") or "unknown"),
        },
        "typography": {
            "heading_scale": str(typography.get("heading_scale") or "unknown"),
            "heading_font": _optional_str(typography.get("heading_font")),
            "body_font": _optional_str(typography.get("body_font")),
        },
        "layout": {
            "has_navigation": bool(layout.get("has_navigation")),
            "has_hero": bool(layout.get("has_hero")),
            "visual_density": str(layout.get("visual_density") or "unknown"),
            "layout_patterns": _string_list(layout.get("layout_patterns"))[:8],
        },
        "components": {
            "primary_ctas": _string_list(components.get("primary_ctas"))[:8],
            "component_types": _component_types(components),
        },
        "consistency": {
            "overall_consistency": _score01(consistency.get("overall_consistency")),
        },
    }


def _first_impression_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantic_data = _dict(_dict(payload.get("semantics")).get("data"))
    polish = _float_or_none(semantic_data.get("visual_polish_score"))
    if polish is not None and polish > 1:
        polish = polish / 10
    return {
        "status": "blocked" if capture.get("status") != "usable" else "available",
        "source": "llm_multimodal" if semantic_data else "heuristic",
        "visual_polish": round(max(0.0, min(1.0, polish)), 3) if polish is not None else None,
        "summary": _optional_str(semantic_data.get("visual_coherence")) or "",
        "evidence_refs": ["visual_signature:semantics"] if semantic_data else ["visual_signature:capture"],
    }


def _copy_visual_alignment_contract(payload: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    semantic_data = _dict(_dict(payload.get("semantics")).get("data"))
    coherence = semantic_data.get("visual_coherence")
    status = "blocked" if capture.get("status") != "usable" else "available" if coherence else "unknown"
    return {
        "status": status,
        "source": "llm_multimodal" if coherence else "heuristic",
        "summary": _optional_str(coherence) or "",
        "evidence_refs": ["visual_signature:semantics"] if coherence else ["visual_signature:layout", "visual_signature:typography"],
    }


def _tile_signals(
    payload: dict[str, Any],
    *,
    capture: dict[str, Any],
    identity: dict[str, Any],
    visual_system: dict[str, Any],
    first_impression: dict[str, Any],
    copy_visual_alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    if capture.get("status") != "usable":
        return [
            _tile_signal(
                tile=tile,
                effect="insufficient_evidence",
                confidence="high",
                source="heuristic",
                evidence_refs=["visual_signature:capture"],
                rationale=f"capture_unreliable:{capture.get('status')}",
            )
            for tile in VISUAL_TILE_IDS
        ]

    consistency = _score01(_dict(visual_system.get("consistency")).get("overall_consistency"))
    logo_confidence = _score01(identity.get("confidence"))
    has_logo = bool(identity.get("logo_detected"))
    density = str(_dict(visual_system.get("layout")).get("visual_density") or "unknown")
    layout_patterns = _string_list(_dict(visual_system.get("layout")).get("layout_patterns"))
    polish = first_impression.get("visual_polish")
    polish_score = _score01(polish)
    copy_summary = str(copy_visual_alignment.get("summary") or "")
    return [
        _threshold_signal("coherencia.C6", consistency, source="heuristic", evidence_refs=["visual_signature:consistency"]),
        _threshold_signal("brand_idea.I1", logo_confidence if has_logo else 0.0, source="heuristic", evidence_refs=["visual_signature:identity"]),
        _threshold_signal("brand_idea.I2", consistency, source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        _threshold_signal("brand_idea.I3", polish_score, source="llm_multimodal", evidence_refs=["visual_signature:first_impression"]),
        _threshold_signal("brand_idea.I6", 0.72 if layout_patterns else 0.35, source="heuristic", evidence_refs=["visual_signature:layout"]),
        _threshold_signal("brand_idea.I7", 0.7 if density in {"balanced", "sparse"} else 0.4, source="heuristic", evidence_refs=["visual_signature:layout"]),
        _threshold_signal("brand_idea.I8", consistency, source="heuristic", evidence_refs=["visual_signature:palette", "visual_signature:typography"]),
        _threshold_signal("brand_idea.I9", _distinctiveness_proxy(payload), source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        _threshold_signal("core_purpose.PR8", 0.72 if copy_summary else 0.35, source="llm_multimodal" if copy_summary else "heuristic", evidence_refs=copy_visual_alignment.get("evidence_refs") or ["visual_signature:layout"]),
        _threshold_signal("magnetism.MG1", polish_score, source="llm_multimodal", evidence_refs=first_impression.get("evidence_refs") or ["visual_signature:first_impression"]),
        _threshold_signal("magnetism.MG5", _distinctiveness_proxy(payload), source="heuristic", evidence_refs=["visual_signature:visual_system"]),
        _threshold_signal("magnetism.MG7", polish_score if copy_summary else consistency, source="llm_multimodal" if copy_summary else "heuristic", evidence_refs=["visual_signature:semantics"] if copy_summary else ["visual_signature:consistency"]),
    ]


def _threshold_signal(tile: str, score: float, *, source: str, evidence_refs: list[str]) -> dict[str, Any]:
    bounded = max(0.0, min(1.0, float(score or 0.0)))
    if bounded >= 0.62:
        effect = "supports"
    elif bounded <= 0.42:
        effect = "weakens"
    else:
        effect = "insufficient_evidence"
    confidence = "high" if bounded >= 0.75 or bounded <= 0.25 else "medium" if bounded >= 0.55 or bounded <= 0.45 else "low"
    return _tile_signal(
        tile=tile,
        effect=effect,
        confidence=confidence,
        source=source,
        evidence_refs=evidence_refs,
        rationale=f"visual_signal_score:{round(bounded, 3)}",
    )


def _tile_signal(
    *,
    tile: str,
    effect: str,
    confidence: str,
    source: str,
    evidence_refs: list[str],
    rationale: str,
) -> dict[str, Any]:
    return {
        "tile": tile,
        "effect": effect,
        "confidence": confidence,
        "source": source,
        "evidence_refs": _unique([str(item) for item in evidence_refs if item]),
        "rationale": rationale,
    }


def _limitations(payload: dict[str, Any], capture: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    extraction = _dict(payload.get("extraction_confidence"))
    limitations.extend(str(item) for item in extraction.get("limitations") or [])
    acquisition = _dict(payload.get("acquisition"))
    limitations.extend(f"acquisition_error:{item}" for item in acquisition.get("errors") or [])
    limitations.extend(f"acquisition_warning:{item}" for item in acquisition.get("warnings") or [])
    if capture.get("status") != "usable":
        limitations.append(f"capture_unreliable:{capture.get('status')}")
    if not capture.get("available"):
        limitations.append("screenshot_not_available")
    obstruction = _dict(capture.get("obstruction"))
    if obstruction.get("present"):
        limitations.append(f"visual_obstruction:{obstruction.get('type')}")
    if capture.get("first_fold_evaluable") is False:
        limitations.append("first_fold_not_evaluable")
    return _unique(limitations)


def _fingerprint_contract(
    payload: dict[str, Any],
    capture: dict[str, Any],
    screenshot: dict[str, Any],
) -> dict[str, Any]:
    normalized_payload = {
        "brand_name": payload.get("brand_name"),
        "website_url": payload.get("website_url"),
        "analyzed_url": payload.get("analyzed_url"),
        "capture": {
            "status": capture.get("status"),
            "capture_variant": capture.get("capture_variant"),
            "viewport": capture.get("viewport"),
            "url_final": capture.get("url_final"),
        },
        "identity": payload.get("logo"),
        "visual_system": {
            "colors": payload.get("colors"),
            "typography": payload.get("typography"),
            "layout": payload.get("layout"),
            "components": payload.get("components"),
            "consistency": payload.get("consistency"),
        },
        "semantics": payload.get("semantics"),
    }
    return {
        "screenshot_sha256": _screenshot_sha256(screenshot),
        "normalized_payload_sha256": _sha256_json(normalized_payload),
        "capture_variant": capture.get("capture_variant"),
        "captured_at": capture.get("captured_at"),
        "viewport": capture.get("viewport"),
        "url_requested": capture.get("url_requested"),
        "url_final": capture.get("url_final"),
    }


def _screenshot_sha256(screenshot: dict[str, Any]) -> str | None:
    explicit = screenshot.get("sha256") or screenshot.get("screenshot_sha256")
    if explicit:
        return str(explicit)
    path_value = screenshot.get("path")
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _component_types(components: dict[str, Any]) -> list[str]:
    rows = components.get("components")
    if not isinstance(rows, list):
        return []
    values = []
    for row in rows:
        if isinstance(row, dict) and row.get("type"):
            values.append(str(row["type"]))
    return _unique(values)


def _distinctiveness_proxy(payload: dict[str, Any]) -> float:
    colors = _dict(payload.get("colors"))
    typography = _dict(payload.get("typography"))
    layout = _dict(payload.get("layout"))
    score = 0.35
    if colors.get("palette_complexity") in {"medium", "high"}:
        score += 0.12
    if _string_list(colors.get("accent_candidates")):
        score += 0.1
    if typography.get("heading_scale") in {"expressive", "strong"}:
        score += 0.14
    if _string_list(layout.get("layout_patterns")):
        score += 0.08
    return round(min(score, 0.86), 3)


def _score01(value: Any) -> float:
    number = _float_or_none(value)
    if number is None:
        return 0.0
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value if item not in (None, "")] if isinstance(value, list) else []


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)

