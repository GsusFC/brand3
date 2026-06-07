# Visual Diagnosis Reference Profiles

## Purpose

This document defines Brand3-owned reference profiles and visual anti-patterns for lab-only visual diagnosis.

These profiles are not aesthetic preferences. They are observable comparison frames for interpreting screenshots, Visual Signature evidence, and Magnetism visual diagnostics.

External references:

- `jaytel0/taste`: useful for converting visual references into reusable design rules.
- `pbakaus/impeccable`: useful for operational review vocabulary and deterministic anti-patterns.

Brand3 does not import either project as runtime dependency. The references inform this taxonomy only.

## Diagnostic Principles

- Diagnose evidence, not taste.
- Separate visual weakness from evidence weakness.
- Prefer "not evaluable" over unsupported inference.
- Explain category fit, not universal beauty.
- Treat LLM vision as support, not final authority.
- Keep scoring integration blocked until lab validation proves value.

## Reference Profiles

### `template_saas`

Typical observable signals:

- neutral or very light background;
- one saturated accent color;
- rounded cards or feature tiles;
- repeated three-column or bento-like sections;
- abstract hero artwork, dashboard mockup, or gradient panel;
- moderate typographic contrast;
- consistent spacing with low visual specificity;
- generic product/value language visually supported by generic components.

Positive signals:

- clear structure;
- predictable navigation;
- readable hierarchy;
- low interaction ambiguity.

Risk signals:

- low distinctiveness;
- interchangeable hero;
- card-heavy composition;
- visual polish without brand specificity;
- weak support for a differentiated promise.

Common diagnosis:

- `coherent_but_generic`
- `polished_but_undifferentiated`

### `premium_luxury`

Typical observable signals:

- restrained palette;
- high whitespace control;
- strong editorial pacing;
- high-quality product or lifestyle imagery;
- distinctive typography or art direction;
- fewer UI elements;
- deliberate asymmetry or cinematic composition.

Positive signals:

- strong distinctiveness;
- high polish;
- visual restraint feels intentional;
- product or brand object is visually central.

Risk signals:

- low product clarity;
- beauty without proof;
- excessive opacity;
- category mismatch for functional products.

Common diagnosis:

- `visually_distinctive`
- `high_polish_with_category_risk`

### `developer_first`

Typical observable signals:

- dense but controlled information;
- code snippets, docs, terminal motifs, or technical diagrams;
- high contrast between text blocks and actions;
- utility-first navigation;
- restrained decorative system;
- clear product surface or API proof.

Positive signals:

- clear technical orientation;
- fast comprehension for technical buyers;
- strong trust through specificity.

Risk signals:

- too much density;
- weak emotional memory;
- generic dark terminal aesthetic;
- unclear non-technical value.

Common diagnosis:

- `functionally_clear`
- `technical_but_visually_generic`

### `editorial_media`

Typical observable signals:

- strong typographic hierarchy;
- article or story-led composition;
- image/editorial rhythm;
- visible content density;
- contrast between headlines, metadata, and body modules;
- less reliance on CTA-heavy product blocks.

Positive signals:

- strong information hierarchy;
- content credibility;
- recognisable editorial voice.

Risk signals:

- clutter;
- ad-heavy visual disruption;
- weak brand distinctiveness if relying only on layout convention.

Common diagnosis:

- `editorially_coherent`
- `content_rich_but_visually_noisy`

### `ai_native`

Typical observable signals:

- abstract intelligence metaphors;
- dark or high-contrast palette;
- gradients, glow, glass, mesh, or spatial depth;
- prompt/chat/demo surfaces;
- future-facing typography or interaction language;
- strong claim density around capability.

Positive signals:

- clear category signaling;
- product demo can make abstract AI concrete;
- strong novelty if visual system is specific.

Risk signals:

- generic AI aesthetic;
- purple/blue gradient dependence;
- abstract visuals not tied to product proof;
- high polish with low trust specificity.

Common diagnosis:

- `category_aligned_but_generic`
- `abstract_promise_weak_visual_proof`

### `wellness_lifestyle`

Typical observable signals:

- warm or calm palette;
- lifestyle photography;
- soft spacing and rounded forms;
- human body, routine, wellbeing, or environment cues;
- lighter density;
- emotionally supportive copy and visual tone.

Positive signals:

- clear mood;
- approachable tone;
- strong sensory consistency.

Risk signals:

- category sameness;
- generic calm aesthetic;
- low evidence of product differentiation.

