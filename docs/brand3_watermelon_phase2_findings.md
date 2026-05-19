# Brand3 Watermelon Phase 2 Findings

Date: 2026-05-16

Scope: Phase 2 candidate audit for Watermelon only. No prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, `EntityNarrativeState` builder, or runtime behavior were changed.

## Inputs

Planning references:

- `docs/brand3_phase_2_candidate_set.md`
- `docs/brand3_launchdarkly_phase2_findings.md`
- `docs/brand3_iris_phase2_findings.md`
- `docs/brand3_narrative_harness_phase_1_boundary.md`

Target:

```text
https://watermelon.sh
```

Run used for diagnostics:

```text
run_id: 78
brand: Watermelon
score: 77.7
data_quality: good
llm_used: true
```

Generated artifacts:

```text
examples/reports/narrative_harness/watermelon.payload.json
examples/reports/narrative_harness/watermelon.diagnostic.json
examples/reports/narrative_harness/watermelon.render_aware.diagnostic.json
```

## Expected Role

Watermelon was selected as the ecosystem / composition ambiguity candidate.

Expected pressure from the candidate memo:

- entity fragmentation,
- `observed_related_surfaces` complexity,
- roadmap/current-state ambiguity,
- contradiction candidates,
- ecosystem narrative drift,
- repeated opener budgets,
- evidence URL coverage,
- composition hierarchy,
- synthesis coherence.

The Phase 2 question was:

```text
Did Watermelon expose a fundamentally different narrative failure mode,
or did it reproduce the same evidence-binding/caveat pattern through a more complex ecosystem structure?
```

## Actual Evidence Context

The run collected a strong enough evidence base:

| Signal | Result |
|---|---:|
| web scrape | 4,513 chars scraped |
| Exa mentions | 15 mentions, 10 news |
| competitors | 5 discovered, 5 scraped |
| screenshot | captured |
| evidence total | 26 |
| dimensions without evidence | 0 |
| data quality | good |
| composite score | 77.7 |

Discovery was entity-rich:

- owned evidence: 2
- third-party evidence: 37
- discovery evidence preview: recommended
- trust basis: `company_brand_enriched`
- context coverage: 0.62
- context confidence: 0.80

Observed related surfaces included:

- `watermelon.sh`
- `watermelon.ai`
- `watermelon.market`
- `watermelon.us`
- `github.com/watermelontools`
- `github.com/WatermelonCorp/watermellon-registry`
- `developer.watermelon.ai`
- `producthunt.com/products/watermelon`
- unrelated or ambiguous watermelon-name surfaces such as `drinkwtrmln.com`, `watermelon.co`, and a honey watermelons brand-refresh article.

This made Watermelon the clearest Phase 2 pressure test for entity hierarchy.

## Harness Results

Payload-level diagnostic:

| Metric | Result |
|---|---:|
| status | warning |
| total checks | 8 |
| warnings | 5 |
| findings | 14 |
| findings without evidence URLs | 6 |
| safe attribution total | 9 |
| generic `teams in this position typically` | 11 |
| fallback evidence family | 8 |
| external corroboration caveat family | 16 |

Render-aware diagnostic:

| Metric | Result |
|---|---:|
| visible render status | warning |
| suppressed risks | 3 |
| still-visible risks | 7 |
| visible evidence chip links | 13 |
| visible `Decision space` count | 2 |
| visible `Teams in this position typically` | 0 |
| visible safe attribution total | 9 |
| visible `no external corroboration` | 8 |
| visible `The brand...` count | 29 |

## Comparison Across Phase 2

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

Watermelon reduces safe attribution compared with LaunchDarkly and Iris, but does not break the pattern. The same evidence-binding/caveat family persists across all three good-data Phase 2 runs.

## Comparison Against Expectations

### Safe Attribution Repetition

Expected: medium.

Actual: elevated but lower than the first two Phase 2 candidates.

The payload contains:

```text
safe_attribution_total: 9
the brand describes itself: 1
based only on self-description: 8
```

Interpretation:

Watermelon does not overuse `the brand describes itself` as much as LaunchDarkly or Iris. Instead, the repeated safe-attribution pattern mostly comes from the phrase `based only on self-description`.

This suggests the issue is less about a single opening phrase and more about the narrative layer repeating the same epistemic caveat whenever a finding lacks attached evidence URLs.

### External Corroboration Caveat Repetition

