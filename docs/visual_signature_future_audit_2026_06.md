# Visual Signature Future Audit - June 2026

## Verdict

Visual Signature is worth keeping, but not as an immediate replacement for the current Magnetism `visual_identity` signal.

The correct status is: separate project, evidence-only, with a controlled re-entry path. Brand3 core and Scanner should remain stable. Search Enrichment Lab can stay parked. Visual Signature should be audited and validated on its own because it already contains enough architecture to become useful, but it is not ready to become a default scoring dependency.

## Scope

This audit reviews the local Visual Signature system as it exists now:

- `src/visual_signature/`
- `scripts/visual_signature_*.py`
- `web/routes/visual_signature.py`
- `web/visual_signature_data.py`
- `examples/visual_signature/`
- Visual Signature route tests and selected pipeline tests

This document does not propose changing Brand3 scoring, Scanner publication behavior, or report readiness.

## Current State

Visual Signature is not a small abandoned helper. It is a broad lab system with:

- visual extraction and normalization;
- screenshot and viewport analysis;
- multimodal semantic fallback;
- Phase Zero / Phase One / Phase Two evidence records;
- calibration readiness;
- category baselines;
- annotation and human review workflows;
- governance registry and runtime policy matrix;
- read-only local web UI;
- optional shadow persistence inside Brand3 runs.

The code repeatedly states the same boundary: Visual Signature is evidence-only and does not modify scoring, rubric dimensions, production reports, or runtime behavior.

That boundary is technically visible in:

- `web/routes/visual_signature.py`: read-only UI routes.
- `web/visual_signature_data.py`: local artifact adapters under `examples/visual_signature`.
- `src/visual_signature/persistence.py`: raw-input persistence only.
- `src/services/brand_service.py`: optional `enable_visual_signature_shadow_run`.
- `src/visual_signature/governance/runtime_policy_matrix.py`: `scoring_integration` blocked.

## Architecture Observed

### Web UI

The Visual Signature web section is a local read-only lab:

- `/visual-signature`
- `/visual-signature/governance`
- `/visual-signature/calibration`
- `/visual-signature/corpus`
- `/visual-signature/reviewer`
- screenshot and artifact preview routes

It renders generated artifacts and screenshots from `examples/visual_signature`. It does not execute production scoring.

### Extraction

`src/visual_signature/extract_visual_signature.py` builds a structured `visual-signature-mvp-1` payload from existing web data or a Visual Signature acquisition adapter. It normalizes:

- colors;
- typography;
- logo signals;
- layout;
- components;
- assets;
- consistency;
- extraction confidence;
- viewport obstruction;
- optional screenshot semantics.

The extractor explicitly prefers existing Brand3 web payloads to avoid duplicate acquisition calls during a main analysis run.

### Vision and Multimodal Semantics

`src/visual_signature/vision/multimodal_analyzer.py` is defensive. It returns a stable fallback contract for:

- missing screenshot;
- missing API key;
- unreadable image;
- LLM timeout/error;
- JSON parse error;
- invalid model response.

This is good design for a lab that may later compare visual evidence. It is not enough, by itself, to make scoring decisions.

### Evidence Phases

Visual Signature has a real evidence pipeline:

- Phase Zero defines taxonomies, schemas, states, transitions, uncertainty policy, review records, and dataset eligibility.
- Phase One builds perceptual observation/state/transition records from captures.
- Phase Two joins Phase One evidence with human review and recalculates reviewed eligibility.

This is stronger than a one-off visual scrape. It is closer to an evidence governance system.

### Calibration and Governance

The calibration readiness gate is explicit:

- minimum total claims;
- minimum reviewed claims;
- minimum categories;
- minimum claims per category;
- confidence bucket coverage;
- contradiction and unresolved-rate thresholds.

The governance matrix blocks `production_runtime`, `scoring_integration`, and `model_training` for relevant capabilities. That is the right default.

### Brand3 Integration Boundary

Brand3 can run Visual Signature as a shadow path:

- `_run_visual_signature_shadow(...)` in `src/services/brand_service.py`
- persisted as raw evidence through `save_visual_signature_evidence`
- no scoring mutation

This is the right integration shape for now.

## Relationship With Magnetism `visual_identity`

Visual Signature could eventually improve or partially replace the current `visual_identity` coherence input, but it should not do so now.

The current `visual_identity` warning we saw on Netlify is relevant because it shows visual evidence is still a weak frontier. But that does not prove Visual Signature is ready to be promoted. It only proves we need a better comparison framework.

The safe path is:

1. Keep current `visual_identity` scoring unchanged.
2. Run Visual Signature as shadow evidence on selected cases.
3. Compare its observations against current coherence breakdowns.
4. Promote only fields that are stable, explainable, cheap enough, and demonstrably better.

