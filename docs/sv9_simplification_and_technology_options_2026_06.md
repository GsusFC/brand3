# SV9 simplification and technology options - June 2026

## Verdict

SV9 should become the canonical product surface. Magnetism scoring should not remain a required product-level intermediate unless there is a separate commercial reason to expose it.

The best simplification path is not a Rust rewrite. The best path is:

```text
acquisition -> evidence contracts -> tile signals -> SV9 -> views
```

Rust, or any non-Python implementation, should only be considered for small stable modules where benchmarks show a real bottleneck and the contract is already mature. The current highest leverage is contract consolidation, naming cleanup, and traceability.

## Current product tension

The current stack has several historically valid layers that now compete conceptually:

- Pass 1 / TLDR detection
- Magnetism Scanner score
- Magnetism evidence
- Research Pack / EvidenceGraph / Evidence vNext
- Visual Signature evidence
- SV9 tile evaluation

This makes quality control harder because an operator has to answer too many questions before trusting a result:

- Did the score move because acquisition changed?
- Did Pass 1 drift?
- Did Magnetism scoring drift?
- Did SV9 evaluation drift?
- Did visual evidence exist, fail, or get ignored?
- Did the UI show a product score or an intermediate score?

The target should be fewer public products and more explicit internal contracts.

## Proposed product hierarchy

SV9 should own the final evaluation.

Magnetism should survive as a component family inside SV9, not as a mandatory public scoring product.

TLDR should survive as an interpretation artifact, not as a product surface or hidden scoring authority.

Visual Signature should contribute evidence-only packets and tile signals. It should not contribute an autonomous score.

Recommended hierarchy:

```text
1. Acquisition
   Raw web, context, Exa, social, screenshot, Visual Signature capture.

2. Evidence contracts
   Normalized, traceable packets with provenance and quality gates.

3. Interpretation artifacts
   TLDR, claims, proof points, visual observations, market/context observations.

4. Tile signals
   supports / weakens / insufficient_evidence / blocked / capture_unreliable.

5. SV9 aggregation
   The only canonical score.

6. Views
   /sv9, /brand, debug/evidence, legacy scanner routes during migration.
```

## Naming recommendation

Current name | Recommended role
--- | ---
`Pass 1` | `detect_brand_blocks()` or `build_brand_interpretation()`
`tldr_brand3` | `brand_interpretation_v1`
`MagnetismExtractor` | Compatibility facade; future `BrandInterpretationBuilder`
`Magnetism score` | Legacy/debug view
`Magnetism evidence` | Part of unified evidence/tile signal contract
`Visual Signature score` | Internal diagnostic only
`visual-signature-evidence-v1` | Evidence contract consumed by SV9

## Technology decision

### Do not migrate these to Rust now

These parts are mostly orchestration, API glue, prompt shaping, or policy logic:

- SV9 service orchestration
- Magnetism/TLDR extraction flow
- Research Pack builder selection
- Evidence vNext promotion gates
- FastAPI routes/templates
- LLM prompt construction and response normalization

Rust would add build, packaging, deploy, and debugging complexity without solving the core problem: unstable or overlapping contracts.

### Possible Rust candidates later

Only consider Rust for narrow, stable, benchmarked modules:

Module area | Why it might qualify | Current recommendation
--- | --- | ---
Screenshot pixel sampling | CPU-heavy, stable byte-level work | Wait. Pillow already handles decoding; benchmark first.
Palette/composition sampling | Repeated pixel scans can be vectorized | Prefer Pillow/numpy-style optimization before Rust.
Evidence dedupe/fingerprint | Deterministic, pure transformations | Maybe later if datasets become large.
Large JSON normalization/diffing | Could benefit from compiled tooling | Try `orjson`/streaming first.
HTML/text extraction cleanup | Potentially CPU-heavy at scale | Avoid until acquisition scale proves it.

### Better near-term technology upgrades

Lower-risk options before Rust:

- `orjson` for large JSON serialization if profiling shows JSON cost.
- `pydantic` v2 models for stable boundary contracts where validation matters.
- SQLite indexes / query shape review for scan lists and evidence lookup.
- Deterministic fingerprints for evidence packets and interpretation artifacts.
- A benchmark harness around repeated scans before changing implementation language.

