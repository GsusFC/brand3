# Visual Diagnosis Clean Capture Probe - 2026-06-07

## Verdict

Brand3 already had infrastructure to attempt safe cookie/overlay dismissal, but
the current policy did not produce clean captures for this calibration set.

This means the previous concern was valid: the issue is not that we forgot
cookies entirely. The issue is that the clean-capture path is conservative,
separate from Visual Diagnosis Lab, and not strong enough yet to remove the
dominant page-state noise.

## What Was Tested

Input:

- `/tmp/brand3_visual_diagnosis_clean_capture_probe/capture_input.json`

Command:

```bash
./.venv/bin/python scripts/visual_signature_capture_screenshots.py \
  --input /tmp/brand3_visual_diagnosis_clean_capture_probe/capture_input.json \
  --output-dir /tmp/brand3_visual_diagnosis_clean_capture_probe/screenshots \
  --manifest /tmp/brand3_visual_diagnosis_clean_capture_probe/capture_manifest.json \
  --capture-type viewport \
  --attempt-dismiss-obstructions
```

Output:

- `/tmp/brand3_visual_diagnosis_clean_capture_probe/capture_manifest.json`
- `/tmp/brand3_visual_diagnosis_clean_capture_probe/screenshots/dismissal_audit.json`

The command emitted the known local Python `hashlib` warnings for `blake2b` and
`blake2s`, but completed successfully.

## Capture Results

| Brand | Dismiss attempted | Dismiss successful | Clean attempt | Before obstruction | After obstruction | Note |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Linear | no | no | no | `newsletter_modal`, blocking, 0.92 | `newsletter_modal`, blocking, 0.92 | `no_safe_close_button_found` |
| OpenAI | no | no | no | `cookie_modal`, blocking, 0.92 | `cookie_modal`, blocking, 0.92 | `no_safe_cookie_button_found` |
| The Verge | no | no | no | `newsletter_modal`, blocking, 0.92 | `newsletter_modal`, blocking, 0.92 | `no_safe_close_button_found` |
| Allbirds | yes | no | yes | `newsletter_modal`, blocking, 0.92 | `newsletter_modal`, blocking, 0.92 | clicked `Close` |
| Stripe Docs | no | no | no | `newsletter_modal`, blocking, 0.92 | `newsletter_modal`, blocking, 0.92 | `no_safe_close_button_found` |
| Headspace | no | no | no | `login_wall`, blocking, 0.92 | `login_wall`, blocking, 0.92 | no safe mutation |
| Notion | yes | no | yes | `promo_modal`, blocking, 0.92 | `promo_modal`, blocking, 0.92 | clicked `X` |
| Le Labo | no | no | no | `newsletter_modal`, blocking, 0.92 | `newsletter_modal`, blocking, 0.92 | `no_safe_close_button_found` |

Summary:

- 8/8 captures completed.
- 2/8 attempted a dismissal mutation.
- 2/8 produced a `clean_attempt` image.
- 0/8 were classified as successful dismissal.
- 8/8 remained blocked after the safe mutation policy.

## Manual Visual Check

Allbirds:

- raw capture had country selector plus cookie banner;
- clean attempt removed the country selector;
- cookie banner remained;
- this is visually better, but not clean.

Notion:

- raw capture showed the campaign hero with cookie overlay;
- clean attempt moved the page state toward lower page/footer content;
- cookie overlay remained;
- this is worse for first-impression diagnosis.

## Lab Integration Change

Visual Diagnosis Lab now understands `screenshot_capture_path` rows produced by
the Visual Signature capture manifest.

It can derive `page_state` automatically from:

- `before_obstruction`;
- `after_obstruction`;
- `dismissal_attempted`;
- `dismissal_successful`;
- `dismissal_block_reason`;
- `raw_screenshot_path`;
- `clean_attempt_screenshot_path`.

Conservative screenshot selection:

- use raw screenshot by default;
- use `clean_attempt_screenshot_path` only when `dismissal_successful` is true.

This prevents a failed or degrading clean attempt from silently becoming the
diagnosis screenshot.

## Auto Page-State Lab Run

Input:

