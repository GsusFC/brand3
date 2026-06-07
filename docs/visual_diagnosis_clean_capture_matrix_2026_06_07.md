# Visual Diagnosis Clean Capture Matrix - 2026-06-07

## Verdict

The new clean-capture contract is useful, but the capture path is not yet
producing clean screenshots on this matrix.

The improvement is in observability and safe affordance discovery, not in final
capture quality:

- 8/8 captures completed.
- 5/8 found safe dismissal controls and attempted mutation.
- 0/8 produced a successful clean attempt.
- 5/5 attempted mutations were classified as `no_material_improvement`.
- 8/8 Lab rows kept `raw_viewport` as the selected variant.

This supports keeping Visual Diagnosis in Lab mode. It is not ready to feed
Brand Audit scoring or replace `visual_identity`.

## Inputs

Command:

```bash
./.venv/bin/python scripts/visual_signature_capture_screenshots.py \
  --input /tmp/brand3_visual_clean_matrix/capture_input.json \
  --output-dir /tmp/brand3_visual_clean_matrix/screenshots \
  --manifest /tmp/brand3_visual_clean_matrix/capture_manifest.json \
  --capture-type viewport \
  --attempt-dismiss-obstructions
```

Capture outputs:

- `/tmp/brand3_visual_clean_matrix/capture_manifest.json`
- `/tmp/brand3_visual_clean_matrix/screenshots/dismissal_audit.json`

Lab command:

```bash
./.venv/bin/python scripts/visual_diagnosis_lab.py \
  --manifest /tmp/brand3_visual_clean_matrix/lab_manifest.json \
  --output-root /tmp/brand3_visual_clean_matrix/lab_output
```

Lab output:

- `/tmp/brand3_visual_clean_matrix/lab_output/20260607T145308Z/comparison.json`

The capture command emitted the known local Python `hashlib` warnings for
`blake2b` and `blake2s`, but completed successfully.

## Capture Matrix

| Brand | Attempted | Successful | Clean attempt quality | Block reason | Safe candidates |
| --- | ---: | ---: | --- | --- | --- |
| OpenAI | no | no | `not_available` | `no_safe_cookie_button_found` | none |
| Allbirds | yes | no | `no_material_improvement` | - | `Close` |
| Le Labo | yes | no | `no_material_improvement` | - | `Aceptar`, `Rechazar` |
| Notion | yes | no | `no_material_improvement` | - | `Accept all`, `Reject all` |
| Linear | no | no | `not_available` | `no_safe_cookie_button_found` | none |
| Sklum | no | no | `not_available` | `no_safe_cookie_button_found` | none |
| ElevenLabs | yes | no | `no_material_improvement` | - | `REJECT ALL`, `ACCEPT ALL COOKIES`, `X` |
| Netlify | yes | no | `no_material_improvement` | - | `Reject All`, `Accept All` |

Distribution:

- `clean_attempt_quality_distribution`: `{"no_material_improvement": 5}`
- attempted: `5`
- successful: `0`

## Lab Decisions

| Brand | Decision | Improvement state | Selected variant | Page state |
| --- | --- | --- | --- | --- |
| OpenAI | `raw_only` | `not_evaluated` | `raw_viewport` | `cookie_obstructed` |
| Allbirds | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` | `cookie_obstructed` |
| Le Labo | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` | `cookie_obstructed` |
| Notion | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` | `cookie_obstructed` |
| Linear | `raw_only` | `not_evaluated` | `raw_viewport` | `cookie_obstructed` |
| Sklum | `raw_only` | `not_evaluated` | `raw_viewport` | `cookie_obstructed` |
| ElevenLabs | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` | `cookie_obstructed` |
| Netlify | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` | `cookie_obstructed` |

## Interpretation

The safe-affordance layer is now finding real controls in more cases:

- Spanish consent labels are handled in Le Labo.
- English accept/reject controls are handled in Notion, ElevenLabs and Netlify.
- Close controls are handled in Allbirds.

But the mutation outcome is still weak:

- Post-click obstruction remains `blocking` with coverage `0.92` in every
  attempted case.
- No clean attempt is eligible to replace raw evidence.
- The Lab correctly keeps all rows on `raw_viewport`.

## Next Work

Do not tune taste heuristics from these captures.

The next useful investigation is capture mechanics:

1. Verify whether click actions are firing but consent state is not persisted.
2. Add post-click waits or second-pass obstruction analysis only if evidence
   shows the page updates late.
3. Inspect whether cookie controls inside CMP/iframe/shadow DOM require a
   different selector path.
4. Keep raw evidence primary until at least one matrix produces stable
   `clear_improvement` or defensible `partial_improvement` cases.

## Follow-up: Visible Overlay DOM Snapshot

After verifying that consent clicks were firing but the post-click detector still
reported blocked states, the capture path was changed to pass only visible
overlay-like DOM snippets into obstruction analysis instead of the full page
HTML. This avoids treating hidden CMP remnants, footer privacy links, or global
site markup as active first-viewport obstruction evidence.

Focused probe:

- Inputs: Le Labo, Netlify, ElevenLabs.
- Captures: 3/3 OK.
- Attempted dismissals: 3/3.
- `clear_improvement`: 2/3.
- `no_material_improvement`: 1/3.
- Netlify and ElevenLabs became clean after rejecting cookies.
- Le Labo remained obstructed because a visible newsletter/promo layer remained
  after accepting cookies.

Matrix rerun:

- Captures: 8/8 OK.
- Attempted dismissals: 4.
- Successful dismissals: 2.
- `clean_attempt_quality_distribution`: `{"clear_improvement": 2, "no_material_improvement": 2}`.
- Clear improvements: ElevenLabs, Netlify.
- No material improvement: Allbirds, Le Labo.
- No attempted mutation: OpenAI, Notion, Linear, Sklum.

Interpretation:

- The previous 0/5 result was partly caused by false positives from non-visible
  DOM.
- The safe mutation policy is still conservative: visible promo/newsletter
  layers are not treated as solved cookie banners.
- This is a Lab-only capture robustness improvement, not a reason to connect
  Visual Diagnosis to Brand Audit scoring.

Known limitation:

- The current click-target discovery can still enumerate some controls outside
  the first viewport in long pages. The ownership and interaction policy blocks
  unsafe clicks, but this should be tightened later so candidate discovery uses
  the same first-viewport discipline as obstruction analysis.
