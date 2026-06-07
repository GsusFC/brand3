# Visual Diagnosis Human Review Probe - 2026-06-07

## Verdict

The first human-review pass supports the current Lab direction, with one
important boundary: Visual Diagnosis is useful when multiple evidence sources
agree, but computed-style-only rows must stay limited.

This probe is not a final quality benchmark. It is a calibration pass to verify
that `comparison.json` can carry human review notes and expose source conflicts
without changing diagnosis output.

## Run

Input manifest:

- `/tmp/brand3_visual_diagnosis_visual_heavy_probe/manifest.six-brand-human-review.json`

Output:

- `/tmp/brand3_visual_diagnosis_visual_heavy_probe/lab_six_brand_human_review/20260607T115815Z/comparison.json`

Review fixtures:

- `examples/visual_diagnosis_lab/reviews/six_brand_probe/netlify.json`
- `examples/visual_diagnosis_lab/reviews/six_brand_probe/langchain.json`
- `examples/visual_diagnosis_lab/reviews/six_brand_probe/elevenlabs.json`
- `examples/visual_diagnosis_lab/reviews/six_brand_probe/sklum.json`
- `examples/visual_diagnosis_lab/reviews/six_brand_probe/a24.json`
- `examples/visual_diagnosis_lab/reviews/six_brand_probe/hermes.json`

The run emitted the known local Python `hashlib` warnings for `blake2b` and
`blake2s`, but completed successfully.

## Results

| Brand | Sources | Diagnosis read | Human verdict | Human fit |
| --- | --- | --- | --- | --- |
| `www.netlify.com` | `computed_style`, `web_payload`, `screenshot_vision` | `functionally_clear` | `directionally_useful` | profile yes, identity yes |
| `www.langchain.com` | `computed_style`, `web_payload`, `screenshot_vision` | `functionally_clear` | `useful_but_obstructed` | profile yes, identity yes |
| `elevenlabs.io` | `computed_style`, `web_payload`, `screenshot_vision` | `weak_or_inconsistent` | `needs_manual_check` | profile yes, identity partial |
| `www.sklum.com` | `computed_style`, `web_payload`, `screenshot_vision` | `commerce_clear` | `directionally_useful` | profile yes, identity yes |
| `A24` | `computed_style` | `editorially_coherent` | `insufficient_visual_evidence` | profile partial, identity partial |
| `Hermes` | `computed_style` | `visually_distinctive` | `insufficient_visual_evidence` | profile partial, identity partial |

Aggregates:

- 2 rows: `directionally_useful`
- 1 row: `useful_but_obstructed`
- 1 row: `needs_manual_check`
- 2 rows: `insufficient_visual_evidence`
- 4 rows had `computed_style + web_payload + screenshot_vision`
- 2 rows had `computed_style` only
- 3 rows had human `identity_read_fit = yes`
- 3 rows had human `identity_read_fit = partial`

## Interpretation

### What improved

The Lab can now separate three different situations:

1. Diagnosis is directionally useful: Netlify and Sklum.
2. Diagnosis is useful but polluted by page state: LangChain viewport modal.
3. Diagnosis exposes source conflict: ElevenLabs.

This is better than a single confidence score because the human note explains
why a row is useful, blocked or disputed.

### What remains weak

A24 and Hermes confirm the same boundary seen in the computed-style probe:
computed styles can suggest a profile, but they cannot validate visual taste,
image treatment, composition or brand atmosphere by themselves.

These rows should not be used to tune editorial or luxury heuristics until
screenshot or multimodal evidence is attached.

### ElevenLabs conflict

ElevenLabs is the most useful row in the probe. The Lab reports
`weak_or_inconsistent` because Magnetism contributes `visual_promise_mismatch`,
while screenshot-derived evidence still reports an internally consistent visual
system.

That is not a reason to patch the heuristic immediately. It is evidence that
source disagreement must remain visible in `comparison.json` and charts.

## Decision

Keep Visual Diagnosis Lab-only.

Do not promote this into Brand3 scoring yet. The next useful step is a slightly
larger human-reviewed comparison set where each row has:

- screenshot evidence;
- computed-style evidence;
- web payload evidence;
- optional Magnetism evidence;
- a human `profile_fit`;
- a human `identity_read_fit`;
- a human disagreement note when sources conflict.

Promotion should only be reconsidered when the Lab can show that disagreements
are explainable by source coverage or page state, not by unstable heuristics.

## Validation

```bash
./.venv/bin/python -m pytest tests/test_visual_diagnosis.py tests/test_visual_diagnosis_style_capture.py -q
```

Result:

- `30 passed`
