# Brand3 Narrative Harness Phase 1 Boundary

Date: 2026-05-16

Scope: phase-boundary document only. No code, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, new fixtures, builder, runtime wiring, or LLM calls were added.

## Executive Boundary

Phase 1 proved that Brand3's narrative issue is measurable and narrower than a general "bad prompt" problem.

The report pipeline already has useful structure:

- evidence objects,
- source grouping,
- confidence,
- readiness/data quality,
- persisted report narrative,
- prompt-level editorial guardrails,
- separated `Finding` fields before rendering.

But it does not build an explicit entity-level composition state before writing or displaying findings. The result can be structurally valid and evidence-aware while still reading like assembled fragments.

Phase 1 should now be considered closed as a diagnostic phase. The next work should not add more checks casually. It should decide which measured failures justify a small Phase 2 composition contract.

## 1. What Phase 1 Accomplished

Phase 1 established a read-only Narrative Harness around existing Brand3 report narratives.

It produced:

- a cohesion diagnostic of the current report pipeline,
- a decision memo recommending harness-before-architecture,
- an offline payload-level harness,
- example diagnostics for representative payloads,
- a render-aware diagnostic surface,
- multi-report comparison,
- observation repetition family checks,
- a minimal `EntityNarrativeState` design memo,
- two offline `EntityNarrativeState` fixtures,
- a fixture-shape review.

The important shift is methodological: Brand3 now has a way to measure narrative cohesion risks before changing prompts, scoring, generation, rendering, or runtime behavior.

## 2. What Was Measured

Phase 1 measured two separate surfaces.

Payload-level risk:

- repeated sentence openings,
- generic strategic filler,
- unsupported prescription language,
- missing evidence URLs,
- unsafe self-description validation,
- safe attribution overuse,
- synthesis/tension lexical mismatch,
- observation repetition families.

Visible-render risk:

- visible repeated sentence openings,
- visible safe attribution overuse,
- visible generic strategic filler,
- visible evidence chip/link count,
- visible `Decision space` count,
- visible `Teams in this position typically` count,
- visible `The brand...` count,
- suppressed risks versus still-visible risks.

The main measured cases were:

- `builtwith_kit_com`: real persisted narrative issue.
- `netlify_snapshot_mock`: deterministic fallback/control case.
- `clean_control`: synthetic clean control.

Measured patterns:

| Case | Main issue | Evidence coverage issue | Render status |
|---|---|---|---|
| `builtwith_kit_com` | owned-claim attribution and corroboration-caveat repetition | 4 findings without evidence URLs | warning |
| `netlify_snapshot_mock` | fallback evidence-opening repetition | 2 findings without evidence URLs | warning |
| `clean_control` | none | 0 findings without evidence URLs | pass |

This matters because the Builtwith pattern is not universal, but the broader composition problem appears in more than one form.

## 3. What Was Improved At Render Level

Phase 1 included one contained rendering experiment before this boundary document.

The key render-level improvement was separating findings visually instead of flattening `observation + implication + typical_decision` through `finding.prose`.

Then conditional `Decision space` display suppressed clearly generic `typical_decision` language such as:

```text
teams in this position typically
```

For `builtwith_kit_com`, render-aware diagnostics showed:

- payload `teams in this position typically`: 9
- visible `teams in this position typically`: 0
- visible `Decision space`: 0

This improved visible report quality without changing:

- `Finding.prose`,
- persisted payload format,
- prompts,
- generation,
- scoring.

But this should not be mistaken for narrative repair. The payload still contains the same generic material. Rendering only changed what is exposed.

## 4. What Remains Unsolved

Phase 1 did not solve entity-level composition.

Still unsolved:

- owned-claim repetition across findings,
- fallback evidence-opening repetition,
- external corroboration caveat repetition,
- repeated observation openings,
- incomplete evidence URL coverage,
- missing entity consolidation before findings,
- contradiction prioritization,
- deciding when a caveat belongs once globally instead of inside every finding,
- deciding when decision framing belongs per finding, per dimension, or not at all.

The most important remaining issue is not the phrase itself. It is the absence of a shared narrative state that can govern repetition, evidence confidence, source ownership, and entity framing before prose is produced or displayed.

## 5. What Is Experimental Only

These artifacts remain experimental-only:

- `src/reports/narrative_harness.py`
- example diagnostics under `examples/reports/narrative_harness/`
- render-aware harness diagnostics,
- observation repetition family metrics,
- `examples/reports/narrative_harness/entity_state/*.entity_narrative_state.json`
- `EntityNarrativeState` fixture shape,
- compression candidates inside entity-state fixtures.

They are not production gates.

They do not:

- modify scores,
- modify prompts,
- generate report prose,
- change persisted `report_narrative`,
- block reports,
- call LLMs,
- integrate with Visual Signature,
- act as official records.

