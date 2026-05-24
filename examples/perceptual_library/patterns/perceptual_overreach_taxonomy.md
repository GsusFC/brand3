# Brand3 Perceptual Overreach Taxonomy

Generated: 2026-05-15
Status: draft taxonomy
Scope: perceptual narrative augmentation only

## Purpose

This taxonomy formalizes the failure modes discovered during the perceptual narrative evaluation pass.

It is documentation only. It does not change scoring, prompts, report rendering, runtime behavior, Visual Signature, schemas, or case records.

The goal is to protect Brand3 from turning perceptual reasoning into decorative interpretation. A valid perceptual reading moves from observable signal to cluster, pattern, tension, emotional temperature, and narrative implication. Overreach happens when one of those steps is skipped or inflated.

## Core Rule

The strongest Brand3 reading is the most precise interpretation the evidence can support.

Do not reward dramatic prose. Reward bounded prose:

- observation before interpretation
- direct evidence before pattern language
- confidence before implication
- tension before recommendation
- limitation before polish

## Failure Modes

### 1. Invented Intentionality

**Definition:** Assigning motive, strategy, audience intent, or business objective to the brand without direct evidence.

**Examples:**

- "The brand seeks cultural authority."
- "The company is targeting sophisticated enterprise buyers."
- "The surface is designed to make users feel safe."

**Why it happens:** Perceptual language invites causal explanation. Writers see a surface pattern and fill in the internal strategy that would make the pattern make sense.

**Observable warning signs:**

- verbs like seeks, intends, aims, wants, designed to, built to
- audience claims without source support
- strategic conclusions attached to aesthetic signals
- "because" clauses that explain internal motivation

**Mitigation strategies:**

- Replace intention with supported reading: "supports a reading of..."
- Name the evidence type: direct, copy-based, inferred, weak inference.
- Add "internal intent is not observable from outside" when needed.
- Require human review for unstated strategic intent.

**Confidence rules:**

- High only when intent is directly stated by the brand or source.
- Medium when repeated source language consistently frames intent but product behavior is not visible.
- Low when intent is inferred from aesthetics, tone, layout, or category alone.

**Acceptable form:** "The owned copy frames the product as a system for enterprise workflow, which may support a reading of operational ambition."

**Unacceptable form:** "The brand is pursuing enterprise authority."

### 2. Unsupported Emotional Projection

**Definition:** Claiming a felt emotional state without tying it to observable mechanisms.

**Examples:**

- "The brand feels reassuring."
- "The experience is calming and supportive."
- "The interface creates trust."

**Why it happens:** Emotional temperature is useful, but mood words are easy to write without evidence. Wellness, finance, and premium consumer brands are especially vulnerable.

**Observable warning signs:**

- calm, warm, reassuring, supportive, trustworthy, inviting, human, confident
- no reference to color, pacing, hierarchy, density, typography, motion, illustration, or copy
- emotional outcome phrased as user effect

**Mitigation strategies:**

- Tie emotional temperature to mechanisms.
- Keep user impact conditional.
- Avoid therapeutic, psychological, or trust claims unless evidence supports them.

**Confidence rules:**

- High when repeated visible mechanisms converge.
- Medium when surface signals and copy tone align.
- Low when emotion comes from category expectation or brand reputation.

**Acceptable form:** "Soft color, low-density hierarchy, and friendly illustration can support a low-to-medium confidence reading of calm accessibility."

**Unacceptable form:** "The brand makes users feel supported."

### 3. Cinematic Inflation

**Definition:** Overusing cinematic or motion language when motion is absent, copy-only, or not concept-bearing.

**Examples:**

- "The brand creates a cinematic journey."
- "The experience has filmic momentum."
- "The motion system expresses transformation."

**Why it happens:** The registry contains motion-oriented patterns such as Guided Movement, Concept-Bearing Motion, and Threshold Pacing. Those patterns can become decorative if applied to static surfaces.

**Observable warning signs:**

