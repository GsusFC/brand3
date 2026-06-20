"""Schemas for Brand3 market classification.

These dataclasses keep the contract deterministic and serializable. They are
small on purpose: storage can begin as JSON while preserving enough traceability
for human review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.classification.market_taxonomy import (
    CLASSIFIERS,
    CONFIDENCE_LEVELS,
    GROUPS,
    TAG_STATUSES,
    TAXONOMY_VERSION,
    canonical_tag,
)


@dataclass(frozen=True)
class ClassificationTag:
    group: str
    tag: str
    confidence: str
    status: str = "proposed"
    evidence_text: str = ""
    source_url: str = ""
    classifier: str = "heuristic"
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.group not in GROUPS:
            raise ValueError(f"Unknown market classification group: {self.group}")
        canonical = canonical_tag(self.group, self.tag)
        if canonical is None:
            raise ValueError(f"Unknown tag for {self.group}: {self.tag}")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise ValueError(f"Unknown confidence level: {self.confidence}")
        if self.status not in TAG_STATUSES:
            raise ValueError(f"Unknown tag status: {self.status}")
        if self.classifier not in CLASSIFIERS:
            raise ValueError(f"Unknown classifier: {self.classifier}")
        object.__setattr__(self, "tag", canonical)
        object.__setattr__(self, "evidence_text", self.evidence_text.strip())
        object.__setattr__(self, "source_url", self.source_url.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "group": self.group,
            "tag": self.tag,
            "confidence": self.confidence,
            "status": self.status,
            "evidence_text": self.evidence_text,
            "source_url": self.source_url,
            "classifier": self.classifier,
            "reason_codes": list(self.reason_codes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClassificationTag":
        return cls(
            group=str(payload.get("group") or ""),
            tag=str(payload.get("tag") or ""),
            confidence=str(payload.get("confidence") or "low"),
            status=str(payload.get("status") or "proposed"),
            evidence_text=str(payload.get("evidence_text") or ""),
            source_url=str(payload.get("source_url") or ""),
            classifier=str(payload.get("classifier") or "heuristic"),
            reason_codes=tuple(str(item) for item in payload.get("reason_codes") or []),
        )


@dataclass
class MarketClassification:
    brand_key: str
    tags: list[ClassificationTag] = field(default_factory=list)
    version: str = TAXONOMY_VERSION
    requires_human_review: bool = False

    def __post_init__(self) -> None:
        self.brand_key = self.brand_key.strip().lower()
        self.tags = _dedupe_tags(self.tags)
        if any(tag.status == "proposed" for tag in self.tags):
            self.requires_human_review = True

    @property
    def accepted_tags(self) -> list[ClassificationTag]:
        return [tag for tag in self.tags if tag.status == "accepted"]

    @property
    def proposed_tags(self) -> list[ClassificationTag]:
        return [tag for tag in self.tags if tag.status == "proposed"]

    def tags_by_group(self, *, status: str = "accepted") -> dict[str, list[str]]:
        grouped = {group: [] for group in GROUPS}
        for tag in self.tags:
            if tag.status == status:
                grouped[tag.group].append(tag.tag)
        return grouped

    @property
    def primary_category(self) -> str | None:
        accepted = self.tags_by_group(status="accepted")
        for group in ("sector_industry", "technology_capability", "business_model"):
            if accepted[group]:
                return accepted[group][0]
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "brand_key": self.brand_key,
            "requires_human_review": self.requires_human_review,
            "primary_category": self.primary_category,
            "accepted": self.tags_by_group(status="accepted"),
            "proposed": self.tags_by_group(status="proposed"),
            "tags": [tag.to_dict() for tag in self.tags],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MarketClassification":
        return cls(
            brand_key=str(payload.get("brand_key") or ""),
            version=str(payload.get("version") or TAXONOMY_VERSION),
            requires_human_review=bool(payload.get("requires_human_review")),
            tags=[
                ClassificationTag.from_dict(item)
                for item in payload.get("tags") or []
                if isinstance(item, dict)
            ],
        )


def _dedupe_tags(tags: list[ClassificationTag]) -> list[ClassificationTag]:
    seen: set[tuple[str, str, str]] = set()
    out: list[ClassificationTag] = []
    for tag in tags:
        key = (tag.group, tag.tag, tag.status)
        if key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out
