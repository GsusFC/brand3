# Brand3 State-Aware Findings Experiment Critical Review

Date: 2026-05-17

Scope: critical review only. No code, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, builder fields, fixtures, audits, or runtime behavior were changed.

## Executive Judgment

The state-aware findings experiment shows a real compositional improvement, but not enough evidence for prompt rollout or runtime use.

The strongest result is that `EntityNarrativeState` helps convert repeated local caveats into one explicit composition constraint. In Builtwith / Kit, Iris, and Watermelon, the state-aware variants are less fragmented because they stop treating every finding as an isolated paragraph and instead name the governing condition:

- entity boundary uncertainty,
- owned-claim density,
- missing finding-level evidence URLs,
- unresolved related surfaces,
- generic Decision Space overuse.

That is not merely style. It changes the unit of analysis from isolated claim to entity-level narrative condition.

The main risk is that the state-aware variants become smoother than the evidence permits. They reduce visible defensive language, but that can create false coherence if the uncertainty is not preserved in a compact and explicit way.

Recommendation:

```text
continue lab-only
```

Do not expand into production prompts yet. The next step should be a measured lab-only runner or fixture comparison that evaluates diagnostic deltas, not a runtime integration.

## Review Question

The question under review is:

```text
Does EntityNarrativeState reduce defensive fragmentation
without weakening evidence discipline?
```

Answer:

```text
mostly yes in the three manual examples,
but only because the variants keep uncertainty visible
and avoid turning state into strategy.
```

The improvement is conditional. If future prompt use quotes state fields directly, hides review flags, or turns ambiguity into confident synthesis, the same mechanism could weaken evidence discipline.

## Case Review

### Builtwith / Kit

Baseline failure:

- repeats safe attribution,
- repeats missing corroboration caveats,
- includes generic strategic options,
- mixes `builtwith.kit.com` creator-email positioning with BuiltWith technology-intelligence descriptions,
- does not make entity ambiguity the central problem.

State-aware improvement:

- entity boundary becomes the finding,
- owned positioning and external technology-intelligence signal are separated,
- missing evidence URLs become a coverage limit,
- generic expansion/pivot advice is removed.

Epistemic discipline:

Mostly preserved. The variant explicitly says the entity boundary needs review and avoids recommending expansion, pivoting, or audience broadening.

Remaining risk:

The phrase "the narrative is split" is useful but still interpretive. It is acceptable in lab context because it is tied to the audited surface versus external surface distinction. In production, it should require either explicit entity metadata or a clear review flag.

Judgment:

True compositional improvement, not just cosmetic fluency.

### Iris

Baseline failure:

- owned claim is repeated with caveats,
- speed and price contrast are inflated into possible market democratization,
- weak evidence is carried as local defensive wording rather than as a global evidence condition,
- unresolved Iris-name collisions are not part of the finding.

State-aware improvement:

- preserves the owned claim,
- narrows interpretation to surface behavior: speed, price contrast, maker accessibility,
- rejects external adoption, agency displacement, and market democratization as unproven,
- keeps name-collision ambiguity review-gated.

Epistemic discipline:

Preserved, but more fragile than Builtwith. The variant is disciplined because it explicitly rejects overreach. Without that sentence, the cleaner prose could easily read as a confident market interpretation.

Remaining risk:

"Maker accessibility" is a mild interpretive phrase. It is grounded in the indie-developer claim, but it should remain a reading of surface language, not a fact about audience adoption.

Judgment:

True improvement with moderate overconfidence risk. This case shows why state-aware prompts need explicit anti-inflation rules.

### Watermelon

Baseline failure:

- repeats self-description caveats,
- flattens design-infrastructure positioning and adjacent ecosystem surfaces into one narrative space,
- risks reading roadmap/current-state ambiguity as unified strategy,
- generic strategic advice remains available through `typical_decision`.

State-aware improvement:

- separates audited surface from broader related-surface pressure,
- treats related surfaces as unverified and review-gated,
- names ecosystem ambiguity as a composition risk,
- avoids inferring a unified platform strategy.

Epistemic discipline:

Preserved if and only if the related-surface input is explicit and reviewed. The variant correctly says the surrounding surfaces are not verified as the same entity.

Remaining risk:

The variant depends on manual `observed_related_surfaces` metadata. Without that metadata, a prompt should not independently assemble adjacent domains, repositories, or marketplace profiles into an ecosystem reading.

Judgment:

Strong compositional improvement, but only under strict input-contract conditions.

## Evaluation Dimensions

### Repeated Caveat Reduction

Improved across all three examples.

