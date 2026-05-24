# Watermelon State-First Findings Trial

Status: lab-only generation trial. Not production. No runtime integration. No scoring change. No report mutation.

## Selected Case

Watermelon was selected over Builtwith / Kit because it has the richest existing composition pressure:

- `report_narrative` payload
- payload-level Narrative Harness diagnostic
- render-aware diagnostic
- EntityNarrativeState v0
- reviewed `observed_related_surfaces` input

The core pressure is not only repetition. It is entity composition: `watermelon.sh` is the primary audited surface, but the evidence set also contains adjacent domains, developer surfaces, repository surfaces, marketplace profiles, alternatives pages, and unrelated-looking Watermelon references.

## Baseline

The baseline contains 14 findings across five dimensions:

- `coherencia`: 3 findings
- `diferenciacion`: 3 findings
- `percepcion`: 3 findings
- `presencia`: 3 findings
- `vitalidad`: 2 findings

Measured Narrative Harness problems:

- 5 payload warnings
- 7 visible render warnings
- 6 findings without evidence URLs
- 9 safe attribution repetitions
- 11 generic `teams in this position typically` decision-space phrases
- 16 external-corroboration caveat repetitions
- 8 fallback `the evidence pool` repetitions

The baseline’s main issue is that it treats each finding as an isolated paragraph. That causes repeated caveats, generic strategy choices, and surface merging. It notices ambiguity, but it does not govern the report with that ambiguity.

## Shared Entity State

Primary audited surface:

- `watermelon.sh`

Primary entity signal:

- label: Watermelon
- confidence: medium
- requires human review: true

Related surfaces are not aliases. They are composition pressure only:

- `watermelon.ai`
- `watermelon.market`
- `watermelon.us`
- `developer.watermelon.ai`
- `github.com/watermelontools`
- `github.com/watermeloncorp/watermellon-registry`
- `producthunt.com/products/watermelon`

The state says: do not infer ownership, equivalence, or unified roadmap from these surfaces.

## Shared Evidence Map

Primary owned evidence:

- `https://watermelon.sh/`
- `https://watermelon.sh/sitemap.xml`
- `https://watermelon.sh/robots.txt`

This supports observation of the owned surface, narrow site footprint, and the design-infrastructure positioning. It does not prove adoption, market fit, or external validation.

Repository/developer evidence:

- `https://github.com/watermelontools`
- `https://github.com/WatermelonCorp/watermellon-registry`

This supports observation that Watermelon-named developer surfaces exist. It does not prove they are official extensions of `watermelon.sh`.

Marketplace/external evidence:

- `https://www.producthunt.com/products/watermelon`
- `https://www.softwaresuggest.com/watermelon/alternatives`
- `https://perishablenews.com/produce/fresh-pro-announces-honey-watermelons-brand-refresh-new-mascot/`
- `https://watermelon.us/`

These are review-gated. They may be related, adjacent, stale, or irrelevant. They must not be merged into one brand story without entity review.

## Global Uncertainty Model

Can state as observation:

- `watermelon.sh` presents a design-infrastructure claim for modern startups.
- The evidence set contains Watermelon-named repository, marketplace, alternatives, and adjacent-domain surfaces.
- Several baseline findings lack evidence URLs.
- The baseline repeats self-description and external-corroboration caveats.

Can state as interpretation:

- Watermelon is an entity-composition case, not a simple positioning case.
- The owned surface has a coherent problem frame.
- The wider evidence set weakens entity certainty.

Must remain uncertain:

- Whether `watermelon.sh`, `watermelon.ai`, `watermelon.us`, the GitHub repositories, and the Product Hunt profile are the same entity.
- Whether the design-infrastructure claim is externally validated.
- Whether developer-tool signals represent an official product direction.

Must not infer:

- unified platform roadmap
- verified funding or growth for `watermelon.sh` from `watermelon.us`
- official open-source strategy from GitHub presence alone
- market traction from Product Hunt or alternatives pages alone
- unrelated food/produce coverage as perception of the audited software/design entity

## State-First Finding Plan

Coordination rules:

- Use one global caveat about entity ambiguity.
- Do not repeat `no external corroboration` in every finding.
- Do not use generic Decision Space paragraphs.
- Treat owned claims as owned claims.
- Separate primary-surface observations from related-surface ambiguity.
- Use dimensions to distribute the same entity problem, not to repeat it.

Dimension roles:

- `coherencia`: Does the story hold together across owned and adjacent surfaces?
- `diferenciacion`: What differentiates the owned surface, without external validation inflation?
- `percepcion`: Is public perception actually known, or is evidence collection fragmented?
- `presencia`: What surfaces exist, and which are safe to treat as owned?
- `vitalidad`: What activity signals exist, and which are entity-safe?

## Generated State-First Findings

Global caveat:

> State-first reading treats `watermelon.sh` as the audited primary surface. Other Watermelon-named domains, repositories, marketplace pages, and third-party references are related-surface pressure only until ownership or entity continuity is reviewed.

### Coherencia

#### The owned story is coherent, but the entity boundary is not

`watermelon.sh` presents a clear owned story around design infrastructure for modern startups and a founder pain point: startups move quickly while design becomes a bottleneck. That is a coherent primary-surface claim. The problem is not the claim itself; it is that the wider evidence set also contains Watermelon-named developer, repository, marketplace, alternatives, and adjacent-domain surfaces whose relationship to `watermelon.sh` is not verified.

Evidence: `https://watermelon.sh/`

