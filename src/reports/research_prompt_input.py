"""Compact BrandResearchPack input for feature-level LLM prompts.

Brand Audit feature extractors should not feed raw, early-page markdown to the
LLM when a structured research pack is available. This module keeps that prompt
input contract small, deterministic, and reusable across dimensions.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


DEFAULT_MAX_CHARS = 6000


def research_pack_prompt_input(
    research_pack: Any,
    *,
    feature: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """Return a compact evidence-first prompt input for one feature.

    The output is plain text by design because the existing LLMAnalyzer methods
    accept a text block. It preserves source labels and evidence gaps so prompts
    can distinguish observed evidence from missing evidence.
    """

    pack = _pack_dict(research_pack)
    if not pack:
        return ""

    sections: list[str] = [
        "Structured Brand Research Pack",
        f"Feature target: {feature}",
        "",
        "Global evidence rules:",
        "- Use only the included evidence below.",
        "- Treat owned claims as self-declarations, not external validation.",
        "- Treat press/founder/proof evidence as context unless the feature explicitly asks for external perception.",
        "- Do not use rejected noise as support.",
        "- If evidence is thin or missing, return an unclear/low-confidence reading.",
        "- Prefer a conservative verdict over a polished but under-evidenced interpretation.",
        "",
    ]
    sections.extend(_feature_rules(feature))

    identity = _dict(pack.get("resolved_entity"))
    sections.extend(
        [
            "Entity:",
            f"- resolved_entity: {_str(identity.get('resolved_entity') or pack.get('resolved_entity'))}",
            f"- entity_type: {_str(pack.get('entity_type'))}",
            f"- parent_brand: {_str(pack.get('parent_brand'))}",
            f"- canonical_url: {_str(identity.get('canonical_url') or pack.get('input_url'))}",
            "",
            "Core evidence:",
            f"- company_summary: {_str(pack.get('company_summary'))}",
            f"- product_summary: {_str(pack.get('product_summary'))}",
            f"- category: {_str(pack.get('category'))}",
            f"- audience: {_str(pack.get('audience'))}",
            f"- offer: {_str(pack.get('offer'))}",
            f"- outcome: {_str(pack.get('outcome'))}",
            f"- declared_mission: {_str(pack.get('declared_mission'))}",
            f"- future_direction: {_str(pack.get('future_direction'))}",
            f"- tone_of_voice: {_str(pack.get('tone_of_voice'))}",
            "",
        ]
    )

    sections.append("Signal lists:")
    for key in (
        "personality_signals",
        "visual_or_conceptual_signals",
        "values_signals",
        "attributes_signals",
    ):
        values = _str_list(pack.get(key), limit=8)
        sections.append(f"- {key}: {', '.join(values) if values else '-'}")
    sections.append("")

    sections.extend(_evidence_section("Proof points", pack.get("proof_points"), limit=6))
    sections.extend(_evidence_section("Founder or press context", pack.get("founder_or_press_context"), limit=4))
    sections.extend(_evidence_section("Rejected noise", pack.get("noise_rejected"), limit=6))

    gaps = _str_list(pack.get("evidence_gaps"), limit=8)
    notes = _str_list(pack.get("confidence_notes"), limit=8)
    if gaps:
        sections.extend(["Evidence gaps:", *[f"- {item}" for item in gaps], ""])
    if notes:
        sections.extend(["Confidence notes:", *[f"- {item}" for item in notes], ""])

    text = "\n".join(sections).strip()
    return text[:max_chars]


def _feature_rules(feature: str) -> list[str]:
    rules = {
        "positioning_clarity": [
            "Feature-specific rules:",
            "- Clear positioning requires enough owned/self evidence to sustain category, audience, offer, and differentiator.",
            "- Press, funding, customer proof, or category descriptions cannot compensate for thin owned positioning.",
            "",
        ],
        "uniqueness": [
            "Feature-specific rules:",
            "- Score uniqueness from ownable language, repeated vocabulary, or distinctive strategic framing.",
            "- A specific category is not enough; penalize language that competitors could copy unchanged.",
            "",
        ],
        "messaging_consistency": [
            "Feature-specific rules:",
            "- Compare brand self-description against independent third-party mentions only.",
            "- If independent mentions are absent or weak, the correct verdict is unclear, not aligned.",
            "",
        ],
        "tone_consistency": [
            "Feature-specific rules:",
            "- Tone alignment requires evidence from both brand-side language and independent mentions.",
            "- If third-party tone evidence is absent, use a conservative gap signal.",
            "",
        ],
    }
    return rules.get(feature, [])


def _pack_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        try:
            data = value.to_dict()
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    if is_dataclass(value):
        data = asdict(value)
        return data if isinstance(data, dict) else {}
    return {}


def _evidence_section(title: str, raw_items: Any, *, limit: int) -> list[str]:
    items = raw_items if isinstance(raw_items, list) else []
    out = [f"{title}:"]
    if not items:
        return out + ["- -", ""]
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        text = _str(item.get("text"))
        if not text:
            continue
        meta = []
        for key in ("kind", "source_type", "source_label", "surface_role", "entity_scope", "confidence"):
            value = _str(item.get(key))
            if value:
                meta.append(f"{key}={value}")
        url = _str(item.get("source_url"))
        suffix = f" ({'; '.join(meta)})" if meta else ""
        out.append(f"- {text}{suffix}")
        if url:
            out.append(f"  source_url: {url}")
    if len(out) == 1:
        out.append("- -")
    out.append("")
    return out


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str(value: Any) -> str:
    return " ".join(str(value or "").split())


def _str_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _str(item)
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out