The baseline repeats caveats inside each finding. The state-aware variants consolidate caveats into one governing limitation:

- Builtwith / Kit: entity boundary review.
- Iris: owned claim without external adoption proof.
- Watermelon: related surfaces are unverified.

This is a valid improvement because the caution is not removed; it is moved to the right level.

Risk:

If the compact caveat is omitted, the variant becomes overconfident. Caveat compression must never become caveat deletion.

### Evidence Binding Quality

Improved, but not fully solved.

The variants bind findings to evidence conditions better than the baseline because they describe:

- owned positioning,
- external or third-party signal,
- missing evidence URLs,
- reviewed related-surface ambiguity.

However, they do not add actual evidence URLs. They improve interpretation of evidence coverage, not the underlying evidence attachment problem.

Conclusion:

State-aware composition can guide evidence use, but it does not replace the need to fix finding-level evidence URL binding later.

### Entity Ambiguity Handling

Improved clearly.

This is the strongest use of `EntityNarrativeState`.

The variants avoid treating ambiguity as noise. They make it part of the finding while preserving review status:

- Builtwith / Kit: entity split.
- Iris: name-collision pressure.
- Watermelon: adjacent ecosystem surfaces.

Risk:

Entity ambiguity can become a narrative magnet. The prompt must not over-bind every related surface into a single strategy, roadmap, or brand architecture.

### Overreach Risk

Reduced in the manual variants, but not eliminated.

The state-aware variants remove several unsupported moves:

- "democratize brand creation",
- "differentiate from broader productivity or CRM platforms",
- "specialized solution provider",
- expansion/pivot recommendations.

Remaining overreach risk:

- smoother prose can imply more certainty,
- terms such as "composition risk" or "narrative is split" are analytical judgments,
- explicit state fields can make weak signals feel more official than they are.

### Suppression Of Legitimate Uncertainty

Partially avoided.

The variants preserve uncertainty in compact form. That is good.

But compact uncertainty is easier to miss than repeated caveats. A production experiment would need a visible uncertainty rule:

```text
every state-aware finding that compresses caveats must include one explicit uncertainty sentence
when source ownership, corroboration, or related-surface status is unresolved.
```

### Loss Of Caution

Low in the manual examples.

The variants are cautious because they explicitly reject unsupported conclusions.

Risk becomes higher if future variants only optimize for readability. The goal is not cleaner prose by itself; the goal is cleaner evidence discipline.

### False Coherence Risk

Medium.

`EntityNarrativeState` can reduce fragmentation by naming the composition condition. That is valuable. But the same move can create false coherence if it makes unrelated artifacts feel intentionally connected.

Highest-risk case:

Watermelon. Related surfaces can be described safely as ambiguity pressure, but should not be treated as proof of ecosystem strategy.

### Narrative Fragmentation

Reduced.

The variants no longer read like isolated LLM findings. Each one has a governing narrative condition:

- Builtwith / Kit: unresolved entity boundary.
- Iris: owned surface claim versus evidentiary confidence.
- Watermelon: audited surface versus adjacent-surface ambiguity.

This is the core positive result of the experiment.

### Does Ambiguity Become Clearer Or Merely Quieter?

Mostly clearer.

The variants are not just quieter because they replace repeated caveats with explicit composition diagnoses. The ambiguity is still named.

However, the review should not overstate this result. The examples were manually written. A generated prompt may hide ambiguity unless the contract requires the uncertainty sentence.

## Improvement Classification

### True Compositional Improvement

Observed when the variant:

- moves caveats from repeated local phrasing to a global evidence condition,
- names entity ambiguity directly,
- separates owned claim from external signal,
- avoids generic Decision Space,
- refuses unsupported strategic recommendations.

Cases:

- Builtwith / Kit: strong.
- Watermelon: strong when related-surface input is explicit.
- Iris: moderate-to-strong.

### Cosmetic Fluency Improvement

Also present.

The variants read better because they are shorter and less repetitive. That alone is not proof of better analysis.

Cosmetic fluency would become dangerous if it:

- removes caveats without replacing them,
- makes weak evidence feel settled,
- hides missing evidence URLs,
- turns review-gated ambiguity into confident synthesis.

### Dangerous Confidence Inflation

Not present in a severe form in the manual variants, but the risk is real.

Watch phrases:

- "the useful finding is...",
- "the stronger Brand3 reading is...",
- "the finding should therefore...",
- "composition risk".

These are acceptable in an internal lab memo. In production findings, they need either direct evidence anchoring or clear uncertainty framing.

### Hidden Uncertainty

