"""Run a cost-controlled Gemini Deep Research evidence packet trial.

This script is intentionally standalone and lab-only. It does not import Brand3
collectors, scoring, prompts, report generation, rendering, or Visual Signature.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
API_REVISION = "2026-05-20"
AGENT = "deep-research-preview-04-2026"

URLS = [
    "https://builtwith.kit.com",
    "https://kit.com/",
    "https://builtwith.com/",
    "https://builtwith.com/about",
    "https://blog.builtwith.com/2026/02/25/llms-and-mcp/",
    "https://www.scamadviser.com/check-website/builtwith.kit.com",
    "https://www.joesandbox.com/analysis/1719754/0/html",
]


PROMPT = """You are preparing an evidence packet for Brand3.

Target audit surface:
- builtwith.kit.com
- URL: https://builtwith.kit.com

Use ONLY the provided URL context tool and the fixed URL set below.
Do not use open web search.
Do not generate Brand Audit findings.
Do not score.
Do not recommend strategy.
Do not write a report.

Fixed URL set:
{urls}

Return a structured evidence packet only. Prefer valid JSON and no Markdown.

Required top-level JSON shape:
{{
  "case_id": "builtwith_kit_com",
  "audited_surface": {{
    "url": "https://builtwith.kit.com",
    "entity_label": "...",
    "confidence": "high | medium | low",
    "evidence": []
  }},
  "owned_claims": [],
  "external_evidence": [],
  "related_surface_evidence": [],
  "technical_signals": [],
  "trust_or_security_signals": [],
  "entity_ambiguity": [],
  "excluded_noise": [],
  "missing_evidence": [],
  "finding_eligible_evidence": [],
  "evidence_not_eligible_for_findings": [],
  "requires_human_review": []
}}

Rules:
- Cite every evidence item with a URL from the fixed URL set.
- Mark uncertainty explicitly.
- Do not infer ownership between Kit and BuiltWith unless explicitly supported.
- Do not treat technical artifacts as brand intent.
- Do not treat visual or technical metrics as market evidence.
- Do not smooth entity ambiguity.
- If evidence is weak, mark it weak instead of making it useful.
- If a provided URL cannot be read, list it under missing_evidence or excluded_noise.
- finding_eligible_evidence should include only evidence that can safely support a Brand3 narrative finding.
- evidence_not_eligible_for_findings should include technical, weak, ambiguous, or appendix-only material.
""".format(urls="\n".join(f"- {url}" for url in URLS))


SINGLE_URL_PROMPT = """You are preparing an evidence packet for Brand3.

Target audit URL:
- https://builtwith.kit.com

Use this single URL as the starting point. You may use Google Search and URL
context, but do not use any provided seed URLs or previous Brand3 evidence.

This is an acquisition and classification task only.
Do not generate Brand Audit findings.
Do not score.
Do not recommend strategy.
Do not write report prose.
Do not do competitor, market, or broad strategy research.

Allowed research questions:
1. What is https://builtwith.kit.com?
2. Who appears to control or publish it?
3. What claims does the audited surface make?
4. What external sources, if any, corroborate or challenge those claims?
5. Are there related or similarly named surfaces?
6. Are those surfaces explicitly related, unrelated, or unresolved?
7. Which evidence is suitable for Brand Audit findings?
8. Which evidence should be excluded, treated as technical-only, or sent to appendix?

Return a structured evidence packet only. Prefer valid JSON and no Markdown.

Required top-level JSON shape:
{
  "case_id": "builtwith_kit_com_single_url",
  "audited_surface": {
    "url": "https://builtwith.kit.com",
    "entity_label": "...",
    "publisher_or_controller": {
      "value": "...",
      "confidence": "high | medium | low | unresolved",
      "evidence": []
    },
    "confidence": "high | medium | low | unresolved",
    "evidence": []
  },
  "owned_claims": [],
  "external_evidence": [],
  "related_surface_evidence": [],
  "technical_signals": [],
  "trust_or_security_signals": [],
  "entity_ambiguity": [],
  "excluded_noise": [],
  "missing_evidence": [],
  "finding_eligible_evidence": [],
  "evidence_not_eligible_for_findings": [],
  "requires_human_review": [],
  "discovered_sources": [],
  "search_queries_used": [],
  "source_quality_notes": [],
  "cost_risk_notes": []
}

