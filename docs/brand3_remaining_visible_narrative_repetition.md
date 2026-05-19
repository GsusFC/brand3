# Brand3 Remaining Visible Narrative Repetition

Date: 2026-05-16

Scope: diagnostic memo only. No code, prompts, scoring, generation, payload format, Visual Signature code, or `EntityNarrativeState` work were changed.

## Inputs Reviewed

```text
docs/brand3_conditional_decision_space_impact.md
docs/brand3_narrative_harness_v1_findings.md
examples/reports/narrative_harness/builtwith_kit_com.payload.json
```

The builtwith.kit.com representative payload was rendered through the current report template after conditional `Decision space` suppression.

## Visible Render Counts

| Visible pattern | Count |
|---|---:|
| findings | 13 |
| primary finding bodies | 13 |
| visible `Decision space` lines | 0 |
| visible `Teams in this position typically` | 0 |
| evidence chip links | 15 |
| visible `the brand` | 17 |
| visible `the brand describes itself` | 4 |
| visible `the brand claims` | 1 |
| visible `based only on self-description` | 6 |
| visible `no external corroboration` | 8 |

The conditional render solved the most obvious repeated decision-space phrase in the visible HTML. The remaining visible repetition now concentrates in observation and evidence-attribution language.

## What Rendering Solved

### 1. The generic decision-space cadence is no longer visible

The repeated phrase:

```text
Teams in this position typically...
```

is gone from the rendered report.

This is a real presentation improvement. The report no longer reads as a list of findings followed by the same generic strategic advice structure.

### 2. Findings now read more like evidence analysis

Visible findings now emphasize:

```text
title
observation + implication
evidence chips
```

This shifts §4 toward analytical reading rather than repeated recommendation framing.

### 3. Evidence chips remain intact

The render still shows 15 evidence chip links. The conditional display did not weaken source visibility where URLs exist.

## What Remains Visible

### 1. Safe attribution is still over-repeated

The report still relies heavily on safe owned-claim framing:

```text
The brand describes itself...
The brand claims...
This is based only on self-description...
no external corroboration...
```

This is epistemically safer than validating owned claims as fact, but it creates a mechanical rhythm. The report now sounds less like generic consultancy advice, but still like assembled LLM fragments around source caveats.

### 2. Observation openings are still too similar

Several findings begin from the same pattern:

```text
The brand describes itself...
Third parties describe...
The brand appears...
The domain...
```

Those openings are not produced by `typical_decision`. They live in `observation`, so conditional `Decision space` cannot fix them.

### 3. The report still lacks an editorial representation of the entity

The findings are locally valid, but the report does not appear to decide what builtwith.kit.com is as an entity before moving dimension by dimension.

This creates a visible assembly effect:

- creator/email positioning,
- BuiltWith technology intelligence positioning,
- safety/trust scans,
- robots.txt,
- API ecosystem,
- knowledge base.

These are all evidence-backed fragments, but the report does not strongly prioritize which signals define the case and which are secondary artifacts.

### 4. Missing evidence chips remain a payload issue

The Narrative Harness found 4 findings with narrative text and empty `evidence_urls`.

Rendering cannot solve that. The visible report can only show chips for URLs present in the payload.

## Classification Of Remaining Issues

| Issue | Current status | Likely layer |
|---|---|---|
| repeated `Teams in this position typically...` visible cadence | solved in visible render | rendering |
| repeated safe attribution | still visible | prompt + composition |
| repeated `The brand...` openings | still visible | prompt + observation generation |
| missing evidence chips | still present where payload lacks URLs | payload/evidence binding |
| fragmented entity picture | still present | composition / future `EntityNarrativeState` |
| generic decision-space text in source payload | still present but hidden | prompt + generation |
| Narrative Harness warnings | still valid | payload diagnostic |

## Does It Now Feel Like Evidence Analysis?

Partially.

The current render is materially better than the flattened `Finding.prose` version. It is more evidence-first and less obviously shaped by repeated recommendation cadence.

But it still does not feel like a fully composed Brand3 reading. The remaining issue is no longer primarily the visible `Decision space` field. The issue is that each finding still explains itself from scratch, often with the same defensive attribution language.

The report now reads more like evidence analysis than before, but still like stitched dimension-level LLM output rather than a single editorial judgment.

## What Requires Prompt Changes

Prompt changes would help with:

- reducing repeated observation openings,
- varying safe attribution language,
- making observations more direct and less caveat-heavy,
- asking for fewer repeated self-description caveats when several findings use the same owned source type,
- discouraging stock phrases like `This may indicate...` and repeated `suggests a focus...`.

However, prompt changes alone would not decide which signals matter most across dimensions.

## What Requires A Composition Layer Or EntityNarrativeState

A composition layer is needed for:

- source ownership density,
- repeated attribution budget,
- entity-level identity consolidation,
- contradiction prioritization,
- deciding when several findings are all about the same owned claim,
- deciding whether a trust/safety signal should dominate the report,
- deciding when decision-space framing should be absent, per dimension, or synthesized once.

This should not be built directly into scoring or prompt generation yet. It should first be measured as an offline harness/composition diagnostic.

## Recommended Next Step

Do not start with a broad prompt rewrite.

The smallest useful next step is to extend the offline Narrative Harness with a render-aware diagnostic pass:

```text
payload narrative risk
visible-render narrative risk
```

That would let Brand3 measure:

1. which warnings remain visible after template suppression,
2. how often safe attribution dominates visible observations,
3. how many findings lack visible evidence chips,
4. whether entity fragments repeat without consolidation,
5. whether the report has a usable entity-level reading before recommendations.

After that, design the first `EntityNarrativeState` fields around measured failures:

- primary entity signal,
- owned-claim density,
- third-party contradiction priority,
- repeated opener budget,
- evidence chip coverage,
- decision-space visibility mode.

## Bottom Line

Conditional `Decision space` rendering fixed the loudest visible repetition, but it exposed the next layer of the problem.

The report is now cleaner, but the remaining repetition sits in observation-level safe attribution and entity-level fragmentation. That is not a template problem anymore. It needs measured prompt refinement plus a future composition layer, with the next immediate step being render-aware diagnostics in the offline Narrative Harness.
