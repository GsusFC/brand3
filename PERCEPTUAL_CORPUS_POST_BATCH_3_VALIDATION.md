# Brand3 Perceptual Corpus Post Batch 3 Validation

Status: post-expansion validation

## Purpose

This note checks whether the non-web3 expansion improved the experimental perceptual narrative layer.

The comparison was done against the corpus before Batch 3 and the corpus after Batch 3, using the same narrative helper paths and the same dimensions:

- coherencia
- presencia
- percepcion
- diferenciacion
- vitalidad

## Method

The validation compared:

1. the default stable narrative hints produced by `build_perceptual_narrative_hints(dimension)`
2. the underlying surface signals with a larger budget, to see whether the new non-web3 cases were present but hidden by the current collector limit

The comparison used the current corpus after Batch 3 and a filtered corpus that removed:

- `irisdesign_dev`
- `launchdarkly`
- `watermelon_sh`

## Findings

### 1. Default stable hint output is unchanged

At the current default budget, the first five stable surface signals are identical before and after Batch 3 for all checked dimensions.

That means:

- the visible stable prompt hints are not yet less crypto-skewed
- the non-web3 batch does not currently change the top-level hint surface
- the collector still reaches its five-signal cap before the new cases contribute

In other words, the batch improved the corpus, but not the default visible hint output.

### 2. The new non-web3 cases do add latent value

When the surface-signal budget is expanded beyond the default five, the new records begin to contribute additional non-web3 signals.

That is the key result:

- `irisdesign_dev` contributes a product-first / design-adjacent surface reading
- `launchdarkly` contributes a mature SaaS / B2B platform reading
- `watermelon_sh` contributes a product-digital / developer infrastructure reading

So the batch is not wasted data. It is simply not visible yet in the default five-signal collector budget.

### 3. SaaS / B2B / product-digital readings do improve

The new cases add distinct value in the broader corpus:

- LaunchDarkly improves the mature SaaS control-case side of the corpus
- Watermelon improves the product-digital / developer infrastructure side
- Iris adds a design-adjacent SaaS surface that is not crypto-native

That said, the improvement is latent in the current prompt path because of the collector limit.

### 4. The corpus is still not overrun by generic patterns

The existing patterns still appear to be useful and not yet too generic:

- Category-To-Surface Translation
- Evidence-Bound Behavior
- Claim / Signal Gap
- System Cohesion Difference
- Guided Movement
- Threshold Pacing

They remain broad, but they still describe real distinctions in the corpus.

The right response is not to invent a new pattern label yet.

### 5. No non-web3 case should become review-only

Based on the current records, none of the Batch 3 non-web3 cases needs to become `needs_human_review`.

All three are appropriate as normalized records:

- `irisdesign_dev`
- `launchdarkly`
- `watermelon_sh`

## Documentation consistency

The normalization documentation was corrected so it no longer says "No new cases were added" in the Batch 3 outcome section.

That wording now reflects the actual state: Batch 3 added three new cases and no new patterns were added.

## Recommendation

### Ready for next expansion?

**Yes.**

The corpus is ready for another controlled expansion batch.

### Refine pattern registry?

**Not yet.**

The current pattern set is broad, but it is still doing useful work. There is not enough evidence to justify a new pattern label yet.

### Keep current stable hint rules?

**Yes, for now.**

The current stable-hint rule that excludes review-only records is still correct.

However, if the goal is for the new non-web3 corpus to materially influence the visible prompt hints, the next improvement should be to diversify the surface-signal collector order or budget, not to weaken the review filter.

## Final conclusion

Batch 3 improves the corpus quality and domain coverage, but the default experimental perceptual hint output is still dominated by the earlier records because the surface-signal collector stops after five items.

So the practical answer is:

- the corpus is better
- the prompt path is not yet visibly better
- stable hint rules should stay
- the next change, if needed, is signal-sampling policy rather than pattern taxonomy