- cinematic, immersive, filmic, kinetic, choreographed, journey
- no captured motion, sequence, transition, or interaction evidence
- production terms treated as perceptual effects

**Mitigation strategies:**

- Separate motion claim from motion observation.
- Use "copy states" when motion is source-described but not captured.
- Require capture, video, or sequential evidence before high confidence.

**Confidence rules:**

- High with direct motion evidence and clear concept linkage.
- Medium with source-stated motion and some supporting still-sequence evidence.
- Low when inferred from static aesthetics or production language alone.

**Acceptable form:** "The case copy names Datamosh transitions, but concept-bearing motion remains unverified until motion evidence is reviewed."

**Unacceptable form:** "The brand uses cinematic motion to symbolize disruption."

### 4. False Sophistication Language

**Definition:** Using prestige-coded adjectives as if they were analysis.

**Examples:**

- "The brand is sophisticated."
- "The visual identity is premium and polished."
- "The system is elegant, modern, and refined."

**Why it happens:** Baseline LLM prose often defaults to generic quality language when evidence is thin. Perceptual augmentation can reduce this, but can also replace old generic language with new pseudo-premium vocabulary.

**Observable warning signs:**

- sophisticated, premium, elegant, refined, polished, elevated, world-class
- adjectives not followed by observable mechanism
- quality words standing where pattern behavior should be

**Mitigation strategies:**

- Replace quality labels with surface behavior.
- Ban prestige adjectives unless quoted or directly evidenced.
- Ask what changed on the surface: density, hierarchy, pacing, material, contrast, repetition, modularity.

**Confidence rules:**

- Prestige labels should almost never be high-confidence observations.
- Treat as low-confidence interpretation unless directly quoted from source.
- Prefer no confidence assignment and rewrite as mechanism.

**Acceptable form:** "The surface uses restrained spacing, product-scale imagery, and short declarative copy."

**Unacceptable form:** "The brand feels premium and sophisticated."

### 5. Weak Evidence Amplification

**Definition:** Making sparse, copy-only, obstructed, or single-source evidence sound more conclusive than it is.

**Examples:**

- "The interface is intuitive" based on a source claim.
- "The system is scalable" based on case-study copy.
- "The brand lacks differentiation" based only on missing evidence.

**Why it happens:** The narrative layer tries to be useful even when evidence is thin. Without strict confidence handling, weak evidence becomes a confident finding.

**Observable warning signs:**

- single URL drives broad conclusion
- copy claims become product behavior
- absence becomes defect
- obstruction or missing capture disappears from prose

**Mitigation strategies:**

- Name evidence limits inside the observation.
- Convert conclusions into limitations or review questions.
- Keep copy-based material at medium or low confidence.
- Do not infer failure from missing evidence.

**Confidence rules:**

- High only with direct or corroborated evidence.
- Medium for copy-based claims stated clearly as copy.
- Low for absent, obstructed, or inferred signals.

**Acceptable form:** "The source states a seamless interface, but current evidence only supports a copy-level guidance claim."

**Unacceptable form:** "The product offers a seamless interface."

### 6. Aesthetic Hallucination

**Definition:** Inventing visual details that are not present in the evidence pool.

**Examples:**

- "Soft gradients and rounded modules" when no capture exists.
- "Dense navigation and code panels" when only homepage copy was reviewed.
- "Large serif typography" copied from another case.

**Why it happens:** Static perceptual hints include surface signals from prior cases. If treated as target-brand facts, they contaminate the current finding.

**Observable warning signs:**

- visual details not found in screenshots, HTML, or source text
- FLOC* case-specific signals appear in unrelated brand analysis
- pattern examples leak into target observations

**Mitigation strategies:**

- Treat adapter hints as lenses only, never target facts.
- Require every visual detail to map to evidence.
- Do not mention Charms, D4DATA, Grandvalira, or their motifs unless in the evidence pool.

**Confidence rules:**

- High only for directly visible or directly extracted signals.
- Medium for source-stated visual claims.
- Low or invalid for visual details imported from registry examples.