## 6. What Must Not Be Automated Yet

Do not automate `primary_tension` yet.

The Netlify fixture shows why: a payload can contain a tension-like sentence, but the supporting evidence may be too compact to promote it into entity-level state without human review.

Do not automate `compression_candidates` yet.

They are editorial hypotheses, not rewrite instructions.

Do not automate source ownership counts from the fixture shape.

Current `source_ownership_summary` values are `manual_estimate`. A real classifier would need its own design and tests.

Do not automate contradiction candidates yet.

Contradiction detection needs stronger evidence anchoring than phrase metrics.

Do not turn inactive fields into failures.

The Netlify fixture proves that absence is meaningful. A case can legitimately have no attribution overuse, no corroboration-caveat issue, no contradiction candidates, and no Decision Space content.

Do not create broad narrative quality scores.

Phase 1 supports warning families and budgets, not a universal prose quality score.

## 7. Conditions That Would Justify A Future Builder

A future `EntityNarrativeState` builder becomes justified only when these conditions are met:

1. At least three to five real persisted report narratives have been audited, not only mocks or controls.
2. The same small field set proves useful across different failure types.
3. Required versus optional fields are defined.
4. Source ownership can be estimated deterministically with acceptable false-positive risk.
5. Evidence URL coverage can be computed directly from payload/dossier structures.
6. Repetition budgets can be derived without subjective interpretation.
7. Primary entity signal can be built from explicit metadata and source surfaces without inferring strategy.
8. Tension and contradiction fields remain review-gated or are excluded from the first builder.

The first builder, if created, should produce diagnostic state only. It should not rewrite prose, select prompts, or affect report output.

## 8. Conditions That Would Justify Prompt Changes

Prompt changes become justified when the harness shows repeated failures that are clearly generation-side, not rendering-side.

Good candidates:

- repeated `The brand describes itself...`,
- repeated `based only on self-description`,
- repeated `no external corroboration`,
- repeated fallback evidence openings,
- generic `typical_decision` outputs that remain useful but need less formulaic language.

Prompt changes should wait until:

- the repetition family is measured across several real reports,
- render suppression is ruled out as sufficient,
- the desired replacement behavior is specified,
- tests can detect regression,
- the change does not weaken evidence caution.

Prompt changes should not try to solve:

- source ownership classification,
- entity ambiguity,
- contradiction priority,
- evidence URL absence,
- runtime fallback behavior.

Those need composition or data-layer work.

## 9. Conditions That Would Justify Runtime Integration

Runtime integration is premature now.

It becomes defensible only when:

1. The harness has stable false-positive behavior across real reports.
2. A minimal builder exists and is tested offline.
3. The builder output is deterministic and side-effect free.
4. The integration is opt-in or diagnostic-only at first.
5. Public report reads remain deterministic and fast.
6. No report is blocked by warning-only checks.
7. Scoring remains unchanged.
8. Visual Signature remains isolated.
9. Persisted `report_narrative` format remains compatible.
10. Rollback is trivial.

The safest first runtime use would be a diagnostic attachment or lab-only display, not prose mutation.

## 10. Recommended Phase 2 Direction

Phase 2 should not begin with a builder or prompt rewrite.

Recommended sequence:

1. Collect more real persisted narratives.

   The current local set had only one true persisted narrative. More real cases are needed before architecture hardens.

2. Create one additional offline entity-state fixture from a healthier report.

   The next fixture should have stronger evidence URL coverage and less fallback language. It should test whether the shape can represent a relatively healthy narrative state without forcing warnings.

3. Define a minimal `EntityNarrativeState` contract.

   Separate required fields from conditional fields.

   Stable core:

   - `status`
   - `metadata`
   - `primary_entity_signal`
   - `entity_aliases.observed_related_surfaces`
   - `owned_claim_density`
   - `source_ownership_summary`
   - `repeated_opener_budget`
   - `fallback_language_budget`
   - `evidence_url_coverage`
   - `decision_space_mode`

   Conditional layer:

   - `attribution_budget`
   - `corroboration_caveat_budget`
   - `primary_tension`
   - `contradiction_candidates`
   - `compression_candidates`

4. Keep the harness warning-only.

   The harness should remain an instrument, not an editorial judge.

5. Only then consider a deterministic offline builder.

   The builder should emit state, not prose.

6. After builder validation, consider narrow prompt refinement.

   Start with measured repetition families, not broad voice rewrites.

## Phase 1 Closing Position

Brand3 has enough evidence to say:

- the narrative problem is real,
- it is measurable,
- rendering can hide some symptoms,
- repeated observation and attribution families remain,
- the future direction is entity-level composition,
- but automation is still premature.

The correct boundary is:

```text
Phase 1 measured the problem.
Phase 2 should stabilize the state contract.
Runtime should wait.
```
