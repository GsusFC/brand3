# TLDR Brand3 benchmark from existing runs

Date: 2026-05-28

Purpose: compare current Magnetism Scanner TLDR output against a stricter
Brand3 analyst reading, using existing Brand Audit and Magnetism Scanner runs as
the corpus. This document is not a product report. It is a benchmark for the
next implementation pass.

Decision boundary: this benchmark records failures and target readings. It is
not an implementation plan for brand-specific keyword patches. Base44,
Bokeroon, Fly, Every, and tinyNature are regression cases for the next
Research Pack -> Analyst Pass flow, not templates for product heuristics.

## Method

For each case, compare:

- Current scanner block output.
- Evidence available in Brand Audit / Magnetism Scanner.
- Ideal Brand3 answer.
- Question the block should have answered.
- Failure type.
- Implementation implication.

The goal is not to make the model more verbose. The goal is to make evidence
selection and block reasoning closer to a strategist's working method.

## Block Questions

### Core Purpose

Question: Why does this brand appear to exist beyond selling the product?

Use:

- About page.
- Mission page.
- Founder/company narrative.
- Explicit purpose language.
- Repeated category belief.

Reject:

- Partnership CTAs.
- Student programs unless central to the company.
- Blog/article snippets.
- Product feature copy without a wider reason for existing.

### Magnetism

Question: What phrase, tension, or promise is most likely to be remembered?

Use:

- Hero line.
- Tagline.
- Repeated short claim.
- Strong contrast phrase.

Reject:

- Generic slogans with no category specificity if a stronger phrase exists.
- Navigation labels.
- SEO headings.

### Value Proposition

Question: What does the brand offer, to whom, and what changes for that
audience?

Use:

- Product description.
- Audience language.
- Outcome / transformation language.
- Pricing, feature, use case, and product pages when they clarify the offer.

Reject:

- Page chrome.
- Broken excerpts.
- "top of page" / navigation fragments.
- Founder stories unless they explain the offer.
- Proof points that only validate credibility.

### Personality

Question: What personality does the brand perform through tone, vocabulary,
behavior, and visual stance?

Use:

- Tone of voice.
- Repeated vocabulary.
- CTA style.
- Behavioral policies.
- Visual and interaction style if available.

Reject:

- Founder success story as personality unless the brand itself consistently
performs that archetype.
- Third-party headlines as primary personality evidence.

### Brand Idea

Question: What conceptual idea connects category, offer, expression, and
metaphor?

Use:

- Metaphors.
- Product/category reframing.
- Repeated conceptual contrast.
- Expression that turns the offer into a memorable idea.

Reject:

- One decorative phrase with no product/category connection.
- Absence just because the idea is not stated literally.

### Attributes

Question: Which attributes does the brand demonstrate consistently?

Use:

- Functional claims.
- Repeated product qualities.
- Evidence of behavior.
- Proof-backed descriptors.

Reject:

- Single generic adjectives.
- Values pretending to be attributes.

### Values

Question: What does the brand appear to value by what it says and does?

Use:

- Explicit values.
- Policies.
- Pricing behavior.
- Trust/security stances.
- Repeated beliefs.

Reject:

- "Innovation" as a default value unless supported by a clear belief or behavior.

### Mission

Question: What does the brand concretely do today?

Use:

- Present-tense operating language.
- "We build / provide / help / offer" statements.
- Product/service description.

Reject:

- Vision language.
- Blog articles.
- Market predictions.
- CTAs.
- Taglines without operating substance.

### Vision

Question: What future or category change does the brand appear to be building
toward?

Use:

- Future-facing language.
- Category-change claims.
- Founder/press statements if clearly about the company direction.
- "The future of..." only when connected to brand activity.

Reject:

- Roadmap links without content.
- Blog/news market predictions.
- Product description without future/category change.

## Case 1: base44.com

Source: production Magnetism scan #8, Brand Audit run #81.

### Current Problem

The scanner had useful evidence available:

- "Base44 is an AI app builder that lets anyone turn ideas into working apps in
  minutes."
- "Using just natural language, you can create tools, back-office apps, customer
  portals, or complete enterprise products that are ready to use."