## Rust adoption gate

No module should move to Rust unless all conditions are true:

1. The module has a stable input/output contract.
2. It is pure or nearly pure: no network, no LLM, no DB writes.
3. Profiling shows it consumes meaningful runtime or memory.
4. A Python implementation remains as reference or fallback during migration.
5. The Rust boundary has contract tests comparing Python and Rust outputs.
6. Packaging works in local dev and Fly deploy.

Suggested rule:

```text
No benchmark, no Rust.
No stable contract, no Rust.
No Python fallback during rollout, no Rust.
```

## Migration path without touching production behavior

### Phase A - Architecture inventory

Create a table for each current artifact:

- input
- output
- owner
- consumer
- public/debug/internal
- canonical/legacy
- replaceable by evidence contract

Primary targets:

- `src/sv9/service.py`
- `src/sv9/signals.py`
- `src/features/magnetism/*`
- `src/research/research_pack_facade.py`
- `src/research/evidence_vnext.py`
- `src/visual_signature/evidence.py`
- `web/routes/magnetism_scanner*.py`
- `web/routes/sv9_scan.py`

### Phase B - Canonical contracts

Define the future boundary documents before changing code:

- `brand_evidence_pack_v1`
- `brand_interpretation_v1`
- `sv9_tile_signals_v1`
- `visual_signature_evidence_v1` stays evidence-only and maps into tile signals.

### Phase C - Shadow adapter

Add a non-production adapter that turns current outputs into the future shape:

```text
current snapshot + current TLDR + current VS evidence
  -> canonical evidence pack candidate
  -> canonical tile signal candidate
```

This adapter should not alter current scoring, routes, or persistence semantics.

### Phase D - Stability harness

Use existing scans to compare:

- repeated scan same day
- fixed snapshot replay
- fixed screenshot replay
- with and without Visual Signature evidence
- current SV9 versus canonical-adapter SV9 inputs

The main metric is not only score movement. The main metric is whether tile-level explanations and evidence references remain stable.

### Phase E - Retire legacy surfaces

Only after the shadow path is stable:

- hide or mark Magnetism score as legacy/debug;
- route Magnetism pages from SV9 component data where possible;
- rename Pass 1 internally;
- collapse duplicate evidence displays into one evidence/debug surface.

## Practical recommendation

Do not start with a Rust spike.

Start with a no-runtime-change architecture cut:

1. Document current artifact ownership.
2. Define canonical evidence and interpretation contracts.
3. Build a read-only adapter from current outputs to the canonical shape.
4. Add a stability report over 5-10 real scans.
5. Only then decide if a small module deserves a Rust/Python compiled boundary.

This keeps the product goal clear: SV9 gets simpler and more controllable before the implementation gets more sophisticated.

## Current artifact inventory

This inventory is intentionally product-oriented. The goal is to decide which
objects are canonical and which ones are implementation details, without
changing runtime behavior yet.

Artifact | Current role | Keep as | Notes
--- | --- | --- | ---
`SV9 scan` | Final diagnostic and scoring surface | Canonical product | Should remain the only public score.
`Magnetism score` | Historical product score and scanner UI output | Legacy/debug | Useful for regression comparison, not as an upstream authority.
`MagnetismExtractor` | TLDR/Pass 1 facade used by SV9 and scanner paths | Compatibility facade | Future name should describe interpretation, not magnetism scoring.
`Pass 1` | Non-deterministic TLDR/block detection over an audit snapshot | Pinned interpretation artifact | Current `sv9_detection_cache` and `sv9_detection_runs` are the right direction.
`tldr_brand3` | Compact interpreted brand blocks | `brand_interpretation_v1` candidate | Keep the data, retire the product-ish name over time.
`Research Pack` | Normalized textual evidence source for TLDR/interpretation | Evidence contract input | Should feed interpretation, not become another scoring surface.
`EvidenceGraph` / `Evidence vNext` | Candidate upstream evidence model | Evidence contract builder | Keep behind facade until it proves superior and stable.
`Visual Signature evidence` | Evidence-only visual packet with tile signals | Evidence contract input | Already correctly avoids contributing a standalone score to SV9.
`sv9_visual_evidence` | SV9-time legacy vision pass over screenshot | Fallback/debug | Candidate for retirement once Visual Signature evidence is reliable enough.
`SV9 tile signals` | Component-scoped evaluator hints | Canonical internal contract | Should become the main integration boundary.

