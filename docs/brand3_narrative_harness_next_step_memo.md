# Brand3 Narrative Harness Next Step Memo

Date: 2026-05-16

Scope: decision memo only. No runtime, scoring, prompt, report renderer, schema, or Visual Signature changes were made.

Note: references to `Finding`, `Finding.prose`, and `typical_decision` in this memo are about report findings, not the TLDR block contract.

## Recommendation

Build the offline Narrative Harness first. Do not build `EntityNarrativeState` as the next implementation step.

The repository already has enough structured inputs to audit narrative quality without touching generation:

- `build_report_base(...)` creates a deterministic dossier from a run snapshot.
- `build_brand_dossier(...)` applies persisted or generated narrative overlays.
- `build_report_narrative_payload(...)` serializes report narrative into a stable payload.
- `Finding` already separates `observation`, `implication`, `typical_decision`, and `evidence_urls`.
- Public report reads already prefer persisted `report_narrative` and avoid live LLM calls.

The missing information is empirical: which narrative failures actually appear, how often, and under what evidence conditions. An offline harness gives Brand3 that measurement layer before committing to a new entity-state abstraction.

## Why Harness Before EntityNarrativeState

`EntityNarrativeState` is likely the right architectural direction later, but it should not be designed first.

Reasons:

1. The current failure modes are plausible but not yet measured across stored narratives.
2. A premature entity-state model risks encoding assumptions about failures rather than evidence from reports.
3. The current pipeline has clear non-invasive inspection points.
4. The persisted `report_narrative` format is already a natural audit target.
5. The harness can produce concrete examples that later define the fields of `EntityNarrativeState`.

Grounding:

- `build_report_narrative_payload(...)` already returns `synthesis_prose`, `tensions_prose`, and `findings_by_dimension` in `src/reports/dossier.py`.
- `build_brand_dossier(...)` already decides whether to use persisted narrative or generate a fresh overlay in `src/reports/dossier.py`.
- The public route uses `_WebReportNarrativeFallback`, confirming public report reads should stay deterministic and not call LLM generation live in `web/routes/report.py`.

## Rejected Alternatives

### Rewrite prompts first

Rejected for now.

The prompts already contain substantial editorial discipline:

- no echo-chamber
- observation vs implication separation
- no singular prescriptions
- no closed evaluative adjectives
- evidence anchor first

These are in `src/reports/narrative.py`, especially the synthesis and findings prompt sections.

Prompt tuning may still be needed later, but changing prompts before measuring failures would make it harder to distinguish architecture problems from wording problems.

### Build EntityNarrativeState immediately

Rejected for now.

The diagnostic identified the absence of entity-level state, but the repo does not yet have a measured failure corpus showing which entity fields matter most. The harness should tell us whether the first state object needs to prioritize contradiction, evidence weighting, repetition, source ownership, entity drift, or synthesis/tension mismatch.

### Add runtime validation now

Rejected.

The report path is currently production-sensitive:

- report narratives can be persisted during analysis in `src/services/brand_service.py`
- public report reads render from snapshots through `web/routes/report.py`
- `ReportRenderer.render(...)` delegates to `build_brand_dossier(...)`

Adding a hard runtime gate before the harness is calibrated could block or degrade reports for reasons that are not yet validated.

### Change report template rendering now

Rejected.

The template currently renders `finding.prose`, which concatenates separated fields. That likely contributes to paragraph sameness. But the next step should identify the failure rate and shape first, not redesign rendering.

## Proposed Harness Scope

The first Narrative Harness should be read-only and offline.

It should inspect existing report narrative plus the base dossier data and emit a diagnostic JSON. It should not rewrite, block, score, persist official records, or change report output.

Initial checks:

- repeated sentence openings
- generic strategic filler
- entity drift
- weak evidence binding
- unsupported recommendations
- overuse of self-description as external validation
- contradiction smoothing
- synthesis/tension mismatch

Out of scope:

- rewriting prose
- changing prompts
- changing scoring
- changing report rendering
- enabling perceptual narrative globally
- integrating Visual Signature
- adding production persistence

## Proposed File Locations

Recommended module:

```text
src/reports/narrative_harness.py
```

Reason: the harness operates on report dossiers and `report_narrative` payloads, so it belongs near `src/reports/dossier.py`, `src/reports/narrative.py`, and `src/reports/derivation.py`.

Recommended tests:

```text
tests/test_reports_narrative_harness.py
```

Reason: existing report narrative tests already live in:

- `tests/test_reports_narrative.py`
- `tests/test_reports_dossier.py`
- `tests/test_reports_renderer.py`
- `tests/test_reports_snapshot.py`

Optional later CLI, not first pass:

```text
scripts/audit_report_narrative.py
```

Reason: a CLI may be useful for running against local SQLite snapshots, but the first pass should be a pure module with tests.

## Proposed Inputs

The harness should accept either:

