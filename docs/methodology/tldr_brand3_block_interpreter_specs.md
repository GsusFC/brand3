# TLDR Brand3 Block Interpreter Specs v0.1

Status: working methodology draft  
Owner: FLOC* / Brand3  
Scope: Magnetism Scanner, TLDR Brand3, Block Interpreters  
Last updated: 2026-05-22

## Principle

Each TLDR Brand3 block is a distinct strategic exercise. The system should not ask a model to "generate the TLDR" globally. It should ask nine smaller questions, each with its own evidence scope, rejection rules, confidence rules, and output discipline.

The goal is not to make the model sound more strategic. The goal is to make each answer more traceable, more bounded, and more honest about what kind of claim it is.

Every block interpreter must produce:

- `block`
- `answer`
- `detected`
- `claim_type`: `declared | performed | inferred | absent`
- `mode`: `literal | compressed | interpreted_from_discourse | needs_human_review | not_detected`
- `confidence`: `high | medium | low`
- `observations`
- `reasoning`
- `evidence_used`
- `counter_evidence`
- `source_layers`
- `human_review_recommended`

And it must preserve the canonical TLDR block metadata:

- `question`
- `evidence_scope`
- `source_signal`
- `source_signal_path`
- `source_layer`
- `content` as a compatibility alias for `answer`
- `evidence` as a compatibility alias for `evidence_used`
- `rationale` as a compatibility alias for `reasoning`

## Shared Spec Shape

Each block interpreter should be defined with:

- `Task`: what exercise the model/system performs.
- `Primary Question`: the exact strategic question for the block.
- `Evidence Scope`: the evidence the block is allowed to use.
- `Look For`: positive patterns that can support an answer.
- `Reject`: signals that must not be used as sufficient basis.
- `Minimum Evidence`: the minimum support required to answer.
- `Claim Type Rules`: when the answer is declared, performed, inferred, or absent.
- `Mode Rules`: when the answer is literal, compressed, interpreted, needs human review, or not detected.
- `Confidence Rules`: when confidence is high, medium, or low.
- `Output Style`: how the final answer should be written.
- `Human Review Triggers`: when a strategist must review the block.

## 1. Core Purpose

### Task

Identify why the brand appears to exist beyond the product, feature set, or commercial transaction.

### Primary Question

Why does this brand appear to exist beyond the product?

### Evidence Scope

- Essence signal
- About page
- Purpose copy
- Mission-adjacent claims
- Founder story
- Manifesto language
- Repeated "why this matters" language
- Sustainability, cultural, category, or social change claims

### Look For

- Explicit purpose statements
- "We believe" / "we exist to" / "our purpose is" claims
- Moral, cultural, environmental, or category-level reason for being
- Repeated language that frames the brand as solving more than a product problem
- Founder-origin evidence that explains why the brand exists

### Reject

- Generic benefits
- Product features
- Category participation
- Commercial ambition alone
- "Transform" language without explanation of why the transformation matters
- Founder intent not visible in public evidence

### Minimum Evidence

At least one explicit purpose-like statement, or two independent signals pointing to the same broader reason for being.

### Claim Type Rules

- `declared`: the brand directly states a purpose or reason for being.
- `performed`: the brand repeatedly demonstrates a purpose through behavior, commitments, or product choices.
- `inferred`: Brand3 articulates a purpose hypothesis from repeated public signals.
- `absent`: only product, benefit, or commercial evidence exists.

### Mode Rules

- `literal`: direct purpose statement is already concise.
- `compressed`: direct purpose evidence is long and can be shortened.
- `interpreted_from_discourse`: purpose is inferred from repeated discourse or behavior.
- `needs_human_review`: purpose is plausible but strategically under-supported.
- `not_detected`: no evidence beyond product or commercial utility.

### Confidence Rules

- `high`: explicit purpose statement plus supporting evidence.
- `medium`: repeated purpose-like signals across multiple sources.
- `low`: one weak purpose signal or inferred pattern.

### Output Style

Concise, reason-for-being language. Avoid turning purpose into an inspirational slogan.

### Human Review Triggers

- Purpose is inferred from sparse evidence.
- Purpose depends on sustainability, social impact, or founder intent that is not directly documented.
- Purpose sounds stronger than the evidence.

## 2. Magnetism

### Task

Find the phrase, tension, or emotional hook that concentrates the brand's attention energy.

### Primary Question

What phrase, tension, or emotional hook best concentrates the brand's magnetic energy?

### Evidence Scope

- Hero copy
- Tagline
- Repeated claims
- Campaign language
- Short CTAs
- Mantra-like phrasing
- Category tension
- Strong emotional promise

