# Brand3 Prism Deep Research Evidence Packet Trial: Watermelon

## Purpose

This trial tested a stricter replacement question than the earlier Builtwith runs:

Can Gemini Deep Research start from one audit URL and classify evidence through the Brand3 methodology prism before Brand3 writes findings?

Target URL: `https://watermelon.sh`

This was not a report-generation trial. Deep Research was asked only to acquire and classify evidence.

## Scope

Mode:

- one interaction only
- single audit URL only
- no seed URLs
- no previous Brand3 evidence
- Google Search allowed
- URL context allowed
- no Deep Research Max
- no Brand Audit findings
- no scoring
- no recommendations
- no report prose

Artifacts:

- `examples/reports/deep_research_trial/watermelon_prism/request.json`
- `examples/reports/deep_research_trial/watermelon_prism/raw_interaction.json`
- `examples/reports/deep_research_trial/watermelon_prism/evidence_packet.json`
- `examples/reports/deep_research_trial/watermelon_prism/cost_observation.json`
- `examples/reports/deep_research_trial/watermelon_prism/trial_notes.md`

## Execution Summary

The interaction completed, but it did not return the requested structured JSON evidence packet.

Instead, it returned a long narrative audit with:

- entity resolution prose
- Brand3 dimension analysis prose
- source list
- strong interpretive conclusions
- strategic/positioning language despite the explicit instruction not to write report prose

The script therefore recorded:

`completed_but_no_parseable_evidence_packet`

Observed usage:

- total input tokens: `407,940`
- total output tokens: `17,095`
- total thought tokens: `31,452`
- total tool-use tokens: `269,051`
- total tokens: `725,538`
- cached tokens: `69,632`
- Google Search: enabled through default Deep Research tools
- seed URLs: not provided
- previous Brand3 evidence: not provided

Estimated cost:

- approximate model cost: `USD 2.505606`
- basis: Gemini 3.1 Pro Preview standard long-context rates, counting thought tokens as output
- Google Search charge: excluded from estimate

## Contract Compliance

| Contract requirement | Result |
|---|---|
| Single URL only | Passed |
| No seed URLs | Passed |
| No previous Brand3 evidence | Passed |
| Google Search allowed | Passed |
| URL context allowed | Passed |
| No Deep Research Max | Passed |
| Return structured evidence packet only | Failed |
| Prefer valid JSON | Failed |
| Do not generate Brand Audit findings | Failed in spirit |
| Do not recommend strategy | Partially failed |
| Do not write report prose | Failed |
| Cite evidence | Partially passed, but citations were prose/source-list citations rather than packet fields |
| Classify finding eligibility | Failed as structured output |

This is the core result of the trial: Deep Research improved discovery and entity separation, but did not obey the evidence-packet contract under this prompt.

## What It Found

The raw output appeared to identify:

- `watermelon.sh` as a React UI/component registry.
- a claimed relation to `WatermelonCorp` on GitHub.
- a claimed relation to `Watermelon Studio` / `studio.watermelon.sh`.
- unrelated Watermelon AI/customer-service surfaces as separate entities.
- unrelated consumer/product noise such as cannabis, fishing equipment, and apparel.
- possible Product Hunt, directory, GitHub, and developer-community presence.

This is materially better discovery than the old Brand3 Watermelon payload, which mixed several Watermelon surfaces and let ecosystem ambiguity leak into findings.

However, the output also made strong interpretive claims:

- "exceptionally high coherence"
- "highly favorable external perception"
- "stark differentiation"
- "robust signals of high vitality"
- "commercial parent entity"
- "strategic deployment"

Those phrases are analysis, not evidence classification. They are exactly the kind of conclusion Brand3 should generate only after evidence eligibility is settled.

## Comparison With Current Brand3 Watermelon Behavior

Current Brand3 Watermelon behavior, based on the prior Phase 2 work, had the opposite problem:

