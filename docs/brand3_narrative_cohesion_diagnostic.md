# Brand3 Narrative Cohesion Diagnostic

Date: 2026-05-16

Scope: diagnostic only. No scoring, runtime, prompt, renderer, schema, or Visual Signature changes were made.

## Executive Finding

The current Brand3 report narrative is not simply suffering from weak tone. The code already contains meaningful prompt-level guardrails around evidence, echo-chamber risk, conditional inference, and closed evaluative adjectives. The deeper gap is architectural: Brand3 generates and assembles narrative at the dimension level, then adds a cross-dimension tension and synthesis, but it does not first build an explicit entity-level narrative state.

That means the report can be structurally valid, evidence-aware, and still read like adjacent LLM fragments. The system has evidence, scores, confidence, source grouping, and readiness policy, but no explicit consolidation layer that decides: what is the entity, what claims are supported, what contradictions matter most, what voice position should govern every section, and what repetitions should be rejected before rendering.

## Current Pipeline Map

1. Audit/scoring produces a run snapshot in storage.
   - The report system consumes snapshots shaped around `run`, `scores`, `features`, `annotations`, `raw_inputs`, and optional persisted evidence.
   - The dossier builder documents this as its source contract in `src/reports/derivation.py` via `build_report_base(...)`.

2. `build_report_base(...)` creates the deterministic base dossier.
   - File: `src/reports/derivation.py`
   - Function: `build_report_base(snapshot, theme="dark")`
   - It indexes features by dimension, parses raw feature payloads, extracts evidence, collects insights, confidence, coverage, readiness, trust summary, score display, sources, and deterministic fallback narrative.
   - Relevant locations:
     - dimension construction: `src/reports/derivation.py:329-409`
     - evidence/readiness/trust construction: `src/reports/derivation.py:411-439`
     - deterministic fallback synthesis: `src/reports/derivation.py:471-494`
     - final base object: `src/reports/derivation.py:509-568`

3. `build_brand_dossier(...)` applies narrative overlays.
   - File: `src/reports/dossier.py`
   - Function: `build_brand_dossier(...)`
   - It builds the base dossier, prefers persisted `report_narrative` when present, otherwise calls `_apply_narrative(...)`.
   - Relevant locations:
     - base + persisted narrative decision: `src/reports/dossier.py:40-70`
     - persisted payload format: `src/reports/dossier.py:73-106`
     - persisted overlay application: `src/reports/dossier.py:119-181`

4. `_apply_narrative(...)` generates findings, tensions, then synthesis.
   - File: `src/reports/dossier.py`
   - Function: `_apply_narrative(...)`
   - Order:
     - collect evidence with `collect_evidences(snapshot)`
     - group evidence by dimension with `group_by_dimension(...)`
     - generate per-dimension findings with `generate_all_findings(...)`
     - generate cross-dimension tension with `generate_tensions(...)`
     - generate synthesis with `generate_synthesis(...)`
   - Relevant locations: `src/reports/dossier.py:210-288`

5. Public reads prefer stored narrative and force deterministic fallback if no stored narrative exists.
   - During analysis, `brand_service.run(...)` persists `report_narrative` when an LLM exists:
     - `src/services/brand_service.py:2006-2022`
   - The public web route passes `_WebReportNarrativeFallback` to avoid LLM calls on public reads:
     - `web/routes/report.py:18-33`
     - `web/routes/report.py:89-93`
   - Therefore public report reads are intended to be stable and fast, not live LLM generation.

6. Rendering is presentation-only.
   - File: `src/reports/renderer.py`
   - `ReportRenderer.render(...)` calls `build_brand_dossier(...)` then renders `report.html.j2`.
   - Relevant location: `src/reports/renderer.py:68-82`
   - Template rendering points:
     - synthesis: `src/reports/templates/report.html.j2:792-798`
     - findings by dimension: `src/reports/templates/report.html.j2:801-824`
     - cross-dimension tensions: `src/reports/templates/report.html.j2:832-839`

## Observed Narrative Generation Points

The final report narrative is generated in `src/reports/narrative.py`, orchestrated by `src/reports/dossier.py`, and displayed by `src/reports/templates/report.html.j2`.

The narrative module declares three public entry points:

- `generate_synthesis(context)` for synthesis prose.
- `generate_dimension_findings(dim, brand)` for per-dimension findings.
- `generate_tensions(dimensions, brand)` for cross-dimension tension.

This is explicit in `src/reports/narrative.py:1-7`.

The main writing calls are:

- `generate_all_findings(...)` loops through dimensions and calls `generate_dimension_findings(...)`.
  - `src/reports/narrative.py:173-218`
- `generate_dimension_findings(...)` calls `_try_findings(...)`, which sends one dimension at a time to the LLM.
  - `src/reports/narrative.py:124-152`
  - `src/reports/narrative.py:567-641`
- `generate_tensions(...)` requests one cross-dimensional tension.
  - `src/reports/narrative.py:155-170`
- `generate_synthesis(...)` requests the synthesis paragraph after tensions are available.
  - `src/reports/narrative.py:108-121`

## Entity-Level Representation Check

The system does not currently build an explicit entity-level representation before writing.

What exists:

- A deterministic base dossier with brand metadata, dimensions, scores, evidence, confidence, readiness, trust summary, and sources.
- A `SynthesisContext` dataclass with brand, URL, composite score, dimension evidences, data quality, top evidences, analysis date, and optional tension text.
- A `Finding` dataclass that separates observation, implication, typical decision, and evidence URLs.

What does not exist:

- A consolidated entity model that identifies the core brand/entity read before findings are written.
- A claim inventory separating owned claims, third-party claims, observed behavior, and inferred interpretation.
- A contradiction priority model across dimensions and sources.
- A narrative state shared by findings, tension, and synthesis.
- A single editorial viewpoint object that governs all generated sections.
- A cohesion/repetition validator before persistence or rendering.

`SynthesisContext` is a useful input bundle, but it is not an entity-level narrative state. It is created after dimension findings and tension generation in `src/reports/dossier.py:271-280`, so it cannot guide the first generation pass of §4 findings.

## Explicit Layer Inventory

### Entity consolidation

Partial only.

`build_report_base(...)` consolidates the report view-model, but it is not a semantic entity consolidation layer. It groups features and evidence by dimension, not by entity-level claims, contradictions, or narrative priorities.

Evidence:

- dimension blocks are built directly from scores/features/evidence in `src/reports/derivation.py:345-409`
- narrative findings remain empty placeholders until the narrative overlay runs in `src/reports/derivation.py:406-407`

### Narrative state

Not explicit.

The closest object is `SynthesisContext` in `src/reports/narrative.py:80-91`, but it is only used for §1 synthesis. It is not passed into per-dimension findings and does not carry global repetition, contradiction, or voice constraints.

### Contradiction prioritization

Prompt-level only.

The findings prompt asks the LLM to dedicate a finding to contradiction if evidence contains one:

- `src/reports/narrative.py:554-556`

The tensions prompt asks for one significant cross-dimensional tension only if it exists:

- `src/reports/narrative.py:674-680` and following prompt text

But there is no deterministic contradiction inventory or prioritization before the LLM call.

### Evidence weighting

Partial only.

Evidence exists and is grouped, but narrative evidence weighting is minimal:

- `_pick_top_evidences(...)` maximizes source-type diversity among quoted evidence.
  - `src/reports/dossier.py:184-207`
- `_validate_urls(...)` rejects evidence URLs not present in the input evidence pool.
  - `src/reports/narrative.py:621-624` calls it, implementation at `src/reports/narrative.py:797-815`

This protects citation validity, but it does not rank claim strength, owned-vs-third-party risk, contradiction severity, or evidence-to-claim fit.

### Editorial viewpoint

Prompt-level and policy-level, but not stateful.

There is an editorial policy helper:

- `src/reports/editorial_policy.py:1-5`
- report modes and dimension states: `src/reports/editorial_policy.py:12-82`
- evidence language hints: `src/reports/editorial_policy.py:84-135`

However, the file explicitly says these helpers do not change narrative generation, rendering, prompts, or storage. They are exposed into the report context by `build_report_context_from_base(...)`, but they do not control the LLM writing pass.

Prompt-level editorial discipline exists in `src/reports/narrative.py`, especially:

- synthesis disciplines: `src/reports/narrative.py:276-329`
- findings disciplines: `src/reports/narrative.py:457-490`

This is valuable, but it is not the same as a deterministic editorial intelligence layer.

### Narrative cohesion checks

Not found.

Tests currently check:

- prompt date anchoring
- fallback behavior
- JSON parsing
- URL allowlist filtering
- no default perceptual hints
- perceptual experiment off by default
- persisted narrative overlay
- renderer sections remain visible

I did not find tests that detect repeated sentence openings, generic filler, entity drift, unsupported recommendations, weak evidence binding, or overuse of self-description as validation.

## Source of Repeated Generic Patterns

### “Teams in this position typically...”

