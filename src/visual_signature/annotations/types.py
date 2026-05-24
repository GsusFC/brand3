"""Types for Visual Signature multimodal annotation overlays."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


AnnotationStatus = Literal["annotated", "partial", "not_interpretable", "failed"]
AnnotationSource = Literal["viewport_screenshot", "full_page_screenshot", "visual_signature_payload", "unknown"]
ConfidenceLevel = Literal["low", "medium", "high"]

ANNOTATION_TARGETS = (
    "logo_prominence",
    "imagery_style",
    "product_presence",
    "human_presence",
    "template_likeness",
    "visual_distinctiveness",
    "category_fit",
    "perceived_polish",
    "category_cues",
)


@dataclass(frozen=True)
class AnnotationRequest:
    brand_name: str
    website_url: str
    visual_signature_payload: dict[str, Any]
    expected_category: str | None = None
    viewport_screenshot_path: str | None = None
    full_page_screenshot_path: str | None = None
    baseline_context: dict[str, Any] | None = None
    metric_audit_context: dict[str, Any] | None = None
    prompt_version: str = "visual-signature-annotation-prompt-1"


@dataclass
class ProviderInfo:
    name: str
    model: str
    prompt_version: str
    mock: bool = True


@dataclass
class AnnotationTarget:
    label: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    source: AnnotationSource = "unknown"
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnnotationConfidence:
    score: float
    level: ConfidenceLevel
    factors: dict[str, float] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnnotationOverlay:
    version: str
    status: AnnotationStatus
    provider: ProviderInfo
    targets: dict[str, AnnotationTarget]
    overall_confidence: AnnotationConfidence
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["provider"] = asdict(self.provider)
        payload["targets"] = {key: value.to_dict() for key, value in self.targets.items()}
        payload["overall_confidence"] = self.overall_confidence.to_dict()
        return payload


@dataclass
class AnnotationProviderResult:
    status: AnnotationStatus
    targets: dict[str, dict[str, Any]]
    provider_name: str
    model: str
    prompt_version: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)
