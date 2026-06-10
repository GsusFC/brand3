# Strategic Message Layer Benchmark

## Purpose

This benchmark validates whether the Strategic Message Layer can turn raw Brand3 signals, score state, evidence state, and TLDR Brand3 extraction into a clearer client-safe strategic reading without inventing unsupported brand meaning.

The benchmark does not ask whether the new text sounds better. It asks whether the new text explains the brand more accurately while preserving the truth of the underlying evidence.

## Working Definition

Strategic Message Layer:

> A score-aware explanation layer that converts detected signals, missing evidence, scoring tensions, and validation needs into a clear, useful, client-safe strategic reading.

It is not a replacement for scoring. It is not a replacement for TLDR Brand3 extraction. It is the interpretation layer between structured system output and human strategic action.

## Architecture Position

```text
Raw signals
→ TLDR Brand3 structured extraction
→ score + evidence state
→ Strategic Message Layer
→ client-safe strategic reading
→ optional human review / strategic action
```

## Evaluation Rule

Prompts may improve explanation, but they may not change the truth of the system.

If the evidence does not support a claim, the layer must describe the absence, weakness, inference, or validation need. It must not fill the gap with invented purpose, values, personality, vision, proof, or market positioning.

## Global Evaluation Questions

For every case, evaluate:

1. Does the output explain the brand better than the current TLDR without becoming more speculative?
2. Does it distinguish evidence from inference?
3. Does it turn absences into useful diagnosis?
4. Does it identify strategic tensions and opportunities?
5. Does it produce better client-facing validation questions?
6. Does it avoid inventing unsupported narrative?
7. Does it preserve score/evidence constraints?

## Pass / Fail Criteria

### Passes if

- It explains the strategic meaning of detected and missing signals.
- It separates functional clarity from brand maturity.
- It describes absent signals as absent from visible evidence.
- It marks inferred claims as inferred.
- It produces useful client-facing questions.
- It remains traceable to TLDR Brand3, score state, or evidence state.

### Fails if

- It invents purpose, values, personality, vision, audience, or market position.
- It turns weak evidence into confident positive claims.
- It hides evidence limitations.
- It contradicts the score or extraction state.
- It uses decorative strategy language without improving diagnosis.
- It treats “not detected” as a copywriting gap only, instead of a strategic/evidence gap.

---

# Case 001 — Blinka

## Case Metadata

- Brand: `blinka.co`
- Case ID: `strategic_message_layer_case_001_blinka`
- Case type: functional fintech / banking infrastructure with clear product utility but weak foundational brand narrative.
- Benchmark role: sparse functional brand audit.
- Primary evaluation risk: over-interpreting utility into unsupported brand meaning.

## Input State

The case should be evaluated using:

- current TLDR Brand3 output,
- scanner score state,
- evidence state,
- source/evidence limitations,
- Client TLDR v2 / Strategic Message Layer candidate output.

## Current TLDR Behavior

The current TLDR correctly detects available brand signals and marks several core sections as absent or unsupported.

Detected:

- Magnetism
- Value Proposition
- Attributes
- Mission

Not clearly detected:

- Core Purpose
- Personality
- Brand Idea
- Values
- Vision

## Strategic Problem

Blinka is not empty as a product, but it is under-articulated as a brand system.

It explains what the product does, but does not clearly explain:

- why the brand exists beyond infrastructure,
- what belief drives it,
- what distinctive point of view it owns,
- what personality makes it recognizable,
- what values shape its behavior,
- what future it wants to build.

The strategic gap is not simply “more copy needed.” The issue is that product utility is visible, while foundational brand meaning is not yet strongly evidenced.

## Expected Strategic Message Layer Contribution

The layer should improve the output by explaining the strategic meaning of each absence.

Instead of only saying:

```text
not detected
```

It should say something like:

```text
The brand clearly communicates product utility, but it does not yet articulate a larger reason for existing beyond infrastructure.
```

The output should make clear that Blinka has functional clarity but limited visible brand maturity.

## What Should Improve

- Absences become useful diagnosis.
- Functional clarity is separated from brand maturity.
- Product promise is distinguished from brand idea.
- Generic attributes are treated as weak unless made ownable.
- Vision is marked as peripheral, inferred, or unvalidated when evidence is insufficient.
- Client questions become strategic briefing prompts, not system-debug prompts.

## Forbidden Behavior

The layer must not invent Blinka’s:

- purpose,
- values,
- personality,
- vision,
- belief system,
- founder intent,
- customer promise beyond evidence,
- cultural or category point of view.

It may only explain that those elements are absent, weak, inferred, or require validation.

## Example Acceptable Interpretation

```text
Blinka reads as a useful banking infrastructure product with a clear operational promise, but the visible evidence does not yet show a larger brand idea or distinctive worldview. The brand can explain what it enables, but it has not yet made clear why this should matter as a brand beyond utility and access.
```

