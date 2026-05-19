# Brand3 Lab-Only State-First Findings Generator v0 Spec

Date: 2026-05-17

Status: specification only. No implementation, runtime integration, scoring change, prompt rollout, renderer change, official report mutation, persisted payload change, Visual Signature change, UI change, persistence, or LLM runtime call is introduced by this document.

## Purpose

Define the contract for a future lab-only state-first findings generator.

The generator exists to test whether Brand3 can produce better §4 findings when generation is governed by shared composition state before dimension-level prose is written.

The goal is not:

- better style,
- warmer prose,
- shorter text,
- suppression of bad-looking caveats,
- or official report replacement.

The goal is:

```text
avoid false coherence by generating findings from:
entity state
+ evidence map
+ uncertainty model
+ dimension roles
```

## Core Research Question

```text
Can entity-state-first generation produce better Brand3 findings than the current dimension-by-dimension pipeline without inventing coherence or hiding uncertainty?
```

## Operating Principle

The generator must decide whether it can safely generate before it writes.

If the required state is missing, contradictory, too thin, or unsafe, the generator must return:

```text
No safe state-first generation candidate.
```

This is a valid output, not a failure.

## Scope

In scope:

- lab-only candidate findings,
- offline artifacts comparable to the manual state-first trials,
- baseline-vs-state-first comparison,
- explicit evidence boundaries,
- explicit uncertainty rules,
- intervention mode selection.

Out of scope:

- production report generation,
- scoring,
- report rendering,
- prompt rollout,
- Visual Signature integration,
- persistence,
- user-facing claims of improvement,
- automatic replacement of existing findings.

## Required Inputs

### 1. `report_narrative_payload`

Required.

Expected shape:

- `summary`
- `synthesis_prose`
- `tensions_prose`
- `findings_by_dimension`
- optional `run_id`
- optional `generated_at`
- optional `source`

The generator must treat this as baseline material. It must not mutate it.

### 2. `payload_diagnostic`

Required unless it can be built offline in the same lab process.

Expected source:

- `audit_report_narrative_payload(...)`

Minimum useful fields:

- warning count,
- finding count,
- findings without evidence URLs,
- safe attribution counts,
- fallback evidence-opening counts,
- external corroboration caveat counts,
- generic decision-space counts,
- repeated opener metrics.

### 3. `render_diagnostic`

Required unless it can be built offline in the same lab process.

Minimum useful fields:

- visible repeated openings,
- visible safe attribution count,
- visible external-corroboration caveat count,
- visible fallback repetition,
- visible evidence chip count,
- suppressed-by-rendering list,
- still-visible risks.

### 4. `entity_narrative_state`

Required.

Minimum useful fields:

- status/offline flags,
- primary entity signal,
- entity aliases or observed related surfaces,
- owned-claim density,
- source ownership summary,
- evidence URL coverage,
- primary tension,
- contradiction candidates,
- decision-space mode,
- compression candidates.

The generator must reject state that is not explicitly offline/lab-only.

### 5. Optional `observed_related_surfaces`

Allowed only when explicitly reviewed or deterministically safe.

Must not be inferred by the generator from:

- arbitrary evidence URLs,
- name similarity alone,
- third-party mentions,
- search co-occurrence.

### 6. Optional `snapshot_metadata`

Allowed for:

- brand name,
- target URL,
- run ID,
- report token,
- score summary,
- dimension score summary.

The generator must not use scores to justify prose. Scores are context only.

## Preconditions To Generate

The generator may generate a state-first candidate only when all required conditions are met:

1. A report narrative payload exists.
2. There is at least one finding in `findings_by_dimension`.
3. Payload diagnostics exist or can be built offline.
4. Render diagnostics exist or can be built offline.
5. EntityNarrativeState exists.
6. EntityNarrativeState status says:
   - offline,
   - experimental,
   - not runtime,
   - not scoring,
   - not rendering,
   - not prompt,
   - not persisted report narrative.
7. The generator can build a meaningful evidence map.
8. Unresolved ambiguity is explicit rather than inferred.
9. Related surfaces, if present, are explicit or reviewed.
10. Every generated finding can state at least one evidence boundary.

