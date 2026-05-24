# Brand3 Scoring Prompt Refinement Plan

Generated: 2026-05-14
Scope: planning only

This plan converts the scoring narrative audit into staged prompt and fallback rules. It does not change prompts, scoring logic, rubric dimensions, or the renderer yet.

## Goal

Make report prose more diagnostic and less repetitive by tightening the existing narrative prompts, fallback text, and output contracts.

## Prompt Targets

Current prompt entry points in `src/reports/narrative.py`:

- `generate_synthesis(context)` via `_SYNTHESIS_SYSTEM` and `_build_synthesis_user_prompt`
- `generate_dimension_findings(dim, brand)` via `_FINDINGS_SYSTEM` and `_build_findings_user_prompt`
- `generate_tensions(dimensions, brand)` via `_TENSIONS_SYSTEM` and `_build_tensions_user_prompt`
- fallback prose:
  - `_fallback_synthesis`
  - `_fallback_findings`

These are the primary places to refine first.

## Low-Risk Changes First

### 1) Tighten Synthesis Prompt

Target:

- `_SYNTHESIS_SYSTEM`
- `_build_synthesis_user_prompt`

Changes to make later:

- forbid score-first openings explicitly
- require one concrete evidence anchor in the opening sentence
- require a named pattern, not a praise phrase
- require one real tension or explicit no-tension statement
- reduce generic strategic phrases such as "clear message" and "strong presence"

Expected effect:

- less score-led prose
- more evidence-linked opening
- less consultant-style padding

### 2) Tighten Findings Prompt

Target:

- `_FINDINGS_SYSTEM`
- `_build_findings_user_prompt`

Changes to make later:

- preserve the observation / implication / typical_decision structure
- forbid closed evaluative adjectives unless directly quoted
- require dimension-specific observations rather than one-size-fits-all "available evidence"
- make single-source / thin-evidence limitations explicit
- prevent the fallback from becoming the same sentence for every dimension

Expected effect:

- more useful per-dimension findings
- fewer generic "consolidated evidence" blocks
- clearer evidence limits

### 3) Tighten Tension Prompt

Target:

- `_TENSIONS_SYSTEM`
- `_build_tensions_user_prompt`

Changes to make later:

- keep null as a valid and preferred outcome when no real tension exists
- require a concrete evidence delta when a tension is produced
- ban generic "compelling story" / "strong positioning" phrasing
- keep the strategic question space narrow and evidence-based

Expected effect:

- fewer forced tensions
- fewer inflated strategic statements

### 4) Refine Fallback Text

Target:

- `_fallback_synthesis`
- `_fallback_findings`

Changes to make later:

- make fallback paragraphs dimension-specific
- avoid the repeated phrase "available evidence"
- avoid "automatic synthesis unavailable" as a generic ending
- keep the score out of the opening sentence
- be honest about missing evidence or missing signal types

Expected effect:

- better honesty when LLM output is unavailable
- less repetition across degraded runs

## Medium-Risk Changes Later

These changes improve the narrative system, but they are structurally broader than prompt edits.

### 1) Reduce Duplicate Narrative Surface

Target:

- `src/reports/templates/report.html.j2`
- `src/reports/derivation.py`

Future change:

- reduce the repeated prose rendered in both current-reading and synthesis tabs
- make the tabs intentionally different in function:
  - one technical / current reading
  - one narrative / synthesis

Expected effect:

- less duplication of the same story in two places
- clearer reader experience

### 2) Split Narrative Into Distinct Signal Layers

Target:

- `src/reports/narrative.py`

Future change:

- separate observation, implication, tension, and recommendation-space into stronger contracts
- keep each layer from collapsing into the others

Expected effect:

- less generic prose
- better structure for future reuse

### 3) Make Fallbacks Dimension-Specific

Target:

- `src/reports/narrative.py`

Future change:

- fallback copy should explain what signal failed for each dimension
- each dimension should have a distinct fallback style

Expected effect:

- more precise failure modes
- easier debugging

## Prompt Changes By File / Function

### `src/reports/narrative.py`

Functions to refine later:

- `_SYNTHESIS_SYSTEM`
- `_build_synthesis_user_prompt`
- `_FINDINGS_SYSTEM`
- `_build_findings_user_prompt`
- `_TENSIONS_SYSTEM`
- `_build_tensions_user_prompt`

Fallback helpers to refine later:

- `_fallback_synthesis`
- `_fallback_findings`

### `src/reports/templates/report.html.j2`

No prompt change here yet. This file is a future structural follow-up only.

Planned future role:

- reduce duplicated prose between the tabs
- keep current-reading and synthesis visually distinct

## Dimension-Specific Prompt Rules

### Coherencia

- require explicit touchpoints
- distinguish visual, message, tone, and cross-channel signals
- avoid generic "clear message" wording

### Presencia

- separate owned web presence from external discoverability
- mention missing social or directory signals explicitly

### Percepcion

- separate awareness, sentiment, controversy, and review surface
- avoid collapsing sparse mentions into a generic positive/negative claim

### Diferenciacion

- require ownable vocabulary and competitor compression language
- keep "strong positioning" out unless evidence truly supports it

### Vitalidad

- separate recency, cadence, momentum, and lifecycle stage
- avoid life/death metaphors unless the evidence is strong

## Validation Method

Use the existing sample reports as the before/after comparison set:

- `tests/snapshots/report-netlify-light.html`
- `output/reports/manual-preview.html`
- `output/reports/manual-preview-real.html`
- `output/reports/manual-preview-real-actual.html`
- `output/reports/charms-real.html`
- `output/reports/charms-real-actual.html`
- `output/reports/elevenlabs/13-20260430-230043/report.dark.html`
- `output/reports/floc/9-20260430-064008/report.light.html`
- `output/reports/a16z/42-20260419-144049/report.light.html`

Validation steps after prompt edits:

1. Re-render a small set of sample reports.
2. Compare the synthesis opening line against the old score-led template.
3. Check whether each dimension now names a more specific evidence pattern.
4. Check whether fallback text is dimension-specific and non-repetitive.
5. Check whether the report no longer repeats the same summary twice.

## Success Criteria

- synthesis no longer opens with the score
- findings stop defaulting to generic "available evidence"
- tensions are only produced when real evidence supports them
- fallback prose is honest and dimension-aware
- sample reports sound more diagnostic and less consultant-like
