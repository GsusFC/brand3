"""Types for local Visual Signature vision enrichment."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


ScreenshotQuality = Literal["missing", "unreadable", "blank", "low_detail", "usable"]
CaptureType = Literal["viewport", "full_page", "unknown"]
VisualDensity = Literal["sparse", "balanced", "dense", "unknown"]
CompositionClass = Literal["blank", "sparse_single_focus", "balanced_blocks", "dense_grid", "unknown"]
ConfidenceLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class RasterImage:
    width: int
    height: int
    pixels: list[tuple[int, int, int]]
    source_path: str


@dataclass
class VisionScreenshotEvidence:
    available: bool
    source: str = "none"
    path: str | None = None
    capture_type: CaptureType = "unknown"
    page_url: str | None = None
    width: int | None = None
    height: int | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    quality: ScreenshotQuality = "missing"
    file_size_bytes: int | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class VisionColor:
    hex: str
    occurrences: int
    ratio: float


@dataclass
class VisionPaletteEvidence:
    dominant_colors: list[VisionColor] = field(default_factory=list)
    color_count: int = 0
    confidence: float = 0.0


@dataclass
class VisionCompositionEvidence:
    whitespace_ratio: float | None = None
    visual_density: VisualDensity = "unknown"
    composition_classification: CompositionClass = "unknown"
    edge_density: float | None = None
    color_variance: float | None = None
    confidence: float = 0.0


@dataclass
class VisionConfidence:
    score: float
    level: ConfidenceLevel
    factors: dict[str, float]
    limitations: list[str] = field(default_factory=list)


@dataclass
class VisionEvidence:
    screenshot: VisionScreenshotEvidence
    screenshot_palette: VisionPaletteEvidence
    composition: VisionCompositionEvidence
    vision_confidence: VisionConfidence
    agreement: dict[str, object] | None = None
    viewport_palette: VisionPaletteEvidence | None = None
    viewport_whitespace_ratio: float | None = None
    viewport_visual_density: VisualDensity = "unknown"
    viewport_composition: VisionCompositionEvidence | None = None
    viewport_confidence: VisionConfidence | None = None
    viewport_obstruction: dict[str, object] | None = None
    version: Literal["vision-enrichment-mvp-1"] = "vision-enrichment-mvp-1"

    def to_dict(self) -> dict:
        return asdict(self)
