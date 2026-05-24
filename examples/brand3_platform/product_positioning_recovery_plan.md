# Brand3 Product Positioning And Navigation Recovery Plan

This plan restores Brand3 Scoring as the primary user-facing product while
keeping Visual Signature as a secondary research and lab module.

Principle:

- Brand3 Scoring is the working product and user hook.
- Visual Signature is the long-term R&D layer for human-reviewed visual
  perception.

This is a planning document only. It does not change scoring logic, prompts,
reports, or Visual Signature semantics.

## Current State

The current app already centers scoring on `/` with the brand input form and
recent analyses. That is the right primary direction, but the navigation still
gives Visual Signature enough prominence that it can read as a co-equal product
rather than a secondary lab surface.

Observed current pattern:

- Home page: scoring input and latest analyses live together.
- Footer: `Initial Scoring`, `/reports`, and `Visual Signature` are presented
  side by side.
- Visual Signature: multiple routes exist and are easy to reach, which is good
  for access but too strong if the goal is product focus.

## Ideal Homepage Hierarchy

The homepage should make the scoring loop obvious in the first viewport.

Recommended order:

1. Brand3 Scoring title and one-line value statement.
2. Prominent URL input and analyze button.
3. Short trust / constraints note, if needed.
4. Recent analyses.
5. Quick access to reports and brand history.
6. Secondary access to Visual Signature Lab.

What should feel primary:

- entering a brand URL
- getting a new analysis
- seeing recent results
- opening reports or brand history

What should feel secondary:

- research tools
- governance details
- calibration
- reviewer workflow
- corpus expansion

## Main Navigation Proposal

The primary navigation should reinforce scoring as the user hook.

Recommended primary items:

- `Analyze`
- `Latest Results`
- `Reports`
- `Brands`
- `Team`

If a top nav is not desired, the same hierarchy should still be reflected in the
homepage layout and footer copy.

## Secondary Navigation Proposal

Visual Signature should move into a secondary, lab-oriented navigation block.

Recommended label:

- `Visual Signature Lab`

Recommended sub-items:

- `Overview`
- `Governance`
- `Calibration`
- `Corpus`
- `Reviewer`

Recommended placement:

- footer secondary group
- an `Advanced` or `Research` section
- a collapsed lab drawer or secondary nav region

The label should signal that this is a research surface, not the main product.

## Copy Changes

Recommended copy direction:

- Replace product-facing language that implies a single broad observatory with
  scoring-first language.
- Make the homepage headline and helper copy about brand analysis / scoring
  first.
- Treat Visual Signature copy as lab or research copy.

Suggested homepage phrasing:

- `Analyze a brand from its URL`
- `See the latest scores and reports`
- `Visual Signature Lab`

Suggested Visual Signature phrasing:

- `Lab`
- `Research`
- `Advanced`
- `Evidence-only`
- `Human-reviewed visual perception`

What to avoid on the homepage:

- Visual Signature as a peer product in the top hero
- governance language above the scoring form
- long explanations of lab functionality before the scoring action

## Route Naming Suggestions

Do not change canonical behavior first. Re-label before renaming.

Suggested visible labels for existing routes:

- `/visual-signature` -> `Visual Signature Lab`
- `/visual-signature/governance` -> `Advanced`
- `/visual-signature/calibration` -> `Research Calibration`
- `/visual-signature/corpus` -> `Research Corpus`
- `/visual-signature/reviewer` -> `Lab Reviewer`

If aliases are later introduced, keep the current routes canonical and add
friendlier path aliases only after tests confirm nothing regresses.

## What To Hide By Default

On the homepage and main scoring surfaces:

- Visual Signature governance details
- calibration summary blocks
- corpus expansion diagnostics
- reviewer workflow pilot details
- raw JSON
- advanced research metadata

On Visual Signature pages:

- keep governance and calibration visible only as secondary sections
- keep raw JSON collapsed by default

## What To Keep Visible

Always visible on the main product surface:

- brand URL input
- analyze action
- recent analyses
- report entry points
- brand history / results links

Visible but secondary:

- Visual Signature Lab entry point
- research / advanced sections
- calibration status summaries only when the user is already in the lab area

## Staged Implementation Plan

1. Reframe copy only.
   - Update labels and helper text to make scoring the primary hook.
   - Re-label Visual Signature as Lab / Research / Advanced.

2. Rebalance homepage hierarchy.
   - Keep the input form above the fold.
   - Keep results and report access directly below it.
   - Push lab links below the main action path.

3. Adjust navigation grouping.
   - Add a clear primary nav for scoring workflows.
   - Move Visual Signature into a secondary or collapsed nav group.

4. Reduce lab prominence in shared chrome.
   - Change footer and global link treatment so Visual Signature is accessible
     but not dominant.

5. Verify user flow.
   - Home -> analyze -> status -> report should remain the main path.
   - Visual Signature should remain one click away, but not foregrounded.

## Non-Goals

- No scoring logic changes.
- No prompt changes.
- No report changes.
- No Visual Signature semantic changes.
- No capture changes.
- No persistence changes.
- No runtime behavior changes.