Rules:
- Cite every evidence item with a URL.
- Mark uncertainty explicitly.
- Do not infer ownership unless explicitly supported.
- Do not treat similarly named domains as aliases.
- Do not treat technical artifacts as brand intent.
- Do not treat visual or technical metrics as market evidence.
- Do not smooth entity ambiguity.
- If evidence is weak, mark it weak instead of making it useful.
- If entity ownership is unresolved, say unresolved.
- Prefer exclusion over forced usefulness.
- finding_eligible_evidence should include only evidence that can safely support a Brand3 narrative finding.
- evidence_not_eligible_for_findings should include technical, weak, ambiguous, or appendix-only material.
"""


WATERMELON_PRISM_PROMPT = """You are preparing a Brand3 methodology-prism evidence packet.

Target audit URL:
- https://watermelon.sh

Use this single URL as the starting point. You may use Google Search and URL
context. Do not use seed URLs. Do not use previous Brand3 evidence. Do not use
known related domains supplied by Brand3.

This is an acquisition and classification task only.
Do not generate Brand Audit findings.
Do not score.
Do not recommend strategy.
Do not write report prose.
Do not do competitor landscape research unless it is needed only to disambiguate
the audited entity or source quality.

Core research questions:
1. What is https://watermelon.sh?
2. Who appears to control or publish the audited surface?
3. What claims does the audited surface make?
4. What external sources, if any, corroborate or challenge those claims?
5. Are there related, adjacent, or similarly named Watermelon surfaces?
6. Are those surfaces explicitly related, unrelated, or unresolved?
7. Which evidence is eligible for Brand3 narrative findings by dimension?
8. Which evidence should be excluded, treated as technical-only, trust/security
   review-only, or appendix-only?

Return a structured evidence packet only. Prefer valid JSON and no Markdown.

Required top-level JSON shape:
{
  "case_id": "watermelon",
  "target_url": "https://watermelon.sh",
  "entity_resolution": {
    "audited_surface": {
      "url": "https://watermelon.sh",
      "entity_label": "...",
      "publisher_or_controller": {
        "value": "...",
        "confidence": "high | medium | low | unresolved",
        "evidence": []
      },
      "confidence": "high | medium | low | unresolved",
      "evidence": []
    },
    "related_or_similarly_named_surfaces": [],
    "ownership_or_relation_status": "explicit | partially_supported | unresolved | contradicted",
    "requires_human_review": true
  },
  "source_inventory": [],
  "coherencia": {
    "eligible_evidence": [],
    "observation_only": [],
    "excluded_or_review_only": [],
    "evidence_gaps": []
  },
  "presencia": {
    "eligible_evidence": [],
    "observation_only": [],
    "excluded_or_review_only": [],
    "evidence_gaps": []
  },
  "percepcion": {
    "eligible_evidence": [],
    "observation_only": [],
    "excluded_or_review_only": [],
    "evidence_gaps": []
  },
  "diferenciacion": {
    "eligible_evidence": [],
    "observation_only": [],
    "excluded_or_review_only": [],
    "evidence_gaps": []
  },
  "vitalidad": {
    "eligible_evidence": [],
    "observation_only": [],
    "excluded_or_review_only": [],
    "evidence_gaps": []
  },
  "cross_dimension_evidence": [],
  "evidence_gaps": [],
  "source_quality_notes": [],
  "cost_risk_notes": [],
  "search_queries_used": [],
  "discovered_sources": []
}

Brand3 dimension meanings:
- coherencia: whether the audited surface presents a coherent brand promise,
  product identity, and entity frame.
- presencia: whether the audited entity has observable owned/public presence,
  channels, surfaces, or indexing.
- percepcion: how credible external perception, trust, reviews, listings, or
  third-party characterization affect interpretation.
- diferenciacion: what makes the audited offer distinct, and whether that
  distinction is supported by evidence rather than only owned claims.
- vitalidad: whether there is evidence of recent activity, momentum, product
  development, community activity, or market movement tied to the audited entity.

Evidence item shape:
{
  "claim": "...",
  "source_url": "...",
  "source_type": "audited_surface | owned_claim | external_evidence | related_surface | technical_signal | trust_or_security_signal | marketplace_or_listing | developer_surface | search_result | unknown",
  "dimension_relevance": ["coherencia", "presencia", "percepcion", "diferenciacion", "vitalidad"],
  "finding_eligibility": "eligible | observation_only | appendix_only | technical_only | trust_security_review_only | requires_human_review | excluded_noise",
  "confidence": "high | medium | low | unresolved",
  "requires_human_review": true,
  "notes": "..."
}

