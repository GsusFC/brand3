"""Mock provider for offline Visual Signature annotation calibration."""

from __future__ import annotations

from typing import Any

from src.visual_signature.annotations.types import (
    ANNOTATION_TARGETS,
    AnnotationProviderResult,
    AnnotationRequest,
)


class MockMultimodalAnnotationProvider:
    """Deterministic provider used in tests and offline corpus scaffolding."""

    name = "mock"
    model = "mock-visual-annotator-v1"

    def __init__(self, response: dict[str, Any] | None = None, *, fail: bool = False):
        self.response = response
        self.fail = fail

    def annotate(self, request: AnnotationRequest) -> AnnotationProviderResult:
        if self.fail:
            return AnnotationProviderResult(
                status="failed",
                targets={},
                provider_name=self.name,
                model=self.model,
                prompt_version=request.prompt_version,
                errors=["mock_provider_failure"],
            )
        if self.response is not None:
            return AnnotationProviderResult(
                status=str(self.response.get("status") or "annotated"),  # type: ignore[arg-type]
                targets=dict(self.response.get("targets") or {}),
                provider_name=str(self.response.get("provider_name") or self.name),
                model=str(self.response.get("model") or self.model),
                prompt_version=str(self.response.get("prompt_version") or request.prompt_version),
                errors=list(self.response.get("errors") or []),
                warnings=list(self.response.get("warnings") or []),
                raw_response=dict(self.response),
            )
        return AnnotationProviderResult(
            status="annotated",
            targets=_default_targets(request),
            provider_name=self.name,
            model=self.model,
            prompt_version=request.prompt_version,
            raw_response={"mock": True},
        )


def _default_targets(request: AnnotationRequest) -> dict[str, dict[str, Any]]:
    payload = request.visual_signature_payload
    vision = payload.get("vision") if isinstance(payload.get("vision"), dict) else {}
    screenshot = vision.get("screenshot") if isinstance(vision.get("screenshot"), dict) else {}
    source = "viewport_screenshot" if screenshot.get("available") else "visual_signature_payload"
    category = (request.expected_category or (payload.get("calibration") or {}).get("expected_category") or "").lower()
    density = str(vision.get("viewport_visual_density") or "unknown")
    has_logo = bool((payload.get("logo") or {}).get("logo_detected"))
    has_product_images = int((payload.get("assets") or {}).get("image_count") or 0) > 0
    labels = {
        "logo_prominence": "clear" if has_logo else "unknown",
        "imagery_style": "product_ui" if "saas" in category or "developer" in category else "photographic",
        "product_presence": "visible" if has_product_images else "unclear",
        "human_presence": "unknown",
        "template_likeness": "high" if "template" in category else ("medium" if density == "dense" else "low"),
        "visual_distinctiveness": "moderate",
        "category_fit": "aligned" if category else "unknown",
        "perceived_polish": "medium",
        "category_cues": category.replace("_", " ") or "unknown",
    }
    targets: dict[str, dict[str, Any]] = {}
    for target in ANNOTATION_TARGETS:
        label = labels[target]
        targets[target] = {
            "label": label,
            "confidence": 0.72 if label != "unknown" else 0.25,
            "evidence": [f"Mock annotation for {target} from available Visual Signature evidence."],
            "source": source,
            "limitations": ["mock_provider_no_real_visual_semantics"],
        }
    return targets
