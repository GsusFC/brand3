# Brand3 Finding.prose / typical_decision Memo

Date: 2026-05-16

Scope: diagnostic memo only. No prompts, rendering, scoring, runtime, persisted payload format, or Visual Signature code were changed.

## Executive Diagnosis

`typical_decision` should probably not continue being rendered inside every visible `finding.prose` paragraph by default.

The underlying field is useful and should remain in the generated/persisted payload for now. The problem is presentation and composition: `Finding.prose` concatenates `observation + implication + typical_decision`, and the report template renders only that combined property. This collapses a structured analytical object into one repeated paragraph shape.

The resulting issue is not just prompt wording. It is the interaction of:

1. prompt contract requiring every finding to include `typical_decision`,
2. `Finding.prose` concatenating it into the main paragraph,
3. the template rendering only `finding.prose`,
4. dimension-by-dimension generation without a shared editorial state.

The smallest safe next step is not to remove the field or change the persisted payload. It is to prototype a rendering/composition variant that shows `observation` and `implication` as the primary paragraph and moves `typical_decision` out of the default body, either as a secondary line, optional disclosure, or dimension-level compressed note.

## Current Code Path

### Finding data model

`src/reports/narrative.py` defines `Finding` with:

```python
title
observation
implication
typical_decision
evidence_urls
```

The docstring explicitly says `typical_decision` is a plural space of moves teams typically consider, and that `prose` exists for backwards compatibility with templates that have not migrated to four-part rendering.

Key locations:

- `Finding` fields and docstring: `src/reports/narrative.py`
- `Finding.prose`: concatenates `observation`, `implication`, and `typical_decision`

Current behavior:

```python
parts = [p for p in (self.observation, self.implication, self.typical_decision) if p]
return " ".join(parts)
```

### Prompt contract

The findings prompt asks every finding to return five parts:

- `title`
- `observation`
- `implication`
- `typical_decision`
- `evidence_urls`

It explicitly frames `typical_decision` as:

```text
teams in this position typically choose between X, Y, or Z
```

This is the source of the repeated construction detected in `builtwith.kit.com`.

### Template usage

The report template renders:

```jinja2
<h4>{{ finding.title }}</h4>
<p>{{ finding.prose }}</p>
```

Location:

- `src/reports/templates/report.html.j2`

It does not render `observation`, `implication`, and `typical_decision` separately. Therefore the internal separation discipline exists in the data model, but is flattened for the reader.

### Persistence path

`src/reports/dossier.py` serializes all four finding fields into `report_narrative`:

- `_finding_to_payload(...)` includes `typical_decision`
- `_finding_from_payload(...)` reads `typical_decision`

This means changing the field itself would affect persisted narrative compatibility. Changing only presentation would not require a payload format change.

## Test Dependencies

Existing tests rely on the current shape in several ways.

### `tests/test_reports_dossier.py`

Relevant dependencies:

- `test_build_report_narrative_payload_serializes_rich_narrative`
  - expects `typical_decision` to serialize into the payload.
- `test_build_brand_dossier_prefers_persisted_narrative_without_llm`
  - expects `findings[0].prose` to equal:

```text
Stored observation. Stored implication. Stored decision space.
```

This directly depends on `Finding.prose` including `typical_decision`.

### `tests/test_reports_narrative.py`

Relevant dependencies:

- old-style `prose` payloads are still accepted as backward-compatible observations.
- fallback findings use `Finding.prose`.
- perceptual hint tests include a `typical_decision` string using the repeated “Teams in this position typically...” construction.

### `tests/test_web_app.py`

The public report test inserts a persisted `report_narrative` with `typical_decision`, but only asserts that the report includes the finding title and narrative/tension strings. It does not currently assert that `typical_decision` appears in rendered HTML.

## What The Harness Shows

The refreshed Narrative Harness diagnostics show:

