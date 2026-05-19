# Brand3 State-First Generation Trials Synthesis

Date: 2026-05-17

Scope: research synthesis only. No runtime integration, prompt rollout, scoring change, renderer change, report mutation, persisted payload change, Visual Signature change, UI change, or automated generator was added.

## Executive Judgment

The five lab-only trials are enough to justify a new research phase:

```text
State-First Narrative Generation Research
```

They are not enough to justify production use.

The result is stronger than a style improvement. Across the trials, the useful change is that findings are governed by shared state before dimension prose is written:

- entity state,
- evidence map,
- uncertainty model,
- dimension roles.

That reduces a specific failure in the current pipeline:

```text
findings are locally plausible,
but the report can still create false coherence because each dimension writes without shared epistemic coordination.
```

## Trial Matrix

| Case | Pressure family | State-first result | Strength of signal |
|---|---|---|---|
| Builtwith / Kit | Entity-boundary collision | Strong improvement. Entity ambiguity becomes the governing condition instead of hidden fragmentation. | High |
| Iris | Name-collision ambiguity | Strong improvement. Similar names are not converted into aliases or one strategy. | High |
| Watermelon | Ecosystem ambiguity | Strong improvement. Related surfaces stay review-gated instead of becoming one platform story. | High |
| LaunchDarkly | Healthy / high-evidence control | Moderate improvement. Main value is restraint and evidence discipline. | Medium |
| Netlify mock | Fallback repetition control | Modest improvement. Main value is fallback compression, not deeper strategy. | Low to medium |

## What State-First Actually Improves

### 1. Entity Coherence

This is the strongest result.

Builtwith / Kit, Iris, and Watermelon all show that state-first generation can prevent the model from collapsing distinct uncertainty types into one confident story.

Examples:

- Builtwith / Kit: Kit creator/email positioning and BuiltWith web-intelligence positioning must not be merged.
- Iris: Iris-name collisions must not become false brand architecture.
- Watermelon: ecosystem surfaces must not become one roadmap or one proof chain.

This is not cosmetic. It changes what the report is allowed to know.

### 2. Evidence Binding

State-first improves evidence binding because every generated finding has a clearer evidence boundary:

- what the evidence supports,
- what it does not support,
- what remains review-gated.

It does not fix the underlying payload issue where findings may lack evidence URLs. That remains a data-contract problem.

### 3. Caveat Discipline

The trials consistently show that repeated caveats can be moved from paragraph spam into shared uncertainty rules.

This is an improvement only if uncertainty remains visible.

The rule should be:

```text
caveat compression is valid;
caveat deletion is not.
```

### 4. Restraint In Healthy Cases

LaunchDarkly is important because state-first does not need to create drama.

The useful finding is:

```text
the tension is proof distribution,
not entity fragmentation.
```

That means state-first can act as a coordination layer instead of a complexity generator.

### 5. Fallback Compression

Netlify mock shows a smaller but useful behavior:

- repeated fallback openings can be compressed,
- each dimension can get a distinct job,
- thin evidence remains thin instead of being inflated.

This case also proves that state-first should not always create a dramatic rewrite.

## What State-First Does Not Solve

### 1. It Does Not Prove Automation

All state-first findings were manual/offline lab artifacts.

The trials prove the target behavior is valuable. They do not prove an automated generator can reliably produce it.

### 2. It Does Not Fix Evidence URL Attachment

Missing finding-level evidence URLs remain unresolved.

State-first can recognize the gap and route around it, but the data contract still needs work later.

### 3. It Does Not Replace Entity Discovery

Watermelon and Iris require explicit reviewed related-surface metadata.

If a future generator infers related surfaces from arbitrary URLs, name similarity, or search co-occurrence, it will recreate the original problem.

### 4. It Can Become Too Diagnostic

Several state-first outputs are clearer but still read more like epistemic analysis than final report prose.

That is acceptable in lab.

It is not yet production copy.

### 5. It Can Hide Uncertainty By Becoming Fluent

The biggest risk is not that state-first writes badly.

The biggest risk is that it writes smoothly enough that unresolved uncertainty becomes less visible.

## Case-Level Conclusions

