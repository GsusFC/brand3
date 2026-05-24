# Brand3 Phase 2 Narrative Harness Candidate Set

Date: 2026-05-16

Scope: corpus-selection and methodology memo only. Brand3 was not run. No fixtures, prompts, scoring, generation, rendering, persisted payload format, Visual Signature code, `EntityNarrativeState` builder, runtime wiring, or LLM runtime generation were added.

## Purpose

Phase 1 established that Brand3's narrative cohesion risks are measurable:

- owned-claim repetition,
- fallback evidence-opening repetition,
- external corroboration caveat repetition,
- repeated opener overuse,
- missing evidence URL coverage,
- entity fragmentation,
- premature or repeated decision framing.

Phase 2 should not start by adding more checks at random. It should select cases that put pressure on the emerging composition model in different ways.

This memo defines the next candidate set for narrative/composition exploration:

1. LaunchDarkly
2. Iris
3. Watermelon

These are not conclusions about the brands. They are pre-analysis hypotheses about what each case is expected to test.

## Candidate Comparison Table

| Candidate | Primary narrative pressure | Expected evidence quality | Expected ambiguity level | Expected owned-claim density | Expected contradiction pressure | Expected Visual Signature pressure | Expected usefulness for Phase 2 |
|---|---|---|---|---|---|---|---|
| LaunchDarkly | Healthy high-evidence narrative control | High | Low | Low to moderate | Low | Low to moderate | Tests whether the state can represent a strong case without forcing warnings |
| Iris | Strong visual identity with weaker corroboration | Mixed | Medium | High | Medium | High | Tests owned-claim caution, visual/perceptual pressure, and AI-claim boundaries |
| Watermelon | Ecosystem and composition hierarchy | Mixed | High | Medium | High | Medium to high | Tests entity fragmentation, roadmap/current-state ambiguity, and contradiction prioritization |

## 1. LaunchDarkly

### Why Selected

LaunchDarkly is selected as the healthy/high-evidence/low-ambiguity candidate.

Phase 1 identified the need for a third fixture that is neither Builtwith-like nor Netlify-like. LaunchDarkly should test whether the emerging `EntityNarrativeState` shape can represent a relatively healthy report without turning into a list of forced warnings.

Expected role:

- positive control,
- high evidence coverage pressure,
- stable entity signal pressure,
- low repetition-family pressure.

### Expected Narrative-Risk Families

Expected low risk:

- safe attribution repetition,
- external corroboration caveat repetition,
- fallback evidence-opening repetition,
- entity fragmentation.

Expected possible risk:

- generic enterprise-platform language,
- score-first explanation,
- repetition around product category or feature-management language.

The useful test is whether the harness can remain quiet when the report is actually well supported.

### Expected Evidence Patterns

Expected evidence pattern:

- stronger third-party or ecosystem corroboration,
- clearer public product/category footprint,
- likely stronger source diversity than Builtwith or Netlify mock,
- fewer findings without evidence URLs.

Healthy outcome:

- strong evidence URL coverage,
- low warning density,
- no forced caveat repetition,
- stable `primary_entity_signal`,
- no major `observed_related_surfaces` ambiguity.

Failure outcome:

- the harness still produces warnings because the prose is formulaic despite strong evidence,
- the report overuses generic enterprise SaaS language,
- evidence is present but not carried into visible findings.

### Composition Pressures

LaunchDarkly should pressure the composition model in the opposite direction from Builtwith.

Instead of asking "how do we handle weak corroboration?", it asks:

```text
can Brand3 avoid inventing problems when evidence is strong?
```

Useful state expectations:

- `owned_claim_density`: low or moderate,
- `evidence_url_coverage`: strong,
- `repeated_opener_budget`: within budget,
- `fallback_language_budget`: inactive,
- `contradiction_candidates`: empty or weak.

### Stress On Brand3 Systems

Narrative Harness:

- should avoid false positives,
- should prove that clean or low-warning reports are possible outside synthetic controls.

Render-aware diagnostics:

- should confirm that evidence chips remain visible,
- should not detect hidden payload problems that become visible only after rendering.

EntityNarrativeState:

- should support inactive budgets,
- should represent a healthy state without forcing `compression_candidates`.

Visual Signature interpretation pressure:

- should remain secondary,
- should not over-interpret a polished enterprise surface as strategy without evidence.

## 2. Iris

### Why Selected

Iris is selected as the strong visual identity / weak external corroboration candidate.