```python
audit_report_narrative_payload(
    payload: dict,
    *,
    base_dossier: dict | None = None,
) -> dict
```

or:

```python
audit_report_dossier(dossier: dict) -> dict
```

Smallest useful path:

1. Use a `report_narrative` payload as the primary narrative input.
2. Use `base_dossier` or rendered dossier context as supporting context when available.

Existing input structures to reuse:

- `report_narrative` payload:
  - produced by `build_report_narrative_payload(...)`
  - contains `synthesis_prose`, `tensions_prose`, `findings_by_dimension`
- report dossier:
  - produced by `build_brand_dossier(...)`
  - contains `brand`, `score`, `evaluation`, `dimensions`, `sources`, `editorial_policy`, `presentation_policy`
- base context:
  - produced by `build_report_base(...)` and `build_report_context_from_base(...)`
- `Finding` fields:
  - `title`
  - `observation`
  - `implication`
  - `typical_decision`
  - `evidence_urls`

## Proposed Output Contract

Smallest useful diagnostic JSON:

```json
{
  "version": 1,
  "status": "warning",
  "summary": {
    "total_checks": 8,
    "passed": 3,
    "warnings": 5,
    "errors": 0
  },
  "checks": [
    {
      "check_id": "repeated_sentence_openings",
      "severity": "warning",
      "status": "fail",
      "message": "Repeated opener detected across findings.",
      "evidence": [
        {
          "path": "findings_by_dimension.presencia[0].observation",
          "excerpt": "The brand says..."
        }
      ]
    }
  ],
  "metrics": {
    "sentence_opening_counts": {},
    "generic_phrase_counts": {},
    "findings_count": 0,
    "findings_without_evidence_urls": 0
  }
}
```

Recommended top-level fields:

- `version`
- `status`
- `summary`
- `checks`
- `metrics`
- `input_metadata`

Keep the first output factual and mechanical. Do not produce an editorial rewrite.

## Safe Invariants Now

These are safe to enforce as testable failures in the harness module because they do not require semantic judgment or live model interpretation.

### JSON shape

The harness must always return valid structured data with `version`, `status`, `summary`, `checks`, and `metrics`.

### Evidence URL allowlist awareness

If a finding has `evidence_urls`, the harness can check that they are strings and optionally compare them against known dossier/source URLs when provided.

This aligns with existing `_validate_urls(...)` behavior in `src/reports/narrative.py`.

### Repeated sentence openings

Safe as a warning/error threshold because it is syntactic.

Example:

- more than two findings beginning with the same normalized first 3-5 words

### Generic phrase counts

Safe to count. First pass should warn, not fail production.

Examples:

- `the brand demonstrates`
- `strong positioning`
- `compelling`
- `robust`
- `world-class`
- `teams in this position typically`

### Unsupported prescription language

Safe to flag direct prescriptive phrases:

- `the brand should`
- `needs to`
- `must`
- `the right move is`

This is consistent with prompt rules in `src/reports/narrative.py`.

### Missing evidence URLs

Safe to warn when a finding has substantive observation text and no `evidence_urls`.

Do not hard-fail yet because tests show existing fixtures sometimes use empty evidence URL lists.

Grounding:

- `tests/test_reports_dossier.py` creates findings with empty `evidence_urls`.
- The current code accepts those payloads.

## Warning-Only Checks First

These checks require more judgment and should start as warnings.

### Entity drift

Warning only.

Detecting unsupported named entities is useful, but false positives are likely without a proper entity extractor and source-aware allowlist.

### Weak evidence binding

Warning only.

A finding may be evidence-bound through an observation quote even if `evidence_urls` is empty in older payloads. Treat as warning until the narrative payload contract is tightened.

### Overuse of self-description as external validation

Warning only.

The prompt intentionally permits “the brand says/describes itself...”. The harness should distinguish safe attribution from unsafe validation, but that requires careful phrase patterns.

### Contradiction smoothing

Warning only.

This requires detecting contradiction candidates in source data and checking whether they survive into `tensions_prose` or findings. The first version should flag likely candidates, not fail.

### Synthesis/tension mismatch

Warning only.

The synthesis prompt already asks for coherence with §5 tension, but deterministic verification is hard unless the tension has a normalized label. First version can compare lexical overlap and key phrase reuse, but should not enforce strict failure.

## Minimal Tests

Create `tests/test_reports_narrative_harness.py`.

First tests should cover pure functions only. No LLM, no DB, no web app.

Recommended tests:

1. `test_harness_returns_stable_shape`
   - Given a minimal persisted `report_narrative` payload, returns `version`, `status`, `summary`, `checks`, `metrics`.

2. `test_repeated_sentence_openings_are_flagged`
   - Payload with three findings starting with “The brand says...” produces a repeated opener warning.

3. `test_generic_filler_is_counted`
   - Payload containing “strong positioning” or “compelling” produces a generic phrase warning.

