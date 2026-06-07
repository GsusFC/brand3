# Visual Interpretation Lab Evaluation

Evaluated: 2026-06-07

Run: `/tmp/brand3_visual_interpretation_lab_gemini/20260607T202134Z`

## Verdict

Continue, but keep it Lab-only.

The experiment shows enough value to continue: Gemini produced better visual
interpretation than the heuristic path on several real brands and correctly
refused contaminated captures that the manifest still marked as usable.

It is not ready for Brand Audit, Magnetism Scanner, scoring or public reports.
The current flow is too slow and too dependent on Pro adjudication.

## Metrics

| Metric | Value |
| --- | ---: |
| Brands | 10 |
| Valid JSON outputs | 10 |
| Invalid outputs | 0 |
| Usable interpretations | 7 |
| Limited interpretations | 0 |
| Not evaluable | 3 |
| Provider failures | 0 |
| Pro-adjudicated rows | 7 |
| Missing screenshot rows | 1 |
| Total latency | 219244 ms |
| Average latency | 21924 ms |
| Prompt tokens | 45207 |
| Candidate tokens | 11318 |
| Total tokens | 76993 |

## What Improved

- The contract held across all 10 rows.
- Gemini rejected OpenAI as not evaluable because the screenshot was a
  Cloudflare verification page.
- Gemini rejected Hermes as not evaluable because the screenshot was an access
  restriction page, not the real brand site.
- The Verge was read as an editorial media system and the model separated the
  privacy banner from the underlying brand identity.
- Linear, Stripe Docs, Headspace, Notion and Le Labo received operationally
  useful reads and recommendations.
- The model identified disagreement between screenshot reality and automated
  visual evidence in several cases.

## What Still Fails

- The deterministic capture metadata is weaker than the model: OpenAI and
  Hermes were marked as usable packs even though the screenshots were blocked.
- Seven rows used `gemini-2.5-pro` adjudication. That is not viable for default
  product usage.
- Average latency was 21.9 seconds per brand in the adjudicated run.
- Some category mapping remains interpretive. Allbirds was useful as a
  sustainability/lifestyle read, but not a strict ecommerce profile.
- The benchmark proves promise, not production readiness.

## Decision

Do not integrate with Brand Audit or Magnetism Scanner yet.

Continue the Lab only if the next pass focuses on:

1. Flash-only quality before Pro adjudication.
2. Stronger page-state and obstruction metadata.
3. A stricter adjudication policy.
4. Human review comparison of recommendation usefulness.
5. Token and latency caps before any promotion discussion.

Promotion to product should require stable Flash performance, correct refusal on
blocked captures and materially better strategist usefulness than the heuristic
Visual Diagnosis path.
