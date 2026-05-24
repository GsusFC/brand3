# Brand3 Perceptual Narrative Evaluation

Generated: 2026-05-15
Status: evaluation pass
Scope: `experimental_perceptual_narrative` only

## Purpose

This pass evaluates whether the experimental perceptual reasoning layer improves Brand3 findings prose versus the current baseline narrative system.

This is not scoring logic, not runtime rollout, not report rendering, not Visual Signature integration, and not a schema change. The paired examples below are controlled editorial evaluation fixtures: they compare the expected behavior of the current findings prompt with the same prompt when perceptual hints are injected.

## Method

Inputs reviewed:

- `src/reports/experimental_perceptual_narrative.py`
- `src/reports/narrative.py`
- `examples/perceptual_library/patterns/perceptual_reading_semantics.*`
- `examples/perceptual_library/patterns/perceptual_pattern_registry.*`
- existing report narrative tests and snapshots

Evaluation criteria:

- specificity
- perceptual richness
- observational grounding
- tension quality
- emotional temperature accuracy
- reduction of generic LLM prose
- reduction of score-first writing
- overreach risk
- narrative coherence
- repetition
- "feels Brand3/FLOC*" confidence

Important limitation: these are not live brand audits. They are paired narrative specimens designed to test whether the experimental hint layer changes the writing behavior in the desired direction.

## Overall Finding

The perceptual augmentation improves findings when the evidence pool contains observable surface behavior or a clear claim/signal gap. It pushes prose away from score-first summary and toward surface mechanisms: density, pacing, system behavior, claim boundaries, movement, and contradiction.

The main risk is over-interpretation. If the evidence is thin, the augmented version can sound more intelligent than the evidence allows. The layer is strongest when it names limits explicitly; it is weakest when it turns pattern language into a style overlay.

Recommendation: keep the experiment off by default. Continue with opt-in evaluation and add a stricter acceptance gate before any production rollout.

## Paired Examples

### Apple

**Baseline excerpt**

Apple's public surface presents a highly polished product ecosystem with clear hierarchy, premium imagery, and consistent communication across devices and services. This supports a strong perception of coherence and reinforces the brand's leadership position in consumer technology.

**Perceptual-augmented excerpt**

Apple's owned surface repeatedly organizes attention around product object, material finish, controlled whitespace, and short declarative copy. That supports a high-confidence observation of product-first hierarchy; the broader reading of institutional authority remains an interpretation, not a directly visible fact. The productive tension sits between restraint and commercial density: the surface often feels minimal at the frame level while carrying many simultaneous product, ecosystem, and service signals.

**Evaluation**

- Helps: replaces generic "polished", "premium", and "leadership" language with observable surface behavior.
- Harms: still risks importing reputation knowledge unless the evidence pool contains the specific pages.
- Overreach watch: "institutional authority" must remain interpretive.
- Brand3/FLOC* confidence: high if screenshots or owned-page evidence are present; medium without captures.

### Linear

**Baseline excerpt**

Linear presents a modern, focused SaaS experience with strong product clarity and a well-defined workflow narrative. The brand appears differentiated through a refined interface language and a clear emphasis on speed, collaboration, and execution.

**Perceptual-augmented excerpt**

Linear's available surface evidence points to product-navigation language, compact UI claims, and a controlled software-workflow frame. That supports a reading of guided movement rather than broad "modern SaaS" positioning: the surface directs attention through workflow, sequence, and operational rhythm. The claim/signal gap matters because some visual evidence is obstructed or screenshot-limited, so interface clarity should be written as a copy-supported reading until direct product-surface evidence confirms it.

**Evaluation**

- Helps: converts generic SaaS praise into guided movement and evidence limitation.
- Harms: can sound cautious even when the brand is well-known and mature.
- Overreach watch: do not assert UX clarity from marketing copy alone.
- Brand3/FLOC* confidence: medium-high because the limitation is explicit.

### Stripe Docs

**Baseline excerpt**

Stripe's documentation experience is robust and developer-friendly, with a comprehensive information architecture that supports onboarding and technical implementation. The brand demonstrates strong coherence between product complexity and developer trust.

**Perceptual-augmented excerpt**

Stripe Docs' surface is best read through operational density: navigation, code-oriented content, and implementation pathways make the category legible through use rather than campaign language. That supports a category-to-surface reading with a system-driven emotional temperature: controlled, dense, and instructional. The tension is not whether the brand is "developer-friendly" as a quality claim, but how much complexity the surface can expose while still guiding action.

**Evaluation**

- Helps: removes "robust", "comprehensive", and trust-as-fact language.
- Harms: "operational density" may become reusable jargon if not tied to visible navigation or code evidence.
- Overreach watch: do not infer developer trust without behavioral or third-party evidence.
- Brand3/FLOC* confidence: high when docs structure is included in evidence.

### Headspace

**Baseline excerpt**

