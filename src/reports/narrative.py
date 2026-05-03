"""
LLM-powered narrative generators for the redesigned report.

Three public entry points:
  - generate_synthesis(context)            → §1 prose (4-6 lines)
  - generate_dimension_findings(dim, brand) → §3 sub-findings per dimension
  - generate_tensions(dimensions, brand)    → §4 cross-dim tension (or None)

All three fail closed: any LLM or parsing error falls back to a deterministic
result so the report always renders. All LLM text is untrusted — the caller
(Jinja template with autoescape) is responsible for HTML escaping.
"""

from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass, field
from typing import Any

from .derivation import DimensionEvidences, Evidence

log = logging.getLogger("brand3.reports.narrative")


@dataclass
class Finding:
    """One §3 sub-block: title + prose + supporting URLs."""

    title: str
    prose: str
    evidence_urls: list[str] = field(default_factory=list)


@dataclass
class SynthesisContext:
    """Input bundle for §1 generation."""

    brand: str
    url: str
    composite_score: float | None
    dimensions: list[DimensionEvidences]
    data_quality: str
    top_evidences: list[Evidence]


# In-memory cache — keyed by (run_id, function_name, extra). TTL = process life.
_CACHE: dict[tuple, Any] = {}

_SYNTHESIS_MAX_TOKENS = 1200
_FINDINGS_MAX_TOKENS = 2000
_TENSIONS_MAX_TOKENS = 1200
_FINDINGS_CALL_TIMEOUT_S = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_synthesis(
    context: SynthesisContext,
    analyzer=None,
    run_id: int | None = None,
) -> str:
    """§1 prose (4-6 lines in English). Falls back to a deterministic summary."""
    cache_key = ("synthesis", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    prose = _try_synthesis(context, analyzer) or _fallback_synthesis(context)
    if cache_key is not None:
        _CACHE[cache_key] = prose
    return prose


def generate_dimension_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer=None,
    run_id: int | None = None,
) -> list[Finding]:
    """§3 sub-findings for one dimension. Empty list if no evidences at all."""
    cache_key = ("findings", run_id, dim.dimension) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    if not dim.evidences:
        result: list[Finding] = []
    else:
        result = _try_findings(dim, brand, analyzer) or _fallback_findings(dim)

    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
) -> str | None:
    """§4 cross-dimension tension, or None if nothing relevant to say."""
    cache_key = ("tensions", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    result = _try_tensions(dimensions, brand, analyzer)
    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_all_findings(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    max_workers: int = 5,
) -> dict[str, list[Finding]]:
    """Run generate_dimension_findings for all dimensions in parallel.

    Applies a hard timeout via `concurrent.futures.wait(timeout=...)` so a
    hung LLM call can never block the report render past that window. Any
    dimension that fails or times out falls back to `_fallback_findings`;
    the rest are unaffected.
    """
    out: dict[str, list[Finding]] = {}
    if not dimensions:
        return out

    dim_by_name = {d.dimension: d for d in dimensions}
    # NOTE: do NOT use a `with` block — on timeout we must return without
    # waiting for hung workers. `pool.shutdown(wait=False)` lets stuck LLM
    # calls finish in the background while the report still renders.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_to_name = {
            pool.submit(
                generate_dimension_findings, d, brand, analyzer, run_id
            ): d.dimension
            for d in dimensions
        }
        done, not_done = concurrent.futures.wait(
            future_to_name.keys(),
            timeout=_FINDINGS_CALL_TIMEOUT_S,
            return_when=concurrent.futures.ALL_COMPLETED,
        )
        for fut in done:
            name = future_to_name[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:
                log.warning("findings call for %s failed: %s", name, exc)
                out[name] = _fallback_findings(dim_by_name[name])
        for fut in not_done:
            name = future_to_name[fut]
            log.warning(
                "findings call for %s exceeded %ss timeout — using fallback",
                name, _FINDINGS_CALL_TIMEOUT_S,
            )
            fut.cancel()
            out[name] = _fallback_findings(dim_by_name[name])
    finally:
        pool.shutdown(wait=False)

    return out


def clear_cache() -> None:
    """Drop the in-memory cache. Mostly useful for tests."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Synthesis (§1)
# ---------------------------------------------------------------------------


_SYNTHESIS_SYSTEM = (
    "You are a brand analyst writing for a CMO or founder. "
    "Your output is inserted verbatim into a professional report. "
    "Always respond in English, in continuous prose, no markdown or bullets."
)


def _build_synthesis_user_prompt(ctx: SynthesisContext) -> str:
    dim_lines = []
    for d in ctx.dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        dim_lines.append(f"- {d.display_name}: {score}/100 ({d.verdict})")

    evidences = _format_evidences_for_prompt(ctx.top_evidences, limit=5)
    if ctx.composite_score is None:
        composite_line = "- Global score: n/a (not computed for this run)"
    else:
        band = _band_letter(ctx.composite_score)
        composite_line = f"- Global score: {ctx.composite_score:.0f}/100 (band {band})"

    return f"""Write a SYNTHESIS PARAGRAPH about the brand {ctx.brand} ({ctx.url}) in English, 4 to 6 lines long.

Context:
{composite_line}
{chr(10).join(dim_lines)}
- Data quality: {ctx.data_quality}

Selected evidence:
{evidences or "(no relevant evidence)"}

Rules:
1. DO NOT use bullet points or tables. Continuous prose only.
2. DO NOT cite numbers except the global score if it helps.
3. DO NOT say "this brand has". Talk about what the brand does, says, or achieves.
4. The last sentence must identify the main tension if one exists (e.g. "strong presence but generic perception") or an actionable takeaway when no clear tension is visible.
5. Register: professional, direct. No marketing-speak.
6. Return ONLY the paragraph, no title, no metadata."""


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
    # Strip accidental markdown wrappers.
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0].strip()
    return text


def _fallback_synthesis(ctx: SynthesisContext) -> str:
    """Deterministic 4-line fallback. Used when LLM is unavailable.

    When `composite_score` is None the header line intentionally avoids
    fabricating a "0/100" score — the UI must honestly reflect that the
    run was not scorable end-to-end.
    """
    scored = [d for d in ctx.dimensions if d.score is not None]
    if ctx.composite_score is None:
        header = f"{ctx.brand}: global score unavailable for this run."
    else:
        band = _band_letter(ctx.composite_score)
        header = f"{ctx.brand} scores {ctx.composite_score:.0f}/100 (band {band})."
    if scored:
        top = max(scored, key=lambda d: d.score)
        bottom = min(scored, key=lambda d: d.score)
        lines = [
            header,
            f"Strongest dimension: {top.display_name} ({top.score:.0f}/100).",
            f"Weakest dimension: {bottom.display_name} ({bottom.score:.0f}/100).",
            f"Analysis data quality: {ctx.data_quality}.",
        ]
    else:
        lines = [
            header,
            "Per-dimension scores unavailable for this run.",
            "Check engine logs to understand the scoring failure.",
            f"Data quality: {ctx.data_quality}.",
        ]
    return " ".join(lines)


# ---------------------------------------------------------------------------
# Findings (§3) — one list per dimension
# ---------------------------------------------------------------------------


_FINDINGS_SYSTEM = (
    "You are a brand analyst. "
    "You ALWAYS return valid JSON with the exact shape requested. "
    "Text inside the JSON is written in English."
)


def _build_findings_user_prompt(dim: DimensionEvidences, brand: str) -> str:
    score = "n/a" if dim.score is None else f"{dim.score:.0f}"
    evidences = _format_evidences_for_prompt(dim.evidences, limit=12)
    return f"""Dimension: {dim.display_name}
Score: {score}/100
Verdict: {dim.verdict} · {dim.verdict_adjective}
Brand: {brand}

Evidence available for this dimension:
{evidences or "(none)"}
(Format: [SOURCE_TYPE · DOMAIN · sentiment?] "quote if present" → url)

Identify between 1 and 3 distinct thematic FINDINGS within this dimension. A finding groups evidence items that tell the same story.

For each finding return:
- title: descriptive phrase of 3-6 words in English, no trailing period.
- prose: 2-3 lines in English (max 350 characters) weaving the relevant evidence. Mention at least one concrete detail.
- evidence_urls: list of URLs (2-4) that support this finding. Only URLs that actually appear in the input evidence.

Rules:
1. DO NOT cite numbers.
2. DO NOT use bullets inside the prose.
3. If evidence comes from ONE source only (e.g. only the brand's own site), return a single finding that makes it explicit ("self-description only").
4. If you detect a contradiction between sources, dedicate a finding to it titled with the contradiction.

Return JSON with exactly this shape:
{{"findings": [{{"title": "...", "prose": "...", "evidence_urls": ["...", "..."]}}]}}"""


def _try_findings(
    dim: DimensionEvidences,
    brand: str,
    analyzer,
) -> list[Finding] | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        data = client._call_json(
            system=_FINDINGS_SYSTEM,
            user=_build_findings_user_prompt(dim, brand),
            max_tokens=_FINDINGS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("findings call for %s raised: %s", dim.dimension, exc)
        return None
    if not isinstance(data, dict):
        return None
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list) or not raw_findings:
        return None

    known_urls = {ev.url for ev in dim.evidences if ev.url}
    out: list[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        prose = str(item.get("prose") or "").strip()
        if not title or not prose:
            continue
        urls_raw = item.get("evidence_urls") or []
        if not isinstance(urls_raw, list):
            urls_raw = []
        urls = _validate_urls(urls_raw, known_urls)
        out.append(Finding(title=title, prose=prose, evidence_urls=urls))
    return out or None


def _fallback_findings(dim: DimensionEvidences) -> list[Finding]:
    """Single-finding fallback used when LLM is unavailable but evidences exist."""
    if not dim.evidences:
        return []
    urls = _unique_preserve([ev.url for ev in dim.evidences if ev.url])
    prose = (
        f"{len(dim.evidences)} sources consulted; automatic synthesis "
        "unavailable for this run."
    )
    return [
        Finding(
            title="Available evidence",
            prose=prose,
            evidence_urls=urls[:4],
        )
    ]


# ---------------------------------------------------------------------------
# Tensions (§4)
# ---------------------------------------------------------------------------


_TENSIONS_SYSTEM = (
    "You are a brand analyst. "
    "You answer with strict JSON: a single cross-dimensional tension in prose, or null."
)


def _build_tensions_user_prompt(
    dimensions: list[DimensionEvidences], brand: str
) -> str:
    score_lines = []
    evidence_lines = []
    for d in dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        score_lines.append(f"- {d.display_name}: {score}/100 ({d.verdict} · {d.verdict_adjective})")
        top = _format_evidences_for_prompt(d.evidences, limit=2)
        evidence_lines.append(f"* {d.display_name}:\n{top or '  (no evidence)'}")

    return f"""Brand: {brand}

Scores and verdicts:
{chr(10).join(score_lines)}

Top evidence per dimension:
{chr(10).join(evidence_lines)}

Decide whether ONE significant cross-dimensional tension exists. Examples of tensions:
- Self-description versus external categorization diverge.
- High publishing frequency paired with low external resonance.
- Strong visual identity paired with a confusing message.
- Clear differentiation in copy but generic market perception.

If you find a real tension, return 3-4 lines of prose in English describing it. If no meaningful tension exists, return null.

Return JSON: {{"tension": "prose text"}} or {{"tension": null}}"""


def _try_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer,
) -> str | None:
    client = analyzer or _default_analyzer()
    if client is None:
        return None
    try:
        data = client._call_json(
            system=_TENSIONS_SYSTEM,
            user=_build_tensions_user_prompt(dimensions, brand),
            max_tokens=_TENSIONS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("tensions call raised: %s", exc)
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("tension")
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_analyzer():
    """Instantiate the shared LLMAnalyzer, returning None if no API key."""
    try:
        from src.features.llm_analyzer import LLMAnalyzer
        from src.config import LLM_PREMIUM_MODEL
    except Exception as exc:
        log.warning("LLMAnalyzer import failed: %s", exc)
        return None
    analyzer = LLMAnalyzer(model=LLM_PREMIUM_MODEL)
    if not analyzer.api_key:
        return None
    return analyzer


def _format_evidences_for_prompt(evidences: list[Evidence], limit: int) -> str:
    lines = []
    for ev in evidences[:limit]:
        quote = (ev.quote or "").strip()
        if len(quote) > 240:
            quote = quote[:237] + "…"
        quote_part = f'"{quote}"' if quote else "(no quote)"
        src_bits = [ev.source_type]
        if ev.source_domain:
            src_bits.append(ev.source_domain)
        if ev.sentiment:
            src_bits.append(ev.sentiment)
        tag = " · ".join(src_bits)
        url_part = f" → {ev.url}" if ev.url else ""
        lines.append(f"[{tag}] {quote_part}{url_part}")
    return "\n".join(lines)


def _validate_urls(urls: list, allowlist: set[str]) -> list[str]:
    """Keep only http(s) URLs present in the input evidences, dedupe, cap at 4."""
    out: list[str] = []
    seen: set[str] = set()
    for u in urls:
        if not isinstance(u, str):
            continue
        s = u.strip()
        if not (s.startswith("http://") or s.startswith("https://")):
            continue
        if allowlist and s not in allowlist:
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= 4:
            break
    return out


def _unique_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _band_letter(score: float | None) -> str:
    if score is None:
        return "?"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C+"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"
