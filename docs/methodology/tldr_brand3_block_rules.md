# TLDR Brand3 Block Rules v0.3

Status: working methodology draft  
Owner: FLOC* / Brand3  
Scope: Magnetism Scanner, Magenta Circle, TLDR Brand3  
Last updated: 2026-05-22

## v0.3 Principle

The TLDR must not present Brand3 interpretations as final truths about the brand. The improvement is not that the model "gets the brand right" more often; the improvement is that every TLDR claim has a visible epistemic status.

Every block must distinguish:

- `declared`: the brand says it directly in available evidence.
- `performed`: the brand demonstrates it through tone, behavior, offer, visual language, or repeated discourse.
- `inferred`: Brand3 articulates a strategic hypothesis from observable signals.
- `absent`: the available evidence is not sufficient.

If a claim cannot be supported with traceable evidence, the block must degrade to `needs_human_review` or `not_detected`. Strategic fluency is not enough.

## v0.3 Block Contract

Every TLDR block must expose:

- `block`
- `detected`
- `question`
- `evidence_scope`
- `source_signal`
- `source_signal_path`
- `source_layer`
- `observations`
- `answer`
- `claim_type`: `declared | performed | inferred | absent`
- `mode`: `literal | compressed | interpreted_from_discourse | needs_human_review | not_detected`
- `confidence`: `high | medium | low`
- `reasoning`
- `evidence_used`
- `counter_evidence`
- `human_review_recommended`

Compatibility aliases may remain during migration:

- `content` mirrors `answer`
- `evidence` mirrors `evidence_used`
- `rationale` mirrors `reasoning`

Derived metadata that must stay present on the block:

- `source_layers`
- `human_review_recommended`
- `detected`

## v0.3 Migration Scope

This iteration migrates the TLDR as an incremental Block Interpreter architecture:

1. Mission, vision, value proposition, and personality are the first priority blocks.
2. Magnetism, brand idea, attributes, values, and core purpose must still emit the v0.3 contract.
3. Blocks may remain heuristic-backed, but they must state their claim type and confidence honestly.
4. Existing scans must render even when they predate the v0.3 fields.
5. The UI must make declared, performed, inferred, and absent claims visibly different.

## v0.3 UI Rule: TLDR First, Magenta Embedded

The product view should not show TLDR Brand3 and Magenta Circle as competing primary sections. The user-facing surface is the TLDR. The Magenta Circle should be embedded inside each TLDR block as the source signal that explains where the block came from.

The Magenta Circle remains a 7-signal methodology, while the TLDR remains a 9-block strategic articulation:

```text
7 Magenta signals -> 9 TLDR blocks
```

Use human signal labels in the main TLDR:

- `Mindspace` -> `Emotions -> Magnetism`
- `Aetherspace` -> `Essence -> Core Purpose`
- `Gamespace` -> `Voice -> Personality`
- `Envispace` -> `Expression -> Brand Idea`
- `Netspace` -> `Exchange -> Value Proposition`
- `Tactispace` -> `Action / Direction -> Mission + Vision`
- `Ambientspace` -> `Context / Beliefs -> Attributes + Values`

The technical layer names may appear only in methodology/debug details, not as the primary title of a TLDR block.

## 1. Executive Summary

The TLDR Brand3 is not a literal extraction table. It is a strategy artifact generated from observed evidence.

Some blocks are often declared directly by the brand. Others almost never exist as literal copy and must be articulated from discourse, tone, vocabulary, visual language, category behavior, and contextual evidence.

The system must therefore separate:

```text
EVIDENCE -> INTERPRETATION -> TLDR OUTPUT
```

Brand3 should not ask: "does this exact phrase exist?"

Brand3 should ask: "can this block be responsibly articulated from available evidence, and what is the basis of that articulation?"

The product risk is a two-sided failure:

- Too literal: the scanner marks useful strategic material as `not_detected` because the website does not explicitly state it.
- Too generative: the scanner writes plausible consultancy text that is not supported by evidence.

The solution is a block-level inference model. Every TLDR block must declare whether it is literal, compressed, interpreted, missing, or in need of human review.

