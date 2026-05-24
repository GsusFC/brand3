# Brand3 State-First Side-By-Side Comparison

Date: 2026-05-17

Scope: lab-only comparison artifact. No runtime integration, prompt rollout, scoring change, renderer change, report mutation or Visual Signature change.

## Purpose

Compare three layers for the same cases:

```text
baseline Brand Audit finding
vs manual state-first candidate
vs generated state-first candidate
```

The question is not whether the generator can produce valid JSON. It can.

The question is whether generated prose is good enough to show as Brand3 Lab value.

## Overall Read

The generator preserves structure and guardrails.

It does not yet match manual state-first prose quality.

That matters. The generated output is safer than baseline, but in Iris and Watermelon it is still too templated to be the visible “best” Lab reading.

## Case Summary

| Case | Pressure subtype | Generated result | Assessment |
|---|---|---|---|
| Iris | `name_collision` | Correctly blocks false aliasing. | Structurally valid, but manual is sharper. |
| Watermelon | `ecosystem_surface_pressure` | Correctly blocks ecosystem ownership/roadmap/traction inference. | Structurally valid, but manual is sharper. |
| LaunchDarkly | `stable_entity_evidence_binding` | Keeps case stable and improves proof boundaries. | Generated candidate is acceptable as light Lab output. |

## Iris

Baseline problem:

The baseline blends `irisdesign.dev`, agency-like Iris domains, AI Iris surfaces and collaborative Iris surfaces into a single implied reading.

Manual state-first improvement:

The manual candidate names the audited surface, names the ambiguity class, and explains how each dimension should treat Iris-like surfaces differently.

Generated state-first result:

The generator preserves the rule:

```text
similarly named Iris surfaces are not aliases
```

But it repeats a broad construction across dimensions:

```text
The [dimension] reading should start from https://irisdesign.dev and keep similarly named Iris surfaces separate...
```

Assessment:

The generated output is safer than baseline, but not as useful as the manual version. It needs richer relation-aware phrasing before being presented as a high-value Lab reading.

## Watermelon

Baseline problem:

The baseline lets owned copy, adjacent domains, GitHub repositories, marketplace surfaces and unrelated Watermelon references sound like one coherent ecosystem.

Manual state-first improvement:

The manual candidate distinguishes owned surface, adjacent surfaces, GitHub evidence, Product Hunt evidence and unrelated produce-news noise.

Generated state-first result:

The generator preserves the core safety rule:

```text
ecosystem evidence is not proof of ownership, roadmap, traction or one controlled brand architecture
```

But it uses the same broad sentence shape across dimensions.

Assessment:

The generated output is structurally correct and safer than baseline, but it needs more surface-family specificity to match manual quality.

## LaunchDarkly

Baseline problem:

The baseline is entity-stable but repeats owned-claim caveats and leaves several findings without local evidence URLs.

Manual state-first improvement:

The manual candidate keeps LaunchDarkly healthy and focuses only on proof distribution.

Generated state-first result:

The generator does the same:

- no invented ambiguity,
- no invented hidden tension,
- missing evidence treated as coverage limit,
- owned claims bounded.

Assessment:

This is the strongest generated result. The stable/light case is where deterministic generation is closest to manual quality.

## What The Comparison Proves

The generator can:

- preserve mode and pressure subtype,
- keep strong ambiguity cases review-gated,
- avoid false aliasing,
- avoid ecosystem ownership inference,
- avoid inventing tension in stable cases,
- include evidence boundary, uncertainty retained and overreach avoided per dimension.

## What It Does Not Prove

It does not prove that generated prose is ready for humans as the main Lab value.

The generated ambiguity cases still feel like protected templates. They are useful as structured candidates, but not yet as the polished comparison layer partners should judge.

## Recommendation

Keep the generator lab-only.

Do not wire it into Brand Audit.

Do not show generated prose as the default “improved” Lab reading yet.

Next useful step:

```text
improve subtype-specific prose for name_collision and ecosystem_surface_pressure
```

The target is not more abstraction. The target is sharper deterministic prose:

- Iris should mention audited surface, name collision and vitality risk without repeating the same frame.
- Watermelon should mention owned surface, adjacent domain, repository, marketplace and unrelated-reference risk with more precision.
- LaunchDarkly can remain mostly as-is.