**Acceptable form:** "If similar repeated forms appear in the target evidence, they may support a motif-control reading."

**Unacceptable form:** "The brand uses soft light fields and ritual pacing" when those signals come only from Charms.

### 7. Narrative Over-Binding

**Definition:** Forcing multiple signals into a single coherent story when the evidence supports only partial or divergent readings.

**Examples:**

- "Every surface reinforces the same strategic narrative."
- "The ecosystem resolves complexity through a unified grammar."
- "All channels converge around trust and speed."

**Why it happens:** Reports prefer coherent stories. Perceptual reasoning introduces reusable patterns that can make fragmented evidence feel artificially integrated.

**Observable warning signs:**

- all, every, fully, resolves, unified, converges
- no acknowledgement of divergent channels
- contradiction smoothed into coherence
- pattern names used to close uncertainty

**Mitigation strategies:**

- Preserve partiality.
- Name channel divergence when present.
- Use "one available reading" instead of "the story".
- Keep contradictions unresolved when evidence is unresolved.

**Confidence rules:**

- High only when multiple independent anchors support the same reading.
- Medium when two or more signals converge but source diversity is limited.
- Low when the story is assembled from scattered or weak signals.

**Acceptable form:** "Several owned-surface signals point toward operational clarity, while external corroboration remains limited."

**Unacceptable form:** "The brand coherently expresses operational clarity across the ecosystem."

### 8. Perception Without Observable Grounding

**Definition:** Applying perceptual pattern language without naming the signal that supports it.

**Examples:**

- "This is category-to-surface translation."
- "The brand uses guided movement."
- "The emotional temperature is controlled."

**Why it happens:** Registry vocabulary can become shorthand. Shorthand is useful internally but unsafe in report prose unless anchored.

**Observable warning signs:**

- pattern label appears without evidence
- emotional temperature appears before observation
- no quote, source, surface, channel, visual signal, or structural mechanism

**Mitigation strategies:**

- Every pattern sentence must include at least one surface mechanism.
- Pattern labels should follow observations, not replace them.
- If no mechanism can be named, do not use the pattern.

**Confidence rules:**

- High when signal, cluster, and pattern are all present.
- Medium when signal exists but cluster is partial.
- Low when pattern is plausible but only one weak signal exists.

**Acceptable form:** "Navigation density, code-oriented content, and implementation pathways support a category-to-surface reading."

**Unacceptable form:** "This is category-to-surface translation."

### 9. Tension Fabrication

**Definition:** Inventing a contradiction or tradeoff because the report expects one.

**Examples:**

- "The brand balances accessibility and authority" with no evidence for either side.
- "There is a tension between calm and conversion" without conversion evidence.
- "Minimalism conflicts with density" when only one surface was reviewed.

**Why it happens:** Tension improves narrative quality, but not every evidence pool contains a real tension.

**Observable warning signs:**

- "between X and Y" where X or Y has no evidence
- tension language appears in every dimension
- tension is generic enough to fit any brand
- no contradiction, absence, mismatch, or tradeoff is named

**Mitigation strategies:**

- Require evidence for both sides.
- Use "no stable tension identified" when needed.
- Treat claim/evidence gaps as unverified, not automatically defects.

**Confidence rules:**

- High when both sides are directly evidenced.
- Medium when one side is direct and one side is copy-based.
- Low when one side is inferred or absent.

**Acceptable form:** "The source claims modularity, but available evidence supports repeated motif control more clearly than component behavior."

**Unacceptable form:** "The brand balances modularity and emotion" without evidence for both.

### 10. Generic Premium Projection

**Definition:** Reading premium status into restraint, minimalism, whitespace, or monochrome surfaces without evidence.

**Examples:**

- "The restrained layout signals premium positioning."
- "Minimalism makes the product feel luxury."
- "Whitespace creates a high-end perception."

**Why it happens:** Premium is often used as a shortcut for restraint. Brand3 must separate surface restraint from market position, price tier, or cultural status.

**Observable warning signs:**