- `builtwith.kit.com`
  - 13 findings
  - 9 occurrences of `teams in this position typically`
  - 11 safe attribution phrases
  - 4 findings without evidence URLs
  - `self_description_as_validation: pass`
  - `safe_attribution_overuse: warning`

This suggests the system is behaving safely in one sense, but monotonously in another. The report is not necessarily overclaiming; it is over-repeating defensive and decision-space constructions.

## Option Analysis

### Option 1: Keep `typical_decision` inside every finding paragraph

Benefits:

- No code changes.
- No template changes.
- No test changes.
- Maintains backwards compatibility.
- Keeps every finding self-contained.

Risks:

- Keeps the exact cohesion problem now measured by the harness.
- Every finding tends to end with the same strategic move-space cadence.
- Makes reports feel longer and more generic.
- Encourages “consultancy paragraph” structure even when the observation is specific.

Compatibility impact:

- None.

Test impact:

- None.

Persisted payload format impact:

- None.

Assessment:

- Safest technically, weakest editorially.

### Option 2: Render `typical_decision` separately

Example structure:

```text
Title
Observation + implication paragraph.
Decision space: ...
Evidence chips
```

Benefits:

- Preserves all generated content.
- Preserves persisted payload format.
- Makes the field’s role explicit instead of hiding it inside prose.
- Lets future CSS visually demote it without deleting it.
- Reduces the feeling that every paragraph is the same kind of sentence.

Risks:

- Requires template change.
- Requires snapshot/test update.
- The page may still feel repetitive if every finding shows a visible decision-space line.
- It may add vertical weight unless styled compactly.

Compatibility impact:

- Low if `Finding.prose` remains unchanged for compatibility.
- Existing payloads keep working.

Test impact:

- Add/update renderer tests to assert separate rendering.
- Existing `Finding.prose` tests can remain unchanged unless intentionally revised.

Persisted payload format impact:

- None.

Assessment:

- Good transitional option. It improves readability without changing generation or storage.

### Option 3: Omit `typical_decision` from default prose

This could mean changing `Finding.prose` to concatenate only:

```text
observation + implication
```

Benefits:

- Directly removes the repetitive decision-space cadence from default report paragraphs.
- Keeps findings sharper and more evidence-bound.
- Makes §4 feel more analytical and less advisory.

Risks:

- Breaks current `Finding.prose` compatibility expectations.
- `tests/test_reports_dossier.py` currently asserts that `Finding.prose` includes stored decision space.
- Existing consumers of `finding.prose` would silently stop seeing `typical_decision`.
- This changes semantics of a property explicitly marked as backwards-compatible.

Compatibility impact:

- Medium.

Test impact:

- Must update tests that assert `.prose` includes `typical_decision`.
- Need tests for explicit access to `typical_decision`.

Persisted payload format impact:

- None, if the field remains stored.

Assessment:

- Editorially attractive, but too risky as the first move because `Finding.prose` is explicitly a backward-compatibility property.

### Option 4: Make `typical_decision` conditional

Examples:

- Render only when confidence is high enough.
- Render only once per dimension.
- Render only when `typical_decision` is not repetitive.
- Render only when the finding has external evidence.

Benefits:

- Preserves the field when useful.
- Reduces repetition.
- Allows the harness to inform display choices.

Risks:

- Requires policy design.
- Could hide content unpredictably.
- Needs confidence/evidence semantics that are not yet fully connected at finding level.
- Could become a runtime editorial gate before the team has agreed on criteria.

Compatibility impact:

- Low to medium, depending on implementation.

Test impact:

- Tests must cover display/omit conditions.

Persisted payload format impact:

- None.

Assessment:

- Promising later, but not the smallest safe first step. Needs more harness data.

### Option 5: Compress repeated typical decisions at dimension level

Instead of one decision-space sentence per finding, show one compact decision note per dimension.

Example:

```text
Dimension decision space:
The findings raise a choice between narrowing the claim, adding proof, or clarifying audience.
```

Benefits:

