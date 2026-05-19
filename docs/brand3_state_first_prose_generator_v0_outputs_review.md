# Brand3 State-First Prose Generator v0 Outputs Review

Date: 2026-05-17

Scope: lab-only review. No runtime integration, prompt rollout, scoring change, renderer change, report mutation or Visual Signature change.

## What Was Generated

The new deterministic generator was run against the three reviewed planning artifacts:

- Iris
- Watermelon
- LaunchDarkly

Generated outputs:

- `examples/reports/narrative_harness/state_first_prose_generator_v0/iris.state_first_prose_generator_v0.json`
- `examples/reports/narrative_harness/state_first_prose_generator_v0/watermelon.state_first_prose_generator_v0.json`
- `examples/reports/narrative_harness/state_first_prose_generator_v0/launchdarkly.state_first_prose_generator_v0.json`

Manual references:

- `examples/reports/narrative_harness/state_first_prose_v0/iris.state_first_prose_v0.json`
- `examples/reports/narrative_harness/state_first_prose_v0/watermelon.state_first_prose_v0.json`
- `examples/reports/narrative_harness/state_first_prose_v0/launchdarkly.state_first_prose_v0.json`

## Summary

The generator works structurally.

It does not yet match the best manual prose.

That is acceptable for v0. The important test was not whether the text sounds finished. The important test was whether the generator preserves the epistemic boundaries that made the manual candidates useful.

It does.

## Case Review

### Iris

Mode: `strong`

Pressure subtype: `name_collision`

The generator correctly:

- anchors `irisdesign.dev` as the audited surface,
- treats similarly named Iris domains as ambiguity pressure,
- avoids alias and ownership inference,
- keeps human review required.

It is weaker than the manual candidate because it does not yet distinguish the specific risk created by each Iris-like surface. The manual version is sharper around Iris AI/open-source activity versus the audited design surface.

Verdict: structurally valid, editorially partial.

### Watermelon

Mode: `strong`

Pressure subtype: `ecosystem_surface_pressure`

The generator correctly:

- separates audited surface from ecosystem context,
- blocks ownership inference,
- blocks roadmap inference from repositories,
- blocks traction inference from marketplace surfaces,
- keeps human review required.

It is weaker than the manual candidate because it handles ecosystem evidence at a broad family level. The manual version is sharper about unrelated watermelon references and the difference between adjacent domains, repositories, marketplaces and unrelated mentions.

Verdict: structurally valid, editorially partial.

### LaunchDarkly

Mode: `light`

Pressure subtype: `stable_entity_evidence_binding`

The generator correctly:

- keeps LaunchDarkly entity-stable,
- does not invent ambiguity,
- does not invent hidden tension,
- treats missing evidence as coverage limit,
- keeps global human review false.

This is the strongest generated output because the required move is simpler: proof distribution, not ambiguity handling.

Verdict: structurally valid and close to manual.

## What Worked

- Output shape matches the manual candidate structure.
- Mode and pressure subtype are preserved.
- Strong cases remain review-gated.
- Light stable case remains restrained.
- Every dimension includes:
  - evidence boundary,
  - uncertainty retained,
  - overreach avoided.
- Unsupported subtypes abstain.

## What Is Still Weak

The generator still writes with broad templates.

It does not yet:

- rank evidence importance per dimension,
- use relation types deeply enough,
- distinguish all source families with manual-level nuance,
- compress prose as sharply as the manual candidates,
- decide which dimension deserves more or less text.

That means it is useful as a candidate generator, not as report prose.

## Safety Assessment

The generated candidates are safer than the baseline because they preserve boundaries:

- no false aliasing,
- no false ecosystem ownership,
- no invented tension in stable cases,
- no score-as-evidence writing,
- no runtime mutation.

But they are not production-ready.

The unsafe next moves would be:

- wiring this into official report generation,
- replacing official findings,
- enabling runtime generation,
- using it as a prompt rollout,
- removing human review from strong-mode ambiguity cases.

## Recommendation

Continue lab-only.

The next step should be a side-by-side comparison artifact:

```text
baseline finding
vs manual state-first candidate
vs generated state-first candidate
```

for Iris, Watermelon and LaunchDarkly.

That is the clearest way to decide whether the generator is good enough to show in Brand3 Lab or whether its prose still needs another deterministic refinement pass.
