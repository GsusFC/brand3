# Report Structure Improvement Plan

Generated: 2026-05-14
Scope: planning only

Goal: reduce score-first and duplicated narrative caused by renderer / summary structure, without changing scoring logic or rubric dimensions.

## What Repetition Remains

The current report still repeats the same analytical payload in multiple places:

- the current reading tab renders `legacy_summary`
- the synthesis tab renders `synthesis_prose`
- the fallback synthesis in `src/reports/derivation.py` still repeats `strongest / weakest / data quality`
- the score hero and the prose sections are visually close enough that score-led framing bleeds into the narrative

The result is not just duplicate wording. It is duplicate authority: the same score-plus-summary logic appears in more than one place, so the report feels like it is re-saying itself.

## Where It Comes From

### 1. `src/reports/derivation.py`

The base dossier still populates:

- `legacy_summary`
- `summary`
- `synthesis_prose`

In the current structure, these are effectively aliases for the same underlying narrative.

The deterministic fallback synthesis also still emits a score-shaped paragraph with:

- strongest dimension
- weakest dimension
- data quality

That wording is useful as metadata, but it is too close to a narrative paragraph to be harmless duplication.

### 2. `src/reports/templates/report.html.j2`

The template still separates:

- `§3A current reading` -> `legacy_summary`
- `§3N synthesis` -> `synthesis_prose`

This means the report shows two narrative blocks that are too close in function, even when their text is slightly different.

### 3. Score hero relationship

The hero / score area and the prose areas are not visually separated enough in meaning.

Even when the prose is improved, the page still reads as:

1. score metadata
2. score-shaped summary
3. narrative paragraph

That ordering keeps the score-first mental model alive.

## Proposed Minimal Structural Changes

### Change 1: Make the current reading tab explicitly metadata-first

Proposed adjustment:

- keep the tab
- reduce `§3A current reading` to a compact diagnostic summary
- emphasize status / readiness / data quality / evidence coverage instead of repeating the same narrative paragraph

Risk: low

Expected impact:

- less duplicate prose
- less score-led opening pressure
- clearer separation between metadata and editorial synthesis

### Change 2: Stop rendering two narrative paragraphs that say the same thing

Proposed adjustment:

- keep only one full-length narrative lead
- treat the other block as a short contextual lead or a pointer

Implementation options:

- show `legacy_summary` as a condensed preface
- or show `synthesis_prose` as the main narrative and convert `legacy_summary` into a one-line label / note

Risk: medium

Expected impact:

- less redundancy
- stronger narrative hierarchy
- easier to read at a glance

### Change 3: Reframe fallback synthesis as metadata, not a pseudo-paragraph

Proposed adjustment:

- keep deterministic fallback behavior
- remove or downrank the strongest / weakest / data-quality wording from the narrative position
- move that information into a compact metadata strip or diagnostic note

Risk: medium

Expected impact:

- less score-shaped prose
- fewer duplicated summary phrases
- cleaner Brand3 / FLOC* voice

### Change 4: Make the score hero and prose blocks visually distinct

Proposed adjustment:

- keep the score hero as summary metadata
- visually separate it from the narrative lead
- reduce the sense that the prose is merely an explanation of the score

Risk: medium

Expected impact:

- better narrative hierarchy
- less score-first impression
- clearer distinction between evaluation and interpretation

## Risk Level by Change

- current reading compression: low
- single narrative lead instead of duplicated narrative: medium
- fallback synthesis reframe: medium
- hero / prose separation: medium

## Expected Impact on Brand3 / FLOC* Voice

If these changes land, the report should sound:

- less repetitive
- less score-first
- less self-summarizing
- more diagnostic and editorial
- more clearly layered between metadata, synthesis, and evidence

The biggest gain is not simply fewer repeated words. It is a better hierarchy of attention.

## Tests Needed

### Existing tests that should catch regressions

- `tests/test_reports_renderer.py`
- `tests/test_reports_snapshot.py`
- `tests/test_reports_dossier.py`
- `tests/test_reports_derivation.py`

### Additional checks to add later

- snapshot comparison for the current reading tab
- snapshot comparison for the synthesis tab
- assertion that the hero / summary area no longer duplicates the same wording as the synthesis block
- assertion that fallback prose does not reintroduce score-first openings in visible narrative sections

## Rollback Plan

If a structural change makes the report worse:

1. restore the prior template split between current reading and synthesis
2. restore the prior fallback synthesis wording
3. keep the prompt improvements in place
4. compare snapshot output before considering any further hierarchy changes

Rollback should be fast because the proposed changes are template / presentation changes, not scoring logic changes.

## Staged Implementation Order

1. Compress the current reading tab into a metadata-first summary.
2. Reduce duplication between current reading and synthesis.
3. Reframe fallback synthesis away from score-shaped prose.
4. Rebalance the score hero versus the narrative blocks.
5. Update snapshots once the hierarchy stabilizes.