## What the current code already gets right

- `materialize_sv9_scan()` caches Pass 1 detection before evaluation, which
  acknowledges that detection drift and SV9 evaluation drift must be separated.
- `sv9_detection_runs` records fingerprints for Pass 1 payloads, giving us a
  basis for same-run stability reports.
- `visual_signature_shadow_signals()` adapts Visual Signature into grouped SV9
  evidence and explicitly avoids consuming a Visual Signature score.
- `MagnetismExtractor` is already a compatibility shim, which makes it possible
  to rename or wrap the concept later without breaking callers immediately.

These are good signs. The simplification work should lean into them instead of
starting a rewrite.

## Main design correction

The product should stop thinking in this sequence:

```text
Pass 1 -> Magnetism score -> SV9
```

The target mental model should be:

```text
Evidence -> brand interpretation -> tile signals -> SV9
```

That means:

- Pass 1 is not a product step. It is an interpretation build.
- TLDR is not a score. It is compact interpreted context.
- Magnetism is not an upstream scorer. It is a component family inside SV9.
- Visual Signature is not a visual score. It is visual evidence and optional
  tile-level support/weakening.

## No-runtime-change workplan

### Step 1 - Name the compatibility boundaries

Add documentation and tests around current behavior before renaming anything:

- `MagnetismExtractor` remains the import path.
- Internally document it as the legacy facade for future
  `BrandInterpretationBuilder`.
- `detect_for_snapshot()` remains the SV9 entrypoint for pinned detection.
- `tldr_brand3` remains persisted, but the docs should call it
  `brand_interpretation_v1` candidate.

No routes, payloads, or DB columns need to change in this step.

### Step 2 - Promote tile signals as the integration boundary

Define `sv9_tile_signals_v1` as the target shape used by all auxiliary sources:

```json
{
  "schema_version": "sv9_tile_signals_v1",
  "component": "coherencia",
  "tile": "coherencia.C6",
  "effect": "supports|weakens|insufficient_evidence|blocked|capture_unreliable",
  "confidence": "low|medium|high",
  "source": "research_pack|visual_signature|legacy_feature|llm_interpretation",
  "evidence_refs": ["..."],
  "rationale": "..."
}
```

The current `signals` object can keep its existing shape while adapters produce
this target shape in shadow.

### Step 3 - Create a read-only architecture report

Build a script/report that reads existing scans and outputs:

- source run id;
- Pass 1 fingerprint;
- TLDR generation mode;
- whether Visual Signature evidence was present;
- whether `sv9_visual_evidence` fallback was used;
- score and component deltas across repeated runs;
- tile-level fields that changed.

This gives control of quality before changing architecture.

### Step 4 - Freeze public scores, compare internal candidates

For a limited batch, keep the public SV9 output exactly as today and add a
shadow report:

```text
current SV9 inputs
candidate canonical evidence inputs
candidate tile signals
diff only, no score authority
```

The success metric is not a better-looking score. The success metric is lower
unexplained drift and clearer provenance.

## Candidate modules for extraction to another language

This is deliberately later-stage. The language is secondary; the boundary is
the decision.

Candidate | Boundary maturity | Why it could move | Current decision
--- | --- | --- | ---
Detection fingerprint/diff | Medium | Pure JSON hashing/diffing | Keep Python until report volume grows.
Evidence packet hashing | Medium | Deterministic, pure, easy to contract-test | Possible later.
Tile aggregation math | Medium/high | Pure scoring and weighting | Keep Python while rubric still moves.
Screenshot sampling | Medium | CPU-bound image traversal | Benchmark Pillow/numpy path first.
HTML cleanup/extraction | Low/medium | Could become CPU-heavy | Too coupled to acquisition policy now.
LLM response normalization | Low | Business rules still moving | Keep Python.

The immediate extraction candidate is not Rust or any other language. It is a
small pure-Python core with stable contract tests. Once that core is stable,
another implementation can compete against it.

## Recommended next deliverables

