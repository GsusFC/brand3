# Brand3 Narrative Harness v1 Findings

Date: 2026-05-16

Scope: offline evaluation only. No prompts, scoring, rendering, runtime integration, persistence, or Visual Signature code were changed.

## Inputs Audited

The first harness pass generated payload fixtures and diagnostics under:

```text
examples/reports/narrative_harness/
```

Audited payloads:

1. `builtwith_kit_com.payload.json`
   - Source: existing SQLite `raw_inputs.source = report_narrative` for `builtwith.kit.com`.
   - Purpose: represents the observed `builtwith.kit.com` narrative issue.

2. `netlify_snapshot_mock.payload.json`
   - Source: existing `NETLIFY_SNAPSHOT` fixture plus the deterministic `_snapshot_analyzer()` used by report snapshot tests.
   - Purpose: checks harness behavior on existing deterministic report-test narrative output.

3. `clean_control.payload.json`
   - Source: minimal control fixture.
   - Purpose: verifies the harness can return a clean pass when prose is varied, evidence-bound, and non-prescriptive.

## Diagnostic Outputs

Generated diagnostics:

```text
examples/reports/narrative_harness/builtwith_kit_com.diagnostic.json
examples/reports/narrative_harness/netlify_snapshot_mock.diagnostic.json
examples/reports/narrative_harness/clean_control.diagnostic.json
```

## Summary

| Payload | Status | Warnings | Findings | Findings without evidence URLs | Safe attribution total | Main warning types |
|---|---:|---:|---:|---:|---:|---|
| `builtwith_kit_com` | warning | 4 | 13 | 4 | 11 | repeated openings, generic filler, missing evidence URLs, safe attribution overuse |
| `netlify_snapshot_mock` | warning | 2 | 5 | 2 | 0 | repeated openings, missing evidence URLs |
| `clean_control` | pass | 0 | 2 | 0 | 0 | none |

## What The Harness Catches

### 1. Repeated sentence openings

The `builtwith.kit.com` payload triggers repeated opening warnings around:

- `the brand describes`
- `teams in this`

This matches the suspected report issue: individual findings are valid, but many paragraphs begin from the same grammatical construction.

The Netlify mocked snapshot also triggers repeated openings:

- `the available sources`

That is useful because it proves the harness does not only catch live LLM prose. It also catches deterministic test prose when it becomes structurally repetitive.

### 2. Generic strategic filler

The `builtwith.kit.com` payload contains 9 occurrences of:

```text
teams in this position typically
```

The harness correctly flags this as generic strategic filler. This confirms that the phrase is not just a theoretical concern from the prompt review; it appears repeatedly in an actual persisted narrative payload.

### 3. Missing evidence URLs

The `builtwith.kit.com` payload has 4 findings with narrative text and empty `evidence_urls`.

The Netlify mocked snapshot has 2 findings with missing evidence URLs.

This is a warning, not an error, because current tests and payloads already allow empty evidence URL lists. The warning is still useful because it identifies places where the report reads as evidence-aware but cannot show a source chip.

### 4. Safe attribution overuse

The refreshed `builtwith.kit.com` diagnostic now separates safe-but-repetitive attribution from unsafe self-description validation.

It reports 11 safe attribution phrases:

```text
the brand describes itself: 4
the brand claims: 1
based only on self-description: 6
```

This is warning-only. The language is epistemically safer than saying the brand *is* the thing it claims to be, but repetition at this density becomes a cohesion risk. It makes the report feel mechanically defensive rather than editorially composed.

The Netlify mocked snapshot and clean control payload both report `safe_attribution_total: 0`.

## What The Harness Does Not Catch In This Pass

### Unsupported prescriptions

No audited payload triggered unsupported prescription warnings.

This does not mean recommendations are always safe. It only means the configured v1 phrase list did not find direct forms like:

- `the brand should`
- `needs to`
- `must`
- `the right move is`

### Unsafe self-description validation

The `builtwith.kit.com` payload repeats self-description heavily, but most of it is phrased as attribution:

```text
The brand describes itself as...
```

That is allowed by the current narrative discipline. The refreshed harness therefore does not flag it as unsafe validation:

```text
self_description_as_validation: pass
safe_attribution_overuse: warning
```

This distinction matters. The report is not overclaiming the owned description as fact, but it is leaning too heavily on the same safe attribution construction.

### Synthesis/tension mismatch

The `builtwith.kit.com` payload has `tensions_prose: null`, so mismatch comparison is skipped.

This highlights a limitation: the harness can detect lexical mismatch when both fields exist, but it cannot yet tell whether a missing tension is itself a problem.

### Entity drift

The current v1 harness does not implement entity drift detection. This remains a future check because it requires a source-aware named-entity allowlist to avoid false positives.

## Interpretation

The first pass supports the original architectural diagnosis.

The most visible issue is not hallucinated intent or unsupported direct prescription. The first measurable issue is structural sameness:

- repeated observation openings
- repeated typical-decision framing
- missing evidence URL anchoring in some findings
- repeated safe attribution language

This points to a narrative assembly problem more than a pure safety problem. The existing prompt discipline prevents some dangerous overreach, but it also creates repeated safe constructions.

## Implications For Next Step

Do not rewrite all prompts yet.

Recommended next move:

1. Add a small fixture based on the actual `builtwith.kit.com` payload to tests, or keep it as an example-only diagnostic if the team wants tests to avoid local DB-derived content.
2. Review whether `typical_decision` should remain rendered inside every `finding.prose`, because it is a major source of repetitive cadence.
3. Decide whether safe attribution overuse should inform a future prose compression or composition layer before any prompt rewrite.
4. Only after one or two more payload passes, design the first `EntityNarrativeState` fields around measured failures:
   - source ownership density
   - repeated opener budget
   - evidence URL coverage
   - primary entity vs adjacent entities
   - tension presence / absence

## Caution

The harness is currently lexical and structural. It should be read as a diagnostic instrument, not as an editorial judge.

It is good at catching repeated forms and obvious unsafe phrases. It is not yet good at understanding whether a subtle interpretation is strategically true, whether a contradiction should have been prioritized, or whether a missing tension is acceptable.
