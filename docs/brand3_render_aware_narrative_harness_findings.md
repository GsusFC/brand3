# Brand3 Render-Aware Narrative Harness Findings

Date: 2026-05-16

Scope: offline diagnostic findings only. No prompts, scoring, generation, persisted payload format, Visual Signature code, production runtime wiring, or `EntityNarrativeState` work were changed.

## What Was Added

The Narrative Harness now has a second offline diagnostic surface:

```text
payload-level narrative risk
visible-render narrative risk
```

The existing payload-level function remains unchanged:

```python
audit_report_narrative_payload(...)
```

The new render-aware function accepts an already-rendered HTML or text string:

```python
audit_report_narrative_render(payload, rendered_output, rendered_as_html=True)
```

It does not render reports itself, call LLMs, mutate payloads, write production records, change scoring, or participate in runtime behavior.

## Example Diagnostic

Generated example:

```text
examples/reports/narrative_harness/builtwith_kit_com.render_aware.diagnostic.json
```

Input payload:

```text
examples/reports/narrative_harness/builtwith_kit_com.payload.json
```

The example uses the current report template after conditional `Decision space` suppression.

## Builtwith.kit.com Results

### Payload-Level Metrics

| Metric | Count |
|---|---:|
| findings | 13 |
| findings without evidence URLs | 4 |
| payload `teams in this position typically` | 9 |
| payload safe attribution total | 11 |
| `the brand describes itself` | 4 |
| `the brand claims` | 1 |
| `based only on self-description` | 6 |

### Visible-Render Metrics

| Metric | Count |
|---|---:|
| visible `Decision space` | 0 |
| visible `teams in this position typically` | 0 |
| visible `the brand` | 17 |
| visible `no external corroboration` | 8 |
| visible links total | 22 |
| visible evidence chip links | 13 |
| visible safe attribution total | 11 |
| `the brand describes itself` | 4 |
| `the brand claims` | 1 |
| `based only on self-description` | 6 |

The render-aware pass confirms the distinction Brand3 needed:

- decision-space repetition exists in the payload,
- conditional rendering suppresses it from the visible report,
- safe attribution repetition remains visible.

## Suppressed By Rendering

The example diagnostic reports these risks as suppressed:

| Risk | Payload count | Visible count | Suppressed |
|---|---:|---:|---:|
| generic strategic filler: `teams in this position typically` | 9 | 0 | 9 |
| repeated opening: `teams in this` | 9 | 0 | 9 |
| repeated opening: `the brand describes` | 4 | 0 | 4 |

The last item needs careful interpretation. The exact sentence-opening metric is less stable in rendered text because HTML extraction changes sentence boundaries. The phrase-level safe attribution counts are the stronger signal for owned-claim repetition.

## Still Visible Risks

The render-aware diagnostic still flags:

- visible safe attribution overuse,
- repeated visible openings such as `it may indicate`,
- repeated visible caveat openings such as `this description is` and `this is based`,
- repeated `no external corroboration`.

This matches the qualitative diagnosis from the earlier memo: rendering fixed the loudest decision-space cadence, but the remaining repetition is now observation-level and attribution-level.

## What This Proves

### 1. Payload warnings and visible warnings are different

The payload can remain warning-heavy while the rendered report becomes cleaner.

This matters because the Narrative Harness should not treat render suppression as narrative repair. It should show both surfaces.

### 2. Conditional `Decision space` is working as presentation logic

The builtwith.kit.com report no longer visibly repeats the most generic strategic phrase.

That is a real visible improvement, but it is not a source-quality improvement.

### 3. The next visible problem is safe attribution

The visible report still repeats owned-claim caveats heavily:

```text
The brand describes itself...
The brand claims...
based only on self-description...
no external corroboration...
```

This is not unsafe, but it reads mechanically defensive.

### 4. Evidence chip coverage can now be separated from total links

The render-aware metrics distinguish:

```text
visible_link_count
visible_evidence_chip_link_count
```

This matters because total report links include navigation and source sections, while evidence chip links are the relevant grounding signal for findings.

## What The Render-Aware Harness Still Does Not Do

It does not yet:

- judge whether a visible interpretation is strategically true,
- know which entity fragments should dominate the report,
- decide whether safe attribution is necessary or redundant,
- validate source ownership,
- inspect CSS/visual prominence,
- compare screenshots,
- rewrite the narrative.

It is still a lexical and structural diagnostic.

## Recommended Next Step

Keep the render-aware harness offline and example-driven for now.

The next smallest useful step is to run it across more representative persisted reports and compare:

1. payload warning count,
2. visible warning count,
3. suppressed generic filler,
4. visible safe attribution density,
5. evidence chip coverage,
6. missing or weak visible entity consolidation.

Only after that should Brand3 design the first `EntityNarrativeState` fields.

Likely first fields:

- primary entity signal,
- source ownership density,
- repeated opener budget,
- visible attribution budget,
- evidence chip coverage,
- contradiction priority,
- decision-space display mode.

## Bottom Line

The render-aware harness gives Brand3 the missing measurement split:

```text
the payload still contains weak narrative material
but the rendered report may expose or suppress different parts of it
```

For builtwith.kit.com, rendering suppresses generic decision-space repetition but leaves safe attribution repetition visible. The next problem is no longer primarily `Decision space`; it is observation-level composition and entity-level consolidation.
