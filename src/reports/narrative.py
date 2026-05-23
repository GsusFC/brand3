"""
LLM-powered narrative generators for the redesigned report.

Three public entry points:
  - generate_synthesis(context)            → §1 prose (4-6 lines)
  - generate_dimension_findings(dim, brand) → §3 sub-findings per dimension
  - generate_tensions(dimensions, brand)    → §4 cross-dim tension (or None)

CAPA 1 EDITORIAL (este patch):
  - Finding ahora tiene estructura formal de evidencia:
    observation / implication / evidence_urls.
  - El prompt de findings prohíbe explícitamente:
      a) echo-chamber: adoptar el discurso self-declared de la marca como
         afirmación propia ("X is the leading platform" → prohibido).
      b) closed evaluative adjectives ("strong", "well-managed", "premier",
         "leading", "successful", etc.) fuera de citas a terceros.
      c) prescripciones singulares ("the brand should X", "needs to Y").
  - `Finding.prose` se mantiene como property concatenada para retrocompat,
    pero excluye `typical_decision` porque Decision Space está desactivado
    temporalmente en el reporte oficial.

NO TOCADO en esta capa (pendiente para capas siguientes):
  - Synthesis (§1) — sigue centrando SCORE_GLOBAL como sujeto. Capa 2.
  - Tensions (§5) — generación independiente sin coordinarse con §1. Capa 2.
  - Trust state propagation a dimensiones individuales. Capa 3.
  - Layout/copy del SCORE_GLOBAL en hero. Capa 4.

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
from .experimental_perceptual_narrative import (
    PerceptualNarrativeHints,
    build_perceptual_narrative_hints,
    format_perceptual_hints_for_prompt,
)

log = logging.getLogger("brand3.reports.narrative")


@dataclass
class Finding:
    """One §3 sub-block. Four-part editorial structure plus URLs.

    Hard discipline:
    - observation: pure factual statement derivable from the evidence.
      Subject must be "the brand says/appears/is described as", never "is/has".
    - implication: editorial inference, conditional language only
      (suggests, may indicate, tends to, likely).
    - typical_decision: legacy compatibility field for persisted payloads.
      New report narratives should not populate it.
    - evidence_urls: 2-4 URLs that actually appear in the input evidence pool.

    Backwards-compat: `prose` is exposed as a derived property concatenating
    observation and implication, so legacy Jinja templates keep rendering
    without reintroducing Decision Space prose.
    """

    title: str
    observation: str = ""
    implication: str = ""
    typical_decision: str = ""
    evidence_urls: list[str] = field(default_factory=list)

    @property
    def prose(self) -> str:
        """Concatenated prose for templates that haven't migrated to structured rendering."""
        parts = [p for p in (self.observation, self.implication) if p]
        return " ".join(parts)


@dataclass
class SynthesisContext:
    """Input bundle for §1 generation."""

    brand: str
    url: str
    composite_score: float | None
    dimensions: list[DimensionEvidences]
    data_quality: str
    top_evidences: list[Evidence]
    analysis_date: str | None = None
    tension_text: str | None = None


# In-memory cache — keyed by (run_id, function_name, extra). TTL = process life.
_CACHE: dict[tuple, Any] = {}

_SYNTHESIS_MAX_TOKENS = 1200
_FINDINGS_MAX_TOKENS = 3500  # 4-field structure + acknowledgment clauses.
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
    analysis_date: str | None = None,
    perceptual_hints: PerceptualNarrativeHints | None = None,
    packet: dict | None = None,
) -> list[Finding]:
    """§3 sub-findings for one dimension. Empty list if no evidences at all."""
    cache_mode = "perceptual" if perceptual_hints and not perceptual_hints.empty() else "base"
    cache_key = ("findings", run_id, dim.dimension, cache_mode) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    if not dim.evidences:
        result: list[Finding] = []
    else:
        result = _try_findings(dim, brand, analyzer, analysis_date, perceptual_hints, packet)
        if result is None:
            log.warning(
                "findings: _try_findings returned None for %s (run_id=%s) — using fallback",
                dim.dimension,
                run_id,
            )
            result = _fallback_findings(dim, reason="llm_unavailable_or_empty")

    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_tensions(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    analysis_date: str | None = None,
) -> str | None:
    """§4 cross-dimension tension, or None if nothing relevant to say."""
    cache_key = ("tensions", run_id) if run_id is not None else None
    if cache_key and cache_key in _CACHE:
        return _CACHE[cache_key]

    result = _try_tensions(dimensions, brand, analyzer, analysis_date)
    if cache_key is not None:
        _CACHE[cache_key] = result
    return result