1. A `sv9_drift_report` over repeated scans using existing persisted data.
2. A `sv9_tile_signals_v1` schema document and fixture.
3. A shadow adapter from current TLDR + Visual Signature evidence to candidate
   tile signals.
4. A decision to mark Magnetism score as legacy/debug in docs and UI labels.
5. A later migration plan for routes, after the shadow adapter proves stable.

## Orchestrators vs workers

The goal is not to create a second scanner. The goal is to make the current
system easier to control by turning pre-SV9 pieces into workers with explicit
inputs and outputs.

### Orchestrator

An orchestrator decides order and side effects:

- load snapshot;
- call evidence workers;
- call interpretation workers;
- call tile-signal workers;
- call final SV9 evaluator;
- persist the final result;
- render or return the product response.

An orchestrator may touch DB, queues, routes, and LLM clients, but it should not
contain dense business logic. It should mostly wire dependencies.

### Worker

A worker performs one testable task:

- extract evidence;
- normalize evidence;
- interpret brand blocks;
- adapt Visual Signature evidence;
- build tile signals;
- summarize/report a candidate;
- fingerprint or diff artifacts.

Workers should accept explicit data and return explicit data. They should not
create a product score before SV9.

### Facade

A facade preserves existing imports while delegating to workers. This is the
right role for legacy names like `MagnetismExtractor` while the underlying
responsibility shifts toward brand interpretation.

### Red flags

The simplification is going in the wrong direction if a change adds:

- a new public score before SV9;
- a new scanner-like route set;
- a new persistent run table for a product that is not SV9;
- a separate UI that looks like a product result;
- a worker that reads/writes global state when it could receive explicit data.

The desired pattern is:

```text
current route/service -> thin orchestrator -> workers -> one SV9 score
```

Not:

```text
new route/service/db -> new scanner -> new score -> later SV9
```

## Surface taxonomy guardrail

The experimental `src/sv9_flow.surface` module encodes this classification in
code so tests can keep the rule honest:

- canonical before SV9: acquisition, evidence, interpretation, tile signals,
  debug;
- not canonical before SV9: intermediate brand scores;
- canonical final score: SV9 only.

This is deliberately lightweight. It is a guardrail for refactoring decisions,
not a replacement pipeline.

## Reference package shape

The experimental `src/sv9_flow` package should stay as the reference shape for
future splits:

```text
contracts.py              data contracts only
orchestrator.py           coordinates workers, no product authority
evidence_worker.py        snapshot/current artifacts -> evidence pack
interpretation_worker.py  TLDR/current interpretation -> brand interpretation
tile_signal_worker.py     interpretation/visual evidence -> tile signals
reporting.py              compact observability over candidates
surface.py                guardrails for product authority
adapters.py               thin compatibility facade
```

This is the pattern to apply to current large files: keep public imports stable,
move work into explicit workers, and leave product authority in SV9 only.

Architecture tests should keep this package from becoming a second scanner:

- no FastAPI imports;
- no SQLite/store imports;
- no web route imports;
- no direct dependency on the current `src.sv9.service` or `src.sv9.store`;
- `adapters.py` remains a thin facade.

## Validation harness boundary

The proposal still needs connected results to prove usefulness. The right
connection point is a validation harness, not a new scanner product.

`scripts/sv9_flow_shadow_run.py` is allowed to connect outward because it is a
script boundary:

- read an existing audit snapshot by `run_id`;
- reuse existing SV9 Pass 1 detection cache when present;
- optionally run live detection only with an explicit flag;
- optionally bypass Pass 1 with the `flow-llm` interpretation worker;
- read Visual Signature evidence from the current snapshot;
- emit a candidate/report JSON to stdout or a file;
- never create routes, product DB tables, public scores, or jobs.

This gives us real data for comparison while keeping product authority in the
current scanner/SV9 stack until the evidence-first flow earns promotion.

Pass 1 is a baseline, not the destination. The harness should compare at least
three interpretation sources:

```text
cached-pass1   current pinned behavior, best for stable baseline
live-pass1     current live behavior, best for measuring current drift
flow-llm       new evidence-first interpretation, candidate replacement
```

Promotion should depend on whether `flow-llm` produces more traceable,
less speculative, less volatile tile signals than both Pass 1 modes.
