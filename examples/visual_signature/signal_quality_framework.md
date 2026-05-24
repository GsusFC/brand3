# Visual Signature Signal Quality Framework

Source batch:

- `examples/visual_signature/calibration_outputs/manifest.json`
- `examples/visual_signature/calibration_outputs/batch_summary.md`
- Completed at: `2026-05-08T12:21:28.677433`

This framework is based only on captures where
`interpretation_status == "interpretable"`. Visual Signature remains a
structured evidence layer. It is not a Brand3 scoring dimension and should not
change rubric weights, production reports, or web UI behavior.

## Calibration Set

Excluded from brand quality comparison:

| Brand | Category | Reason |
| --- | --- | --- |
| Hermes | premium/luxury | `not_interpretable`; acquisition failed with HTTP 403. |
| Joe's Plumbing NYC | weak/small business site | `not_interpretable`; DNS resolution failed. |

Interpretable captures:

| Brand | Category | Confidence | Coverage | Weak signals |
| --- | --- | ---: | ---: | ---: |
| The Verge | editorial/media | 0.76 | 100% | 2 |
| Linear | SaaS | 0.70 | 86% | 3 |
| Allbirds | ecommerce | 0.68 | 86% | 3 |
| Headspace | wellness/lifestyle | 0.68 | 86% | 4 |
| Notion | template-like SaaS | 0.68 | 86% | 4 |
| Stripe Docs | developer-first | 0.67 | 71% | 4 |
| OpenAI | AI-native | 0.60 | 71% | 6 |
| A24 | editorial/media | 0.60 | 86% | 8 |

## Observations By Category

### SaaS: Linear

Linear has useful HTML-derived evidence for palette, layout, and component
structure. It shows a high color confidence, balanced density, and many
recurring component signals. Typography is still missing and assets are weak
because no screenshot is available. CTA labels are noisy: several extracted
items are product/navigation labels rather than true conversion CTAs.

### AI-native: OpenAI

OpenAI is interpretable but weak for visual conclusions. The payload has sparse
layout evidence, limited color extraction, no logo signal, and no typography.
Component counts are high enough to show page structure, but they should not be
read as brand distinction. This is a good example of an interpretable capture
with low signal quality.

### Editorial/media: The Verge and A24

The Verge is the strongest interpretable capture in this batch. It has full
coverage, high typography confidence, dense layout, and recurring editorial
components. A24 is much weaker despite sharing the editorial/media category:
its payload has limited colors, missing typography, lower component confidence,
and consistency limitations. Category comparison is useful here, but only after
separating capture quality from visual quality.

### Ecommerce: Allbirds

Allbirds recovered after the acquisition fix and is now interpretable. It has
good palette coverage, balanced layout, and ecommerce navigation/CTA labels.
Typography is only partially detected and logo is missing. Product imagery,
hero quality, lifestyle photography, and merchandising composition cannot be
interpreted without screenshot or vision analysis.

### Developer-first: Stripe Docs

Stripe Docs has strong color and component extraction, but layout coverage is
limited and logo is missing. The CTA list includes utility/navigation strings
such as search and sign-in actions. The category makes dense navigation
expected, so component density should be interpreted relative to docs surfaces,
not general consumer websites.

### Wellness/lifestyle: Headspace

Headspace has strong color, layout, and component extraction. It lacks reliable
typography and image-style interpretation. Because wellness/lifestyle brands
depend heavily on illustration, photography, tone, and softness of composition,
this category needs screenshot or vision before making quality claims.

### Template-like SaaS: Notion

Notion shows strong HTML-derived palette and layout coverage with common SaaS
component patterns. This supports template/common-pattern detection as a future
candidate, but current signals cannot distinguish "consistent and generic" from
"consistent and strategically familiar" without visual and category baselines.

## Quality Layers

### extraction_quality

Extraction quality answers: "Do we have enough captured evidence to inspect?"

Keep:

- `interpretation_status` as the first gate.
- `acquisition.errors` as a hard reason to exclude a payload from brand quality
  comparison.
- `extraction_confidence.factors` for diagnosing whether a payload has HTML,
  signal, and consistency coverage.
- `signal_coverage` for reviewer triage, as long as `not_interpretable`
  payloads are excluded from weak-brand interpretation.

Improve:

- Treat `screenshot_not_available` as a major limitation for visual
  interpretation, even when HTML coverage is high.
