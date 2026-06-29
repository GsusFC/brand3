"""LLM brand interpretation worker for the evidence-first SV9 Flow."""

from __future__ import annotations

import json
from typing import Any

from src.sv9_flow._utils import truthy_detected, unique_strings
from src.sv9_flow.block_detection_worker import SENSITIVE_BLOCKS, resolve_block_detection
from src.sv9_flow.block_evidence_worker import build_block_evidence_shortlists
from src.sv9_flow.contracts import BrandEvidencePack, BrandInterpretation

FLOW_INTERPRETATION_PROMPT_VERSION = "sv9-flow-brand-interpretation-v1"
_BLOCK_MAX_TOKENS = 1800

_BLOCK_KEYS = (
    "mission",
    "vision",
    "values",
    "attributes",
    "value_proposition",
    "personality",
    "brand_idea",
    "core_purpose",
    "magnetism",
)

_BLOCK_GUIDANCE: dict[str, list[str]] = {
    "brand_idea": [
        "Look for ownable language, distinctive methodology, named concepts, repeated phrases, and vocabulary that could summarize the brand's core idea.",
        "Do not infer brand_idea from visual style alone when textual differentiation evidence is weak.",
    ],
    "value_proposition": [
        "Look for who gets what concrete value: measurable business outcomes, financial value, capital, investment, speed, or operational benefit.",
        "Prefer a concrete offer statement over a broad mission statement.",
    ],
}

_BLOCK_EXAMPLES: dict[str, list[dict[str, Any]]] = {
    "brand_idea": [
        {
            "label": "positive",
            "reason": "The evidence names a repeatable idea or vocabulary the brand could own.",
            "evidence": "Acme calls its approach 'Revenue Clarity OS' across the homepage.",
            "output": {
                "detected": True,
                "content": "Revenue Clarity OS as the organizing idea for finance teams.",
                "confidence": "high",
                "evidence_refs": ["example.ref"],
                "rationale": "The named concept appears as ownable language in the evidence.",
                "limitations": [],
            },
        },
        {
            "label": "negative",
            "reason": "Visual polish alone is not a brand idea.",
            "evidence": "The screenshot is minimal, blue, and professional.",
            "output": {
                "detected": False,
                "content": "",
                "confidence": "low",
                "evidence_refs": [],
                "rationale": "The evidence describes style but not a distinctive brand idea.",
                "limitations": ["brand_idea_requires_textual_or_conceptual_evidence"],
            },
        },
    ],
    "value_proposition": [
        {
            "label": "positive",
            "reason": "The evidence states who receives what concrete benefit.",
            "evidence": "Acme helps CFOs recover 12 hours a month and defend board forecasts.",
            "output": {
                "detected": True,
                "content": "CFOs recover time and defend forecasts with clearer financial evidence.",
                "confidence": "high",
                "evidence_refs": ["example.ref"],
                "rationale": "The evidence names the audience and a concrete business outcome.",
                "limitations": [],
            },
        },
        {
            "label": "negative",
            "reason": "A broad mission claim is not enough.",
            "evidence": "Acme exists to make business better for everyone.",
            "output": {
                "detected": False,
                "content": "",
                "confidence": "low",
                "evidence_refs": [],
                "rationale": "The statement is aspirational but lacks a concrete audience and value.",
                "limitations": ["value_proposition_requires_specific_value_evidence"],
            },
        },
    ],
}

