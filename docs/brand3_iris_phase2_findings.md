# Brand3 Iris Phase 2 Findings

Date: 2026-05-16

Scope: Phase 2 candidate audit for Iris only. No prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, `EntityNarrativeState` builder, or runtime behavior were changed.

## Inputs

Planning references:

- `docs/brand3_phase_2_candidate_set.md`
- `docs/brand3_narrative_harness_phase_1_boundary.md`
- `docs/brand3_launchdarkly_phase2_findings.md`

Target:

```text
https://irisdesign.dev
```

Run used for diagnostics:

```text
run_id: 77
brand: Iris
score: 75.8
data_quality: good
llm_used: true
```

Generated artifacts:

```text
examples/reports/narrative_harness/iris.payload.json
examples/reports/narrative_harness/iris.diagnostic.json
examples/reports/narrative_harness/iris.render_aware.diagnostic.json
```

## Expected Role

Iris was selected as the strong visual identity / weak external corroboration candidate.

Expected pressure from the candidate memo:

- owned-claim density,
- safe attribution repetition,
- corroboration caveat repetition,
- perceptual overreach risk,
- AI-heavy claims,
- weak or mixed external evidence,
- Visual Signature pressure.

The Phase 2 question was:

```text
Did LaunchDarkly expose an anomaly, or does the narrative layer systematically overuse owned-claim attribution and defensive caveats?
```

## Actual Evidence Context

The run collected a meaningful evidence base:

| Signal | Result |
|---|---:|
| web scrape | 13,816 chars scraped |
| Exa mentions | 15 mentions, 10 news |
| competitors | 5 discovered, 5 scraped |
| screenshot | captured |
| evidence total | 24 |
| dimensions without evidence | 0 |
| data quality | good |
| composite score | 75.8 |

Discovery was mixed but active:

- owned evidence: 2
- third-party evidence: 36
- discovery evidence preview: recommended
- trust basis: `company_brand_enriched`
- context coverage: 0.38
- context confidence: 0.65

The important difference from LaunchDarkly is entity ambiguity. Search and discovery surfaced many Iris-related domains:

- `irisdesign.dev`
- `irisdesign.in`
- `irisdigital.design`
- `byiris.io`
- `heyiris.ai`
- `iris-ai.dev`
- `irisdesigncollaborative.com`
- several other Iris-design or Iris-AI surfaces.

This made Iris less like a pure weak-corroboration case and more like an entity-composition case.

## Harness Results

Payload-level diagnostic:

| Metric | Result |
|---|---:|
| status | warning |
| total checks | 8 |
| warnings | 6 |
| findings | 14 |
| findings without evidence URLs | 6 |
| safe attribution total | 15 |
| generic `teams in this position typically` | 14 |
| unsupported prescription count | 2 |
| fallback evidence family | 10 |
| external corroboration caveat family | 20 |

Render-aware diagnostic:

| Metric | Result |
|---|---:|
| visible render status | warning |
| suppressed risks | 4 |
| still-visible risks | 7 |
| visible evidence chip links | 13 |
| visible `Decision space` count | 0 |
| visible `Teams in this position typically` | 0 |
| visible safe attribution total | 15 |
| visible `no external corroboration` | 10 |
| visible `The brand...` count | 21 |

## Comparison With LaunchDarkly

| Metric | LaunchDarkly | Iris |
|---|---:|---:|
| score | 77.6 | 75.8 |
| data quality | good | good |
| evidence total | 28 | 24 |
| payload warnings | 5 | 6 |
| findings | 14 | 14 |
| findings without evidence URLs | 7 | 6 |
| safe attribution total | 13 | 15 |
| external corroboration caveat family | 18 | 20 |
| fallback evidence family | 9 | 10 |
| generic `teams in this position typically` | 9 | 14 |
| visible evidence chips | 10 | 13 |
| visible still-visible risks | 7 | 7 |

