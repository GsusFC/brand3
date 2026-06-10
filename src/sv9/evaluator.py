"""SV9 component evaluator: full ladder, one boolean verdict per rung.

Evaluation principles (design doc section 5):
- Chained context, independent verdicts. Evaluators receive detected texts
  (facts) from other components, never their scores (judgments).
- Every evaluation is total: each component always returns score + status.
  Nothing blocks anything.
- Dependencies live in the rungs, never as preconditions. A missing upstream
  component fails its relational rung semantically; it never aborts evaluation.
- The LLM judges rungs and quotes evidence. The score is computed by code
  (src/sv9/aggregator.py), never by the model.

A passed rung without an evidence quote is demoted to failed: the quote is the
contract (cita obligatoria).
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.sv9.aggregator import score_from_rung_profile
from src.sv9.models import (
    ComponentResult,
    RungVerdict,
    STATUS_NOT_DETECTED,
    STATUS_NOT_EVALUATED,
    STATUS_SCORED,
)
from src.sv9.rubric import COMPONENTS, PRESENTATION_ORDER, RUBRIC_VERSION

SV9_EVALUATOR_PROMPT_VERSION = "sv9-evaluator-v0.1"
SV9_EVALUATOR_TIMEOUT_SECONDS = 90
SV9_EVALUATOR_MAX_WORKERS = 4

_VERDICTS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rung": {"type": "integer"},
                    "passed": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "reasoning": {"type": "string"},
                },
                "required": ["rung", "passed", "evidence", "reasoning"],
            },
        }
    },
    "required": ["verdicts"],
}

_EVALUATOR_SYSTEM_PROMPT = """You are the SV9 evaluator of the Brand3 Scanner.

You judge ONE brand component against a cumulative ladder rubric. Each rung
adds exactly one observable criterion. You return one verdict per rung.

Rules:
- You are an evidence analyst, not a brand strategist. Judge only from the
  material provided in the user message.
- For every rung, decide passed=true or passed=false against that rung's
  criterion on its own.
- Every passed=true REQUIRES a verbatim or near-verbatim quote from the
  provided material in the evidence field. No quote, no pass.
- When the evidence is ambiguous or insufficient for a rung, the verdict is
  passed=false. Prefer a false negative over an unsupported pass.
- Relational criteria (those that reference another component) fail when the
  referenced component is marked '(no detectado)': you cannot connect to
  something absent.
- Auxiliary signals are supporting evidence collected from third-party sources
  (mentions, sentiment, consistency analysis). They may support high rungs that
  the brand's own site cannot prove.
- Do not invent. Do not average. Do not reward ambition without proof.
- Return strict JSON only, with a verdict for every rung from 1 to N.
"""

_COHERENCIA_SYSTEM_PROMPT = """You are the SV9 Coherencia evaluator of the Brand3 Scanner.

Coherencia reads the whole: it has no detection of its own. You judge two axes
against a cumulative ladder rubric:

- INTERNAL axis (sintonía): do the 9 components tell the same story? Does the
  vision continue the mission? Does the personality embody the values? Does the
  magnetism grow from the value proposition or is it a pasted slogan?
- EXTERNAL axis (consistencia): does what the brand says on its site match what
  it says — and what is said about it — across the rest of its digital spaces?
  Judge this axis from the auxiliary consistency signals.

Rules:
- Judge only from the material provided. One verdict per rung.
- Every passed=true REQUIRES a quote or a concrete reference to the provided
  material in the evidence field. No quote, no pass.
- Missing components ('(no detectado)') are coherence information: holes mean
  the pieces cannot be connected at that point.