def build_brand_interpretation_with_llm(
    evidence_pack: BrandEvidencePack,
    *,
    llm: Any,
    block_evidence_shortlists: dict[str, list[str]] | None = None,
    per_block: bool = True,
) -> tuple[BrandInterpretation, dict[str, Any]]:
    """Build brand_interpretation_v1 directly from evidence.

    The returned debug payload is for harness comparison only; it is not a score.
    """

    if llm is None or not getattr(llm, "api_key", None):
        interpretation = BrandInterpretation(
            brand_name=evidence_pack.brand_name,
            url=evidence_pack.url,
            limitations=unique_strings(list(evidence_pack.limitations) + ["missing_llm_api_key"]),
        )
        return interpretation, {"status": "skipped", "reason": "missing_llm_api_key"}

    system = _system_prompt()
    shortlists = block_evidence_shortlists or build_block_evidence_shortlists(evidence_pack)
    if per_block:
        raw = _call_blocks(llm=llm, system=system, evidence_pack=evidence_pack, block_evidence_shortlists=shortlists)
    else:
        user = _user_prompt(evidence_pack, block_evidence_shortlists=shortlists)
        raw = llm._call_json(
            system,
            user,
            max_tokens=3500,
            json_schema=brand_interpretation_response_schema(),
            schema_name="sv9_flow_brand_interpretation",
            strict_schema=False,
        )
    normalized = normalize_llm_interpretation_response(
        raw,
        evidence_pack,
        block_evidence_shortlists=shortlists,
    )
    raw_payload = _coerce_response_object(raw)
    raw_blocks = raw_payload.get("blocks") if isinstance(raw_payload.get("blocks"), dict) else {}
    detected_count = sum(
        1
        for block in normalized.blocks.values()
        if isinstance(block, dict) and block.get("detected") is True
    )
    failed_blocks = [
        key
        for key in _BLOCK_KEYS
        if not isinstance(raw_blocks.get(key), dict) or not raw_blocks.get(key)
    ]
    block_failures = _block_failures(
        raw_blocks=raw_blocks,
        normalized_blocks=normalized.blocks,
        shortlists=shortlists,
    )
    debug = {
        "status": "ok" if raw_blocks and detected_count else "empty",
        "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
        "shortlist_version": "sv9-flow-block-evidence-shortlists-v1",
        "shortlisted_blocks": sorted(shortlists.keys()),
        "mode": "per_block" if per_block else "all_blocks",
        "detected_count": detected_count,
        "failed_blocks": failed_blocks,
        "block_failures": block_failures,
        "block_detection_decisions": _block_detection_decisions(
            evidence_pack=evidence_pack,
            shortlists=shortlists,
        ),
        "block_call_debug": raw_payload.get("_block_call_debug", []),
        "raw": raw,
    }
    failure_reason = getattr(llm, "last_failure_reason", None)
    if failure_reason:
        debug["failure_reason"] = failure_reason
    call_failures = getattr(llm, "call_failures", None)
    if isinstance(call_failures, list) and call_failures:
        latest = call_failures[-1]
        if isinstance(latest, dict):
            debug["failure"] = {
                "reason": latest.get("reason"),
                "error_type": latest.get("error_type"),
                "provider_status": latest.get("provider_status"),
                "response_empty": latest.get("response_empty"),
            }
    return normalized, debug


def normalize_llm_interpretation_response(
    raw: Any,
    evidence_pack: BrandEvidencePack,
    *,
    block_evidence_shortlists: dict[str, list[str]] | None = None,
) -> BrandInterpretation:
    payload = _coerce_response_object(raw)
    blocks_payload = payload.get("blocks") if isinstance(payload.get("blocks"), dict) else {}
    blocks: dict[str, dict[str, Any]] = {}
    evidence_refs: dict[str, list[str]] = {}
    limitations = list(evidence_pack.limitations)

    for key in _BLOCK_KEYS:
        block = blocks_payload.get(key)
        if not isinstance(block, dict):
            blocks[key] = {
                "detected": False,
                "content": "",
                "confidence": "low",
                "rationale": "No interpretation returned for this block.",
            }
            continue
        refs = _valid_refs(
            block.get("evidence_refs"),
            evidence_pack,
            allowed_refs=(block_evidence_shortlists or {}).get(key),
        )
        policy_refs = refs
        if key in SENSITIVE_BLOCKS and block_evidence_shortlists is not None:
            policy_refs = _valid_refs(
                block_evidence_shortlists.get(key) or [],
                evidence_pack,
                allowed_refs=block_evidence_shortlists.get(key),
            )
        detected = _detected_from_evidence_policy(key, block, policy_refs, evidence_pack)
        if truthy_detected(block) and not refs:
            limitations.append(f"{key}_dropped_missing_evidence_refs")
        elif truthy_detected(block) and block_evidence_shortlists is not None:
            raw_refs = [str(ref or "").strip() for ref in block.get("evidence_refs") or []]
            dropped = [ref for ref in raw_refs if ref and ref not in refs]
            if dropped:
                limitations.append(f"{key}_dropped_refs_outside_shortlist")
        if truthy_detected(block) and policy_refs and key in SENSITIVE_BLOCKS and not detected:
            decision = resolve_block_detection(key, evidence_pack, evidence_refs=policy_refs)
            if decision.limitation_code:
                limitations.append(decision.limitation_code)
        blocks[key] = {
            "detected": detected,
            "content": str(block.get("content") or "").strip()[:700],
            "confidence": _confidence(block.get("confidence")),
            "rationale": str(block.get("rationale") or "").strip()[:700],
        }
        if refs:
            evidence_refs[key] = refs

    response_limitations = payload.get("limitations")
    if isinstance(response_limitations, list):
        limitations.extend(str(item) for item in response_limitations if item)

    return BrandInterpretation(
        brand_name=evidence_pack.brand_name,
        url=evidence_pack.url,
        blocks=blocks,
        evidence_refs=evidence_refs,
        limitations=unique_strings(limitations),
    )


