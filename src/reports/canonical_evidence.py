"""Canonical public evidence bundle for downstream Brand3 interpreters.

Brand Audit owns acquisition. This module adapts a persisted audit snapshot into
one reusable evidence bundle so Magnetism, Reverse Engineering, and future TLDR
interpreters read the same public evidence instead of scraping or selecting their
own independent inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.reports.derivation import collect_evidences
from src.reports.strategic_evidence_packet import (
    StrategicEvidencePacket,
    build_strategic_evidence_packet,
)


@dataclass
class CanonicalBrandEvidence:
    """Shared evidence view derived from a Brand Audit run snapshot."""

    brand_name: str
    url: str
    run_id: int | None
    strategic_packet: StrategicEvidencePacket
    interpreter_text: str
    visual_semantics: dict[str, Any]
    public_mentions: list[str] = field(default_factory=list)
    raw_input_sources: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    data_quality: Any = None
    derived_evidence_count: int = 0
    raw_input_count: int = 0
    evidence_item_count: int = 0
    feature_count: int = 0

    def to_summary(self) -> dict[str, Any]:
        strategic_summary = self.strategic_packet.to_summary()
        return {
            "source": "brand_audit_snapshot",
            "source_label": "Canonical Brand Audit evidence",
            "evidence_basis": "Shared Brand Audit snapshot reused by Brand3 downstream lenses.",
            "run_id": self.run_id,
            "raw_input_count": self.raw_input_count,
            "evidence_item_count": self.evidence_item_count,
            "derived_evidence_count": self.derived_evidence_count,
            "feature_count": self.feature_count,
            "sources": self.raw_input_sources,
            "data_quality": self.data_quality,
            "strategic_group_counts": strategic_summary.get("group_counts"),
            "strategic_source_counts": strategic_summary.get("source_counts"),
            "strategic_rejected_count": strategic_summary.get("rejected_count"),
            "strategic_warnings": strategic_summary.get("warnings"),
            "value_policy": (
                "Brand Audit owns collection; downstream tools only interpret "
                "this shared evidence bundle."
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "brand_name": self.brand_name,
            "url": self.url,
            "interpreter_text": self.interpreter_text,
            "public_mentions": self.public_mentions,
            "visual_semantics": self.visual_semantics,
            "limitations": self.limitations,
            "strategic_packet": self.strategic_packet.to_dict(),
        }


def build_canonical_brand_evidence(snapshot: dict[str, Any]) -> CanonicalBrandEvidence:
    """Build the shared evidence bundle from a persisted Brand Audit snapshot."""
    run = snapshot.get("run") or {}
    strategic_packet = build_strategic_evidence_packet(snapshot)
    evidences = collect_evidences(snapshot)
    raw_inputs = snapshot.get("raw_inputs") or []
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")

    interpreter_text = strategic_packet.to_interpreter_text() or _fallback_evidence_text(
        snapshot
    )
    mentions = _public_mentions(strategic_packet)

    return CanonicalBrandEvidence(
        brand_name=str(run.get("brand_name") or "Unknown Brand"),
        url=str(run.get("url") or "manual"),
        run_id=run.get("id"),
        strategic_packet=strategic_packet,
        interpreter_text=interpreter_text,
        visual_semantics=_visual_semantics_from_snapshot(snapshot),
        public_mentions=mentions,
        raw_input_sources=sorted(
            {str(item.get("source")) for item in raw_inputs if item.get("source")}
        ),
        limitations=_snapshot_limitations(snapshot),
        data_quality=data_quality,
        derived_evidence_count=len(evidences),
        raw_input_count=len(raw_inputs),
        evidence_item_count=len(snapshot.get("evidence_items") or []),
        feature_count=len(snapshot.get("features") or []),
    )


def _public_mentions(strategic_packet: StrategicEvidencePacket) -> list[str]:
    mentions: list[str] = []
    seen: set[str] = set()
    for group in ("proof_points", "third_party_context"):
        for line in strategic_packet.groups.get(group, []):
            text = line.text.strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                mentions.append(text)
            if len(mentions) >= 8:
                return mentions
    return mentions


def _fallback_evidence_text(snapshot: dict[str, Any]) -> str:
    evidences = collect_evidences(snapshot)
    preferred = [ev for ev in evidences if str(ev.source_type) in {"owned", "social"}]
    evidence_source = preferred or evidences

    lines: list[str] = []
    seen: set[str] = set()
    for ev in evidence_source:
        quote = _clean_evidence_phrase(str(ev.quote or ""))
        if not quote or _is_unusable_audit_quote(quote):
            continue
        key = quote.lower()
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {quote}")
        if len(lines) >= 80:
            break

    if lines:
        return "\n".join(lines)

    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") != "web":
            continue
        payload = raw_input.get("payload") or {}
        markdown = payload.get("markdown_content") or payload.get("content") or ""
        if markdown:
            return str(markdown)[:8000]
    return ""


def _visual_semantics_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    for raw_input in reversed(snapshot.get("raw_inputs") or []):
        if raw_input.get("source") != "visual_signature":
            continue
        payload = raw_input.get("payload") or {}
        semantics = payload.get("semantics")
        if semantics:
            return {"status": "detected", "data": semantics}
        signature = payload.get("signature") or {}
        if isinstance(signature, dict) and signature.get("semantics"):
            return {"status": "detected", "data": signature["semantics"]}
    return {"status": "not_detected", "data": {}}


def _snapshot_limitations(snapshot: dict[str, Any]) -> list[str]:
    limitations: list[str] = []
    run = snapshot.get("run") or {}
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    if data_quality:
        limitations.append(f"Brand Audit data quality: {data_quality}")
    if not snapshot.get("evidence_items") and not snapshot.get("features"):
        limitations.append("Brand Audit snapshot has no persisted feature evidence.")
    return limitations


def _clean_evidence_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip(" -|•*\t")
    return text.strip()


def _is_unusable_audit_quote(value: str) -> bool:
    low = value.lower().strip()
    if low.startswith(("http://", "https://")):
        return True
    if len(value) < 6:
        return True
    if any(
        marker in low
        for marker in ("; evidence=", "source_type=", "dimension=", "feature=")
    ):
        return True
    if any(marker in low for marker in ("/news/", "graphql api", "product roadmap", "__next_data__")):
        return True
    return False