### Look For

- Short memorable phrases
- Hero statements
- Repeated claims
- Tensions or oppositions
- Action language
- Emotional compression
- Category reframes

### Reject

- Long feature lists
- Generic slogans
- Navigation labels
- One-off boilerplate
- Claims that are clear but not attention-driving
- Pure value proposition when no emotional/tension signal exists

### Minimum Evidence

At least one phrase or tension that can plausibly operate as the brand's attention anchor.

### Claim Type Rules

- `declared`: a tagline, hero phrase, or repeated claim exists.
- `performed`: the brand repeatedly behaves around one emotional/tension pattern.
- `inferred`: Brand3 articulates the hook from multiple weaker signals.
- `absent`: no magnetic phrase or tension is visible.

### Mode Rules

- `literal`: phrase is already strong and concise.
- `compressed`: phrase is direct but needs shortening.
- `interpreted_from_discourse`: hook is synthesized from repeated signals.
- `needs_human_review`: hook is plausible but not clearly owned by the brand.
- `not_detected`: no defensible magnetic hook.

### Confidence Rules

- `high`: explicit tagline or repeated hero phrase.
- `medium`: one strong phrase or repeated pattern.
- `low`: weak phrase or broad tension requiring interpretation.

### Output Style

Short, concrete, memorable if the evidence supports it. Do not invent a campaign line.

### Human Review Triggers

- The strongest hook is a generic category claim.
- Multiple competing hooks exist.
- The output would require copywriting beyond evidence.

## 3. Value Proposition

### Task

Identify the concrete value exchange: what the brand offers, to whom, and what changes for that audience.

### Primary Question

What does the brand offer, to whom, and what changes for that audience?

### Evidence Scope

- Hero copy
- Product/service descriptions
- Features
- Use cases
- Pricing copy
- Audience claims
- Product pages
- Benefits

### Look For

- Offer plus audience
- "Help X do Y" statements
- Product/service categories
- Functional transformation
- Before/after improvement
- Clear use cases

### Reject

- Tagline alone
- Vague ambition
- Values statements
- Founder story
- Generic "platform/solution" language without a concrete offer
- Navigation or menu text

### Minimum Evidence

At least one clear offer or service description. Stronger answers require audience and outcome evidence.

### Claim Type Rules

- `declared`: offer is directly stated.
- `performed`: product structure demonstrates the value exchange.
- `inferred`: offer is clear from features but not stated as a proposition.
- `absent`: no clear offer.

### Mode Rules

- `literal`: value proposition is already concise.
- `compressed`: direct offer evidence is long and can be shortened.
- `interpreted_from_discourse`: features imply a value exchange.
- `needs_human_review`: offer exists but audience/outcome are unclear.
- `not_detected`: no defensible offer.

### Confidence Rules

- `high`: offer, audience, and outcome are explicit.
- `medium`: offer is clear but audience or outcome is partial.
- `low`: inferred from features only.

### Output Style

Concrete and functional. Prefer "offers X to Y so they can Z" when supported.

### Human Review Triggers

- Audience is inferred.
- Transformation is inferred.
- Multiple offers compete without hierarchy.

## 4. Personality

### Task

Infer the personality the brand performs through tone, vocabulary, behavior, and expression.

### Primary Question

What personality does the brand perform through tone, vocabulary, behavior, and visual expression?

### Evidence Scope

- Tone of voice
- Verbs
- Repeated vocabulary
- CTA style
- Audience framing
- Visual expression
- Product behavior
- Interaction style
- Archetypal cues

### Look For

- Repeated tone patterns
- Energy level
- Confidence/humility posture
- Care, rebellion, expertise, play, authority, craft, performance, or community cues
- Visual behavior that reinforces voice
- Audience relationship pattern

### Reject

- One-off adjectives
- Product category alone
- "Trusted", "secure", or "simple" as personality unless voice supports it
- Generic SaaS claims
- Founder intent not visible in expression
- Archetype assignment from a single phrase

### Minimum Evidence

At least two expression signals, preferably from different sources: copy plus visual, copy plus CTA, product behavior plus tone, or repeated vocabulary.

### Claim Type Rules

- `declared`: brand directly states its personality or voice.
- `performed`: personality is demonstrated through repeated expression.
- `inferred`: Brand3 maps expression patterns to a personality hypothesis.
- `absent`: not enough expressive signal.

### Mode Rules