## Example Unacceptable Interpretation

```text
Blinka exists to democratize global financial access for a new generation of borderless entrepreneurs.
```

Reason: this may be plausible, but it is unsupported unless directly evidenced by the brand’s own material.

## Client Value

The client should understand the real issue:

Blinka does not need “more copy” first. It needs sharper strategic articulation around purpose, personality, brand idea, values, and vision, backed by evidence the brand can actually sustain.

## Case-Specific Pass / Fail

### Passes if

- It distinguishes utility from brand maturity.
- It explains absent blocks as absent from visible evidence.
- It avoids treating missing purpose/personality/vision as proof that the brand is bad.
- It produces validation questions suitable for briefing or workshop use.
- It keeps the diagnosis grounded in current evidence.

### Fails if

- It invents a higher-order purpose for Blinka.
- It presents financial access, democratization, trust, empowerment, or borderless entrepreneurship as brand truth without evidence.
- It turns generic fintech attributes into distinctive values.
- It claims a clear vision where the evidence only shows product utility.
- It rewrites the brand more than it diagnoses it.

## Benchmark Decision

Keep as a strong first benchmark case.

Reason:

Blinka clearly tests whether the Strategic Message Layer can turn a sparse, functional brand audit into a useful strategic reading without inventing unsupported meaning.

---

# Case 002 — Factorial

## Case Metadata

- Brand: `Factorial`
- Case ID: `strategic_message_layer_case_002_factorial`
- Case type: strong HR / business management software brand with a clear message, but inference-sensitive strategic depth.
- Benchmark role: strong but inference-sensitive brand.
- Primary evaluation risk: over-converting plausible strategic readings into validated brand truth.

## Input State

The case should be evaluated using:

- current TLDR Brand3 output,
- scanner score state,
- evidence state,
- confidence labels,
- human-review flags,
- Client TLDR v2 / Strategic Message Layer candidate output.

Relevant scan state:

- Magnetism: `77/100` — memorable.
- Coherence: `83/100` — aligned.
- Strategic tension: high originality, but lower specificity.
- Structural tension: strong completion, but only moderate semantic alignment.

This is not a Blinka-style case where the brand is under-written. Factorial is already articulated and legible. The benchmark question is whether the Strategic Message Layer can explain a strong brand while preserving visible inference and confidence limits.

## Current TLDR Behavior

The current TLDR detects a coherent brand direction around:

- people over paperwork,
- administrative time savings,
- HR and business process automation,
- AI-supported operations,
- a more human-centered reading of HR technology.

However, several strategic blocks remain inferential or require human review. The current extraction can identify the likely direction, but it should not treat every strategic reading as fully validated brand doctrine.

## Strategic Problem

Factorial has a clear and effective narrative: reduce paperwork so companies can focus more on people.

That narrative works because it connects the product to a real category tension in HR:

- managing processes,
- protecting time,
- supporting teams,
- making HR feel less administrative and more human.

The strategic risk is not absence. The risk is low specificity. “Simplify HR,” “save time,” “automate admin,” and “focus on people” are strong but familiar SaaS/HR-tech claims unless Factorial makes them more ownable through sharper proof, tone, product experience, and category point of view.

## Expected Strategic Message Layer Contribution

The layer should explain both the strength and the risk.

It should not primarily fill gaps. It should clarify:

- where Factorial is already strong,
- where the brand idea is inferred,
- where evidence supports the reading,
- where the reading needs human validation,
- where the strategy needs more specificity to become distinctive.

The correct tone is not “this brand is missing.” The correct tone is:

```text
Factorial already communicates a clear and useful HR-tech promise. The opportunity is to make the strategic idea more ownable: not only less paperwork, but a more specific point of view about how modern companies should use AI, operations, and people systems to free human capacity.
```

## Block-Level Strategic Reading

### Core Purpose

Factorial articulates a recognizable purpose: freeing administrative time so companies can focus more on people.

Strategically, this works because it connects directly with a real HR category tension: the distance between managing processes and caring for teams. The layer may present this as a plausible strategic reading, but if the extraction marks it as inferred or low-confidence, it must remain framed as inferred rather than as a fully validated foundational declaration.

### Magnetism

Factorial’s magnetism concentrates around a clear tension:

```text
Focus on people, not paperwork.
```

This is stronger than a purely functional software promise because it reframes the product as relief from operational burden. The opportunity is to make the tension more ownable and less generic inside HR tech.

### Value Proposition

The value proposition is mature and well supported:

- HR and business management software,
- AI-supported process simplification,
- time savings,
- cost reduction,
- centralization of operational workflows.

The strategic reading should say that Factorial knows what it sells and what benefit it produces. The risk is not comprehension. The risk is similarity to other HR platforms unless Factorial specifies what only it can credibly own.

