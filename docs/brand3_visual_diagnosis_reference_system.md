# Brand3 Visual Diagnosis Reference System

## Verdict

Brand3 should not try to make Visual Signature "better" as an isolated lab. The higher-value goal is to improve how the platform diagnoses a brand visually.

The right direction is a Brand3-owned Visual Diagnosis layer:

- uses screenshots and existing visual evidence;
- uses Visual Signature as one evidence source;
- borrows methods from external design-taste projects;
- produces explainable observations;
- does not change scoring until validated.

External projects such as `taste` and `impeccable` are useful references, but they should not become Brand3's source of truth. Their value is methodological: they show how to turn visual taste into reusable rules, anti-patterns, and review vocabulary.

## Problem

Today, Brand3 can score and explain `visual_identity`, but the visual diagnosis is not yet a first-class contract.

The current platform can answer parts of the question:

- whether screenshot capture succeeded;
- whether visual evidence is weak or unavailable;
- whether Magnetism coherence includes a `visual_identity` component;
- whether Visual Signature can extract visual signals in shadow mode.

But the platform does not yet have one canonical output that says:

- what was visually observed;
- how trustworthy the visual evidence is;
- whether the brand looks coherent, distinctive, generic, polished, or not evaluable;
- which visual anti-patterns support the diagnosis;
- whether the visual surface fits the brand promise and category.

That missing contract is the improvement opportunity.

## External References

### `jaytel0/taste`

Reference:

- <https://github.com/jaytel0/taste>

Useful idea:

`taste` treats design taste as something that can be distilled from references into reusable rules. The important pattern for Brand3 is not the generated skill file itself; it is the idea of converting visual references into explicit, inspectable criteria.

Potential Brand3 translation:

- reference profiles by category;
- observable style rules;
- visual vocabulary for density, rhythm, color, hierarchy, tone, polish, and composition;
- comparison between a captured brand surface and a reference profile.

Risk:

If copied directly, it could push Brand3 toward subjective "good taste" judgments. Brand3 should instead use it to support explainable pattern matching.

### `pbakaus/impeccable`

Reference:

- <https://github.com/pbakaus/impeccable>

Useful idea:

`impeccable` is more useful for operational diagnosis. It frames visual quality through review commands, domain references, deterministic anti-patterns, and LLM-assisted critique. That is close to what Brand3 needs: not just taste, but actionable visual QA vocabulary.

Potential Brand3 translation:

- detect common AI/SaaS generic patterns;
- identify weak hierarchy, bland cards, overused gradients, generic hero structures, poor contrast, weak CTA weight, and responsive fragility;
- separate polish issues from brand-fit issues;
- support a structured diagnosis rather than an aesthetic opinion.

Risk:

The repo is a reference for design review, not a Brand3 evidence model. We should not import its judgments wholesale.

### UI Critique and Benchmark References

Useful reference families:

- screenshot-based UI critique tools;
- UI design quality benchmarks;
- multimodal design critique datasets;
- human-reviewed critique corpora.

Examples already identified during research:

- UIClip: <https://uimodeling.github.io/uiclip/>
- UICrit: <https://people.eecs.berkeley.edu/~bjoern/papers/duan-uicrit-uist2024.pdf>
- Visual Prompting for Design Critique: <https://arxiv.org/abs/2404.12500>

Useful idea:

These references make one thing clear: visual diagnosis should be grounded in visible regions, evidence, and human-reviewable feedback. Multimodal models can help, but they should not be treated as final arbiters of visual quality.

Brand3 implication:

The LLM vision layer should support observations. It should not silently decide final score.

## Proposed Brand3 Layer

### Name

`VisualDiagnosis`

### Position

```text
Screenshot capture
        |
Visual evidence quality
        |
Visual Signature and heuristics
        |
Reference profile / anti-pattern matching
        |
VisualDiagnosis
        |
Magnetism explanation / report support
        |
Optional future scoring support
```

### Ownership

`VisualDiagnosis` should belong to Brand3/Magnetism, not to the Visual Signature lab.

Visual Signature remains an evidence provider. It can supply capture quality, obstruction state, palette, composition, layout, semantic visual notes, and extraction confidence. It should not own the platform's final visual diagnosis.

## Minimal Contract

Draft JSON shape:

```json
{
  "schema_version": "visual-diagnosis-v1",
  "status": "usable",
  "capture": {
    "available": true,
    "type": "viewport",
    "quality": "good",
    "obstruction": "none",
    "limitations": []
  },
  "diagnosis": {
    "identity_read": "coherent_but_generic",
    "reference_profile": "template_saas",
    "profile_confidence": "medium",
    "distinctiveness": "low",
    "polish": "medium",
    "brand_fit": "weak",
    "template_likeness": "high"
  },
  "signals": {
    "positive": [
      "consistent spacing",
      "clear primary CTA"
    ],
    "negative": [
      "generic abstract hero",
      "card-heavy composition",
      "low visual specificity"
    ],
    "antipatterns": [
      "template_saas_layout",
      "generic_ai_aesthetic"
    ]
  },
  "evidence_refs": [
    "raw_inputs:screenshot_capture",
    "raw_inputs:visual_signature"
  ],
  "confidence": "medium",
  "limitations": [
    "viewport-only capture"
  ]
}
```

## Reference Profiles

Initial profiles should be small and practical:

- `premium_luxury`
- `developer_first`
- `editorial_media`
- `ai_native`
- `template_saas`
- `wellness_lifestyle`
- `ecommerce_mass_market`
- `local_service`

Each profile should define observable signals, not taste adjectives.

### Example: `template_saas`

Observable signals:

- neutral background;
- localized saturated accent;
- generic abstract hero or dashboard mockup;
- rounded cards;
- repetitive feature grid;
- moderate typography contrast;
- strong internal consistency but low distinctiveness.

Possible diagnosis:

- coherent;
- polished enough;
- low originality;
- may weaken differentiated brand promises.

### Example: `premium_luxury`

Observable signals:

- strong whitespace control;
- restrained palette;
- high image specificity;
- editorial pacing;
- distinctive typography or art direction;
- fewer but more intentional UI elements.

Possible diagnosis:

- strong visual distinctiveness if execution supports brand category;
- weak fit if used by a utility SaaS without product clarity.

## Anti-pattern Families

The first useful anti-pattern set should be small:

- `generic_ai_aesthetic`
- `template_saas_layout`
- `card_heavy_composition`
- `low_distinctiveness_hero`
- `weak_cta_weight`
- `flat_typographic_hierarchy`
- `overused_gradient_palette`
- `poor_contrast_or_legibility`
- `visual_promise_mismatch`
- `capture_not_evaluable`

These should be evidence labels, not insults. They should explain why Brand3 has low confidence or why the visual identity appears generic.

## Diagnostic Language

Brand3 should avoid:

- "good taste";
- "bad design";
- "ugly";
- "premium" as a universal positive;
- "minimal" as a universal positive;
- ungrounded visual claims without screenshot or DOM evidence.

Brand3 should prefer:

- "coherent but generic";
- "visually distinctive";
- "polished but weakly differentiated";
- "not evaluable from available capture";
- "capture quality limits the visual diagnosis";
- "visual surface does not strongly support the stated promise";
- "identity system is consistent but resembles a common SaaS template pattern".

## Validation Plan

Before any scoring integration, run this as a comparison project.

### Candidate Brands

Use a small set:

- Netlify
- Sklum
- ElevenLabs
- LangChain
- Linear
- Allbirds
- The Verge
- one local service brand
- one generic ecommerce brand
- one visually strong premium/editorial brand

### For Each Brand

Collect:

- screenshot capture diagnostics;
- current Magnetism `visual_identity`;
- current coherence breakdown;
- Visual Signature shadow evidence if available;
- proposed `VisualDiagnosis`;
- one quick human judgment;
- latency and provider cost where multimodal calls are used.

### Promotion Criteria

The layer is useful only if it does at least one of these:

- separates weak visual identity from weak evidence;
- explains why visual identity is generic;
- catches capture failures before they degrade interpretation;
- improves consistency between local and deploy diagnosis;
- provides evidence-backed language for reports;
- reduces false visual conclusions in known cases.

## What Not To Do

- Do not import `taste` or `impeccable` as runtime dependencies.
- Do not let an LLM decide final visual quality alone.
- Do not connect the new layer to scoring by default.
- Do not refactor Visual Signature around this until the small contract proves useful.
- Do not turn Brand3 into a generic UI review tool.

## Next Implementation Step

Create a lab-only `visual_diagnosis` prototype:

1. Define `VisualDiagnosis` data model.
2. Add reference profiles as static JSON/YAML/Markdown.
3. Build a mapper from screenshot diagnostics + Visual Signature payload into diagnosis inputs.
4. Add an LLM prompt that reads only those inputs plus optional screenshot, returning the contract.
5. Run it on 10 brands.
6. Compare against current `visual_identity` and human notes.

Only after that should Brand3 decide whether this becomes:

- report explanation only;
- Scanner diagnostics only;
- shadow evidence;
- partial support for `visual_identity`;
- or parked as a lab artifact.

## Bottom Line

The opportunity is not Visual Signature itself. The opportunity is making Brand3's visual diagnosis more objective, explainable, and evidence-aware.

`taste` helps define reference profiles. `impeccable` helps define operational critique and anti-patterns. Visual Signature supplies evidence. Brand3 should own the final diagnostic contract.