Iris did not disprove LaunchDarkly. It strengthened the same finding.

Both runs had good overall data quality and evidence totals above 20. Both still generated heavy safe-attribution and corroboration-caveat repetition inside §4 findings.

## Comparison Against Expectations

### Safe Attribution Repetition

Expected: high pressure.

Actual: high.

The payload contains:

```text
safe_attribution_total: 15
the brand describes itself: 4
the brand claims: 1
based only on self-description: 10
```

This confirms that Iris activates the owned-claim attribution family more strongly than LaunchDarkly.

Interpretation:

The report correctly avoids treating owned claims as external truth, but it repeats the defensive construction too often. The result is epistemically cautious but editorially mechanical.

### External Corroboration Caveat Repetition

Expected: high pressure.

Actual: high.

The harness reports:

```text
external_corroboration_caveat_repetition: 20
based only on self-description: 10
no external corroboration: 10
```

This is slightly higher than LaunchDarkly.

Interpretation:

Iris validates that corroboration caveat repetition is not only a Builtwith or LaunchDarkly issue. The narrative layer repeats the caveat at finding level instead of consolidating the evidence condition once.

### Fallback Evidence-Opening Repetition

Expected: moderate to high.

Actual: high.

The harness reports:

```text
fallback_evidence_opening_repetition: 10
phrase: the evidence pool
```

This is again close to LaunchDarkly's pattern.

Interpretation:

The phrase family appears when findings cannot bind enough evidence URLs, even if the run overall has evidence. This confirms that the issue is local finding evidence binding, not only global data quality.

### Evidence URL Coverage

Expected: mixed.

Actual: mixed.

Payload evidence URL coverage:

| Dimension | Findings | Findings without evidence URLs | Evidence URLs |
|---|---:|---:|---:|
| coherencia | 3 | 3 | 0 |
| diferenciacion | 3 | 3 | 0 |
| percepcion | 3 | 0 | 4 |
| presencia | 2 | 0 | 4 |
| vitalidad | 3 | 0 | 5 |

Overall:

```text
findings: 14
findings_without_evidence_urls: 6
visible_evidence_chip_link_count: 13
```

Interpretation:

Like LaunchDarkly, Iris has global evidence but uneven finding-level evidence binding. `coherencia` and `diferenciacion` are the weak spots: six findings across those two dimensions carry no evidence URLs.

### Repeated Opener Budget

Expected: high pressure.

Actual: over budget.

Payload repeated openings include:

```text
teams in this: 14
the brand describes: 5
this suggests a: 4
the brand appears: 3
```

Visible repeated openings after rendering:

```text
the brand describes: 5
the brand appears: 3
```

Interpretation:

Rendering suppresses all visible `teams in this position typically` instances, but visible observation openings remain repetitive.

### Visible Render Repetition

Expected: high pressure.

Actual: warning.

The render-aware pass suppressed:

- `teams in this position typically`: 14
- `teams in this` repeated opening: 14
- `this suggests a`: 4
- `compelling`: 1

But it still exposed:

- safe attribution total: 15
- `no external corroboration`: 10
- repeated `the brand describes`: 5
- repeated `the brand appears`: 3
- observation repetition families.

Interpretation:

The rendering experiment is useful but insufficient. It removes generic decision-space cadence, but Iris still reads defensive because the observations themselves are repetitive.

## Did The Report Become Overly Defensive?

Yes.

The report has good data quality and 24 evidence items, but the visible narrative repeats:

```text
based only on self-description
no external corroboration
the evidence pool
```

This produces a defensive posture that may be stronger than the actual evidence condition warrants.

The defensive posture is not entirely wrong: Iris does have entity ambiguity and many owned claims. But repeating the same caveat per finding makes the report feel less synthesized and less editorially controlled.

## Did Visual / Perceptual Strength Cause Unsupported Inference?

Not primarily.