Headspace communicates a calm and accessible wellness brand through friendly visuals, approachable messaging, and a reassuring tone. The experience feels warm and supportive, helping users engage with meditation and mental health.

**Perceptual-augmented excerpt**

Headspace's surface evidence should separate stated wellness positioning from directly observed interface behavior. Soft color, simple hierarchy, and friendly illustration can support a low-to-medium confidence emotional temperature of calm accessibility, but "supportive mental-health experience" is an interpretation unless product-flow evidence is available. The useful tension is between emotional reassurance and proof of actual guidance: the surface may invite comfort while the evidence pool still needs interaction-level confirmation.

**Evaluation**

- Helps: sharply distinguishes emotional surface from product efficacy.
- Harms: can make a wellness reading feel overly procedural if the prose loses warmth.
- Overreach watch: mental-health support claims require especially careful wording.
- Brand3/FLOC* confidence: medium because emotional temperature is plausible but must stay evidence-bound.

### Notion

**Baseline excerpt**

Notion has a cohesive productivity ecosystem with a flexible workspace narrative that appeals to teams and individuals. Its brand system is simple, recognizable, and effective at communicating versatility.

**Perceptual-augmented excerpt**

Notion's surface can be read as system cohesion with preserved difference when the evidence shows modular workspace language, template variety, and repeated block-based framing. The stronger observation is not that the ecosystem is "cohesive", but that many use cases are held inside a shared workspace grammar. The tension sits between flexibility and legibility: the surface needs to show breadth without making the product feel like an undefined container.

**Evaluation**

- Helps: replaces high-level productivity praise with a reusable perceptual pattern.
- Harms: "workspace grammar" is useful but needs evidence from templates, navigation, or product surfaces.
- Overreach watch: do not claim actual team adoption or workflow success from brand copy.
- Brand3/FLOC* confidence: medium-high with product or template evidence; medium from homepage copy only.

### Example Company

**Baseline excerpt**

Example Company has a basic online presence with limited differentiation and generic messaging. The brand appears weak across presence and vitality, with little evidence of a distinctive market position.

**Perceptual-augmented excerpt**

Example Company's evidence pool appears thin and mostly self-referential, so the safest finding is an evidence-bound absence rather than a personality claim. The surface does not yet provide enough repeated signals to support a stable perceptual pattern. The narrative should name the limitation directly: Brand3 can observe low surface specificity and weak corroboration, but should not infer strategic failure or audience irrelevance from missing evidence alone.

**Evaluation**

- Helps: prevents weak-brand prose from becoming punitive or score-first.
- Harms: produces less dramatic language, which may feel less decisive.
- Overreach watch: absence of evidence is not evidence of failed strategy.
- Brand3/FLOC* confidence: high as a methodological example; low as a brand interpretation.

## Cross-Case Assessment

### Where augmentation helps

- It consistently reduces generic praise: "strong", "premium", "modern", "cohesive", "robust", and "leader" are replaced by surface behavior.
- It makes tensions more useful by naming both sides: restraint/density, guidance/intensity, flexibility/legibility, claim/evidence.
- It improves confidence handling by keeping copy-supported claims below direct visual observations.
- It keeps weak evidence from becoming a verdict.

### Where augmentation harms

- It can introduce a new form of abstraction if pattern names are used without evidence anchors.
- It may over-cautiously qualify well-supported brands when the evidence pool is sparse.
- Emotional temperature language can still become generic if not tied to pacing, density, hierarchy, color, motion, or interaction.
- The static adapter currently supplies general perceptual lenses, not brand-specific perceptual facts.

### Where baseline still performs better

- Baseline is shorter and easier to scan.
- Baseline can be adequate when the evidence is already concrete and the finding only needs summary.
- Baseline avoids the risk of importing registry vocabulary into every brand.

### Where augmented prose becomes too interpretive

- When it describes authority, trust, support, calm, or sophistication without a visible mechanism.
- When it treats category-to-surface translation as proof of strategy.
- When it uses emotional temperature as a quality judgment rather than a surface read.

## Recommendation Before Rollout

Do not roll out globally.

Recommended next steps:

1. Keep `enable_perceptual_narrative=False` by default.
2. Add an evaluation harness that stores baseline and augmented findings for the same evidence bundle.
3. Add lint-style checks for forbidden generic sophistication language.
4. Require every augmented finding to include one visible or source-level mechanism.
5. Require low-confidence phrases to remain conditional.
6. Add a reviewer rubric for "pattern vocabulary used without evidence".
7. Only consider production use after a larger paired corpus shows consistent gains without higher overreach risk.

## Decision

The experiment is promising but not rollout-ready. It improves Brand3's perceptual grammar most clearly in findings that already contain evidence anchors. The layer should remain an opt-in narrative augmentation experiment until paired real-report evaluations show that specificity improves without increasing invented intentionality.
