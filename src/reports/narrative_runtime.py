"""LLM execution and fallback helpers for Brand3 narrative generation."""

from __future__ import annotations

import logging

from .derivation import DimensionEvidences
from .experimental_perceptual_narrative import PerceptualNarrativeHints, format_perceptual_hints_for_prompt
from .narrative_types import Finding, SynthesisContext
from .narrative_prompts import _FINDINGS_SYSTEM, _SYNTHESIS_SYSTEM, _TENSIONS_SYSTEM
from .narrative_support import (
    _build_findings_user_prompt,
    _build_synthesis_user_prompt,
    _build_tensions_user_prompt,
    _date_anchor_clause,
    _default_analyzer,
    _format_evidences_for_prompt,
    _unique_preserve,
    _validate_urls,
)

log = logging.getLogger("brand3.reports.narrative")

_SYNTHESIS_MAX_TOKENS = 1200
_FINDINGS_MAX_TOKENS = 3500
_TENSIONS_MAX_TOKENS = 1200


def _try_synthesis(ctx: SynthesisContext, analyzer) -> str | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        raw = client._call(
            system=_SYNTHESIS_SYSTEM,
            user=_build_synthesis_user_prompt(ctx),
            max_tokens=_SYNTHESIS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("synthesis call raised: %s", exc)
        return None
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return text


def _fallback_synthesis(ctx: SynthesisContext) -> str:
    scored = [d for d in ctx.dimensions if d.score is not None]
    if scored:
        top = max(scored, key=lambda d: d.score)
        bottom = min(scored, key=lambda d: d.score)
        lines = [
            f"Cross-dimension snapshot for {ctx.brand}.",
            f"{top.display_name} is the highest-scoring dimension at {top.score:.0f}/100; {bottom.display_name} the lowest at {bottom.score:.0f}/100.",
            f"Observed pattern: the clearest read sits in {top.display_name}, while {bottom.display_name} remains the weakest read and deserves closer follow-up in §4.",
            f"Data quality for this run: {ctx.data_quality}.",
            "Editorial synthesis unavailable - see per-dimension findings in §4 for the substantive read.",
        ]
    else:
        lines = [
            f"Cross-dimension snapshot for {ctx.brand}.",
            "Per-dimension scores unavailable for this run.",
            "Observed pattern: the run does not yet support a stable cross-dimension read.",
            f"Data quality: {ctx.data_quality}.",
            "Editorial synthesis unavailable - check engine logs.",
        ]
    return " ".join(lines)


def _try_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer,
    analysis_date: str | None = None,
    perceptual_hints: PerceptualNarrativeHints | None = None,
    packet: dict | None = None,
) -> list[Finding] | None:
    client = analyzer or _default_analyzer()
    if client is None:
        log.warning("findings: no LLM client available for %s", dim.dimension)
        return None
    try:
        data = client._call_json(
            system=_FINDINGS_SYSTEM,
            user=_build_findings_user_prompt(dim, brand, analysis_date, perceptual_hints, packet),
            max_tokens=_FINDINGS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("findings call for %s raised: %s", dim.dimension, exc)
        return None
    if not isinstance(data, dict):
        log.warning("findings for %s: response was not a dict (type=%s)", dim.dimension, type(data).__name__)
        return None
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list) or not raw_findings:
        log.warning("findings for %s: 'findings' missing or empty in response keys=%s", dim.dimension, list(data.keys()))
        return None

    known_urls = {ev.url for ev in dim.evidences if ev.url}
    out: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        observation = str(item.get("observation") or "").strip()
        implication = str(item.get("implication") or "").strip()
        typical_decision = ""
        if not observation and item.get("prose"):
            observation = str(item.get("prose")).strip()
        if not title or not observation:
            continue
        urls_raw = item.get("evidence_urls") or []
        if not isinstance(urls_raw, list):
            urls_raw = []
        urls = _validate_urls(urls_raw, known_urls)
        out.append(
            Finding(
                title=title,
                observation=observation,
                implication=implication,
                typical_decision=typical_decision,
                evidence_urls=urls,
            )
        )
    if not out:
        log.warning("findings for %s: parsed %d items, all rejected by validation", dim.dimension, len(raw_findings))
        return None
    return out


def _fallback_findings(dim: DimensionEvidences, reason: str = "unknown") -> list[Finding]:
    if not dim.evidences:
        return []
    urls = _unique_preserve([ev.url for ev in dim.evidences if ev.url])
    dominant_surface = urls[0] if urls else "the available sources"
    evidence_kind = "self-description" if len(urls) == 1 else "mixed evidence"
    return [
        Finding(
            title="Available evidence",
            observation=(
                f"{len(dim.evidences)} evidence items consulted for {dim.display_name}, "
                f"anchored in {dominant_surface} ({evidence_kind}). "
                f"Editorial synthesis unavailable (reason: {reason})."
            ),
            implication="",
            typical_decision="",
            evidence_urls=urls[:4],
        )
    ]


def _try_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer,
    analysis_date: str | None = None,
) -> str | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        data = client._call_json(
            system=_TENSIONS_SYSTEM,
            user=_build_tensions_user_prompt(dimensions, brand, analysis_date),
            max_tokens=_TENSIONS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("tensions call raised: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("tension")
    if value is None or not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