- premium, luxury, high-end, elevated attached to whitespace or restraint
- market tier inferred from aesthetics
- no pricing, audience, product, or third-party evidence

**Mitigation strategies:**

- Replace premium with observable restraint.
- If market position matters, require separate evidence.
- Treat premium as interpretation, never direct visual fact.

**Confidence rules:**

- High only when premium positioning is explicitly stated or externally corroborated.
- Medium when surface restraint aligns with product/category evidence.
- Low when inferred from visual restraint alone.

**Acceptable form:** "The surface is restrained: sparse copy, high whitespace, and controlled product imagery."

**Unacceptable form:** "The brand reads as premium because it is restrained."

## Safe Perceptual Augmentation Zones

Perceptual augmentation is safest when:

- the evidence pool includes direct screenshots, source quotes, HTML structure, or repeated visual signals
- the finding names a concrete surface mechanism
- the interpretation is conditional
- the prose separates claim, observation, implication, and limitation
- pattern vocabulary follows evidence
- contradiction is recorded as claim/signal, not defect
- emotional temperature is tied to pacing, density, hierarchy, color, motion, or interaction
- weak evidence is written as a limitation or review question

Safe examples:

- "The owned page repeats short declarative product copy and product-scale imagery, which may support a product-first hierarchy reading."
- "The case copy states seamless guidance, but current evidence does not verify the interface behavior."
- "The surface is low-density and soft-toned; any claim about user reassurance remains interpretive."

## High-Risk Narrative Zones

Perceptual augmentation is high-risk when:

- the evidence pool is copy-only
- screenshots are unavailable, obstructed, or stale
- a famous brand's reputation is likely to fill evidence gaps
- the category carries strong emotional assumptions, such as wellness, finance, AI, or luxury
- the brand has sparse or generic evidence
- the finding uses pattern names without mechanisms
- the writer reaches for authority, trust, support, sophistication, leadership, or premium status
- the report expects a tension but the evidence does not contain one
- motion, cinematic, or interface claims are source-stated but not captured

High-risk examples:

- "The product is intuitive" from homepage copy.
- "The brand builds trust" from clean typography.
- "The system is scalable" from a design-system claim without component evidence.
- "The experience is cinematic" from static imagery.

## Dimensions Most Vulnerable To Overreach

### Percepcion

Most vulnerable to invented audience readings, trust claims, authority claims, and emotional projection. Perception findings often drift from "how the brand is described" into "what the market believes".

Control: require source type and corroboration status.

### Diferenciacion

Most vulnerable to false uniqueness, leadership language, and unsupported category distinction. Differentiation invites claims that something is distinctive before alternatives are evidenced.

Control: require comparison anchor or state that comparison is unavailable.

### Vitalidad

Most vulnerable to cinematic inflation, momentum claims, and unsupported community or cultural energy. Motion and activity can be inferred too easily from category language.

Control: require timestamped activity, motion evidence, or channel behavior.

### Presencia

Most vulnerable to weak evidence amplification. Thin public presence can become a verdict about strategy, maturity, or market traction.

Control: treat absence as evidence limitation unless the absence itself is measured and relevant.

### Coherencia

Most vulnerable to narrative over-binding and generic cohesion language. Repetition can be mistaken for system logic.

Control: separate repeated motif, design-system claim, and verified component behavior.

## Editorial Acceptance Gate

A perceptual-augmented finding should pass all checks:

1. Does it name at least one observable signal?
2. Does it distinguish source claim from observed behavior?
3. Does every interpretation use conditional language unless directly stated?
4. Does it avoid prestige-coded adjectives as analysis?
5. Does it avoid importing signals from prior cases?
6. Does any tension have evidence on both sides?
7. Does emotional temperature cite the mechanism that creates it?
8. Does low-confidence material remain a limitation or review question?
9. Would the sentence still be true if brand fame were ignored?
10. Does the prose improve specificity without increasing invented intent?

If any answer is no, the finding should be rewritten or left in baseline mode.
