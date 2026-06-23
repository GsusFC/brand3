"""Shared types for Brand Context Brief generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BrandContextSignal:
    text: str
    source: str
    group: str
    url: str = ""
    surface_role: str = ""
    entity_scope: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "text": self.text,
            "source": self.source,
            "group": self.group,
            "url": self.url,
            "surface_role": self.surface_role,
            "entity_scope": self.entity_scope,
        }


@dataclass(frozen=True)
class BrandContextBrief:
    version: str
    brand_name: str
    url: str
    what_it_is: BrandContextSignal | None = None
    value_proposition_signal: BrandContextSignal | None = None
    operating_mission_signal: BrandContextSignal | None = None
    future_direction_signal: BrandContextSignal | None = None
    belief_signals: list[BrandContextSignal] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "brand_name": self.brand_name,
            "url": self.url,
            "what_it_is": self.what_it_is.to_dict() if self.what_it_is else None,
            "value_proposition_signal": self.value_proposition_signal.to_dict() if self.value_proposition_signal else None,
            "operating_mission_signal": self.operating_mission_signal.to_dict() if self.operating_mission_signal else None,
            "future_direction_signal": self.future_direction_signal.to_dict() if self.future_direction_signal else None,
            "belief_signals": [signal.to_dict() for signal in self.belief_signals],
            "limitations": self.limitations,
        }