### Personality

The personality appears accessible, helpful, conversational, and people-oriented.

This is coherent with the “make HR more human” territory. The guardrail is that the personality may still be derived from interface tone and product messaging rather than from a complete verbal identity system. The layer should mark this as directionally visible, not fully proven across all surfaces.

### Brand Idea

The strongest inferred brand idea is:

```text
Use AI to absorb administrative work so HR can become more human again.
```

This is strategically promising because it connects product, category tension, and emotional consequence. But if the system marks it as inferred or requiring review, the layer must not present it as an official claim or closed brand idea.

### Attributes

Visible attributes:

- automated,
- simplifying,
- people-centered,
- AI-supported,
- operationally useful.

The layer should note that automation and simplification are expected SaaS attributes. The more differentiating attribute is people-centeredness, but only if Factorial can sustain it through product experience, proof, tone, and customer evidence.

### Values

The most visible value is human time: giving people more time to grow and focus on higher-value work.

This is stronger than pure efficiency because it turns operational savings into human value. The opportunity is to develop this into a clearer value system around work, people, management, AI, and company operations.

### Mission

The operational mission is clear:

- automate HR administrative tasks,
- centralize HR and business processes,
- support payroll, reports, talent, and management workflows,
- use AI to reduce operational load.

The strategic opportunity is to elevate this from operational mission to broader transformation: not only better HR management, but freeing human capacity through intelligent systems.

### Vision

The vision points toward integrated AI-assisted business operations, potentially through product signals such as an AI agent layer.

This suggests a direction from HR software toward an intelligent operational layer for companies. The layer must stay cautious: if this vision is inferred from product signals, it should be presented as an emerging direction, not as a declared manifesto.

## What Should Improve

- Strengths are explained without flattening them into generic praise.
- Inferred strategic ideas remain labeled as inferred.
- Human-review needs remain visible.
- The reading distinguishes product clarity from brand specificity.
- High scores are translated into meaningful strategic consequences.
- The output explains why a strong brand may still need sharper ownability.

## Forbidden Behavior

The layer must not:

- treat inferred purpose as declared purpose,
- treat “people over paperwork” as fully ownable without competitive context,
- claim Factorial has a complete value system if only one value is visible,
- claim a declared AI-agent vision if the evidence only shows product direction,
- hide low-confidence or human-review flags,
- inflate “automation” and “simplification” into differentiating attributes without proof.

## Example Acceptable Interpretation

```text
Factorial already has a strong and legible strategic territory: reducing administrative drag so companies can focus more on people. The reading is credible, but some of its higher-order brand meaning remains inferred. The opportunity is to make the idea more ownable: not just HR automation, but a specific belief about how AI and operations should create more human capacity inside modern companies.
```

## Example Unacceptable Interpretation

```text
Factorial exists to redefine the future of work by making every company more human through autonomous AI operations.
```

Reason: this may extrapolate from product direction, but it overstates vision and purpose unless the evidence explicitly supports it.

## Client Value

The client should understand that Factorial is not weak or under-written.

The real issue is sharper strategic specificity:

- what Factorial can own beyond HR simplification,
- how “people over paperwork” becomes distinctive,
- how AI changes the brand idea rather than just the product feature set,
- which inferred readings should be validated by leadership, product, proof, or customer evidence.

## Case-Specific Pass / Fail

### Passes if

- It explains why Factorial is already strategically legible.
- It preserves inference labels and human-review needs.
- It distinguishes clear value proposition from ownable brand idea.
- It identifies specificity as the main strategic improvement area.
- It translates high magnetism/coherence into client-useful interpretation.
- It asks validation questions about purpose, AI point of view, values, personality, and proof.

### Fails if

- It treats all plausible strategic readings as validated truth.
- It invents a complete purpose, values system, or long-term vision.
- It hides low-confidence or review-required signals.
- It praises the brand generically without identifying the specificity risk.
- It frames the case as a missing-brand problem like Blinka.
- It rewrites Factorial more than it diagnoses Factorial.

## Benchmark Decision

Keep as Case 002.

Reason:

Factorial tests a different benchmark behavior than Blinka. Blinka tests how to explain functional brands with absent foundational blocks. Factorial tests how to explain a strong brand without overinterpreting inference-sensitive strategic readings.

---

## Next Benchmark Cases Needed

Add 6–10 more cases that stress different failure modes:

- strong brand with clear narrative and evidence,
- product with strong utility but no brand system,
- brand with heavy storytelling but weak proof,
- web3 brand with over-narrativized language,
- non-web3 commodity SaaS,
- ecommerce brand with generic positioning,
- visually strong brand with weak message,
- FLOC* case with strategic nuance,
- startup AI commodity with category sameness,
- brand with high score but low narrative specificity,
- brand with low score but one distinctive strategic signal.