## 2. Inference Modes

Every TLDR block must declare one `mode`.

### literal

Definition: the content exists almost exactly in the source.

Use when:

- the brand explicitly states a mission, vision, value, tagline, promise, or offer
- the output only removes casing, punctuation, or minor noise

Risks:

- accepting generic corporate language as if it were strong branding
- letting bad literal copy inflate confidence

Example:

```json
{
  "content": "Private Banking for Next-Gen Wealth Managers",
  "mode": "literal"
}
```

### compressed

Definition: the system shortens one or more explicit phrases without changing meaning.

Use when:

- source material is clear but too long for the TLDR
- the brand expresses the idea directly but not elegantly
- a block requires a concise formulation

Risks:

- over-sharpening into a slogan the brand did not earn
- deleting nuance that matters in regulated or technical categories

Example:

```text
Evidence: "Unete al nuevo modelo industrial basado en el potencial de las macroalgas..."
Output: "Unete al nuevo modelo industrial de las macroalgas."
```

### interpreted_from_discourse

Definition: the system articulates the block from multiple evidence signals.

Use when:

- the block is normally implicit, such as Personality or Brand Idea
- signal comes from tone, vocabulary, repeated claims, visual semantics, category posture, or third-party descriptions
- a strategist could responsibly articulate the block from the available material

Risks:

- producing generic consultancy language
- overstating confidence
- confusing plausible category norms with brand-specific evidence

Example:

```text
PERSONALITY: Applied Sage with Caregiver and scientific Creator traits.
```

### not_detected

Definition: there is not enough evidence to articulate the block responsibly.

Use when:

- evidence is missing, contradictory, or too generic
- available text is only navigation, CTA, boilerplate, or category labels
- interpretation would rely on category assumptions rather than brand evidence

Risks:

- being too conservative and missing strategy that is implicit but clear

### needs_human_review

Definition: there is signal, but interpretation is ambiguous or strategically sensitive.

Use when:

- multiple plausible interpretations compete
- a block affects high-level positioning
- the category is regulated, reputationally sensitive, or socially loaded
- the system detects contradiction between evidence families

Risks:

- blocking too often and reducing product usefulness
- hiding useful low-confidence interpretation from the user

## 3. Shared Data Contract

Every TLDR block should use this shape. This is the canonical runtime contract used by the extractor and tests:

```json
{
  "block": "value_proposition",
  "detected": true,
  "question": "What does the brand offer, to whom, and what changes for that audience?",
  "evidence_scope": ["netspace", "tactispace", "ambientspace"],
  "source_signal": "Exchange",
  "source_signal_path": "Exchange → Value Proposition",
  "source_layer": "netspace",
  "observations": ["Uses 2 traceable evidence item(s) selected for value_proposition."],
  "answer": "string | string[] | null",
  "claim_type": "declared | performed | inferred | absent",
  "mode": "literal | compressed | interpreted_from_discourse | needs_human_review | not_detected",
  "confidence": "high | medium | low",
  "reasoning": "short explanation of how evidence supports the formulation",
  "evidence_used": ["literal quote or exact visual/context signal"],
  "counter_evidence": ["short limitation or rebuttal"],
  "source_layers": ["netspace", "tactispace", "ambientspace"],
  "human_review_recommended": false,
  "content": "string | string[] | null",
  "evidence": ["literal quote or exact visual/context signal"],
  "rationale": "short explanation of how evidence supports the formulation"
}
```

Required fields for every block:

- `block`
- `detected`
- `content`
- `question`
- `evidence_scope`
- `source_signal`
- `source_signal_path`
- `source_layer`
- `observations`
- `answer`
- `claim_type`
- `mode`
- `confidence`
- `reasoning`
- `evidence_used`
- `counter_evidence`
- `source_layers`
- `human_review_recommended`

Required when `mode=interpreted_from_discourse`:

- `reasoning`

Required when `mode=needs_human_review`:

- `human_review_recommended=true`
- `reasoning` must explain ambiguity

Renderer rule:

