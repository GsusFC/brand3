# Brand3 Finding Generation Contract Audit

## Purpose

This audit answers one question:

> Is Brand3 asking the model to generate intelligent findings from clean evidence, or is it asking the model to rationalize noisy, weak, technical, or entity-mixed inputs into strategic prose?

The answer is: **the current contract often asks the model to rationalize mixed evidence into strategic prose.** The model upgrade to Gemini 3.1 may improve obedience and fluency, but it does not fix the evidence contract by itself.

## Pipeline Map

1. Collectors and feature analyzers write feature `raw_value` records and optional `evidence_items`.
2. `src/reports/derivation.py` extracts normalized `Evidence` objects from feature raw values and persisted evidence items.
3. `src/reports/dossier.py` groups evidence by dimension and calls report narrative generation.
4. `src/reports/narrative.py` asks the LLM to generate findings, tensions, and synthesis.
5. `src/reports/dossier.py` persists `report_narrative` as `title`, `observation`, `implication`, `typical_decision`, and `evidence_urls`.
6. `src/reports/renderer.py` renders persisted findings. Current rendering can hide generic `Decision space`, but it does not change the payload or generation contract.

## LLM Call Map

| Area | File | Role/model | Output | Affects scoring | Affects final report prose | Persists |
|---|---|---:|---|---:|---:|---:|
| Feature analysis | `src/features/llm_analyzer.py` | default model unless caller overrides | JSON feature outputs | yes, through feature values | indirectly | feature raw values/cache |
| Run preparation | `src/services/run_preparation.py` | cheap model | pre-run/metadata support | indirectly | no direct prose | run prep artifacts |
| Visual analysis | `src/features/visual_analyzer.py` | vision model | visual feature signals | yes, through features | indirectly | feature raw values |
| Findings | `src/reports/narrative.py` | premium model via `_default_analyzer()` | `Finding` JSON | no direct score change | yes | `report_narrative` |
| Tensions | `src/reports/narrative.py` | premium model | tensions JSON/prose | no | yes | `report_narrative` |
| Synthesis | `src/reports/narrative.py` | premium model | synthesis prose | no | yes | `report_narrative` |

The current default/premium report narrative model is Gemini 3.1 Pro Preview. Cheap model is Gemini 3.1 Flash Lite. Vision remains Gemini 2.5 Flash.

## Finding Generation Contract

Findings are generated in `src/reports/narrative.py`.

The `Finding` dataclass is explicitly structured as:

- `observation`
- `implication`
- `typical_decision`
- `evidence_urls`

The `.prose` property concatenates `observation + implication + typical_decision` for backward compatibility.

The findings prompt sends each dimension:

- dimension name
- dimension score
- dimension verdict
- brand name
- up to 12 formatted evidence items
- optional perceptual hints

Each evidence line is formatted as:

```text
[SOURCE_TYPE · DOMAIN · sentiment?] "quote if present" → url
```

What the model receives:

- source type: coarse `owned`, `review`, `news`, `social`, `encyclopedic`, `changelog`, `other`
- source domain when a URL exists
- sentiment when present
- quote or URL

What the model does **not** reliably receive:

- source ownership summary across the finding
- entity ambiguity or related-surface status
- evidence confidence
- freshness
- whether evidence is internal technical analysis
- whether evidence is technical appendix only
- whether evidence is weak and should not become a finding
- whether an item is owned-claim-only
- whether a signal is off-entity or ambiguous
- whether `typical_decision` should be omitted
- a `no_finding` or `reject` output path

The prompt requires every finding to include:

- observation
- implication
- typical decision
- evidence URLs

The most important failure is that the prompt asks the model to state what the observation could mean “commercially or strategically” and to provide a plural decision space for each finding. That creates pressure to turn even thin technical or internal evidence into strategic prose.

## Evidence Metadata Map

The normalized `Evidence` object contains:

- `dimension`
- `quote`
- `url`
- `source_type`
- `source_domain`
- `sentiment`
- `feature_name`
- `extra`

This is useful, but the final prompt compresses it heavily. `extra` fields such as confidence and freshness from `evidence_items` are not shown in the prompt. The persisted `report_narrative` drops `source_type`, `source_domain`, `feature_name`, confidence, freshness, ownership summaries, technical/internal flags, and entity relation metadata.

This means the model has too little structured context before generation, and the renderer has too little metadata after generation.

## Evidence Quality Findings

Evidence can enter finding generation from:

- `evidence`
- `quotes`
- `examples`
- `messaging_gaps`
- `tone_examples`
- `evidence_url`
- `evidence_snippet`
- `evidence_snippets`
- `evidence_insights`
- persisted `evidence_items`

This allows internal or technical strings such as visual metrics to become ordinary evidence quotes. `robots.txt`, sitemap context, screenshot metrics, malware scans, trust scans, owned claims, and third-party summaries can all arrive in the same dimension-level evidence pool.

There is no pre-generation eligibility gate that says:

- eligible for narrative finding
- owned claim only
- technical appendix only
- internal analysis only
- off-entity or ambiguous
- weak external signal
- reject
- requires human review

