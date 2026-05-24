# Brand3 State-First Narrative Generation Research Corpus

Date: 2026-05-17

Scope: research planning only. No runtime integration, prompt rollout, scoring change, report mutation, renderer change, persisted payload change, Visual Signature change, UI change, automated generator, or LLM runtime call was added.

## Purpose

The first state-first generation trials show enough signal to treat this as a new research phase:

```text
State-First Narrative Generation Research
```

The point is not to make Brand3 prose sound better. The point is to test whether Brand3 can generate findings from shared composition constraints before writing dimension-level paragraphs.

The research question is:

```text
Can entity-state-first generation produce better Brand3 findings than the current dimension-by-dimension pipeline without inventing coherence or hiding uncertainty?
```

This corpus defines which cases should pressure that question next.

## Current Evidence

Existing state-first trials:

| Case | Pressure family | What the trial showed |
|---|---|---|
| Watermelon | Ecosystem ambiguity | State-first helps when related surfaces must not be collapsed into one platform story. |
| Iris | Name-collision ambiguity | State-first helps prevent similarly named surfaces from becoming false aliases or brand architecture. |
| LaunchDarkly | Healthy / high-evidence control | State-first can stay light when the entity is stable; overstructuring would be a failure. |

Existing diagnostic cases without full state-first generation trial:

| Case | Pressure family | Why it still matters |
|---|---|---|
| Builtwith / Kit | Entity ambiguity and caveat inflation | Strong candidate for state-first generation because ambiguity is central and measured. |
| Netlify mock | Fallback repetition and weak local evidence binding | Useful control for whether state-first can improve fallback prose without overclaiming. |

## Research Corpus

The corpus should remain small. The next phase should not become a volume exercise.

### Tier 1: Already Measured / Ready

These cases have enough local artifacts to support offline state-first comparison now.

| Case | Status | Primary pressure | Next use |
|---|---|---|---|
| Watermelon | Trial complete | Ecosystem / multi-surface ambiguity | Reference case for entity hierarchy. |
| Iris | Trial complete | Name collision and visual/perceptual overreach risk | Reference case for false equivalence control. |
| LaunchDarkly | Trial complete | High-evidence, low-ambiguity control | Reference case for restraint. |
| Builtwith / Kit | Diagnostics and entity state available | Entity ambiguity, owned claims, caveat inflation | Next full state-first trial candidate. |
| Netlify mock | Diagnostics and entity state available | Fallback repetition, weak evidence binding | Next control candidate if the goal is fallback discipline. |

### Tier 2: New Candidate Audits

These require fresh or refreshed Brand3 runs before state-first generation can be compared.

| Case | Target type | Primary research question | Why useful |
|---|---|---|---|
| Supabase | High-evidence / low-ambiguity | Does state-first stay light outside LaunchDarkly? | Strong public footprint and clear developer ecosystem. |
| Temporal | High-evidence / technical category | Can state-first avoid generic infrastructure prose? | Technical category can trigger template-like enterprise language. |
| Vercel | Ecosystem / multi-surface | Can state-first manage product/platform/ecosystem hierarchy without flattening? | Strong ecosystem, many surfaces, many proof types. |
| Sentry | Ecosystem / operational product | Can state-first coordinate evidence across product, docs, community, and category? | Strong external footprint, possible category familiarity bias. |
| Spooky | Visual/perceptual pressure | Does state-first prevent aesthetic confidence from becoming evidentiary confidence? | Useful perceptual-pressure candidate. |
| Stipple | Visual/perceptual pressure | Can Brand3 read surface behavior without inventing intention? | Useful if enough evidence can be collected. |

## Recommended Next Batch

Run only three next trials.

1. Builtwith / Kit
   - Reason: strongest unresolved entity ambiguity case.
   - Expected win: caveats become a global entity-boundary constraint instead of repeated paragraph filler.
   - Expected failure: the rewritten version becomes too fluent and hides unresolved entity boundary review.

2. Netlify mock
   - Reason: fallback repetition case with weaker evidence binding.
   - Expected win: fallback openings are centralized and findings stop repeating evidence scarcity.
   - Expected failure: state-first cannot improve because the payload is too thin or synthetic.

3. Supabase or Temporal
   - Reason: second high-evidence control beyond LaunchDarkly.
   - Expected win: state-first stays light and only improves evidence discipline.
   - Expected failure: the method invents tension to justify itself.

Do not run Vercel or Sentry before this batch unless the team explicitly wants to test ecosystem complexity first. They are useful, but they may pull the research back into entity-discovery design before generation behavior is clear.

## Evaluation Criteria

Every trial should answer the same questions:

1. Is the state-first version better than baseline?
2. Is it safer than baseline?
3. Is it clearer than baseline?
4. Does it preserve uncertainty?
5. Does it reduce defensive fragmentation?
6. Does it improve evidence binding?
7. Does it avoid false coherence?
8. Does it avoid generic consultancy language?
9. Does it avoid score-first prose?
10. Does it know when to stay light?

## Case-Specific Success And Failure Signals

### Builtwith / Kit

Success:

- entity ambiguity becomes explicit and review-gated,
- owned claims and external BuiltWith-like signals are separated,
- repeated safe attribution is compressed,
- missing evidence URLs become a limitation, not a repeated caveat.

Failure:

- state-first turns ambiguity into a confident strategic story,
- Kit and BuiltWith are treated as one entity without proof,
- caveats are hidden instead of governed.

### Netlify Mock

Success:

- fallback openings are not repeated per finding,
- weak evidence is named once at the right level,
- the result remains modest instead of over-polished.

Failure:

- state-first manufactures strategic depth from thin evidence,
- baseline remains equally good because there is not enough signal to improve.

### Supabase / Temporal

Success:

- state-first stays light,
- no false ambiguity is introduced,
- evidence binding improves without making the report heavier.

Failure:

- the method invents hidden tension,
- the output reads as a diagnostic essay rather than Brand3 findings,
- state fields become content to cite rather than constraints to obey.

### Vercel / Sentry

Success:

- ecosystem surfaces are separated by role,
- public proof, docs, product pages, community, and category evidence are coordinated,
- state-first avoids flattening the ecosystem into one generic platform claim.

Failure:

- the output becomes a map of surfaces instead of findings,
- strong brand familiarity substitutes for evidence,
- entity state becomes an excuse for overlong narrative.

### Spooky / Stipple

Success:

- visual or perceptual strength stays separate from evidentiary confidence,
- the text describes surface signals without inventing intent,
- unsupported emotional readings are withheld or marked as interpretation.

Failure:

- the rewrite becomes aesthetic criticism,
- visual confidence is treated as market or strategic proof,
- Brand3 voice becomes stylish but less disciplined.

## Non-Goals

Do not use this corpus to:

- change production prompts,
- replace Brand Audit findings,
- modify scoring,
- modify report rendering,
- add UI,
- add persistence,
- integrate Visual Signature,
- build an automated generator,
- claim production readiness.

## Recommended Next Action

Create a single goal for the next batch:

```text
Run State-First Generation Trials For Builtwith, Netlify, And One High-Evidence Control
```

The high-evidence control should be Supabase or Temporal. If neither has an existing reliable Brand3 run, the goal should first create the audit artifacts and then stop before generation.

The expected outputs should be lab-only files under:

```text
examples/reports/narrative_harness/state_first_generation_trial/
```

The phase should continue only if the next batch shows one of two things:

- state-first improves the hard cases while staying light on healthy cases, or
- state-first fails clearly enough to define what should not be automated.

