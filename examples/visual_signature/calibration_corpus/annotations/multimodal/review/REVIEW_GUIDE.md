# Visual Signature Annotation Review Guide

This guide is for offline calibration of Visual Signature multimodal annotations.
Reviews are evidence-only. They do not affect Brand3 scoring, rubric dimensions,
production reports, or UI.

## Review Scope

Review only what is supported by the saved annotation overlay and screenshot
evidence. Prefer the viewport screenshot when judging first-impression behavior.
Use full-page evidence only when it is explicitly part of the annotation source.

For every target, reviewers should decide:

- `agree`: the label is supported by visible evidence.
- `disagree`: the label is wrong or contradicted by visible evidence.
- `uncertain`: evidence is ambiguous, cropped, blocked, too generic, or too weak.
- `not_applicable`: the target cannot reasonably be evaluated for this capture.

Usefulness is scored from `1` to `5`:

- `1`: not useful; misleading, unsupported, or too vague.
- `2`: weak; some signal exists but not reliable enough for calibration.
- `3`: usable but limited.
- `4`: useful and reasonably clear.
- `5`: highly useful; clear, specific, and well-supported.

## Global Definitions

`useful` means the annotation helps a reviewer understand the visual system and
is tied to visible evidence.

`uncertain` means the reviewer cannot confidently verify the annotation from the
available screenshot or payload.

`hallucinated` means the annotation claims something not visible, not supported,
or contradicted by the screenshot. Mark `hallucination=true` even if the label
sounds plausible for the brand.

`unsupported by screenshot` means the annotation may be true elsewhere, but it is
not visible in the supplied evidence.

`wrong label` means a better label is clearly available from the evidence. Add
`corrected_label` when possible.

## Target Criteria

### logo_prominence

Evaluate whether a logo or brand mark is visible and how strongly it appears in
the viewport.

Useful labels are supported by visible logo placement, scale, and clarity.
Mark uncertain if the logo is tiny, cropped, hidden by a modal, or replaced by
text that may not be a brand mark.
Mark hallucinated if the annotation claims a logo is dominant when no logo is
visible.

Acceptable notes:

- `Header wordmark is visible but small relative to the hero.`
- `No clear logo in the viewport; only product text is visible.`
- `Label says dominant, but the logo is a small nav element.`

### imagery_style

Evaluate the dominant visible image style: photography, illustration, UI
screenshots, product renders, editorial imagery, abstract graphics, or minimal/no
imagery.

Useful labels should describe the visible style, not the presumed brand style.
Mark uncertain when the screenshot is text-heavy or imagery is below the fold.
Mark hallucinated if the annotation mentions humans, products, or illustrations
that are not visible.

Acceptable notes:

- `Viewport is mostly UI screenshots, not lifestyle photography.`
- `Hero uses editorial photography with large image treatment.`
- `No meaningful imagery visible above the fold.`

### product_presence

Evaluate whether the actual product, service interface, packaging, physical
object, or offer is visible.

Useful labels distinguish visible product from implied product. For SaaS, UI
screenshots can count as product presence. For ecommerce, product photography or
product cards count. For service businesses, booking widgets or service lists may
count as service presence.

Mark hallucinated when the annotation claims product visibility but the viewport
only shows abstract copy or generic imagery.

Acceptable notes:

- `Dashboard UI is visible in the hero, so product presence is clear.`
- `Lifestyle image appears, but no product is visible.`
- `Service offering is visible through booking CTA and service list.`

### human_presence

Evaluate whether people are visibly present in the screenshot.

Use visible human bodies, faces, silhouettes, portraits, or lifestyle scenes.
Do not infer human presence from testimonials, avatars, names, or text.
Mark hallucinated if the annotation claims people are present but only text,
icons, or illustrations are shown.

Acceptable notes:

- `No people visible in viewport.`
- `Hero image includes multiple visible people.`
- `Small avatar icons are present, but not enough for strong human presence.`

### template_likeness

Evaluate whether the page visually resembles a common template pattern.

Useful evidence includes generic SaaS hero layout, repeated cards, stock-like
module rhythm, predictable CTA/social-proof blocks, or undifferentiated section
structure. Do not mark a page template-like only because it is clean or uses
cards.

Mark uncertain when the page is too sparse to judge or when only one viewport is
available.

Acceptable notes:

- `Generic centered SaaS hero with repeated logo strip and feature cards.`
- `Layout is common, but visual treatment has distinctive art direction.`
- `Only a sparse first fold is visible; template-likeness is uncertain.`

### visual_distinctiveness

Evaluate whether the visible system has memorable, ownable visual traits.

Useful evidence includes distinctive typography, art direction, layout rhythm,
color behavior, motion stills, product presentation, or visual metaphor. Avoid
judging brand quality or strategy.

Mark hallucinated if the annotation claims distinctiveness without naming a
visible trait.

Acceptable notes:

- `Distinctive color blocking and editorial image crop create a recognizable look.`
- `Visuals are competent but generic; no specific distinctive trait is visible.`
- `Annotation says distinctive but evidence only cites clean layout.`

### category_fit

Evaluate whether the visible presentation fits the expected category.

Use the provided `expected_category` and visible evidence. Category fit is not a
quality score. A brand can fit its category and still be visually generic.
Mark uncertain if the category itself seems mixed or the viewport lacks enough
context.

Acceptable notes:

- `Dense editorial grid fits editorial_media.`
- `Sparse luxury-style product presentation fits premium_luxury.`
- `Category fit is uncertain because the viewport does not show the offer.`

### perceived_polish

Evaluate visible execution quality: alignment, hierarchy, clarity, image quality,
spacing, consistency, and apparent finish.

Do not equate polish with luxury, minimalism, or high brand fame. A practical
local-service site can be polished for its category.
Mark hallucinated if polish is asserted while the screenshot is blank, broken, or
visibly low-quality.

Acceptable notes:

- `Typography and spacing are consistent; polish reads medium-high.`
- `Screenshot has broken/cropped layout, so polish cannot be confirmed.`
- `Useful label, but confidence should be lower due to modal overlay.`

### category_cues

Evaluate whether visible cues support the expected category: product visuals,
language, layout patterns, iconography, domain-specific modules, or offer
structure.

Do not rely on prior brand knowledge. Use only visible screenshot/payload
evidence.
Mark hallucinated when cues are named but not visible.

Acceptable notes:

- `Pricing CTA and dashboard image support SaaS cues.`
- `Course cards and institutional copy support education cues.`
- `No visible category cues beyond the brand name.`

## Reviewer Notes

Good notes are short, concrete, and evidence-based.

Acceptable:

- `Label should be "unclear"; viewport shows copy and CTA but no product.`
- `Evidence cites photography, but screenshot is mostly UI chrome.`
- `Agree, but usefulness is 3 because the target is generic.`
- `Hallucination: annotation mentions people; no people are visible.`
- `Corrected label: subtle. Logo appears only as a small header wordmark.`

Avoid:

- `Bad brand.`
- `Looks nice.`
- `I know this company is premium.`
- `Probably true from other pages.`
- `This should improve the score.`

## Review Boundary

Human review outputs are calibration artifacts. They may be used to improve
annotation prompts, provider normalization, target definitions, and corpus
sampling. They must not be wired into scoring, rubric dimensions, production
reports, or UI without a separate reviewed implementation phase.
