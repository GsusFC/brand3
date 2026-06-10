# Brand3 Decision Space Display Modes Memo

Date: 2026-05-16

Scope: diagnostic comparison only. No prompts, scoring, generation, persisted payload format, Visual Signature code, or `EntityNarrativeState` work were changed.

Note: this memo is about the report finding `typical_decision` field and its display modes. It is not describing the TLDR block contract, which is normalized elsewhere.

## Context

The separate finding rendering prototype improved visible composition by moving `typical_decision` out of the main paragraph and into a secondary `Decision space` line.

The `builtwith.kit.com` representative render still showed:

| Measure | Result |
|---|---:|
| findings | 13 |
| `Decision space` lines | 13 |
| visible `Teams in this position typically` phrases | 9 |
| visible `The brand` phrases | 20 |
| evidence chip links | 15 |
| findings without evidence URLs | 4 |

This means the prototype solved the flattened paragraph problem, but not the underlying repeated language problem.

The remaining question is whether repetition should be handled through display, compression, prompt changes, or a later entity-level narrative state.

## Display Mode Comparison

| Mode | What changes | What improves | What fails to solve | Compatibility impact | Test impact | Risk |
|---|---|---|---|---|---|---|
| 1. Show `Decision space` on every finding | Keep current prototype: every non-empty `typical_decision` renders as a secondary line. | Preserves all generated content; makes field role explicit; removes `typical_decision` from the main paragraph; no payload migration. | Still repeats `Teams in this position typically...`; still adds vertical weight; still exposes generic decision framing 9 times in builtwith.kit.com; does not fix repeated `The brand...` openings. | Very low. `Finding.prose` and payload stay unchanged. | Existing renderer tests should assert primary body, secondary decision line, evidence chips, and backward-compatible `Finding.prose`. | Low technical risk, medium editorial risk if the secondary line appears mechanically in every finding. |
| 2. Show `Decision space` only when non-generic | Render `typical_decision` only if it passes a simple genericity filter or editorial value check. | Reduces visible generic cadence; keeps useful decision framing when specific; keeps payload intact; can be implemented as display-only. | Requires defining "non-generic"; brittle phrase filters can hide useful content or miss generic content; does not fix payload warnings; does not fix repeated observation openings. | Low if implemented in rendering/context only. No payload or generation change required. | Add tests for generic suppression, specific decision display, empty/legacy payload behavior, and `Finding.prose` compatibility. | Medium. A naive filter can become hidden editorial logic without enough diagnostics. |
| 3. Compress decision framing at dimension level | Do not show `typical_decision` under every finding; collect or summarize decision-space framing once per dimension. | Best visible reduction of repetition; aligns decision framing with dimension-level synthesis; makes findings more observational; avoids 13 repeated decision blocks. | Requires composition logic; may need heuristics to combine multiple `typical_decision` values; can lose nuance; still does not fix raw payload; may become a pseudo-synthesis layer without `EntityNarrativeState`. | Medium if done as render-context derivation; high if it changes persisted payload or generation. | Add tests for dimension-level decision block, preserved findings, hidden per-finding decision lines, evidence chips, legacy payloads, and no payload mutation. | Medium-high. It starts approaching architecture territory and could conceal unresolved narrative weaknesses. |

## Mode 1: Show Every Decision Space

This is the current prototype.

It is the safest implementation because it only changes visible hierarchy:

```text
title
observation + implication
Decision space: typical_decision
evidence chips
```

### Improves

- Stops `Finding.prose` from forcing every finding into a three-part paragraph.
- Preserves every generated field.
- Makes decision framing visibly separate from observation.
- Keeps evidence chips in the same place.
- Maintains compatibility with stored `report_narrative` payloads.

### Fails To Solve

- `Teams in this position typically...` still appears 9 times in the builtwith.kit.com render.
- The visible report still has 13 decision-space lines.
- The report can still feel formulaic, just with a clearer formula.
- Narrative Harness warnings remain unchanged because the payload text is unchanged.

### Fit

Good as a first rendering improvement. Not enough as the final answer.

## Mode 2: Show Decision Space Only When Non-Generic

This mode keeps `typical_decision` in the payload but suppresses it from display when it looks like generic strategic filler.

Possible display-only suppression signals:

- starts with `Teams in this position typically`,
- starts with `Companies in this position typically`,
- contains broad option lists without brand-specific nouns,
- contains generic dependency endings such as `depends on market reception, competitive landscape, and available resources`,
- repeats the same decision frame already shown in the same dimension.

### Improves

- Reduces visible generic cadence without changing generation.
- Keeps specific decision framing where it has real value.
- Allows the report to remain evidence-first.
- Can be tested as presentation logic.

