# SV9 Flow -> SV9 Contract Audit

Date: 2026-06-30

## Verdict

Parcialmente correcto. El modulo ya separa Evidence -> Brand Interpretation -> Tile Signals -> SV9 scoring, pero hay autoridad de scoring indirecta en dos puntos:

- `interpretation_llm_worker` puede convertir bloques sensibles en `detected=true` mediante gates deterministas.
- `tile_signal_worker` puede emitir senales negativas de alta confianza que el evaluador SV9 aplica como overrides por baldosa.

Esto no es necesariamente malo. Pero debe tratarse como contrato de scoring indirecto, no como una capa puramente descriptiva.

## Contract Table

| Layer | Authority | Inputs | Outputs | Must Not Do |
|---|---|---|---|---|
| `evidence_worker` | Normalizar evidencia observable | Brand Audit snapshot, Visual Signature evidence | `BrandEvidencePack` | Puntuar, inferir estrategia, inventar refs |
| `block_evidence_worker` | Seleccionar refs candidatas por bloque | `BrandEvidencePack` | shortlists por bloque | Decidir si el bloque existe, puntuar tiles |
| `interpretation_llm_worker` | Redactar/normalizar `brand_interpretation` | Evidence pack, shortlists, LLM | `BrandInterpretation`, debug gates | Crear score SV9, citar refs fuera de shortlist |
| `block_detection_worker` | Gate determinista para bloques sensibles | bloque, refs, evidence pack | `BlockDetectionDecision` | Evaluar tiles o calidad estrategica completa |
| `tile_signal_worker` | Traducir interpretacion a senales por baldosa | `BrandInterpretation`, Visual Signature | `TileSignal[]` | Encender tiles por si solo; los `supports` deben ser advisory |
| `tldr_adapter` | Compatibilidad con SV9 actual | `Sv9FlowCandidate` | payload tipo `tldr_brand3` | Reinterpretar evidencia, cambiar deteccion |
| `sv9.evaluator` | Juicio final por baldosa | tldr, snapshot signals, Flow tile signals | `ComponentResult` | Usar conocimiento externo o aceptar `ok` sin cita |
| `sv9.aggregator` | Score determinista | componentes evaluados | `Sv9ScanResult` | Llamar LLM o cambiar tiles |
| batch/report scripts | Validacion/calibracion | shadow compare JSON | report review/blocker | Ser runtime canonico o calibrar por marca |

## Confirmed Fix

`value_proposition` emitia `value_proposition.PV1`, pero la rubrica SV9 usa `P1..P10`. Se corrigio a `value_proposition.P1` en `src/sv9_flow/tile_signal_worker.py` y se cubrio con test en `tests/test_sv9_flow_contracts.py`.

## Findings

### 1. Sensitive gates can override LLM non-detection

`normalize_llm_interpretation_response` usa la shortlist completa como `policy_refs` para bloques sensibles y puede marcar `detected=true` aunque el LLM no lo haya hecho si el gate soporta deteccion.

Reference: `src/sv9_flow/interpretation_llm_worker.py:213-244`.

Impact:

- Bueno: recupera falsos negativos como Bland mission.
- Riesgo: terminos amplios como `build`, `platform for`, `momentum` pueden promover detecciones por presencia lexical, no por interpretacion robusta.

Decision recomendada:

- Mantener para shadow, pero nombrarlo como "deterministic promotion gate".
- Separar en debug `llm_detected`, `gate_detected`, `final_detected`.

### 2. Negative Flow tile signals are scoring authority

`supports` es advisory, pero `insufficient_evidence` y `weakens` de alta confianza se aplican despues del LLM como override en `sv9.evaluator`.

References:

- `src/sv9_flow/tile_signal_worker.py:85-145`
- `src/sv9/evaluator.py:335-394`

Impact:

- Bueno: evita que el evaluador encienda MG3-MG8 o PR3/PR4 por arrastre del bloque.
- Riesgo: si la senal negativa es demasiado gruesa, apaga muchas baldosas validas.

Decision recomendada:

- Exigir que toda senal negativa de alta confianza sea tile-scoped y explique que evidencia falta.
- No emitir rangos amplios sin clasificar si falta "mecanismo", "hook", "preferencia", "comunidad" o "gravedad".

### 3. Magnetism market-momentum-only is correct but coarse

La regla actual marca MG3-MG8 como `insufficient_evidence` cuando los support terms son solo `momentum`, `funding`, `press`, o `revenue growth`.

Impact in batch v3:

- Corrige sobrepuntuacion de Bland y Mistral.
- Convierte Mafer en blocker porque su magnetism citado es funding/media, no hook/preferencia directa.

Risk:

- Puede ser demasiado conservadora si el evidence pack contiene copy de hook en otras refs, pero la interpretacion magnetism solo cito momentum/funding.

Decision recomendada:

