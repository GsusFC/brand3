# Brand3 Phase 2 Synthesis: EntityNarrativeState Readiness

Date: 2026-05-16

Scope: synthesis memo only. No code, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, fixtures, builder, or runtime behavior were changed.

## Executive Decision

The minimal `EntityNarrativeState` contract is now ready for an offline builder prototype.

It is not ready for runtime integration.

It is not ready to rewrite prompts.

It is not a scoring or Visual Signature layer.

The Phase 2 audits show a stable pattern across three good-data runs:

```text
good evidence collection
but uneven finding-level evidence binding
plus repeated safe attribution and corroboration caveats
```

LaunchDarkly, Iris, and Watermelon all had good data quality, reliable scores, active LLM narrative generation, and more than 20 evidence items. Yet all three generated warning-level narratives with repeated caveats and missing evidence URLs inside §4 findings.

That means the issue is no longer speculative. Brand3 needs an offline composition-state builder that measures the entity/narrative state before any prompt or runtime change.

## Phase 2 Evidence Matrix

| Metric | LaunchDarkly | Iris | Watermelon |
|---|---:|---:|---:|
| score | 77.6 | 75.8 | 77.7 |
| data quality | good | good | good |
| evidence total | 28 | 24 | 26 |
| payload warnings | 5 | 6 | 5 |
| findings | 14 | 14 | 14 |
| findings without evidence URLs | 7 | 6 | 6 |
| safe attribution total | 13 | 15 | 9 |
| external corroboration caveat family | 18 | 20 | 16 |
| fallback evidence family | 9 | 10 | 8 |
| generic `teams in this position typically` | 9 | 14 | 11 |
| visible evidence chips | 10 | 13 | 13 |
| visible still-visible risks | 7 | 7 | 7 |

This is enough signal to move from manual fixture exploration to an offline builder prototype.

## 1. Stable Failure Pattern

The stable pattern is not low-quality data.

All three candidates collected enough evidence for a reliable audit:

- LaunchDarkly: 28 evidence items.
- Iris: 24 evidence items.
- Watermelon: 26 evidence items.

The stable failure is local narrative composition:

- findings lack evidence URLs even when the run has evidence,
- self-description caveats repeat per finding,
- `no external corroboration` repeats per finding,
- `the evidence pool` repeats per finding,
- `teams in this position typically` repeats in payload,
- rendering suppresses decision-space repetition but not observation-level repetition.

In short:

```text
the pipeline has evidence,
but §4 findings do not consistently bind that evidence
or compose uncertainty at entity level.
```

## 2. Evidence-Binding / Data-Contract Issues

These failures are primarily evidence-binding or data-contract issues:

### Findings without evidence URLs

Repeated across all three Phase 2 runs:

- LaunchDarkly: 7 of 14 findings.
- Iris: 6 of 14 findings.
- Watermelon: 6 of 14 findings.

Pattern:

- `coherencia` and `diferenciacion` repeatedly carry no finding-level evidence URLs.
- `percepcion`, `presencia`, and `vitalidad` are better grounded.

This suggests the narrative generation contract can produce evidence-aware prose without attaching evidence URLs for some dimensions.

### Global evidence not used locally

All three runs had substantial evidence, but findings still say:

```text
based only on self-description
no external corroboration in the evidence pool
```

That may be true for the specific finding, but without a state object, the report repeats the caveat rather than expressing it once as a local evidence limitation.

### Evidence source ownership is not consolidated

The system sees owned and third-party evidence at run level, but the narrative lacks a compact source-ownership summary before findings are written.

This is why a run can have strong third-party discovery and still produce local findings that sound as if corroboration is globally absent.

## 3. Prompt-Level Issues

Some failures are prompt-level, but prompt rewrite should not be the next move.

Prompt-level issues:

- repeated `teams in this position typically`,
- repeated generic decision-space cadence,
- some unsupported prescription wording such as `the brand should` in Iris,
- generic or filler terms such as `compelling`,
- repeated sentence openings such as `The brand describes...`.

However, rendering already suppresses the most visible `Decision space` problem:

- LaunchDarkly: `teams in this position typically` visible count 0.
- Iris: visible count 0.
- Watermelon: visible count 0.

The remaining visible problems are not solved by a broad prompt rewrite. They require knowing:

- which owned claims are already caveated,
- which evidence gaps are global versus local,
- which entity surfaces are primary, adjacent, or ambiguous,
- which dimensions should receive stricter evidence binding.

Prompt refinement should wait until the offline builder can provide measured state fields. Otherwise the prompt rewrite will be forced to solve composition without structured inputs.

## 4. Failures Requiring Entity-Level Composition

These failures require entity-level composition:

### Repeated caveats

The same caution appears across findings:

- `based only on self-description`,
- `no external corroboration`,
- `the evidence pool`.

A composition state should decide whether this is:

- a global owned-claim caveat,
- a local finding limitation,
- a missing evidence URL issue,
- a source ownership issue.

### Entity and surface hierarchy

Iris and Watermelon both expose entity complexity.

Iris surfaces include:

