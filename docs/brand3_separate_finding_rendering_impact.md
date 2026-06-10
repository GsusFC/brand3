# Brand3 Separate Finding Rendering Impact

Date: 2026-05-16

Scope: rendering impact memo only. No prompts, scoring, generation, payload format, Visual Signature code, or `EntityNarrativeState` work were changed.

Note: this memo describes the visible composition of report findings. The TLDR block contract is separate and already normalized elsewhere.

## Input Reviewed

Representative payload:

```text
examples/reports/narrative_harness/builtwith_kit_com.payload.json
```

Reference diagnostic:

```text
examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json
docs/brand3_narrative_harness_v1_findings.md
```

The payload was rendered through the updated report template by injecting it as a persisted `report_narrative` raw input into a minimal report snapshot. This tests the same compatibility path used by stored narrative payloads.

## What Changed In The Visible Report

Before the rendering prototype, each finding displayed one flattened paragraph:

```text
observation + implication + typical_decision
```

That meant every finding carried the same three-part cadence, and the `typical_decision` language sat inside the main analytical paragraph.

With the updated template, each finding now displays:

```text
title
observation + implication
Decision space: typical_decision
evidence chips
```

`Finding.prose` remains unchanged for compatibility, but the template no longer uses it as the primary visible body when structured fields are available.

## Render Inspection

Rendered builtwith.kit.com output showed:

| Measure | Result |
|---|---:|
| structured primary finding bodies | 13 |
| `Decision space` secondary lines | 13 |
| visible `Teams in this position typically` phrases | 9 |
| visible `The brand` phrases | 20 |
| evidence chip links rendered | 15 |
| findings expected without evidence URLs | 4 |

The first finding now reads as a main observation/implication block followed by a separate decision-space line. This makes the generic move-space language visibly secondary instead of letting it complete every core paragraph.

## Improvements

### 1. The main finding body is less consultancy-shaped

The primary paragraph now ends after the observation and implication. This reduces the visible sense that each finding is a complete consulting recommendation paragraph.

The repeated `Teams in this position typically...` construction is still present, but it is demoted. The reader can now scan the analytical claim first and treat the decision framing as supporting context.

### 2. Field roles are clearer

The report now communicates that `typical_decision` is not part of the factual observation. It is a separate decision-space framing.

That distinction matters because the field is inherently more interpretive than the surface observation.

### 3. Evidence chips remain visible

Evidence URL chips still render after each finding when present. The rendering change did not remove source visibility or alter chip behavior.

For builtwith.kit.com, 15 evidence links render across the visible findings. Four findings still have no evidence URL chips because the persisted payload has empty `evidence_urls` for those findings.

### 4. Persisted narrative compatibility is preserved

The test path uses the existing persisted `report_narrative` payload shape:

```text
observation
implication
typical_decision
evidence_urls
```

No payload migration is required.

## What Remains Unresolved

### 1. Repeated `The brand...` openings remain

The render change does not rewrite observations. The builtwith.kit.com payload still contains repeated safe attribution patterns such as:

```text
The brand describes itself...
The brand claims...
This is based only on self-description...
```

Separating fields improves readability, but it does not solve repeated observation openings.

### 2. Repeated `Teams in this position typically...` remains in the payload

The phrase still appears 9 times in the rendered report because the underlying `typical_decision` text is unchanged.

The improvement is compositional, not lexical: those phrases are now isolated under `Decision space` instead of fused into the main body.

### 3. Generic decision-space language is still generic

The separated line makes the generic cadence easier to identify, but it does not make the decision-space language sharper.

A future step still needs either:

- prompt-level variation,
- field-level compression,
- dimension-level consolidation,
- or an entity-level narrative state that decides which decision-space notes are worth showing.

### 4. Missing evidence URLs remain missing

Four findings still have no evidence chips because the payload has no `evidence_urls` for those items. Rendering cannot recover evidence that was not persisted.

This should remain a Narrative Harness warning rather than being treated as a template failure.

## Harness Implication

Narrative Harness warnings may remain unchanged after this rendering prototype.

That is expected.

The harness audits the payload text and structure, not the visual hierarchy of the rendered report. Since the payload still contains the same repeated openings, same `typical_decision` phrases, same safe attribution language, and same missing evidence URL lists, the diagnostic should continue flagging:

- repeated sentence openings,
- generic strategic filler,
- missing evidence URLs,
- safe attribution overuse.

The rendering experiment improves the reader experience without changing the measured narrative payload.

## Evaluation

The separate rendering is a useful low-risk improvement.

It does not fix the deeper narrative cohesion problem, but it reduces one visible source of monotony: the forced paragraph shape created by rendering `Finding.prose` directly.

The result supports keeping this prototype as a presentation-layer improvement while continuing the larger Narrative Harness path.

## Recommended Next Step

Keep the separated rendering.

Do not treat it as a full narrative fix.

The next safe diagnostic step is to compare rendered reports with:

1. separated `Decision space` on every finding,
2. `Decision space` shown only when it adds non-generic information,
3. dimension-level compressed decision framing.

That comparison should still avoid prompt rewrites, scoring changes, generation changes, and payload format changes until the Narrative Harness has measured the remaining failures across more reports.
