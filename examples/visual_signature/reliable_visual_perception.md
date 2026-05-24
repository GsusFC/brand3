# Brand3 Reliable Visual Perception

This document formalizes the current Visual Signature architecture so future
development stays evidence-preserving, conservative, and traceable.

## Core Thesis

Brand3 Visual Signature is not a scraper.

It is an evidence-preserving visual perception system.

The system exists to observe, classify, compare, and preserve visual evidence
without silently mutating the environment it is analyzing.

Three rules define the architecture:

1. Raw evidence must remain immutable.
2. Clean or attempted states are supplemental, never replacements.
3. Any intervention must be explicitly logged and reviewable.

Visual Signature therefore treats capture, interpretation, and intervention as
different things.

## Perception Stack

Visual Signature is organized as a stack of evidence layers.

### 1. Raw Acquisition Layer

This layer captures the original page state and stores the raw viewport,
payload metadata, acquisition status, and any failures.

The raw capture is the primary evidence source.

### 2. Visual Surface Layer

This layer reads screenshot-derived evidence such as palette, whitespace,
density, composition, and other first-impression traits.

It describes what is visibly present, not what the page "means."

### 3. Obstruction Perception Layer

This layer detects cookie banners, consent modals, login walls, paywalls,
newsletter modals, promo overlays, sticky bars, and other viewport obstructions
that interfere with first-impression analysis.

Its purpose is diagnostic. It does not dismiss, bypass, or modify anything by
default.

### 4. Interaction-Risk Layer

This layer decides whether a minimal intervention is safe enough to attempt.

It is conservative by design and must prefer inaction over ambiguous action.

### 5. Mutation Audit Layer

This layer records any attempted state change, including:

- what was observed before the interaction
- what was attempted
- what changed after the interaction
- whether the raw state remained intact

The audit is part of the evidence, not a side effect.

### 6. Counterfactual Evidence Layer

This layer preserves both the raw state and the attempted/clean state so the
system can compare before/after conditions without overwriting the original.

This is supplemental evidence only.

### 7. Annotation / Review Layer

This layer stores offline multimodal annotations and human review decisions on
top of the evidence stack.

Annotations describe evidence quality and interpretation confidence. They do not
replace the source evidence.

### 8. Scoring Boundary

This is the hard boundary between evidence and Brand3 scoring.

Visual Signature remains outside scoring unless a future architecture decision
explicitly and safely moves a specific signal across that boundary.

## Perceptual States

Visual Signature uses explicit perceptual states to avoid silent ambiguity.

### `RAW_STATE`

The original capture before any attempted intervention.

### `OBSTRUCTED_STATE`

A raw state where an overlay, modal, wall, or banner materially blocks first
impression analysis.

### `CLEAN_ATTEMPT_STATE`

A post-intervention state that was produced by a minimal safe dismissal attempt.

This state is supplemental and never replaces the raw state.

### `MINIMALLY_MUTATED_STATE`

A state where the environment was changed only through a narrowly scoped,
logged, reversible interaction.

### `UNSAFE_MUTATED_STATE`

A state where the environment has been changed in a way that breaks evidence
integrity, crosses a protected boundary, or is too ambiguous to trust.

### `REVIEW_REQUIRED_STATE`

A state that cannot be interpreted safely without human review.

This includes ambiguous overlays, low-confidence obstruction cases, and any
evidence sequence where mutation provenance is incomplete.

## Evidence Taxonomy

Visual Signature distinguishes several kinds of evidence.

### Observed Evidence

Directly captured evidence from the page, viewport, screenshot, or extracted
payload.

### Inferred Evidence

A conclusion derived from observed evidence using heuristics or comparison
logic.

### Heuristic Evidence

A structured rule-based estimate, such as obstruction type, density, palette
complexity, or agreement level.

### Model Annotation

A multimodal or provider-based interpretation layered on top of existing
evidence.

### Human Review