- When the evidence is ambiguous, the verdict is passed=false.
- Return strict JSON only, with a verdict for every rung from 1 to N.
"""


def evaluate_snapshot_components(
    *,
    tldr: dict[str, Any],
    signals: dict[str, list[dict[str, Any]]],
    brand_name: str,
    url: str,
    llm: Any,
) -> dict[str, ComponentResult]:
    """Evaluate the 9 detected components in parallel, then Coherencia.

    All nine only need detection texts (available upfront), so they are
    independent. Coherencia needs the nine verdicts and runs last.
    """
    component_keys = [key for key in PRESENTATION_ORDER if key != "coherencia"]

    def _evaluate(key: str) -> ComponentResult:
        return evaluate_component(
            key,
            tldr=tldr,
            signals=signals.get(key) or [],
            brand_name=brand_name,
            url=url,
            llm=llm,
        )

    results: dict[str, ComponentResult] = {}
    with ThreadPoolExecutor(max_workers=SV9_EVALUATOR_MAX_WORKERS) as pool:
        for key, result in zip(component_keys, pool.map(_evaluate, component_keys)):
            results[key] = result

    results["coherencia"] = evaluate_coherencia(
        components=results,
        tldr=tldr,
        signals=signals.get("coherencia") or [],
        brand_name=brand_name,
        url=url,
        llm=llm,
    )
    return results


def evaluate_component(
    key: str,
    *,
    tldr: dict[str, Any],
    signals: list[dict[str, Any]],
    brand_name: str,
    url: str,
    llm: Any,
) -> ComponentResult:
    """Evaluate one of the 9 components against its full ladder."""
    spec = COMPONENTS[key]
    block = tldr.get(spec["tldr_key"]) if spec["tldr_key"] else None
    block = block if isinstance(block, dict) else {}

    detected = bool(block.get("detected")) and block.get("content")
    if not detected:
        return ComponentResult(
            component=key,
            status=STATUS_NOT_DETECTED,
            score=0,
            detection_mode=str(block.get("mode") or "not_detected"),
            detection_confidence=str(block.get("confidence") or "insufficient"),
        )

    if llm is None or not getattr(llm, "api_key", None):
        return ComponentResult(
            component=key,
            status=STATUS_NOT_EVALUATED,
            detected_content=_block_content_text(block),
            error="llm_unavailable",
        )

    user_prompt = _build_component_prompt(
        key,
        block=block,
        signals=signals,
        tldr=tldr,
        brand_name=brand_name,
        url=url,
    )
    return _run_ladder_call(
        key,
        system=_EVALUATOR_SYSTEM_PROMPT,
        user=user_prompt,
        llm=llm,
        detected_content=_block_content_text(block),
        detection_mode=str(block.get("mode") or ""),
        detection_confidence=str(block.get("confidence") or ""),
        evidence=[str(e) for e in (block.get("evidence") or [])],
    )


def evaluate_coherencia(
    *,
    components: dict[str, ComponentResult],
    tldr: dict[str, Any],
    signals: list[dict[str, Any]],
    brand_name: str,
    url: str,
    llm: Any,
) -> ComponentResult:
    """Evaluate Coherencia over the whole: internal harmony + external consistency."""
    if llm is None or not getattr(llm, "api_key", None):
        return ComponentResult(
            component="coherencia",
            status=STATUS_NOT_EVALUATED,
            error="llm_unavailable",
        )

    user_prompt = _build_coherencia_prompt(
        components=components,
        tldr=tldr,
        signals=signals,
        brand_name=brand_name,
        url=url,
    )
    return _run_ladder_call(
        "coherencia",
        system=_COHERENCIA_SYSTEM_PROMPT,
        user=user_prompt,
        llm=llm,
    )


def _run_ladder_call(
    key: str,
    *,
    system: str,
    user: str,
    llm: Any,
    detected_content: str | None = None,
    detection_mode: str | None = None,
    detection_confidence: str | None = None,
    evidence: list[str] | None = None,
) -> ComponentResult:
    spec = COMPONENTS[key]
    try:
        raw = llm._call_json(
            system,
            user,
            json_schema=_VERDICTS_JSON_SCHEMA,
            schema_name=f"sv9_ladder_{key}",
            timeout_seconds=SV9_EVALUATOR_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # Total evaluation: a crash is a status, not an abort.
        raw = {}
        failure_detail = f"evaluator_exception: {exc}"
    else:
        failure_detail = str(getattr(llm, "last_failure_reason", None) or "llm_error")

    verdicts = _normalize_verdicts(raw, scale=spec["scale"])
    if verdicts is None:
        return ComponentResult(
            component=key,
            status=STATUS_NOT_EVALUATED,
            detected_content=detected_content,
            detection_mode=detection_mode,
            detection_confidence=detection_confidence,
            evidence=evidence or [],
            error=failure_detail,
        )

    return ComponentResult(
        component=key,
        status=STATUS_SCORED,
        score=score_from_rung_profile(verdicts),
        rung_profile=verdicts,
        detected_content=detected_content,
        detection_mode=detection_mode,
        detection_confidence=detection_confidence,
        evidence=evidence or [],
    )


def _normalize_verdicts(raw: Any, *, scale: int) -> list[RungVerdict] | None:
    """Validate the LLM payload into one verdict per rung, or None on failure.

    Enforces the evidence contract: a pass without a quote is demoted to fail.
    """
    if not isinstance(raw, dict):
        return None
    items = raw.get("verdicts")
    if not isinstance(items, list):
        return None

    by_rung: dict[int, RungVerdict] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        verdict = RungVerdict.from_dict(item)
        if 1 <= verdict.rung <= scale:
            by_rung[verdict.rung] = verdict
    if set(by_rung) != set(range(1, scale + 1)):
        return None

    normalized = []
    for rung in range(1, scale + 1):
        verdict = by_rung[rung]
        if verdict.passed and not verdict.evidence.strip():
            verdict = RungVerdict(
                rung=verdict.rung,
                passed=False,
                evidence="",
                reasoning=(verdict.reasoning + " | demoted: pass without evidence quote").strip(" |"),
            )
        normalized.append(verdict)
    return normalized


def _block_content_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False) if content else ""


def _ladder_lines(key: str) -> str:
    spec = COMPONENTS[key]
    lines = [f"0: {spec['level_zero']} (baseline, not judged)"]
    for rung in spec["ladder"]:
        lines.append(f"{rung['rung']}: {rung['criterion']}")
    return "\n".join(lines)


def _context_texts(key: str, tldr: dict[str, Any]) -> dict[str, str]:
    """Detected texts of components referenced by relational rungs. Facts, not scores."""
    spec = COMPONENTS[key]
    needed = {dep for rung in spec["ladder"] for dep in rung.get("context_needs", [])}
    context = {}
    for dep in sorted(needed):
        dep_block = tldr.get(COMPONENTS[dep]["tldr_key"]) or {}
        if isinstance(dep_block, dict) and dep_block.get("detected") and dep_block.get("content"):
            context[dep] = _block_content_text(dep_block)
        else:
            context[dep] = "(no detectado)"
    return context


def _signals_lines(signals: list[dict[str, Any]]) -> str:
    if not signals:
        return "(none)"
    lines = []
    for signal in signals:
        value = signal.get("value")
        confidence = signal.get("confidence")
        line = (
            f"- {signal.get('feature')} (legacy {signal.get('legacy_dimension')}): "
            f"value={value} confidence={confidence}"
        )
        detail = signal.get("detail")
        if detail:
            line += f"\n  observations: {detail}"
        lines.append(line)
    return "\n".join(lines)


def _build_component_prompt(
    key: str,
    *,
    block: dict[str, Any],
    signals: list[dict[str, Any]],
    tldr: dict[str, Any],
    brand_name: str,
    url: str,
) -> str:
    spec = COMPONENTS[key]
    context = _context_texts(key, tldr)
    context_section = (
        "\n".join(f"- {COMPONENTS[dep]['label']}: {text}" for dep, text in context.items())
        if context
        else "(not needed for this ladder)"
    )
    evidence_quotes = block.get("evidence") or []
    evidence_section = (
        "\n".join(f"- {quote}" for quote in evidence_quotes) if evidence_quotes else "(none)"
    )
    return f"""Brand: {brand_name}
