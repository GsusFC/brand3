"""Compare legacy snapshot packs with EvidenceGraph-backed packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.brand_research_pack import build_brand_research_pack_from_snapshot
from src.research.evidence_graph import build_evidence_graph_from_snapshot
from src.research.research_pack_builder import build_brand_research_pack_from_graph


TEXT_FIELDS = (
    "company_summary",
    "product_summary",
    "audience",
    "offer",
    "outcome",
    "category",
    "declared_purpose",
    "declared_mission",
    "future_direction",
    "tone_of_voice",
)

LIST_FIELDS = (
    "personality_signals",
    "visual_or_conceptual_signals",
    "values_signals",
    "attributes_signals",
    "evidence_gaps",
    "confidence_notes",
)

EVIDENCE_FIELDS = (
    "proof_points",
    "founder_or_press_context",
    "competitive_context",
    "noise_rejected",
)


@dataclass(slots=True)
class FieldComparison:
    field: str
    legacy_empty: bool
    graph_empty: bool
    changed: bool
    legacy_preview: str = ""
    graph_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "legacy_empty": self.legacy_empty,
            "graph_empty": self.graph_empty,
            "changed": self.changed,
            "legacy_preview": self.legacy_preview,
            "graph_preview": self.graph_preview,
        }


@dataclass(slots=True)
class PackComparison:
    run_id: int | None
    brand_name: str
    url: str
    legacy_entity_type: str
    graph_entity_type: str
    legacy_parent_brand: str
    graph_parent_brand: str
    graph_summary: dict[str, Any]
    fields: list[FieldComparison] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "brand_name": self.brand_name,
            "url": self.url,
            "legacy_entity_type": self.legacy_entity_type,
            "graph_entity_type": self.graph_entity_type,
            "legacy_parent_brand": self.legacy_parent_brand,
            "graph_parent_brand": self.graph_parent_brand,
            "graph_summary": self.graph_summary,
            "fields": [field.to_dict() for field in self.fields],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        gained = [item.field for item in self.fields if item.legacy_empty and not item.graph_empty]
        lost = [item.field for item in self.fields if not item.legacy_empty and item.graph_empty]
        changed = [item.field for item in self.fields if item.changed]
        return {
            "gained_fields": gained,
            "lost_fields": lost,
            "changed_fields": changed,
            "gained_count": len(gained),
            "lost_count": len(lost),
            "changed_count": len(changed),
            "entity_type_changed": self.legacy_entity_type != self.graph_entity_type,
            "parent_brand_changed": self.legacy_parent_brand != self.graph_parent_brand,
        }


def compare_pack_builders_from_snapshot(snapshot: dict[str, Any]) -> PackComparison:
    """Compare the current snapshot pack builder against the graph-backed builder."""

    legacy_pack = build_brand_research_pack_from_snapshot(snapshot)
    graph = build_evidence_graph_from_snapshot(snapshot)
    graph_pack = build_brand_research_pack_from_graph(graph)
    legacy = legacy_pack.to_dict()
    graph_payload = graph_pack.to_dict()
    run = snapshot.get("run") if isinstance(snapshot.get("run"), dict) else {}

    fields = [
        _compare_field(field, legacy.get(field), graph_payload.get(field))
        for field in (*TEXT_FIELDS, *LIST_FIELDS, *EVIDENCE_FIELDS)
    ]
    return PackComparison(
        run_id=_optional_int(run.get("id")),
        brand_name=str(run.get("brand_name") or ""),
        url=str(run.get("url") or ""),
        legacy_entity_type=str(legacy.get("entity_type") or ""),
        graph_entity_type=str(graph_payload.get("entity_type") or ""),
        legacy_parent_brand=str(legacy.get("parent_brand") or ""),
        graph_parent_brand=str(graph_payload.get("parent_brand") or ""),
        graph_summary=graph.summary(),
        fields=fields,
    )


def _compare_field(field: str, legacy_value: Any, graph_value: Any) -> FieldComparison:
    legacy_normalized = _normalize_value(legacy_value)
    graph_normalized = _normalize_value(graph_value)
    return FieldComparison(
        field=field,
        legacy_empty=not bool(legacy_normalized),
        graph_empty=not bool(graph_normalized),
        changed=legacy_normalized != graph_normalized,
        legacy_preview=_preview(legacy_value),
        graph_preview=_preview(graph_value),
    )


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    if isinstance(value, list):
        return "\n".join(_normalize_value(item) for item in value if _normalize_value(item))
    if isinstance(value, dict):
        return " ".join(str(value.get(key) or "") for key in sorted(value))
    return str(value).strip()


def _preview(value: Any, limit: int = 180) -> str:
    if isinstance(value, list):
        if not value:
            return ""
        parts = []
        for item in value[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("source_url") or item)[:80])
            else:
                parts.append(str(item)[:80])
        text = " | ".join(parts)
    elif isinstance(value, dict):
        text = str(value)
    else:
        text = str(value or "")
    text = " ".join(text.split())
    return text[:limit]


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