- "our mission to help anyone create their own apps with zero hassle."

But it selected poor block evidence:

- Core Purpose: "Partner with Base44 to help students create and innovate."
- Value Proposition: "Our Mission, Your Vision top of page # About Us..."
- Personality: "Solo founder, $80M exit, 6 months..."
- Brand Idea: not detected.
- Vision: not detected.

### Ideal TLDR Reading

Core Purpose: democratize software creation by letting people turn ideas into
working apps without code, team, or technical setup.

Magnetism: "Think it. Prompt it. Launch it." or, if unavailable in the stored
evidence, "Built for builders, powered by possibility."

Value Proposition: Base44 lets builders, founders, and teams turn natural
language prompts into working apps, including tools, back-office apps, customer
portals, and enterprise products.

Personality: builder-first, empowering, fast, anti-friction, practical.

Brand Idea: software creation becomes a conversation; intent becomes working
software.

Attributes: fast, accessible, full-stack, conversational, practical.

Values: accessibility, autonomy, creative agency, speed, removing gatekeepers.

Mission: help anyone create their own apps with zero hassle.

Vision: move from buying or manually coding software to creating software from
intent. This needs entity/press/founder evidence and should be marked inferred
or declared depending on source.

### Failure Types

- `structural_noise_selected`: broken page chrome became value proposition.
- `secondary_program_promoted`: student partnership became core purpose.
- `proof_point_as_personality`: founder success story became personality.
- `concept_not_inferred`: brand idea was absent despite strong offer/category
  signals.
- `entity_context_not_promoted`: vision needs external or entity-level evidence.

### Benchmark Implications

- The Research Pack must classify page chrome, proof points, partnership
  snippets, and entity-level evidence before the Analyst Pass writes TLDR
  blocks.
- The Analyst Pass should rank owned product/about evidence above partnership
  or education snippets when answering core purpose and value proposition.
- Founder/media proof belongs in proof or credibility context unless the brand
  repeatedly performs that stance.
- Brand Idea should be synthesized from product, category, and metaphor when
  evidence is strong, marked inferred, and reviewable.
- Entity-level evidence may inform Vision only when the source clearly describes
  brand direction.

## Case 2: bokeroon.com

Source: production Magnetism scan #7, Brand Audit run #80.

### Current Strength

The scanner correctly improved mission and value proposition compared with
earlier noisy runs:

- "En Bokeroon estamos creado una plataforma que convierte la gestión cripto en
  una experiencia instantánea y transparente."
- "Menos complicaciones, más claridad."

It also rejected a noisy vision candidate from feed/article content.

### Remaining Problem

Core Purpose still uses a question as if it were purpose:

- "¿Listo para simplificar tus inversiones en criptomonedas?"

This is better treated as a magnetic prompt or value proposition support, not
core purpose.

Attributes are absent even though there is evidence for:

- rapidez
- eficiencia
- claridad
- simplicidad
- transparencia

### Ideal TLDR Reading

Core Purpose: make crypto investing easier to understand and manage for users
who feel overwhelmed by complexity. Claim type should be inferred, medium.

Magnetism: "Menos complicaciones, más claridad."

Value Proposition: Bokeroon is building a platform that turns crypto management
into an instant, transparent, and simpler experience.

Personality: urgent, encouraging, challenger-like, educational.

Brand Idea: crypto management without opacity. This is weak and should probably
be `needs_human_review`.

Attributes: clear, fast, transparent, simple.

Values: clarity, accessibility, practical control.

Mission: build a platform that makes crypto management instant and transparent.

Vision: not detected from current evidence. Feed/article market predictions
should stay rejected.

### Failure Types

- `rhetorical_question_as_purpose`.
- `attributes_under_extracted`.
- `brand_idea_weak_but_not_absent`: the idea exists as a weak hypothesis, not a
  confident block.

### Benchmark Implications

- The Analyst Pass should treat rhetorical questions as supporting evidence,
  not as standalone purpose.
- Product adjectives repeated across offer, mission, and value evidence should
  be available to Attributes through the Research Pack.