If any hard precondition fails, output `No safe state-first generation candidate`.

## Reasons To Return No Candidate

Return no candidate when:

- `report_narrative_payload` is missing,
- findings are absent,
- diagnostics are missing and cannot be built offline,
- EntityNarrativeState is missing,
- EntityNarrativeState is not marked offline/lab-only,
- entity ambiguity is implied but not explicit,
- related surfaces appear only through name similarity,
- evidence is too thin to create a meaningful evidence map,
- the only possible improvement is stylistic,
- uncertainty would need to be hidden to make the result read well,
- a stable/healthy case would be overstructured by a rewrite,
- the generator cannot separate observation from interpretation.

## Intervention Modes

The generator must choose one mode before writing.

### 1. `none`

Use when:

- baseline is already coherent,
- evidence is too thin,
- no meaningful state-first improvement is available,
- any rewrite would mostly be stylistic.

Output:

```text
No safe state-first generation candidate.
```

### 2. `light`

Use when:

- entity is stable,
- evidence is adequate,
- state-first can improve evidence boundaries or caveat discipline,
- but heavy rewrite would add unnecessary complexity.

Typical cases:

- LaunchDarkly-like healthy controls,
- Netlify-like fallback compression when safe.

Allowed behavior:

- compact global caveat,
- dimension role clarification,
- local evidence-boundary improvements,
- no artificial entity tension.

### 3. `strong`

Use when:

- baseline risks false coherence,
- related surfaces may be collapsed into aliases,
- owned claims are repeatedly treated as proof,
- visual/perceptual confidence may become evidentiary confidence,
- external caveats repeat because uncertainty is not centralized.

Typical cases:

- Builtwith / Kit,
- Iris,
- Watermelon.

Allowed behavior:

- global governing caveat,
- explicit entity-boundary reading,
- review-gated related surfaces,
- dimension-level redistribution of evidence and uncertainty.

Forbidden behavior:

- resolving the ambiguity,
- inferring ownership,
- inferring intent,
- turning uncertainty into confident strategy.

## Output Contract

The generator output must be JSON-serializable and may have an accompanying Markdown rendering.

Required top-level fields:

- `version`
- `created_at`
- `case_id`
- `status`
- `input_artifacts`
- `generation_decision`
- `baseline`
- `shared_entity_state`
- `shared_evidence_map`
- `global_uncertainty_model`
- `state_first_finding_plan`
- `generated_state_first_findings`
- `comparison`
- `verdict`

### `status`

Required flags:

- `lab_only: true`
- `runtime_integration: false`
- `prompt_rollout: false`
- `scoring_change: false`
- `renderer_change: false`
- `report_mutation: false`
- `visual_signature_change: false`
- `production_ready: false`

### `generation_decision`

Required fields:

- `mode`: `none | light | strong`
- `candidate_available`: boolean
- `reason`
- `blocked_reasons`
- `preconditions_passed`
- `preconditions_failed`

If `mode` is `none`, `generated_state_first_findings` must be empty or null and `reason` must say why.

### `baseline`

Required fields:

- baseline summary,
- measured problems,
- primary baseline failure,
- dimensions present,
- findings count.

### `shared_entity_state`

Required fields:

- primary entity signal,
- entity ambiguity status,
- observed related surfaces if available,
- owned-claim density,
- evidence coverage,
- active budgets,
- primary tension if available.

This section must summarize state. It must not promote state fields into strategic claims.

### `shared_evidence_map`

Required fields:

- evidence used,
- evidence missing,
- owned/self-description evidence,
- third-party/external evidence,
- technical/configuration evidence if relevant,
- evidence that must not be over-interpreted.

### `global_uncertainty_model`

Required fields:

- `can_state_as_observation`
- `can_state_as_interpretation`
- `must_remain_uncertain`
- `requires_human_review`
- `must_not_infer`

### `state_first_finding_plan`

Required fields:

- coordination rules,
- dimension roles,
- caveat strategy,
- evidence-binding strategy,
- overreach suppression rules.

### `generated_state_first_findings`

Required only when `candidate_available` is true.

Each finding must include:

