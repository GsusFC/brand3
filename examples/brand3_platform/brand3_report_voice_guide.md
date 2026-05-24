# Brand3 / FLOC* Report Voice Guide

Generated: 2026-05-14
Scope: documentation only

This guide turns the scoring narrative audit into writing rules for the report voice. It does not change prompts, scoring logic, dimensions, or the renderer.

## Voice Goal

Brand3 / FLOC* reports should sound like a precise diagnostic of a brand surface, not a generic brand-strategy memo.

Desired voice:

- concise
- diagnostic
- observation-first
- tension-aware
- evidence-linked
- specific
- perceptual

Undesired voice:

- score-led
- promotional
- consultant-sounding
- overconfident relative to evidence
- literary without diagnostic gain

## Core Voice Rules

1. Start with what is observable, not with the score.
2. Name the actual pattern, not a generic positive impression.
3. Separate observation from implication.
4. Use tension language only when evidence really supports a tension.
5. Prefer concrete signals, pages, quotes, channels, and mismatches over abstract branding language.
6. Keep fallback language honest and specific about what is missing.

## Forbidden Phrases

Avoid these phrases unless they appear inside a direct third-party quote:

- clear message
- strong presence
- differentiated strategy
- well-defined identity
- sophisticated platform ambition
- the available sources point in the same direction
- automatic synthesis unavailable
- available evidence
- the brand demonstrates
- the brand is

Also avoid these structural habits:

- opening with `score / strongest / weakest / data quality`
- ending every paragraph with a generic caveat
- repeating the same summary sentence in multiple sections
- using praise words as if they were evidence

## Preferred Sentence Structures

Use sentence shapes like these:

- `The evidence shows X across Y, while Z remains limited.`
- `Self-description emphasizes X; external coverage compresses it into Y.`
- `This may indicate ...`
- `That leaves a strategic question around ...`
- `The pattern is visible in ...`

Prefer short, direct sentences over ornate prose. When possible:

- observation first
- implication second
- tension third

## Observation / Implication / Tension Model

### Observation

State only what is visible in the evidence.

Examples:

- `The website and external coverage both point to a builder-oriented product.`
- `The brand describes itself in platform language, but third-party mentions simplify it to a narrower tool.`

### Implication

Use conditional language only.

Examples:

- `This may indicate that the category story is not yet fully stable.`
- `That could leave the brand easier to compress into a competitor-shaped mental model.`

### Tension

Use only when there is a real contradiction, mismatch, or trade-off.

Examples:

- `Main tension: strong owned differentiation, but weaker external recognition.`
- `Main tension: active publishing, but limited evidence of market pull.`

If there is no meaningful tension, do not invent one.

## Dimension-Specific Writing Rules

### Coherencia

- Describe consistency or divergence across touchpoints.
- Name the specific touchpoints: web, social, press, visual identity, tone.
- Do not drift into generic praise of "clarity".

Preferred:

- `visual language stays aligned across surfaces`
- `self-description diverges from third-party framing`

Avoid:

- `clear message`
- `coherent brand identity` unless the evidence is very explicit

### Presencia

- Describe discoverability and footprint, not just whether the website exists.
- Separate owned web presence from broader discoverability.
- Name missing channels or thin channels explicitly.

Preferred:

- `owned site is live, but external footprint is shallow`
- `social / directory reach is limited`

Avoid:

- `strong presence`
- `the brand is easy to find` without source support

### Percepcion

- Separate awareness, sentiment, controversy, and review surface.
- Say whether the evidence is sparse, mixed, or concentrated in niche coverage.
- Do not compress everything into one sentiment adjective.

Preferred:

- `mentions are sparse and concentrated in niche sources`
- `coverage is positive but thin`
- `controversy is absent in the current evidence pool`

Avoid:

- `positive perception`
- `mixed reception` without naming what is mixed

### Diferenciacion

- This is the most strategic dimension, but it should still stay evidence-led.
- Name the ownable vocabulary, the generic language, and the competitor compression.
- Keep the tension concrete: ownable thesis versus market flattening.

Preferred:

- `the brand uses ownable category language`
- `third-party coverage compresses the offer into a narrower tool`
- `competitors share too much of the vocabulary`

Avoid:

- `clear, differentiated strategy`
- `strong positioning`

### Vitalidad

- Describe cadence, recency, and momentum separately when possible.
- Do not collapse activity into a life/death metaphor unless the evidence is very strong.
- Prefer `building`, `maintaining`, `slowing`, `quiet`, `recent`, `inactive`.

Preferred:

- `recent publishing exists, but cadence is irregular`
- `activity looks maintained rather than expanding`

Avoid:

- `alive`
- `dead`
- `brand is building` without evidence

## Fallback Text Rules

Fallback prose should be honest, short, and dimension-specific.

Rules:

1. Say what failed or what is missing.
2. Do not pretend a generic observation is a real synthesis.
3. Do not repeat the same fallback sentence across all dimensions.
4. Keep the score out of the opening line.
5. Mention the evidence limitation explicitly.

Preferred fallback patterns:

- `Synthesis unavailable for this run; the available evidence is too thin to support a stronger reading.`
- `Coherencia fallback: visual evidence is missing, so the reading is limited to message and channel signals.`
- `Percepcion fallback: mention volume is too sparse to support a reliable sentiment reading.`

Avoid fallback patterns like:

- `Available evidence`
- `Automatic synthesis unavailable`
- `The available sources point in the same direction`

## Before / After Rewrites

### Example 1: Score-led summary

Before:

`Example scores 72/100 (band B). Strongest dimension: Presence (82/100). Weakest dimension: Differentiation (54/100). Data quality: degraded.`

After:

`The brand is visible on its own site, but the external reading is less stable. Differentiation is the main pressure point: the offer is present, yet the market still compresses it into a narrower category.`

### Example 2: Generic positive synthesis

Before:

`Netlify presents a clear message backed by consistent external coverage.`

After:

`Netlify’s own language and external coverage both point to a builder-facing product, but the market still simplifies the story to serverless infrastructure.`

### Example 3: Fallback block

Before:

`Available evidence.`

After:

`Perception is not reliable here: the mention pool is too sparse to support a stable sentiment reading.`

### Example 4: Consultant tone

Before:

`This creates a tension between the company's sophisticated platform ambition and a more narrow, tool-focused market understanding.`

After:

`The tension is narrower and more useful: the product is framed as a platform internally, while the market still repeats tool-level language.`

## Validation Set

Use the current sample reports as reference material for later rewriting:

- `tests/snapshots/report-netlify-light.html`
- `output/reports/manual-preview.html`
- `output/reports/manual-preview-real.html`
- `output/reports/manual-preview-real-actual.html`
- `output/reports/charms-real.html`
- `output/reports/charms-real-actual.html`
- `output/reports/elevenlabs/13-20260430-230043/report.dark.html`
- `output/reports/floc/9-20260430-064008/report.light.html`
- `output/reports/a16z/42-20260419-144049/report.light.html`

The target is not to make every report sound different by style alone. The target is to make the diagnostic signal sharper and the wording less repetitive.
