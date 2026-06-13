# Brand3 Capture & Interpretation Integrity — Follow-up (2026-06)

## Purpose

This note updates two earlier audits whose findings have since been partly
addressed in code or refined with data. Read it before acting on them:

- [`brand3_information_acquisition_evidence_flow_audit.md`](brand3_information_acquisition_evidence_flow_audit.md)
  — capture/evidence-mixing gaps. **Several are now fixed (see §1–§2).**
- [`brand3_finding_generation_contract_audit.md`](brand3_finding_generation_contract_audit.md)
  — worry that the model "rationalizes mixed evidence into prose". **Measured
  empirically (see §3): zero fabricated sources.**

Scope of this pass: `URL → brand_service.run → collectors → SQLite snapshot`,
plus a read-only integrity probe of the interpretation layer. Read-only audit;
all code changes below shipped as their own commits.

## §1 Capture reliability fixes shipped

| Ref | Commit | Change |
|---|---|---|
| R1 | `30cd84e` | Screenshots persist to `data/screenshots/` (`BRAND3_SCREENSHOT_DIR`), not the OS temp dir — evidence no longer dies on tmp cleanup |
| R2 | `ce3c5fc` | Enriched web re-save tagged `derived`; cross-run cache skips derived rows so a later run never treats enriched content as a raw capture |
| R3 | `08aafb6` | Acquisition provenance (cache hits, partial/failed sources, `data_quality`) persisted in `run_audits.audit_json` under `acquisition` — previously it died in `output/*.json` and never reached the snapshot consumers |
| R4 | `407bfed` | `runs.status` lifecycle (running/complete/failed/cancelled/interrupted) + startup sweep of orphaned runs |
| R6 | `25ff684` | Consent-wall captures flagged (`WebData.capture_obstruction`, acquisition status `obstructed`) instead of being indistinguishable from an empty/failed fetch |
| R8 | `97166dd` | One retry with backoff on Firecrawl scrape and Exa search (transient failure no longer loses a source for the run) |
| R9 | `3649399` | Corrupt `llm_cache` rows treated as a cache miss instead of crashing the run |

## §2 Product decisions shipped

| Decision | Commit | Change |
|---|---|---|
| Per-source cache TTL | `9abcde5` | `BRAND3_CACHE_TTL_HOURS_BY_SOURCE`: owned-site sources (web/context/hyperbrowser) = 1h so a client who changed their site is not served a stale capture; external perception sources keep 24h |
| Competitor HTML trim | `29911dd` | Competitor raw HTML (~99% of the payload, unused after comparisons) dropped before persisting; brand_web + comparisons kept |
| Visual-evidence flag | `8094f16` | `audit.acquisition.visual_evidence` {captured/skipped/failed/missing} — a capture-layer signal that does NOT touch readiness/scoring |
| Orphan DB | n/a | `data/brand3.db` (empty, gitignored) deleted from the filesystem |

## §3 Interpretation integrity — measured

Question: does the LLM only assert what the captured evidence supports, or does
it fabricate? Method: cross every URL cited in `executive_analysis_v2` against
URLs present in the same run's `raw_inputs` (read-only, no LLM calls).

Result over **159 cited URLs / 18 runs**:

- **94% EXACT** — cited page was actually captured
- **5% domain-only** — right site, uncrawled subpage (e.g. `/sitemap.xml`)
- **0% NOT-CAPTURED** — **zero fabricated sources**

The preventive layer works: `brand_audit_analyst.py` (schema forces
`evidence`/`confidence`/`limitations` "from supplied evidence only") and
`client_tldr_v2.py` (classifies evidence owned/direct/indirect/weak/ambiguous/
off-entity, bars off-entity from positive claims). Of 70 runs, only 18 cite
URLs; the rest use score observations (`"Score: 41.8"` — traceable, not
hallucinable) or paraphrase, not source citations.

**Updates the finding-generation-contract audit:** the contract is healthier
than feared — no source fabrication in the verifiable (URL) axis. A URL
verifier would solve a non-problem.

## §4 What remains (not done — intentional)

- **The narrative harness was deleted (2026-06-14).** `narrative_harness.py`,
  `entity_narrative_state.py`, and the `state_first_findings/prose_generator`
  modules were an offline-only Phase-2 family (`runtime_enabled: False`) with
  zero production callers; the `unsupported_editorial_synthesis` readiness gate
  never received input (`_readiness_inputs_from_snapshot` never populated
  `narrative_summary`, so the gate always saw `{}`). Removed (~63 files incl.
  tests/fixtures) rather than carried as dead code, along with the now-unreachable
  gate plumbing in `report_readiness.py` and `derivation.py`. Its 8 checks were
  prose-quality heuristics — none crossed a claim against `raw_inputs` — so the
  removal dropped **no anti-hallucination safety**. Prose quality is governed in
  the TLDR/SV9 path (`src/features/magnetism/`), which is untouched. Decision:
  developing post-generation prose QC adds nothing now; rebuild if it ever lands
  on the roadmap.
- **Paraphrase-quote fidelity** (non-URL claims like "the copy emphasizes X") is
  unverified — low severity given the 0% URL fabrication; only measurable via
  noisy quote-matching.
- **Criterio** (scoring weights, rubric design, TLDR tone) is a human decision,
  not an audit target. The audit covers integrity (faithful, traceable
  mechanism), not whether the judgment itself is correct.