Missing evidence URLs are possible because string-only evidence can be collected as quotes without URLs, and `_try_findings` does not reject findings whose validated `evidence_urls` list is empty.

## Prompt Failure Modes

The current prompt improves attribution discipline, but it still encourages several failure modes:

| Failure mode | Contract source |
|---|---|
| Turning every signal into strategic implication | `implication` is required and asks for commercial/strategic read |
| Generic consultancy prose | `typical_decision` is required for every finding |
| Repeated caveats | single-source self-description rule repeats per finding |
| Technical artifacts as brand intent | no technical-only or appendix-only evidence class |
| Entity ambiguity smoothing | no explicit entity state or related-surface contract |
| Weak evidence becomes enough for narrative | no evidence eligibility threshold |
| Missing evidence URLs persist | URL validation filters but does not reject empty URL findings |
| Flattened narrative | `.prose` still concatenates all fields for compatibility |

## Payload And Render Contract

The persisted `report_narrative` preserves:

- `title`
- `observation`
- `implication`
- `typical_decision`
- `evidence_urls`

It does not preserve enough metadata to later distinguish:

- owned claim vs external validation
- technical signal vs brand evidence
- off-entity evidence vs same-entity evidence
- weak signal vs eligible finding
- internal analysis vs observed market evidence

Rendering now separates `observation + implication` from `Decision space` and hides clearly generic decision space. That improves visible repetition, but it is a display patch. It does not make the underlying finding safer or more valid.

## Builtwith / Kit Trace

| Finding | Likely evidence source | Why the model was allowed to generate it | Missing metadata | Recommended handling |
|---|---|---|---|---|
| `Visual analysis metrics` | `visual_consistency` feature `evidence_insights`: local image analysis color groups, whitespace ratio, contrast signal | Internal technical observations were collected as evidence quotes; prompt required strategic implication and typical decision | `internal_analysis_only`, `technical_appendix_only`, no URL, no product relation, no eligibility gate | Reject as finding or move to technical appendix |
| `Technical site configuration` | `robots.txt` URL and context readiness signals | URL evidence was available, and prompt asked for implication/decision space | `technical_appendix_only`, no SEO intent evidence, no evidence threshold | Move to technical appendix or weaken heavily |
| `Email-first OS for creators` | Kit owned website/self-description, sometimes string evidence with no URL | Owned self-description is allowed; prompt says to caveat but still asks for implication and decision space | entity ambiguity between `builtwith.kit.com`, `kit.com`, and BuiltWith; owned-claim-only flag; finding-level URL missing in some dimensions | Keep only if entity boundary is clear; otherwise require evidence/entity review |
| `Technology intelligence provider` | BuiltWith third-party/self-description evidence mixed with Kit run surface | Contradictory/mixed dimension evidence was grouped; prompt asks to name contradictions but lacks entity-state boundary | related-surface status, source ownership summary, entity relation | Keep as entity-boundary issue, not as normal brand positioning |

## Root Cause Assessment

The root cause is not simply “bad writing” and not mainly “old model quality.”

The root cause is a contract mismatch:

1. Evidence collection accepts weak, technical, internal, owned, and entity-mixed signals into the same dimension evidence pool.
2. The findings prompt requires strategic implication and decision-space prose for each generated finding.
3. The prompt has caution rules, but no evidence eligibility rules.
4. Validation checks shape and URL allowlist, not narrative eligibility.
5. Persisted payload drops metadata that would let later stages distinguish weak or technical signals from real finding evidence.
6. Rendering can suppress visible `Decision space`, but cannot correct upstream evidence misuse.

## Gemini 3.1 Implications

Gemini 3.1 may improve:

- JSON obedience
- instruction following
- caveat wording
- refusal to overstate some claims
- handling of longer context
- consistency across dimensions

It cannot fix:

- mixed entity evidence with no entity contract
- internal technical observations presented as ordinary evidence
- mandatory strategic implication for every finding
- mandatory decision framing for every finding
- missing evidence URLs allowed after validation
- persisted payload metadata loss

If the contract remains unchanged, a better model can still produce a more polished rationalization of bad inputs.

## Recommended Next Step

Do **not** add another Lab layer first. Do **not** start with broad prompt rewriting.

Recommended next step:

**Specify and implement an offline finding evidence eligibility gate before report finding generation.**

The gate should classify each evidence item or candidate evidence group into:

- `narrative_eligible`
- `owned_claim_only`
- `technical_appendix_only`
- `internal_analysis_only`
- `off_entity_or_ambiguous`
- `weak_external_signal`
- `reject`
- `requires_human_review`

The first implementation should be offline/diagnostic against existing payloads and Builtwith run data. It should answer which existing findings would be kept, weakened, rejected, or moved to an appendix. Only after that should prompt changes be made.

## Explicit Non-Goals

- No scoring changes.
- No prompt changes in this audit.
- No generation changes in this audit.
- No rendering changes.
- No payload format changes.
- No Visual Signature changes.
- No new runtime gate.
- No new LLM calls.
- No new Brand3 Lab layer.