- `literal`: rare; only if personality is explicitly declared.
- `compressed`: declared voice/personality is long and can be shortened.
- `interpreted_from_discourse`: normal mode for this block.
- `needs_human_review`: competing or weak personality readings.
- `not_detected`: no repeated tone/behavior signal.

### Confidence Rules

- `high`: explicit voice/personality plus expression evidence.
- `medium`: repeated expression patterns across sources.
- `low`: one or two weak expression signals.

### Output Style

Hypothesis language. Example: "Hero with Creator traits", not "The brand is Hero."

### Human Review Triggers

- Only one expression signal exists.
- Multiple archetypes compete.
- Visual and verbal signals conflict.
- The output depends heavily on archetype interpretation.

## 5. Brand Idea

### Task

Articulate the conceptual idea connecting strategy, category, offer, and expression.

### Primary Question

What conceptual idea connects the brand's strategy, category, offer, and expression?

### Evidence Scope

- Visual signature
- Hero message
- Category framing
- Product metaphor
- Core promise
- Purpose
- Repeated narrative patterns
- Naming
- Design behavior

### Look For

- Category reframe
- Strong metaphor
- Coherent link between product and expression
- Repeated conceptual language
- Visual/verbal alignment
- Distinct point of view

### Reject

- Generic positioning copy
- Product feature summary
- Isolated visual style
- Slogan without category or offer connection
- Consultancy-sounding abstraction not traceable to evidence

### Minimum Evidence

At least three connected signals: category/offer, message, and expression. If visual evidence is missing, confidence should usually be low or human review should be recommended.

### Claim Type Rules

- `declared`: brand explicitly states a central idea.
- `performed`: idea is demonstrated coherently across product, message, and expression.
- `inferred`: Brand3 articulates the concept from cross-signals.
- `absent`: no coherent cross-signal concept.

### Mode Rules

- `literal`: rare; only if central idea is declared.
- `compressed`: direct idea exists but is too long.
- `interpreted_from_discourse`: normal mode for this block.
- `needs_human_review`: idea is plausible but under-supported.
- `not_detected`: not enough cross-signal evidence.

### Confidence Rules

- `high`: explicit idea or strong alignment across message, product, and expression.
- `medium`: two or three aligned signals.
- `low`: plausible concept from sparse or partial evidence.

### Output Style

Conceptual but bounded. No inflated strategic copy.

### Human Review Triggers

- Visual evidence is absent.
- Only product and message support the idea.
- The phrasing sounds more sophisticated than the evidence.
- Multiple brand ideas compete.

## 6. Attributes

### Task

Identify observable qualities the brand describes or demonstrates consistently.

### Primary Question

Which 3 attributes does the brand describe or demonstrate consistently?

### Evidence Scope

- Claims
- Adjectives
- Product qualities
- UX behavior
- Visual language
- Proof points
- Repeated descriptions
- Category-specific qualities

### Look For

- Repeated descriptors
- Demonstrated product qualities
- Visual qualities
- Operational qualities
- Proof-backed traits
- Audience-recognizable attributes

### Reject

- Category nouns
- Random nouns from feature copy
- Values disguised as attributes
- Generic filler such as "specific", "observable", or "grounded"
- One-off adjective without support

### Minimum Evidence

At least one clear attribute signal for each attribute returned. Do not force three if only one or two are supported.

### Claim Type Rules

- `declared`: attributes are directly stated.
- `performed`: attributes are demonstrated by product, UX, or visual behavior.
- `inferred`: attributes are derived from repeated evidence.
- `absent`: no defensible attributes.

### Mode Rules

- `literal`: direct list of attributes exists.
- `compressed`: direct descriptions are long.
- `interpreted_from_discourse`: attributes are demonstrated, not stated.
- `needs_human_review`: attributes are plausible but weak.
- `not_detected`: no attribute evidence.

### Confidence Rules

- `high`: three repeated or explicit attributes.
- `medium`: two to three supported attributes.
- `low`: one weakly supported attribute or inferred attribute set.

### Output Style

Return short attribute terms. Do not return category nouns.

### Human Review Triggers

- Fewer than three attributes are supported.
- Attributes are inferred from product category.
- Attribute and value distinction is unclear.

## 7. Values

### Task

Identify what the brand appears to defend, not merely what it offers.

### Primary Question

Which 3 values does the brand appear to defend through what it says and how it acts?

### Evidence Scope

- Values page
- Mission/purpose copy
- Manifesto
- Sustainability claims
- Culture claims
- Transparency/security commitments
- Hiring or community language
- Product choices that demonstrate belief

### Look For

- Explicit values
- "We believe" statements
- Commitments
- Tradeoffs the brand seems to defend
- Ethical, cultural, environmental, or community principles
- Repeated belief language