The expected value is pressure on the boundary between perceptual reading and evidentiary caution. If the surface is visually strong but external corroboration is weaker, Brand3 must avoid turning visual confidence into strategic certainty.

Expected role:

- owned-claim density test,
- visual/perceptual pressure test,
- AI-heavy claim caution test,
- safe attribution and corroboration-caveat stress case.

### Expected Narrative-Risk Families

Expected higher risk:

- safe attribution repetition,
- external corroboration caveat repetition,
- unsupported emotional or perceptual projection,
- false sophistication language,
- owned claims being treated as external validation.

Expected possible risk:

- overuse of phrases such as "the brand describes itself",
- repeated lack-of-corroboration caveats,
- aesthetic evidence being used to imply business maturity.

Healthy outcome:

- owned claims are attributed once or cleanly bounded,
- visual strength is described as surface evidence, not proof of market position,
- low-confidence claims require review,
- caveats do not repeat mechanically across findings.

Failure outcome:

- the report becomes defensive and repetitive,
- every dimension repeats self-description caveats,
- visual polish is converted into unsupported strategic confidence,
- AI-related claims are amplified without external evidence.

### Expected Evidence Patterns

Expected evidence pattern:

- heavier owned-surface evidence,
- possibly limited third-party corroboration,
- high perceptual/visual signal,
- claims that may need careful attribution.

Key evidence question:

```text
Is the report grounded in observable surface behavior, or is it borrowing certainty from owned claims and visual execution?
```

### Composition Pressures

Iris should pressure whether the state can distinguish:

- strong surface signal,
- weak external support,
- owned claims,
- perceptual interpretation,
- unsupported strategic inference.

Useful state expectations:

- `owned_claim_density`: moderate to high,
- `source_ownership_summary`: important,
- `attribution_budget`: active,
- `corroboration_caveat_budget`: likely active,
- `primary_tension`: review-gated,
- `compression_candidates`: possible but suggested-only.

### Stress On Brand3 Systems

Narrative Harness:

- should detect safe attribution overuse if it appears,
- should separate safe attribution from unsafe validation,
- should catch repeated corroboration caveats.

Render-aware diagnostics:

- should show whether repetition remains visible after conditional `Decision space` rendering,
- should distinguish visible evidence chips from total report links.

EntityNarrativeState:

- should test whether source ownership and attribution budgets are actually useful beyond Builtwith.

Visual Signature interpretation pressure:

- high.
- The surface may invite perceptual conclusions, so the system must keep observation, interpretation, and low-confidence inference separated.

## 3. Watermelon

### Why Selected

Watermelon is selected as the ecosystem / composition ambiguity candidate.

The expected value is pressure on entity hierarchy and narrative consolidation. If the case includes product, ecosystem, roadmap, integrations, or multiple adjacent surfaces, Brand3 must decide what the audited entity is before writing dimension findings.

Expected role:

- entity fragmentation test,
- roadmap/current-state ambiguity test,
- contradiction prioritization test,
- composition hierarchy test.

### Expected Narrative-Risk Families

Expected higher risk:

- entity drift,
- repeated opener overuse while trying to explain multiple surfaces,
- contradiction smoothing,
- unsupported roadmap interpretation,
- evidence split across current product, ecosystem claims, and future-facing language.

Expected possible risk:

- the report treats adjacent surfaces as one entity without review,
- roadmap language is written as current-state fact,
- ecosystem complexity becomes generic "platform" prose,
- contradictions are flattened into a vague tension.

Healthy outcome:

- primary entity signal is explicit,
- related surfaces are listed cautiously as `observed_related_surfaces`,
- roadmap claims are separated from observed current-state signals,
- contradiction candidates are evidence-anchored and review-gated,
- dimension findings do not drift between different entity frames.

Failure outcome:

- findings alternate between product, ecosystem, and roadmap without hierarchy,
- the report invents a stable strategy from fragmented evidence,
- contradiction pressure is smoothed into generic synthesis,
- evidence URLs are present but do not support the claims they are attached to.

### Expected Evidence Patterns

Expected evidence pattern:

- mixed owned and product/ecosystem sources,
- possible roadmap or future-facing language,
- possible integration or partner references,
- potential gaps between stated ambition and observable current state.

Key evidence question:

```text
Can Brand3 establish a primary entity read without collapsing related surfaces into one overconfident narrative?
```

### Composition Pressures

Watermelon should pressure the fields that remain most experimental:

