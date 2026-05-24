# Brand3 Scoring Narrative Pipeline Audit

Generated: 2026-05-14
Scope: audit only

This audit traces how Brand3 narrative is constructed end to end, why the report voice keeps converging toward similar outputs, and where the system can move toward sharper Brand3 / FLOC* strategic analysis without changing scoring logic, rubric dimensions, or the report renderer.

## Executive Summary

Brand3 narrative is not produced in one place. It is assembled across multiple layers:

1. input collection and evidence assembly
2. feature extraction and scoring
3. score summary generation
4. report dossier derivation
5. LLM narrative overlays and deterministic fallbacks
6. Jinja template rendering

The repetition problem comes from the whole stack, not just the final prompts. The same few rhetorical shapes are reused at several layers:

- score-first summaries
- strongest / weakest dimension comparisons
- trust or data-quality tails
- generic fallback paragraphs such as "available evidence" or "automatic synthesis unavailable"
- consultant-style synthesis language such as "clear message", "strong presence", "differentiated strategy", "main tension"

The report template also repeats content intentionally: it renders a "current reading" tab and a "new synthesis" tab, both built from the same snapshot and both anchored to the same score metadata. That makes the final report feel stable, but also formulaic.

## Pipeline Map

### 1) Input Collection

Entry points:

- FastAPI web form: `POST /analyze`
- CLI: `python main.py analyze <url> [brand_name]`
- Web backend: `src.services.brand_service.run(...)`

Collection layer:

- `src/services/input_collection.py`
- `src/services/run_preparation.py`
- collectors for web, Exa, context, social, and competitors

What happens:

- raw inputs are collected or loaded from cache
- context, web, Exa, social, and competitor data are persisted as raw inputs
- evidence items are stored in SQLite when available
- `data_quality` and partial-dimension status are computed before scoring

Where interpretation starts:

- context readiness and data-quality classification begin to interpret the input surface
- this is still pre-narrative, but it already shapes the eventual report tone

### 2) Feature Extraction

Files:

- `src/services/brand_service.py`
- `src/services/feature_pipeline.py`
- `src/features/coherencia.py`
- `src/features/presencia.py`
- `src/features/percepcion.py`
- `src/features/diferenciacion.py`
- `src/features/vitalidad.py`

What happens:

- each dimension is converted into feature values
- each feature carries a numeric score, confidence, source, and structured `raw_value`
- many features embed literal quotes or snippets in their raw payloads

Where interpretation starts:

- several extractors are already doing editorial interpretation:
  - `messaging_consistency`
  - `tone_consistency`
  - `brand_sentiment`
  - `sentiment_trend`
  - `positioning_clarity`
  - `uniqueness`
  - `momentum`

These are not just measurements. They are linguistic judgments with evidence attached.

### 3) Scoring and Stored Summary

Files:

- `src/services/scoring_pipeline.py`
- `src/scoring/engine.py`
- `src/storage/sqlite_store.py`

What happens:

- `score_features(...)` computes per-dimension scores and the composite score
- `SQLiteStore.save_scores(...)` persists per-dimension scores, insights, and rules
- `ScoringEngine.generate_summary(...)` produces the CLI / stored run summary
- `SQLiteStore.finalize_run(...)` stores `runs.summary`

Where prose generation happens:

- the scoring engine summary is a separate prose artifact from the report narrative
- it is still formulaic: score, dimension bars, weakest dimension, strongest dimension

### 4) Snapshot to Report Dossier

Files:

- `src/reports/derivation.py`
- `src/reports/dossier.py`
- `src/quality/dimension_confidence.py`
- `src/quality/evidence_summary.py`
- `src/quality/report_readiness.py`
- `src/quality/trust.py`

What happens:

- `SQLiteStore.get_run_snapshot(...)` is converted into a renderable dossier
- evidence is normalized from `features.raw_value` and `evidence_items`
- confidence and evidence summaries are recomputed from the snapshot
- readiness and trust summaries determine what language level the report can use
- a deterministic synthesis fallback is always created in `build_report_base(...)`

Where interpretation happens:

- `derive_data_quality(...)`
- `dimension_confidence_from_snapshot(...)`
- `summarize_evidence_records(...)`
- `evaluate_report_readiness(...)`
- `build_trust_summary(...)`
- `build_trust_interpretation(...)`

This is where the report starts deciding whether the language should be editorial, observational, technical, or blocked.

### 5) Narrative Overlays

Files:

- `src/reports/narrative.py`
- `src/reports/dossier.py`

What happens:

- `generate_synthesis(...)` writes the §1 paragraph
- `generate_all_findings(...)` writes per-dimension finding blocks
- `generate_tensions(...)` writes the cross-dimension tension block
- when the LLM is unavailable or fails, deterministic fallback text is used

Where prose generation happens:

- prompt-driven prose is created here
- the fallback prose is also created here
- this is the main narrative generation layer, but not the only one that shapes voice

### 6) Report Rendering

Files:

- `src/reports/renderer.py`
- `src/reports/templates/report.html.j2`

What happens:

- the Jinja template renders:
  - score hero
  - trust state
  - evidence summary
  - current reading tab
  - synthesis / findings tab
  - sources and footer

Renderer assumptions:

- prose arrives already prepared
- the renderer does not try to re-structure the narrative
- the template displays both `legacy_summary` and `synthesis_prose`, which reinforces repetition
- the template expects short flat prose blocks, not a hierarchical argument

### 7) Persisted Output Surface

Files:

- `output/*.json`
- `output/reports/**/*.html`

What happens:

- the run JSON stores the raw analysis payload
- rendered HTML files store the final report
- no dedicated persisted `generated_texts_per_dimension` artifact was found

## Dimension Analysis

### Coherencia

- Intended semantic meaning: consistency across touchpoints, including visual identity, messaging, tone, and cross-channel coherence.
- Actual emergent behavior: the dimension often becomes a comparison between self-description and third-party description, with visual consistency as a weaker or missing sub-signal.
- Common generic outputs: "clear message", "consistent coverage", "aligned themes", or fallback "available evidence" when the LLM cannot produce a richer finding.
- Ambiguity sources: visual evidence is optional; message and tone can be over-weighted; the dimension overlaps with differentiation when wording and self-description diverge.
- Overlap with other dimensions: presence (channel footprint), differentiation (ownable vocabulary), perception (external coverage).
- Sharper diagnosis opportunity: split coherence into explicit sub-questions for visual consistency, message consistency, tone consistency, and channel coherence.

### Presencia

- Intended semantic meaning: discoverability and actual presence across web, social, search, and directories.
- Actual emergent behavior: it often reads like "is the brand findable and structurally live?" rather than a richer distribution story.
- Common generic outputs: "found", "available", "mixed", "ghost brand", "web exists but socials weak", or fallback "available evidence".
- Ambiguity sources: a live website can still be low presence; social and directory signals are often sparse; the dimension can collapse into a simple existence check.
- Overlap with other dimensions: coherence (cross-channel structure), vitality (active publishing), perception (external awareness).
- Sharper diagnosis opportunity: separate owned web presence from external discoverability and platform footprint.

### Percepcion

- Intended semantic meaning: public sentiment, awareness, and how people talk about the brand.
- Actual emergent behavior: it often becomes mention-volume and sentiment-summary language, sometimes with a weak "niche press" framing.
- Common generic outputs: "positive", "mixed", "niche coverage", "limited mentions", or fallback "available evidence".
- Ambiguity sources: low mention volume turns the dimension into a neutral placeholder; sentiment and controversy are conflated in some prompts.
- Overlap with other dimensions: vitality (recent activity and news), presence (surface visibility), coherence (self vs external narrative).
- Sharper diagnosis opportunity: separate awareness from sentiment from controversy from review quality.

### Diferenciacion

- Intended semantic meaning: whether the brand says something ownable, distinct, and defensible instead of generic category language.
- Actual emergent behavior: this is the most narrative-heavy dimension; it often generates the most consultant-like prose.
- Common generic outputs: "clear, differentiated strategy", "ownable vocabulary", "generic language", "strong positioning", "main tension", "highly differentiated concept".
- Ambiguity sources: positioning clarity, uniqueness, competitor distance, authenticity, and personality all point at a similar strategic center.
- Overlap with other dimensions: coherence (consistent messaging), perception (how others simplify the brand), presence (how discoverable the proposition is).
- Sharper diagnosis opportunity: split "what the brand claims", "what is ownable", and "what competitors compress or flatten" into separate readings.

### Vitalidad

- Intended semantic meaning: whether the brand is active, publishing, and evolving.
- Actual emergent behavior: it tends to become a recency/cadence proxy plus a growth-vs-maintenance judgment.
- Common generic outputs: "building", "maintaining", "declining", "active", "regular publishing", or fallback "available evidence".
- Ambiguity sources: sparse dates or indirect mention signals make it easy to over-generalize momentum.
- Overlap with other dimensions: perception (new mentions), presence (active channels), differentiation (new launches can look unique).
- Sharper diagnosis opportunity: separate recency, cadence, momentum, and lifecycle stage instead of letting them collapse into one "alive/dead" reading.

## Linguistic Analysis

### Repeated Sentence Structures

Across sampled reports, the same sentence shapes recur:

- score statement + strongest dimension + weakest dimension + data quality
- "presenta / presents" + a generic positive clause + a tension clause
- "the available sources point in the same direction"
- "available evidence" + explanation that synthesis is unavailable
- "Trust state: partial ..."
- "Data quality: degraded."

In a small scan of 26 prose blocks from sample outputs, the most repeated clauses included:

- `Data quality: degraded.`
- `Strongest dimension: Presence ...`
- `Weakest dimension: Perception ...`
- `FLOC* scores 62/100 (band C+).`
- `The available sources point in the same direction.`
- `Main tension: ...`

### Repeated Adjectives

Frequently repeated adjectives / evaluative words:

- clear
- strong
- consistent
- differentiated
- solid
- mixed
- partial
- limited
- mostly-solid
- uneven
- cohesive

### Overused Abstractions

Common abstraction clusters:

- message
- positioning
- coverage
- presence
- perception
- strategy
- tension
- evidence
- alignment
- clarity

### Vague Strategic Language

The narrative often falls back to strategist-sounding phrases that do not add much diagnostic specificity:

- clear message
- strong presence
- differentiated strategy
- sophisticated platform ambition
- market understanding
- strategic question
- trade-off space
- current reading
- consolidated evidence

### Literary Filler

The report can become polished without becoming sharper. Signs include:

- broad praise or critique without a concrete signal attached
- repeated "however" / "this creates a tension" structures
- sentences that sound authoritative but do not name the actual evidence delta
- finding blocks that say "The available sources point in the same direction."

### Consultant-Sounding Patterns

The prompt and output style often reads like a brand strategist memo:

- "presents a clear message"
- "reinforce its ... positioning"
- "emphasizes the builder experience"
- "sophisticated platform ambition"
- "more narrow, tool-focused market understanding"

That tone is not wrong, but it is overused and can flatten distinct brands into the same analytical register.

### Generic Praise Patterns

These are the patterns most likely to make different reports sound alike:

- "clear"
- "strong"
- "solid"
- "consistent"
- "well-defined"
- "differentiated"
- "backed by"
- "reinforce"
- "emphasizes"
- "creates a tension"

## Brand3 / FLOC* Voice Gap

### What The Reports Currently Sound Like

- score-led, even when the prompt says not to open with the score
- professionally competent but often generic
- more like a consultant summary than a perceptual diagnosis
- occasionally overconfident relative to evidence quality
- prone to repeating the same structural rhythm across brands

### What They Should Sound Like

- shorter and more diagnostic
- grounded in what is visible or stated, not in what sounds impressive
- more contrastive and tension-aware
- more specific about what the evidence does and does not support
- less dependent on praise language

### Editorial Characteristics Desired

- concise over literary
- diagnostic over descriptive
- observation-first over interpretation-first
- specific over atmospheric
- evidence-linked over free-floating

### Strategic Characteristics Desired

- name the actual trade-off
- identify where the brand is compressed, overgeneralized, or over-claimed
- distinguish signal from narrative polish
- state what the evidence changes about the reading

### Perceptual Characteristics Desired

- describe what is visible on the surface
- separate what the brand says from what others say
- separate what is present from what is merely claimed
- keep the evidence chain obvious

## Recommended Writing Model

1. Concise over literary. Every sentence should earn its place.
2. Diagnostic over descriptive. Say what changed in the reading, not just what exists.
3. Tension-aware over celebratory. If there is no tension, do not invent one.
4. Observation-first over interpretation-first. State the visible signal before the inference.
5. Specific over atmospheric. Prefer the concrete page, quote, or channel to a general mood.
6. Perceptual over branding jargon. Use brand language only when it is evidence, not decoration.

## Anti-Patterns

### Phrases To Avoid

- clear message
- strong presence
- differentiated strategy
- well-defined identity
- sophisticated platform ambition
- the available sources point in the same direction
- automatic synthesis unavailable
- available evidence
- the brand demonstrates
- the brand is

### Narrative Styles To Avoid

- score-first opening paragraphs
- consultant-summary cadence
- praise plus caveat template
- “one big insight” paragraphs that flatten the evidence
- repeated "however" or "this creates a tension" scaffolding without new evidence

### Tone Patterns To Avoid

- celebratory
- promotional
- overconfident
- too polished for the evidence level
- generic brand-strategy optimism

### Structure Repetition To Avoid

- score / strongest / weakest / data quality in every summary paragraph
- the same fallback paragraph for every dimension
- identical "available evidence" blocks across dimensions
- duplicated prose that says the same thing in the current-reading and synthesis tabs

## Future Directions

### Low-Risk Prompt Improvements

- tighten openings so synthesis cannot drift back to score-first language
- force one concrete evidence anchor per paragraph
- ban the most generic praise/consultant phrases
- require an explicit observation / implication split in findings
- make fallback language more dimension-specific instead of "available evidence"

### Medium-Risk Structural Changes

- split report prose into distinct layers:
  - observation
  - implication
  - tension
  - recommendation space
- make the current-reading tab more compact and more technical
- reduce duplicated prose between the two narrative tabs
- give each dimension a distinct diagnostic template instead of one shared paragraph shape

### Future Semantic Architecture Improvements

- store structured narrative atoms instead of freeform prose
- persist observation / implication / tension records separately
- represent evidence linkage as first-class data, not just prose references
- build reusable perceptual knowledge from recurring observation types rather than from full paragraphs
- allow future strategic synthesis to compose from structured signals rather than from one monolithic LLM paragraph

## Sample Reports Reviewed

- `tests/snapshots/report-netlify-light.html`
- `output/reports/manual-preview.html`
- `output/reports/manual-preview-real.html`
- `output/reports/manual-preview-real-actual.html`
- `output/reports/charms-real.html`
- `output/reports/charms-real-actual.html`
- `output/reports/elevenlabs/13-20260430-230043/report.dark.html`
- `output/reports/floc/9-20260430-064008/report.light.html`
- `output/reports/a16z/42-20260419-144049/report.light.html`