- Store richer acquisition metadata when available: final URL, status code,
  content formats returned, and whether HTML came from Firecrawl, static fetch,
  or browser fallback.
- Add an explicit capture mode such as `html_only`, `rendered_html`, or
  `screenshot_backed` so reviewers can quickly understand evidence depth.

Downgrade confidence:

- Any payload without screenshot should be capped for asset, logo prominence,
  image style, composition, and visual distinctiveness interpretation.
- Any payload with acquisition errors should be `not_interpretable`, even if a
  fallback produced partial HTML.

### signal_quality

Signal quality answers: "Are the extracted fields stable and useful?"

Safe to keep now:

- Color palette existence and rough palette complexity from HTML/CSS.
- Layout primitives: header, navigation, hero, section count, density, and
  broad layout patterns.
- Component presence and approximate component mix.
- Extraction limitations and weak-signal counts for calibration review.
- Consistency as an internal heuristic, not as a brand-quality conclusion.

Needs improvement:

- Typography parsing. Current captures often miss fonts or capture bad tokens
  such as escaped HTML fragments or CSS variable names.
- CTA extraction. Navigation, accessibility, product module labels, and utility
  actions are often mixed with real primary CTAs.
- Component taxonomy. Counts can be inflated by repeated cards, hidden modules,
  docs navigation, pricing fragments, and class-name heuristics.
- Logo detection. Missing logos for OpenAI, Allbirds, and Stripe Docs show that
  HTML-only detection is not reliable enough.
- Asset signals. All interpretable captures still show
  `screenshot_available=false`, so asset confidence stays weak.

Downgrade for now:

- Logo presence, logo location, and logo prominence.
- Asset mix and image count.
- Component counts as a proxy for sophistication.
- Palette role attribution such as background, text, or accent unless verified
  by screenshot.
- Consistency scores when typography or assets are missing.

### interpretation_quality

Interpretation quality answers: "Can this evidence support a brand judgment?"

Safe interpretation now:

- "This capture is inspectable" vs "not interpretable."
- "This site exposes enough HTML/CSS to extract palette/layout/components."
- "This payload has missing or weak evidence in typography, logo, assets, or
  screenshot-backed visual analysis."
- Category-relative calibration notes for human review.

Do not infer yet:

- Premium/luxury quality.
- Ecommerce merchandising strength.
- AI-native design distinctiveness.
- Weak/small-business visual quality.
- Template-like or generic brand expression.
- Overall brand design quality.

Requires screenshot or vision:

- Above-the-fold composition and hierarchy.
- True dominant colors and visible palette balance.
- Logo prominence, placement, scale, and contrast.
- Product photography, editorial art direction, illustration style, and stock
  imagery detection.
- Visual density as perceived by a user, not just DOM structure.
- Template-likeness, distinctiveness, polish, memorability, and category fit.

## First Keep/Improve/Downgrade Framework

| Signal | Decision | Reason |
| --- | --- | --- |
| `interpretation_status` | Keep | Correctly separates acquisition failures from low-confidence captures. |
| Acquisition errors | Keep | Hard exclusion gate for brand quality comparison. |
| Extraction confidence factors | Keep | Useful operational diagnostics. |
| Signal coverage | Keep | Good reviewer triage metric after excluding `not_interpretable`. |
| HTML/CSS color palette | Keep | Stable enough for palette availability and rough complexity. |
| Layout primitives | Keep | Useful, especially for SaaS, media, ecommerce, and docs surfaces. |
| Component presence | Keep | Useful for broad structural comparison. |
| Component counts | Improve | Counts are noisy and can be inflated by DOM repetition. |
| CTA labels | Improve | Need filtering for nav, accessibility, utility, and module labels. |
| Typography | Improve | Missing or noisy in most captures. |
| Logo signals | Downgrade | HTML-only detection misses obvious logos. |
| Asset signals | Downgrade | No screenshot-backed evidence in this batch. |
| Consistency | Downgrade | Useful as a heuristic, not a quality judgment. |
| Category interpretation | Future | Needs category baselines and human-reviewed calibration labels. |
| Visual distinctiveness | Future vision | Requires screenshot or multimodal analysis. |

## Next Calibration Step

Before Visual Signature influences any rubric:

1. Keep the module as evidence-only.
2. Add screenshot-backed acquisition or a separate vision adapter.
3. Re-run the same calibration set.
4. Compare `html_only` vs screenshot-backed outputs for the same brands.
5. Review whether typography, logo, asset, and composition signals become
   stable enough for interpretation.