Rules:
- Cite every evidence item with a URL.
- Separate owned claims from external validation.
- Separate technical signals from narrative evidence.
- Separate the audited surface from related surfaces.
- Do not infer ownership from similar names.
- Do not infer ownership from GitHub, Product Hunt, marketplace, directory, or
  repository evidence unless explicit evidence supports the relationship.
- Do not infer roadmap, traction, growth, market adoption, or ecosystem strategy
  unless directly supported.
- Do not treat technical artifacts as brand intent.
- Do not treat visual or technical metrics as market evidence.
- Do not smooth entity ambiguity.
- Mark weak evidence as weak instead of making it useful.
- Mark missing evidence explicitly.
- Mark human review when entity relation is not explicit.
- Classify finding eligibility conservatively.
- Prefer exclusion over forced usefulness.
- If a source is about a different Watermelon entity, put it under
  excluded_or_review_only or entity ambiguity, not eligible evidence.
"""


def paths_for_mode(mode: str) -> dict[str, Path]:
    output_slug = {
        "single-url-search": "builtwith_kit_com_single_url",
        "watermelon-prism": "watermelon_prism",
    }.get(mode, "builtwith_kit_com")
    output_dir = ROOT / "examples" / "reports" / "deep_research_trial" / output_slug
    return {
        "output_dir": output_dir,
        "request": output_dir / "request.json",
        "raw": output_dir / "raw_interaction.json",
        "packet": output_dir / "evidence_packet.json",
        "cost": output_dir / "cost_observation.json",
        "notes": output_dir / "trial_notes.md",
    }


def case_id_for_mode(mode: str) -> str:
    return {
        "single-url-search": "builtwith_kit_com_single_url",
        "watermelon-prism": "watermelon",
    }.get(mode, "builtwith_kit_com")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_env_api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("BRAND3_LLM_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()


def build_request(mode: str) -> dict[str, Any]:
    if mode == "watermelon-prism":
        # Deep Research has google_search and url_context by default. We do not
        # pass seed URLs or previous Brand3 evidence in this mode.
        return {
            "agent": AGENT,
            "input": WATERMELON_PRISM_PROMPT,
            "background": True,
            "agent_config": {
                "type": "deep-research",
                "thinking_summaries": "auto",
                "collaborative_planning": False,
            },
        }
    if mode == "single-url-search":
        # Deep Research has google_search and url_context by default. We do not
        # pass seed URLs or previous Brand3 evidence in this mode.
        return {
            "agent": AGENT,
            "input": SINGLE_URL_PROMPT,
            "background": True,
            "agent_config": {
                "type": "deep-research",
                "thinking_summaries": "auto",
                "collaborative_planning": False,
            },
        }
    return {
        "agent": AGENT,
        "input": PROMPT,
        "background": True,
        "tools": [{"type": "url_context"}],
        "agent_config": {
            "type": "deep-research",
            "thinking_summaries": "auto",
            "collaborative_planning": False,
        },
    }


def create_interaction(api_key: str, request_payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        INTERACTIONS_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "Api-Revision": API_REVISION,
        },
        json=request_payload,
        timeout=60,
    )
    return _response_payload(response)


def get_interaction(api_key: str, interaction_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{INTERACTIONS_URL}/{interaction_id}",
        headers={
            "x-goog-api-key": api_key,
            "Api-Revision": API_REVISION,
        },
        timeout=60,
    )
    return _response_payload(response)


def _response_payload(response: requests.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except Exception:
        body = {"raw_text": response.text}
    if response.status_code >= 400:
        return {
            "error": True,
            "status_code": response.status_code,
            "body": body,
        }
    return body


def _interaction_id(payload: dict[str, Any]) -> str:
    for key in ("id", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.rsplit("/", 1)[-1]
    return ""


def _status(payload: dict[str, Any]) -> str:
    for key in ("status", "state"):
        value = payload.get(key)
        if isinstance(value, str):
            return value.lower()
    return ""


def _is_done(payload: dict[str, Any]) -> bool:
    status = _status(payload)
    return status in {"completed", "succeeded", "failed", "cancelled", "canceled"}


def _is_success(payload: dict[str, Any]) -> bool:
    status = _status(payload)
    return status in {"completed", "succeeded"}


def _walk_text(value: Any) -> list[str]:
    texts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "raw_text"} and isinstance(item, str):
                texts.append(item)
            else:
                texts.extend(_walk_text(item))
    elif isinstance(value, list):
        for item in value:
            texts.extend(_walk_text(item))
    return texts


def _extract_json_packet(payload: dict[str, Any], *, expected_case_id: str) -> dict[str, Any] | None:
    for text in reversed(_walk_text(payload)):
        candidate = text.strip()
        if not candidate:
            continue
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
        if fenced:
            candidate = fenced.group(1)
        else:
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start >= 0 and end > start:
                candidate = candidate[start : end + 1]
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict) and parsed.get("case_id") == expected_case_id:
            return parsed
    return None


def _walk_usage(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if "usage" in key.lower() and isinstance(item, dict):
                found.append(item)
            found.extend(_walk_usage(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_usage(item))
    return found


def _int_from_usage(usage: dict[str, Any], keys: tuple[str, ...]) -> int:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return 0


def build_cost_observation(
    *,
    request_payload: dict[str, Any],
    raw_payload: dict[str, Any] | None,
    executed: bool,
    mode: str,
    interaction_id: str = "",
    error: str = "",
) -> dict[str, Any]:
    usage_records = _walk_usage(raw_payload or {})
    usage = usage_records[-1] if usage_records else {}
    input_tokens = _int_from_usage(
        usage,
        (
            "promptTokenCount",
            "inputTokenCount",
            "input_tokens",
            "prompt_tokens",
            "total_input_tokens",
        ),
    )
    output_tokens = _int_from_usage(
        usage,
        (
            "candidatesTokenCount",
            "outputTokenCount",
            "output_tokens",
            "completion_tokens",
            "total_output_tokens",
        ),
    )
    total_tokens = _int_from_usage(usage, ("totalTokenCount", "total_tokens"))
    thought_tokens = _int_from_usage(usage, ("thoughtTokenCount", "thought_tokens", "total_thought_tokens"))
    billed_output_tokens = output_tokens + thought_tokens
    estimated_usd = None
    estimate_basis = "unknown"
    if input_tokens or billed_output_tokens:
        # Gemini 3.1 Pro Preview standard rates. Prompts over 200k tokens use
        # the higher long-context input/output rates.
        input_rate = 4.0 if input_tokens > 200_000 else 2.0
        output_rate = 18.0 if input_tokens > 200_000 else 12.0
        estimated_usd = round(
            (input_tokens / 1_000_000 * input_rate)
            + (billed_output_tokens / 1_000_000 * output_rate),
            6,
        )
        estimate_basis = (
            "approx_gemini_3_1_pro_preview_standard_rates_long_context_when_input_exceeds_200k_"
            "counts_thought_tokens_as_output_excludes_search_tool_charges"
        )
    return {
        "case_id": case_id_for_mode(mode),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trial_mode": mode,
        "executed": executed,
        "interaction_id": interaction_id,
        "agent": request_payload.get("agent"),
        "tools": request_payload.get("tools"),
        "default_agent_tools_used": mode in {"single-url-search", "watermelon-prism"},
        "open_google_search_enabled": mode in {"single-url-search", "watermelon-prism"},
        "url_context_enabled": True,
        "seed_urls_provided": mode not in {"single-url-search", "watermelon-prism"},
        "previous_brand3_evidence_provided": False,
        "deep_research_max_enabled": False,
        "retries": 0,
        "usage_metadata_found": bool(usage),
        "usage_metadata": usage,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "thought_tokens": thought_tokens,
        "estimated_billed_output_tokens": billed_output_tokens,
        "total_tokens": total_tokens,
        "estimated_usd": estimated_usd,
        "estimate_basis": estimate_basis,
        "cost_observability": "observable" if usage else "unknown",
        "automation_recommendation": (
            "do_not_automate_until_usage_and_packet_quality_are_reviewed"
            if not usage
            else "manual_review_required_before_any_automation"
        ),
        "error": error,
    }


def write_notes(
    *,
    paths: dict[str, Path],
    mode: str,
    executed: bool,
    interaction_id: str,
    packet: dict[str, Any] | None,
    error: str,
) -> None:
    tools_note = (
        "default Deep Research tools: google_search and url_context"
        if mode in {"single-url-search", "watermelon-prism"}
        else "url_context only"
    )
    search_note = "enabled" if mode in {"single-url-search", "watermelon-prism"} else "disabled"
    case_note = "Watermelon prism" if mode == "watermelon-prism" else "Builtwith / Kit"
    paths["notes"].write_text(
        "\n".join(
            [
                "# Deep Research Evidence Packet Trial Notes",
                "",
                f"- Case: {case_note}",
                f"- Mode: {mode}",
                f"- Executed: {executed}",
                f"- Interaction ID: {interaction_id or 'n/a'}",
                f"- Tools: {tools_note}",
                f"- Open Google Search: {search_note}",
                f"- Seed URLs provided: {mode not in {'single-url-search', 'watermelon-prism'}}",
                "- Previous Brand3 evidence provided: False",
                "- Deep Research Max: disabled",
                "- Collaborative planning: not used; the scope was fixed to one evidence-packet interaction.",
                f"- Evidence packet parsed: {bool(packet)}",
                f"- Error: {error or 'none'}",
                "",
                "This trial is lab-only. It does not replace Brand3 collectors, scoring, prompts, report generation, rendering, persisted payloads, or Visual Signature.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> int:
    paths = paths_for_mode(args.mode)
    request_payload = build_request(args.mode)
    _write_json(paths["request"], request_payload)

    if args.recompute_cost_from_raw:
        if not paths["raw"].exists():
            cost = build_cost_observation(
                request_payload=request_payload,
                raw_payload=None,
                executed=False,
                mode=args.mode,
                error="raw_interaction_missing",
            )
            _write_json(paths["cost"], cost)
            return 6
        raw_payload = json.loads(paths["raw"].read_text(encoding="utf-8"))
        cost = build_cost_observation(
            request_payload=request_payload,
            raw_payload=raw_payload,
            executed=True,
            mode=args.mode,
            interaction_id=_interaction_id(raw_payload),
            error="",
        )
        _write_json(paths["cost"], cost)
        return 0

    if args.dry_run:
        cost = build_cost_observation(
            request_payload=request_payload,
            raw_payload=None,
            executed=False,
            mode=args.mode,
            error="dry_run_only",
        )
        _write_json(paths["cost"], cost)
        write_notes(paths=paths, mode=args.mode, executed=False, interaction_id="", packet=None, error="dry_run_only")
        return 0

    api_key = _read_env_api_key()
    if not api_key:
        cost = build_cost_observation(
            request_payload=request_payload,
            raw_payload=None,
            executed=False,
            mode=args.mode,
            error="missing_api_key",
        )
        _write_json(paths["cost"], cost)
        write_notes(paths=paths, mode=args.mode, executed=False, interaction_id="", packet=None, error="missing_api_key")
        return 2

    created = create_interaction(api_key, request_payload)
    if created.get("error"):
        _write_json(paths["raw"], created)
        cost = build_cost_observation(
            request_payload=request_payload,
            raw_payload=created,
            executed=True,
            mode=args.mode,
            error="create_interaction_failed",
        )
        _write_json(paths["cost"], cost)
        write_notes(paths=paths, mode=args.mode, executed=True, interaction_id="", packet=None, error="create_interaction_failed")
        return 3

    interaction_id = _interaction_id(created)
    if not interaction_id:
        _write_json(paths["raw"], created)
        cost = build_cost_observation(
            request_payload=request_payload,
            raw_payload=created,
            executed=True,
            mode=args.mode,
            error="missing_interaction_id",
        )
        _write_json(paths["cost"], cost)
        write_notes(paths=paths, mode=args.mode, executed=True, interaction_id="", packet=None, error="missing_interaction_id")
        return 4

    current = created
    deadline = time.time() + args.timeout_seconds
    while not _is_done(current) and time.time() < deadline:
        time.sleep(args.poll_seconds)
        current = get_interaction(api_key, interaction_id)
        if current.get("error"):
            break

    _write_json(paths["raw"], current)
    packet = _extract_json_packet(current, expected_case_id=case_id_for_mode(args.mode)) if _is_success(current) else None
    if packet:
        _write_json(paths["packet"], packet)

    error = ""
    if current.get("error"):
        error = "get_interaction_failed"
    elif not _is_done(current):
        error = "timeout_waiting_for_completion"
    elif not _is_success(current):
        error = f"interaction_not_successful:{_status(current)}"
    elif not packet:
        error = "completed_but_no_parseable_evidence_packet"

    cost = build_cost_observation(
        request_payload=request_payload,
        raw_payload=current,
        executed=True,
        mode=args.mode,
        interaction_id=interaction_id,
        error=error,
    )
    _write_json(paths["cost"], cost)
    write_notes(paths=paths, mode=args.mode, executed=True, interaction_id=interaction_id, packet=packet, error=error)
    return 0 if not error else 5


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("seeded-url-context", "single-url-search", "watermelon-prism"),
        default="seeded-url-context",
        help=(
            "Trial mode. single-url-search and watermelon-prism use only the audit URL "
            "and default Deep Research web tools."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Only write request and dry-run cost files.")
    parser.add_argument(
        "--recompute-cost-from-raw",
        action="store_true",
        help="Rebuild cost_observation.json from an existing raw_interaction.json without making an API call.",
    )
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