Common diagnosis:

- `emotionally_coherent`
- `calm_but_undifferentiated`

### `ecommerce_mass_market`

Typical observable signals:

- product grid or commerce modules;
- promotional banners;
- visible pricing, offer, cart, or category navigation;
- strong image/product density;
- conversion-oriented hierarchy.

Positive signals:

- product clarity;
- shopping intent is easy to understand;
- offers and CTAs are visible.

Risk signals:

- banner clutter;
- low brand memory;
- over-reliance on discount signals;
- product imagery inconsistent with stated positioning.

Common diagnosis:

- `commerce_clear`
- `conversion_heavy_low_brand_signal`

### `local_service`

Typical observable signals:

- service area, phone, booking, quote, or contact CTA;
- trust badges, reviews, or before/after imagery;
- practical service photography or stock imagery;
- simpler typography and layout;
- high emphasis on immediate action.

Positive signals:

- clear service;
- clear conversion path;
- trust evidence visible.

Risk signals:

- stock-like imagery;
- dated or template-heavy execution;
- weak differentiation from local competitors.

Common diagnosis:

- `practical_but_generic`
- `clear_service_low_visual_distinctiveness`

## Anti-patterns

### `generic_ai_aesthetic`

Signals:

- purple/blue gradients;
- abstract glowing shapes;
- glass panels;
- vague intelligence motifs;
- no visible product proof.

Diagnostic meaning:

The page signals "AI" but does not provide visual specificity or category differentiation.

### `template_saas_layout`

Signals:

- predictable hero + logo row + feature cards + testimonial + pricing pattern;
- generic dashboard mockup;
- limited unique imagery or interaction.

Diagnostic meaning:

The page is coherent but may be visually interchangeable.

### `card_heavy_composition`

Signals:

- repeated card blocks dominate the viewport;
- nested panels;
- uniform radius/shadow treatment;
- little editorial rhythm.

Diagnostic meaning:

The visual system may be organized but lacks hierarchy and memorability.

### `low_distinctiveness_hero`

Signals:

- hero could belong to many competitors;
- weak brand object/product visibility;
- generic headline support visuals;
- no unique composition.

Diagnostic meaning:

The first impression does not create strong brand memory.

### `weak_cta_weight`

Signals:

- primary action lacks contrast or prominence;
- many competing actions;
- CTA visually disconnected from value proposition.

Diagnostic meaning:

Visual hierarchy may weaken conversion clarity.

### `flat_typographic_hierarchy`

Signals:

- headings, body, labels, and buttons have similar scale/weight;
- no clear focal point;
- dense text without editorial structure.

Diagnostic meaning:

The page may be readable but visually hard to scan.

### `overused_gradient_palette`

Signals:

- gradient carries most of the brand feeling;
- palette resembles common AI/SaaS defaults;
- weak supporting typography/image system.

Diagnostic meaning:

The color system may feel polished but not ownable.

### `poor_contrast_or_legibility`

Signals:

- text blends into background;
- low contrast on CTAs;
- small type over imagery;
- decorative effects reduce readability.

Diagnostic meaning:

Visual polish may reduce usability and evidence confidence.

### `visual_promise_mismatch`

Signals:

- promise suggests premium, trust, speed, craft, intelligence, or simplicity;
- visual surface suggests a conflicting pattern;
- category expectations are not supported by the captured surface.

Diagnostic meaning:

The brand message and visual system are not reinforcing each other.

### `capture_not_evaluable`

Signals:

- screenshot missing;
- screenshot blank or low detail;
- viewport blocked by modal/login/paywall;
- only irrelevant section captured.

Diagnostic meaning:

Brand3 should not diagnose visual identity as weak. It should diagnose evidence quality as insufficient.

## Output Language

Preferred labels:

- `visually_distinctive`
- `coherent_but_generic`
- `polished_but_undifferentiated`
- `functionally_clear`
- `editorially_coherent`
- `emotionally_coherent`
- `commerce_clear`
- `practical_but_generic`
- `not_evaluable`

Avoid:

- `good taste`
- `bad taste`
- `ugly`
- `premium` as universal praise
- unsupported claims about intent

## Lab Validation Requirement

A profile or anti-pattern is useful only if it improves at least one of:

- separates poor evidence from poor identity;
- improves explanation of current `visual_identity`;
- reduces false visual conclusions;
- produces reviewable evidence references;
- holds up across at least 10 real brands.