Expected: medium to high.

Actual: high.

The harness reports:

```text
external_corroboration_caveat_repetition: 16
based only on self-description: 8
no external corroboration: 8
```

Interpretation:

This is lower than Iris but still too high for a run with 26 evidence items and 37 third-party evidence signals in discovery. As with LaunchDarkly and Iris, the caveat is repeated locally instead of being composed as a single global evidence condition.

### Fallback Evidence-Opening Repetition

Expected: medium to high.

Actual: high.

The harness reports:

```text
fallback_evidence_opening_repetition: 8
phrase: the evidence pool
```

Interpretation:

This confirms the Phase 2 pattern. The phrase family persists when findings lack local evidence URLs, even though global evidence exists.

### Evidence URL Coverage

Expected: mixed.

Actual: mixed.

Payload evidence URL coverage:

| Dimension | Findings | Findings without evidence URLs | Evidence URLs |
|---|---:|---:|---:|
| coherencia | 3 | 3 | 0 |
| diferenciacion | 3 | 3 | 0 |
| percepcion | 3 | 0 | 4 |
| presencia | 3 | 0 | 5 |
| vitalidad | 2 | 0 | 4 |

Overall:

```text
findings: 14
findings_without_evidence_urls: 6
visible_evidence_chip_link_count: 13
```

Interpretation:

The same dimension-level split appears again: `coherencia` and `diferenciacion` carry no evidence URLs, while `percepcion`, `presencia`, and `vitalidad` are visibly better grounded.

This is now a repeated Phase 2 finding, not case noise.

### Repeated Opener Budget

Expected: high pressure.

Actual: over budget.

Payload repeated openings include:

```text
teams in this: 13
the brand appears: 7
the brand's owned: 3
```

Visible repeated openings after rendering:

```text
the brand appears: 6
the brand's owned: 3
```

Interpretation:

Rendering suppresses the decision-space cadence but cannot solve observation-level repetition. In Watermelon, `the brand appears` becomes the visible repeated opener because the report is trying to describe several surfaces without an entity hierarchy.

### Visible Render Repetition

Expected: high pressure.

Actual: warning.

The render-aware pass suppressed:

- `teams in this position typically`: 11
- `teams in this` repeated opening: 13
- one instance of `the brand appears`

But it still exposed:

- safe attribution total: 9
- `no external corroboration`: 8
- repeated `the brand appears`: 6
- repeated `the brand's owned`: 3
- observation repetition families.

Interpretation:

The rendering layer again helps, but the remaining risk is upstream composition.

## Ecosystem / Entity Fragmentation

Watermelon clearly exposes entity fragmentation.

The synthesis and tension identify the right broad problem:

- owned `watermelon.sh` positions itself as design infrastructure for modern startups,
- GitHub surfaces suggest developer tooling,
- `watermelon.sh/alternatives` and Product Hunt imply product/ecosystem context,
- `watermelon.us` introduces startup/funding/employment evidence,
- unrelated watermelon-name results create public-perception noise.

The report does notice this, but it does not fully resolve hierarchy.

Examples:

- `watermelon.sh` is treated as the primary owned surface.
- `github.com/watermelontools` and `WatermelonCorp/watermellon-registry` are treated as related developer surfaces.
- `watermelon.us` is used for founding, headcount, and funding.
- a honey watermelons brand-refresh article is flagged as ambiguous.

The report is aware of ambiguity, but it lacks a state object that says:

```text
primary entity: watermelon.sh
observed related surfaces: watermelon.ai, watermelon.us, GitHub orgs, Product Hunt
ambiguous unrelated surfaces: honey watermelon brand, other watermelon domains
review required before treating these as one entity
```

This is exactly where lexical diagnostics begin to hit their limits.

## Roadmap vs Current-State Ambiguity

Watermelon does not expose a clean roadmap/current-state contradiction, but it does expose current-state versus ecosystem-scope ambiguity.

The findings mix:

- design infrastructure positioning,
- open-source copilot/code-review language,
- GitHub repositories,
- Product Hunt listing,
- sitemap/robots context,
- startup funding/headcount,
- ambiguous external watermelon references.

That is not purely roadmap ambiguity. It is broader composition ambiguity:

```text
what is Watermelon right now,
which surfaces belong to it,
and which evidence should define the report?
```

The existing harness can count repeated phrases, but it cannot answer that hierarchy question.

