# CLIENT TLDR v2 Method Gap — Scan 109

## Scope

- Scan: `109`
- Brand URL: `https://www.monora.ai`
- Source run used for score/report context: `226`
- Timestamp captured from existing artifacts: `/analysis` JSON + route diagnostics generated for this scan

This document maps the legacy TLDR input path, the Client TLDR v2 rewrite path, and the observed output behavior for scan 109.

## 1) Inputs that actually feed Client TLDR v2

### Data path actually used by scan rendering

- `raw_payload` loaded from storage is transformed through:
  - `web/storage.py` row load path for `web_requests` / `magnetism_scans`.
  - `web/routes/magnetism_scanner.py::_magnetism_scan_model(scan_id)` which calls:
    - `_normalized_scan_payload(row)` (API contract normalization layer),
    - `_payload_for_language(scan_id, payload, lang)`,
    - `_scan_model_from_payload(row, payload, scan_id=...)`.
  - Resulting dict includes `model["payload"]`, `model["source_run_id"]`, and `model["payload"]["tldr_brand3"]`.
- `GET /magnetism-scanner/scan/{scan_id}/client-tldr-v2` path:
  - uses `_magnetism_scan_model(scan_id, lang)`,
  - reads `source_run_id`,
  - opens `SQLiteStore(BRAND3_DB_PATH)` and builds:
    - `snapshot = store.get_run_snapshot(source_run_id)`,
    - `narrative_payload = _report_translation_payload(store, source_run_id, lang)`,
    - `score_provenance = build_score_provenance_report(store, source_run_id)`,
    - `report_context = build_brand_dossier(snapshot, narrative_payload=...)`.
  - sets `current_tldr = model["payload"].get("tldr_brand3")`.
  - calls `build_client_tldr_v2(brand_name, url, current_tldr, score_provenance, report_base=report_context, lang=lang)`.
- `GET /api/v1/scanner/{scan_id}/result` does not invoke Client TLDR v2:
  - it builds `magnetism_scan_model_from_row(row)` and returns `scanner_result_payload(...)`,
  - which exposes `tldr_brand3` directly from persisted payload and not `tldr_brand3_v2`/`generation_mode`.

### Legacy TLDR source path

- The scan payload contains three relevant TLDR variants in `raw_payload`:
  - `tldr_brand3`: 9-block analyst output (concise, object-shaped TLDR block)
  - `legacy_tldr_brand3`: interpreter-style TLDR with richer provenance (`source_signal`, `evidence_scope`, `observations`, etc.)
  - `analyst_tldr_raw`: full analyst pass report object including `tldr_brand3`
- `build_client_tldr_v2` is fed from the route with:
  - `current_tldr = model["payload"].get("tldr_brand3")`
  - `score_provenance` built from source run (`scans.id=109`, `source_run_id=226`)
  - `report_base` from `raw_payload`/scan report metadata

### Score / provenance inputs

Observed scan 109 score state used by the helper:

- Computed score: `64.3`
- Display source: `computed`
- Replay integrity: `valid` and fingerprint match `match`
- Recommended display score: `64.3`
- Limited-confidence: `False`
- Warnings: none

The TLDR v2 helper receives these through `score_provenance` and renders `score_reading` with `status="computed"`.

### Prompt/contract source

- Current runtime constant in codebase: `brand3-client-tldr-v2-v0.3`.
- Captured diagnostic artifact for this scan documents prompt as `brand3-client-tldr-v2-v0.1`, indicating this run was captured under older contract than current runtime.

## 2) Legacy contract, v2 contract, and block-level rewrite behavior

### 2.1 Analyst legacy contract (`tldr_brand3`)

- Canonical block set (`TLDR_KEYS`):
  - `core_purpose`, `magnetism`, `value_proposition`, `personality`, `brand_idea`, `attributes`, `values`, `mission`, `vision`
- Each block has analyst-grade fields, for example:
  - `answer`, `content`, `claim_type`, `mode`, `confidence`
  - `question`, `source_signal`, `source_signal_path`, `evidence_scope`, `observations`
  - `counter_evidence`, `reason`, `human_review_recommended`, `review_note`
