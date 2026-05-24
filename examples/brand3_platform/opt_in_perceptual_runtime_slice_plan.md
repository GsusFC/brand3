# Opt-In Compressed Perceptual Runtime Slice Plan

Generated: 2026-05-16
Status: implementation plan
Scope: experimental opt-in planning only

## Decision

Prepare a minimal opt-in runtime slice for compressed perceptual narrative findings, but do not implement it yet.

The slice should affect only findings by dimension, referred to in product/report language as §4 findings by dimension. In code, the relevant entry points are currently `generate_all_findings`, `generate_dimension_findings`, and `build_brand_dossier`.

## Guardrails

- No scoring changes.
- No global enablement.
- No report structure changes.
- No Visual Signature changes.
- No production prompt rewrite.
- No default runtime behavior change.
- No persistence requirement for lab experiments.
- Fallback must be identical to baseline when activation conditions fail.

## Current Runtime Boundary

The current runtime already has an opt-in perceptual path:

- `build_brand_dossier(... enable_perceptual_narrative=False)`
- `build_report_narrative_payload(... enable_perceptual_narrative=False)`
- `generate_all_findings(... enable_perceptual_narrative=False)`
- `build_perceptual_narrative_hints(dimension)`
- `format_perceptual_hints_for_prompt(hints)`

That path passes perceptual hints into findings generation. It does not change scoring, synthesis, tensions, Visual Signature, or renderer behavior.

The compressed slice should not replace this path. It should add one additional explicit opt-in mode after the raw perceptual path:

`baseline -> perceptual hints -> compressed perceptual findings`

## Proposed Runtime Shape

Add a future explicit flag only when implementation begins:

- `enable_perceptual_narrative=False`
- `enable_compressed_perceptual_narrative=False`

Rules:

- `enable_compressed_perceptual_narrative=True` has no effect unless `enable_perceptual_narrative=True`.
- If high-signal detection fails, return baseline findings.
- If confidence gating fails, return baseline findings.
- If compression validation fails, return raw perceptual findings only in lab mode; production opt-in should fall back to baseline.
- Public report reads should continue to prefer persisted narrative and should not trigger live LLM work.

## Safe Activation Conditions

All conditions must pass:

1. Explicit opt-in flag is true.
2. The target surface is findings by dimension only.
3. The run has enough evidence to support perceptual language.
4. The dimension is eligible for augmentation.
5. At least one direct or source-level evidence anchor exists for the dimension.
6. The evidence is not copy-only unless the finding explicitly remains copy-supported.
7. The generated text preserves at least one visible mechanism or source boundary.
8. The compressed finding does not introduce forbidden overreach patterns.
9. The output remains structurally compatible with `Finding(title, observation, implication, typical_decision, evidence_urls)`.

## High-Signal Detection Rules

High-signal means the dimension has enough evidence to support compressed perceptual language without importing assumptions.

Minimum rule:

- at least 2 evidence items in the dimension, or
- 1 evidence item plus a directly quoted concrete surface/detail, or
- repeated evidence from multiple source types across the run.

Preferred rule:

- at least 2 distinct evidence URLs;
- at least one quote or extracted detail;
- evidence contains surface mechanisms such as navigation, typography, image hierarchy, product objects, code content, templates, proof modules, service lists, reviews, screenshots, or source-stated interface details;
- the finding can name a signal before interpretation.

Fail high-signal detection when:

- evidence is empty;
- evidence is only generic marketing copy;
- no concrete quote/detail exists;
- the dimension only has score metadata;
- the signal would need to be imported from the perceptual registry rather than target evidence.

## Confidence Thresholds

Allowed:

- High confidence: direct visible evidence, direct source statement, repeated evidence across sections or URLs.
- Medium confidence: copy-supported reading with explicit source boundary; category-to-surface reading supported by concrete evidence.

Blocked from compression:

- Low confidence strategic intent.
- Inferred audience emotion.
- Trust, wellness, safety, therapeutic support, financial security, market leadership, or product efficacy without corroboration.
- Motion/cinematic claims without capture, sequence, or source-stated motion evidence.
- Any material marked weak, unverified, or requiring human review unless the output explicitly names that limitation.

## Dimensions Eligible For Augmentation

Initial eligible dimensions:

- `coherencia`: useful for claim/signal gap, system consistency, proof structure.
- `presencia`: useful for surface visibility, attention hierarchy, channel evidence.
- `percepcion`: useful for emotional temperature only when mechanism-bound.
- `diferenciacion`: useful for category-to-surface translation and template behavior.

Conditionally eligible:

- `vitalidad`: only when there is direct evidence of motion, publishing rhythm, interaction, update cadence, or concept-bearing movement.

## Dimensions Excluded Initially

Exclude any dimension or finding when:

- the evidence is copy-only and seeks to infer UX behavior;
- the category is wellness, health, finance, legal, safety, or security and the output cannot preserve explicit caution;
- the finding depends on internal strategy, intent, audience sophistication, cultural authority, or leadership;
- the dimension lacks concrete source anchors;
- the finding would mainly add style vocabulary rather than evidence.

