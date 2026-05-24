"""Apply offline multimodal annotation overlays to Visual Signature payloads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.visual_signature.annotations.confidence import (
    calculate_annotation_confidence,
    normalize_confidence,
)
from src.visual_signature.annotations.providers.base import MultimodalAnnotationProvider
from src.visual_signature.annotations.providers.mock_provider import MockMultimodalAnnotationProvider
from src.visual_signature.annotations.types import (
    ANNOTATION_TARGETS,
    AnnotationOverlay,
    AnnotationRequest,
    AnnotationStatus,
    AnnotationTarget,
    ProviderInfo,
)


VERSION = "visual-signature-annotations-mvp-1"
VALID_STATUSES = {"annotated", "partial", "not_interpretable", "failed"}
VALID_SOURCES = {"viewport_screenshot", "full_page_screenshot", "visual_signature_payload", "unknown"}


def annotate_visual_signature(
    *,
    visual_signature_payload: dict[str, Any],
    provider: MultimodalAnnotationProvider | None = None,
    expected_category: str | None = None,
    viewport_screenshot_path: str | None = None,
    full_page_screenshot_path: str | None = None,
    baseline_context: dict[str, Any] | None = None,
    metric_audit_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return payload plus top-level annotation overlay.

    This function is offline-only by default. It uses the mock provider unless a
    caller injects another provider explicitly.
    """
    payload = deepcopy(visual_signature_payload)
    request = AnnotationRequest(
        brand_name=str(payload.get("brand_name") or ""),
        website_url=str(payload.get("website_url") or payload.get("analyzed_url") or ""),
        visual_signature_payload=payload,
        expected_category=expected_category or _expected_category(payload),
        viewport_screenshot_path=viewport_screenshot_path,
        full_page_screenshot_path=full_page_screenshot_path,
        baseline_context=baseline_context,
        metric_audit_context=metric_audit_context,
    )
    if _not_interpretable(payload):
        overlay = _not_interpretable_overlay(request, provider or MockMultimodalAnnotationProvider())
    else:
        overlay = _provider_overlay(request, provider or MockMultimodalAnnotationProvider(), payload)
    payload["annotations"] = overlay.to_dict()
    validation = validate_annotation_overlay(payload["annotations"])
    if not validation["valid"]:
        payload["annotations"]["status"] = "failed"
        payload["annotations"].setdefault("errors", []).extend(validation["errors"])
    return payload


def validate_annotation_overlay(overlay: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if overlay.get("version") != VERSION:
        errors.append("annotation_version_invalid")
    if overlay.get("status") not in VALID_STATUSES:
        errors.append("annotation_status_invalid")
    targets = overlay.get("targets")
    if not isinstance(targets, dict):
        errors.append("annotation_targets_missing")
        targets = {}
    missing = [target for target in ANNOTATION_TARGETS if target not in targets]
    if missing and overlay.get("status") == "annotated":
        errors.append(f"annotation_targets_missing:{','.join(missing)}")
    elif missing:
        warnings.append(f"annotation_targets_missing:{','.join(missing)}")
    for key, value in targets.items():
        if key not in ANNOTATION_TARGETS:
            warnings.append(f"annotation_target_unknown:{key}")
        if not isinstance(value, dict):
            errors.append(f"{key}:target_must_be_object")
            continue
        if not str(value.get("label") or "").strip():
            errors.append(f"{key}:label_missing")
        if not 0 <= normalize_confidence(value.get("confidence")) <= 1:
            errors.append(f"{key}:confidence_invalid")
        if value.get("source") not in VALID_SOURCES:
            errors.append(f"{key}:source_invalid")
        if not isinstance(value.get("evidence"), list):
            errors.append(f"{key}:evidence_must_be_list")
        if not isinstance(value.get("limitations"), list):
            errors.append(f"{key}:limitations_must_be_list")
    confidence = overlay.get("overall_confidence")
    if not isinstance(confidence, dict):
        errors.append("overall_confidence_missing")
    elif not 0 <= normalize_confidence(confidence.get("score")) <= 1:
        errors.append("overall_confidence_score_invalid")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _provider_overlay(
    request: AnnotationRequest,
    provider: MultimodalAnnotationProvider,
    payload: dict[str, Any],
) -> AnnotationOverlay:
    try:
        result = provider.annotate(request)
    except Exception as exc:
        result = MockMultimodalAnnotationProvider(fail=True).annotate(request)
        result.errors.append(str(exc))
    status = _normalize_status(result.status)
    targets = _normalize_targets(result.targets)
    if status == "annotated" and len(targets) < len(ANNOTATION_TARGETS):
        status = "partial"
    confidence = calculate_annotation_confidence(status=status, targets=targets, visual_signature_payload=payload)
    return AnnotationOverlay(
        version=VERSION,
        status=status,
        provider=ProviderInfo(
            name=result.provider_name,
            model=result.model,
            prompt_version=result.prompt_version,
            mock=result.provider_name == "mock",
        ),
        targets=targets,
        overall_confidence=confidence,
        errors=result.errors,
        warnings=result.warnings,
    )


def _not_interpretable_overlay(
    request: AnnotationRequest,
    provider: MultimodalAnnotationProvider,
) -> AnnotationOverlay:
    status: AnnotationStatus = "not_interpretable"
    return AnnotationOverlay(
        version=VERSION,
        status=status,
        provider=ProviderInfo(
            name=getattr(provider, "name", "mock"),
            model=getattr(provider, "model", "mock-visual-annotator-v1"),
            prompt_version=request.prompt_version,
            mock=getattr(provider, "name", "mock") == "mock",
        ),
        targets={},
        overall_confidence=calculate_annotation_confidence(
            status=status,
            targets={},
            visual_signature_payload=request.visual_signature_payload,
        ),
        warnings=["visual_signature_not_interpretable"],
    )


def _normalize_targets(raw_targets: dict[str, Any]) -> dict[str, AnnotationTarget]:
    targets: dict[str, AnnotationTarget] = {}
    for key in ANNOTATION_TARGETS:
        value = raw_targets.get(key)
        if not isinstance(value, dict):
            continue
        targets[key] = AnnotationTarget(
            label=str(value.get("label") or "unknown"),
            confidence=normalize_confidence(value.get("confidence")),
            evidence=[str(item) for item in value.get("evidence") or [] if str(item).strip()],
            source=_normalize_source(value.get("source")),
            limitations=[str(item) for item in value.get("limitations") or [] if str(item).strip()],
        )
    return targets


def _normalize_status(value: Any) -> AnnotationStatus:
    status = str(value or "failed")
    if status in VALID_STATUSES:
        return status  # type: ignore[return-value]
    return "failed"


def _normalize_source(value: Any) -> str:
    source = str(value or "unknown")
    return source if source in VALID_SOURCES else "unknown"


def _not_interpretable(payload: dict[str, Any]) -> bool:
    if payload.get("interpretation_status") == "not_interpretable":
        return True
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    return bool(vision) and not screenshot.get("available")


def _expected_category(payload: dict[str, Any]) -> str | None:
    calibration = payload.get("calibration") if isinstance(payload.get("calibration"), dict) else {}
    return calibration.get("expected_category")