- show `content` first, then `answer`
- expose `mode`, `confidence`, `evidence`, and `rationale` as inspection metadata
- never hide the difference between literal and interpreted content

## 4. Block-by-Block Rules

## 4.1 CORE PURPOSE

Magenta layer: Aetherspace  
Question: Why  
Normal nature: interpreted  
Default mode: interpreted_from_discourse

### Goal

Articulate why the brand exists beyond the immediate product or service.

Purpose is not mission. Purpose is the underlying reason the effort matters.

### Recommended Inputs

- about page
- founder story
- manifesto
- category tension
- repeated moral, cultural, or systemic language
- third-party explanations of why the company exists
- values when connected to market or social need

### Useful Frameworks

- purpose / mission / vision distinctions
- founder-market fit
- category tension
- Simon Sinek's "why" as a lens, not a template

### Strong Signals

- "we believe"
- "why we exist"
- "our purpose"
- market failure the brand is correcting
- specific world-view language
- repeated category-level tension

### Weak Signals

- "innovation"
- "future"
- "transform"
- ESG language without operational grounding
- generic impact claims

### Mark not_detected When

- evidence only describes functionality
- the only source is category boilerplate
- a purpose would require inventing motivation

### Mark needs_human_review When

- the brand operates in health, finance, climate, social impact, or public-interest categories and purpose could be overstated
- owned claims and third-party evidence diverge

### Good Output

```text
Build a regenerative industrial model around Mediterranean macroalgae.
```

### Bad Output

```text
Save the planet through innovation.
```

### Confidence Criteria

High:

- explicit purpose or manifesto plus corroborating product/activity evidence

Medium:

- repeated purpose-like language across owned pages

Low:

- one strong phrase in hero copy only

### Scoring Implication

CORE PURPOSE is a primary Magnetism input. Interpreted purpose can score, but only if evidence is specific.

## 4.2 MAGNETISM

Magenta layer: Mindspace  
Question: Which  
Normal nature: literal, compressed, or interpreted  
Default mode: compressed

### Goal

Find or articulate the phrase, tension, or emotional charge that makes the brand memorable.

This is the line a founder could repeat when the product pivots.

### Recommended Inputs

- hero headline
- tagline
- manifesto
- founder quote
- repeated high-energy claim
- community language
- emotionally charged category tension

### Useful Frameworks

- verbal identity
- slogan / tagline theory
- distinctiveness
- memorability heuristics

### Strong Signals

- short phrase
- rhythm
- specificity
- tension
- distinctive vocabulary
- promise that can be remembered or repeated

### Weak Signals

- "empowering the future of"
- "leading platform"
- "unlock your potential"
- category descriptor without emotional charge

### Mark not_detected When

- all phrases are interchangeable with competitors
- there is no memorable phrase or articulable tension

### Mark needs_human_review When

- the strongest phrase is promising but too long, ambiguous, or legally sensitive

### Good Output

```text
Unete al nuevo modelo industrial de las macroalgas.
```

### Bad Output

```text
Empowering sustainable innovation.
```

### Confidence Criteria

High:

- distinctive literal tagline or repeated founder/hero language

Medium:

- compressed from a strong phrase

Low:

- articulated from weak but coherent tension

### Scoring Implication

MAGNETISM should be scored for originality, specificity, memorability, and verifiable promise. Literal generic copy should not score highly.

## 4.3 VALUE PROPOSITION

Magenta layer: Netspace  
Question: When  
Normal nature: compressed  
Default mode: compressed

### Goal

State what the brand offers, for whom, and what value is exchanged.

This block should be less poetic than MAGNETISM. It must stay close to product and audience reality.

### Recommended Inputs

- hero product description
- product pages
- service pages
- pricing
- use cases
- audience language
- third-party descriptions of offering

### Useful Frameworks

- Value Proposition Canvas
- Jobs To Be Done
- positioning statement
- category design

### Strong Signals

- offer + audience + outcome
- product tied to job/pain/gain
- specific use case
- concrete functional value

### Weak Signals

