from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


PROMOTION_MAX_LIMITED_REVIEW_COUNT = 3
PROMOTION_MAX_LIMITED_MISSING_URL_COUNT = 2
PROMOTION_BLOCKING_REVIEW_REASONS = {"same_name_different_root_domain"}
MANUAL_AUDIT_MATERIAL_FIELDS = {"proof_points", "founder_or_press_context", "competitive_context"}
RESERVED_OR_PLACEHOLDER_ROOTS = {"example.com", "example.net", "example.org", "example.edu"}
RESERVED_OR_PLACEHOLDER_TLDS = {"example", "invalid", "localhost", "test"}


def _top_counts(counts: dict[str, Any], limit: int = 3) -> list[tuple[str, int]]:
    pairs = [(str(key), int(value or 0)) for key, value in counts.items()]
    return sorted(pairs, key=lambda item: (-item[1], item[0]))[:limit]


def _merge_counts(target: dict[str, int], source: dict[str, Any]) -> None:
    for key, value in source.items():
        target[str(key)] = target.get(str(key), 0) + int(value or 0)


def _accumulate_semantic_evidence(
    *,
    target: dict[str, Any],
    payload: dict[str, Any],
    run_id: int | None,
    brand_name: str,
) -> None:
    if not payload:
        return
    classifier = str(payload.get("classifier") or "")
    if classifier:
        target["classifier"] = classifier
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    target["accepted_material"] = int(target.get("accepted_material") or 0) + int(
        summary.get("accepted_material_count") or 0
    )
    target["accepted_weak"] = int(target.get("accepted_weak") or 0) + int(summary.get("accepted_weak_count") or 0)
    for source_key, target_key in (
        ("semantic_class_counts", "semantic_class_counts"),
        ("materiality_counts", "materiality_counts"),
        ("entity_fit_counts", "entity_fit_counts"),
    ):
        counts = summary.get(source_key) if isinstance(summary.get(source_key), dict) else {}
        bucket = target.setdefault(target_key, {})
        for key, value in counts.items():
            bucket[str(key)] = int(bucket.get(str(key)) or 0) + int(value or 0)
        target[target_key] = dict(sorted(bucket.items()))
    weak_examples = target.setdefault("weak_examples", [])
    for item in payload.get("assessments") or []:
        if not isinstance(item, dict):
            continue
        if item.get("gate_status") != "accepted" or item.get("materiality") != "low":
            continue
        weak_examples.append(
            {
                "run_id": run_id,
                "brand_name": brand_name,
                "semantic_class": item.get("semantic_class") or "",
                "entity_fit": item.get("entity_fit") or "",
                "url": item.get("url") or "",
                "text_preview": item.get("text_preview") or "",
                "reason_codes": list(item.get("reason_codes") or []),
            }
        )
    target["weak_examples"] = weak_examples[:20]


def _accumulate_semantic_llm_comparison(
    *,
    target: dict[str, Any],
    heuristic: dict[str, Any],
    llm: dict[str, Any],
    run_id: int | None,
    brand_name: str,
) -> None:
    status = str(llm.get("status") or "missing")
    status_counts = target.setdefault("status_counts", {})
    status_counts[status] = int(status_counts.get(status) or 0) + 1
    target["status_counts"] = dict(sorted(status_counts.items()))
    model = str(llm.get("model") or "")
    if model:
        models = target.setdefault("models", {})
        models[model] = int(models.get(model) or 0) + 1
        target["models"] = dict(sorted(models.items()))

    heuristic_by_id = {
        str(item.get("observation_id") or ""): item
        for item in heuristic.get("assessments") or []
        if isinstance(item, dict)
    }
    llm_rows = [item for item in llm.get("assessments") or [] if isinstance(item, dict)]
    semantic_disagreements = 0
    materiality_disagreements = 0
    examples: list[dict[str, Any]] = []
    for item in llm_rows:
        observation_id = str(item.get("observation_id") or "")
        baseline = heuristic_by_id.get(observation_id)
        if not baseline:
            continue
        class_changed = item.get("semantic_class") != baseline.get("semantic_class")
        materiality_changed = item.get("materiality") != baseline.get("materiality")
        if class_changed:
            semantic_disagreements += 1
        if materiality_changed:
            materiality_disagreements += 1
        if class_changed or materiality_changed:
            examples.append(
                {
                    "observation_id": observation_id,
                    "heuristic_class": baseline.get("semantic_class") or "",
                    "llm_class": item.get("semantic_class") or "",
                    "heuristic_materiality": baseline.get("materiality") or "",
                    "llm_materiality": item.get("materiality") or "",
                    "llm_reason_codes": list(item.get("reason_codes") or []),
                }
            )
    target["semantic_class_disagreement_count"] = int(target.get("semantic_class_disagreement_count") or 0) + semantic_disagreements
    target["materiality_disagreement_count"] = int(target.get("materiality_disagreement_count") or 0) + materiality_disagreements
    rows = target.setdefault("rows", [])
    rows.append(
        {
            "run_id": run_id,
            "brand_name": brand_name,
            "status": status,
            "model": model,
            "assessment_count": len(llm_rows),
            "semantic_class_disagreement_count": semantic_disagreements,
            "materiality_disagreement_count": materiality_disagreements,
            "examples": examples[:5],
            "reason": llm.get("reason") or "",
        }
    )
    target["rows"] = rows