- `/tmp/brand3_visual_diagnosis_clean_capture_probe/visual_diagnosis_manifest.auto-page-state.json`

Output:

- `/tmp/brand3_visual_diagnosis_clean_capture_probe/lab_auto_page_state_after_fix/20260607T124659Z/comparison.json`

Result:

- 8/8 rows were marked `page_state.status = cookie_obstructed`.
- 8/8 rows were marked `capture_quality = blocked`.
- No bot-check false positives after fixing the `bot` vs `bottom` substring issue.

## Decision

Do not promote Visual Diagnosis into scoring yet.

The next Lab improvement should target capture-state quality, not taste
heuristics:

1. Improve obstruction classification so `newsletter_modal`, `cookie_modal`,
   `location_gate`, `promo_modal` and `login_wall` are separated cleanly.
2. Improve safe dismissal candidate detection for explicit accept/reject/close
   buttons inside the active obstruction.
3. Score whether `clean_attempt` improves or degrades first impression before it
   is used downstream.
4. Keep raw evidence preserved as the primary artifact.

## Safe Dismissal Follow-Up

After the first clean-capture probe, candidate detection was tightened in the
lab-only capture script:

- Spanish cookie consent labels are now recognized: `Aceptar`, `Aceptar todas`,
  `Rechazar`, `Rechazar todas`, `Denegar`, `Continuar`, `Cerrar`.
- Dismissal phrase matching now allows short labels such as `Aceptar todas las
  cookies`, but rejects long banner-region text as a click target.
- Candidate selection requires the deterministic affordance policy to resolve
  as `safe_to_dismiss`.
- If a visually detected `newsletter_modal` or `promo_modal` carries cookie /
  consent / privacy signals, button semantics are evaluated with cookie-consent
  context.

Follow-up command:

```bash
./.venv/bin/python scripts/visual_signature_capture_screenshots.py \
  --input /tmp/brand3_visual_diagnosis_safe_dismissal_probe_input.json \
  --output-dir /tmp/brand3_visual_diagnosis_safe_dismissal_probe_after/screenshots \
  --manifest /tmp/brand3_visual_diagnosis_safe_dismissal_probe_after/capture_manifest.json \
  --capture-type viewport \
  --attempt-dismiss-obstructions
```

Follow-up result:

| Brand | Candidate detection | Attempted | Successful | Note |
| --- | --- | ---: | ---: | --- |
| OpenAI | none | no | no | no safe cookie button found |
| Allbirds | `Close` as active obstruction | yes | no | raw evidence preserved |
| Le Labo | `Aceptar` and `Rechazar` as active cookie consent controls | yes | no | `Personalizar` rejected as preferences |

This is an improvement in safe affordance discovery, not yet a clean-capture
success. The conservative rule remains: failed clean attempts do not replace
raw screenshots in Visual Diagnosis.

The follow-up Lab pass also emits `clean_capture_decision`:

| Brand | Clean capture decision | Improvement state | Selected variant |
| --- | --- | --- | --- |
| OpenAI | `raw_only` | `not_evaluated` | `raw_viewport` |
| Allbirds | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` |
| Le Labo | `keep_raw_no_material_improvement` | `no_material_improvement` | `raw_viewport` |

This gives us a machine-readable reason for keeping raw evidence instead of
relying on manual judgment after each probe.

The capture-side `dismissal_audit.json` also reports
`clean_attempt_quality_distribution` and each result includes
`clean_attempt_quality`. This keeps the capture audit and the Lab decision
aligned: the audit tells us whether the mutation was a clear improvement,
partial improvement, no material improvement, degraded, or unavailable; the Lab
decides whether that is strong enough to replace raw evidence.

## Validation

```bash
./.venv/bin/python -m pytest tests/test_visual_diagnosis.py tests/test_visual_diagnosis_style_capture.py -q
```

Result:

- `32 passed`

Follow-up validation:

```bash
./.venv/bin/python -m pytest tests/test_visual_signature_capture_screenshots.py tests/test_visual_diagnosis.py tests/test_visual_diagnosis_style_capture.py -q
```

Result:

- `55 passed`