- menu labels
- CTA labels
- broad category claims
- "solutions for modern teams"

### Mark not_detected When

- it is unclear what is sold, to whom, or why it matters
- only navigation or generic category language is available

### Mark needs_human_review When

- multiple offers compete without hierarchy
- B2B and B2C audiences are mixed ambiguously

### Good Output

```text
Macroalgae-based solutions for cosmetics, nutrition, and bioremediation.
```

### Bad Output

```text
Sustainable solutions for the future.
```

### Confidence Criteria

High:

- clear offer visible in hero/product page

Medium:

- offer reconstructed from product categories and use cases

Low:

- offer inferred from partial site structure

### Scoring Implication

VALUE PROPOSITION contributes to Coherence and secondarily to Magnetism. It should be penalized if it lacks audience or concrete offer.

## 4.4 PERSONALITY

Magenta layer: Gamespace  
Question: Who  
Normal nature: interpreted  
Default mode: interpreted_from_discourse

### Goal

Articulate the character of the brand from discourse, tone, vocabulary, visual semantics, category behavior, and audience posture.

Personality usually does not exist as a literal phrase. The system should not require a brand to say "we are a Sage brand".

### Recommended Inputs

- tone of voice
- vocabulary
- claims
- CTAs
- category posture
- audience relationship
- visual semantics
- founder voice
- third-party descriptions

### Useful Frameworks

Use as lenses, not final truth:

- Jennifer Aaker Brand Personality Dimensions: sincerity, excitement, competence, sophistication, ruggedness.
- Jungian / brand archetypes: Sage, Creator, Caregiver, Ruler, Hero, Rebel, Explorer, Lover, Everyman, Innocent, Jester, Magician.

### Strong Signals

- consistent vocabulary
- recognizable tone
- clear relationship with audience
- visual system with character
- repeated behavioral posture

### Weak Signals

- one adjective
- neutral technical copy
- category alone
- no visual evidence

### Mark not_detected When

- only functional description exists
- there is no tone, no vocabulary pattern, no visual signal, and no founder/audience posture

### Mark needs_human_review When

- multiple personality readings compete
- brand tone conflicts with category trust requirements
- visual and verbal signals contradict each other

### Good Output

```text
Applied Sage with Caregiver and scientific Creator traits.
```

### Bad Output

```text
Innovative, modern and reliable.
```

### Confidence Criteria

High:

- verbal tone, visual identity, and audience posture all point to the same composite profile

Medium:

- repeated discourse supports two or three traits

Low:

- only category and limited vocabulary support the profile

### Scoring Implication

PERSONALITY is usually interpreted and should be weighted accordingly. It is critical for Coherence with MAGNETISM.

## 4.5 BRAND IDEA

Magenta layer: Envispace  
Question: How  
Normal nature: interpreted visual-conceptual  
Default mode: interpreted_from_discourse

### Goal

Articulate the visual and conceptual idea that makes the brand recognizable.

Brand Idea is not an aesthetic label. It is the bridge between strategy and perception.

### Recommended Inputs

- visual signature
- screenshot semantics
- typography/color/layout/image signals
- naming
- hero concept
- repeated metaphors
- product/category concept
- distinctive visual assets

### Useful Frameworks

- semiotics
- visual identity systems
- distinctive brand assets
- brand concepting

### Strong Signals

- visual system connected to concept
- repeated metaphor
- distinctive visual asset
- coherent verbal/visual idea

### Weak Signals

- "minimalist"
- "modern"
- "premium"
- generic SaaS layout
- color description without meaning

### Mark not_detected When

- no screenshot or visual signature is available
- visual system is generic and copy provides no organizing concept

### Mark needs_human_review When

- visual identity conflicts with purpose/personality
- visual evidence is obstructed or incomplete

### Good Output

```text
Mediterranean biotech translated into a regenerative industrial identity.
```

### Bad Output

```text
Clean modern website.
```

### Confidence Criteria

High:

- visual semantics and copy converge on the same idea

Medium:

- clear visual-conceptual pattern with partial evidence

Low:

- concept inferred mostly from copy without visual support

