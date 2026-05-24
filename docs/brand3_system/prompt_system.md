# Brand3 Prompt System

This document explains where Brand3 prompts live, what they affect, and how to change them safely.

## Where Prompts Live

### Scoring-related prompts

- `src/features/llm_analyzer.py`
- `src/features/coherencia.py`
- `src/features/diferenciacion.py`
- `src/features/percepcion.py`
- `src/features/vitalidad.py`
- `src/features/authenticity.py`

These modules contain the LLM instructions used by the feature extractors that feed scoring.

### Report narrative prompts

- `src/reports/narrative.py`

This module contains the prompts and deterministic fallbacks for:

- synthesis
- per-dimension findings
- cross-dimension tensions

### Visual Signature prompts and contracts

- `src/visual_signature/annotations/prompts.py`
- `src/visual_signature/annotations/review/*`

These are separate from scoring and should remain a separate semantic layer.

## Which Prompts Affect Scoring

Scoring-relevant prompts live inside the feature extractors.

They affect:

- feature values
- confidence
- per-dimension score derivation
- the data that later feeds report readiness and narrative overlays

If a prompt changes a feature extractor, it can change scores.

## Which Prompts Affect Report Narrative

`src/reports/narrative.py` affects report copy, not scoring.

It controls:

- synthesis prose
- per-dimension findings
- cross-dimension tensions
- deterministic fallback wording when LLM output is unavailable

## Which Prompts Affect Fallback / Narrative Overlays

The fallback and overlay behavior lives in:

- `src/reports/narrative.py`
- `src/reports/dossier.py`

The dossier wires narrative overlays into the base report view-model. The renderer does not call the LLM directly.

## Prompt Guardrails

Brand3 prompts should stay:

- evidence-led
- explicit about conditional language
- strict about source separation
- resistant to echo-chamber language
- defensive about malformed or missing LLM output

For report writing specifically, Brand3 should keep:

- score out of opening lines
- observation separate from implication
- fallback prose honest about missing synthesis
- generic consultant language out of the output

## How To Edit Prompts Safely

1. Update the prompt text in the owning module.
2. Preserve the JSON / text contract expected by the caller.
3. Preserve fallback behavior for empty or malformed responses.
4. Run the narrow tests for the affected area.
5. Run snapshot tests if the output is user-visible.
6. Update docs if the semantic contract changes.

## What Not To Touch Without Approval

- scoring formulas
- rubric dimensions
- feature contracts that feed the scoring engine
- report renderer structure
- Visual Signature semantics
- persistence schema used by prompt cache or run snapshots

## Safe Change Zones

- wording improvements with test coverage
- prompt guardrail tightening
- fallback phrasing refinements
- prompt version bumps when the cache contract changes

## Risky Change Zones

- changing response shapes
- changing the meaning of feature values
- changing prompt output that downstream code parses
- changing `PROMPT_VERSION` without thinking through cache invalidation
- mixing Visual Signature semantics into scoring prompts

## Suggested Tests

- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_narrative.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_renderer.py tests/test_reports_snapshot.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_feature_extractors.py tests/test_scoring_engine.py -q`
- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_visual_signature_* -q`