def _collect_examples(
    target: dict[str, list[dict[str, Any]]],
    observations: list[dict[str, Any]],
    *,
    run_id: Any,
    brand_name: str,
    limit_per_reason: int = 3,
) -> None:
    for item in observations:
        if not isinstance(item, dict):
            continue
        reason = _observation_reason(item)
        examples = target.setdefault(reason, [])
        if len(examples) >= limit_per_reason:
            continue
        examples.append(
            {
                "run_id": run_id,
                "brand_name": brand_name,
                "feature_name": str(item.get("feature_name") or ""),
                "provider": str(item.get("provider") or ""),
                "source_class": str(item.get("source_class") or ""),
                "eligibility": str(item.get("eligibility") or ""),
                "url": str(item.get("url") or ""),
                "text_preview": _preview_text(item.get("text"), limit=160),
            }
        )


def _compact_review_observations(observations: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for item in observations:
        if not isinstance(item, dict):
            continue
        examples.append(
            {
                "feature_name": str(item.get("feature_name") or ""),
                "provider": str(item.get("provider") or ""),
                "source_class": str(item.get("source_class") or ""),
                "eligibility": str(item.get("eligibility") or ""),
                "classification_reason": _observation_reason(item),
                "url": str(item.get("url") or ""),
                "text_preview": _preview_text(item.get("text"), limit=160),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _changed_material_field_previews(comparison: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "field": str(field.get("field") or ""),
            "current_preview": _preview_text(field.get("legacy_preview"), limit=160),
            "vnext_preview": _preview_text(field.get("graph_preview"), limit=160),
        }
        for field in comparison.get("fields") or []
        if isinstance(field, dict)
        and field.get("changed")
        and str(field.get("field") or "") in MANUAL_AUDIT_MATERIAL_FIELDS
    ]


def _review_material_overlaps(*, gate_payload: dict[str, Any], vnext_pack: dict[str, Any]) -> list[dict[str, str]]:
    material_text_by_field = {
        field: _pack_field_text(vnext_pack.get(field))
        for field in MANUAL_AUDIT_MATERIAL_FIELDS
        if _pack_field_text(vnext_pack.get(field))
    }
    overlaps: list[dict[str, str]] = []
    for item in gate_payload.get("review_required") or []:
        if not isinstance(item, dict):
            continue
        observation_text = _normalized_overlap_text(item.get("text"))
        if len(observation_text) < 24:
            continue
        for field, field_text in material_text_by_field.items():
            if _text_overlaps_field(observation_text, field_text):
                overlaps.append(
                    {
                        "field": field,
                        "feature_name": str(item.get("feature_name") or ""),
                        "classification_reason": _observation_reason(item),
                        "url": str(item.get("url") or ""),
                        "text_preview": _preview_text(item.get("text"), limit=160),
                    }
                )
    overlaps.extend(_material_profile_source_overlaps(gate_payload=gate_payload, vnext_pack=vnext_pack))
    return _dedupe_overlap_items(overlaps)


def _material_profile_source_overlaps(*, gate_payload: dict[str, Any], vnext_pack: dict[str, Any]) -> list[dict[str, str]]:
    unresolved_profile_urls = {
        _url_identity(item.get("url"))
        for item in gate_payload.get("review_required") or []
        if isinstance(item, dict)
        and _observation_reason(item) == "same_name_external_profile_not_alias"
        and _url_identity(item.get("url"))
    }
    if not unresolved_profile_urls:
        return []
    overlaps: list[dict[str, str]] = []
    for field in MANUAL_AUDIT_MATERIAL_FIELDS:
        value = vnext_pack.get(field)
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            source_url = str(item.get("source_url") or "").strip()
            if _url_identity(source_url) not in unresolved_profile_urls:
                continue
            overlaps.append(
                {
                    "field": field,
                    "feature_name": "material_source_url",
                    "classification_reason": "same_name_external_profile_material_source",
                    "url": source_url,
                    "text_preview": _preview_text(item.get("text"), limit=160),
                }
            )
    return overlaps


def _dedupe_overlap_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for item in items:
        key = (
            str(item.get("field") or ""),
            str(item.get("feature_name") or ""),
            str(item.get("classification_reason") or ""),
            str(item.get("url") or ""),
            str(item.get("text_preview") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _pack_field_text(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item or ""))
        return _normalized_overlap_text(" ".join(parts))
    return _normalized_overlap_text(value)


def _text_overlaps_field(observation_text: str, field_text: str) -> bool:
    if observation_text in field_text:
        return True
    words = observation_text.split()
    if len(words) < 5:
        return False
    head = " ".join(words[:8])
    tail = " ".join(words[-8:])
    return (len(head) >= 24 and head in field_text) or (len(tail) >= 24 and tail in field_text)


def _normalized_overlap_text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _observation_reason(item: dict[str, Any]) -> str:
    return (
        str(item.get("classification_reason") or "").strip()
        or str(item.get("eligibility") or "").strip()
        or str(item.get("source_class") or "").strip()
        or "unknown"
    )


def _preview_text(value: Any, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit] if text else "-"


def _host(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    return (parsed.netloc or parsed.path).strip("/").removeprefix("www.")


def _url_identity(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = (parsed.netloc or parsed.path).strip("/").removeprefix("www.")
    path = parsed.path.strip("/")
    if not parsed.netloc and "/" in parsed.path:
        host, _, path = parsed.path.partition("/")
        host = host.strip("/").removeprefix("www.")
        path = path.strip("/")
    return f"{host}/{path}".rstrip("/")


def _root_domain(host: str) -> str:
    parts = [part for part in str(host or "").split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return str(host or "")


def _count_dict(pairs: list[tuple[str, int]]) -> dict[str, int]:
    return {key: value for key, value in pairs}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _join_unique(values: list[Any]) -> str:
    return ", ".join(_unique([str(value or "") for value in values]))


def _context_url_identity(value: Any) -> str:
    identity = _url_identity(value)
    if not identity:
        return ""
    return f"https://{identity}"


def _batch_recommendation(
    totals: dict[str, int],
    status_counts: dict[str, int],
    review_reasons: dict[str, int],
) -> dict[str, Any]:
    reason_codes: list[str] = []
    if totals.get("material_lost_fields", 0) > 0:
        reason_codes.append("material_regressions_present")
    if status_counts.get("blocked", 0) > 0:
        reason_codes.append("blocked_runs_present")
    if totals.get("review_required", 0) > 0:
        reason_codes.append("review_required_evidence_present")
    if review_reasons.get("missing_evidence_url", 0) > 0:
        reason_codes.append("missing_evidence_url_needs_source_propagation")
    if totals.get("reclassified_to_noise", 0) > 0:
        reason_codes.append("reclassified_noise_should_be_reviewed")

    if totals.get("material_lost_fields", 0) > 0 or status_counts.get("blocked", 0) > 0:
        status = "blocked"
    elif totals.get("review_required", 0) > 0:
        status = "review_required"
    else:
        status = "promising"

    return {
        "status": status,
        "reason_codes": reason_codes or ["no_batch_blockers_detected"],
    }