### Scoring Implication

BRAND IDEA is a primary bridge for Coherence. If Envispace contradicts other internal layers, Coherence should drop.

## 4.6 ATTRIBUTES

Magenta layer: Ambientspace  
Question: What  
Normal nature: synthesized  
Default mode: interpreted_from_discourse

### Goal

Return three observable brand attributes.

Attributes are descriptive qualities of how the brand appears or behaves. They are not necessarily moral values.

### Recommended Inputs

- repeated adjectives
- product qualities
- visual semantics
- service model
- feature evidence
- third-party descriptors

### Useful Frameworks

- brand attributes
- product attribute mapping
- visual/verbal consistency

### Strong Signals

- repeated descriptors
- qualities demonstrated by product/service
- visual cues aligned with copy

### Weak Signals

- generic adjectives
- decorative words without evidence
- single unsupported adjective

### Mark not_detected When

- no quality appears consistently
- only generic marketing adjectives are present

### Good Output

```json
["regenerative", "circular", "functional"]
```

### Bad Output

```json
["innovative", "modern", "premium"]
```

### Confidence Criteria

High:

- attributes are explicit and repeated

Medium:

- attributes are synthesized from multiple related phrases

Low:

- attributes come from one phrase only

### Scoring Implication

ATTRIBUTES mostly affect Coherence, especially against VALUE PROPOSITION and VALUES.

## 4.7 VALUES

Magenta layer: Ambientspace  
Question: What  
Normal nature: literal or interpreted  
Default mode: interpreted_from_discourse

### Goal

Return three values the brand declares or demonstrates.

Values are principles. They should not be confused with product attributes.

### Recommended Inputs

- values page
- manifesto
- purpose copy
- ESG or ethics claims
- operational proof
- third-party validation

### Useful Frameworks

- brand values
- declared vs demonstrated values
- proof hierarchy

### Strong Signals

- values explicitly listed
- repeated ethical language
- operational proof
- third-party corroboration

### Weak Signals

- generic values
- sustainability word without evidence
- compliance language used as brand value

### Mark not_detected When

- values are absent or purely generic
- evidence does not support principles, only attributes

### Mark needs_human_review When

- values involve ESG, health, finance, safety, or social claims without proof

### Good Output

```json
["regeneration", "circularity", "environmental commitment"]
```

### Bad Output

```json
["quality", "innovation", "excellence"]
```

### Confidence Criteria

High:

- values are declared and demonstrated

Medium:

- values are consistently implied by copy and behavior

Low:

- values are inferred from one phrase

### Scoring Implication

VALUES should not inflate score if they are declared but not demonstrated.

## 4.8 MISSION

Magenta layer: Tactispace  
Question: Where  
Normal nature: literal or articulated operational  
Default mode: interpreted_from_discourse

### Goal

State what the brand is doing now to move toward its purpose.

Mission is a present-tense operating mandate. It is not a CTA.

### Recommended Inputs

- mission statement
- about page
- "we create/build/provide" claims
- product/service activity
- operating model
- roadmap if operational

### Useful Frameworks

- mission vs vision distinction
- operating mandate
- strategy-to-action translation

### Strong Signals

- present-tense verb
- activity concrete enough to perform
- audience or beneficiary
- product/service connection

### Weak Signals

- contact us
- book demo
- subscribe
- pricing
- menu label
- broad aspiration

### Mark not_detected When

- no present operational mandate exists
- only CTA or future aspiration exists

### Mark needs_human_review When

- operational claims are unclear or too broad
- current activity and purpose diverge

### Good Output

```text
Create Mediterranean macroalgae-based functional raw materials for sustainable formulations.
```

### Bad Output

```text
Contact customers and grow the business.
```

### Confidence Criteria

High:

- explicit mission statement

Medium:

- clear "we create/build/provide" operating claim

Low:

- mission inferred from product/service only

### Scoring Implication

MISSION supports Coherence with CORE PURPOSE. CTA-only evidence must not count.

## 4.9 VISION

