"""Models for the local Visual Signature platform bundle."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlatformArtifact:
    key: str
    label: str
    path: str
    artifact_type: str
    required: bool = True
    exists: bool = False
    record_type: str | None = None
    generated_at: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlatformSection:
    key: str
    title: str
    status: str
    summary: str
    badges: list[str] = field(default_factory=list)
    artifact_keys: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    items: list[dict[str, Any]] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlatformBundle:
    schema_version: str
    record_type: str
    generated_at: str
    platform_status: str
    guardrails: list[str]
    artifacts: list[PlatformArtifact]
    sections: list[PlatformSection]
    navigation: list[dict[str, str]]
    next_steps: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_type": self.record_type,
            "generated_at": self.generated_at,
            "platform_status": self.platform_status,
            "guardrails": list(self.guardrails),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "sections": [section.to_dict() for section in self.sections],
            "navigation": list(self.navigation),
            "next_steps": list(self.next_steps),
            "notes": list(self.notes),
        }