- `irisdesign.dev`
- `irisdesign.in`
- `irisdigital.design`
- `byiris.io`
- `heyiris.ai`
- `iris-ai.dev`
- `irisdesigncollaborative.com`

Watermelon surfaces include:

- `watermelon.sh`
- `watermelon.ai`
- `watermelon.market`
- `watermelon.us`
- GitHub orgs,
- Product Hunt,
- ambiguous watermelon-name surfaces.

The harness can count repeated phrases, but it cannot decide which surfaces belong to the audited entity.

That is an `EntityNarrativeState` responsibility.

### Contradiction and tension hierarchy

Watermelon especially shows that the report can notice ambiguity in synthesis but not structure it before findings.

Needed structure:

- stated claim,
- observed surface,
- supporting URLs,
- relation confidence,
- contradiction level,
- human review flag.

This should remain review-gated, but the state needs a place to hold it.

## 5. Fields Justified Across All Three Phase 2 Audits

These fields are now justified across LaunchDarkly, Iris, and Watermelon.

### `status`

Required.

Every state artifact must clearly say:

- offline,
- experimental,
- not runtime,
- not scoring,
- not prompt,
- not rendering,
- not persisted report narrative.

### `metadata`

Required.

The builder must record:

- run ID,
- brand,
- source payload path or run source,
- diagnostic inputs,
- generation timestamp,
- builder version.

### `primary_entity_signal`

Required.

Even LaunchDarkly, the low-ambiguity case, needs a stable entity anchor. Iris and Watermelon make this essential.

The first builder should keep this conservative:

- primary brand name,
- canonical URL,
- confidence from discovery/entity data,
- uncertainty notes from observed related surfaces.

It should not infer brand intent or market strategy.

### `entity_aliases.observed_related_surfaces`

Required.

All three runs expose at least some related surfaces. In Iris and Watermelon this becomes central.

The field name should remain cautious:

```text
observed_related_surfaces
```

not verified aliases.

### `owned_claim_density`

Required.

Safe attribution appears in all three:

- LaunchDarkly: 13.
- Iris: 15.
- Watermelon: 9.

The builder can derive this from existing harness metrics.

### `repeated_opener_budget`

Required.

All three are over budget:

- repeated `teams in this`,
- repeated `the brand describes`,
- repeated `the brand appears`,
- repeated `the brand's owned`.

The builder should report budget pressure, not rewrite prose.

### `fallback_language_budget`

Required.

All three trigger fallback evidence-family repetition:

- LaunchDarkly: 9.
- Iris: 10.
- Watermelon: 8.

This is no longer a Netlify-only fallback issue.

### `evidence_url_coverage`

Required.

This is the cleanest measured field.

The first builder should compute:

- findings total,
- findings with evidence URLs,
- findings without evidence URLs,
- per-dimension coverage,
- visible evidence chip count if render diagnostics exist.

### `decision_space_mode`

Required, advisory only.

Rendering suppresses generic `Decision space` effectively, but payload-level `typical_decision` repetition remains. The state should record:

- visible count,
- suppressed count,
- generic payload count,
- recommended mode.

It should not mutate display.

## 6. Fields Justified Only For Ambiguous / Multi-Surface Cases

These fields are justified, but not always active.

### `source_ownership_summary`

Justified for all, but precision remains limited.

It is especially useful for Iris and Watermelon because owned/third-party/ambiguous surfaces diverge. In the builder, it should start as deterministic and coarse:

- owned URLs,
- third-party URLs,
- ambiguous URLs,
- unknown URLs,
- missing evidence URL findings.

Avoid manual-like counts unless they are directly computed.

### `attribution_budget`

Conditional.

Needed when safe attribution exceeds threshold.

All three Phase 2 cases exceed threshold, but Netlify showed it can be inactive. The builder should include it with:

- `applicable: true | false`,
- observed counts,
- suggested global caveat preference,
- no rewrite action.

### `corroboration_caveat_budget`

Conditional.

Needed when external-corroboration caveat repetition exceeds threshold.

It is active for all three Phase 2 cases, inactive for Netlify.

### `primary_tension`

Optional and review-gated.

Watermelon and Iris justify it. LaunchDarkly does not require it structurally.

The builder should not generate rich tension prose. At most it should extract or reference existing `tensions_prose` and mark:

- present,
- absent,
- source,
- requires review.

### `contradiction_candidates`

Optional and review-gated.

Watermelon makes this field necessary as a future contract, but it should not be auto-populated with strategic interpretation yet.

The first builder may set:

```json
"contradiction_candidates": []
```

plus a diagnostic note if related-surface ambiguity is high.

### `compression_candidates`

Optional and suggested-only.

Useful as an editorial hypothesis, not a rewrite instruction.

The builder can safely create mechanical candidates such as:

- findings without evidence URLs,
- repeated caveat families over threshold,
- repeated opener over threshold.

It must mark them:

```text
suggested_only: true
requires_human_review: true
```

## 7. Fields That Should Remain Optional / Review-Gated

These must not become automatic truth:

- `primary_tension`
- `contradiction_candidates`
- `compression_candidates`
- `source_ownership_summary` interpretation notes
- any relation between observed surfaces beyond simple domain observation

Review flags are mandatory when:

- surfaces may not belong to the same entity,
- a claim is based on owned copy,
- a contradiction is inferred from multiple sources,
- a tension is derived from synthesis prose rather than direct structured evidence.

## 8. Is A Third Offline Fixture Needed Before A Builder?

No.

The earlier fixture review recommended one more fixture before a builder because the shape had only Builtwith and Netlify.

Phase 2 changed the evidence base.

Now Brand3 has:

- two earlier offline fixtures,
- three real Phase 2 audits,
- three generated payload diagnostics,
- three render-aware diagnostics,
- stable metrics across good-data runs.

At this point, a third manual fixture would be less useful than a deterministic offline builder prototype.

The builder should be treated as the next fixture generator, not as runtime logic.

## 9. Should The Next Fixture Be Iris Or Watermelon?

If one manual fixture is still desired, choose Watermelon.

Reason:

- LaunchDarkly tested evidence-binding under stable entity conditions.
- Iris tested owned-claim and visual/perceptual pressure.
- Watermelon tests entity hierarchy most clearly.

Watermelon is the strongest candidate for a third manual fixture because it exposes a failure that budgets alone cannot represent:

```text
which observed surfaces belong to the audited entity,
which are adjacent,
which are ambiguous,
and which should be excluded from narrative synthesis.
```

But the recommendation is to skip the manual fixture and let the offline builder produce candidate state for all three Phase 2 runs.

## 10. Is A Minimal Offline Builder Justified?

Yes.

Only as an offline builder.

The builder should live near the Narrative Harness, consume existing report artifacts, and emit diagnostic state.

It should build:

- `status`
- `metadata`
- `primary_entity_signal`
- `entity_aliases.observed_related_surfaces`
- `owned_claim_density`
- `source_ownership_summary`
- `repeated_opener_budget`
- `attribution_budget`
- `corroboration_caveat_budget`
- `fallback_language_budget`
- `evidence_url_coverage`
- `decision_space_mode`
- optional/review-gated `primary_tension`
- optional/review-gated `contradiction_candidates`
- optional/suggested-only `compression_candidates`

It should consume:

- `report_narrative` payload,
- payload-level harness diagnostic,
- render-aware harness diagnostic when available,
- base run snapshot or base dossier metadata,
- discovery/entity data when available.

It should emit:

```text
examples/reports/narrative_harness/entity_state/<case>.entity_narrative_state.json
```

for offline analysis only.

## Builder Non-Goals

The builder must not:

- rewrite prose,
- change prompts,
- change scores,
- change rendering,
- change persisted `report_narrative`,
- call LLMs,
- infer brand archetype,
- infer audience psychology,
- infer strategic intent,
- mark contradiction candidates as fact,
- decide related surfaces are true aliases,
- integrate with Visual Signature,
- run in production paths,
- block reports.

It should be deterministic and side-effect free.

## Prompt Changes: Not Yet

Prompt changes are probably needed later, but not first.

Strictly scoped prompt changes may eventually target:

- generic `teams in this position typically`,
- repeated `based only on self-description`,
- repeated `no external corroboration`,
- evidence URL attachment behavior,
- duplicated observation openings.

But those should wait until the builder can produce state that tells the prompt:

- which caveats are already globally established,
- which findings have weak evidence URL coverage,
- which surfaces are ambiguous,
- which dimensions should avoid assertive language.

Without that state, prompt changes risk only rewording the same structural problem.

## Runtime Integration: Not Yet

Runtime integration is not justified.

The next phase should remain:

```text
offline builder
example states
tests
comparison memo
```

No production route, report generation path, scoring path, or Visual Signature path should consume the state yet.

## Recommended Next Step

Implement `EntityNarrativeState` offline builder v0.

Minimal scope:

1. Add a pure module, probably near:

   ```text
   src/reports/entity_narrative_state.py
   ```

2. Add a public function:

   ```python
   build_entity_narrative_state(
       payload: dict,
       *,
       payload_diagnostic: dict | None = None,
       render_diagnostic: dict | None = None,
       snapshot: dict | None = None,
   ) -> dict
   ```

3. Keep all output diagnostic and offline.

4. Add tests for:

   - stable output shape,
   - inactive budgets when metrics are absent,
   - active attribution/corroboration/fallback budgets when thresholds are exceeded,
   - evidence URL coverage calculation,
   - observed related surfaces remain cautious,
   - review-gated fields are not auto-promoted to fact.

5. Generate builder outputs for:

   - LaunchDarkly,
   - Iris,
   - Watermelon.

6. Compare builder outputs against the manual Builtwith and Netlify fixture assumptions.

## Bottom Line

Phase 2 validates the readiness of a minimal offline `EntityNarrativeState` builder.

It does not validate runtime integration.

It does not validate prompt rewrite.

It does not validate scoring changes.

The correct next move is:

```text
build the state offline,
measure it against the three Phase 2 cases,
and only then decide whether prompts or reports should consume it.
```