## Contradiction Handling

The synthesis does identify a useful tension:

- intended positioning: design infrastructure for modern startups,
- external signals: GitHub/tooling, alternatives pages, ambiguous watermelon references.

That is better than ignoring the contradiction.

However, the contradiction is not represented structurally. It remains prose-level.

Missing structured distinction:

- stated claim,
- observed surface,
- supporting URLs,
- whether the surface is confirmed related,
- contradiction level,
- requires human review.

This supports the Phase 1 memo: `contradiction_candidates` should remain optional and review-gated, but Watermelon shows why the field is needed.

## Synthesis Coherence

The synthesis is more coherent than the individual findings.

It correctly frames the main problem as:

```text
the intended design-infrastructure identity may be diluted or overshadowed by adjacent public associations
```

But the findings remain fragmented because they describe surfaces one by one without a shared state:

- owned homepage,
- GitHub,
- Product Hunt,
- sitemap,
- `watermelon.us`,
- ambiguous external article.

This is a stronger composition failure than LaunchDarkly.

LaunchDarkly had stable entity but weak evidence binding.

Iris had entity ambiguity plus visual/owned-claim pressure.

Watermelon shows entity hierarchy pressure most clearly.

## Do EntityNarrativeState Fields Become Necessary Beyond Budgets?

Yes.

Watermelon makes budgets necessary but insufficient.

Useful budget fields:

- `repeated_opener_budget`
- `attribution_budget`
- `corroboration_caveat_budget`
- `fallback_language_budget`
- `evidence_url_coverage`

But Watermelon also needs entity-composition fields:

- `primary_entity_signal`
- `entity_aliases.observed_related_surfaces`
- `source_ownership_summary`
- `primary_tension`
- `contradiction_candidates`
- `requires_human_review` flags for ambiguous related surfaces.

This is the first Phase 2 case where the future state object is not just about reducing repetition. It is about preventing the report from collapsing several related or ambiguous surfaces into one unreviewed narrative.

## Do Lexical Diagnostics Hit Their Limits?

Yes.

The harness correctly reports:

- repeated openers,
- safe attribution,
- caveat repetition,
- missing evidence URLs,
- visible render risks.

But it cannot determine:

- whether `watermelon.ai` belongs to the same entity as `watermelon.sh`,
- whether `watermelon.us` should influence the same report,
- whether the honey watermelons article is unrelated noise,
- whether GitHub orgs should be primary, adjacent, or excluded,
- whether Product Hunt describes the same entity,
- whether the core contradiction should be framed as ecosystem complexity or entity contamination.

Those are entity-state questions, not lexical questions.

## Did Watermelon Expose A Different Failure Mode?

Yes, but not instead of the existing pattern.

Watermelon reproduced the same evidence-binding/caveat pattern:

- 6 findings without evidence URLs,
- 8 fallback evidence-family matches,
- 16 corroboration-caveat matches,
- 9 safe-attribution matches,
- visible render still warning.

But it also exposed a different and deeper mode:

```text
entity hierarchy failure under ecosystem ambiguity
```

The answer is:

```text
Watermelon reproduced the evidence-binding/caveat pattern
through a more complex ecosystem structure,
and it exposed the limit of lexical diagnostics for entity hierarchy.
```

## Phase 2 Conclusion

Across LaunchDarkly, Iris, and Watermelon, the repeated narrative issue is stable:

```text
good evidence collection
but uneven finding-level evidence binding
plus repeated safe attribution and corroboration caveats
```

Watermelon adds the strongest argument yet for `EntityNarrativeState`:

```text
Brand3 needs a structured entity/surface hierarchy before findings are written
```

Without that hierarchy, the report can notice ambiguity but cannot control it. It has to resolve uncertainty inside individual findings, which produces repeated caveats and fragmented narrative.

## Recommended Next Step

Do not implement a runtime builder yet.

The next correct artifact is a Phase 2 synthesis memo comparing the three candidate audits and deciding whether the minimal `EntityNarrativeState` contract is ready for an offline builder.

That memo should answer:

- which fields are now justified by all three Phase 2 cases,
- which fields are justified only by Iris/Watermelon ambiguity,
- which failures are still prompt-level,
- which failures are evidence-binding/data-contract issues,
- whether a third offline entity-state fixture should be Watermelon or Iris,
- what the first offline builder must explicitly avoid.
