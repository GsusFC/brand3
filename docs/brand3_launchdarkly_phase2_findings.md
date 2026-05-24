# Brand3 LaunchDarkly Phase 2 Findings

Date: 2026-05-16

Scope: Phase 2 candidate audit for LaunchDarkly only. No prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, `EntityNarrativeState` builder, or runtime behavior were changed.

## Inputs

Planning references:

- `docs/brand3_phase_2_candidate_set.md`
- `docs/brand3_narrative_harness_phase_1_boundary.md`
- `docs/brand3_entity_narrative_state_design_memo.md`

Target:

```text
https://launchdarkly.com
```

Run used for diagnostics:

```text
run_id: 76
brand: LaunchDarkly
score: 77.6
data_quality: good
llm_used: true
```

Generated artifacts:

```text
examples/reports/narrative_harness/launchdarkly.payload.json
examples/reports/narrative_harness/launchdarkly.diagnostic.json
examples/reports/narrative_harness/launchdarkly.render_aware.diagnostic.json
```

Execution note: an earlier sandboxed attempt produced `run_id: 75` with DNS failures and insufficient data. It is not used for this audit. The valid audit is `run_id: 76`, executed with network access.

## Expected Role

LaunchDarkly was selected as the healthy / high-evidence / low-ambiguity control case.

Expected pressure from the candidate memo:

- low caveat repetition,
- strong evidence coverage,
- stable positioning,
- low entity fragmentation,
- low owned-claim density,
- low contradiction pressure.

The question was not whether Brand3 could find problems. The question was:

```text
Can Brand3 remain stable, evidence-aware, and low-warning when the evidence ecosystem is relatively strong?
```

## Actual Evidence Context

The scoring run did collect a strong evidence base:

| Signal | Result |
|---|---:|
| web scrape | 52,109 chars scraped |
| Exa mentions | 14 mentions, 10 news |
| social | 4 platforms |
| competitors | 5 discovered, 5 scraped |
| evidence total | 28 |
| dimensions without evidence | 0 |
| data quality | good |
| composite score | 77.6 |

Discovery was also strong:

- owned evidence: 23
- third-party evidence: 15
- discovery evidence preview: recommended
- trust basis: `company_brand_enriched`
- limitations: none

This means LaunchDarkly did function as a high-evidence test at the collection/scoring level.

## Harness Results

Payload-level diagnostic:

| Metric | Result |
|---|---:|
| status | warning |
| total checks | 8 |
| warnings | 5 |
| findings | 14 |
| findings without evidence URLs | 7 |
| safe attribution total | 13 |
| generic `teams in this position typically` | 9 |
| fallback evidence family | 9 |
| external corroboration caveat family | 18 |

Render-aware diagnostic:

| Metric | Result |
|---|---:|
| visible render status | warning |
| suppressed risks | 2 |
| still-visible risks | 7 |
| visible evidence chip links | 10 |
| visible `Decision space` count | 4 |
| visible `Teams in this position typically` | 0 |
| visible safe attribution total | 13 |
| visible `no external corroboration` | 9 |
| visible `The brand...` count | 21 |

## Comparison Against Expectations

### Safe Attribution Repetition

Expected: low.

Actual: high.

The payload contains:

```text
safe_attribution_total: 13
the brand describes itself: 4
based only on self-description: 9
```

This is the biggest miss against the healthy-control expectation. Even though the run collected third-party evidence, many findings still frame observations as owned/self-description only.

Interpretation:

The narrative layer is not fully exploiting the stronger evidence ecosystem. It falls back to safe attribution language in several findings, especially in `coherencia`, `diferenciacion`, and parts of `presencia`.

### Fallback Evidence-Opening Repetition

Expected: low.

Actual: high.

The harness reports:

```text
fallback_evidence_opening_repetition: 9
phrase: the evidence pool
```

This does not look like the Netlify deterministic fallback phrase (`the available sources`), but it is the same family of problem. The narrative repeats an evidence-pool caveat even when the overall audit has substantial evidence.

Interpretation:

The fallback family is not limited to low-evidence reports. It can appear inside high-evidence reports when individual findings lack evidence URLs or the generation step does not bind the available evidence to the finding.

### Corroboration Caveat Repetition

Expected: low.

Actual: high.

The harness reports:

```text
external_corroboration_caveat_repetition: 18
based only on self-description: 9
no external corroboration: 9
```

This is a strong Phase 2 finding. LaunchDarkly had 15 third-party evidence items in discovery, but the narrative still repeatedly says there is no external corroboration in the evidence pool.

Interpretation:

This suggests a composition/evidence-binding issue, not simply weak data. The final narrative can behave as if corroboration is thin even when the broader run collected external evidence.

### Evidence URL Coverage

Expected: strong.

Actual: mixed.

Payload evidence URL coverage:

| Dimension | Findings | Findings without evidence URLs | Evidence URLs |
|---|---:|---:|---:|
| coherencia | 3 | 3 | 0 |
| diferenciacion | 3 | 3 | 0 |
| percepcion | 2 | 0 | 2 |
| presencia | 3 | 1 | 3 |
| vitalidad | 3 | 0 | 5 |