4. `test_unsupported_prescription_is_flagged`
   - Payload containing “the brand should...” or “must...” produces an unsupported recommendation warning.

5. `test_missing_evidence_urls_warns_not_errors`
   - Payload with observation text and empty `evidence_urls` produces warning severity, not hard error.

6. `test_synthesis_tension_mismatch_warns_when_both_exist`
   - Payload with unrelated `synthesis_prose` and `tensions_prose` produces a mismatch warning.

7. `test_clean_payload_passes_without_errors`
   - A small payload with varied openings, evidence URLs, and conditional language should produce no errors.

Existing fixtures to reuse:

- `_sample_snapshot()` from `tests/test_reports_renderer.py`
- persisted narrative examples in `tests/test_reports_dossier.py`
- persisted public narrative setup in `tests/test_web_app.py`
- `NETLIFY_SNAPSHOT` and snapshot renderer tests in `tests/test_reports_snapshot.py`

Do not depend on `tests/snapshots/*.html` for first harness tests. HTML snapshots are useful later for rendered-output review, but the harness should operate below the template layer first.

## Minimal Implementation Plan

1. Add `src/reports/narrative_harness.py`.
2. Define a pure `audit_report_narrative_payload(payload, *, base_dossier=None)` function.
3. Normalize narrative text from:
   - `synthesis_prose`
   - `tensions_prose`
   - each finding `title`
   - each finding `observation`
   - each finding `implication`
   - each finding `typical_decision`
4. Add simple check functions:
   - repeated openers
   - generic phrase counts
   - unsupported prescription phrases
   - missing evidence URL warnings
   - self-description validation patterns
   - synthesis/tension lexical mismatch
5. Add unit tests only.
6. Do not call the harness from `build_brand_dossier(...)`.
7. Do not call the harness from `ReportRenderer`.
8. Do not persist harness output.
9. Optionally document a later CLI in the module docstring, but do not add it yet.

## Implementation Risks

### False positives

Phrase matching can over-flag legitimate prose. This is why most semantic checks should start as warnings.

### Making the harness another style cop

The purpose is not prettier prose. The purpose is evidence binding, entity stability, and narrative cohesion.

### Tight coupling to current prompt artifacts

If the harness only checks phrases currently produced by prompts, it may become stale after prompt changes. Keep check IDs conceptual, not prompt-specific.

### Penalizing necessary caution language

Brand3 needs conditional language. The harness should flag repetition and unsupported claims, not punish every use of `may`, `could`, or `suggests`.

### Blocking valid thin reports

Weak or thin evidence should be readable as thin evidence. The harness must not assume that all warnings imply a failed report.

### Runtime creep

The largest architectural risk is accidentally wiring the harness into production reads too early. Keep it offline until calibrated.

## Existing Assets We Can Reuse

### Code objects

- `build_report_base(...)` from `src/reports/derivation.py`
- `build_report_context_from_base(...)` from `src/reports/derivation.py`
- `build_brand_dossier(...)` from `src/reports/dossier.py`
- `build_report_narrative_payload(...)` from `src/reports/dossier.py`
- `Finding` from `src/reports/narrative.py`

### Tests and fixtures

- `tests/test_reports_dossier.py`
  - persisted narrative payload shape
  - rich narrative serialization
  - persisted narrative without LLM
- `tests/test_reports_renderer.py`
  - `_sample_snapshot()`
- `tests/test_reports_derivation.py`
  - publishable and processed snapshot builders
  - evidence/readiness/editorial policy expectations
- `tests/test_web_app.py`
  - persisted public `report_narrative` used by `/r/{token}`
- `tests/test_reports_snapshot.py`
  - rendered Netlify report snapshots

### Documentation

- `docs/brand3_narrative_cohesion_diagnostic.md`
- `docs/brand3_system/report_generation.md`
- `examples/brand3_platform/scoring_narrative_pipeline_audit.md`
- `examples/brand3_platform/scoring_report_voice_audit.md`

## Explicit Non-Goals

Do not:

- change scoring
- change prompts
- change report rendering
- change `Finding.prose`
- split observation/implication rendering in the template
- add `EntityNarrativeState` yet
- block report generation
- alter persisted `report_narrative` format
- modify Visual Signature Phase Zero, Phase One, or Phase Two
- enable perceptual narrative globally
- add Notion dependency
- add production persistence for harness diagnostics
- call LLMs from the harness
- run the harness in public report reads

## Answer to the Main Question

Yes, the proposed direction is the right next step.

Build the offline Narrative Harness first because it is the smallest move that increases architectural intelligence without changing runtime behavior. It gives Brand3 a measurable failure map. That map should then define the first useful `EntityNarrativeState`.

The harness should live under `src/reports/`, consume `report_narrative` payloads and optional dossier context, emit diagnostic JSON, and start with mostly warning-level checks. Only mechanical invariants should be strict at first.

The next architectural decision after this should be based on harness results, not intuition.