The run did capture a screenshot and produced visual-analysis evidence. The report mentions visual attributes such as color groups, contrast, and design signals, but the biggest issue is not visual overreach.

The bigger issue is entity and evidence binding:

- multiple Iris domains are treated as potentially related surfaces,
- external evidence spans different Iris entities,
- `coherencia` and `diferenciacion` lack finding-level evidence URLs,
- self-description caveats are repeated heavily.

There is some perceptual risk in phrases such as "confident, modern, and results-oriented" and in drawing strategic implications from visual/service language, but the harness results point more strongly to composition risk than to pure visual hallucination.

## Did The Narrative Feel Grounded Or Speculative?

Mixed.

Grounded where evidence URLs are attached:

- `percepcion`
- `presencia`
- `vitalidad`

More speculative where evidence URLs are absent:

- `coherencia`
- `diferenciacion`

The synthesis and tension are more coherent than the individual findings. They identify a useful tension between:

- rapid brand identity creation for indie developers,
- traditional design agency surfaces,
- multiple Iris domains.

But the findings still repeat local caveats instead of making that entity/tension problem explicit once.

## EntityNarrativeState Implications

Iris makes `EntityNarrativeState` more necessary than LaunchDarkly.

LaunchDarkly mainly proved that strong evidence collection does not guarantee strong finding-level evidence binding.

Iris adds:

- entity ambiguity,
- adjacent-surface ambiguity,
- owned-claim density,
- corroboration caveat repetition,
- visual/perceptual pressure,
- AI/domain ambiguity.

Fields that become clearly useful:

- `primary_entity_signal`
- `entity_aliases.observed_related_surfaces`
- `source_ownership_summary`
- `owned_claim_density`
- `attribution_budget`
- `corroboration_caveat_budget`
- `fallback_language_budget`
- `evidence_url_coverage`
- `primary_tension` with `requires_human_review`
- `contradiction_candidates` as optional/review-gated.

Iris is a better candidate than LaunchDarkly for a future offline entity-state fixture, but the builder should still wait until Watermelon is audited.

## Did Brand3 Correctly Distinguish Strong Visual/Perceptual Confidence From Strong Evidentiary Confidence?

Only partially.

Positive:

- The system did not treat visual polish alone as proof of market strength.
- Visual analysis stayed relatively bounded.
- The report used caveats around self-description rather than validating owned claims as fact.

Negative:

- The report did not clearly separate visual/perceptual confidence from entity confidence.
- It mixed several Iris surfaces and external references into one narrative frame.
- It repeated "no external corroboration" even while the broader run had substantial third-party evidence.
- It converted the uncertainty into repeated defensive caveats rather than a single entity-level caution.

Answer:

```text
Brand3 partially distinguished visual/perceptual signal from evidentiary confidence,
but it did not yet compose that distinction cleanly at entity level.
```

## Phase 2 Conclusion

Iris confirms that LaunchDarkly was not anomalous.

The repeated pattern is now visible across two good-data Phase 2 runs:

```text
good evidence collection
but uneven finding-level evidence binding
plus repeated safe attribution and corroboration caveats
```

Iris adds a second problem:

```text
entity ambiguity needs to be represented before findings are written
```

Without that state, the report has to defend itself inside individual findings, which produces repetitive caution instead of coherent synthesis.

## Recommended Next Step

Run Watermelon next before building anything.

Reason:

LaunchDarkly tested high-evidence stability and still showed evidence-binding failure.

Iris tested visual/owned-claim/entity ambiguity and amplified the same caveat pattern.

Watermelon should now test whether ecosystem and roadmap/current-state ambiguity create the same failure through entity hierarchy rather than visual or owned-claim pressure.

Do not build the `EntityNarrativeState` builder yet.

Do not change prompts yet.

Do not change rendering further yet.

After Watermelon, Brand3 should compare all three Phase 2 candidates and decide whether the minimal state contract is ready.