Overall:

```text
findings: 14
findings_without_evidence_urls: 7
visible_evidence_chip_link_count: 10
```

Interpretation:

The audit had evidence, but §4 findings did not consistently carry evidence URLs. The issue is not global evidence absence; it is uneven narrative evidence binding by dimension.

### Repeated Opener Budget

Expected: within budget.

Actual: over budget.

Payload repeated openings include:

```text
teams in this: 11
the brand describes: 4
the brand's owned: 3
```

Visible repeated openings after rendering:

```text
the brand describes: 4
the brand's owned: 3
```

Interpretation:

Rendering suppresses the `teams in this` phrase, but visible observation openings remain repetitive. This confirms the Phase 1 boundary: render-level mitigation helps, but it does not solve observation-level composition.

### Visible Render Repetition

Expected: low.

Actual: warning.

Visible risks still include:

- visible safe attribution overuse,
- visible repeated openings,
- visible `no external corroboration`,
- visible observation repetition families.

The rendered report suppresses:

```text
teams in this position typically: 9 payload / 0 visible
teams in this opening: 11 payload / 0 visible
```

But still exposes:

```text
safe attribution total: 13
no external corroboration: 9
fallback evidence family: 9
```

Interpretation:

Conditional `Decision space` rendering is working, but it is not enough for this case.

## Did Warnings Remain Low?

No.

This was expected to be a low-warning control. Instead, the payload diagnostic produced 5 warnings and the render-aware diagnostic found 7 still-visible risks.

The important nuance: the warnings are not because LaunchDarkly is low quality or ambiguous. They appear because the generated narrative does not fully use the evidence available to the run.

## Was Rendering Suppression Needed?

Yes.

Rendering suppression prevented the most generic `Decision space` cadence from becoming visible:

- `teams in this position typically`: 9 suppressed
- `teams in this` repeated opening: 11 suppressed

Without the earlier render experiment, LaunchDarkly would visibly repeat the same decision-space formula despite being a high-evidence case.

## Does The Report Still Feel Fragmented?

Yes, in a specific way.

The report does not appear fragmented because of entity ambiguity. LaunchDarkly remains a stable entity.

It feels fragmented because the narrative alternates between:

- strong global evidence/scoring,
- owned-claim caveats,
- missing evidence URLs in several findings,
- repeated warnings that no external corroboration exists,
- visible repeated observation openings.

This creates a mismatch:

```text
the run is high-evidence
but parts of the narrative read as if evidence is thin
```

That mismatch is a stronger finding than expected.

## EntityNarrativeState Implications

LaunchDarkly does not strongly need:

- entity ambiguity handling,
- `observed_related_surfaces` review,
- contradiction candidates as a primary mechanism.

LaunchDarkly does need:

- `evidence_url_coverage`,
- `source_ownership_summary`,
- `repeated_opener_budget`,
- `attribution_budget`,
- `corroboration_caveat_budget`,
- `fallback_language_budget`.

This means the future state should not be only for messy or ambiguous cases. Even a healthy high-evidence case may need entity-level composition state to prevent the generated findings from underusing available evidence.

## Did Brand3 Avoid Inventing Problems When Evidence Was Strong?

Partially, but not enough.

At the scoring and evidence level, Brand3 behaved well:

- data quality was good,
- score was reliable,
- evidence coverage existed across all dimensions,
- entity identity was stable,
- the report did not fabricate a major entity ambiguity.

At the narrative level, Brand3 did not fully avoid inventing or amplifying problems:

- it repeatedly framed findings as self-description only,
- it repeatedly said there was no external corroboration in the evidence pool,
- it produced 7 findings without evidence URLs despite 28 total evidence items,
- it made the report read more caution-heavy than the collected evidence appears to justify.

So the answer is:

```text
Brand3 avoided scoring-level overreaction,
but the narrative layer still manufactured a thin-evidence posture inside parts of a strong-evidence run.
```

## Phase 2 Conclusion

LaunchDarkly did not validate the hope that a healthy/high-evidence case would naturally produce a low-warning narrative.

Instead, it revealed a sharper architecture issue:

```text
strong evidence collection does not guarantee strong evidence binding in §4 findings
```

The next Phase 2 work should not be a broad prompt rewrite. The measured issue is narrower:

- findings need better evidence URL binding,
- owned/self-description caveats need a budget,
- external corroboration caveats should be globalized or suppressed when third-party evidence exists elsewhere in the run,
- `EntityNarrativeState` may be necessary even for healthy cases, not only ambiguous ones.

## Recommended Next Step

Run Iris next.

Reason:

LaunchDarkly unexpectedly reproduced owned-claim/caveat repetition despite strong evidence. Iris was already expected to pressure owned-claim density and weak external corroboration. Running Iris next will show whether LaunchDarkly is an anomaly in evidence binding or whether the narrative layer systematically overuses self-description caution whenever owned claims are prominent.

Do not build the `EntityNarrativeState` builder yet.

Do not change prompts yet.

Do not change rendering further yet.

The immediate value is comparative measurement across the selected Phase 2 candidate set.