### Builtwith / Kit

Verdict: strong state-first win.

Why:

- entity boundary becomes explicit,
- Kit and BuiltWith are not merged,
- external trust/security evidence is bounded,
- repeated caveats become one global constraint.

Remaining risk:

- the rewrite could feel so coherent that readers miss that entity review is still unresolved.

### Iris

Verdict: strong state-first win.

Why:

- name-collision ambiguity is handled directly,
- visual/perceptual confidence does not become evidentiary confidence,
- AI-related surfaces are not transferred to the primary entity.

Remaining risk:

- strong visual surface language can still tempt future generation into unsupported strategic certainty.

### Watermelon

Verdict: strong state-first win.

Why:

- ecosystem ambiguity is governed,
- related surfaces are review-gated,
- roadmap/platform claims are withheld.

Remaining risk:

- without explicit `observed_related_surfaces`, a future generator could infer an ecosystem that is not proven.

### LaunchDarkly

Verdict: useful but restrained state-first win.

Why:

- stable entity is preserved,
- evidence gaps are coordinated,
- no false ambiguity is introduced.

Remaining risk:

- state-first could overstructure healthy reports just to justify its existence.

### Netlify Mock

Verdict: modest state-first win.

Why:

- fallback repetition is reduced,
- sparse evidence remains sparse,
- no artificial depth is created.

Remaining risk:

- the payload may be too synthetic/thin to prove much beyond fallback control.

## Cross-Case Pattern

State-first helps most when the baseline risks one of these failures:

1. false entity coherence,
2. repeated local caveats,
3. owned claims treated as proof,
4. visual/perceptual confidence treated as evidentiary confidence,
5. related surfaces treated as aliases,
6. generic Decision Space filling in for real evidence,
7. fallback openings repeated because the system lacks a shared evidence map.

State-first helps least when:

1. the entity is already stable,
2. the evidence is thin but not ambiguous,
3. the baseline is already coherent,
4. a heavy rewrite would create analysis overhead.

## Readiness Decision

State-first is ready for:

- a lab-only generator specification,
- a small offline generation runner,
- strict comparison against baseline,
- no production use.

State-first is not ready for:

- runtime report generation,
- prompt rollout,
- official report replacement,
- automatic Lab display as improved output,
- scoring influence,
- Visual Signature integration.

## Recommended Next Phase

Create a lab-only state-first generation runner.

The runner should not be a production generator. It should produce artifacts comparable to the manual trials.

Minimum input:

- `report_narrative` payload,
- payload-level Narrative Harness diagnostic,
- render-aware diagnostic,
- EntityNarrativeState v0,
- optional reviewed `observed_related_surfaces`,
- optional base dossier/snapshot metadata.

Minimum output:

- baseline summary,
- shared entity state,
- shared evidence map,
- global uncertainty model,
- state-first finding plan,
- generated state-first findings,
- comparison against baseline,
- verdict.

Hard requirements:

- no scoring,
- no renderer change,
- no report mutation,
- no prompt rollout,
- no Visual Signature,
- no persistence,
- no claim of production readiness.

## Generator Preconditions

A lab-only generator should only run when:

- a report narrative payload exists,
- Narrative Harness diagnostics exist or can be built offline,
- EntityNarrativeState exists or can be built offline,
- the case has enough evidence to build a meaningful evidence map,
- unresolved ambiguity is explicitly marked,
- related surfaces are explicit/reviewed, not inferred from arbitrary URLs.

If these conditions fail, the runner should produce:

```text
No safe state-first generation candidate.
```

## What Should Not Happen Next

Do not:

- apply state-first to Brand Audit production output,
- change existing scoring reports,
- rewrite global prompts,
- add more architecture before testing generation behavior,
- let Lab claim these findings are official,
- hide uncertainty to make the result look better,
- infer related surfaces from name similarity,
- treat state fields as prose to quote directly.

## Recommendation

Continue, but narrowly.

The next useful goal is:

```text
Specify Lab-Only State-First Findings Generator v0
```

That goal should define a deterministic input/output contract and a strictly offline workflow for producing candidate artifacts. It should not implement runtime integration.

