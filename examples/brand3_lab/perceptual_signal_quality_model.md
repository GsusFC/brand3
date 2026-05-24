# Brand3 Lab Perceptual Signal Quality Model

Generated: 2026-05-16
Status: concept specification
Scope: Brand3 Lab research only

## Principle

All brands deserve perceptual analysis.

Brand3 Lab should not decide whether a brand is eligible for perceptual reading with a yes/no gate. The system should classify the depth, specificity, and quality of the available perceptual signal.

The absence of rich signal is still a perceptual finding. A generic template, weak specificity, sparse proof, or incoherent surface can be read safely when the reading is framed as signal quality rather than brand failure.

## Non-Goals

- No runtime global enablement.
- No scoring changes.
- No report changes.
- No prompt changes.
- No renderer changes.
- No Visual Signature changes.
- No production rollout.

## Core Shift

Previous runtime planning used "high-signal" as an activation gate. For Brand3 Lab, that is too binary.

New model:

- Every analyzed brand receives a perceptual reading.
- Every reading receives a signal-depth classification.
- Thin, generic, weak, or negative readings remain valid.
- The system adapts the depth of interpretation to evidence quality.
- Low signal reduces interpretive reach; it does not remove the brand from analysis.

## Signal Depth Classes

### Rich Perceptual Signal

Definition:

The evidence contains repeated, concrete, surface-level mechanisms that can support a detailed perceptual reading.

Observable markers:

- multiple distinct surfaces or sections;
- repeated visual, structural, motion, copy, or interaction signals;
- clear hierarchy, rhythm, density, navigation, imagery, typography, product objects, proof modules, or system behavior;
- enough signal to identify patterns and tensions without importing assumptions.

Valid reading posture:

- name surface mechanisms;
- identify signal clusters;
- connect to perceptual patterns;
- name productive tensions;
- use medium-to-high confidence for observations;
- keep strategic intent conditional unless directly stated.

Example reading shape:

"Navigation, code content, and implementation paths make the category legible through use. The tension is how much complexity the surface can expose while still guiding action."

### Moderate Perceptual Signal

Definition:

The evidence contains some concrete mechanisms, but the reading depends on a limited surface area, source copy, or partial corroboration.

Observable markers:

- one or two useful surfaces;
- some concrete visual or structural details;
- source-stated claims with partial surface support;
- enough to describe direction, but not enough for broad pattern confidence.

Valid reading posture:

- describe observed signals;
- use conditional pattern language;
- keep claims copy-supported where needed;
- avoid broad brand conclusions;
- name missing evidence when it matters.

Example reading shape:

"Product-navigation language and compact UI claims point to guided movement, but interface clarity remains copy-supported until product-surface proof appears."

### Thin Perceptual Signal

Definition:

The evidence contains limited, sparse, or weakly corroborated surface material. A reading is still possible, but it should focus on limits, absences, and uncertainty.

Observable markers:

- one main source;
- thin homepage or basic profile;
- generic claims with little proof;
- few repeated signals;
- weak external corroboration;
- little visual or interaction evidence.

Valid reading posture:

- name the available signal;
- frame thinness as an evidence condition;
- avoid personality claims;
- avoid strategic failure claims;
- use low-to-medium confidence;
- keep the reading compact.

Example reading shape:

"The evidence pool is thin and mostly self-referential. Low specificity is visible; strategic failure is not."

### Absent Or Generic Signal

Definition:

The available evidence does not show enough distinctive surface behavior to support a specific perceptual pattern, or it shows mostly category-default language and layout.

Observable markers:

- generic hero promise;
- standard feature cards;
- abstract benefit copy;
- stock-like imagery;
- no distinctive proof modules;
- no repeated identity mechanism;
- no meaningful surface contrast.

Valid reading posture:

- identify genericity as surface behavior;
- avoid turning absence into failure;
- describe what is missing in signal terms;
- compare only when comparative evidence exists;
- use low confidence for interpretation and high confidence for the absence itself.

Example reading shape:

"The surface repeats standard SaaS moves: broad hero promise, feature-card grid, and low proof density. That supports a template-like surface reading, not a conclusion about product value."

## Negative Perceptual Reading

Definition:

A reading that identifies harmful, incoherent, overloaded, misleading, generic, inaccessible, or low-specificity surface behavior without turning it into a moral or business verdict.

Negative perceptual readings are valid when they are evidence-bound.

Valid negative signals:

- claim/signal mismatch;
- dense surface without guidance;
- low specificity;
- generic template behavior;
- inaccessible or confusing hierarchy;
- proof claims without proof structure;
- surface contradiction;
- excessive abstraction;
- category confusion;
- weak corroboration;
- self-description with no external support.