def generate_all_findings(
    dimensions: list[DimensionEvidences],
    brand: str,
    analyzer=None,
    run_id: int | None = None,
    max_workers: int = 1,
    analysis_date: str | None = None,
    enable_perceptual_narrative: bool = False,
    packet: dict | None = None,
) -> dict[str, list[Finding]]:
    """Run generate_dimension_findings for all dimensions.

    Sequential by default (max_workers=1). Why:
    On macOS, parallel LLM HTTP calls via ThreadPoolExecutor trigger an
    Objective-C fork-safety crash when one worker forks a subprocess while
    another thread is initializing macOS frameworks (NSCharacterSet via
    getproxies_macosx_sysconf in urllib). Running findings serially avoids
    the race entirely.

    Cost: about 5 dims x 5s = 20s extra wall-clock per run. Acceptable for an
    editorial tool. On Linux/prod, pass max_workers > 1 explicitly to
    re-enable parallelism; the bug is macOS-specific.

    The per-call timeout (_FINDINGS_CALL_TIMEOUT_S) is preserved in the
    parallel path so a hung LLM call cannot block the run indefinitely.
    """
    out: dict[str, list[Finding]] = {}
    if not dimensions:
        return out

    if max_workers <= 1:
        for d in dimensions:
            try:
                perceptual_hints = (
                    build_perceptual_narrative_hints(d.dimension)
                    if enable_perceptual_narrative
                    else None
                )
                out[d.dimension] = generate_dimension_findings(
                    d, brand, analyzer, run_id, analysis_date, perceptual_hints, packet
                )
            except Exception as exc:
                log.warning("findings call for %s failed: %s", d.dimension, exc)
                out[d.dimension] = _fallback_findings(
                    d, reason=f"exception:{type(exc).__name__}"
                )
        return out

    dim_by_name = {d.dimension: d for d in dimensions}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    try:
        future_to_name = {
            pool.submit(
                generate_dimension_findings,
                d,
                brand,
                analyzer,
                run_id,
                analysis_date,
                build_perceptual_narrative_hints(d.dimension)
                if enable_perceptual_narrative
                else None,
                packet,
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
                out[name] = _fallback_findings(
                    dim_by_name[name], reason=f"exception:{type(exc).__name__}"
                )
        for fut in not_done:
            name = future_to_name[fut]
            log.warning(
                "findings call for %s exceeded %ss timeout — using fallback",
                name, _FINDINGS_CALL_TIMEOUT_S,
            )
            fut.cancel()
            out[name] = _fallback_findings(dim_by_name[name], reason="timeout")
    finally:
        pool.shutdown(wait=False)

    return out


def clear_cache() -> None:
    """Drop the in-memory cache. Mostly useful for tests."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Synthesis (§1) — UNCHANGED in capa 1. Capa 2 will rewrite this.
# ---------------------------------------------------------------------------


_SYNTHESIS_SYSTEM = (
    "You are an editorial brand analyst writing the §1 synthesis paragraph "
    "for a CMO or founder. Your output is inserted verbatim into a "
    "professional report.\n"
    "\n"
    "FIVE DISCIPLINES (violations make the output unusable):\n"
    "\n"
    "1. THE SCORE IS NOT THE STORY. Do NOT open the paragraph with the "
    "global score, with any band letter, or with any numeric cite. The "
    "score lives elsewhere in the report as metadata. The synthesis is "
    "narrative - its subject is the cross-dimension PATTERN, not the "
    "number that summarizes it.\n"
    "\n"
    "2. NO ECHO-CHAMBER. Never adopt the brand's self-description as "
    "your own assertion. If the brand calls itself 'X', refer to it as "
    "'the brand describes itself as X'. Do NOT echo it as fact.\n"
    "\n"
    "3. CLOSED EVALUATIVE ADJECTIVES are FORBIDDEN outside of direct "
    "quotes from third-party sources. Banned: strong, leading, premier, "
    "essential, successful, robust, compelling, prestigious, top, "
    "dominant, world-class, well-defined, well-managed, well-established, "
    "established, consolidated, matured, polished, comprehensive, "
    "sophisticated, solid, vibrant, cohesive (when applied to brand or "
    "identity), coherent (when applied to brand or identity), "
    "cutting-edge, innovative.\n"
    "\n"
    "Generic procedure: if you reach for an evaluative adjective to "
    "describe the brand or its components, ask whether the evidence "
    "directly shows that quality. If not, drop the adjective and "
    "describe the observable pattern instead.\n"
    "\n"
    "4. SUBJECT MUST BE THE PATTERN, NOT THE BRAND'S ESSENCE. Use "
    "grammatical subjects like 'the dimensions', 'the evidence', "
    "'self-description', 'external coverage'. Avoid 'the brand is', "
    "'the brand has', 'X demonstrates Y'.\n"
    "\n"
    "5. OBSERVATION / IMPLICATION / TENSION. Build the paragraph in that "
    "order. Start from a concrete evidence anchor, then name the observed "
    "pattern, then state the implication in conditional language, and only "
    "then raise the strategic tension or trade-off space if one genuinely "
    "exists.\n"
    "\n"
    "6. NO GENERIC REPORT OPENERS. Avoid openings that sound like a "
    "summary template, such as 'the report shows', 'the brand appears', "
    "'overall, the brand', or any score-led opening. The first sentence "
    "should anchor in evidence, not in the score or in generic praise.\n"
    "\n"
    "7. COHERENCE WITH §5 TENSION. If a tension was identified for §5, "
    "the synthesis paragraph must REFLECT THE SAME TENSION. Do not "
    "invent a different one. Do not contradict §5. If §5 returned no "
    "tension, the synthesis describes the cross-dimension pattern "
    "neutrally without forcing one.\n"
    "\n"
    "Output: 4-6 lines of continuous prose in English. No bullets, no "
    "headers, no markdown. Return ONLY the paragraph."
)


def _build_synthesis_user_prompt(ctx: SynthesisContext) -> str:
    dim_lines = []
    for d in ctx.dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        dim_lines.append(f"- {d.display_name}: {score}/100 ({d.verdict})")

    evidences = _format_evidences_for_prompt(ctx.top_evidences, limit=5)
    date_anchor = _date_anchor_clause(ctx.analysis_date)

    if ctx.tension_text:
        tension_section = (
            "Tension already identified by §5 (the synthesis MUST be "
            "coherent with this - describe the same pattern in slightly "
            "different words, do not invent a different tension):\n"
            f"\"\"\"\n{ctx.tension_text}\n\"\"\""
        )
    else:
        tension_section = (
            "§5 did not identify a meaningful cross-dimensional tension "
            "for this run. The synthesis should describe the cross-"
            "dimension pattern neutrally without forcing one."
        )

    return f"""{date_anchor}

Write the §1 SYNTHESIS PARAGRAPH for the brand {ctx.brand} ({ctx.url}).

Per-dimension scores (for context only - DO NOT open the paragraph with these):
{chr(10).join(dim_lines)}
- Data quality: {ctx.data_quality}

Selected evidence:
{evidences or "(no relevant evidence)"}

{tension_section}

Internal structure of the paragraph (4-6 lines total):
- Open with one concrete evidence anchor from the selected evidence
  (a quote, source domain, page, or channel) and then describe the
  observable pattern it supports. Do not open with the score.
- Make the first sentence diagnostic rather than celebratory. Prefer
  contrast, repetition, mismatch, concentration, or absence over vague
  praise.
- Use the observation / implication / tension order: observation first,
  implication in conditional language (may, could, suggests, likely),
  tension or trade-off space last.
- If a §5 tension exists, name it in the middle of the paragraph using
  the same pattern already identified there. Do not invent a new one.
- Close with what kind of strategic question this configuration
  typically raises - a question or trade-off space, not a prescription.

FORBIDDEN OPENINGS (will be rejected):
- "X scores Y/100"
- "With a global score of..."
- "The brand demonstrates..."
- "X has successfully..."
- Any closed adjective from the banned list applied to the brand
  outside a third-party quote.

Return ONLY the paragraph, no title, no metadata."""


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

    Even in fallback, do not open with the global score - the score is
    metadata. Open with a neutral cross-dimension framing instead.
    """
    scored = [d for d in ctx.dimensions if d.score is not None]
    if scored:
        top = max(scored, key=lambda d: d.score)
        bottom = min(scored, key=lambda d: d.score)
        lines = [
            f"Cross-dimension snapshot for {ctx.brand}.",
            f"{top.display_name} is the highest-scoring dimension at "
            f"{top.score:.0f}/100; {bottom.display_name} the lowest at "
            f"{bottom.score:.0f}/100.",
            f"Observed pattern: the clearest read sits in {top.display_name}, "
            f"while {bottom.display_name} remains the weakest read and "
            f"deserves closer follow-up in §4.",
            f"Data quality for this run: {ctx.data_quality}.",
            "Editorial synthesis unavailable - see per-dimension findings "
            "in §4 for the substantive read.",
        ]
    else:
        lines = [
            f"Cross-dimension snapshot for {ctx.brand}.",
            "Per-dimension scores unavailable for this run.",
            "Observed pattern: the run does not yet support a stable "
            "cross-dimension read.",
            f"Data quality: {ctx.data_quality}.",
            "Editorial synthesis unavailable - check engine logs.",
        ]
    return " ".join(lines)


# ---------------------------------------------------------------------------
# Findings (§3) — REWRITTEN in capa 1
# ---------------------------------------------------------------------------


_FINDINGS_SYSTEM = (
    "You are an editorial brand analyst with strict separation discipline.\n"
    "You ALWAYS return valid JSON with the exact shape requested.\n"
    "Text inside the JSON is written in English.\n"
    "\n"
    "FOUR CRITICAL DISCIPLINES (violations make the output unusable):\n"
    "\n"
    "1. NO ECHO-CHAMBER. Never adopt the brand's self-description as your own assertion. "
    "If the brand calls itself \"the leading platform for X\", the observation reads "
    "\"the brand describes itself as 'the leading platform for X'\" — NEVER \"X is the leading platform\". "
    "The analyst describes what the brand says about itself; the analyst does not echo it as fact.\n"
    "\n"
    "2. SEPARATE OBSERVATION FROM IMPLICATION. Observation = what is literally in the evidence. "
    "Implication = what you editorially infer, in conditional language only "
    "(suggests, tends to, may indicate, likely, could). Mixing the two in a single sentence is a violation.\n"
    "\n"
    "3. NO STRATEGIC PRESCRIPTIONS. Do not include decision-space prose, recommendations, "
    "resource-allocation speculation, or claims about what founders/management teams "
    "should weigh. Keep the output to evidence-anchored observation and bounded implication.\n"
    "\n"
    "4. CLOSED EVALUATIVE ADJECTIVES are FORBIDDEN outside of direct quotes from third-party sources. "
    "Banned list: strong, well-managed, leading, premier, essential, successful, robust, "
    "compelling, prestigious, top, best-in-class, superior, dominant, world-class, "
    "cutting-edge, innovative. If the evidence contains these words inside a quote from a third party, "
    "you may quote them — never restate them as your own characterization.\n"
    "\n"
    "5. DIAGNOSTIC, NOT CELEBRATORY. Prefer mismatch, concentration, repetition, "
    "contrast, absence, or channel divergence over generic praise. If a finding can "
    "be written as a vague compliment, tighten it until the evidence anchor is visible.\n"
    "\n"
    "6. EVIDENCE ANCHOR FIRST. Every observation should start from a concrete anchor "
    "(a quote, source domain, page, surface, or channel) before moving to interpretation."
)


def _build_findings_user_prompt(
    dim: DimensionEvidences,
    brand: str,
    analysis_date: str | None = None,
    perceptual_hints: PerceptualNarrativeHints | None = None,
    packet: dict | None = None,
) -> str:
    score = "n/a" if dim.score is None else f"{dim.score:.0f}"
    evidences = _format_evidences_for_prompt(dim.evidences, limit=12)
    date_anchor = _date_anchor_clause(analysis_date)
    perceptual_hints_section = format_perceptual_hints_for_prompt(perceptual_hints)
    if perceptual_hints_section:
        perceptual_hints_section = f"\n\n{perceptual_hints_section}\n"

    contradiction_warnings = []
    if packet:
        cross_evidence = packet.get("cross_dimension_evidence") or {}
        candidates = cross_evidence.get("contradiction_candidates") or packet.get("contradiction_candidates") or []
        
        feature_names_in_dimension = {ev.feature_name for ev in dim.evidences if ev.feature_name}
        
        FEATURE_TO_DIMENSION = {
            "messaging_consistency": "coherencia",
            "tone_consistency": "coherencia",
            "visual_consistency": "coherencia",
            "web_presence": "presencia",
            "social_footprint": "presencia",
            "search_visibility": "presencia",
            "site_structure": "presencia",
            "brand_sentiment": "percepcion",
            "positioning_clarity": "diferenciacion",
            "competitor_distance": "diferenciacion",
            "momentum": "vitalidad",
            "content_recency": "vitalidad",
            "publication_cadence": "vitalidad",
        }
        
        for cand in candidates:
            if cand.get("type") == "owned_claim_vs_external_source_mismatch":
                feat = cand.get("feature_name") or ""
                is_associated = (
                    feat in feature_names_in_dimension
                    or FEATURE_TO_DIMENSION.get(feat) == dim.dimension
                )
                if is_associated:
                    contradiction_warnings.append(
                        f"Warning: Discrepancy detected between owned claims and external sources for feature '{feat}'. "
                        f"Ensure owned claims are clearly framed as self-declarations and NOT mixed with external validation."
                    )

    warnings_section = ""
    if contradiction_warnings:
        warnings_section = "\nACTIVE CONTRADICTIONS / WARNINGS:\n" + "\n".join(f"- {w}" for w in contradiction_warnings) + "\n"

    return f"""{date_anchor}

Dimension: {dim.display_name}
Score: {score}/100
Verdict: {dim.verdict}
Brand: {brand}

Evidence available for this dimension:
{evidences or "(none)"}
(Format: [SOURCE_TYPE · DOMAIN · sentiment?] "quote if present" → url)
{perceptual_hints_section}{warnings_section}

Identify between 1 and 3 distinct thematic FINDINGS within this dimension. A finding groups evidence items that tell the same story.

Use this writing model for every finding:
- Observation: start with a concrete evidence anchor and describe only what is literally present.
- Implication: state the likely commercial or strategic read in conditional language only.

For each finding return FOUR parts:

- title: 3-6 words describing the PATTERN, not its quality. NO closed adjectives. NO trailing period.
  Good: "Self-described as Designer Hub", "Single-Source Self-Description", "External Coverage Mirrors Self-Pitch"
  Bad: "Strong Identity for Creatives", "Leading Platform", "Well-Managed Infrastructure"

- observation: 1-2 lines. PURE FACTUAL DESCRIPTION. 
  Focus the sentence structure and grammatical subject on source claims or observed surfaces (e.g., "Web copy on netlify.com highlights...", "Landing pages emphasize...", "The official documentation describes...", "External press coverage on techcrunch.com characterizes...", "Self-published materials on the landing page state..."). 
  Avoid repeating the exact same sentence starters across findings. 
  NEVER write objective essence statements like "the brand is X", "the brand has X", "the brand demonstrates X", "the brand projects X".
  Start with one concrete quote, page, source domain, or channel from the evidence pool.
  Quote at least one concrete piece of language or detail from the evidence.

- implication: 1-2 lines. Editorial inference using conditional language ONLY
  (suggests, tends to, may indicate, likely, could). State what the observation could mean
  commercially or strategically. NEVER assert inferred content as fact. NEVER use closed adjectives.

- evidence_urls: list of 2-4 URLs that actually appear in the input evidence.

HARD RULES:
1. SINGLE-SOURCE EVIDENCE: If evidence comes only from the brand's own surface (self-description, no external secondary corroboration in the active pool), clearly state this limitation in the observation using premium, varied phrasing (e.g., "confined exclusively to owned brand channels", "as documented solely in self-published copy with no external validation in the active dataset", "without independent third-party coverage in the evidence pool", "based on owned-media self-description") instead of repeating the same literal disclaimer across findings. The implication must reflect this limitation.
2. CONTRADICTION: If evidence contains a contradiction between sources (e.g. brand says
   one thing, third parties say another), dedicate one finding to that contradiction with
   a title that names it.
3. FORBIDDEN PHRASES (will be rejected): "the brand should", "needs to", "must",
   "X positions itself successfully", "essential hub", "premier destination",
   anything from the closed-adjective list outside a third-party quote.
4. DO NOT cite numbers.
5. DO NOT use bullets inside any field.
6. DO NOT include typical_decision or Decision space fields.

FEW-SHOT EXAMPLES OF PREMIUM EDITORIAL FINDINGS (Syntactically diverse, rich, organic, not matching hiding filters):

Example 1 (Mixed sources):
{{
  "title": "Social Feeds Mirror Site Messaging",
  "observation": "Owned copy on netlify.com asserts 'Build the best web experiences', which mirrors claims on the Netlify X/Twitter profile describing the service as the standard for frontend developers.",
  "implication": "This alignment suggests an active, consistent distribution of core positioning across major brand-owned surfaces, though it relies heavily on self-published material.",
  "evidence_urls": ["https://www.netlify.com/about", "https://x.com/netlify"]
}}

Example 2 (Single-source):
{{
  "title": "Technical Focus Without Third-Party Press",
  "observation": "Developer documentation at docs.wiocapital.com details a specialized API for 'multi-tenant ledger synchronization', which is confined exclusively to owned channels with no external press coverage in the active dataset.",
  "implication": "The lack of external signal could indicate that the product remains in a pre-launch phase or is addressing a highly specialized developer niche rather than a mainstream audience.",
  "evidence_urls": ["https://docs.wiocapital.com/api"]
}}

Return JSON with exactly this shape:
{{"findings": [{{"title": "...", "observation": "...", "implication": "...", "evidence_urls": ["...", "..."]}}]}}"""


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
            user=_build_findings_user_prompt(
                dim, brand, analysis_date, perceptual_hints, packet
            ),
            max_tokens=_FINDINGS_MAX_TOKENS,
        )
    except Exception as exc:
        log.warning("findings call for %s raised: %s", dim.dimension, exc)
        return None
    if not isinstance(data, dict):
        log.warning(
            "findings for %s: response was not a dict (type=%s)",
            dim.dimension,
            type(data).__name__,
        )
        return None
    raw_findings = data.get("findings")
    if not isinstance(raw_findings, list) or not raw_findings:
        log.warning(
            "findings for %s: 'findings' missing or empty in response keys=%s",
            dim.dimension,
            list(data.keys()),
        )
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
        # Backwards compat: if a model returns the old single `prose` field
        # (e.g. an older provider not yet rolled to the new prompt), route
        # it to observation so the report still renders something usable.
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
        log.warning(
            "findings for %s: parsed %d items, all rejected by validation",
            dim.dimension,
            len(raw_findings),
        )
        return None
    return out


def _fallback_findings(
    dim: DimensionEvidences,
    reason: str = "unknown",
) -> list[Finding]:
    """Single-finding fallback used when LLM is unavailable but evidences exist."""
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


# ---------------------------------------------------------------------------
# Tensions (§4) — UNCHANGED in capa 1. Capa 2 will rewrite this.
# ---------------------------------------------------------------------------


_TENSIONS_SYSTEM = (
    "You are an editorial brand analyst with strict separation discipline.\n"
    "You answer with strict JSON: {\"tension\": \"<prose>\"} or {\"tension\": null}.\n"
    "\n"
    "FIVE DISCIPLINES (violations make the output unusable):\n"
    "\n"
    "1. NO ECHO-CHAMBER. Never adopt the brand's self-description as your "
    "own assertion. If the brand calls itself 'the leading platform for X', "
    "say 'the brand describes itself as the leading platform for X' — "
    "NEVER 'X is the leading platform'.\n"
    "\n"
    "2. CLOSED EVALUATIVE ADJECTIVES are FORBIDDEN outside of direct quotes "
    "from third-party sources. Banned list: strong, leading, premier, "
    "essential, successful, robust, compelling, prestigious, top, dominant, "
    "world-class, well-defined, well-managed, well-established, solid, "
    "vibrant, cutting-edge, innovative. The dimensions and the evidence "
    "describe the pattern; the analyst does NOT praise it.\n"
    "\n"
    "3. SUBJECT MUST BE THE PATTERN, NOT THE BRAND'S ESSENCE. Use "
    "grammatical subjects like 'the dimensions', 'the evidence', "
    "'self-description', 'external coverage', 'the scores'. Avoid 'the "
    "brand is', 'the brand has', 'X demonstrates Y', 'X has established Y'.\n"
    "\n"
    "4. CONDITIONAL LANGUAGE FOR INFERENCE. When stating what a tension "
    "means commercially or strategically, use 'may', 'could', 'tends to', "
    "'suggests', 'likely' — never 'is', 'demonstrates', 'proves'.\n"
    "\n"
    "5. PREFER NULL OVER FORCED TENSION. If no meaningful cross-dimensional "
    "tension exists in the evidence, return {\"tension\": null}. Do not "
    "invent tension to fill the slot.\n"
    "\n"
    "6. EVIDENCE ANCHOR FIRST. Start from a concrete evidence anchor before "
    "moving to strategic interpretation."
)


def _build_tensions_user_prompt(
    dimensions: list[DimensionEvidences],
    brand: str,
    analysis_date: str | None = None,
) -> str:
    score_lines = []
    evidence_lines = []
    for d in dimensions:
        score = "n/a" if d.score is None else f"{d.score:.0f}"
        score_lines.append(f"- {d.display_name}: {score}/100 ({d.verdict} · {d.verdict_adjective})")
        top = _format_evidences_for_prompt(d.evidences, limit=2)
        evidence_lines.append(f"* {d.display_name}:\n{top or '  (no evidence)'}")

    date_anchor = _date_anchor_clause(analysis_date)

    return f"""{date_anchor}

Brand: {brand}

Per-dimension scores:
{chr(10).join(score_lines)}

Top evidence per dimension:
{chr(10).join(evidence_lines)}

Identify ONE significant cross-dimensional TENSION if and only if one
genuinely exists in the evidence. Examples of valid tensions:
- Self-description versus external categorization diverge.
- High publishing frequency paired with low external resonance.
- Specific vocabulary in self-description but generic terms in third-party coverage.
- Visual consistency observable across surfaces while messaging varies between channels.

If a real tension exists, return 3-4 lines of prose in English with this
internal structure:
- Open with the OBSERVABLE PATTERN (what the dimensions and evidence
  show in concert). Cite a specific signal from at least one dimension.
- State the IMPLICATION in conditional language (may, could, suggests).
- Close with what kind of strategic QUESTION this pattern typically
  raises for teams in this configuration — do NOT prescribe a single
  answer; describe the question or trade-off space.

Keep the language specific to the evidence pool. Avoid generic praise or
consultant-style summary language.

FORBIDDEN PHRASES (will be rejected):
- "compelling story" / "well-defined identity" / "strong positioning"
- "X has successfully established Y"
- "X demonstrates Y" / "X projects Y"
- Any closed adjective from the banned list applied to the brand
  outside a third-party quote.
- Adopting the brand's self-description as an assertion (e.g. saying
  "X is the leading platform" when only the brand says so).

If no meaningful tension exists, return {{"tension": null}}.

Return JSON: {{"tension": "prose text"}} or {{"tension": null}}"""


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


def _resolve_analysis_date(date_str: str | None) -> str:
    """Return an ISO date (YYYY-MM-DD) for prompt injection."""
    if date_str:
        return str(date_str).split("T")[0].split(" ")[0].strip()
    from datetime import date
    return date.today().isoformat()


def _date_anchor_clause(analysis_date: str | None) -> str:
    """Prompt fragment that anchors the model's sense of now."""
    today = _resolve_analysis_date(analysis_date)
    return (
        f"Today's date is {today}. When evaluating any temporal claim "
        f"(founding dates, effective dates, 'recent', 'new', 'upcoming', "
        f"copyright years, version numbers tied to a year), treat this as "
        f"the current date, NOT your training cutoff. Anything dated on or "
        f"before {today} is past or present, never future."
    )