- dimension,
- title,
- finding,
- evidence URLs or explicit missing-evidence note,
- confidence,
- uncertainty note when applicable,
- review flag when applicable.

### `comparison`

Required fields:

- specificity,
- evidence binding,
- entity coherence,
- caveat discipline,
- uncertainty preservation,
- overreach risk,
- narrative cohesion,
- whether the result stayed light when appropriate.

### `verdict`

Required fields:

- better than baseline,
- safer than baseline,
- clearer than baseline,
- worth continuing,
- biggest improvement,
- biggest remaining risk,
- what failed.

## Evidence Rules

1. Evidence URLs are not decorative. Every generated claim must know what evidence supports it.
2. Missing evidence is allowed, but must be visible.
3. Owned claims support positioning observations, not market validation.
4. External trust/security pages support scrutiny signals, not broad perception claims.
5. Product Hunt, alternatives pages, articles, repositories, or docs do not prove ownership without review.
6. Scores must not be used as proof inside findings.
7. Visual/perceptual strength must not compensate for weak evidentiary confidence.
8. Evidence limits should be centralized when global and local when dimension-specific.

## Uncertainty Rules

1. Caveat compression is valid; caveat deletion is not.
2. A compressed caveat must remain visible.
3. Entity uncertainty must be stated before dimension findings when it governs the case.
4. Related surfaces must be marked as review-gated unless deterministic and explicit.
5. Interpretation must remain separate from observation.
6. Strategic intention must not be inferred from surface signals alone.
7. Healthy cases must not receive artificial tension.
8. Thin cases must not receive synthetic depth.

## Prompt/Generation Guardrails For Future Implementation

If a future implementation uses an LLM inside the lab-only runner, the prompt must include these constraints:

- do not invent new evidence,
- do not cite unavailable evidence,
- do not resolve entity ambiguity,
- do not infer ownership,
- do not use scores as prose justification,
- do not write generic Decision Space,
- do not hide uncertainty,
- do not convert related surfaces into aliases,
- do not turn state fields into quoted report content,
- return no candidate if conditions are unsafe.

This spec does not implement that prompt.

## Expected Tests For Future Implementation

### Output Shape

- stable output shape for all modes,
- JSON serializable,
- no candidate output when mode is `none`,
- required status flags remain false for runtime/scoring/prompts/rendering/Visual Signature.

### Preconditions

- missing payload returns no candidate,
- missing findings returns no candidate,
- missing EntityNarrativeState returns no candidate,
- non-offline state returns no candidate,
- unreviewed related surfaces return no candidate or review-gated blocked state,
- thin payload can select `none` or `light`, not `strong`.

### Evidence Discipline

- generated findings include evidence URLs or explicit missing-evidence notes,
- owned claims are not treated as market validation,
- external trust pages are not treated as broad reputation proof,
- repositories do not imply official roadmap without review,
- scores are not used as evidence.

### Uncertainty Discipline

- caveats are compressed but not deleted,
- entity ambiguity is preserved,
- visual confidence does not become evidentiary confidence,
- healthy cases do not gain false tension,
- thin cases do not gain artificial depth.

### Case Fixtures

Future implementation should test:

- Builtwith / Kit selects `strong`,
- Iris selects `strong`,
- Watermelon selects `strong`,
- LaunchDarkly selects `light`,
- Netlify mock selects `light` or `none` depending on evidence-map quality.

## Explicit Non-Goals

Do not use v0 to:

- modify Brand Audit output,
- modify scoring,
- modify prompts in production,
- modify report renderer,
- modify persisted report narrative,
- integrate Visual Signature,
- create official Lab claims,
- persist generated candidates,
- replace human review,
- automate entity discovery,
- infer related surfaces.

## Next Implementation Boundary

The next safe implementation, if approved, should be:

```text
src/reports/state_first_findings_generator.py
```

with a single pure function:

```python
generate_state_first_findings_candidate(
    payload: dict,
    *,
    payload_diagnostic: dict,
    render_diagnostic: dict,
    entity_state: dict,
    snapshot: dict | None = None,
) -> dict
```

It must be offline, lab-only, deterministic around precondition and mode selection, and must not be wired into report generation or rendering.