Invalid negative claims:

- "the strategy failed";
- "the audience does not care";
- "the brand is irrelevant";
- "the company lacks ambition";
- "the product is bad";
- "the business is weak";
- "the team does not understand the market."

Safe negative reading shape:

"The surface shows low specificity and weak corroboration. That limits how much Brand3 can infer about differentiation; it does not prove strategic failure."

## Template-Like Surface

Definition:

A surface that relies on common category patterns without enough specific language, proof, structure, or visual behavior to distinguish the brand.

Observable markers:

- interchangeable SaaS or service copy;
- generic "all-in-one", "simple", "powerful", "modern" claims;
- feature-card grid without proof hierarchy;
- stock or abstract imagery;
- default hero/CTA/testimonial layout;
- category language that could fit many competitors.

Valid reading posture:

- name template behavior directly;
- identify missing specificity;
- avoid inferring product quality;
- avoid mocking or punitive tone;
- ask what proof or specificity would make the surface more legible.

Example:

"The page uses a familiar hero, feature-card grid, and broad benefit copy. The template behavior is visible; product weakness is not."

## Low Specificity Surface

Definition:

A surface that does not provide enough distinctive details to make the brand, offer, audience, proof, or category behavior legible.

Observable markers:

- claims without concrete nouns;
- few named use cases;
- vague value proposition;
- absent proof examples;
- interchangeable adjectives;
- unclear audience or product object;
- broad category promises without operating detail.

Valid reading posture:

- separate low specificity from low quality;
- identify which specificity is missing;
- keep interpretation bounded;
- avoid extrapolating to business performance.

Example:

"The surface gives broad benefit language but few concrete use cases or proof examples. The perceptual issue is low specificity, not evidence of low product value."

## Lab Classification Model

Every Brand3 Lab perceptual reading should include:

- `signal_depth`: rich, moderate, thin, absent_or_generic;
- `signal_quality`: distinctive, mixed, generic, low_specificity, contradictory, obstructed;
- `reading_valence`: positive, mixed, negative, diagnostic, insufficient_for_strategy;
- `interpretive_reach`: full_pattern_reading, bounded_pattern_reading, limitation_reading, absence_reading;
- `confidence`: high, medium, low;
- `required_caution`: none, source_boundary, explicit_low_confidence, human_review;
- `safe_output_mode`: compressed_perceptual, raw_perceptual_with_caution, baseline_summary, lab_only_review.

## Reading Modes By Signal Depth

| Signal depth | Reading mode | Interpretation allowed | Caution |
| --- | --- | --- | --- |
| Rich | full perceptual reading | patterns, tensions, emotional temperature | normal evidence boundaries |
| Moderate | bounded perceptual reading | limited patterns and tensions | source/status boundaries |
| Thin | limitation reading | evidence limits, low specificity, weak corroboration | explicit low-confidence |
| Absent/generic | absence or template reading | genericity, missing specificity, template behavior | no strategic verdict |

## Implications For Runtime Planning

The lab concept should not use "eligible" as the main concept.

Better terms:

- depth;
- signal quality;
- interpretive reach;
- safe output mode;
- caution requirement.

For production runtime, high-signal gating may still be useful as a safety mechanism for compressed automated prose. But Brand3 Lab should show all readings, including weak, generic, thin, and negative ones, with the correct label.

## What Stays Baseline-Only

- Scores.
- Dimension verdicts.
- Global report synthesis.
- Production report rendering.
- Any claim that would require strategic, financial, legal, health, trust, or user outcome evidence.

## What Stays Lab-Only

- Negative perceptual reading experiments.
- Thin-signal or absence readings before calibration.
- Reviewer disagreement around weak/generic cases.
- Unsafe or rejected compressed outputs.
- Any reading requiring human review.

## What Should Never Become Automatic

- Equating generic surface with business failure.
- Equating low specificity with low quality.
- Inferring strategic intent from thin evidence.
- Inferring audience irrelevance.
- Inferring product value from template behavior.
- Inferring user emotional outcomes from tone alone.
- Treating absence of evidence as evidence of absence outside the surface.

## Final Principle

Brand3 Lab should become better at reading every kind of brand surface, not only strong ones.

Rich brands get pattern readings. Moderate brands get bounded readings. Thin brands get limitation readings. Generic brands get template readings. Weak brands get negative or absence readings when evidence supports them.

The value is not deciding who qualifies. The value is naming what kind of perceptual truth the evidence can safely support.