### Reject

- Generic product benefits
- Trust/security/simple as values unless framed as commitments or beliefs
- Category requirements
- Feature nouns
- Attributes without belief evidence
- Aspirational values unsupported by behavior

### Minimum Evidence

At least one explicit value or repeated commitment. Do not force three values when evidence supports fewer.

### Claim Type Rules

- `declared`: brand states values directly.
- `performed`: values are demonstrated through repeated commitments or behavior.
- `inferred`: Brand3 infers values from strong repeated patterns.
- `absent`: only features or generic benefits exist.

### Mode Rules

- `literal`: values are listed directly.
- `compressed`: values statements are long.
- `interpreted_from_discourse`: values are demonstrated, not stated.
- `needs_human_review`: values are plausible but not explicit.
- `not_detected`: no belief/commitment evidence.

### Confidence Rules

- `high`: explicit values plus supporting evidence.
- `medium`: repeated commitments.
- `low`: values inferred from sparse behavior.

### Output Style

Short value terms, but only as many as evidence supports.

### Human Review Triggers

- Values are inferred from product benefits.
- Values overlap heavily with attributes.
- Values would imply ethical/cultural claims not directly evidenced.

## 8. Mission

### Task

Identify the brand's current operating activity.

### Primary Question

What does the brand concretely do today?

### Evidence Scope

- Tactispace signal
- Product/service copy
- Operational claims
- Present-tense "we build/create/provide" language
- Current audience served
- Delivery mechanism

### Look For

- Present-tense verbs: build, create, provide, offer, operate, deliver
- Concrete products or services
- Current audience served
- "We help X do Y" when it describes current activity
- Delivery mechanism or operating model

### Reject

- CTAs
- Taglines
- Future ambitions
- Purpose statements
- Category slogans
- Emotional claims without operation

### Minimum Evidence

At least one concrete present-tense operating claim.

### Claim Type Rules

- `declared`: copied or compressed from a direct operating claim.
- `performed`: product/service evidence demonstrates current activity.
- `inferred`: activity is clear from product evidence but no mission-like sentence exists.
- `absent`: only CTAs, benefits, or vision language exist.

### Mode Rules

- `literal`: operating sentence is already concise.
- `compressed`: operating evidence is long but direct.
- `interpreted_from_discourse`: product/service evidence clearly implies activity.
- `needs_human_review`: current activity is inferred from product evidence only.
- `not_detected`: no operating evidence.

### Confidence Rules

- `high`: explicit mission/current activity statement.
- `medium`: clear product/service description.
- `low`: inferred from sparse product evidence.

### Output Style

Concrete, present-tense, operational. No aspiration.

### Human Review Triggers

- Mission is inferred from product evidence only.
- Evidence mixes mission with vision or purpose.
- The output introduces verbs not supported by evidence.

## 9. Vision

### Task

Identify the future state, category shift, or long-term change the brand appears to be building toward.

### Primary Question

What future, category shift, or change does the brand appear to be building toward?

### Evidence Scope

- Future-facing language
- "New model" claims
- "Future of" category language
- Manifesto
- Category-change claims
- Long-term ambition
- Roadmap language
- Purpose-to-future connection

### Look For

- Future state
- Category transformation
- New model or paradigm
- Long-term change
- Explicit vision statements
- Ambition beyond current product delivery

### Reject

- Current offer alone
- Product roadmap without future thesis
- Generic "transform" language without direction
- Mission statements
- Tagline without future state

### Minimum Evidence

At least one future-facing or category-change signal. Do not infer vision from the current offer alone.

### Claim Type Rules

- `declared`: brand states a vision directly.
- `performed`: brand repeatedly behaves toward a visible future model.
- `inferred`: Brand3 articulates a future hypothesis from future-facing evidence.
- `absent`: no future/category-change evidence.

### Mode Rules

- `literal`: vision statement is already concise.
- `compressed`: direct vision evidence is long.
- `interpreted_from_discourse`: future direction is inferred from evidence.
- `needs_human_review`: future direction is plausible but under-supported.
- `not_detected`: no future evidence.

### Confidence Rules

- `high`: explicit vision statement plus support.
- `medium`: clear future/category-change signal.
- `low`: weak future language or sparse evidence.

### Output Style

Future-oriented but bounded. Avoid grandiose category claims unless explicit.

### Human Review Triggers

- Future is inferred from current offer.
- Future language is generic.
- Vision overlaps with core purpose or mission.
- Regulatory, technical, or category constraints could challenge the claim.