## Fallback Behavior

Fallback must be boring and safe.

Fallback order:

1. If compressed mode is off: current baseline behavior.
2. If compressed mode is on but perceptual mode is off: current baseline behavior.
3. If high-signal detection fails: current baseline behavior.
4. If confidence gating fails: current baseline behavior.
5. If LLM or JSON parsing fails: current deterministic fallback.
6. If compression produces overreach: current baseline behavior in production opt-in; raw perceptual output may be shown only in lab comparison mode.

No fallback should alter scores, dimension verdicts, evidence URLs, report structure, persisted schema, or Visual Signature state.

## Overreach Suppression Rules

Reject or rewrite compressed findings containing:

- invented intentionality: seeks, intends, aims, wants, designed to, built to;
- unsupported emotional projection: makes users feel, creates trust, provides support;
- cinematic inflation without motion evidence: cinematic, filmic, choreographed, immersive journey;
- false sophistication language: premium, sophisticated, elevated, world-class, refined, polished unless quoted;
- weak evidence amplification: copy claim presented as product behavior;
- aesthetic hallucination: visual details not present in evidence;
- narrative over-binding: all, every, fully, resolves, unified, converges without evidence;
- tension fabrication: contrast invented to make prose stronger;
- generic premium projection.

Preferred suppression output:

- keep baseline finding;
- or keep the compressed finding only after replacing overreach with source-bound language;
- never silently assert a stronger claim.

## What Remains Baseline-Only

- Scores and scoring logic.
- Global synthesis.
- Cross-dimensional tension prose.
- Dimension verdicts.
- Evidence collection and source classification.
- Report rendering and template structure.
- Persisted public report reads unless an explicitly generated opt-in payload exists.
- Sparse, copy-only, low-signal, or sensitive findings that cannot preserve caution.

## What Stays Lab-Only

- Side-by-side baseline/raw/compressed comparison.
- Reviewer preference controls.
- Calibration logs.
- Unsafe overreach examples.
- Raw perceptual output when compression fails.
- Any run where human review is required before showing compressed prose.

## What Should Never Become Automatic

- Strategic intent inference.
- User emotion or therapeutic/support outcome claims.
- Trust, safety, financial, legal, medical, or security claims.
- Famous-brand reputation filling evidence gaps.
- Motion/cinematic interpretation without motion evidence.
- Perceptual registry examples treated as target-brand facts.
- Automatic replacement of baseline findings for all reports.

## Rollout Boundaries

Phase 0: planning only.

Current document. No code changes.

Phase 1: lab-only implementation.

Add explicit flag and generate paired baseline/perceptual/compressed outputs for reviewer comparison. No public report default.

Phase 2: private opt-in payload generation.

Allow compressed findings to be generated for selected high-signal runs and stored as experimental metadata, not official report truth.

Phase 3: limited partner review.

Expose compressed findings only where reviewers can compare against baseline and mark unsafe overreach.

No phase should activate global defaults without a separate decision record and test evidence.

## Monitoring Requirements

Track per run:

- activation flag state;
- high-signal pass/fail reason;
- dimension eligibility;
- confidence gating result;
- fallback reason;
- overreach suppression hits;
- reviewer preference where available;
- whether compressed text preserved evidence URLs;
- whether low-confidence material remained explicit.

Review metrics:

- compressed better / baseline better / mixed / unsafe overreach;
- failure mode frequency;
- sensitive-category caution failures;
- generic sophistication phrase recurrence;
- percentage of findings falling back to baseline.

## Rollback Conditions

Immediately disable compressed opt-in mode if:

- scores or dimension verdicts change;
- public reads trigger live LLM generation unexpectedly;
- Visual Signature output changes;
- compressed findings omit evidence boundaries for low-confidence material;
- sensitive categories generate unsupported user outcome claims;
- reviewer unsafe-overreach rate exceeds a small controlled threshold;
- fallback is not identical to baseline when gates fail;
- prompt output causes JSON parsing instability or report rendering errors.

## Test Requirements Before Implementation

Before code implementation, add tests for:

- flag off produces byte-equivalent baseline findings payload where feasible;
- compressed flag has no effect unless perceptual flag is also on;
- low-signal dimensions fall back to baseline;
- copy-only UX claims remain copy-supported or fall back;
- sensitive categories preserve explicit caution;
- scores and verdicts are unchanged;
- Visual Signature routes and outputs are unchanged;
- persisted public report reads do not call LLM;
- overreach terms are rejected or suppressed.

## Recommendation

Prepare implementation only as an explicit opt-in lab-first slice.

The first implementation should be small:

- one new opt-in flag;
- high-signal gating before hints;
- compression instructions only inside findings prompt or post-generation lab step;
- strict fallback to baseline;
- no renderer change;
- no scoring change;
- no global enablement.

The runtime slice is viable, but only if treated as a controlled editorial experiment, not a product default.