Partially present as a risk, not as a failure.

The variants hide repetitive uncertainty but do not hide uncertainty entirely. The compact caveats are visible. That is the correct direction, but it must be enforced as an invariant.

## Useful State Fields For Prompting

These fields appear genuinely useful as prompt context or constraints:

| Field | Why useful | Safe use |
|---|---|---|
| `owned_claim_density` | Tells prompt not to repeat self-attribution per finding. | Use to choose global caveat strategy. |
| `attribution_budget` | Converts safe-attribution repetition into a composition constraint. | Use as warning, not as content. |
| `corroboration_caveat_budget` | Prevents repeated `no external corroboration` phrasing. | Require one compact uncertainty sentence. |
| `fallback_language_budget` | Flags fallback-like evidence openings. | Suppress repeated fallback phrasing. |
| `evidence_url_coverage` | Identifies coverage limits by finding/dimension. | Mention as coverage limit; do not treat as score weakness. |
| `decision_space_mode` | Prevents generic strategic advice. | Omit or demote generic Decision Space. |
| `entity_aliases.observed_related_surfaces` | Helps represent ambiguity without aliasing. | Use only when explicit, reviewed, and review-gated. |
| `primary_entity_signal.requires_human_review` | Prevents premature entity certainty. | Keep uncertainty visible. |

## Fields That Should Not Become Prompt-Visible As Content

These fields should not be quoted or treated as prose input:

- raw `compression_candidates`,
- raw budget thresholds,
- raw phrase counts,
- `warning_count`,
- `error_count`,
- internal derivation notes,
- `source_ownership_summary` estimates when method is not explicit,
- related-surface evidence notes as if they were verified relationships.

They are useful as control signals, not narrative facts.

## Fields That Could Encourage Overconfidence

### `primary_entity_signal`

Risk:

The label can make an unresolved entity anchor look settled.

Mitigation:

Expose `requires_human_review` and uncertainty notes whenever confidence is not high.

### `observed_related_surfaces`

Risk:

Related surfaces can be mistaken for aliases, ownership, or product architecture.

Mitigation:

Prompt must preserve relation type and must not infer ownership or equivalence.

### `primary_tension`

Risk:

If added later as prompt-visible content, it could become a synthetic strategic claim.

Mitigation:

Keep review-gated and never auto-promote to fact.

### `compression_candidates`

Risk:

Could become an instruction to remove caution rather than compress repetition.

Mitigation:

Keep suggested-only. Never treat compression as deletion.

## Epistemic Discipline Verdict

Did the state-aware experiment preserve epistemic discipline while reducing fragmentation?

```text
Yes, in the manual examples.
Not proven for generated output.
```

The experiment preserves discipline because each variant:

- keeps unresolved evidence status visible,
- avoids unsupported recommendations,
- treats related surfaces as review-gated,
- refuses to infer ownership,
- separates surface claim from external validation,
- does not use state as proof of strategy.

It reduces fragmentation because each variant:

- gives the finding a governing entity-level condition,
- avoids repeating the same caveat mechanically,
- removes generic Decision Space,
- clarifies whether the problem is evidence coverage, owned positioning, or entity ambiguity.

But this is not production-ready. The examples are manually authored and manually cautious. The next experiment must test whether a constrained generator can reproduce the same discipline.

## Recommendation

Recommendation:

```text
continue lab-only
```

Do not stop the experiment. It produced enough signal to continue.

Do not expand broadly. The epistemic risk is still real.

Do not roll into production prompts. The improvement has not been measured on generated outputs.

## Recommended Next Step

Create a lab-only measured comparison pass.

Inputs:

- baseline selected finding excerpts,
- state-aware generated or manually constrained variants,
- payload diagnostics,
- render-aware diagnostics,
- `EntityNarrativeState` outputs.

Measure:

- repeated caveat count,
- repeated opener count,
- generic filler count,
- unsupported recommendation count,
- explicit uncertainty sentence present,
- evidence URL coverage mentioned accurately,
- related surfaces not treated as aliases,
- human preference.

Required invariant:

```text
fragmentation reduction is only valid when uncertainty remains explicit.
```

## What Should Not Happen Next

Do not:

- integrate `EntityNarrativeState` into runtime,
- rewrite production prompts,
- add new builder fields,
- create automatic contradiction candidates,
- treat related surfaces as aliases,
- optimize for nicer prose alone,
- remove caveats without replacing them with a compact uncertainty frame,
- use state fields as strategic claims,
- let Visual Signature confidence become evidence confidence.

The experiment should remain a lab-only epistemic behavior test.
