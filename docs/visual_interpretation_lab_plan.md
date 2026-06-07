# Visual Interpretation Lab Plan

## Verdict

Visual Signature should stop growing as a heuristic taste engine.

The next experiment is a Lab-only visual interpretation flow based on controlled
evidence plus Gemini multimodal interpretation. Stitch is explicitly out of
scope.

## Decision

- Do not use Stitch.
- Do not connect this work to Brand Audit, Magnetism Scanner, report scoring or
  public output.
- Keep Visual Signature artifacts only where they help create or validate
  visual evidence.
- Freeze heuristic taste/scoring expansion until Gemini-based interpretation
  proves measurable value.

## What We Keep

Keep these pieces as evidence infrastructure:

- Screenshot capture.
- Viewport obstruction detection.
- Page state and capture quality.
- Safe dismissal audit and clean-capture decision.
- Visual evidence bundle concepts.
- Evidence refs and provenance.
- Human review fixtures.
- Reference profiles and anti-pattern vocabulary.
- Guardrail tests that prevent judging blocked or insufficient evidence.

These components should support evidence preparation, not make final visual
taste judgments.

## What We Freeze

Freeze these areas unless a bug blocks the Lab:

- `src/visual_signature/baselines`
- `src/visual_signature/calibration`
- `src/visual_signature/corpus_expansion`
- `src/visual_signature/governance`
- `src/visual_signature/platform`
- `src/visual_signature/phase_zero`
- `src/visual_signature/phase_one`
- `src/visual_signature/phase_two`
- large corpus/example expansion under `examples/visual_signature`

These modules may remain in the repository for traceability, but they should not
receive new feature work until the new Lab proves value.

## New Flow

The Lab should follow the same pattern that works in Brand Audit and Magnetism:

1. Collect controlled evidence.
2. Build a compact evidence pack.
3. Ask a trained LLM to answer operational questions.
4. Validate the output deterministically.
5. Compare against human review.

Proposed flow:

```text
Screenshot + page state + context
  -> VisualEvidencePack
  -> Gemini multimodal interpretation
  -> VisualInterpretation JSON
  -> deterministic validators
  -> benchmark vs human review
```

## VisualEvidencePack

The pack should be compact and explicit:

- `brand_name`
- `website_url`
- `category_hint`
- `screenshot_ref`
- `capture_type`
- `capture_quality`
- `page_state`
- `obstructions`
- `clean_capture_decision`
- `available_sources`
- `visual_helper_signals`
- `known_context`
- `limitations`
- `evidence_refs`

Rules:

- Do not hide capture contamination.
- Do not transform weak evidence into a strong visual claim.
- Do not include giant payloads when short summaries are enough.
- Preserve raw evidence refs.

## VisualInterpretation

The LLM output should be a closed JSON contract, not a free-form essay.

Required fields:

- `status`: `usable`, `limited`, `not_evaluable`
- `reference_profile`
- `identity_read`
- `visual_strengths`
- `visual_weaknesses`
- `distinctiveness_risks`
- `brand_fit`
- `category_fit`
- `recommendations`
- `confidence`
- `evidence_used`
- `limitations`
- `requires_human_review`

Hard rules:

- If capture quality is blocked, the model must return `not_evaluable`.
- If no screenshot is available, confidence must be low.
- Every judgment must cite evidence from the pack.
- Recommendations must be operational, not generic design advice.
- Source disagreement must be explicit.

## Gemini Model Policy

Use only two Gemini tiers for the first benchmark:

- `gemini-2.5-flash`: default benchmark model.
- `gemini-2.5-pro`: adjudicator for disputed or ambiguous rows.

Do not test many model variants. If Flash cannot show value on clean evidence,
the Lab should not expand.

## Benchmark

Use 10 brands:

- 5 rows with clean or usable screenshot evidence.
- 3 rows with contaminated evidence.
- 2 rows with insufficient evidence.

