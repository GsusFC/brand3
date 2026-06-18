# Evidence vNext Local Validation — 2026-06-18

Purpose: verify locally, with real configured connectors, whether evidence vNext improves evidence quality without changing production runtime/prompt/persistence behavior.

## Environment

- Branch: `main`
- Local server: `http://127.0.0.1:8000`
- Exa configured: yes
- LLM configured: yes
- Known local warning: pyenv Python 3.11.8 logs missing `blake2b/blake2s`; tests and scripts completed despite the warning.

## Tests

```bash
./.venv/bin/python -m pytest tests/test_evidence_vnext.py tests/test_evidence_semantic_llm.py tests/test_evidence_llm_shadow_script.py tests/test_llm_cache.py tests/test_exa_collector.py tests/test_exa_vnext_bakeoff.py tests/test_magnetism_scanner.py -q
```

Result:

- `178 passed in 39.22s`

## Deterministic vNext Evidence Comparison

Command:

```bash
./.venv/bin/python scripts/compare_evidence_vnext.py 291 286 285 283 282 264 263 248 231 228 --report-json out/evidence_vnext/local_real_vnext_compare.json --report-md out/evidence_vnext/local_real_vnext_compare.md
```

Result over 10 real local Brand Audit runs:

- Accepted: `150`
- Review required: `24`
- Rejected: `99`
- Reclassified to noise: `96`
- Material lost fields: `0`
- Accepted material evidence: `125`
- Accepted weak evidence: `25`
- Contract-blocked observations: `123`

Interpretation:

vNext materially improves evidence hygiene. It rejects or review-gates weak/unsafe evidence without losing material fields in this sample.

## Live Exa Bakeoff

Command:

```bash
./.venv/bin/python scripts/exa_vnext_bakeoff.py --limit 5 --results 5 --output-dir out/evidence_vnext/local_real_exa_bakeoff_5
```

Result:

| Variant | Results | Accepted | Review | Rejected | Accepted rate | Rejected rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current | 121 | 84 | 15 | 20 | 70.6% | 16.8% |
| vnext_precision_plan | 95 | 88 | 7 | 0 | 92.6% | 0.0% |
| vnext_query_plan | 145 | 105 | 23 | 16 | 72.9% | 11.1% |

Interpretation:

The precision Exa query plan is the strongest acquisition candidate in this batch: higher accepted rate and no rejected results.

## Live LLM Semantic Shadow

Command:

```bash
./.venv/bin/python scripts/evidence_llm_shadow.py 291 286 248 --no-cache --output-json out/evidence_vnext/local_real_llm_shadow_3_nocache.json --output-md out/evidence_vnext/local_real_llm_shadow_3_nocache.md
```

Result:

| Run | Brand | Status | Transport | Batches | Attempts | Retries | Seconds |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| 291 | www.becauce.com | ok | gemini_native | 3 | 3 | 0 | 29.79 |
| 286 | guru-usa.com | ok | gemini_native | 4 | 4 | 0 | 27.89 |
| 248 | www.lemlist.com | ok | gemini_native | 1 | 1 | 0 | 7.72 |

Aggregate:

- 3/3 ok
- Total batches: 8
- Total attempts: 8
- Total retries: 0
- Total elapsed: 65.4s
- Semantic class disagreements vs heuristic: 12
- Materiality disagreements vs heuristic: 17

Interpretation:

Gemini native compact structured output is stable in this no-cache sample, but too slow for synchronous scanner runtime. It should remain shadow/asynchronous.

## Local Web Validation

Health:

```text
GET /_health -> {"status":"ok","queue_size":0,"running":0}
```

vNext JSON:

```text
GET /magnetism-scanner/run/291/evidence-vnext -> 200
```

Key fields observed:

- `runtime_effect=false`
- `prompt_effect=false`
- `persistence_effect=false`
- `material_lost_fields=0`
- `semantic_evidence.accepted_material=9`
- `semantic_evidence.accepted_weak=2`

vNext HTML:

```text
GET /magnetism-scanner/run/291/evidence-vnext/view?lang=es -> 200
```

HTML verification found:

- `semantic shadow`
- `llm shadow`
- `gate summary`
- `acquisition matrix`
- `heuristic_shadow_v0`
- `disabled=1`
- `accepted_material`
- `accepted_weak`
- `shadow exclusions`

Scanner from existing Brand Audit run:

```text
POST /magnetism-scanner/from-run run_id=291 -> /magnetism-scanner/{token}/status
ready -> /sv9/scan/29?lang=es in 5s
```

Fetched result:

```text
GET /sv9/scan/29?lang=es -> 200, 67886 bytes
```

Detected in page:

- `SV9`
- `Magnetism`
- `becauce`
- `V9`
- `scan`

## Verdict

Evidence vNext is demonstrably better in local validation:

- It improves deterministic evidence hygiene.
- It preserves material fields in the tested sample.
- The Exa precision plan improves acquisition quality.
- The LLM classifier adds useful semantic disagreement signals, but should stay asynchronous/shadow.
- Local web routes render the diagnostics and can run from an existing Brand Audit snapshot.

Recommended next step: promote the deterministic vNext evidence gate and Exa precision acquisition improvements first; keep LLM semantic classification as a shadow/asynchronous metric until latency is addressed.