- Mantener por ahora.
- Siguiente mejora: dividir magnetism evidence en tres familias:
  - owned hook/copy/visual: MG1-MG6
  - preference/packaging/comparison: MG7-MG8
  - external gravity/community: MG9-MG10

### 4. Shortlist scoring is substring-based and can admit acquisition noise

`block_evidence_worker` usa coincidencias por substring. Ejemplos de riesgo:

- `engagement` puede aparecer en social scrape failed payloads.
- `vision` puede aparecer en metadata tipo `block_source_guidance`.
- JSON completos de contexto pueden entrar como evidence cuando no hay texto limpio.

Reference: `src/sv9_flow/block_evidence_worker.py:133-174`.

Decision recomendada:

- Introducir source classes antes de scoring: `owned_copy`, `external_proof`, `acquisition_metadata`, `derived_strategy`, `visual_signal`.
- Penalizar o excluir acquisition failure payloads para bloques estrategicos.

### 5. Cached Pass 1 path does not use the same gates

`build_brand_interpretation_from_tldr` normaliza un `tldr_brand3` existente con `truthy_detected`, pero no aplica gates sensibles ni shortlists.

Reference: `src/sv9_flow/interpretation_worker.py:12-52`.

Impact:

- `cached-pass1` and `flow-llm` are not contract-equivalent.
- Batch SV9 Flow v3 used `flow-llm`; a future runtime using cached Pass 1 could behave differently.

Decision recomendada:

- Either mark cached Pass 1 mode as compatibility-only, or route cached TDLR through the same gate normalizer before generating tile signals.

## Batch V3 Read

Report: `tmp/sv9_flow_sv9_batch_report_deploy_v2.md`

Summary:

- acceptable: 1
- review: 7
- blocker: 2
- blockers: `mistral.ai`, `www.mafer.ai`

Interpretation:

- Bland blocker resolved.
- Linear stable at total score.
- Mistral is still +13 because Flow reads stronger primary copy than legacy, not because vision/values are over-detected.
- Mafer is a legitimate unresolved policy decision: whether funding/media plus technical copy should support only MG1/MG10, or also owned-hook MG2-MG6.

## Next Actions

1. Add a debug contract with `llm_detected`, `gate_detected`, and `final_detected`.
2. Refactor magnetism tile signals by evidence family instead of one broad `market_momentum_only` flag.
3. Add source-class scoring to `block_evidence_worker`.
4. Decide whether cached Pass 1 should remain compatibility-only or be normalized through the same gates.
5. Re-run deploy batch after each contract change, not after each brand-specific patch.

## Applied Plan, 2026-06-30

Implemented after this audit:

- `EvidenceRecord.metadata.source_class` for raw inputs, legacy features, and Visual Signature evidence.
- Acquisition-noise penalty/exclusion for shortlist scoring and sensitive block gates.
- Detection provenance per block: `llm_detected`, `gate_detected`, `final_detected`, `final_source`, `gate_reason`.
- Magnetism limitation families:
  - `magnetism_no_owned_hook_evidence` -> MG3-MG6
  - `magnetism_no_preference_evidence` -> MG7-MG8
  - `magnetism_no_belonging_status_evidence` -> MG9
  - `magnetism_no_gravity_evidence` -> MG10
- Cached/provided/live Pass 1 shadow candidates are marked as compatibility-only.
- Batch report now separates `assessment` from `assessment_kind` so contract blockers are not mixed with legacy-delta blockers.

Validation:

- Focused + extended Flow/SV9 tests: `120 passed`.
- Deploy batch v4 output: `tmp/sv9_flow_sv9_batch_report_deploy_v3.md` and `.json`.

Batch v4 read:

- runs: 10
- acceptable: 0
- review: 7
- blocker: 3
- assessment kinds: `legacy_delta_blocker:3`, `legacy_delta_review:3`, `policy_review:4`
- blocker brands: `www.databricks.com`, `www.mafer.ai`, `www.pleo.io`

Interpretation:

- The remaining blockers are not contract blockers; they are score deltas against legacy.
- Linear improved materially: `flow=70`, `legacy=71`, delta `-1`.
- Mistral moved from blocker territory to review: `flow=50`, `legacy=41`, delta `+9`.
- Mafer remains unresolved through magnetism: `flow=51`, `legacy=67`, delta `-16`.
- Pleo is now a positive delta blocker because Flow detects mission/vision that legacy did not: `flow=53`, `legacy=38`, delta `+15`.
- Databricks is a negative delta blocker driven by mission/vision/magnetism differences: `flow=41`, `legacy=56`, delta `-15`.

Next technical focus:

1. Inspect Pleo mission/vision: decide whether Flow is correctly recovering missed legacy detections or over-crediting sparse evidence.
2. Inspect Databricks mission/vision/magnetism: determine whether Flow is too strict or legacy is over-scoring.
3. Inspect Mafer magnetism: decide whether funding/media should support only gravity/status or also any owned-hook/preference mechanism.