Confidence: medium for owned-surface observation, low for cross-surface entity interpretation.

#### The code-review/copilot signal should be held outside the core narrative for now

The baseline treats an open-source code-review/copilot surface as part of the Watermelon story. State-first generation keeps that signal separate: it may be relevant to a broader ecosystem, but the current evidence does not prove it is an official extension of the design-infrastructure surface.

Evidence: `https://github.com/watermelontools`, `https://github.com/WatermelonCorp/watermellon-registry`

Confidence: low. Repository ownership, naming variance, and relation to `watermelon.sh` require review.

### Diferenciacion

#### Differentiation currently rests on an owned platform claim

Watermelon differentiates itself through the language of infrastructure, ecosystem, and relief from fragmented design tools. That is a stronger and more specific claim than a generic design-service offer, but the available evidence supports it as owned positioning rather than externally validated differentiation.

Evidence: `https://watermelon.sh/`

Confidence: medium for claim visibility, low for market validation.

#### The strongest safe reading is problem framing, not strategic intent

The brand's safest differentiating signal is its problem frame: founders stitching tools together, inconsistent UI, and design slowing product development. The report can say this is the brand's chosen frame. It should not infer a full platform strategy, category ownership, or adoption pathway from that copy alone.

Evidence: `https://watermelon.sh/`

Confidence: medium. External corroboration is needed before treating the problem frame as market truth.

### Percepcion

#### Perception is fragmented by evidence collection, not necessarily by the market

The evidence set exposes several Watermelon associations: the primary design-infrastructure surface, GitHub repositories, a Product Hunt listing, alternatives pages, and unrelated-looking news coverage. State-first reading does not frame this as proven public confusion. It frames it as an evidence-ecology problem: Brand3 cannot yet tell which surfaces belong to the same entity.

Evidence: `https://watermelon.sh/`, `https://github.com/watermelontools`, `https://github.com/WatermelonCorp/watermellon-registry`, `https://www.producthunt.com/products/watermelon`, `https://www.softwaresuggest.com/watermelon/alternatives`, `https://perishablenews.com/produce/fresh-pro-announces-honey-watermelons-brand-refresh-new-mascot/`

Confidence: medium for evidence fragmentation, low for audience-perception claims.

#### Product Hunt is a visibility signal, not traction proof

The Product Hunt profile can support the observation that a Watermelon product surface exists in an early-adopter channel. It cannot support a claim about adoption, feedback quality, or traction without engagement data and entity review.

Evidence: `https://www.producthunt.com/products/watermelon`

Confidence: low to medium.

### Presencia

#### The primary owned presence is small but legible

`watermelon.sh` gives Brand3 a usable primary surface: a focused domain, a clear startup/design-infrastructure line, and basic crawl/indexing files. The safer presence finding is that the owned footprint is narrow but legible, not that the brand has an SEO or acquisition problem.

Evidence: `https://watermelon.sh/`, `https://watermelon.sh/sitemap.xml`, `https://watermelon.sh/robots.txt`

Confidence: medium.

#### Developer surfaces widen presence but also raise review burden

GitHub surfaces add technical presence, but they also increase ambiguity. The report should show them as possible related developer surfaces, not as confirmed proof that the design-infrastructure brand has an active open-source community.

Evidence: `https://github.com/WatermelonCorp/watermellon-registry`, `https://github.com/watermelontools`

Confidence: low.

### Vitalidad

#### Vitality signals are present but not entity-safe

The baseline uses `watermelon.us` for founding, hiring growth, and funding signals. State-first reading holds those claims as potentially useful but not entity-safe for `watermelon.sh`. They should not be used to describe the audited brand's vitality until the relationship between surfaces is verified.

Evidence: `https://watermelon.us/`

Confidence: low.

#### External activity is mixed and partly irrelevant

The alternatives page, repository activity, and unrelated-looking produce/news reference do not form one clean vitality signal. The safer reading is that external collection is noisy: some surfaces may indicate low developer or marketplace activity, while others should be excluded or reviewed before interpretation.

Evidence: `https://www.softwaresuggest.com/watermelon/alternatives`, `https://github.com/WatermelonCorp/watermellon-registry`, `https://perishablenews.com/produce/fresh-pro-announces-honey-watermelons-brand-refresh-new-mascot/`

Confidence: low.

## Comparison

State-first wins on specificity because it names the actual problem: entity composition.

State-first wins on evidence binding because each finding says what the evidence can support and what it cannot support.

State-first wins on caveat discipline because uncertainty is centralized and then applied locally, rather than repeated as paragraph filler.

State-first wins on narrative cohesion because the dimensions now coordinate around the same entity-level condition.

State-first also wins on overreach risk. It avoids claims about unified roadmap, adoption, market traction, open-source strategy, and audience perception.

The baseline remains closer to the current report structure, but it is less safe. It sounds more complete because it fills gaps with generic strategy language.

## Verdict

Better than baseline: yes.

Safer than baseline: yes.

Clearer than baseline: yes.

Worth continuing: yes, but only as a lab-only generation trial.

Biggest improvement:

> The state-first version turns fragmented findings into one coordinated entity-composition reading.

Biggest remaining risk:

> False coherence could return immediately if related surfaces are treated as aliases or official proof.

What failed:

- This was manual generation, not a reusable generator.
- The better narrative is still heavily bounded because the evidence is genuinely ambiguous.
- The output is clearer, but not production-ready report copy.
- A shared evidence map is mandatory before generation; otherwise the model will merge surfaces again.
