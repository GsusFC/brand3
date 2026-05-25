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


MAX_PUBLIC_MENTIONS = 8
MAX_FALLBACK_LINES = 80
MAX_FALLBACK_MARKDOWN_CHARS = 8000
MIN_USABLE_QUOTE_LENGTH = 6
SOURCE_WEB = "web"
SOURCE_VISUAL_SIGNATURE = "visual_signature"
OWNED_EVIDENCE_SOURCE_TYPES = {"owned", "social"}
UNUSABLE_QUOTE_METADATA_MARKERS = (
    "; evidence=",
    "source_type=",
    "dimension=",
    "feature=",
)
UNUSABLE_QUOTE_CONTENT_MARKERS = (
    "/news/",
    "graphql api",
    "product roadmap",
    "__next_data__",
)


@dataclass
class RawInputContext:
    sources: list[str]
    fallback_markdown: str = ""
    visual_semantics: dict[str, Any] = field(
        default_factory=lambda: {"status": "not_detected", "data": {}}
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
        evidence_quality = _evidence_quality_summary(
            interpreter_text=self.interpreter_text,
            raw_input_count=self.raw_input_count,
            group_counts=strategic_summary.get("group_counts") or {},
            source_counts=strategic_summary.get("source_counts") or {},
            visual_semantics=self.visual_semantics,
        )
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
            "evidence_quality": evidence_quality,
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


KEY_STRATEGIC_GROUPS = ("product_offer", "audience", "outcome")
OWNED_STRATEGIC_SOURCE_TYPES = ("owned_raw", "owned", "social")


def _evidence_quality_summary(
    *,
    interpreter_text: str,
    raw_input_count: int,
    group_counts: dict[str, Any],
    source_counts: dict[str, Any],
    visual_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Summarize whether the canonical packet is useful for downstream lenses."""
    normalized_group_counts = {
        str(key): int(value or 0) for key, value in group_counts.items()
    }
    missing_key_groups = [
        group for group in KEY_STRATEGIC_GROUPS if not normalized_group_counts.get(group)
    ]
    usable_group_count = len(
        [count for count in normalized_group_counts.values() if count > 0]
    )
    owned_source_count = sum(
        int(source_counts.get(source_type) or 0)
        for source_type in OWNED_STRATEGIC_SOURCE_TYPES
    )
    visual_detected = visual_semantics.get("status") == "detected"

    reasons: list[str] = []
    if not interpreter_text.strip():
        reasons.append("no_interpreter_text")
    if raw_input_count <= 0:
        reasons.append("no_raw_inputs")
    if usable_group_count <= 0:
        reasons.append("no_strategic_groups")
    if not normalized_group_counts.get("product_offer"):
        reasons.append("no_product_offer")
    if not normalized_group_counts.get("audience"):
        reasons.append("no_audience")
    if not normalized_group_counts.get("outcome"):
        reasons.append("no_outcome")
    if owned_source_count <= 0:
        reasons.append("no_owned_evidence")

    if "no_interpreter_text" in reasons or "no_strategic_groups" in reasons:
        status = "insufficient"
    elif not normalized_group_counts.get("product_offer"):
        status = "weak"
    elif (
        all(group not in missing_key_groups for group in KEY_STRATEGIC_GROUPS)
        and owned_source_count > 0
    ):
        status = "strong"
    elif normalized_group_counts.get("product_offer") and (
        normalized_group_counts.get("audience") or normalized_group_counts.get("outcome")
    ):
        status = "usable"
    else:
        status = "weak"

    return {
        "status": status,
        "reasons": reasons,
        "key_groups": list(KEY_STRATEGIC_GROUPS),
        "missing_key_groups": missing_key_groups,
        "usable_group_count": usable_group_count,
        "owned_source_count": owned_source_count,
        "visual_semantics_detected": visual_detected,
    }


def build_canonical_brand_evidence(snapshot: dict[str, Any]) -> CanonicalBrandEvidence:
    """Build the shared evidence bundle from a persisted Brand Audit snapshot."""
    run = snapshot.get("run") or {}
    strategic_packet = build_strategic_evidence_packet(snapshot)
    evidences = collect_evidences(snapshot)
    raw_inputs = snapshot.get("raw_inputs") or []
    audit = run.get("audit") or {}
    data_quality = audit.get("data_quality") or run.get("data_quality")
    raw_input_context = _raw_input_context(raw_inputs)

    interpreter_text = strategic_packet.to_interpreter_text() or _fallback_evidence_text(
        evidences, raw_input_context.fallback_markdown
    )
    mentions = _public_mentions(strategic_packet)

    return CanonicalBrandEvidence(
        brand_name=str(run.get("brand_name") or "Unknown Brand"),
        url=str(run.get("url") or "manual"),
        run_id=run.get("id"),
        strategic_packet=strategic_packet,
        interpreter_text=interpreter_text,
        visual_semantics=raw_input_context.visual_semantics,
        public_mentions=mentions,
        raw_input_sources=raw_input_context.sources,
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
            if len(mentions) >= MAX_PUBLIC_MENTIONS:
                return mentions
    return mentions


def _raw_input_context(raw_inputs: list[dict[str, Any]]) -> RawInputContext:
    sources = sorted(
        {str(item.get("source")) for item in raw_inputs if item.get("source")}
    )
    fallback_markdown = ""
    visual_semantics: dict[str, Any] = {"status": "not_detected", "data": {}}

    for raw_input in reversed(raw_inputs):
        source = raw_input.get("source")
        payload = raw_input.get("payload") or {}

        if source == SOURCE_WEB and not fallback_markdown:
            fallback_markdown = str(
                payload.get("markdown_content") or payload.get("content") or ""
            )

        if (
            source == SOURCE_VISUAL_SIGNATURE
            and visual_semantics["status"] == "not_detected"
        ):
            semantics = payload.get("semantics")
            if semantics:
                visual_semantics = {"status": "detected", "data": semantics}
                continue
            signature = payload.get("signature") or {}
            if isinstance(signature, dict) and signature.get("semantics"):
                visual_semantics = {
                    "status": "detected",
                    "data": signature["semantics"],
                }

    return RawInputContext(
        sources=sources,
        fallback_markdown=fallback_markdown[:MAX_FALLBACK_MARKDOWN_CHARS],
        visual_semantics=visual_semantics,
    )


def _fallback_evidence_text(evidences: list[Any], fallback_markdown: str) -> str:
    preferred = [
        ev for ev in evidences if str(ev.source_type) in OWNED_EVIDENCE_SOURCE_TYPES
    ]
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
        if len(lines) >= MAX_FALLBACK_LINES:
            break

    if lines:
        return "\n".join(lines)
    return fallback_markdown


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
    if len(value) < MIN_USABLE_QUOTE_LENGTH:
        return True
    if any(marker in low for marker in UNUSABLE_QUOTE_METADATA_MARKERS):
        return True
    if any(marker in low for marker in UNUSABLE_QUOTE_CONTENT_MARKERS):
        return True
    return False
