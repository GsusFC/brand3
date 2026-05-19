"""Lab-only candidate integration helpers for Evidence Packet prompt input.

This module is offline/lab orchestration glue. It does not modify runtime
generation behavior and does not write persisted report payloads.
"""

from __future__ import annotations

import json
from typing import Any


INCLUDED_STATUSES = {"ready", "thin"}

LAB_SYSTEM_PROMPT = """You are a strict evidence analyst for a Brand3 validation batch.
Return JSON only. Do not write report prose. Do not recommend strategy.
Do not infer leadership, advantage, superiority, moat, traction, adoption,
customer preference, intent, roadmap, or planning direction.

Use only included evidence. If evidence is narrow, produce narrow findings."""

LAB_FINDINGS_SCHEMA = {
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

DEFAULT_PROMPT_RULES = [
    "Do not include typical_decision.",
    "Do not generate strategic choices.",
    "Do not recommend actions.",
    "Do not infer leadership, advantage, superiority, moat, traction, adoption, customer preference, intent, or roadmap.",
    "Use only included evidence URLs.",
    "Return JSON only.",
]

DEFAULT_RISKY_TERMS = (
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


def build_lab_request(
    *,
    case_id: str,
    dimension: str,
    intent: str,
    model: str,
    task_label: str,
    readiness_status: str,
    prompt_constraints: list[str] | None,
    evidence: list[dict[str, Any]] | None,
    max_tokens: int = 1800,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Build one lab request or a skip record based on readiness gates."""
    status = str(readiness_status or "abstain")
    if status not in INCLUDED_STATUSES:
        return None, {
            "case_id": case_id,
            "dimension": dimension,
            "status": status,
            "intent": intent,
            "reason": "status_not_executable_for_lab_call",
        }

    included_evidence = [
        {
            "text": str(item.get("text") or "").strip(),
            "url": str(item.get("url") or "").strip(),
            "source_class": str(item.get("source_class") or ""),
            "limits": str(item.get("limits") or ""),
        }
        for item in (evidence or [])
        if str(item.get("text") or "").strip()
    ]
    allowed_urls = sorted({item["url"] for item in included_evidence if item["url"]})
    prompt_rules = list(DEFAULT_PROMPT_RULES)
    if dimension == "diferenciacion":
        prompt_rules.append("For competitor comparison evidence, only discuss relative positioning distance.")
    prompt_rules.extend(str(rule) for rule in (prompt_constraints or []) if str(rule).strip())

    user_payload = {
        "task": task_label,
        "schema": LAB_FINDINGS_SCHEMA,
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
            "source": "evidence_packet_prompt_input_candidate",
            "model": model,
            "system": LAB_SYSTEM_PROMPT,
            "user": json.dumps(user_payload, indent=2, ensure_ascii=False),
            "max_tokens": max_tokens,
            "allowed_evidence_urls": allowed_urls,
            "included_evidence_count": len(included_evidence),
        },
        None,
    )


def summarize_lab_response(data: Any, allowed_urls: list[str], dimension: str) -> dict[str, Any]:
    """Summarize one lab response with policy checks."""
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        findings = []
    text = json.dumps(findings, ensure_ascii=False).lower()
    text_without_limits = json.dumps(
        [{k: v for k, v in item.items() if k != "limits"} for item in findings if isinstance(item, dict)],
        ensure_ascii=False,
    ).lower()
    risky_terms = [term for term in DEFAULT_RISKY_TERMS if term in text]
    risky_terms_outside_limits = risky_terms_outside_limits_for_dimension(
        text_without_limits=text_without_limits,
        risky_terms=list(DEFAULT_RISKY_TERMS),
        dimension=dimension,
    )

    urls_used: list[str] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        urls = item.get("evidence_urls")
        if isinstance(urls, list):
            urls_used.extend(str(url) for url in urls if isinstance(url, str))
    urls_used = sorted(set(urls_used))
    url_validity = all(url in allowed_urls for url in urls_used) if urls_used else True

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
    }


def risky_terms_outside_limits_for_dimension(
    *,
    text_without_limits: str,
    risky_terms: list[str],
    dimension: str,
) -> list[str]:
    """Dimension-aware risky-term detector outside the `limits` field."""
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
