# Brand3 State-First Generator v0 Outputs Review

Date: 2026-05-17

Scope: review of lab-only generated artifacts. No runtime integration, prompt rollout, scoring change, renderer change, report mutation, persisted payload change, Visual Signature change, UI change, or LLM call was introduced.

## Purpose

Review the first outputs from `src/reports/state_first_findings_generator.py` against the five existing state-first research cases:

- Builtwith / Kit
- Iris
- Watermelon
- LaunchDarkly
- Netlify mock

The generator v0 is not a prose generator. It is a gate and skeleton compiler:

1. decide whether generation is safe,
2. select intervention mode,
3. build a structured lab-only candidate artifact,
4. preserve evidence and uncertainty boundaries.

## Generated Outputs

Files created under:

```text
examples/reports/narrative_harness/state_first_generation_v0/
```

| Case | Output | Mode | Candidate |
|---|---|---:|---|
| Builtwith / Kit | `builtwith_kit_com.state_first_generator_v0.json` | `strong` | yes |
| Iris | `iris.state_first_generator_v0.json` | `strong` | yes |
| Watermelon | `watermelon.state_first_generator_v0.json` | `strong` | yes |
| LaunchDarkly | `launchdarkly.state_first_generator_v0.json` | `light` | yes |
| Netlify mock | `netlify_snapshot_mock.state_first_generator_v0.json` | `light` | yes |

Mode selection matches the manual trial synthesis.

## Correct Mode Selection

### Strong Mode

`strong` was selected for:

- Builtwith / Kit,
- Iris,
- Watermelon.

This is correct.

These cases involve one or more of:

- entity-boundary ambiguity,
- name-collision ambiguity,
- ecosystem/multi-surface pressure,
- related surfaces that must remain review-gated,
- high caveat repetition,
- risk of false coherence.

The generator correctly treats them as cases where shared state must govern dimension findings.

### Light Mode

`light` was selected for:

- LaunchDarkly,
- Netlify mock.

This is also correct.

LaunchDarkly has a stable entity and should not be dramatized. The useful intervention is evidence discipline, not entity-composition rewrite.

Netlify mock is sparse and fallback-like. The useful intervention is fallback compression and evidence-boundary clarity, not strategic depth.

## Where v0 Is Useful

### 1. Gating

The generator now performs the most important first behavior:

```text
decide mode before writing
```

This protects against the old failure where Brand3 always produced dimension prose regardless of whether the state was ready.

### 2. Lab-Only Safety

Every generated artifact carries explicit false flags for:

- runtime integration,
- prompt rollout,
- scoring change,
- renderer change,
- report mutation,
- Visual Signature change,
- production readiness.

That keeps the research layer separated from Brand Audit production output.

### 3. Evidence Boundary Skeleton

Every generated candidate finding includes:

- evidence URLs when available,
- missing-evidence note when not available,
- confidence,
- uncertainty note,
- human review flag when appropriate.

This is a real improvement over pure prose generation because the evidence boundary is structural, not decorative.

### 4. Intervention Restraint

LaunchDarkly being `light` is an important pass.

The generator did not mistake repeated caveats alone for entity ambiguity. That avoids overstructuring a healthy case.

## Where v0 Is Too Conservative

v0 does not generate the kind of state-first prose seen in the manual trials.

For example, the manual Builtwith / Kit trial says the core issue is a collision between Kit creator/email positioning and BuiltWith web-intelligence positioning.

The v0 output correctly identifies strong mode and evidence boundaries, but the generated findings remain generic skeletons such as:

```text
State-first candidate keeps this finding bounded by entity and evidence constraints.
```

That is acceptable for v0, but it is not yet the real value demonstrated by the manual trials.

## Where v0 Cannot Replace Manual Reasoning

v0 cannot yet:

- synthesize a precise entity-level finding,
- rewrite findings with Brand3 editorial quality,
- decide which baseline findings should be merged,
- create a nuanced global uncertainty paragraph,
- distinguish subtle differences between ecosystem ambiguity and name-collision ambiguity in prose,
- judge whether a case has become too diagnostic for final report use.

It compiles a safe structure. It does not yet perform state-first narrative generation.

## Uncertainty Preservation

v0 preserves uncertainty well.

It does this through:

- `generation_decision`,
- `missing_evidence_note`,
- `uncertainty_note`,
- `requires_human_review`,
- mode-specific global caveats,
- explicit status flags.

The main limitation is that the uncertainty is mechanical. It is structurally correct, but not yet editorially intelligent.

## False Coherence Avoidance

v0 avoids false coherence at the structural level.

It does not:

- infer ownership,
- resolve related-surface ambiguity,
- use scores as evidence,
- promote visual/perceptual signal into evidentiary confidence,
- convert related surfaces into aliases.

However, the generated prose skeleton is too generic to prove false coherence avoidance at final writing quality. That still requires a future controlled generation step.

## Comparison With Manual Trials

| Case | Manual trial value | v0 value | Gap |
|---|---|---|---|
| Builtwith / Kit | Names the Kit/BuiltWith entity collision directly. | Selects `strong` and preserves evidence boundaries. | Needs real state-aware prose. |
| Iris | Prevents Iris-name collisions from becoming brand architecture. | Selects `strong` from reviewed related surfaces. | Needs sharper name-collision language. |
| Watermelon | Separates primary surface from ecosystem pressure. | Selects `strong` and review-gates surfaces. | Needs ecosystem-specific synthesis. |
| LaunchDarkly | Stays light and avoids false tension. | Selects `light`. | Needs better proof-distribution prose. |
| Netlify mock | Compresses fallback repetition without adding depth. | Selects `light`. | May need `none` if evidence map is too thin in stricter mode. |

## Recommendation

Continue, but do not treat v0 as a generator yet.

The next phase should improve one layer only:

```text
state-first planning quality
```

Before adding LLM or prose generation, v0 should become better at producing:

- case-specific global caveat,
- case-specific finding plan,
- dimension-level merge/compress suggestions,
- clear distinction between `light` and `strong` output expectations.

Do not move this into runtime.

Do not expose it as improved report output.

Do not call it production-ready.

## Suggested Next Goal

```text
Improve State-First Generator v0 Planning Layer
```

The goal should focus on:

- case-specific `global_caveat`,
- stronger `state_first_finding_plan`,
- better use of `primary_entity_signal`,
- better use of `observed_related_surfaces`,
- better differentiation between entity ambiguity, fallback repetition, and healthy proof-distribution cases.

It should not add LLM prose generation yet.