The benchmark should measure:

- strong agreement with human review;
- partial agreement;
- false positives;
- false negatives;
- correct `not_evaluable`;
- source disagreement quality;
- cost per brand;
- latency per brand;
- usefulness of recommendations.

## Success Criteria

The Lab is worth continuing only if it shows:

- clear improvement over the current heuristic diagnosis;
- correct refusal on blocked or insufficient evidence;
- useful interpretation on clean screenshots;
- stable JSON outputs;
- manageable cost;
- recommendations that a strategist would actually use.

## Failure Criteria

Stop or archive the Lab if:

- it mostly repeats generic design advice;
- it judges blocked screenshots;
- it cannot beat human-reviewed heuristic baselines;
- Pro is required for most rows;
- outputs need too much manual cleanup;
- cost is not viable for repeated use.

## Implementation Status

Implemented on 2026-06-07 as Lab-only code:

- `src/visual_interpretation/models.py`
  - `VisualEvidencePack`
  - `VisualInterpretation`
- `src/visual_interpretation/validation.py`
  - deterministic validation rules
- `src/visual_interpretation/gemini.py`
  - native Gemini multimodal request builder
  - default model: `gemini-2.5-flash`
  - optional adjudicator model: `gemini-2.5-pro`
- `scripts/visual_interpretation_lab.py`
  - manifest runner
  - dry-run mode by default
  - `--execute` for real Gemini calls
  - JSON, comparison JSON, metrics JSON and Markdown outputs
- `examples/benchmarks/visual_interpretation_lab/cases.json`
  - 10 real-brand benchmark fixture

The implementation does not write to Brand Audit, Magnetism Scanner, scoring,
reports or production storage.

Dry-run command:

```bash
./.venv/bin/python scripts/visual_interpretation_lab.py \
  --manifest examples/benchmarks/visual_interpretation_lab/cases.json \
  --output-root /tmp/brand3_visual_interpretation_lab
```

Dry-run result on 2026-06-07:

- Total brands: 10
- Valid outputs: 10
- Invalid outputs: 0
- Usable outputs: 9
- `not_evaluable`: 1
- Human-reviewed rows: 10
- Missing screenshot correctly blocked: 1

This only proves the contract and guardrails. It does not prove model quality.

Gemini benchmark result on 2026-06-07:

- Run path: `/tmp/brand3_visual_interpretation_lab_gemini/20260607T202134Z`
- Primary model: `gemini-2.5-flash`
- Optional adjudicator: `gemini-2.5-pro`
- Total brands: 10
- Valid JSON outputs: 10
- Invalid outputs: 0
- Usable outputs: 7
- `not_evaluable`: 3
- Provider failures: 0
- Pro-adjudicated rows: 7
- Average latency: 21924 ms
- Total tokens: 76993

Decision: continue Lab-only. Do not integrate with Brand Audit, Magnetism
Scanner, scoring or public reports yet.

The benchmark shows value because Gemini refused blocked screenshots that the
manifest still marked as usable and produced useful strategist reads on clean
or partly obstructed captures. It also shows non-viability for product today:
too many rows required Pro adjudication and latency is too high.

Detailed evaluation:

- `examples/benchmarks/visual_interpretation_lab/evaluation.md`
- `examples/benchmarks/visual_interpretation_lab/evaluation.json`

## Next Evidence Step

Run a Flash-only benchmark without Pro adjudication:

```bash
BRAND3_LLM_API_KEY=... ./.venv/bin/python scripts/visual_interpretation_lab.py \
  --manifest examples/benchmarks/visual_interpretation_lab/cases.json \
  --execute \
  --model gemini-2.5-flash
```

Then compare against:

- current `visual_diagnosis_lab.py` outputs;
- human review notes;
- false positives on blocked/missing captures;
- recommendation usefulness;
- cost and latency per brand.

Do not connect it to product until this benchmark shows better strategist value
than the current heuristic path.
