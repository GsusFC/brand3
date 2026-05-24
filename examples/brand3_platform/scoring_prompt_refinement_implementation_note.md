# Scoring Prompt Refinement Implementation Note

Implemented the low-risk narrative wording refinements planned in:

- `examples/brand3_platform/brand3_report_voice_guide.md`
- `examples/brand3_platform/scoring_prompt_refinement_plan.md`
- `examples/brand3_platform/scoring_narrative_pipeline_audit.md`

Scope stayed limited to report narrative prompts and deterministic fallback wording.
No scoring logic, rubric, renderer structure, or Visual Signature code changed.

## Files updated

- `src/reports/narrative.py`

## Prompt and fallback changes

### Synthesis

- Strengthened observation-first guidance.
- Added explicit observation / implication / tension ordering.
- Required a concrete evidence anchor before interpretation.
- Discouraged generic report openings and score-led openings.
- Preserved the existing score-suppression and §5 tension consistency rules.
- Kept the fallback deterministic, but made it more diagnostic by naming the strongest and weakest dimensions and tying the weaker read to follow-up.

### Dimension findings

- Added an explicit observation / implication / tension model to the prompt.
- Required the first observation sentence to start from a concrete evidence anchor.
- Tightened language around diagnostic reading, not celebratory reading.
- Kept the existing JSON shape, the single-source evidence guardrails, and the fallback title `Available evidence`.
- Made fallback prose more dimension-specific by naming the dimension and the dominant evidence surface.

### Tensions

- Added evidence-anchor-first guidance.
- Kept the existing `null`-preferred rule when no real tension exists.
- Tightened the prompt against consultant-style generic summaries.

## Validation

Validated in this session:

- `PYTHONPATH=. ./.venv/bin/python -m pytest tests/test_reports_narrative.py tests/test_reports_renderer.py tests/test_reports_dossier.py -q`
- `python3 -m json.tool examples/brand3_platform/scoring_prompt_refinement_implementation_note.json`
- `git diff --check`
