# Lab-Only Findings Composition Prompt Experiment

Date: 2026-05-17

Status: offline lab experiment only. This does not change production prompts, scoring, report generation, report rendering, persisted payloads, Visual Signature, or runtime behavior.

## Purpose

Test one narrow question:

```text
Does explicit EntityNarrativeState context reduce defensive fragmentation in section 4 findings?
```

The experiment does not try to make prose more literary, more human, or more creative. It only tests whether a state-aware narrative pass can:

- reduce repeated caveats,
- bind findings more clearly to evidence coverage,
- keep entity ambiguity visible without turning it into strategy,
- avoid repeated generic Decision Space framing,
- preserve uncertainty without repeating it in every sentence.

## Inputs

The experiment uses existing offline artifacts:

- `examples/reports/narrative_harness/builtwith_kit_com.payload.json`
- `examples/reports/narrative_harness/iris.payload.json`
- `examples/reports/narrative_harness/watermelon.payload.json`
- `examples/reports/narrative_harness/entity_state/builtwith_kit_com.entity_narrative_state.v0.json`
- `examples/reports/narrative_harness/entity_state/iris.entity_narrative_state.v0.json`
- `examples/reports/narrative_harness/entity_state/watermelon.entity_narrative_state.v0.json`
- matching payload-level and render-aware diagnostics.

## Prompt Contract Under Test

This is a lab-only prompt contract, not a production prompt.

```text
You are rewriting section 4 findings for an offline Brand3 lab comparison.

Inputs:
- existing report_narrative payload
- payload-level Narrative Harness diagnostic
- render-aware Narrative Harness diagnostic
- offline EntityNarrativeState v0

Task:
Rewrite only the selected findings excerpt as a state-aware narrative finding.

Rules:
- Do not change scores.
- Do not invent market intent.
- Do not infer ownership from related surfaces.
- Do not promote low-confidence or review-gated state to fact.
- Do not repeat the same caveat per finding when the state already shows a global caveat budget issue.
- Keep observation separate from interpretation.
- Prefer one explicit uncertainty sentence over repeated defensive caveats.
- Mention evidence URL gaps as coverage limits, not as proof of weakness.
- Treat Decision Space as optional and only include it when specific.
- Do not use generic strategic filler such as "teams in this position typically".
```

## Cases

### Builtwith / Kit

Baseline issue:

The current payload repeats self-description caveats and generic decision framing while also mixing the audited `builtwith.kit.com` surface with third-party descriptions of BuiltWith as a technology intelligence provider.

Entity state used:

- `owned_claim_density.level`: `high`
- `safe_attribution_total`: `11`
- `corroboration_caveat_budget.status`: `over_budget`
- `evidence_url_coverage.findings_without_evidence_urls`: `4`
- `decision_space_mode.mode`: `hidden_generic`
- `primary_entity_signal.requires_human_review`: `true`

Baseline excerpt:

```text
The brand describes itself as 'the email-first operating system for creators who mean business' and states 'Make email your most valuable channel'. This description is based only on self-description; no external corroboration in the evidence pool.

This positioning suggests a focus on a specific user segment and a core value proposition centered around email as a primary business tool. It may indicate an intent to differentiate from broader productivity or CRM platforms.

Teams in this position typically choose between doubling down on the creator/email niche, expanding to adjacent creator tools, or broadening the platform's appeal to a wider business audience.
```

State-aware variant:

```text
The audited surface presents an email-first operating-system claim for creators, but the evidence set also contains third-party descriptions of BuiltWith as a B2B technology-intelligence provider. The useful finding is not a strategic choice between niches yet; it is an entity-composition problem.

Brand3 should treat the creator-email claim as owned positioning, the technology-intelligence signal as a separate external surface, and the missing evidence URLs as a coverage limit. Until the entity boundary is reviewed, the report can say the narrative is split, but should not recommend expansion, pivoting, or audience broadening.
```

Observed improvement:

- The caveat appears once instead of per sentence.
- Entity ambiguity becomes the core finding.
- Generic Decision Space is removed.
- Missing evidence URLs become a coverage constraint.

Remaining risk:

The variant is clearer, but still needs a verified entity boundary before it can become a production-safe finding.

### Iris

Baseline issue:

The current payload repeats owned-claim attribution and corroboration caveats while the entity-state output marks multiple ambiguous Iris-name surfaces that must not become aliases.

Entity state used:

- `owned_claim_density.level`: `high`
- `safe_attribution_total`: `15`
- `corroboration_caveat_budget.status`: `over_budget`
- `entity_aliases.needs_review`: `true`
- `observed_related_surfaces`: six `ambiguous_name_match` surfaces
- `evidence_url_coverage.findings_without_evidence_urls`: `6`

