# Brand3 Conditional Decision Space Impact

Date: 2026-05-16

Scope: rendering prototype evaluation only. No prompts, scoring, generation, persisted payload format, Visual Signature code, Narrative Harness runtime gate, or `EntityNarrativeState` work were changed.

## Prototype Summary

The report renderer now applies a deterministic display-only heuristic before rendering `typical_decision` as `Decision space`.

The heuristic hides clearly generic decision-space text, including openings such as:

```text
Teams in this position typically...
Companies in this position typically...
Companies in this situation typically...
Brands facing such...
Teams with such...
```

The raw field remains untouched:

- `Finding.prose` still includes `typical_decision`.
- persisted `report_narrative` payloads still include `typical_decision`.
- prompts and generation are unchanged.
- Narrative Harness still audits the original payload text.

## Builtwith.kit.com Comparison

Representative payload:

```text
examples/reports/narrative_harness/builtwith_kit_com.payload.json
```

| Measure | Always Show | Conditional Show |
|---|---:|---:|
| findings | 13 | 13 |
| payload `typical_decision` fields | 13 | 13 |
| visible `Decision space` lines | 13 | 0 |
| visible `Teams in this position typically` phrases | 9 | 0 |
| payload `Teams in this position typically` phrases | 9 | 9 |
| evidence chip links | 15 | 15 |

## What Improved

### 1. Visible repetition drops sharply

The most obvious repetitive construction disappears from the rendered report:

```text
Teams in this position typically...
```

This directly addresses the builtwith.kit.com visible cadence problem without changing the stored narrative payload.

### 2. Findings become more observational

The visible finding body now focuses on:

```text
title
observation + implication
evidence chips
```

This makes §4 feel less like repeated consulting advice and more like a sequence of evidence-bound readings.

### 3. Evidence visibility is preserved

Evidence chips still render normally. In the builtwith.kit.com pass, 15 evidence chip links remain visible after conditional suppression.

### 4. Compatibility is preserved

The suppression happens only at render time. Existing persisted reports do not need migration, and downstream code can still access the full field through `Finding.prose` or the raw payload.

## What Remains Unresolved

### 1. Payload warnings remain valid

The Narrative Harness should still flag the same payload-level issues:

- repeated sentence openings,
- generic strategic filler,
- missing evidence URLs,
- safe attribution overuse.

The visible HTML is cleaner, but the source narrative still contains the same repeated decision-space language.

### 2. Repeated observation openings remain

Conditional `Decision space` display does not address repeated observation openings such as:

```text
The brand describes itself...
The brand claims...
This is based only on self-description...
```

Those are generated in `observation`, not `typical_decision`.

### 3. Some reports may lose all visible decision framing

In builtwith.kit.com, all 13 `typical_decision` fields were hidden because all matched generic patterns.

That is probably the correct display outcome for this payload, but it exposes a limitation: if generation only produces generic move-space language, conditional display removes the whole decision layer rather than improving it.

### 4. The heuristic is lexical

The rule is intentionally simple and deterministic. It does not understand strategy. It only suppresses obvious generic forms.

This avoids runtime complexity, but it can miss generic language that uses different phrasing, and it can hide a decision sentence that begins generically but contains a useful later clause.

## Always Show vs Conditional Show

| Criterion | Always Show | Conditional Show |
|---|---|---|
| transparency of generated fields | strongest | weaker, because generic decision text is hidden |
| visible repetition | high | much lower |
| evidence-first reading | moderate | stronger |
| risk of hiding useful context | low | medium |
| payload compatibility | unchanged | unchanged |
| prompt/generation impact | none | none |
| Narrative Harness diagnostics | unchanged | unchanged |
| editorial quality on builtwith.kit.com | cleaner but repetitive | cleaner and less generic |

## Interpretation

Conditional display is a better reader-facing default than showing every `Decision space` line when the generated decision text is formulaic.

It should not be mistaken for a narrative fix.

The prototype improves presentation, not reasoning. It proves that some of the perceived generic quality is caused by rendering weak `typical_decision` text too prominently. It also proves that the deeper issue remains upstream: many `typical_decision` values are not specific enough to deserve visible space.

## Recommended Next Step

Keep the conditional rendering heuristic as a diagnostic prototype.

Before making it a settled production rule, run it across more persisted report payloads and compare:

1. how often `Decision space` is fully suppressed,
2. whether any useful decision framing is hidden,
3. whether dimensions become too observational without strategic tradeoff language,
4. whether a dimension-level compressed decision note would preserve useful strategy better than per-finding suppression.

The next architecture step should not be a prompt rewrite yet. The safer next step is to add render-aware diagnostics to the offline Narrative Harness examples, so Brand3 can distinguish:

```text
payload-level narrative risk
visible-render narrative risk
```

## Explicit Non-Goals

Do not use this prototype to:

- change prompts,
- change scoring,
- change generation,
- mutate persisted payloads,
- hide Narrative Harness warnings,
- implement `EntityNarrativeState`,
- infer that the narrative has been fixed.

## Bottom Line

Conditional `Decision space` display improves visible cohesion for builtwith.kit.com.

It removes the most generic visible cadence while preserving payload compatibility. The remaining problem is upstream narrative quality: the system still generates decision-space text that is often too generic to show.