## Risks

### Too Broad

There are many modules, scripts, examples, generated artifacts, and tests. The project has enough surface area to drift unless we define a narrow future goal.

### Artifact Staleness

The web UI is driven by local artifacts under `examples/visual_signature`. Those artifacts are useful for review, but they can become stale without regular regeneration.

### No Promotion Contract Yet

There is shadow persistence, but no canonical `VisualSignatureObservation` contract mapped into Scanner evidence. That is correct today, but it must exist before any scoring integration.

### Provider and Cost Risk

Multimodal semantics may call the LLM when screenshots exist and API keys are present. This is acceptable for lab or shadow validation, not for default public scoring until cost, latency, failure modes, and value are measured.

### Test Drift

During this audit, the Visual Signature subset mostly passed, but one route test had a stale home-navigation assertion for `href="/brand-audit"`. The current home exposes Scanner, reports, Visual Signature, Scanner API, and result text for `Auditoría de Marca`. The test was updated to match the current UI.

## Validation Performed

Command:

```bash
./.venv/bin/python -m pytest tests/test_visual_signature.py tests/test_visual_signature_vision.py tests/test_visual_signature_multimodal.py tests/test_visual_signature_phase_zero.py tests/test_visual_signature_phase_one.py tests/test_visual_signature_phase_two.py tests/test_visual_signature_calibration_readiness.py tests/test_visual_signature_runtime_policy_matrix.py tests/test_visual_signature_capability_registry.py tests/test_web_visual_signature_routes.py -q
```

Initial result:

- 87 passed
- 1 failed

Failure:

- `tests/test_web_visual_signature_routes.py::WebVisualSignatureRouteTests::test_existing_scoring_home_still_exposes_scan_form_and_navigation`
- Cause: stale expectation for `/brand-audit` link in home navigation.

## Recommendation

Keep Visual Signature alive, but treat it as a separate project with its own decision gate.

Recommended decision:

- Brand3 core / Scanner: stable; do not touch unless a real bug appears.
- Search Enrichment Lab: parked.
- Visual Signature: audit and validate future as its own workstream.
- No immediate scoring integration.
- No immediate replacement of `visual_identity`.

## Re-entry Plan

### 1. Inventory Alive vs Stale

Create a compact inventory of:

- runnable scripts;
- generated artifacts;
- required inputs;
- current outputs;
- tests covering each area;
- artifacts that are stale or only illustrative.

### 2. Run Full Visual Signature Health Check

Run the complete Visual Signature test group, including:

- extraction;
- vision;
- multimodal fallback;
- phase zero/one/two;
- calibration;
- baselines;
- governance;
- corpus expansion;
- web routes.

### 3. Regenerate Governance and Calibration Artifacts

Regenerate capability registry, runtime policy matrix, calibration readiness, and platform bundle. Compare diffs before accepting them.

### 4. Select Comparison Brands

Use a small set of real cases:

- Netlify, because current deploy/local diagnostic showed visual identity variability.
- Sklum, because the scanner result became good after robustness work.
- ElevenLabs, because prior failure exposed degraded canonical TLDR behavior.
- LangChain, because it validated the Research Pack / Analyst Pass path.
- One visually distinctive ecommerce or editorial brand from the existing corpus.

### 5. Define `VisualSignatureObservation`

Before integration, define a small canonical output contract:

- source URL;
- capture type;
- screenshot availability;
- extraction confidence;
- obstruction state;
- palette/composition summary;
- visual coherence observation;
- limitations;
- eligibility for Scanner use;
- raw payload reference.

This should be read by Scanner only as evidence, not as a score.

### 6. Shadow Compare Against `visual_identity`

For each selected brand, compare:

- current Magnetism `visual_identity`;
- screenshot capture diagnostics;
- Visual Signature observation;
- human review notes where needed;
- cost and latency.

Promotion requires evidence that Visual Signature reduces false weak/false strong visual conclusions.

### 7. Decide Narrow Promotion

Possible outcomes:

- keep lab-only;
- use as report-side explanatory evidence;
- use as Scanner shadow diagnostics;
- use selected fields as `visual_identity` support evidence;
- replace part of `visual_identity` only after stronger proof.

## What Not To Do Now

- Do not replace `visual_identity` directly.
- Do not connect Visual Signature to scoring by default.
- Do not run expensive multimodal calls by default in public Scanner flows.
- Do not refactor Brand3 core around Visual Signature.
- Do not delete the lab: there is too much evidence architecture to discard without a focused health pass.

## Bottom Line

Visual Signature is not dead code and not production-ready scoring infrastructure.

It is a serious evidence lab with enough structure to justify a future validation project. The next useful move is not integration; it is a narrow re-entry audit with live comparisons against the exact visual failures and warnings we have already observed.