This phrase is coming from the findings prompt contract, not only from model habit.

The prompt explicitly instructs `typical_decision` to be framed as:

> teams in this position typically choose between X, Y, or Z

Source: `src/reports/narrative.py:542-545`.

The `Finding.prose` property then concatenates `observation`, `implication`, and `typical_decision` into a single paragraph:

- `src/reports/narrative.py:73-77`

The template renders only `finding.prose`, not the separate fields:

- `src/reports/templates/report.html.j2:810-814`

So even though the internal object separates the fields, the report collapses them into one continuous paragraph. That increases the chance that every finding ends with the same “teams in this position...” cadence.

### “The brand...”

This is partly intentional and partly risky.

The findings prompt requires observation subjects such as:

- “the brand says/claims/describes itself as X”
- “the brand appears in/on Y”
- “third parties describe/categorize Z”

Source: `src/reports/narrative.py:530-534`.

This is designed to prevent Brand3 from echoing self-description as fact. But because this subject list is narrow, it can also make many findings start the same way. The prompt bans “the brand is/has/demonstrates/projects”, but still channels the model toward repeated “the brand says...” constructions.

### “This suggests...”

This is mostly prompt-induced.

The system requires implication to use conditional language:

- “suggests, tends to, may indicate, likely, could”

Sources:

- `src/reports/narrative.py:469-471`
- `src/reports/narrative.py:538-540`

That is correct epistemically, but without a varied editorial grammar layer it creates repetitive conditional transitions.

### Generic consultancy language

This is both prompt and architecture.

Prompt-level defenses exist: the prompts ban generic praise, closed adjectives, score-led openings, and empty consultancy phrases. But the architecture asks the LLM to write each dimension independently. Since each dimension receives a similar prompt and similar required fields, the outputs naturally converge toward repeated structures.

In short: the prompts try to prevent generic prose, but the generation architecture still rewards parallel, similarly shaped paragraphs.

## Evidence vs Interpretation vs Editorial Synthesis

The system partially distinguishes these layers.

Evidence layer:

- `Evidence` dataclass in `src/reports/derivation.py`
- evidence extraction and grouping through `collect_evidences(...)` and `group_by_dimension(...)`
- evidence summary/readiness/trust in `build_report_base(...)`

Analytical interpretation:

- `Finding.observation`
- `Finding.implication`
- `Finding.typical_decision`

Source: `src/reports/narrative.py:49-77`.

Editorial synthesis:

- `generate_synthesis(...)`
- `generate_tensions(...)`

But the distinction is weakened at render time because the template renders `finding.prose`, which concatenates the separated parts:

- concatenation: `src/reports/narrative.py:73-77`
- template render: `src/reports/templates/report.html.j2:810-814`

So internally the model has a separation discipline, but the user reads it as a single paragraph. That may be one reason the report feels like stitched LLM output rather than a composed editorial read.

## Likely Cause Classification

This is both a prompt problem and an architecture problem.

Prompt problem:

- Some repeated language is directly specified by the prompt, especially “teams in this position typically...”.
- The allowed observation grammar narrows the model into repeated “the brand says/appears...” subjects.
- The implication grammar repeatedly steers toward “suggests/may/could”.

Architecture problem:

- Findings are generated one dimension at a time.
- There is no shared narrative state before findings are written.
- Tension is generated after findings, so it cannot guide them.
- Synthesis is generated last, so it can harmonize the overview but cannot revise the dimension prose.
- There is no post-generation cohesion gate before persistence.

Prompt tuning alone can reduce surface repetition, but it cannot make independently generated dimension blocks behave like a single editorial argument.

## Uncertain Conclusions

I did not inspect live production outputs or every persisted report in the database during this pass. Conclusions about the exact frequency of repeated phrases are based on code, prompts, tests, and reported symptoms, not a corpus-wide measurement.

I also did not inspect every feature-level prompt deeply. Feature analyzers may contribute upstream phrasing inside `features.raw_value` and `scores.insights_json`, but the final report narrative convergence described here is already explainable from the report narrative layer itself.

## Where a Narrative Harness Fits

A Narrative Harness or Editorial Intelligence Layer should sit between deterministic dossier derivation and LLM prose generation.

Recommended insertion point:

```text
snapshot
→ build_report_base(...)
→ collect_evidences(...) / group_by_dimension(...)
→ Narrative Harness builds EntityNarrativeState
→ generate findings/tension/synthesis using shared state
→ post-generation cohesion checks
→ persist report_narrative
→ render
```

Concretely, it would fit inside `src/reports/dossier.py` before this call:

- `generate_all_findings(...)` at `src/reports/dossier.py:243-251`

The first version does not need to change scoring or runtime behavior. It can be an offline validator/spec that consumes the same snapshot/dossier objects and emits diagnostics.

Suggested future object:

```text
EntityNarrativeState
- entity_name
- entity_url/domain
- owned_claims
- third_party_claims
- observed_surface_behaviors
- source_strength_by_claim
- contradictions
- primary_tension
- unsupported_claims
- editorial_viewpoint
- repetition_budget
- allowed_recommendation_zones
- blocked_language_patterns
```

## Minimal Next Step

Do not start with a prompt rewrite.

Recommended minimal next step:

1. Create a non-runtime Narrative Harness diagnostic that reads an existing report narrative payload.
2. Detect repetition, weak evidence binding, unsupported recommendations, self-description echoing, and entity drift.
3. Run it against stored or fixture report narratives.
4. Only after measuring failures, refine the findings prompt and template rendering.

The smallest useful implementation would be test-first and offline:

- Input: `report_narrative` payload plus the base dossier.
- Output: a diagnostic JSON with warnings and counts.
- Runtime: not enabled in production report rendering.

## Risks of Solving This Only With Prompt Wording

- Prompts cannot coordinate per-dimension sections after each dimension has already been generated independently.
- Prompts cannot reliably remember phrase usage across five separate LLM calls.
- Prompts can ask for “evidence-bound” writing, but they do not compute claim-level support.
- Prompt bans reduce obvious generic prose but may create new repetitive safe phrases.
- Prompt-only fixes do not protect persisted narratives from regressions unless tests enforce invariants.
- The current template collapses separated fields into one paragraph, so prompt improvements may remain less visible than expected.

## Proposed Narrative Harness Invariants

### Generic strategic filler

Flag if a report exceeds a threshold for generic connective phrases:

- “The brand...”
- “This suggests...”
- “This may indicate...”
- “Teams in this position typically...”
- “strong positioning”
- “compelling”
- “robust”
- “sophisticated”
- “world-class”

Invariant: no single sentence opener should dominate the findings section.

### Weak evidence binding

Every finding with an observation should have at least one evidence URL unless the field explicitly says evidence is unavailable.

Invariant: observation text must contain either a quote, a named source/domain, or a visible evidence anchor.

### Entity drift

The generated report should not introduce unrelated brand names, categories, or claims not present in the evidence pool.

Invariant: named entities outside the target brand/domain must appear in source evidence or be marked as comparator/context.

### Repetition

Detect repeated sentence starts and repeated n-grams across findings.

Invariant: no more than two findings should begin with the same first 3-5 words unless they are quoted evidence.

### Unsupported recommendations

Flag prescriptive language unless the prose is explicitly framed as a plural option space.

Examples to flag:

- “the brand should”
- “needs to”
- “must”
- “the right move is”

Invariant: recommendations must be either absent, plural, or explicitly conditional on internal variables not visible from outside.

### Overuse of self-description as external validation

If a claim is based only on owned sources, prose must mark it as self-description.

Invariant: owned-only evidence cannot support language that validates the claim externally.

Allowed:

- “the brand describes itself as...”
- “based only on self-description...”

Blocked:

- “the brand is...”
- “the brand has established...”
- “the brand demonstrates...”

### Contradiction handling

If owned claims and third-party descriptions conflict, the report should surface that as a tension or explicitly explain why it is not material.

Invariant: detected source conflict should not be smoothed into generic positive synthesis.

### Score-first writing

The synthesis and findings should not open with the score unless the section is explicitly a scoring table.

Invariant: narrative paragraphs should begin with an evidence or pattern anchor, not numeric score metadata.

### Cohesion between synthesis and tension

If `tensions_prose` exists, synthesis should reflect the same tension.

There is already a prompt instruction for this in `src/reports/narrative.py:342-348`, but no deterministic test validates the generated output.

Invariant: a shared key phrase or normalized tension label should appear in both synthesis and tension, or the harness should warn.

## Final Diagnosis

Brand3 has already moved beyond raw LLM prose. It has evidence objects, report readiness, confidence, source grouping, field-level narrative structure, and prompt-level editorial discipline.

The missing layer is not “better writing” in isolation. It is an explicit editorial intelligence layer that builds a coherent representation of the entity before the report speaks.

Until that exists, Brand3 can keep producing paragraphs that are locally defensible but globally repetitive. The system needs a Narrative Harness before further prompt refinement is trusted as a durable fix.