A human judgment about usefulness, hallucination risk, ambiguity, or target
quality.

### Mutation Record

An explicit log of any attempted or successful interaction that changed the
page state.

### Counterfactual Evidence

The paired raw and attempted states that allow before/after comparison without
destroying provenance.

## Interaction Policy

Interaction is allowed only when the system can justify it conservatively.

### `safe_to_dismiss`

Use only when the overlay is obviously a reversible cookie or consent surface
and the action target is explicit and safe.

Examples:

- cookie banner with exact `Accept all`
- cookie banner with exact `Reject all`
- cookie modal with exact `Close`
- newsletter modal with exact `X`
- newsletter modal with exact `Dismiss`

### `unsafe_to_mutate`

Use when the target is ambiguous, stateful, or materially changes access to the
page.

Examples:

- login wall
- paywall
- geo gate
- protected content
- ambiguous `Manage choices`
- ambiguous `Close chat`
- ambiguous `Close cart`

### `requires_human_review`

Use when the overlay may be safe in principle, but the evidence is not strong
enough for a minimal automated action.

Examples:

- unclear consent framework
- low-confidence overlay with weak target labeling
- icon-only affordance that cannot be confirmed safely

### `observe_only`

Use when the system should record the obstruction but take no action.

### `protected_environment`

Use when the page state is intentionally guarded or when intervention would
cross a trust boundary.

Examples:

- login wall
- paywall
- geo gate
- protected account flow

## Mutation Principles

1. No silent mutation.
2. Raw viewport is preserved as primary evidence.
3. Every interaction must be logged.
4. Clean attempts must preserve provenance.
5. A successful click is not enough; success is measured by the before/after
   evidence delta.
6. Supplemental states must never overwrite the raw state.

## Scoring Boundary

Visual Signature remains separate from Brand3 scoring.

No obstruction signal, annotation signal, dismissal signal, agreement signal, or
perception metric should affect scoring unless a future explicit architecture
decision moves it across the boundary.

Shadow-run persistence also remains evidence-only. It stores raw evidence for
traceability, calibration, and review.

## Failure Philosophy

Visual Signature should fail conservatively.

Principles:

- conservative failure is preferred
- no action is better than ambiguous action
- unknown is a valid output
- `not_interpretable` is not a weak brand judgment
- uncertainty should be represented explicitly rather than hidden

This is a perception system, not a forced interpretation system.

## Future Phases

The next safe phases are:

### Affordance Understanding

Improve target discovery for safe reversible overlays without broadening
interaction aggressively.

### Confidence-Aware Intervention

Let confidence and obstruction clarity govern whether any dismissal attempt is
allowed.

### Multi-State Perception

Model richer state transitions across raw, obstructed, attempted, and reviewed
states.

### Multimodal Provider Pilot

Use a controlled provider pilot for annotation only, with calibration against
local corpus data.

### Human Review Calibration

Use offline reviewer workflows to measure usefulness, hallucination, and target
reliability.

### Perceptual Friction Research

Measure how much negotiation a page requires before its visual identity can be
seen clearly.

## Operating Rule

Keep Visual Signature as evidence-only until the capture stack, obstruction
perception, interaction policy, and calibration layers remain stable enough to
justify any wider use.

For the official Visual Signature capability governance map, see
[capability_registry.md](./governance/capability_registry.md). Capability
presence does not imply production approval. Readiness is scope-dependent, and
the registry is evidence-only governance metadata that does not modify scoring,
rubric dimensions, runtime behavior, reports, or UI.

For the scope-based execution companion, see
[runtime_policy_matrix.md](./governance/runtime_policy_matrix.md). Capability
existence does not imply runtime approval, runtime policy is scope-dependent,
`production_runtime` blocks runtime mutation, and the matrix is governance
metadata only. It does not change scoring, rubric dimensions, capture
behavior, production UI/reports, taxonomy, or runtime behavior.