- Brand Idea may need a weak, reviewable hypothesis state instead of binary
  absent/present.

## Case 3: fly.io

Source: local Magnetism scan #40, Brand Audit run #142.

### Current Strength

The strategist pass produces a much closer reading:

- Value Proposition: public cloud of hardware-isolated micro-VMs for developers
  and security engineers.
- Mission: deploy and run code in secure sandboxes.
- Personality: bold, technical, playful, anti-corporate.
- Values: fairness, transparency, developer empathy.

### Ideal TLDR Reading

Core Purpose: get infrastructure out of developers' way so they can ship.

Magnetism: "Build fast. Run any code fearlessly."

Value Proposition: Fly.io gives developers a public cloud for running apps and
untrusted code in fast, hardware-isolated machines without infrastructure
complexity.

Personality: technical, playful, dev-native, irreverent.

Brand Idea: infrastructure as an invisible superpower.

Attributes: developer-first, secure, fast, pragmatic.

Values: fairness, transparency, developer empathy.

Mission: run apps and code on globally distributed, hardware-isolated compute.

Vision: not detected unless external/founder evidence states a category-change
ambition.

### Failure Types

- Mostly solved by strategist pass.
- Remaining risk: overclaiming Brand Idea from metaphorical copy.

### Benchmark Implications

- This is a good target shape for the app.
- It suggests the scanner improves when an Analyst Pass synthesizes across
  Research Pack evidence groups instead of selecting one sentence per block.

## Case 4: every.to

Source: local Magnetism scan #41, Brand Audit run #135.

### Current Strength

The scanner captures a coherent entity reading:

- Every publishes newsletters, builds software, offers courses, and provides AI
  consulting/training.
- The brand revolves around "what comes next."
- Vision is detected as collaboratively creating new technologies and businesses.

### Ideal TLDR Reading

Core Purpose: help people think about what comes next in technology and turn
those ideas into new technologies and businesses.

Magnetism: "What comes next?"

Value Proposition: Every gives founders, operators, investors, and AI-native
professionals editorial insight, products, courses, and consulting to stay at
the edge of AI.

Personality: thoughtful, curious, collaborative, non-dogmatic.

Brand Idea: an editorial and product studio for thinking at the edge of AI.

Attributes: AI-native, practical, editorial.

Values: curiosity, usefulness, intellectual independence, experimentation.

Mission: publish, build, teach, and consult around emerging technology and AI.

Vision: help people ask and answer what comes next so new technologies and
businesses can emerge.

### Failure Types

- Good overall.
- Values may be too thin if the scanner only extracts "inspiration."

### Benchmark Implications

- Multi-surface brands need entity architecture: publication + software +
  services, not just homepage offer.
- Values should come from repeated editorial stance, not only explicit value
  words.

## Case 5: lab.naturaumana.ai / tinyNature

Source: local Magnetism scan #39, Brand Audit run #148.

### Current Strength

The strategist pass improved the reading substantially compared with the raw
scanner:

- Value Proposition: personal AI assistant / command center for orchestrating
  tasks across life domains.
- Mission: build personal AI agents and platforms for personalized, always-on
  AI companions.
- Brand Idea: centralized command center with specialized sub-agents.

### Remaining Problem

The product surface alone is too narrow. A manual analyst naturally expands to:

- parent brand: naturaumana.ai
- mission page
- NatureOS
- privacy policy

Without that entity expansion, the scanner underreads purpose and vision.

### Ideal TLDR Reading

Core Purpose: make personal AI feel more human, useful, and integrated into
daily life. Needs parent/entity evidence.

Magnetism: "Life orchestration, perfected by nature."

Value Proposition: tinyNature acts as a personal AI assistant and command center
that coordinates specialized agents across daily tasks and connected tools.

Personality: personal, calm, always-available, companion-like.

Brand Idea: life orchestration through a nature-inspired AI operating layer.

Attributes: private, orchestrated, agentic, personal.

Values: privacy, usefulness, personalization, calm intelligence.

Mission: build AI assistants/agents that help people coordinate daily life.

Vision: unclear from product surface alone; likely needs parent brand research.

### Failure Types