- Source control is explicit in prompt rules (`ANALYST_TLDR_SOURCE_RULES`):
  - mission/vision can be inferred only from owned content; press-only claims are downgraded
  - personality is constrained by discourse consistency
  - direct blocks without owned-literal evidence are not kept as declared
  - weak/mixed/noise evidence adds caveats + human-review flags

### 2.2 Client TLDR v2 contract

- On **successful LLM pass** (`_normalize_client_tldr_v2_editorial_response` path): top-level output includes:
  - `score_reading`, `executive_reading`, `score_note`, `blocks`, `system_reading`, `caveats`, `legacy_tldr_brand3_v2`.
- On **fallback path** (`_fallback_payload` in `src/features/magnetism/client_tldr_v2.py`):
  - `score_reading`, `system_reading`, `legacy_tldr_brand3_v2`, `evidence_refs`, `validation_notes`,
  - `prompt_version`, `generation_mode="fallback_client_v2"`.
- `generation_mode="llm_client_v2"` appears only when validated LLM JSON is normalized in editorial mode.
- Per-block output is serialized to editorial shape:
  - `block`, `question`, `answer`, `claim_type`, `mode`, `confidence`, `reasoning`
  - `evidence_refs`
  - optional `caveat`, `validation_question`, `human_review_recommended`, `source_signal`
- Normalizer guarantees 9-block serializable output in all cases.
- Mission/Vision explicit handling is part of the v2 prompt:
  - avoid hardcoded absence language
  - separate inference path from editorial wording
  - return explicit “gap” when confidence/evidence is insufficient

### 2.3 Reusable block-level rules from legacy prompt + guardrails (ground truth)

These are the behavioral constraints to preserve when producing `v2` editorial copy:

1. `core_purpose`
   - Use claim only from owned content and explicit source signals.
   - Do not assert broad mission language unless provenance is supported.
   - If mode is inferred from discourse, keep attribution language explicit and avoid absolute statements.

2. `magnetism`
   - Requires evidence of market tension and differentiation.
   - If evidence is mixed or weak, downgrade from `declared` toward `interpreted_from_discourse` and attach caveats.
   - Keep the wording strategic but not speculative.

3. `value_proposition`
   - Prefer direct product/offering claims from extraction when `claim_type=declared`.
   - If inferred, limit to the observable evidence scope and mark uncertainty.

4. `personality`
   - Must be derived from discourse traces, tone, and behavior patterns.
   - If personality is not strongly evidenced, mark as `interpreted_from_discourse` with explicit confidence and `human_review_recommended`.
   - Never generate persona labels without source continuity.

5. `brand_idea`
   - Keep as a concise positioning construct tied to concrete capabilities.
   - Do not invent category-defining statements not derivable from sources.

6. `attributes` vs `values`
   - `attributes` should remain feature/feature-like descriptors.
   - `values` should stay behavioral/ethical claims, not product feature duplication.
   - When the source only provides surface terms, keep `values` sparse and mark lower confidence; never collapse weak list terms into high-confidence values.

7. `mission`
   - Guardrail: if evidence is press/weak/chrome-only or low-confidence, force `absent`/`not_detected`.
   - Mission can only move to `interpreted` when owned claims provide at least an explicit directional statement.
   - Must return “not specified” / gap phrasing instead of invented future-state prose.

8. `vision`
   - Same safety gate as mission.
   - If signal is speculative, output explicit `gap` language and preserve low confidence.
   - Do not infer roadmap promises from isolated product features.

9. Cross-block fallback behavior
   - `fallback_client_v2` must retain block count and shape but must not be interpreted as successful editorial rewrite.
   - `generation_mode` and prompt version are mandatory for any trust decision on v2 claims.

### 2.3 Block-level extraction path for scan 109

