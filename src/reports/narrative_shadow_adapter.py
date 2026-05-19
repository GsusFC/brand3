"""Lab-only narrative shadow adapter for evidence-packet prompt candidates.

This module is non-runtime orchestration glue. It consumes only candidate
prompt-input evidence and constraints and prepares a bounded findings request.
"""

from __future__ import annotations

import json
from typing import Any


SHADOW_INCLUDED_STATUSES = {"ready", "thin"}

SHADOW_SYSTEM_PROMPT = """You are a strict evidence analyst for Brand3 lab validation.
Return JSON only. Do not write report prose. Do not recommend strategy.
Do not infer leadership, advantage, superiority, moat, traction, adoption,
customer preference, intent, roadmap, or planning direction.

Use only included evidence. If evidence is narrow, produce narrow findings."""

SHADOW_FINDINGS_SCHEMA = {
    "findings": [
        {
            "title": "",
            "evidence_anchor": "",
            "observation": "",
            "bounded_interpretation": "",
            "limits": "",
            "evidence_urls": [],
        }
    ]
}

SHADOW_PROMPT_RULES = [
    "Do not include typical_decision.",
    "Do not generate strategic choices.",
    "Do not recommend actions.",
    "Do not infer leadership, advantage, superiority, moat, traction, adoption, customer preference, intent, or roadmap.",
    "Use only included evidence URLs.",
    "Return JSON only.",
]

SHADOW_RISKY_TERMS = (
    "strategy",
    "strategic",
    "recommend",
    "should",
    "must",
    "needs to",
    "leadership",
    "advantage",
    "superior",
    "moat",
    "traction",
    "adoption",
    "customer preference",
    "roadmap",
)


def build_shadow_narrative_request(
    request_row: dict[str, Any],
    *,
    model: str,
    max_tokens: int = 1800,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Build one shadow lab request or a skip record based on readiness gates."""
    case_id = str(request_row.get("case_id") or "")
    dimension = str(request_row.get("dimension") or "")
    intent = str(request_row.get("intent") or "shadow_trial_case")
    status = str(request_row.get("readiness_status") or "abstain")
    if status not in SHADOW_INCLUDED_STATUSES:
        return None, {
            "case_id": case_id,
            "dimension": dimension,
            "status": status,
            "intent": intent,
            "reason": "status_not_executable_for_shadow_call",
            "source": "narrative_shadow_adapter",
        }

    source_payload = _load_user_payload(request_row)
    source_rules = list(source_payload.get("prompt_rules") or [])
    source_evidence = list(source_payload.get("included_evidence") or [])

    included_evidence: list[dict[str, str]] = []
    for item in source_evidence:
        text = str(item.get("text") or "").strip()
        url = str(item.get("url") or "").strip()
        if not text:
            continue
        included_evidence.append(
            {
                "text": text,
                "url": url,
                "source_class": str(item.get("source_class") or ""),
                "limits": str(item.get("limits") or ""),
            }
        )
    allowed_urls = sorted({item["url"] for item in included_evidence if item["url"]})

    prompt_rules = list(SHADOW_PROMPT_RULES)
    if dimension == "diferenciacion":
        prompt_rules.append("For competitor comparison evidence, only discuss relative positioning distance.")
    prompt_rules.extend(str(rule) for rule in source_rules if str(rule).strip())
    prompt_rules = _dedupe_prompt_rules(prompt_rules)

    user_payload = {
        "task": str(source_payload.get("task") or f"Generate bounded findings for {case_id}/{dimension}."),
        "schema": SHADOW_FINDINGS_SCHEMA,
        "field_rules": {
            "title": "3-6 words. Pattern, not quality.",
            "evidence_anchor": "Quote, source, URL, or measured evidence used.",
            "observation": "Only what included evidence supports.",
            "bounded_interpretation": "Conditional interpretation only; no strategy, recommendation, or category leadership.",
            "limits": "What the evidence does not prove.",
            "evidence_urls": "Only URLs/provenance values present in included evidence.",
        },
        "prompt_rules": prompt_rules,
        "included_evidence": included_evidence,
    }

    return (
        {
            "case_id": case_id,
            "dimension": dimension,
            "intent": intent,
            "readiness_status": status,
            "source": "narrative_shadow_adapter",
            "model": model,
            "system": SHADOW_SYSTEM_PROMPT,
            "user": json.dumps(user_payload, indent=2, ensure_ascii=False),
            "max_tokens": max_tokens,
            "allowed_evidence_urls": allowed_urls,
            "included_evidence_count": len(included_evidence),
            "group_id": request_row.get("group_id"),
            "source_type": request_row.get("source_type"),
            "run_id": request_row.get("run_id"),
        },
        None,
    )


def parse_shadow_narrative_response(data: Any, allowed_urls: list[str], dimension: str) -> dict[str, Any]:
    """Summarize and validate one shadow response against gate constraints."""
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        findings = []

    text = json.dumps(findings, ensure_ascii=False).lower()
    text_without_limits = json.dumps(
        [{k: v for k, v in item.items() if k != "limits"} for item in findings if isinstance(item, dict)],
        ensure_ascii=False,
    ).lower()
    risky_terms = [term for term in SHADOW_RISKY_TERMS if term in text]
    risky_terms_outside_limits = _risky_terms_outside_limits_for_dimension(
        text_without_limits=text_without_limits,
        risky_terms=list(SHADOW_RISKY_TERMS),
        dimension=dimension,
    )

    urls_used: list[str] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        item_urls = item.get("evidence_urls")
        if isinstance(item_urls, list):
            urls_used.extend(str(url) for url in item_urls if isinstance(url, str))
    urls_used = sorted(set(urls_used))
    invalid_urls = sorted(url for url in urls_used if url not in allowed_urls)
    url_validity = len(invalid_urls) == 0

    return {
        "finding_count": len(findings),
        "titles": [str(item.get("title") or "") for item in findings if isinstance(item, dict)],
        "risky_terms_detected": risky_terms,
        "risky_terms_outside_limits": risky_terms_outside_limits,
        "limits_field_present": all(bool(str(item.get("limits") or "").strip()) for item in findings if isinstance(item, dict))
        if findings
        else False,
        "has_typical_decision": "typical_decision" in text,
        "evidence_urls_used": urls_used,
        "evidence_url_validity": url_validity,
        "invalid_evidence_urls": invalid_urls,
    }


def _load_user_payload(request_row: dict[str, Any]) -> dict[str, Any]:
    user = request_row.get("user")
    if not isinstance(user, str):
        return {}
    try:
        parsed = json.loads(user)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dedupe_prompt_rules(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in values:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _risky_terms_outside_limits_for_dimension(
    *,
    text_without_limits: str,
    risky_terms: list[str],
    dimension: str,
) -> list[str]:
    flagged = [term for term in risky_terms if term in text_without_limits]
    if "leadership" not in flagged or dimension != "vitalidad":
        return flagged
    factual_markers = (
        "leadership team",
        "leadership teams",
        "leadership expansion",
        "expanded leadership",
        "executive team",
        "executive hire",
        "appointed",
    )
    strategic_markers = (
        "market leadership",
        "category leadership",
        "industry leadership",
        "leadership position",
        "leadership over",
        "leadership in",
    )
    if any(marker in text_without_limits for marker in factual_markers) and not any(
        marker in text_without_limits for marker in strategic_markers
    ):
        return [term for term in flagged if term != "leadership"]
    return flagged