- `audited_surface_too_narrow`.
- `parent_entity_not_expanded`.
- `product_surface_used_as_full_brand`.

### Benchmark Implications

- The Research Pack needs entity expansion before TLDR for subdomains, product
  microsites, and labs.
- The Analyst Pass should know whether it is analyzing a brand, product,
  sub-brand, campaign, or content surface before writing claims.

## Cross-Case Findings

### 1. The scanner often has enough evidence, but selects the wrong evidence

Base44 is the clearest example. The page includes useful value proposition and
mission evidence, but the TLDR block selected structural noise.

### 2. Proof points must not become brand meaning

Founder exit stories, migration launches, and case articles can support
credibility, but should not define personality, mission, or values unless the
brand repeatedly performs that stance.

### 3. Entity expansion is not optional

For Natura/tinyNature and Base44, the best TLDR requires knowing whether the
input URL is:

- company
- product
- subdomain
- campaign
- content page
- press/article

### 4. Brand Idea cannot be purely literal

If Brand Idea waits for a literal statement, it will miss the most useful
strategic synthesis. It should be allowed to infer when product, category, and
metaphor align, but must mark `inferred` and often `needs_human_review`.

### 5. The strategist pass is directionally correct

Fly and Every show that the optional strategist pass is closer to the desired
result than the raw block interpreter output. The next step is not more
hardcoded rules. It is better evidence ranking plus controlled synthesis.

## Error Taxonomy

- `structural_noise_selected`: page chrome or broken fragments selected as answer.
- `secondary_program_promoted`: partnership/education/campaign evidence promoted
  to central brand purpose.
- `proof_point_as_personality`: founder story, press, or third-party proof used
  as personality.
- `rhetorical_question_as_purpose`: CTA/question treated as core purpose.
- `concept_not_inferred`: Brand Idea absent despite enough conceptual evidence.
- `attributes_under_extracted`: repeated product adjectives not promoted.
- `entity_context_not_promoted`: external/entity evidence ignored for vision.
- `audited_surface_too_narrow`: product/subdomain analyzed as whole brand without
  parent context.
- `feed_or_article_noise`: blog/feed content treated as brand direction.

## Recommended Next Implementation Slice

Do not implement the following as scattered keyword lists inside block
interpreters. Implement them as Research Pack fields and Analyst Pass
instructions, then use this document as an evaluation fixture.

1. Add a `surface_role` field to the Research Pack:
   - company_home
   - product_surface
   - subdomain_product
   - about_page
   - content_article
   - campaign
   - press_external

2. Add evidence ranking fields by block:
   - Core Purpose: about/mission/company > repeated category belief > product.
   - Value Proposition: product/about offer > use cases > features > proof.
   - Personality: owned tone/voice > behavior/policy > founder story.
   - Brand Idea: product + category + metaphor > visual expression > tagline.
   - Vision: mission/about/founder/press category-change > roadmap > product.

3. Add evidence hygiene labels:
   - "top of page"
   - navigation fragments
   - malformed truncations
   - feed XML residue
   - "Roadmap" alone
   - unrelated blog market predictions

4. Add an Analyst Pass benchmark fixture using these cases:
   - Base44: rejects structural noise and detects Brand Idea.
   - Bokeroon: rejects feed vision and extracts attributes.
   - Fly: preserves strategist-quality synthesis.
   - Every: preserves multi-surface entity architecture.
   - Natura/tinyNature: marks parent/entity expansion need.

## Success Criteria

The scanner should not merely output valid TLDR v0.3 blocks. It should show that
each block answered the correct strategic question using the right class of
evidence.

For this benchmark, success means:

- Base44 value proposition never contains page chrome.
- Base44 Brand Idea is not absent.
- Base44 personality is not based primarily on founder exit proof.
- Bokeroon vision remains absent unless future/category evidence is brand-owned.
- Bokeroon attributes include clarity/simplicity/speed/transparency.
- Fly keeps the strategist-quality value proposition and personality.
- Every keeps publication + software + services as one entity architecture.
- Natura/tinyNature explicitly marks product-surface limitation and parent-entity
  expansion need.
