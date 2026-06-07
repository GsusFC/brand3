"""Data contracts for lab-only visual diagnosis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


VISUAL_DIAGNOSIS_SCHEMA_VERSION = "visual-diagnosis-v1"

DiagnosisStatus = Literal["usable", "limited", "unavailable"]
CaptureQuality = Literal["good", "partial", "poor", "missing", "unknown"]
CaptureType = Literal["viewport", "full_page", "unknown"]
ObstructionState = Literal["none", "cookie_banner", "modal", "login_wall", "paywall", "unknown"]
IdentityRead = Literal[
    "visually_distinctive",
    "coherent_but_generic",
    "polished_but_undifferentiated",
    "functionally_clear",
    "editorially_coherent",
    "emotionally_coherent",
    "commerce_clear",
    "practical_but_generic",
    "weak_or_inconsistent",
    "not_evaluable",
]
ReferenceProfile = Literal[
    "template_saas",
    "premium_luxury",
    "developer_first",
    "editorial_media",
    "ai_native",
    "wellness_lifestyle",
    "ecommerce_mass_market",
    "local_service",
    "unknown",
]
SignalLevel = Literal["high", "medium", "low", "unknown"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class VisualDiagnosisCapture:
    available: bool
    type: CaptureType = "unknown"
    quality: CaptureQuality = "unknown"
    obstruction: ObstructionState = "unknown"
    limitations: list[str] = field(default_factory=list)


@dataclass
class VisualDiagnosisRead:
    identity_read: IdentityRead
    reference_profile: ReferenceProfile = "unknown"
    profile_confidence: ConfidenceLevel = "low"
    distinctiveness: SignalLevel = "unknown"
    polish: SignalLevel = "unknown"
    brand_fit: SignalLevel = "unknown"
    template_likeness: SignalLevel = "unknown"


@dataclass
class VisualDiagnosisSignals:
    positive: list[str] = field(default_factory=list)
    negative: list[str] = field(default_factory=list)
    antipatterns: list[str] = field(default_factory=list)


@dataclass
class VisualDiagnosis:
    status: DiagnosisStatus
    capture: VisualDiagnosisCapture
    diagnosis: VisualDiagnosisRead
    signals: VisualDiagnosisSignals = field(default_factory=VisualDiagnosisSignals)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    limitations: list[str] = field(default_factory=list)
    schema_version: Literal["visual-diagnosis-v1"] = VISUAL_DIAGNOSIS_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)