Baseline excerpt:

```text
The brand describes itself as creating 'complete brand identities for indie developers in minutes' and contrasts this with agencies that 'charge $40k'. This is based only on self-description; no external corroboration in the evidence pool.

This positioning suggests a focus on rapid, cost-effective brand development, potentially targeting a segment of the market underserved by traditional agencies. It may indicate a strategy to democratize brand creation.
```

State-aware variant:

```text
Iris has a clear owned claim: fast, low-cost brand identity creation for indie developers. That claim is legible, but the current evidence does not yet prove external adoption, agency displacement, or market democratization.

The stronger Brand3 reading is narrower: Iris is building its surface around speed, price contrast, and maker accessibility. Because the evidence set also contains unresolved Iris-name collisions, the report should keep the finding at the level of owned positioning and evidence quality, not audience psychology or category intent.
```

Observed improvement:

- Strong surface signal is preserved.
- Visual/perceptual confidence is not confused with evidentiary confidence.
- Name-collision ambiguity stays review-gated.
- The language avoids "democratize" as unsupported strategic elevation.

Remaining risk:

The variant still depends on manual restraint. A production prompt would need hard rules against turning speed and price contrast into broad market intent.

### Watermelon

Baseline issue:

The current payload repeats self-description caveats while the case pressure is really ecosystem ambiguity: design infrastructure, open-source copilot language, adjacent domains, developer surfaces, and repository surfaces.

Entity state used:

- `entity_aliases.needs_review`: `true`
- `observed_related_surfaces`: seven reviewed related surfaces
- `fallback_language_budget.mode`: `fallback_like_repetition`
- `safe_attribution_total`: `9`
- `corroboration_caveat_budget.status`: `over_budget`
- `decision_space_mode.mode`: `compressed_candidate`

Baseline excerpt:

```text
The brand appears on its own surface describing itself as 'Watermelon | Design Infrastructure for Modern Startups'. The brand also states, 'We started Watermelon because we saw the same problem everywhere -- startups move fast, but design becomes the bottleneck.' This observation is based only on self-description; no external corroboration in the evidence pool.

This self-positioning suggests the brand aims to address a specific pain point for early-stage companies, potentially positioning itself as a specialized solution provider.
```

State-aware variant:

```text
Watermelon presents a coherent owned problem statement around design infrastructure for fast-moving startups, but the surrounding evidence introduces adjacent Watermelon surfaces, developer references, repositories, and marketplace profiles that are not verified as the same entity.

The finding should therefore separate two layers: the audited surface frames design as a startup bottleneck; the broader evidence set creates ecosystem ambiguity. Brand3 can describe that ambiguity as a composition risk, but should not merge the surfaces into one roadmap or infer a unified platform strategy.
```

Observed improvement:

- The finding moves from repeated caveat to composition hierarchy.
- Related surfaces are treated as pressure, not aliases.
- The variant avoids roadmap/current-state over-binding.
- Generic strategic advice is removed.

Remaining risk:

The variant needs explicit related-surface metadata. Without that input, the builder correctly remains conservative, but the prompt has less useful state to work with.

## Manual Comparison

| Case | Baseline problem | State-aware gain | Residual risk |
|---|---|---|---|
| Builtwith / Kit | Entity split hidden under repeated caveats | Entity boundary becomes the finding | Needs human entity review |
| Iris | Owned claim inflated into market intent | Strong claim kept narrow and evidence-bound | Prompt must suppress unsupported category intent |
| Watermelon | Ecosystem ambiguity flattened into self-positioning | Composition hierarchy becomes explicit | Depends on reviewed related-surface input |

## What The Experiment Suggests

The offline state is useful when it is used as a composition constraint, not as content to quote.

The best variants do three things differently from the current payload:

1. They move repeated caveats into one global uncertainty frame.
2. They convert entity ambiguity into an explicit narrative condition.
3. They remove generic `typical_decision` prose unless the decision space is specific and evidence-bound.

## What This Does Not Prove

This does not prove that production prompts should change immediately.

It also does not prove that `EntityNarrativeState` should enter runtime. The experiment was written offline and manually reviewed. A real implementation would need deterministic pairing, prompt isolation, snapshot tests, and harness comparison before any opt-in product path.

## Recommended Next Step

Create a lab-only prompt runner or fixture generator that produces paired baseline/state-aware finding excerpts for the same cases, then scores only diagnostic deltas:

- repeated caveat count,
- evidence URL binding,
- repeated opener count,
- unsupported recommendation count,
- entity ambiguity handling,
- human reviewer preference.

Keep the result outside production reports.
