"""LLM-assisted market classification proposals.

The model is only allowed to choose tags from Brand3's controlled taxonomy.
Outputs are reviewable proposals; accepted tags remain a human decision.
"""

from __future__ import annotations

import json
from typing import Any

from src.classification.market_taxonomy import GROUPS, TAXONOMY, canonical_tag
from src.classification.schemas import ClassificationTag, MarketClassification
from src.config import (
    BRAND3_EVIDENCE_LLM_MODEL,
    BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
)
from src.features.llm_analyzer import LLMAnalyzer
from src.research.evidence_semantic_llm import _call_structured_json


def market_llm_response_schema() -> dict[str, Any]:
    group_enum = list(GROUPS)
    tag_enum = sorted(
        {definition.tag for definitions in TAXONOMY.values() for definition in definitions}
    )
    item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "group",
            "tag",
            "confidence",
            "evidence_text",
            "source_url",
            "reason_codes",
        ],
        "properties": {
            "group": {"type": "string", "enum": group_enum},
            "tag": {"type": "string", "enum": tag_enum},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence_text": {"type": "string"},
            "source_url": {"type": "string"},
            "reason_codes": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 4,
            },
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": item_schema,
                "maxItems": 12,
            }
        },
    }


def classify_market_llm(
    *,
    brand_key: str,
    domain: str,
    evidence: list[dict[str, str]],
    llm: Any | None = None,
) -> MarketClassification | None:
    analyzer = llm if llm is not None else LLMAnalyzer(model=BRAND3_EVIDENCE_LLM_MODEL)
    if analyzer is None or not getattr(analyzer, "api_key", None):
        return None
    clean_evidence = _evidence_payload(evidence)
    if not clean_evidence:
        return None
    raw = _call_structured_json(
        analyzer,
        system=_system_prompt(),
        user=_user_prompt(brand_key=brand_key, domain=domain, evidence=clean_evidence),
        max_tokens=2200,
        json_schema=market_llm_response_schema(),
        schema_name="brand3_market_classification",
        timeout_seconds=BRAND3_EVIDENCE_LLM_TIMEOUT_SECONDS,
    )
    tags = _normalize_response(raw)
    if not tags:
        return None
    return MarketClassification(brand_key=brand_key, tags=tags, requires_human_review=True)


def _normalize_response(raw: Any) -> list[ClassificationTag]:
    if not isinstance(raw, dict):
        return []
    items = raw.get("items")
    if not isinstance(items, list):
        return []
    tags: list[ClassificationTag] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        group = str(item.get("group") or "")
        tag = canonical_tag(group, str(item.get("tag") or ""))
        if tag is None:
            continue
        try:
            tags.append(
                ClassificationTag(
                    group=group,
                    tag=tag,
                    confidence=str(item.get("confidence") or "low"),
                    status="proposed",
                    evidence_text=str(item.get("evidence_text") or "")[:320],
                    source_url=str(item.get("source_url") or "")[:500],
                    classifier="llm",
                    reason_codes=tuple(
                        str(code)[:80] for code in item.get("reason_codes") or []
                    ),
                )
            )
        except ValueError:
            continue
    return tags


def _evidence_payload(evidence: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for item in evidence[:30]:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text[:420],
                "source_url": str(item.get("url") or item.get("source_url") or "")[:500],
                "source_type": str(item.get("source_type") or item.get("source") or "")[:80],
            }
        )
    return out


def _system_prompt() -> str:
    return (
        "You classify a company into Brand3's controlled market taxonomy. "
        "Return JSON only. Use only tags explicitly allowed by the schema. "
        "Prefer no tag over a weak guess. These tags are context for filtering and benchmarking, not scoring."
    )


def _user_prompt(*, brand_key: str, domain: str, evidence: list[dict[str, str]]) -> str:
    taxonomy = {
        group: [
            {
                "tag": definition.tag,
                "definition": definition.definition,
                "aliases": list(definition.aliases),
            }
            for definition in definitions
        ]
        for group, definitions in TAXONOMY.items()
    }
    payload = {
        "brand_key": brand_key,
        "domain": domain,
        "taxonomy": taxonomy,
        "evidence": evidence,
        "rules": [
            "Only classify what is supported by evidence.",
            "Use high confidence only when explicitly stated.",
            "Use medium confidence when semantically clear from product description.",
            "Use low confidence for weak but plausible context.",
            "Do not infer brand quality, differentiation, or score from market tags.",
        ],
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True)