def brand_interpretation_response_schema() -> dict[str, Any]:
    block_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["detected", "content", "confidence", "evidence_refs", "rationale"],
        "properties": {
            "detected": {"type": "boolean"},
            "content": {"type": "string"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "rationale": {"type": "string"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["prompt_version", "blocks", "limitations"],
        "properties": {
            "prompt_version": {"type": "string"},
            "blocks": {
                "type": "object",
                "additionalProperties": False,
                "required": list(_BLOCK_KEYS),
                "properties": {key: block_schema for key in _BLOCK_KEYS},
            },
            "limitations": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        },
    }


def block_interpretation_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["detected", "content", "confidence", "evidence_refs", "rationale", "limitations"],
        "properties": {
            "detected": {"type": "boolean"},
            "content": {"type": "string"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "rationale": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        },
    }


def _call_blocks(
    *,
    llm: Any,
    system: str,
    evidence_pack: BrandEvidencePack,
    block_evidence_shortlists: dict[str, list[str]],
) -> dict[str, Any]:
    blocks: dict[str, Any] = {}
    limitations: list[str] = []
    block_call_debug: list[dict[str, Any]] = []
    for block in _BLOCK_KEYS:
        raw_block, call_debug = _call_block_json(
            llm=llm,
            system=system,
            user=_block_user_prompt(
                evidence_pack,
                block=block,
                evidence_refs=block_evidence_shortlists.get(block, []),
            ),
        )
        call_debug["block"] = block
        block_call_debug.append(call_debug)
        block_payload = _coerce_block_object(raw_block)
        blocks[block] = block_payload
        raw_limitations = block_payload.get("limitations")
        if isinstance(raw_limitations, list):
            limitations.extend(str(item) for item in raw_limitations if item)
    return {
        "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
        "blocks": blocks,
        "limitations": unique_strings(limitations),
        "_block_call_debug": block_call_debug,
    }


def _call_block_json(*, llm: Any, system: str, user: str) -> tuple[Any, dict[str, Any]]:
    raw = llm._call_json(
        system,
        user,
        max_tokens=_BLOCK_MAX_TOKENS,
        json_schema=None,
        schema_name=None,
        strict_schema=False,
    )
    if _coerce_block_object(raw):
        return raw, {
            "json_mode_empty": False,
            "text_fallback_attempted": False,
            "text_fallback_empty": None,
        }
    text_call = getattr(llm, "_call", None)
    if not callable(text_call):
        return raw, {
            "json_mode_empty": True,
            "text_fallback_attempted": False,
            "text_fallback_empty": None,
            "last_failure": _latest_failure(llm),
        }
    text_raw = text_call(system, user, max_tokens=_BLOCK_MAX_TOKENS)
    text_payload = _coerce_block_object(text_raw)
    return text_raw, {
        "json_mode_empty": True,
        "text_fallback_attempted": True,
        "text_fallback_empty": not bool(text_payload),
        "last_failure": _latest_failure(llm),
        "text_excerpt": "" if text_payload else _excerpt(text_raw, max_chars=220),
    }


def _system_prompt() -> str:
    return """You are Brand3's evidence interpreter for SV9.

Return strict JSON only. Do not score the brand. Do not invent evidence.
Every detected block must cite existing evidence_refs from the provided evidence list.
If evidence is weak, set detected=false or confidence=low.
"""


def _user_prompt(
    evidence_pack: BrandEvidencePack,
    *,
    block_evidence_shortlists: dict[str, list[str]],
) -> str:
    shortlisted_refs = {
        ref
        for refs in block_evidence_shortlists.values()
        for ref in refs
    }
    evidence = [
        {
            "ref": record.ref,
            "source": record.source,
            "type": record.evidence_type,
            "content": record.content[:500],
            "confidence": record.confidence,
            "url": record.url,
        }
        for record in evidence_pack.evidence
        if record.ref in shortlisted_refs
    ]
    payload = {
        "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
        "task": "Build brand_interpretation_v1 from evidence only.",
        "brand": {"name": evidence_pack.brand_name, "url": evidence_pack.url},
        "required_blocks": list(_BLOCK_KEYS),
        "block_evidence_shortlists": block_evidence_shortlists,
        "evidence": evidence,
        "limitations": evidence_pack.limitations,
        "output_contract": {
            "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
            "blocks": {
                key: {
                    "detected": False,
                    "content": "",
                    "confidence": "low",
                    "evidence_refs": [],
                    "rationale": "",
                }
                for key in _BLOCK_KEYS
            },
            "limitations": [],
        },
        "rules": [
            "Return one JSON object with exactly these top-level keys: prompt_version, blocks, limitations.",
            "The blocks object must include every required block key, even when detected=false.",
            "Do not create a score.",
            "Do not use outside knowledge.",
            "A detected block requires at least one evidence_ref from the evidence list.",
            "For each block, only cite refs listed in block_evidence_shortlists for that block.",
            "Prefer insufficient evidence over speculation.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _block_user_prompt(
    evidence_pack: BrandEvidencePack,
    *,
    block: str,
    evidence_refs: list[str],
) -> str:
    allowed = set(evidence_refs)
    evidence = [
        {
            "ref": record.ref,
            "source": record.source,
            "type": record.evidence_type,
            "content": record.content[:700],
            "confidence": record.confidence,
            "url": record.url,
        }
        for record in evidence_pack.evidence
        if record.ref in allowed
    ]
    payload = {
        "prompt_version": FLOW_INTERPRETATION_PROMPT_VERSION,
        "task": f"Draft exactly one brand_interpretation_v1 block: {block}.",
        "brand": {"name": evidence_pack.brand_name, "url": evidence_pack.url},
        "block": block,
        "block_guidance": _BLOCK_GUIDANCE.get(block, []),
        "allowed_evidence_refs": evidence_refs,
        "evidence": evidence,
        "examples": _BLOCK_EXAMPLES.get(block, []),
        "required_json": {
            "detected": "boolean",
            "content": "string, max 280 characters, empty when detected=false",
            "confidence": "low|medium|high",
            "evidence_refs": "array of allowed_evidence_refs, empty when detected=false",
            "rationale": "string, max 220 characters",
            "limitations": "array of strings",
        },
        "rules": [
            "Return only one valid JSON object with the required_json keys.",
            "Do not create a score.",
            "Do not use outside knowledge.",
            "Only cite refs from allowed_evidence_refs.",
            "If the allowed evidence is weak or missing, set detected=false.",
            "Keep content and rationale concise so the JSON completes.",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _block_failures(
    *,
    raw_blocks: dict[str, Any],
    normalized_blocks: dict[str, dict[str, Any]],
    shortlists: dict[str, list[str]],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for block in _BLOCK_KEYS:
        raw_block = raw_blocks.get(block)
        normalized = normalized_blocks.get(block) or {}
        if not isinstance(raw_block, dict) or not raw_block:
            reason = "empty_or_parse_failed"
        elif raw_block.get("detected") is True and not normalized.get("detected"):
            reason = "dropped_by_normalization"
        elif normalized.get("detected") is True:
            continue
        else:
            reason = "insufficient_evidence"
        raw_refs = raw_block.get("evidence_refs") if isinstance(raw_block, dict) else None
        failures.append(
            {
                "block": block,
                "reason": reason,
                "refs_count": len(shortlists.get(block, [])),
                "raw_refs_count": len(raw_refs) if isinstance(raw_refs, list) else 0,
                "raw_empty": not bool(raw_block),
            }
        )
    return failures


def _block_detection_decisions(
    *,
    evidence_pack: BrandEvidencePack,
    shortlists: dict[str, list[str]],
) -> list[dict[str, object]]:
    decisions: list[dict[str, object]] = []
    for block in sorted(SENSITIVE_BLOCKS):
        refs = _valid_refs(shortlists.get(block) or [], evidence_pack, allowed_refs=shortlists.get(block))
        decisions.append(resolve_block_detection(block, evidence_pack, evidence_refs=refs).to_dict())
    return decisions


def _coerce_response_object(raw: Any) -> dict[str, Any]:
    value = raw
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                extracted = _extract_json_object_text(value)
                if not extracted:
                    return {}
                try:
                    value = json.loads(extracted)
                except json.JSONDecodeError:
                    return {}
            continue
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            continue
        if isinstance(value, dict):
            if isinstance(value.get("blocks"), dict):
                return value
            for key in ("payload", "content", "output", "response", "result", "data"):
                nested = value.get(key)
                if isinstance(nested, (dict, list, str)):
                    value = nested
                    break
            else:
                return value
            continue
        return {}
    return value if isinstance(value, dict) else {}


def _coerce_block_object(raw: Any) -> dict[str, Any]:
    value = raw
    for _ in range(4):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                extracted = _extract_json_object_text(value)
                if not extracted:
                    return {}
                try:
                    value = json.loads(extracted)
                except json.JSONDecodeError:
                    return {}
            continue
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
            continue
        if isinstance(value, dict):
            for key in ("payload", "content", "output", "response", "result", "data"):
                nested = value.get(key)
                if isinstance(nested, (dict, list, str)) and not {"detected", "evidence_refs"} & set(value):
                    value = nested
                    break
            else:
                return value
            continue
        return {}
    return value if isinstance(value, dict) else {}


def _extract_json_object_text(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return ""
    return text[start : end + 1]


def _latest_failure(llm: Any) -> dict[str, Any] | None:
    failures = getattr(llm, "call_failures", None)
    if not isinstance(failures, list) or not failures:
        return None
    latest = failures[-1]
    if not isinstance(latest, dict):
        return None
    return {
        "reason": latest.get("reason"),
        "error_type": latest.get("error_type"),
        "response_empty": latest.get("response_empty"),
        "json_parse_error": latest.get("json_parse_error"),
    }


def _excerpt(value: Any, *, max_chars: int) -> str:
    text = "" if value is None else str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 1]}…"


def _valid_refs(
    raw_refs: Any,
    evidence_pack: BrandEvidencePack,
    *,
    allowed_refs: list[str] | None = None,
) -> list[str]:
    allowed = set(allowed_refs) if allowed_refs is not None else {record.ref for record in evidence_pack.evidence}
    if not isinstance(raw_refs, list):
        return []
    refs = []
    for ref in raw_refs:
        value = str(ref or "").strip()
        if value and value in allowed and value not in refs:
            refs.append(value)
    return refs[:5]


def _detected_from_evidence_policy(
    key: str,
    block: dict[str, Any],
    refs: list[str],
    evidence_pack: BrandEvidencePack,
) -> bool:
    if not truthy_detected(block) or not refs:
        return False
    return resolve_block_detection(key, evidence_pack, evidence_refs=refs).supports_detection


def _confidence(value: Any) -> str:
    candidate = str(value or "").lower()
    return candidate if candidate in {"low", "medium", "high"} else "medium"