Magenta layer: Tactispace  
Question: Where  
Normal nature: articulated aspirational  
Default mode: interpreted_from_discourse

### Goal

State the future world or long-term destination the brand points toward.

Vision is not simply what the product does today.

### Recommended Inputs

- vision statement
- future-state language
- category transformation claims
- manifesto
- long-term ecosystem language
- "new model" language

### Useful Frameworks

- vision as future state
- category design
- market transformation narrative

### Strong Signals

- "new model"
- "future where"
- category transformation
- systemic long-term ambition
- ecosystem language

### Weak Signals

- product promise
- present activity
- generic leadership aspiration

### Mark not_detected When

- no future-state language exists
- only current offer is visible

### Mark needs_human_review When

- future-state claims are grandiose or unsupported
- vision could conflict with evidence or regulatory constraints

### Good Output

```text
A regenerative industrial model built around the potential of Mediterranean macroalgae.
```

### Bad Output

```text
Become the leading platform in sustainability.
```

### Confidence Criteria

High:

- explicit vision statement plus supporting evidence

Medium:

- clear future-state phrase such as "new model" with category specificity

Low:

- future inferred from weak aspiration

### Scoring Implication

VISION supports Coherence with CORE PURPOSE and MISSION. It should be penalized if it is inflated from weak evidence.

## 5. Personality Deep Dive

PERSONALITY should be a composite profile, not a single archetype.

Avoid:

```text
PERSONALITY = Sage
```

Prefer:

```json
{
  "content": "Applied Sage with Caregiver and scientific Creator traits",
  "archetypes": [
    {"name": "Sage", "weight": 0.45},
    {"name": "Caregiver", "weight": 0.35},
    {"name": "Creator", "weight": 0.20}
  ],
  "aaker_dimensions": [
    {"name": "competence", "weight": 0.45},
    {"name": "sincerity", "weight": 0.35},
    {"name": "sophistication", "weight": 0.20}
  ]
}
```

### Archetype Signal Hints

Sage:

- knowledge
- research
- technical clarity
- education
- diagnosis

Caregiver:

- protection
- wellbeing
- health
- environment
- regeneration

Creator:

- materials
- formulations
- design
- invention
- building

Ruler:

- governance
- authority
- control
- compliance
- institutional leadership

Magician:

- transformation
- breakthrough
- AI
- hidden complexity made simple

Hero:

- performance
- conquest
- effort
- overcoming constraints

Rebel:

- anti-status quo
- provocation
- rupture
- refusal of category norms

Explorer:

- discovery
- frontier
- autonomy
- movement

Lover:

- beauty
- sensuality
- intimacy
- desire

Everyman:

- accessibility
- belonging
- practical community

Innocent:

- purity
- simplicity
- optimism

Jester:

- humor
- play
- irreverence

### Aaker Dimension Hints

Sincerity:

- honest
- wholesome
- grounded
- caring

Excitement:

- daring
- spirited
- imaginative
- energetic

Competence:

- reliable
- intelligent
- successful
- technical

Sophistication:

- refined
- premium
- elegant
- aspirational

Ruggedness:

- tough
- outdoors
- resilient
- durable

### Anti-Overdetermination Rules

Do not assign Sage only because the category is technical.

Do not assign Caregiver only because there is an ESG word.

Do not assign Creator only because the company "builds" software.

Require at least two supporting signals for medium confidence.

## 6. Prompt Design Recommendations

Do not implement the TLDR as one global "fill all blocks" prompt.

Use block-specific goals.

Generic pattern:

```text
You are generating the TLDR Brand3 block: {BLOCK}.

Goal:
{BLOCK_GOAL}

Inputs:
- evidence packet
- visual semantics
- source quality state
- existing Magenta layer signals

Task:
1. Identify literal evidence relevant to this block.
2. Decide mode: literal, compressed, interpreted_from_discourse, not_detected, or needs_human_review.
3. Produce the shortest useful formulation.
4. Attach 1-3 evidence items.
5. Explain the rationale in one sentence.
6. Do not invent unsupported claims.
7. Do not recommend strategy.
```