- `primary_entity_signal`,
- `observed_related_surfaces`,
- `primary_tension`,
- `contradiction_candidates`,
- `compression_candidates`.

Useful state expectations:

- `entity_aliases.observed_related_surfaces`: important,
- `primary_tension`: likely review-gated,
- `contradiction_candidates`: possible,
- `decision_space_mode`: may need dimension-level compression rather than per-finding advice.

### Stress On Brand3 Systems

Narrative Harness:

- may catch repetition, but will not fully understand entity hierarchy.
- This case will expose the limits of lexical diagnostics.

Render-aware diagnostics:

- should show whether repeated language remains visible,
- but will not prove whether the entity hierarchy is coherent.

EntityNarrativeState:

- high stress.
- This is the candidate most likely to justify a future state contract if the report fragments across surfaces.

Visual Signature interpretation pressure:

- medium to high.
- Visual identity may help show hierarchy or product maturity, but must not replace evidence about current-state versus roadmap.

## Why Not Selected Yet

### Vercel

Vercel is relevant but not selected in this first Phase 2 set because it may overlap with LaunchDarkly as a high-evidence, developer-platform control.

Potential later use:

- strong ecosystem,
- high public evidence,
- possible overlap between product, platform, and deployment infrastructure.

Reason to wait:

- it may be too familiar and too well documented,
- it could reduce pressure on weak-evidence and ambiguity scenarios in this first set.

### Supabase

Supabase is not selected yet because it may be a strong ecosystem case, but Watermelon is currently the sharper pressure test for composition ambiguity.

Potential later use:

- open-source ecosystem narrative,
- database/platform category framing,
- community versus enterprise positioning.

Reason to wait:

- high public visibility may make the evidence case too easy for this phase,
- it may be better as a later comparison against Watermelon.

### Sentry

Sentry is not selected yet because it likely functions as a healthy or high-evidence developer-tools case.

Potential later use:

- strong category clarity,
- technical credibility,
- enterprise/developer tone analysis.

Reason to wait:

- it may not pressure owned-claim density or entity ambiguity enough for the immediate candidate set.

### Spooky

Spooky is not selected yet because it may be too close to a visual/perceptual or weak-corroboration case, overlapping with Iris.

Potential later use:

- strong mood and visual language,
- possible thin external evidence,
- perceptual interpretation boundary testing.

Reason to wait:

- Phase 2 needs one visual-pressure case first; adding several could over-bias the set toward aesthetic interpretation.

### Vexture

Vexture is not selected yet because it likely belongs to a later thin-signal or low-specificity stress set.

Potential later use:

- weak evidence coverage,
- template-like or generic surface risk,
- negative/thin perceptual reading.

Reason to wait:

- Phase 2 first needs a healthy control, a visual/owned-claim case, and an ambiguity case before testing thinner or weaker surfaces.

## Methodological Status

This candidate set is still corpus-selection and methodology work.

It is not:

- runtime integration,
- prompt redesign,
- scoring redesign,
- report rendering redesign,
- Visual Signature integration,
- fixture creation,
- report generation,
- production rollout.

The candidates should be used to decide what to audit next, not to infer conclusions before running Brand3.

## Recommended Use In Phase 2

Recommended sequence:

1. Run Brand3 on LaunchDarkly first.

   Purpose: establish whether a healthy/high-evidence case can pass with low warnings.

2. Run Iris second.

   Purpose: pressure owned claims, attribution budgets, corroboration caveats, and perceptual overreach boundaries.

3. Run Watermelon third.

   Purpose: pressure entity hierarchy, current-state versus roadmap ambiguity, and contradiction candidates.

4. Only then decide whether to create additional offline entity-state fixtures.

   The fixtures should be created from measured outputs, not from these pre-analysis expectations.

5. Do not design the builder until after this set has produced real diagnostics.

## Phase 2 Decision Criteria

After running the candidate set, Phase 2 should ask:

- Did LaunchDarkly stay clean or low-warning?
- Did Iris reproduce Builtwith-like owned-claim/caveat repetition?
- Did Watermelon expose entity fragmentation beyond lexical repetition?
- Did evidence URL coverage improve or remain uneven?
- Did render-aware diagnostics add enough signal beyond payload diagnostics?
- Did `EntityNarrativeState` fields feel useful, or did the case require fields that are still premature?

Only if those questions produce stable answers should Brand3 move toward a minimal state contract or offline builder.
