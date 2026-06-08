"""Types for Brand3 Visual Signature structured evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol


VisualSignatureAdapterName = Literal[
    "existing_web_data",
    "firecrawl",
    "hyperbrowser",
    "playwright",
    "browserbase",
    "vision",
    "brandfetch",
    "custom",
]

VisualSignalSource = Literal[
    "rendered_html",
    "raw_html",
    "markdown",
    "links",
    "images",
    "screenshot",
    "metadata",
    "adapter",
    "existing_web_data",
]


@dataclass
class VisualSignatureInput:
    brand_name: str
    website_url: str


@dataclass
class VisualAssetCandidate:
    url: str
    source: VisualSignalSource
    alt: str | None = None
    width: int | None = None
    height: int | None = None
    role_hint: Literal["logo", "icon", "illustration", "photo", "background", "unknown"] = "unknown"


@dataclass
class ScreenshotSignal:
    url: str
    source: VisualSignalSource
    viewport: dict[str, Any] = field(default_factory=dict)
    expires_at: str | None = None


@dataclass
class VisualAcquisitionResult:
    adapter: VisualSignatureAdapterName
    requested_url: str
    links: list[str] = field(default_factory=list)
    images: list[VisualAssetCandidate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    acquired_at: str = ""
    final_url: str | None = None
    status_code: int | None = None
    rendered_html: str = ""
    raw_html: str = ""
    markdown: str = ""
    screenshot: ScreenshotSignal | None = None


class VisualAcquisitionAdapter(Protocol):
    name: VisualSignatureAdapterName

    def acquire(self, input_data: VisualSignatureInput) -> VisualAcquisitionResult:
        ...


@dataclass
class ColorSignal:
    hex: str
    role: Literal["background", "text", "accent", "border", "surface", "unknown"]
    occurrences: int
    source: VisualSignalSource
    confidence: float


@dataclass
class NormalizedColorSignals:
    palette: list[ColorSignal] = field(default_factory=list)
    dominant_colors: list[str] = field(default_factory=list)
    accent_candidates: list[str] = field(default_factory=list)
    background_candidates: list[str] = field(default_factory=list)
    text_color_candidates: list[str] = field(default_factory=list)
    palette_complexity: Literal["low", "medium", "high", "unknown"] = "unknown"
    confidence: float = 0.0


@dataclass
class TypographySignal:
    family: str
    role: Literal["heading", "body", "display", "ui", "unknown"]
    occurrences: int
    source: VisualSignalSource
    confidence: float


@dataclass
class NormalizedTypographySignals:
    font_families: list[TypographySignal] = field(default_factory=list)
    heading_scale: Literal["flat", "moderate", "expressive", "unknown"] = "unknown"
    weight_range: dict[str, int] = field(default_factory=dict)
    size_samples_px: list[float] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class LogoCandidate:
    location: Literal["header", "nav", "footer", "metadata", "body", "unknown"]
    source: VisualSignalSource
    confidence: float
    url: str | None = None
    text: str | None = None
    alt: str | None = None


@dataclass
class NormalizedLogoSignals:
    logo_detected: bool = False
    candidates: list[LogoCandidate] = field(default_factory=list)
    favicon_detected: bool = False
    textual_brand_mark_detected: bool = False
    primary_location: Literal["header", "nav", "footer", "metadata", "body", "unknown"] = "unknown"
    confidence: float = 0.0


@dataclass
class NormalizedLayoutSignals:
    has_header: bool = False
    has_navigation: bool = False
    has_hero: bool = False
    has_main_content: bool = False
    has_footer: bool = False
    section_count: int = 0
    layout_patterns: list[str] = field(default_factory=list)
    visual_density: Literal["sparse", "balanced", "dense", "unknown"] = "unknown"
    confidence: float = 0.0


@dataclass
class ComponentSignal:
    type: Literal[
        "navigation",
        "button",
        "card",
        "form",
        "cta",
        "accordion",
        "tabs",
        "modal",
        "pricing",
        "unknown",
    ]
    count: int
    labels: list[str]
    source: VisualSignalSource
    confidence: float


@dataclass
class NormalizedComponentSignals:
    components: list[ComponentSignal] = field(default_factory=list)
    primary_ctas: list[str] = field(default_factory=list)
    interaction_patterns: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class NormalizedAssetSignals:
    image_count: int = 0
    svg_count: int = 0
    video_count: int = 0
    background_image_count: int = 0
    logo_image_candidates: list[VisualAssetCandidate] = field(default_factory=list)
    icon_candidates: list[VisualAssetCandidate] = field(default_factory=list)
    screenshot_available: bool = False
    asset_mix: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class NormalizedConsistencySignals:
    color_consistency: float = 0.0
    typography_consistency: float = 0.0
    component_consistency: float = 0.0
    asset_consistency: float = 0.0
    overall_consistency: float = 0.0
    notes: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ExtractionConfidence:
    score: float
    level: Literal["low", "medium", "high"]
    factors: dict[str, float]
    limitations: list[str]


@dataclass
class VisualSignature:
    brand_name: str
    website_url: str
    analyzed_url: str
    interpretation_status: Literal["interpretable", "not_interpretable"]
    acquisition: dict[str, Any]
    colors: NormalizedColorSignals
    typography: NormalizedTypographySignals
    logo: NormalizedLogoSignals
    layout: NormalizedLayoutSignals
    components: NormalizedComponentSignals
    assets: NormalizedAssetSignals
    consistency: NormalizedConsistencySignals
    extraction_confidence: ExtractionConfidence
    semantics: dict[str, Any] | None = None
    version: Literal["visual-signature-mvp-1"] = "visual-signature-mvp-1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