- Directly addresses repetition.
- Keeps decision framing available.
- Aligns better with the idea that strategy questions often belong at dimension level, not finding level.
- Creates room for future EntityNarrativeState or Narrative Harness compression.

Risks:

- Requires a new composition step.
- If generated by LLM, would be a prompt/runtime change.
- If deterministic, may be crude.
- Needs rules to merge multiple `typical_decision` fields without inventing meaning.

Compatibility impact:

- Medium if implemented as render-only summarization.
- Higher if generation changes.

Test impact:

- New tests for dimension-level aggregation.
- Existing per-finding payload tests can remain.

Persisted payload format impact:

- None if computed at render/context time.

Assessment:

- Likely good direction, but not first implementation unless kept strictly experimental/offline.

### Option 6: Move decision framing into synthesis/tensions only

Benefits:

- Makes findings more observational.
- Places strategic interpretation where cross-dimensional context exists.
- Reduces local repetition substantially.

Risks:

- Requires prompt and narrative architecture changes.
- Synthesis/tensions currently happen after findings and do not rewrite them.
- Could overload synthesis/tensions with too much advisory content.
- Needs EntityNarrativeState or similar to do well.

Compatibility impact:

- High if prompt contracts change.

Test impact:

- Significant narrative tests/snapshots update.

Persisted payload format impact:

- Could remain compatible if `typical_decision` stays optional, but generation semantics change.

Assessment:

- Architecturally coherent later. Too broad now.

## Root Cause Classification

### Prompt issue

Yes, partly.

The prompt explicitly asks for `typical_decision` and gives the phrase frame that is now repeated. This causes the raw material to converge.

### Finding.prose composition issue

Yes, strongly.

`Finding.prose` turns a structured object into a single paragraph. That makes every finding carry the same three-part shape. The field was retained for backwards compatibility, but the template still uses it as the primary display.

### Template/rendering issue

Yes.

The template renders only `finding.prose`, so readers cannot perceive the internal distinction between observation, implication, and decision space. This weakens the methodological separation the code already has.

### Architecture issue

Yes.

Dimension findings are generated independently before synthesis. No shared narrative state controls repetition, decision-space budget, or whether decision framing belongs at finding, dimension, or synthesis level.

## Recommendation

Smallest safe next step:

Create a render/composition experiment that keeps `Finding.prose` and the persisted payload unchanged, but changes the experimental report display of findings to render fields separately:

```text
finding.title
finding.observation + finding.implication
optional/demoted finding.typical_decision
evidence_urls
```

Do not change the prompt yet.
Do not change `Finding.prose` yet.
Do not remove `typical_decision` from persisted payloads.

This isolates the variable:

- If prose improves when `typical_decision` is visually separated or demoted, the main issue is composition/rendering.
- If it still feels generic, the prompt and architecture need deeper work.

## Proposed Test Strategy For That Future Step

If implemented later, add tests that verify:

1. `Finding.prose` remains backward-compatible.
2. The template renders `observation` and `implication` separately or as a primary body.
3. The template still has access to `typical_decision`.
4. Persisted `report_narrative` payloads still load unchanged.
5. Public reports do not call LLMs.
6. Existing `report_narrative` payload format remains valid.
7. A fixture with repeated `typical_decision` produces less visible repetition in rendered HTML.

## Explicit Non-Goals

Do not yet:

- change `Finding.prose`
- remove `typical_decision`
- change the prompt contract
- change persisted payload format
- wire a runtime Narrative Harness gate
- implement EntityNarrativeState
- move decision framing entirely into synthesis/tensions
- change scoring
- touch Visual Signature

## Bottom Line

`typical_decision` is useful as structured analytical metadata, but harmful when injected into every visible finding paragraph through `Finding.prose`.

Keep the field. Keep the payload. Keep `Finding.prose` for compatibility.

The next safe experiment should be display/composition, not prompt rewrite: render the analytical fields separately and demote or conditionally reveal `typical_decision`.