| Block | Legacy input block method (`tldr_brand3`) | v2 rewrite expectation | Scan 109 observed output |
|---|---|---|---|
| `core_purpose` | Short claim from analyst summary + evidence confidence fields | Editorialize concise purpose statement, keep rationale/evidence continuity | Mirrors legacy text exactly in fallback; no rewriting |
| `magnetism` | Explicit market tension + brand position framing + evidence notes | Convert into headline-style strategic claim, optionally tighten wording | Mirrors legacy text exactly in fallback |
| `value_proposition` | Product/offer statement derived from extraction and scoring context | Compress to client-readable value sentence; preserve claim_type/mode semantics | Mirrors legacy text exactly in fallback |
| `personality` | Derived from discourse signals and behavior traces | Surface as brand voice style in client-safe language, preserve caution when inferred | Mirrors legacy text exactly in fallback |
| `brand_idea` | One-line framing concept inferred/composed from product intent | Rephrase as concise positioning line; align confidence with provenance | Mirrors legacy text exactly in fallback |
| `attributes` | Mixed declared + interpreted attributes with evidence references | Convert list-like descriptors into readable attribute bullets/sentences | Mirrors legacy text exactly in fallback |
| `values` | Behavioral/value inference from repeated evidence patterns | Return clear value language, separate from attributes where possible | Mirrors legacy text exactly in fallback |
| `mission` | Usually `claim_type=absent`, `mode=not_detected` when unsupported | Should return explicit gap + inferred status if partial evidence exists | Remains `absent/not_detected` in this run |
| `vision` | Usually `claim_type=absent`, `mode=not_detected` when unsupported | Same explicit-gap behavior; avoid fabricated future-state prose | Remains `absent/not_detected` in this run |

## 3) Scan 109 comparison: legacy input vs Client TLDR v2 result

### 3.1 `current_tldr` input to v2 (from scan 109)

- `current_tldr_present = true`
- `current_tldr_count = 9`
- `current_tldr` keys match the 9 canonical blocks

Extracted block snapshots:

- `core_purpose`: `One context to empower every person. Finally governed.`
  - `claim_type=declared`, `mode=literal`, `confidence=medium`
- `magnetism`: `Everyone’s building a brain. Nobody’s sharing it. Monora is the sharing layer.`
  - `claim_type=declared`, `mode=literal`, `confidence=high`
- `value_proposition`: `A secure, git-based sharing layer for AI-native teams that provides server-enforced, per-folder access control for both human teammates and AI agents.`
  - `claim_type=declared`, `mode=compressed`, `confidence=high`
- `personality`: `Pragmatic, direct, and egalitarian...`
  - `claim_type=performed`, `mode=interpreted_from_discourse`, `confidence=high`
- `brand_idea`: `The 'missing middle' between Git's version control and Drive's simple access management.`
  - `claim_type=declared`, `mode=compressed`, `confidence=high`
- `attributes`: `Secure, AI-native, governed.`
  - `claim_type=performed`, `mode=interpreted_from_discourse`, `confidence=high`
- `values`: `Security, strict governance, and human-agent parity.`
  - `claim_type=performed`, `mode=interpreted_from_discourse`, `confidence=medium`
- `mission`: `None`, `claim_type=absent`, `mode=not_detected`, `confidence=low`
- `vision`: `None`, `claim_type=absent`, `mode=not_detected`, `confidence=low`

### 3.2 Client TLDR v2 output observed in diagnostic artifact

Observed fields in `CLIENT_TLDR_V2_OUTPUT_DIAGNOSIS.json`:

- `result.generation_mode = fallback_client_v2`
- `raw_llm_status = {reason: "llm_error", detail: "The client TLDR v2 pass did not return usable JSON."}`
- `result.tldr_brand3_v2` is present and block-by-block values are the same as `current_tldr`
- No successful editorial synthesis JSON was returned from the model for this run
- `score_reading` resolves to:
  - `status=computed`
  - `label="Calculated score"`
  - `value=64.3`
  - `confidence=high`

**Result:** for scan 109, Client TLDR v2 did not produce a new rewrite; it rendered fallback data derived from the same legacy TLDR payload.

Observed implication for mission/vision:

- `mission` and `vision` were not actively rewritten because fallback mode reused the existing block statuses.
- The block-level caveat machinery existed in inputs and in v2 contract, but was not exercised in this run due to LLM JSON failure.

### 3.3 Legacy `legacy_tldr_brand3` vs `tldr_brand3` vs client output