Anti-patterns to explicitly forbid:

- "management teams should..."
- "founders typically..."
- "the brand could prioritize..."
- generic adjectives without evidence
- unsupported strategic advice
- future claims without future-state evidence
- turning CTA labels into mission

## 7. Scoring Implications

### Mode Weighting

```text
literal                    1.00
compressed                 0.90
interpreted_from_discourse 0.70
needs_human_review         0.40
not_detected               0.00
```

### Confidence Weighting

```text
high         1.00
medium       0.75
low          0.45
insufficient 0.00
```

### Evidence Quality Weighting

```text
third-party corroboration        high
owned product/about page         medium-high
owned hero copy                  medium
visual signature                 medium; high if consistent across system
navigation/menu                  low
CTA only                         weak
boilerplate claim                weak
```

### Magnetism Score

Primary inputs:

- MAGNETISM
- CORE PURPOSE
- BRAND IDEA

Secondary inputs:

- PERSONALITY
- VALUE PROPOSITION

Rules:

- low internal-layer evidence caps Magnetism
- literal but generic Magnetism should score low
- interpreted Magnetism can score if evidence is specific and memorable

### Coherence Score

Critical pairs:

- MAGNETISM <-> PERSONALITY
- CORE PURPOSE <-> MISSION / VISION
- VALUE PROPOSITION <-> ATTRIBUTES / VALUES
- BRAND IDEA <-> all other blocks

Rules:

- Coherence is not just completeness
- a complete TLDR can still be incoherent
- contradictory modes or low-confidence interpretations should cap Coherence

## 8. Example Application: Mediterranean Algae

Evidence available:

- "Macroalgas mediterraneas para industria y medio ambiente"
- "Soluciones con macroalgas para cosmetica, nutricion y biorremediacion"
- "Unete al nuevo modelo industrial basado en el potencial de las macroalgas: regenerativo, circular y comprometido con el medio ambiente"
- "Creamos materias primas funcionales con origen mediterraneo, listas para potenciar formulaciones sostenibles en cosmetica, nutricion y salud animal"

### CORE PURPOSE

```json
{
  "content": "Build a regenerative industrial model around Mediterranean macroalgae.",
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "nuevo modelo industrial basado en el potencial de las macroalgas",
    "regenerativo, circular y comprometido con el medio ambiente"
  ],
  "rationale": "The brand links macroalgae to a new regenerative and circular industrial model.",
  "source_layers": ["aetherspace"]
}
```

### MAGNETISM

```json
{
  "content": "Unete al nuevo modelo industrial de las macroalgas.",
  "mode": "compressed",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "Unete al nuevo modelo industrial basado en el potencial de las macroalgas..."
  ],
  "rationale": "The original phrase functions as an invitation into a category-level shift.",
  "source_layers": ["mindspace"]
}
```

### VALUE PROPOSITION

```json
{
  "content": "Macroalgae-based solutions for cosmetics, nutrition, and bioremediation.",
  "mode": "compressed",
  "detected": true,
  "confidence": "high",
  "evidence": [
    "Soluciones con macroalgas para cosmetica, nutricion y biorremediacion"
  ],
  "rationale": "The offer and use cases are directly stated.",
  "source_layers": ["netspace"]
}
```

### PERSONALITY

```json
{
  "content": "Applied Sage with Caregiver and scientific Creator traits.",
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "materias primas funcionales con origen mediterraneo",
    "regenerativo, circular y comprometido con el medio ambiente"
  ],
  "rationale": "The discourse combines technical knowledge, environmental care, and creation of functional ingredients.",
  "source_layers": ["gamespace", "ambientspace"]
}
```

### BRAND IDEA

```json
{
  "content": "Mediterranean biotech translated into a regenerative industrial identity.",
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "low",
  "evidence": [
    "Macroalgas mediterraneas para industria y medio ambiente"
  ],
  "rationale": "The idea connects origin, biotech material, industry, and environmental context; visual evidence is still needed.",
  "source_layers": ["envispace"]
}
```

### ATTRIBUTES