- It collected a broad pool of Watermelon-related surfaces.
- It mixed audited-domain claims, GitHub references, adjacent domains, Product Hunt, software listings, and unrelated Watermelon references.
- It made ecosystem ambiguity sound more coherent than the evidence supported.
- It repeated caveats and safe attribution language.
- It did not classify evidence eligibility before narrative generation.

Deep Research did better at discovery and entity separation. It recognized that similarly named Watermelon surfaces and unrelated products need filtering.

But it also reproduced the same deeper failure in a different form: it turned evidence into confident narrative before returning a clean evidence contract.

## Comparison With Local Evidence Packet v0 Expectations

The local Evidence Packet v0 direction is deliberately stricter:

- owned claims remain owned claims
- same-name surfaces are not aliases
- related surfaces require review
- technical signals do not become narrative findings
- marketplace/listing evidence does not imply traction
- evidence eligibility is computed before prose
- no LLM is needed for deterministic packet building

The Watermelon Deep Research raw output supports these categories conceptually, but it did not produce them as structured data.

The normalized `evidence_packet.json` for this trial is therefore marked as:

`unstructured_model_output_not_parseable_as_requested_packet`

It should not be treated as a valid packet for generation.

## Evidence Quality By Dimension

### Coherencia

Useful signal:

- The audited surface likely has a clear product identity around a UI/component registry.

Risk:

- The raw output overstates coherence before structured source verification.
- The claimed link between audited surface, GitHub organization, and studio surface needs review.

### Presencia

Useful signal:

- Deep Research found possible GitHub, Product Hunt, directory, and developer-resource presence.

Risk:

- It did not cleanly separate controlled presence from third-party indexing.
- It risked treating presence surfaces as a coherent ecosystem.

### Percepcion

Useful signal:

- It found possible third-party editorial/curatorial commentary.

Risk:

- It turned perception into positive assessment too quickly.
- The output needs quote-level evidence before any finding.

### Diferenciacion

Useful signal:

- Copy-paste registry architecture, component scale, modern stack, and TypeScript/animation choices may be differentiators.

Risk:

- Differentiation claims need source-bound proof and should not become strategic superiority language by default.

### Vitalidad

Useful signal:

- It found possible recent launch, curation, and repository/governance signals.

Risk:

- It inferred high momentum from surfaces that may only prove publication, indexing, or repository maturity.

## Cost Assessment

This trial was expensive:

- `725,538` total tokens
- `269,051` tool-use tokens
- estimated model cost `USD 2.505606`
- search charges not included

The cost is higher than the Builtwith single-URL trial and much higher than the seeded URL-context trial.

More importantly, the output was not contract-safe. Paying this cost for unstructured prose is not acceptable for default runtime use.

## Root Finding

The Watermelon prism trial shows that Deep Research can discover useful entity and source-separation material from a single URL.

It also shows that, without a harder structured-output interface, Deep Research can collapse back into exactly the behavior Brand3 is trying to avoid:

evidence acquisition becomes narrative interpretation too early.

That means Deep Research is not a clean drop-in replacement for Brand3 acquisition.

Its best role remains:

- manual/lab escalation
- benchmark for entity discovery
- source-discovery comparator
- evidence-contract design reference

It should not become the default evidence packet generator unless output structure can be enforced and cost controlled.

## Recommended Next Step

Do not run more Deep Research trials immediately.

The next practical step is to implement or harden the local Evidence Packet v0 around the existing Exa/Web pipeline, using this trial as a warning:

- discovery quality matters
- entity separation matters
- source quality matters
- but classification must happen before narrative
- and structured output must be enforced before any generation step

If Deep Research is tested again, the prompt should be narrower and should probably use a schema/strict JSON mechanism if the Interactions API supports one. Otherwise it will keep being a costly analyst, not a reliable packet compiler.

## Non-Goals Preserved

- No Brand3 production collector changes.
- No scoring changes.
- No prompt rollout.
- No report generation changes.
- No rendering changes.
- No persisted payload format changes.
- No Visual Signature changes.
- No runtime integration.
- No repeated Deep Research tasks.
- No Deep Research Max.