- `legacy_tldr_brand3` and `tldr_brand3` are different sources and differ in wording and structure:
  - `legacy_tldr_brand3.core_purpose` uses `claim_type=inferred`, `mode=interpreted_from_discourse`; `tldr_brand3` uses `declared/literal`.
- `legacy_tldr_brand3.magnetism` includes concatenated phrasing from evidence capture; `tldr_brand3` has canonical concise sentence.
- `legacy_tldr_brand3.value_proposition` is constrained by audit-derived offer/audience wording and is weaker (`For organisations with dedicated infrastructure...`), while `tldr_brand3` is stronger product-summary style (`A secure, git-based sharing layer...`).
- `legacy_tldr_brand3.attributes`/`values` are structured as short lists; `tldr_brand3` returns flattened prose.
- `legacy_tldr_brand3` has additional metadata (`source_signal`, `source_signal_path`, `evidence_scope`, `observations`), while `tldr_brand3` does not.
- Because `build_client_tldr_v2` was fed `current_tldr=tldr_brand3`, the client-v2 fallback mirrored that version (and not the rawer `legacy_tldr_brand3` object).

## 4) Method gap (verifiable)

1. **Mode mismatch at scan-level artifact**: captured scan artifact for 109 shows `prompt_version=v0.1`, while current runtime constant is `v0.3`. This makes provenance comparison across historical runs ambiguous unless explicitly versioned in report exports.
2. **LLM execution failure path dominates**: despite contract-complete score/context inputs, output was `fallback_client_v2` and not a synthesized editorial rewrite. This means scan 109 does not demonstrate the intended client-safe transformation.
3. **Template remains report-shaped under fallback**: helper output remains audit-shaped when fallback is used, because it reuses legacy block fields and system-readings.
4. **Input source ambiguity between legacy variants**: scan artifacts contain both `legacy_tldr_brand3` and `tldr_brand3`; only the latter is directly used by the v2 helper, so analysts comparing “legacy TLDR” must distinguish which legacy artifact they mean.
5. **Mission/Vision rewrite behavior is not evidenced in this run**: fallback mode leaves these blocks unmodified, so there is no confirmation that v2-specific gap handling (explicit inferred/absent messaging) actually executes.
6. **Methodology output cannot confirm client-v2 mode from API result JSON alone**: persisted scanner result payloads surface `tldr_brand3` but do not expose `generation_mode` or `legacy_tldr_brand3_v2`, so a scan is treated as legacy unless the preview route or diagnostic fixture is consulted.
7. **Fallback state can look like parity while proving no synthesis**: with `fallback_client_v2`, the block text can remain identical and still include valid score readings, creating a false-positive impression unless the mode flag is explicitly consumed in reporting.

## 7) What Client TLDR v2 lacks in this evidence run (scan 109)

1. `fallback_client_v2` path executed; there is no actual LLM editorial normalization output.
2. JSON transport failed before model normalization (`_call_json` DNS/socket error), so rewriting logic was never materialized.
3. No mission/vision rewrite behavior was actually exercised because fallback reused existing block statuses.
4. No proof that the v2 readability/style contract was applied end-to-end (language tone and caveat logic were not validated here).
5. Scan-level persisted API payload still exposes legacy `tldr_brand3`, so consumers cannot verify v2 mode without route-level or diagnostic artifacts.

## 5) Current state verdict

For scan 109, this is a **fallback equivalence state**:

- Same strategic text appears in Client TLDR v2 result and `current_tldr`.
- No evidence of editorial re-synthesis is present.
- Client v2 safety/readability gains are blocked by LLM JSON parse failure.

## 6) Next-step recommendations (priority)

1. Capture and archive the effective `prompt_version`, raw prompt JSON, and normalizer version in every persisted v2 output row for strict replay comparability.
2. Add a hard assertion in diagnostics and UI that `generation_mode==fallback_client_v2` is shown as such in-page and not as “editorial rewrite”.
3. Re-run scan 109 once provider stability is restored, then capture both:
   - normalized v2 JSON
   - and the exact rendered HTML
   to confirm mission/vision and caveat behavior when LLM succeeds.