### Fails To Solve

- The payload still contains generic text.
- Narrative Harness will still flag generic filler unless the harness gains a render-aware mode.
- Simple phrase filters are fragile.
- It does not solve repeated observation openings like `The brand describes itself...`.
- It may hide the field rather than improving the underlying reasoning.

### Compatibility

Compatible if implemented as template/context behavior only.

Do not remove `typical_decision` from:

- `Finding`,
- `Finding.prose`,
- `report_narrative`,
- persisted payload readers.

### Test Impact

Tests should cover:

1. generic `typical_decision` is not visibly rendered,
2. specific `typical_decision` is visibly rendered,
3. `Finding.prose` still includes `typical_decision`,
4. persisted payloads load unchanged,
5. evidence chips remain visible,
6. no prompt or generation path changes.

### Risk

This is probably the best next small experiment, but only if the genericity rule is treated as diagnostic and conservative.

The danger is creating hidden editorial suppression that makes reports look cleaner while preserving the same weak narrative payload.

## Mode 3: Dimension-Level Compression

This mode changes the visible structure more substantially.

Instead of rendering `typical_decision` per finding, the renderer would collect decision-space text for a dimension and show one compressed note after the dimension findings.

Example:

```text
4.1 Presence

Finding A
Observation + implication.
Evidence chips

Finding B
Observation + implication.
Evidence chips

Decision space
The practical question is whether to prioritize security proof, clearer owned positioning, or third-party trust repair.
```

### Improves

- Reduces repeated decision framing most strongly.
- Moves the report closer to editorial synthesis.
- Lets findings stay observational.
- Makes decision framing feel like a dimension-level implication rather than a mandatory finding suffix.

### Fails To Solve

- Requires compression logic.
- May over-compress distinct findings into one vague sentence.
- Can become a hidden synthesis layer without the safeguards of `EntityNarrativeState`.
- Still does not rewrite repeated observations.
- Still does not fix missing evidence URLs.

### Compatibility

Compatible only if implemented as derived render context.

It should not:

- mutate the persisted payload,
- change `Finding.prose`,
- change prompt output,
- remove `typical_decision` from generated payloads.

### Test Impact

Tests would need to assert:

1. individual findings no longer display per-finding `Decision space`,
2. dimension-level decision framing appears when source decisions exist,
3. empty or generic-only dimensions do not invent a decision note,
4. payload fields remain unchanged,
5. persisted report narratives load unchanged,
6. evidence chips remain associated with findings.

### Risk

This is editorially promising but too broad as the immediate next step.

It starts to answer architectural questions that probably belong to a future Narrative Harness or `EntityNarrativeState` phase.

## Prompt Changes vs Display Changes

The current evidence suggests both layers matter for report findings:

- Prompt contract contributes to repeated `typical_decision` phrasing.
- Rendering `Finding.prose` created the flattened paragraph problem.
- Dimension-by-dimension generation lacks a shared repetition budget.

Prompt changes alone would be risky now because they might reduce repetition while weakening the useful field structure. Display experiments are safer because they isolate reader experience without changing source generation.

## EntityNarrativeState Implication

The eventual architectural solution is probably not a template rule.

A future `EntityNarrativeState` could decide:

- which tensions matter,
- which decision spaces are redundant,
- which findings should remain observational,
- when self-description has been overused,
- when a dimension needs one decision frame instead of many.

But that is a later step. The current work should keep measuring the problem rather than prematurely building a state model.

## Recommended Smallest Next Step

Prototype Mode 2 as an opt-in or diagnostic rendering variant:

```text
show Decision space only when it is non-generic
```

Keep Mode 1 as the safe baseline.

Do not jump directly to dimension-level compression yet.

The next implementation should be narrow:

1. Add a small pure helper that classifies `typical_decision` display value as `specific`, `generic`, or `empty`.
2. Use it only in render context or template display logic.
3. Keep `Finding.prose` unchanged.
4. Keep payload format unchanged.
5. Add tests proving generic decision text can be hidden while specific decision text remains visible.
6. Document that Narrative Harness payload warnings remain valid even if generic text is visually suppressed.

## Explicit Non-Goals

Do not yet:

- change prompts,
- change scoring,
- change generation,
- mutate persisted payloads,
- alter Visual Signature,
- implement `EntityNarrativeState`,
- treat suppressed display as fixed narrative quality,
- remove `typical_decision` from `Finding.prose`.

## Bottom Line

Mode 1 is safe and useful, but still visibly repetitive.

Mode 3 is probably where the product should go later, but it introduces architecture and synthesis questions too soon.

Mode 2 is the smallest useful next experiment: suppress generic decision-space display while preserving the raw payload and compatibility guarantees.