URL: {url}
Component: {spec['label']} ({key})
Component question: {spec['question']}
Rubric version: {RUBRIC_VERSION}

DETECTED READING (Pass 1, evidence-based):
content: {_block_content_text(block)}
mode: {block.get('mode')}
confidence: {block.get('confidence')}
rationale: {block.get('rationale')}

EVIDENCE QUOTES:
{evidence_section}

AUXILIARY SIGNALS (third-party / cross-surface):
{_signals_lines(signals)}

FACTUAL CONTEXT FROM OTHER COMPONENTS (texts, not judgments):
{context_section}

LADDER (cumulative; judge each rung against its own criterion):
{_ladder_lines(key)}

Return JSON: {{"verdicts": [{{"rung": 1, "passed": true|false, "evidence": "quote", "reasoning": "..."}}, ... one per rung 1..{spec['scale']}]}}"""


def _build_coherencia_prompt(
    *,
    components: dict[str, ComponentResult],
    tldr: dict[str, Any],
    signals: list[dict[str, Any]],
    brand_name: str,
    url: str,
) -> str:
    spec = COMPONENTS["coherencia"]
    pieces = []
    for key in PRESENTATION_ORDER:
        if key == "coherencia":
            continue
        component = components.get(key)
        if component is not None and component.status == STATUS_SCORED and component.detected_content:
            pieces.append(f"- {COMPONENTS[key]['label']}: {component.detected_content}")
        else:
            block = tldr.get(COMPONENTS[key]["tldr_key"]) or {}
            text = (
                _block_content_text(block)
                if isinstance(block, dict) and block.get("detected") and block.get("content")
                else "(no detectado)"
            )
            pieces.append(f"- {COMPONENTS[key]['label']}: {text}")
    return f"""Brand: {brand_name}
URL: {url}
Component: Coherencia
Component question: {spec['question']}
Rubric version: {RUBRIC_VERSION}

INTERNAL AXIS — THE 9 PIECES ON THE TABLE (detected texts):
{chr(10).join(pieces)}

EXTERNAL AXIS — CROSS-SURFACE CONSISTENCY SIGNALS:
{_signals_lines(signals)}

LADDER (cumulative; judge each rung against its own criterion):
{_ladder_lines('coherencia')}

Return JSON: {{"verdicts": [{{"rung": 1, "passed": true|false, "evidence": "quote or concrete reference", "reasoning": "..."}}, ... one per rung 1..{spec['scale']}]}}"""
