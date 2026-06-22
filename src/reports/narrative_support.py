"""Pure helpers for Brand3 narrative generation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .derivation import DimensionEvidences, Evidence
from .experimental_perceptual_narrative import (
    PerceptualNarrativeHints,
    format_perceptual_hints_for_prompt,
)

log = logging.getLogger("brand3.reports.narrative")


def _build_synthesis_user_prompt(ctx) -> str:
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
2. CONTRADICTION: If evidence contains a contradiction between sources (e.g. brand says one thing, third parties say another), dedicate one finding to that contradiction with a title that names it.
3. FORBIDDEN PHRASES (will be rejected): "the brand should", "needs to", "must", "X positions itself successfully", "essential hub", "premier destination", anything from the closed-adjective list outside a third-party quote.
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
    if date_str:
        return str(date_str).split("T")[0].split(" ")[0].strip()
    from datetime import date
    return date.today().isoformat()


def _date_anchor_clause(analysis_date: str | None) -> str:
    today = _resolve_analysis_date(analysis_date)
    return (
        f"Today's date is {today}. When evaluating any temporal claim "
        f"(founding dates, effective dates, 'recent', 'new', 'upcoming', "
        f"copyright years, version numbers tied to a year), treat this as "
        f"the current date, NOT your training cutoff. Anything dated on or "
        f"before {today} is past or present, never future."
    )


def _default_analyzer():
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

