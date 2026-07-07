from __future__ import annotations

from typing import Any


def reliable_visual_semantics_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return only visual semantics that are safe to feed into downstream interpreters.

    Visual Signature may persist semantic observations even when the same payload
    also marks the capture as blocked, review-required, or not valid for first
    impression. In that case we keep the payload for audit/debug, but downstream
    scoring must treat it as unavailable rather than as positive or negative
    brand evidence.
    """

    if not isinstance(payload, dict):
        return {"status": "not_detected", "data": {}}

    semantics = _extract_semantics(payload)
    if not _has_usable_semantics(semantics):
        return {"status": "not_detected", "data": {}}

    run_metadata = _as_dict(payload.get("run_metadata"))
    scan_status = str(run_metadata.get("visual_signature_scan_status") or "").strip().lower()
    raw_vs = _as_dict(payload.get("raw_visual_signature_payload"))
    vision = _as_dict(payload.get("vision_payload"))
    obstruction = _as_dict(vision.get("viewport_obstruction"))
    if not obstruction:
        obstruction = _as_dict(_as_dict(raw_vs.get("vision")).get("viewport_obstruction"))
    if not obstruction:
        obstruction = _as_dict(_as_dict(raw_vs.get("acquisition")).get("viewport_obstruction"))

    first_impression_valid = obstruction.get("first_impression_valid")
    obstruction_present = bool(obstruction.get("present"))
    obstruction_severity = str(obstruction.get("severity") or "").strip().lower()

    unreliable_reasons: list[str] = []
    if scan_status == "review_required":
        unreliable_reasons.append("visual_signature_review_required")
    if first_impression_valid is False:
        unreliable_reasons.append("first_impression_invalid")
    if obstruction_present and obstruction_severity == "blocking":
        unreliable_reasons.append("blocking_viewport_obstruction")

    if unreliable_reasons:
        return {
            "status": "unreliable",
            "data": {},
            "reason_codes": unreliable_reasons,
        }
    return {"status": "detected", "data": semantics}


def _extract_semantics(payload: dict[str, Any]) -> dict[str, Any]:
    direct = payload.get("semantics")
    if isinstance(direct, dict):
        return direct
    signature = _as_dict(payload.get("signature"))
    signature_semantics = signature.get("semantics")
    if isinstance(signature_semantics, dict):
        return signature_semantics
    raw_vs = _as_dict(payload.get("raw_visual_signature_payload"))
    raw_semantics = _as_dict(raw_vs.get("semantics"))
    raw_data = raw_semantics.get("data")
    if isinstance(raw_data, dict):
        return raw_data
    return {}


def _has_usable_semantics(semantics: dict[str, Any]) -> bool:
    if not isinstance(semantics, dict) or not semantics:
        return False
    for value in semantics.values():
        if value is None:
            continue
        if isinstance(value, str) and value.strip() and value.strip().lower() != "not_detected":
            return True
        if not isinstance(value, str):
            return True
    return False


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