```json
{
  "content": ["regenerative", "circular", "functional"],
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "regenerativo, circular",
    "materias primas funcionales"
  ],
  "rationale": "The attributes are repeated as product and system qualities.",
  "source_layers": ["ambientspace"]
}
```

### VALUES

```json
{
  "content": ["regeneration", "circularity", "environmental commitment"],
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "regenerativo, circular y comprometido con el medio ambiente"
  ],
  "rationale": "The values are implied through repeated environmental and circularity language.",
  "source_layers": ["ambientspace"]
}
```

### MISSION

```json
{
  "content": "Create Mediterranean macroalgae-based functional raw materials for sustainable formulations.",
  "mode": "compressed",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "Creamos materias primas funcionales con origen mediterraneo..."
  ],
  "rationale": "The brand states a present-tense operational activity.",
  "source_layers": ["tactispace"]
}
```

### VISION

```json
{
  "content": "A regenerative industrial model built around the potential of Mediterranean macroalgae.",
  "mode": "interpreted_from_discourse",
  "detected": true,
  "confidence": "medium",
  "evidence": [
    "nuevo modelo industrial basado en el potencial de las macroalgas"
  ],
  "rationale": "The phrase points to a future category model, not only a current offer.",
  "source_layers": ["tactispace"]
}
```

## 9. Implementation Checklist

1. Replace current TLDR block shape with the v0.2 contract.
2. Add `mode`, `confidence`, `rationale`, `source_layers`, and `human_review_recommended` to each TLDR block.
3. Implement block-specific prompts instead of one global TLDR prompt.
4. Create fixtures for:
   - Mediterranean Algae
   - Wio Capital
   - Linear or Stripe
   - weak generic SaaS
5. Add tests for each inference mode.
6. Add tests that CTA-only evidence cannot create MISSION or VISION.
7. Add tests that PERSONALITY can be interpreted from discourse.
8. Add tests that BRAND IDEA requires visual or conceptual evidence.
9. Update scoring to use mode, confidence, evidence count, and source quality.
10. Update UI to show content first and metadata second.
11. Add human review flags where interpretation is ambiguous.
12. Keep Evidence Layer and TLDR Layer separate in storage and rendering.

## 10. Reference Lenses

These are lenses, not authorities.

- Jennifer Aaker, Dimensions of Brand Personality: useful for sincerity, excitement, competence, sophistication, ruggedness.
- Jungian brand archetypes: useful for narrative role, but should be mixed and weighted.
- Value Proposition Canvas: useful for grounding value proposition in customer segment, pain, gain, and job.
- Jobs To Be Done: useful for identifying the job behind the offer.
- Purpose / Mission / Vision distinctions: useful for separating why, present mandate, and future state.
- Semiotics and visual identity systems: useful for BRAND IDEA when connected to visual evidence.
- Distinctive Brand Assets: useful for separating recognizability from generic aesthetics.

## 11. Source Notes

Research references used to shape this draft:

- Jennifer Aaker, Dimensions of Brand Personality, Stanford GSB: https://www.gsb.stanford.edu/faculty-research/publications/dimensions-brand-personality
- Strategyzer, Value Proposition Canvas: https://www.strategyzer.com/value-proposition
- Strategyzer, Customer Value Map / Value Proposition Canvas background: https://www.strategyzer.com/library/the-customer-value-map-v-0-8-now-called-value-proposition-canvas
- Jobs To Be Done overview: https://en.wikipedia.org/wiki/Jobs_to_Be_Done
- Brand Archetypes overview: https://thebrandarchetypes.com/archetypes.html
- Scania brand archetype application: https://mediaportal.scania.com/content/scania-assets/group/en/home/our-brand/our-brand/Archetypes.html
- Purpose vs Mission vs Vision distinction: https://www.dontpaniclondon.com/blog/brand-vision-mission-purpose/
- Semiotics and Strategic Brand Management: https://www.marketingsemiotics.com/wp-content/uploads/2012/03/SemioticStrategy.pdf
- Distinctive Brand Assets overview: https://www.distinctivebat.com/distinctive-brand-assets/
