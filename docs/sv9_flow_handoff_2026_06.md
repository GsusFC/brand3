# SV9 Flow Handoff — June 2026

## Veredicto

`sv9_flow` existe para reducir la superficie heredada que puede mover SV9 antes de que el score determinista actue.

No estamos intentando crear otro scanner con nombres nuevos. No estamos cambiando la formula de SV9. Estamos intentando que las baldosas se rellenen desde evidencia trazable y decisiones mas estables, no desde prosa TLDR/Pass 1 demasiado variable.

## Situacion actual

El SV9 actual ya tiene un agregador determinista:

```text
tile_profile -> aggregator -> Brand3 Score
```

Una vez que el `tile_profile` esta relleno, el score es codigo:

- cada baldosa `ok` suma;
- `no` y `sin_evidencia` suman 0;
- multiplicadores y cap de Magnetism se aplican por codigo;
- el LLM no decide el score final.

El problema esta antes:

```text
snapshot -> Pass 1 / TLDR -> evaluator LLM por componente -> tile_profile -> score
```

Pass 1/TLDR puede variar. El evaluator recibe esa lectura como input. Si cambian las baldosas resultantes, el score cambia aunque el agregador sea puro.

## Objetivo de `sv9_flow`

Mover el camino hacia:

```text
snapshot
  -> evidence pack
  -> deterministic block shortlists / gates
  -> brand interpretation
  -> tile_signals
  -> tile_profile
  -> deterministic SV9 aggregator
```

Principio rector:

```text
Evidence -> brand interpretation -> tile signals -> SV9
```

SV9 debe depender de baldosas. Las baldosas deben depender de evidencia trazable. La prosa puede variar, pero no debe mover decisiones estructurales ni score.

## Roles de las piezas

- Scanner actual: produccion, baseline y fuente de snapshots.
- Auditor de estabilidad: herramienta para encontrar casos comparables y separar persistencia, adquisicion, interpretacion, scoring y presentacion.
- Pass 1 / TLDR: baseline legacy, no dependencia objetivo de `sv9_flow`.
- Visual Signature: evidencia gated, no score autonomo.
- `sv9_flow`: camino shadow para probar evidence-first antes de tocar producto.

## Estructura actual de `src/sv9_flow`

- `contracts.py`: contratos `BrandEvidencePack`, `EvidenceRecord`, `BrandInterpretation`, `TileSignal`, `Sv9FlowCandidate`.
- `evidence_worker.py`: convierte snapshot en evidencia trazable desde `raw_inputs`, `features` y opcionalmente Visual Signature.
- `block_evidence_worker.py`: selecciona shortlists deterministas de evidencia por bloque.
- `interpretation_llm_worker.py`: unica pieza LLM del flow nuevo; interpreta bloque a bloque usando solo refs permitidas.
- `block_detection_worker.py`: gates deterministas para bloques sensibles: `vision`, `values`, `magnetism`.
- `tile_signal_worker.py`: convierte interpretacion en `supports` / `insufficient_evidence` / señales visuales.
- `reporting.py`: salida compacta para comparar.
- `scripts/sv9_flow_snapshot_eval.py`: harness usado para snapshots del scanner.

## Qué depende de prompts

Depende de prompt:

```text
evidence_pack + block shortlists -> interpretation_llm_worker -> BrandInterpretation
```

El LLM redacta/interpreta bloques, pero solo puede citar `allowed_evidence_refs`.

No depende de prompt:

- construccion del evidence pack;
- seleccion de shortlists;
- gates de `vision`, `values`, `magnetism`;
- mapping de bloques a tile signals;
- comparacion de estabilidad;
- score SV9 una vez existe `tile_profile`.

## Validacion realizada

Produccion fue limpiada antes de usarla como banco de pruebas:

- bug de persistencia entre columnas publicas y `raw_payload` corregido;
- `/data` en Fly ampliado y saneado;
- auditor separa por `exa_strategy`;
- auditor interno desplegado y optimizado para no cargar payloads completos en memoria.

Commits relevantes:

- `066d1ea` — Fix magnetism scan persistence sync
- `e383fc0` — Expose data volume pressure in health check
- `96823aa` — Separate stability audit groups by Exa strategy
- `61fa4da` — Expose internal scanner stability audit
- `8564300` — Limit scanner stability audit data loading
- `f41aeef` — Stream scanner stability audit payloads
- `fd1a174` — Compact scanner stability raw input hashes

Casos probados con `sv9_flow`:

- Pleo scans `263`, `264`, `268`
- Linear scan `215`
- Factorial scan `266`
- mafer.ai scan `22`

Resultado repetido:

- `tile_signal_effects` estable;
- `detected_blocks` estable;
- `block_detection_decisions` estable;
- texto de bloques variable.

Patron observado:

- `supports=6`
- `insufficient_evidence=3`
- detectados: `attributes`, `brand_idea`, `core_purpose`, `mission`, `personality`, `value_proposition`
- gated/bloqueados: `vision`, `values`, `magnetism`

Interpretacion: la redaccion editorial varia, pero las decisiones estructurales se mantienen. Esto es aceptable si SV9 consume señales/baldosas, no prosa libre.

## Decision importante

No hay que perseguir texto identico como objetivo principal.

Es aceptable que el LLM escriba respuestas distintas desde la misma evidencia, igual que distintos estrategas pueden redactar distinto. Lo que debe ser estable es:

- evidencia usada;
- refs/provenance;
- deteccion estructural;
- tile signals;
- tile profile;
- score.

La prosa puede ser explicacion editorial si no contradice la evidencia ni mueve el score.

## Siguiente paso tecnico

Conectar `sv9_flow` con el evaluator de baldosas en modo shadow.

Objetivo:

```text
sv9_flow tile_signals -> contexto para evaluator SV9 -> tile_profile -> aggregator
```

Comparar:

- `tile_profile` legacy vs `tile_profile` alimentado por `sv9_flow`;
- estabilidad de baldosas;
- cambios de Brand3 Score;
- perdida o mejora de criterio;
- casos donde gates demasiado duros apagan marcas conocidas.

No avanzar a produccion hasta demostrar que el nuevo input reduce deriva sin empobrecer diagnostico.

## Riesgo actual

`sv9_flow` esta siendo muy conservador. Incluso Linear queda con `vision`, `values` y `magnetism` como insuficientes. Puede ser correcto por evidencia disponible, pero antes de promocionar hay que revisar si los gates son demasiado duros o si falta mejor evidencia para esos bloques.

## Regla para continuar

No refactorizar por inercia. Cada cambio debe responder a una de estas preguntas:

1. ¿Reduce la dependencia de Pass 1/TLDR para rellenar baldosas?
2. ¿Mejora la trazabilidad evidencia -> baldosa?
3. ¿Reduce deriva de `tile_profile` o score?
4. ¿Distingue mejor `no` de `sin_evidencia`?
5. ¿Permite integrar Visual Signature como evidencia, no como score?

Si no ayuda a una de esas cinco, no pertenece a este tramo.

## Continuacion 2026-06-30

Se conecto `sv9_flow` con SV9 en modo shadow mediante un adapter compatible con el input actual:

```text
sv9_flow candidate
  -> tldr_adapter / magnetism_result compatible
  -> sv9_flow_tile_signal como extra_signals
  -> evaluator SV9 actual
  -> tile_profile
  -> aggregator determinista
```

Archivos principales del tramo:

- `src/sv9_flow/tldr_adapter.py`
- `scripts/sv9_flow_sv9_shadow_eval.py`
- `scripts/sv9_flow_sv9_batch_report.py`
- `tests/test_sv9_flow_sv9_batch_report.py`

Cambios de politica ya aplicados:

- `magnetism` ya no trata fallos de adquisicion social (`failed to scrape`, creditos insuficientes, contadores a cero por scrape fallido) como evidencia negativa de marca.
- `values` acepta lenguaje operativo/cultural real cuando aparece en evidencia propia, como `what unites us`, `relentless focus`, `fast execution`, `deep care`, `craftsmanship`.
- `vision` normaliza saltos escapados en JSON (`\n`, `\t`, `\r`) antes de hacer matching de terminos; esto corrige el falso negativo de Pleo, donde la evidencia contenia `Our vision`.
- Si el gate determinista soporta un bloque sensible pero el LLM devuelve `detected=false`, la normalizacion puede mantener el bloque como evaluable con confianza baja y limitacion explicita `*_llm_detection_overridden_by_gate`.
- Las señales `sv9_flow_tile_signal` negativas de alta confianza ya son guardarrailes deterministas post-LLM: `insufficient_evidence` fuerza `sin_evidencia` y `weakens` fuerza `no`. `supports` sigue siendo solo contexto; no enciende baldosas por si solo.
- `vision` acepta lenguaje de categoria tipo `operating system for ...` como destino identificable cuando aparece en evidencia trazable, lo que corrige Mafer sin relajar Factorial.
- `core_purpose` emite señales `weakens` para baldosas avanzadas cuando el supuesto proposito descansa en mision/vision/oferta generica en vez de evidencia de por que existe la empresa mas alla del producto.
- `magnetism` distingue falta de metricas de retencion/adquisicion de falta de gravedad: prensa/financiacion pueden seguir soportando MG10, mientras que comunidad/lealtad no se infiere sin evidencia directa.

Estado del batch shadow actual:

```text
Reporte: tmp/sv9_flow_sv9_batch_report_v4.md
Runs: 4
Acceptable: 0
Review: 4
Blocker: 0
```

Resumen:

| Marca | Flow | Legacy | Delta | Estado |
|---|---:|---:|---:|---|
| Linear | 82 | 71 | +11 | review |
| Pleo | 50 | 45 | +5 | review |
| Factorial | 54 | 49 | +5 | review |
| Mafer | 55 | 67 | -12 | review |

Lectura tecnica:

- No es promocionable automaticamente, pero el lote actual ya no tiene blockers.
- La calibracion por baldosas redujo Pleo de +20 a +5 y Mafer de -17 a -12.
- El problema dominante que queda es de revision, no de bloqueo: Linear +11, Mafer -12, y deltas de componente grandes en Pleo/Mafer.
- Factorial sigue en review por `vision` añadido como `not_detected`; no relajar sin evidencia literal mas clara.
- El adapter todavia depende del evaluator actual, que sigue leyendo una prosa tipo TLDR. Eso sirve como puente shadow, pero no cumple aun el objetivo final de que la baldosa dependa de evidencia tile-scoped.

Plan restante, en orden:

1. Convertir `tile_signals` de señal de contexto a contrato por baldosa para los componentes de mayor riesgo (`core_purpose`, `magnetism`, `vision`). El objetivo no es puntuar antes del aggregator, sino evitar que una lectura de bloque encienda baldosas no probadas.
2. Separar evidencia de deteccion de evidencia de puntuacion. Detectar `magnetism` o `core_purpose` no debe bastar para encender `MG3-MG8` o `PR2-PR9`.
3. Revisar gates de `vision` con casos reales:
   - Pleo: explicita y ya corregida.
   - Factorial: no relajar sin evidencia literal mas clara.
   - Mafer: probablemente necesita mejor shortlist/evidencia de manifiesto o compañia, no un termino generico nuevo.
4. Revisar `magnetism` por mecanismos:
   - owned hook/retencion (`MG1-MG6`) debe venir de evidencia de primera pantalla/copy/visual.
   - preferencia, pertenencia y gravedad (`MG7-MG10`) deben venir de prueba distinta; no solo de `momentum`.
5. Reejecutar el batch con los mismos cuatro casos y añadir al menos dos marcas adicionales antes de promocionar.
6. Criterio minimo de promocion:
   - 0 blockers en batch;
   - ningun `not_detected` nuevo en `magnetism`, `mission`, `value_proposition` o `core_purpose`;
   - `abs(score_delta) <= 5` para aceptacion directa;
   - deltas 6-12 quedan en revision humana, no promocion automatica;
   - ningun `magnetism` en 10/10 sin evidencia directa de gravedad/pertenencia.

Conclusion: `sv9_flow` ya puede alimentar SV9 en shadow y reportar deltas. Lo que queda no es infraestructura, sino calibracion de contrato evidencia -> baldosa para que el evaluator deje de usar la prosa de interpretacion como atajo.

## Continuacion 2026-06-30, plan aplicado

Se aplico el plan posterior al audit de contrato:

- `source_class` en evidencia SV9 Flow (`owned_copy`, `external_proof`, `derived_strategy`, `acquisition_metadata`, `visual_signal`).
- Penalizacion/exclusion de ruido de adquisicion en shortlists y gates sensibles.
- Proveniencia de deteccion por bloque: `llm_detected`, `gate_detected`, `final_detected`, `final_source`, `gate_reason`.
- Magnetism separado por familias de evidencia:
  - `magnetism_no_owned_hook_evidence` -> MG3-MG6
  - `magnetism_no_preference_evidence` -> MG7-MG8
  - `magnetism_no_belonging_status_evidence` -> MG9
  - `magnetism_no_gravity_evidence` -> MG10
- Los modos shadow basados en `cached-pass1`, `provided-tldr` y `live-pass1` quedan marcados como `*_compatibility_only`.
- El batch report distingue `assessment` de `assessment_kind`; asi un blocker de delta legacy no se confunde con un blocker de contrato.

Validacion:

```text
./.venv/bin/python -m pytest \
  tests/test_sv9_flow_calibration_loop.py \
  tests/test_sv9_flow_evidence_worker.py \
  tests/test_sv9_flow_sv9_batch_report.py \
  tests/test_sv9_flow_block_detection_worker.py \
  tests/test_sv9_flow_block_evidence_worker.py \
  tests/test_sv9_flow_interpretation_llm_worker.py \
  tests/test_sv9_flow_contracts.py \
  tests/test_sv9_flow_architecture.py \
  tests/test_sv9_flow_snapshot_eval.py \
  tests/test_sv9_flow_shadow_run.py \
  tests/test_sv9_flow_local_eval.py \
  tests/test_sv9_flow_decision_report.py \
  tests/test_sv9_service.py \
  tests/test_sv9_evaluator.py

Resultado: 120 passed
```

Batch deploy v4:

```text
Outputs: tmp/sv9_flow_deploy_batch_v4/
Report: tmp/sv9_flow_sv9_batch_report_deploy_v3.md
JSON: tmp/sv9_flow_sv9_batch_report_deploy_v3.json

Runs: 10
Acceptable: 0
Review: 7
Blocker: 3
Assessment kinds: legacy_delta_blocker:3, legacy_delta_review:3, policy_review:4
```

Lectura:

- No quedan `contract_blocker` en el batch; los 3 blockers son deltas contra legacy.
- Linear queda alineada (`70` vs `71`, delta `-1`).
- Mistral baja a review (`50` vs `41`, delta `+9`).
- Mafer sigue siendo blocker negativo por magnetism (`51` vs `67`, delta `-16`).
- Pleo pasa a blocker positivo porque Flow detecta mission/vision que legacy no detectaba (`53` vs `38`, delta `+15`).
- Databricks pasa a blocker negativo por mission/vision/magnetism (`41` vs `56`, delta `-15`).

Siguiente paso recomendado:

1. Auditar Pleo mission/vision: decidir si Flow recupera evidencia real o sobre-credita.
2. Auditar Databricks mission/vision/magnetism: decidir si Flow es demasiado estricto o legacy sobrepuntua.
3. Auditar Mafer magnetism: decidir si funding/media deben soportar solo gravedad/status o tambien mecanismo de hook/preferencia.

## Decision 2026-06-30: Visual Acquisition Layer

La antigua "Visual Signature" queda renombrada conceptualmente como **Visual Acquisition Layer**.

Frontera:

```text
Visual Acquisition Layer
  -> captura y estructura evidencia visual
  -> visual_evidence_packet
  -> SV9 Flow/evaluator interpreta despues
```

No debe emitir autoridad de scoring ni decidir baldosas por si misma. En codigo:

- nuevo raw input source: `visual_acquisition`
- nuevo alias contractual: `visual_evidence_packet`
- compatibilidad legacy: seguir leyendo `visual_signature` y `visual_signature_evidence`
- paquete interno legacy: `src.visual_signature` se mantiene por ahora para evitar un rename masivo.

Regla operativa: Visual Acquisition puede aportar observaciones visuales para `brand_idea` y `coherencia`; cualquier salida sobre magnetism/core_purpose debe tratarse como evidencia debil o diagnostica hasta que exista validacion humana.

## Calibration note 2026-06-30: Baker / Visual Acquisition authority

Caso: `https://withbaker.com/`, Brand Audit run `347`.

Hallazgo:

- Flow SV9 con Visual Acquisition explicito bajo a `36` frente a legacy `42`.
- La bajada no era solo dureza estrategica: `coherencia` caia a `2` porque senales visuales negativas de confianza media (`multimodal_semantics_unavailable`, `copy_visual_alignment:unknown`) llegaban al evaluator como `sv9_flow_tile_signal`.
- Tras filtrar negativas visuales de baja/media confianza, Flow SV9 sube a `48`; `coherencia` vuelve a `6`, mientras siguen cayendo `mission`, `values` y `personality` por ausencia textual real.

Decision:

- Visual Acquisition sigue entrando al evidence pack aunque no emita tile signal.
- `supports` visuales pueden permanecer como contexto advisory.
- `weakens`, `insufficient_evidence` y `blocked` visuales solo pueden emitirse como tile signal si la confianza es `high`.
- Las negativas visuales de confianza `low` o `medium` quedan como evidencia/limitacion de adquisicion, no como guardarrail SV9.

Artefactos locales:

```text
tmp/sv9_flow_withbaker_20260630/flow_sv9_visual_acquisition_summary_347_after_policy.json
tmp/sv9_flow_withbaker_20260630/flow_sv9_visual_acquisition_eval_347_after_policy.json
```

## Calibration note 2026-06-30: Visual Acquisition en ruta estandar

Se incorporo Visual Acquisition a la ruta estandar de `scripts/sv9_flow_sv9_shadow_eval.py`, no solo al harness manual:

- el snapshot se consulta con `visual_evidence_packet_from_snapshot`;
- el paquete visual entra en `build_evidence_pack_from_snapshot`;
- las senales visuales permitidas entran en `build_tile_signals_from_interpretation`;
- el reporte expone `visual_acquisition_present` y `visual_acquisition_schema_version`.

Reejecucion Baker con la ruta estandar:

```text
Input: tmp/sv9_flow_withbaker_20260630/snapshot_347.json
Output: tmp/sv9_flow_withbaker_20260630/flow_sv9_shadow_eval_347_official_after_visual_policy.json

Flow: 48
Legacy: 42
Delta: +6
visual_acquisition_present: true
tile_signals: 20
```

Tambien se corrigio el shortlist de `magnetism`: Visual Acquisition puede seguir en evidencia, pero `magnetism` ahora se trata como bloque de estrategia textual para el ranking de evidencia, de forma que senales visuales/adquisicion no desplacen evidencia de mercado, copy o momentum.

Batch deploy v6 tras esta correccion:

```text
Outputs: tmp/sv9_flow_deploy_batch_v6_visual_shortlist/
Report: tmp/sv9_flow_sv9_batch_report_deploy_v5_visual_shortlist.md
JSON: tmp/sv9_flow_sv9_batch_report_deploy_v5_visual_shortlist.json

Runs: 10
Acceptable: 0
Review: 8
Blocker: 2
Assessment kinds: legacy_delta_blocker:2, legacy_delta_review:2, policy_review:6
Average score delta: -2.3
```

Lectura:

- Airwallex deja de ser blocker: `47` vs `52`, delta `-5`; ya no cae por `magnetism not_detected`.
- Pleo deja de ser contract blocker: `53` vs `41`, delta `+12`; sigue en review por delta legacy positivo.
- Mafer sigue como blocker negativo: `51` vs `67`, delta `-16`; no usa Visual Acquisition en este snapshot.
- Databricks sigue como blocker negativo: `39` vs `55`, delta `-16`; no usa Visual Acquisition en este snapshot.
- Por tanto, los blockers restantes no son regresiones de Visual Acquisition. Son calibracion semantica/delta legacy: Mafer por magnetism/core purpose y Databricks por mission/vision/score legacy.

Decision:

- Mantener Visual Acquisition como capa de adquisicion, no scoring.
- Mantener negativas visuales `low`/`medium` como evidencia, no como tile signals.
- Permitir negativas visuales solo con confianza `high`.
- Mantener penalizacion de Visual Acquisition en shortlists de bloques textuales, incluido `magnetism`.

Validacion actual:

```text
./.venv/bin/python -m pytest \
  tests/test_llm_cache.py \
  tests/test_sv9_flow_calibration_loop.py \
  tests/test_sv9_flow_evidence_worker.py \
  tests/test_sv9_flow_sv9_batch_report.py \
  tests/test_sv9_flow_block_detection_worker.py \
  tests/test_sv9_flow_block_evidence_worker.py \
  tests/test_sv9_flow_interpretation_llm_worker.py \
  tests/test_sv9_flow_contracts.py \
  tests/test_sv9_flow_architecture.py \
  tests/test_sv9_flow_snapshot_eval.py \
  tests/test_sv9_flow_shadow_run.py \
  tests/test_sv9_flow_local_eval.py \
  tests/test_sv9_flow_decision_report.py \
  tests/test_sv9_service.py \
  tests/test_sv9_evaluator.py

Resultado: 122 passed
```

## Calibration note 2026-06-30: Magnetism preference family

Se corrigio una sobre-restriccion en `magnetism`:

- `entity_research_packet` pasa a tratarse como `acquisition_metadata`, no como evidencia estrategica.
- `magnetism` reconoce una familia de preferencia/diferenciacion distinta de momentum/funding/press.
- Una evidencia de preferencia (`differentiator`, `unique`, `reason to choose`, `native integration`, etc.) permite evaluar MG7/MG8.
- El hecho de que el LLM no detecte `magnetism` y el gate lo encienda (`magnetism_llm_detection_overridden_by_gate`) ya no apaga MG3-MG8 por si solo.
- Las familias se apagan solo con limitaciones explicitas:
  - `magnetism_no_owned_hook_evidence` -> MG3-MG6
  - `magnetism_no_preference_evidence` -> MG7-MG8
- Visual Acquisition y otros metadatos de adquisicion quedan excluidos del gate de deteccion de bloques sensibles.

Rerun puntual:

```text
Mafer:      51 vs 67, delta -16
Databricks: 42 vs 52, delta -10
```

Lectura:

- Databricks deja de ser blocker y pasa a review; el delta restante viene de mission/vision: el snapshot evalua sobre homepage/product surface Lakebase, no sobre la pagina corporativa `/company/about-us`.
- Mafer sigue blocker. El cambio permite evaluar preferencia, pero el evaluator sigue dejando MG7/MG8 como punto ciego; el desacuerdo real contra legacy sigue siendo `magnetism` y `core_purpose`, no un bloqueo tecnico de Visual Acquisition ni del gate.

Batch deploy v7:

```text
Outputs: tmp/sv9_flow_deploy_batch_v7_magnetism_preference/
Report: tmp/sv9_flow_sv9_batch_report_deploy_v6_magnetism_preference.md
JSON: tmp/sv9_flow_sv9_batch_report_deploy_v6_magnetism_preference.json

Runs: 10
Acceptable: 1
Review: 8
Blocker: 1
Assessment kinds: acceptable:1, legacy_delta_blocker:1, legacy_delta_review:5, policy_review:3
Average score delta: -0.2
Blocker: www.mafer.ai
```

Estado por marca:

```text
linear.app            70 vs 71  delta -1   review
www.pleo.io          53 vs 41  delta +12  review
www.factorialhr.es   55 vs 49  delta +6   review
www.mafer.ai         51 vs 67  delta -16  blocker
vercel.com           68 vs 67  delta +1   acceptable
www.airwallex.com    45 vs 52  delta -7   review
base44.com           55 vs 56  delta -1   review
www.bland.ai         66 vs 64  delta +2   review
www.databricks.com   42 vs 52  delta -10  review
mistral.ai           53 vs 41  delta +12  review
```

Siguiente paso tecnico:

1. Mafer: decidir si legacy sobrepuntua MG3-MG8/PR3-PR7 o si Flow debe aceptar evidencia de manifiesto/formulacion como hook narrativo real.
2. Databricks: no calibrar scoring todavia; primero mejorar adquisicion de superficie corporativa para que mission/vision usen `/company/about-us` cuando el research packet la descubra.
3. Promocion todavia no recomendable: queda 1 blocker y 8 reviews.

Validacion final del tramo:

```text
Resultado: 127 passed
```

## Calibration note 2026-06-30: sensitive gate refs y severidad de delta

Se corrigio el ultimo blocker del batch v7 sin introducir una regla especifica para Mafer.

Diagnostico:

- El gate determinista de `magnetism` detectaba evidencia de preferencia/diferenciacion en Mafer (`features.14`, `features.15`, `features.16`, `features.11`, ademas de momentum/funding en `features.7`).
- El LLM devolvia al menos una ref propia para `magnetism`.
- La normalizacion de `interpretation_llm_worker` elegia `refs` cuando existian refs del LLM, y por tanto descartaba `policy_refs`.
- Resultado: el gate encendia el bloque, pero el evaluator recibia una version empobrecida de la evidencia y dejaba MG7/MG8 como punto ciego.

Decision aplicada:

- En bloques sensibles detectados por gate, las refs finales son la union estable de `refs + policy_refs`.
- Esto no enciende baldosas por si solo. Solo evita que el evaluator pierda evidencia que ya justifico la deteccion determinista del bloque.

Rerun puntual Mafer:

```text
Output: tmp/sv9_flow_blocker_full_audit/www_mafer_ai_86_after_gate_refs.json

Flow: 55
Legacy: 67
Delta: -12
Estado: review
Refs magnetism: features.7, features.14, features.15, features.16, features.11
Limitacion restante: magnetism_no_owned_hook_evidence
```

Lectura:

- Mafer deja de ser blocker porque MG7/MG8 ya pueden evaluarse con evidencia de preferencia.
- El desacuerdo restante sigue siendo real: falta evidencia de owned hook/retencion para MG3-MG6 y core_purpose sigue mas estricto que legacy.
- No hay base para relajar MG3-MG6 solo con funding, prensa o integraciones nativas.

Tambien se corrigio la severidad del batch report:

- `score_delta < -12` queda como blocker (`legacy_delta_blocker`).
- `score_delta > 12` queda como review (`legacy_delta_review`).
- `vision`/`values` añadidos como `not_detected` siguen visibles en el reporte, pero no fuerzan review por si solos si no hay delta material de score o componente.
- Una recuperacion positiva de componente desde `legacy not_detected` tampoco fuerza review por si sola cuando el delta total sigue en margen; se conserva como cambio visible en la tabla de componentes.

Razon: un delta positivo grande contra legacy puede ser recuperacion de evidencia real, no una regresion operativa. Debe revisarse, pero no bloquear como si fuera una caida de calidad.

Caso auditado: Mistral

```text
Output: tmp/sv9_flow_blocker_full_audit/mistral_ai_235_v8_full.json

Flow: 57
Legacy: 41
Delta: +16
Estado: review
```

Lectura:

- Flow recupera evidencia explicita de mision que legacy no estaba usando con la misma fuerza.
- El delta +16 no es una regresion negativa; es un desacuerdo grande con legacy que requiere revision humana.

Batch deploy v8:

```text
Outputs: tmp/sv9_flow_deploy_batch_v8_sensitive_gate_refs/
Report: tmp/sv9_flow_sv9_batch_report_deploy_v8_sensitive_gate_refs.md
JSON: tmp/sv9_flow_sv9_batch_report_deploy_v8_sensitive_gate_refs.json

Runs: 10
Acceptable: 3
Review: 7
Blocker: 0
Assessment kinds: acceptable:3, legacy_delta_review:5, policy_review:2
Average score delta: +1.5
```

Estado por marca:

```text
base44.com           57 vs 56  delta +1   acceptable
linear.app            70 vs 71  delta -1   review
www.pleo.io          53 vs 41  delta +12  review
www.factorialhr.es   55 vs 49  delta +6   review
www.mafer.ai         55 vs 67  delta -12  review
vercel.com           69 vs 67  delta +2   acceptable
www.airwallex.com    49 vs 52  delta -3   acceptable
www.bland.ai         66 vs 64  delta +2   review
www.databricks.com   44 vs 52  delta -8   review
mistral.ai           57 vs 41  delta +16  review
```

Lectura adicional:

- Airwallex pasa a acceptable porque el unico motivo automatico restante era una recuperacion positiva de `core_purpose` desde legacy `not_detected`; Flow ya debilita las baldosas avanzadas de proposito generico y el score total queda en margen.
- Bland sigue en policy review, pero ahora por `magnetism` negativo (`MG3-MG6` sin evidencia de owned hook), no por recuperacion positiva de `core_purpose`.
- Linear sigue en policy review por bajada material de `core_purpose`.
- Se probo una regla mas agresiva para tratar propositos funcionales/product-bound como debiles, pero se descarto: en batch experimental `tmp/sv9_flow_deploy_batch_v9_core_purpose_policy/` produjo `core_purpose not_evaluated` y `reliability_status=broken` en Linear, Vercel y Bland. No usar ese batch como baseline.

Validacion:

```text
./.venv/bin/python -m pytest \
  tests/test_sv9_flow_evidence_worker.py \
  tests/test_sv9_flow_sv9_batch_report.py \
  tests/test_sv9_flow_block_detection_worker.py \
  tests/test_sv9_flow_block_evidence_worker.py \
  tests/test_sv9_flow_interpretation_llm_worker.py \
  tests/test_sv9_flow_contracts.py \
  tests/test_sv9_flow_architecture.py \
  tests/test_sv9_flow_snapshot_eval.py \
  tests/test_sv9_flow_shadow_run.py \
  tests/test_sv9_flow_local_eval.py \
  tests/test_sv9_flow_decision_report.py \
  tests/test_sv9_service.py \
  tests/test_sv9_evaluator.py

Resultado: 157 passed
```

Estado de promocion:

- El batch ya no tiene blockers.
- Todavia no es promocion automatica: 7/10 marcas siguen en review.
- El siguiente trabajo debe atacar motivos de review, no blockers: `policy_review` por deltas materiales de componente y `legacy_delta_review` por desacuerdos 6-12 o positivos mayores de 12.

## Calibration loop v1 2026-06-30

Se creo una primera herramienta offline para acelerar calibracion sin lanzar mas LLM por defecto:

```text
scripts/sv9_flow_calibration_loop.py
```

Entrada:

```text
JSONs de scripts/sv9_flow_sv9_shadow_eval.py
```

Salida:

```text
cohort_manifest.json
cost_observation.json
batch_report.json
batch_report.md
review_queue.json
review_queue.md
loop_summary.md
```

Artefacto generado sobre el batch v8:

```text
tmp/sv9_flow_calibration_loop_v1_deploy_v8/
```

Resumen:

```text
Cohort: deploy_v8_sensitive_gate_refs
Runs: 10
Acceptable: 3
Review: 7
Blocker: 0
Review queue items: 7
Priority counts: P1:4, P2:2, P3:1
Cost observability: call_count_estimate_only
Estimated LLM calls upper bound without cache: 290
Gate override count: 5
```

Review queue:

```text
P1 linear.app           core_purpose   full audit before rules
P1 www.bland.ai         magnetism      full audit before rules
P1 www.databricks.com   mission        full audit before rules
P1 www.mafer.ai         magnetism      full audit before rules
P2 www.factorialhr.es   attributes     golden subset / human judgement
P2 www.pleo.io          brand_idea     golden subset / human judgement
P3 mistral.ai           coherencia     positive legacy delta review
```

Guardrails del loop:

- `flow_not_evaluated` o `reliability_status=broken` ahora es `technical_blocker` en el batch report, no solo P0 en la cola.
- El batch report expone `gate_overrides` desde `flow.interpretation_debug.detection_provenance`.
- Los `gate_override` no son scoring por si solos: se reportan siempre, y solo fuerzan `policy_review` si afectan un componente core con delta material (`abs(delta) >= 4`).
- En v8 hay 5 overrides observados: `magnetism` en Linear, Bland, Factorial y Pleo; `mission` en Databricks. Solo Bland/magnetism y Databricks/mission fuerzan review por delta material.

Coste:

- La herramienta no ejecuta nuevas llamadas LLM.
- Desde este handoff, `LLMAnalyzer` mantiene `usage_observations` en memoria por llamada: `cache_hit`, `cache_miss`, `provider_call`, `cache_write`, modelo, tipo de respuesta, schema y `usage_metadata` si el provider lo expone.
- `scripts/sv9_flow_sv9_shadow_eval.py` serializa esas observaciones en `llm_usage` por rol: `flow_interpretation`, `sv9_evaluator` y `sv9_reasoning` cuando aplica.
- `scripts/sv9_flow_calibration_loop.py` usa `llm_usage` si existe y entonces marca `cost_observability=observed_call_count`.
- El batch v8 historico se genero antes de esta instrumentacion; por eso su artefacto actual sigue marcando `cost_observability=call_count_estimate_only`.
- La estimacion actual es por conteo de llamadas planificadas: `9` bloques de interpretacion Flow + `10` componentes SV9 Flow + `10` componentes legacy por marca con compare.
- La cache persistente existe; en nuevos payloads el loop podra separar `cache_hits`, `cache_misses`, `cache_writes` y `provider_calls`.

Decision:

- Antes de ampliar a 30-50 marcas, usar este loop para preparar la cohorte y estimar llamadas.
- Siguiente mejora necesaria: ejecutar un mini-batch nuevo de 2-3 marcas con la instrumentacion activa para verificar que `llm_usage` aparece en payloads reales antes de lanzar 30-50 marcas.

## Usage probe v1 2026-06-30

Se ejecuto un mini-batch nuevo con la instrumentacion activa:

```text
tmp/sv9_flow_usage_probe_v1/
```

Cohorte:

```text
base44.com
linear.app
www.databricks.com
```

Resultado de calidad:

```text
Runs: 3
Acceptable: 1
Review: 2
Blocker: 0
Assessment kinds: acceptable:1, legacy_delta_review:1, policy_review:1
Gate override count: 2
```

Resultado de coste/uso:

```text
cost_observability: observed_call_count
estimated upper bound without cache: 87
observed cache_hits: 87
observed cache_misses: 0
observed cache_writes: 0
observed provider_calls: 0
usage_metadata_available: false
flow_interpretation cache_hits: 27
sv9_evaluator cache_hits: 60
```

Lectura:

- La instrumentacion funciona en payloads reales: `llm_usage` se serializa y el calibration loop lo consume.
- En esta cohorte no hubo gasto incremental de provider: todo fue cache hit.
- Aun no hay tokens/coste monetario porque no hubo `provider_call`; cuando haya llamadas reales, solo habra tokens si el provider devuelve `usage`/`usageMetadata`.
- El siguiente batch de 30-50 ya puede reportar llamadas/cache reales. Para presupuesto monetario exacto aun falta una tabla de precios por modelo o metadata de coste del provider.

## Controlled batch v1 2026-06-30

Se intento ampliar a 30 marcas desde snapshots locales con corte operativo:

```text
script: scripts/sv9_flow_controlled_batch.py
output: tmp/sv9_flow_controlled_30_v1/
provider_call_limit: 300
```

Resultado:

```text
requested: 30
completed: 13
stopped_reason: provider_call_limit_exceeded:327>300
acceptable: 0
review: 5
blocker: 8
assessment kinds:
  contract_blocker: 7
  legacy_delta_blocker: 1
  legacy_delta_review: 3
  policy_review: 2
```

Coste/uso observado:

```text
cost_observability: observed_call_count
estimated upper bound without cache: 377
provider_calls: 327
cache_hits: 51
cache_misses: 314
cache_writes: 310
flow_interpretation provider_calls: 93
sv9_evaluator provider_calls: 234
usage_metadata_available: false
```

Lectura de calidad:

- No esta listo para promocion ni para ampliar sin corregir contrato: 8/13 blockers.
- El patron dominante es `blocking_not_detected_added:mission` en 7/13.
- Esto indica que, fuera del golden set, Flow esta dejando `mission` como `not_detected` mucho mas a menudo que legacy/SV9 espera.
- El siguiente trabajo no debe ser mas batch: debe auditar `mission` en los P0 (`Brandty`, `withbaker.com`, `GetProsper`, `Staris`, `Becauce`, `Cofisolutions`, `Hermes`) y decidir si:
  - Flow esta siendo demasiado estricto al detectar mission;
  - legacy sobre-detectaba mission;
  - o los snapshots tienen evidencia pobre y el blocker policy debe distinguir `mission missing` aceptable de regression real.

Nota tecnica:

- El runner se corrigio despues del batch para cortar con `provider_calls >= limit`; en esta ejecucion empezo una marca extra porque el limite estaba como `>`.

## Mission gate recheck 2026-07-01

Se auditaron los 7 P0 dominados por `blocking_not_detected_added:mission`.

Hallazgo:

- En la mayoria de casos Flow no estaba detectando `mission` porque el gate era demasiado estrecho/anglocentrico.
- La evidencia no era una pagina "Our mission", pero si habia mision operativa suficiente:
  - Brandty: `somos especialistas`, `especialistas en`.
  - Baker: `we decided to create`, `decidimos crear`.
  - COFI: `specializes in`, `convertimos`.
  - Prosper: `so your team can`.
  - CAUCE: `diseñados para`.
  - Staris: `proves which`, `ships the fix`, `cuts noise`.
  - Hermes: `open-source agent that`, `self-improving ai agent`, `focused automation`.

Cambio aplicado:

- Se amplio `mission` en `src/sv9_flow/block_detection_worker.py` con patrones operativos trazables, no con terminos genericos.
- Tests añadidos en `tests/test_sv9_flow_block_detection_worker.py` para español, healthcare ops, AppSec y agent/product mission language.

Recheck consolidado:

```text
output: tmp/sv9_flow_mission_gate_recheck_consolidated/
runs: 7
acceptable: 0
review: 7
blocker: 0
assessment kinds:
  policy_review: 1
  legacy_delta_review: 6
cost_observability: observed_call_count
estimated upper bound without cache: 203
review queue:
  P1: 1
  P2: 5
  P3: 1
```

Lectura:

- El problema de contrato de `mission` queda resuelto para este grupo: 7/7 P0 dejan de ser blockers.
- No significa promocion automatica: tras hacer visible `positive_core_recovery_review`, ningun caso queda acceptable. Staris vuelve a review aunque su delta total sea +4, porque `core_purpose` pasa de legacy `not_detected` a Flow `scored` con delta +6.
- La cola queda mas util: GetProsper es P1 por delta negativo en `values`/`vision`; Baker, COFI, Staris, CAUCE y Hermes son P2 por recuperacion positiva de `core_purpose`; Brandty queda P3 por delta positivo/magnetism.
- Siguiente trabajo real: auditar `core_purpose` recuperado contra refs fuente antes de promocionar. Esto es diagnostico de calibracion, no cambio de scoring.

## Core purpose recovery audit 2026-07-01

Se creo una herramienta offline para auditar recuperaciones core desde payloads full sin cambiar scoring:

```text
script: scripts/sv9_flow_core_recovery_audit.py
output:
  tmp/sv9_flow_core_purpose_recovery_audit/core_purpose_recovery_audit.json
  tmp/sv9_flow_core_purpose_recovery_audit/core_purpose_recovery_audit.md
```

Nota de coste: para regenerar payloads full se registraron 9 intentos `provider_call` en Hermes; 8 terminaron `ok` y 1 fue `http_error`. Baker, COFI, Staris y CAUCE fueron cache hit.

Como Gemini via compatibilidad OpenAI no devolvio `usage_metadata`, el precio solo puede estimarse por escenario de tokens. Se añadio:

```text
script: scripts/llm_usage_cost_report.py
output: tmp/sv9_flow_core_purpose_recovery_audit/hermes_llm_cost_report.json
```

Estimacion para Hermes con `gemini-3.5-flash`:

```text
low  (2k input + 0.5k output por llamada OK): $0.0600
mid  (6k input + 1k output por llamada OK):   $0.1440
high (12k input + 2k output por llamada OK):  $0.2880
```

No contabilizar el `http_error` como billable sin factura/provider metadata. Si Google lo facturase parcialmente, el coste real podria ser algo mayor.

Resultado sobre los cinco P2 de `core_purpose`:

```text
items: 5
risk counts:
  uses_non_owned_refs: 5
  product_or_offer_bound_language: 5
  no_explicit_why_beyond_product_language: 5
  duplicate_owned_copy_refs: 3
```

Lectura:

- Las cinco recuperaciones de `core_purpose` tienen evidencia owned copy, pero la prosa generada por Flow se parece mas a "que hace/vende la empresa" que a "por que existe mas alla del producto".
- El evaluator esta encendiendo muchas baldosas PR a partir de esa prosa:
  - Baker: `PR1, PR2, PR4, PR5, PR6, PR8, PR9`.
  - COFI/Staris/Hermes: `PR1, PR2, PR5, PR6, PR8, PR9`.
  - CAUCE: `PR1, PR2, PR3, PR4, PR5, PR6, PR8, PR9`.
- Hermes mostro drift al regenerar: legacy paso de `not_detected` a `scored` con score `0` y sin lit tiles. La herramienta trata ese caso como recuperacion auditable porque semanticamente legacy no aporta proposito puntuado.

Decision actualizada:

- Se aplico una primera regla experimental en `src/sv9_flow/tile_signal_worker.py`: si `core_purpose` usa lenguaje product-bound/oferta y no contiene evidencia explicita de "why beyond product", emite `weakens` para `PR3`, `PR4`, `PR7`, `PR8` y `PR9`.
- La regla no apaga `PR1`, `PR2`, `PR5` ni `PR6`; por tanto conserva un proposito funcional basico, pero evita que la oferta de producto cuente como proposito avanzado.
- Test añadido en `tests/test_sv9_flow_contracts.py` con caso Baker-like.

Experimento `core_purpose_policy_v1`:

```text
output: tmp/sv9_flow_core_purpose_policy_v1/
runs: 5
acceptable: 0
review: 5
blocker: 0
assessment kinds:
  legacy_delta_review: 2
  policy_review: 3
provider calls: 4 ok / 0 non-ok
estimated cost:
  low:  $0.0300
  mid:  $0.0720
  high: $0.1440
```

Impacto:

- Baker: `core_purpose` baja de +7 a +4; score total baja de `60` a `57`, pero sigue review por delta total +15 y `magnetism +4`.
- COFI: `core_purpose` baja de +6 a +4; score total queda `51` vs `46`, delta +5.
- CAUCE: `core_purpose` baja de +8 a +4; score total queda `52` vs `48`, delta +4.
- Hermes: deja de ser recuperacion core en la regeneracion actual; queda review por delta +10 y `personality +4`.
- Staris no cambia: su formulacion `provides continuous AppSec validation...` no activa la regla actual. No ampliar terminos todavia sin revisar golden subset, porque podria sobrepenalizar propositos operativos legitimos.

Validacion:

```text
tests/test_sv9_flow_contracts.py
tests/test_sv9_flow_core_recovery_audit.py
tests/test_sv9_flow_sv9_batch_report.py
tests/test_sv9_flow_calibration_loop.py
tests/test_sv9_evaluator.py

Resultado: 62 passed
```

Decision actualizada v2:

- Se sustituyo la ampliacion por terminos por una regla mas defensible: si `core_purpose` duplica sustancialmente `mission` o `value_proposition`, y no hay evidencia explicita de "why beyond product", se debilitan las PR avanzadas.
- Esto captura Staris sin introducir una lista amplia de terminos AppSec/producto.
- Implementacion: `src/sv9_flow/tile_signal_worker.py` calcula solapamiento de tokens estrategicos entre `core_purpose` y bloques adyacentes. Hay normalizacion limitada para el patron auditado (`prove/fix/ship`) y plurales simples.
- Test añadido en `tests/test_sv9_flow_contracts.py` con caso Staris-like.

Experimento `core_purpose_policy_v2`:

```text
output: tmp/sv9_flow_core_purpose_policy_v2/
runs: 5
acceptable: 0
review: 5
blocker: 0
assessment kinds:
  legacy_delta_review: 2
  policy_review: 3
provider calls: 5 ok / 0 non-ok
estimated cost:
  low:  $0.0375
  mid:  $0.0900
  high: $0.1800
```

Impacto v2:

- Staris: `core_purpose` baja de +6 a +4; score total baja de `60` a `58`, delta total `+2`.
- Baker, COFI y CAUCE mantienen el ajuste v1: `core_purpose +4`.
- Hermes sigue fuera de recuperacion core; pendiente por `personality +4` y delta total +10.

Lectura:

- El exceso de `core_purpose` en los cinco P2 queda reducido a proposito funcional basico (`PR1`, `PR2`, `PR5`, `PR6`) y las PR avanzadas (`PR3`, `PR4`, `PR7`, `PR8`, `PR9`) quedan apagadas cuando no hay evidencia distinta de mission/value proposition.
- No hay blockers introducidos.
- No promocionar aun: el loop mantiene 5/5 en review porque la politica exige revisar recuperaciones core aunque bajen a +4.

Validacion:

```text
tests/test_sv9_flow_contracts.py
tests/test_sv9_flow_core_recovery_audit.py
tests/test_sv9_flow_sv9_batch_report.py
tests/test_sv9_flow_calibration_loop.py
tests/test_sv9_evaluator.py

Resultado: 63 passed
```

## GetProsper P1: diagnostico de adquisicion, no de gates

Contexto:

- En `tmp/sv9_flow_mission_gate_recheck_consolidated/`, GetProsper quedo como P1 por delta negativo en componentes sensibles (`values` y `vision`).
- El payload de auditoria `tmp/sv9_flow_getprosper_p1/getprosper_311_full_compare.json` confirma que el LLM intento detectar ambos bloques, pero los gates estructurales los rechazaron:
  - `values`: `final_source=gate_rejected`, `gate_reason=values_structural_gate_rejected`.
  - `vision`: `final_source=gate_rejected`, `gate_reason=vision_structural_gate_rejected`.
- La evidencia disponible en el snapshot hacia que el rechazo fuera correcto:
  - `values` era una inferencia desde beneficios/posicionamiento, no una lista o lenguaje explicito de valores.
  - `vision` leia como producto/mission/value proposition, no como vision a largo plazo.

Hallazgo:

- La homepage de GetProsper contiene un link navegacional a `https://www.getprosper.ai/blog/manifesto`.
- Ese link era visible en el HTML del snapshot, pero no entro en `owned_surfaces`; el entity research packet tenia `/company`, case studies y otras superficies, pero no el manifesto.
- La clasificacion ya trataria `/blog/manifesto` como `mission_about`; el fallo estaba en la seleccion previa de links internos:
  - `manifesto` era rol `about`, pero no tenia peso positivo en `_score_internal_links`.
  - `/blog/manifesto` heredaba penalizacion de `blog` y quedaba filtrado o por debajo de `/company`.

Cambio aplicado:

- `src/collectors/web_collector_support_linking_runtime.py`
  - `manifesto`: +12
  - `mission`: +10
  - `principles`: +10
- Esto permite que un manifesto estrategico sobreviva a la penalizacion de `/blog` y gane frente a `/company` dentro del rol `about`, sin ampliar genericamente el cupo de subpaginas.

Validacion:

```text
tests/test_feature_extractors.py -k 'select_internal_links_to_crawl or score_internal_links'
Resultado: 4 passed

tests/test_entity_research_packet.py
Resultado: 3 passed
```

Verificacion contra snapshot real:

```text
run_id: 311
selected:
  https://www.getprosper.ai/use-cases
  https://www.getprosper.ai/blog/manifesto
  https://www.getprosper.ai/case-studies
  https://www.getprosper.ai/case-study/obgyn-ai-voice-agent
manifesto_in_links: True
manifesto_in_selected: True
```

Decision:

- No relajar `values` ni `vision` gates por GetProsper.
- El siguiente paso empirico es rerun de GetProsper desde adquisicion para medir si el manifesto aporta evidencia real a `values`/`vision`.
- Ese rerun tiene coste LLM/red; no asumir mejora de score hasta observar el payload nuevo.

## GetProsper rerun 2026-07-01: manifesto adquirido y usable por Flow

Rerun de adquisicion:

```text
brand: GetProsper
url: https://www.getprosper.ai
new run_id: 349
output: tmp/sv9_flow_getprosper_acquisition_rerun/
```

Resultado de adquisicion:

- `https://www.getprosper.ai/blog/manifesto` entra en `owned_fallback_urls`.
- El `entity_research_packet` clasifica el manifesto como:

```text
role: mission_about
entity_scope: parent_brand
```

Segundo bug encontrado:

- La adquisicion capturaba el manifesto completo, pero `src/sv9_flow/evidence_worker.py` reducia cada raw input a los primeros 700 caracteres.
- Como el manifesto estaba al final del blob agregado de `raw_inputs.web`, Flow solo veia la navegacion `Company Manifesto`, no el contenido.
- Sintoma en payload: el LLM decia que el manifesto estaba referenciado pero no capturado, aunque el raw input si lo contenia.

Cambio aplicado:

- `src/sv9_flow/evidence_worker.py`
  - separa bloques `--- ## Subpage: <url>` en records propios;
  - chunking de subpaginas owned con refs estables tipo `raw_inputs.1.subpage.2.chunk.4`;
  - conserva `url`/`subpage_url` para trazabilidad.
- `src/sv9_flow/block_evidence_worker.py`
  - `vision` shortlist reconoce lenguaje aspiracional de manifesto: `manifesto`, `goal`, `succeed`, `transform`;
  - `values` shortlist reconoce `believe`/`conviction`.
- `src/sv9_flow/block_detection_worker.py`
  - `vision` gate acepta patrones owned y concretos de manifesto:
    - `our goal is`
    - `if we succeed`
    - `transform the experience`

Validacion de shortlist contra run 349:

```text
values shortlist:
  raw_inputs.1.subpage.2.chunk.4  https://www.getprosper.ai/blog/manifesto

vision shortlist:
  raw_inputs.1.subpage.2.chunk.5  https://www.getprosper.ai/blog/manifesto
  raw_inputs.1.subpage.2.chunk.2  https://www.getprosper.ai/blog/manifesto
  raw_inputs.1.subpage.2.chunk.3  https://www.getprosper.ai/blog/manifesto
  raw_inputs.1.subpage.2.chunk.4  https://www.getprosper.ai/blog/manifesto
```

Resultado SV9 Flow final:

```text
payload: tmp/sv9_flow_getprosper_acquisition_rerun/getprosper_349_full_compare_after_vision_gate.json
batch report: tmp/sv9_flow_getprosper_acquisition_rerun/final_batch_report.json

Flow:   63
Legacy: 43
Delta:  +20
Assessment: review
Kind: legacy_delta_review
Reasons:
  - positive_score_delta_gt_12
  - component_delta_gte_4:magnetism
```

Componentes relevantes:

```text
values:         Flow scored, Legacy not_detected, delta +5
vision:         Flow scored, Legacy scored,       delta  0
mission:        Flow scored, Legacy scored,       delta +1
core_purpose:   Flow scored, Legacy scored,       delta -2
magnetism:      Flow scored, Legacy scored,       delta +4
not_detected:   Flow []
```

Gate provenance:

```text
values: llm_confirmed_by_gate, support_terms: we believe
vision: llm_confirmed_by_gate, support_terms: our goal is, if we succeed, transform the experience
mission: llm_confirmed_by_gate, support_terms: enable, build, platform for
```

Coste observado en el compare final:

```text
provider call attempts: 13
provider call ok: 10
provider call non-ok: 3
usage metadata available: false
estimated cost:
  low:  $0.0750
  mid:  $0.1800
  high: $0.3600
```

Nota: el Brand Audit reducido previo tambien uso LLM en feature extraction, pero no expone metadata monetaria comparable en este reporte. No mezclar ese coste con el coste observado del shadow compare.

Lectura:

- GetProsper deja de ser P1 negativo por `values`/`vision`.
- La correccion no demuestra promocion: el caso queda en review por delta positivo grande (+20) y `magnetism +4`.
- La recuperacion de `values` y `vision` parece materialmente correcta: viene de manifesto owned, refs trazables y gate determinista confirmado.
- El siguiente punto a auditar no es `values`/`vision`; es si `magnetism +4` esta sobre-creditando Series A / diferenciacion o si legacy estaba infrapuntuando.

Validacion:

```text
tests/test_feature_extractors.py -k 'select_internal_links_to_crawl or score_internal_links'
Resultado: 4 passed

tests/test_entity_research_packet.py
tests/test_sv9_flow_evidence_worker.py
tests/test_sv9_flow_block_evidence_worker.py
tests/test_sv9_flow_block_detection_worker.py
tests/test_sv9_flow_contracts.py
Resultado: 62 passed
```

## GetProsper magnetism audit 2026-07-01

Diagnostico:

- Flow subia `magnetism` de legacy `1` a Flow `5` (`+4`).
- El evaluator encendia:

```text
MG1, MG2, MG7, MG8, MG9
```

- Las señales deterministas ya bloqueaban correctamente `MG3-MG6` por falta de owned hook/mechanism.
- El problema restante era `MG9`: se encendia por estatus percibido desde funding/diferenciacion (`$30M Series A led by a16z`, uniqueness/competitor terms), aunque no habia evidencia directa de comunidad, pertenencia, orgullo, estatus de usuario o advocacy.

Decision:

- Funding/press/diferenciacion pueden ayudar a detectar `magnetism` o soportar preferencia (`MG7/MG8`) si hay evidencia.
- No deben encender por si solos:
  - `MG9` pertenencia/status;
  - `MG10` gravedad/pull;
  - ni los mecanismos owned `MG3-MG6`.

Cambio aplicado:

- `src/sv9_flow/interpretation_llm_worker.py`
  - `_magnetism_family_limitations()` ahora emite:
    - `magnetism_no_belonging_status_evidence` cuando no hay comunidad, customer love/reviews, user/follower/audience growth o word of mouth.
    - `magnetism_no_gravity_evidence` cuando no hay demand/traction/market pull/funding/press/revenue growth.
- `src/sv9_flow/tile_signal_worker.py` ya sabia convertir esas limitaciones en `insufficient_evidence` para `MG9` y `MG10`; faltaba alimentar las limitaciones.

Resultado GetProsper tras la correccion:

```text
payload: tmp/sv9_flow_getprosper_acquisition_rerun/getprosper_349_full_compare_after_magnetism_family.json
batch report: tmp/sv9_flow_getprosper_acquisition_rerun/final_batch_report_after_magnetism_family.json

Flow:   61
Legacy: 43
Delta:  +18
Assessment: review
Kind: legacy_delta_review
Reasons:
  - positive_score_delta_gt_12
```

Magnetism queda:

```text
score_delta: +3
lit_added: MG1, MG7, MG8
blind_spot_added: MG3, MG4, MG5, MG6, MG9, MG10
```

Lectura:

- La sobre-promocion concreta de `MG9` queda corregida.
- `magnetism` ya no fuerza review por `component_delta_gte_4`.
- GetProsper sigue en review solo por delta positivo total `+18`, dominado por recuperaciones reales de `values` (+5) y varios ajustes positivos menores.
- No promocionar por una marca: este caso ahora valida la cadena adquisicion -> chunking -> gate -> tile signals, pero hay que rerun del grupo P1/P2 antes de ampliar.

Coste observado del compare final:

```text
provider call attempts: 1
provider call ok: 1
provider call non-ok: 0
estimated cost:
  low:  $0.0075
  mid:  $0.0180
  high: $0.0360
```

Validacion:

```text
tests/test_sv9_flow_interpretation_llm_worker.py
tests/test_sv9_flow_contracts.py
tests/test_sv9_evaluator.py
tests/test_sv9_flow_block_detection_worker.py
tests/test_sv9_flow_evidence_worker.py
tests/test_sv9_flow_block_evidence_worker.py
Resultado: 113 passed
```

## CAUCE evidence hygiene 2026-07-01

Contexto:

- Al filtrar el TLDR manual de CAUCE contra Flow real se uso `run_id=291` (`https://www.becauce.com`).
- El score correcto tras la politica de `core_purpose` ya era Flow `52` vs legacy `48`, delta `+4`, review por `positive_core_recovery_review:core_purpose`.
- Al inspeccionar el compare completo aparecio un bug de higiene: chunks de subpaginas `404 Not Found` entraban como evidencia addressable (`raw_inputs.*.subpage.*`) y podian terminar en refs de bloques como `mission`.

Cambio aplicado:

- `src/sv9_flow/evidence_worker.py` ahora descarta subpaginas cuyo contenido inicial es una pagina `404/Not Found` antes de crear chunks.
- Test añadido en `tests/test_sv9_flow_evidence_worker.py`: homepage valida + subpagina missing conserva `raw_inputs.0` y descarta `raw_inputs.0.subpage.1.chunk.1`.

Resultado CAUCE tras el filtro:

```text
output: tmp/sv9_flow_cauce_real_scoring_v2_after_404_filter/
brand: www.becauce.com
run_id: 291
Flow: 52
Legacy: 48
Delta: +4
Assessment: review
Kind: policy_review
Reasons: positive_core_recovery_review:core_purpose
not_detected: vision, values
provider_calls in rerun: 0 (cache hit)
```

Refs limpias verificadas:

```text
mission_refs: raw_inputs.1, raw_inputs.2, raw_inputs.6, features.20
not_found_records: []
```

Lectura:

- Esto no cambia la decision estrategica sobre CAUCE: sigue siendo review sano, no blocker.
- Si se usa el TLDR manual como candidato estrategico, no debe entrar como scoring directo; necesita refs por bloque.
- El valor del cambio es contractual: evita que paginas de error contaminen la trazabilidad y estabiliza futuros reruns.

Validacion:

```text
tests/test_sv9_flow_evidence_worker.py
tests/test_sv9_flow_interpretation_llm_worker.py
tests/test_sv9_flow_contracts.py
tests/test_sv9_evaluator.py
tests/test_sv9_flow_block_detection_worker.py
tests/test_sv9_flow_block_evidence_worker.py
Resultado: 114 passed
```

## P1/P2 rerun after CAUCE/GetProsper 2026-07-01

Objetivo:

- No ampliar a 30-50 marcas todavia.
- Primero rerun del grupo P1/P2 afectado por adquisicion/evidencia y por recuperaciones positivas de `core_purpose`.

Runs:

```text
withbaker.com                  run_id 347
www.cofisolutions.com          run_id 343
Staris                         run_id 297
www.becauce.com                run_id 291
hermes-agent.nousresearch.com  run_id 285
GetProsper                     run_id 349
```

Primer rerun:

```text
output: tmp/sv9_flow_p1_p2_rerun_after_getprosper_cauce_v1/
runs: 6
acceptable: 0
review: 6
blocker: 0
provider_calls: 49
estimated cost:
  low:  $0.3675
  mid:  $0.8820
  high: $1.7640
```

Hallazgo:

- Staris volvio a `core_purpose +8` por drift de formulacion:
  - v2 anterior: `Staris provides continuous AppSec validation...`
  - rerun actual: `Staris delivers automated penetration testing and continuous security validation...`
- La regla de solapamiento no lo capturaba, aunque seguia siendo proposito funcional/product-bound.
- Hermes tambien volvia a `core_purpose +8` con una variante funcional:
  - `open-source, autonomous agent... persistent memory... auto-generate skills... platforms and messaging interfaces`.

Cambio aplicado:

- `src/sv9_flow/tile_signal_worker.py`
  - añade detector estructural de `core_purpose` funcional/producto:
    - verbos de entrega/automatizacion/diseno/ejecucion (`delivers`, `automates`, `designed to`, `features`, `running across`, etc.);
    - sustantivos de producto/sistema (`platform`, `service`, `workflow`, `security validation`, `agent`, `memory`, `skills`, `interfaces`, etc.).
  - Si no hay lenguaje de conviccion/why beyond product, mantiene PR basicas pero debilita PR avanzadas (`PR3`, `PR4`, `PR7`, `PR8`, `PR9`).
- Tests añadidos:
  - Staris-like functional product purpose.
  - Hermes-like agent feature purpose.

Efecto medido:

```text
Staris:
  antes: Flow 62 vs legacy 56, delta +6, core_purpose +8
  despues: Flow 58 vs legacy 56, delta +2, core_purpose +4

Hermes:
  antes: Flow 76 vs legacy 58, delta +18, core_purpose +8
  despues: Flow 72 vs legacy 58, delta +14, core_purpose +4
```

Batch final del tramo:

```text
output: tmp/sv9_flow_p1_p2_rerun_after_agent_core_policy_v3/
runs: 6
acceptable: 0
review: 6
blocker: 0
assessment kinds: legacy_delta_review:3, policy_review:3
average score delta: +9.83
provider_calls in final rerun: 0 (cache hit)
```

Estado final:

```text
withbaker.com                  58 vs 42  delta +16  review
www.cofisolutions.com          51 vs 46  delta +5   review
Staris                         58 vs 56  delta +2   review
www.becauce.com                52 vs 48  delta +4   review
hermes-agent.nousresearch.com  72 vs 58  delta +14  review
GetProsper                     61 vs 43  delta +18  review
```

Lectura:

- No hay blockers en el grupo P1/P2.
- La sobrepromocion de `core_purpose` avanzado queda reducida para Staris/Hermes sin crear reglas por marca.
- Todavia no es promocionable:
  - Baker sigue con delta +16.
  - Hermes sigue con delta +14, ahora dominado por `personality +5` y deltas positivos secundarios.
  - GetProsper sigue con delta +18; su recuperacion de `values` parece real, pero el delta total exige revision.
- Siguiente auditoria antes de ampliar:
  - Baker: decidir si delta +16 es recuperacion real de atributos/coherencia/magnetism o sobrecredito.
  - Hermes: auditar `personality +5`; revisar si PE2/PE4/PE7/PE9/PE10 estan justificados por evidencia o por prosa de evaluator.
  - GetProsper: revisar delta positivo total con foco en `values +5` y `magnetism +3`.

Validacion:

```text
tests/test_sv9_flow_contracts.py
tests/test_sv9_flow_evidence_worker.py
tests/test_sv9_evaluator.py
tests/test_sv9_flow_interpretation_llm_worker.py
tests/test_sv9_flow_block_detection_worker.py
tests/test_sv9_flow_block_evidence_worker.py
Resultado: 116 passed
```

## Personality tile id contract fix 2026-07-01

Hallazgo:

- Durante la auditoria de Hermes `personality +5` se encontro un bug contractual menor:
  - `src/sv9_flow/tile_signal_worker.py` emitia `personality.P1`.
  - La rubrica SV9 usa tiles `PE1..PE10` para `personality`.
- El efecto era advisory (`supports`), no un override determinista, pero el contrato debe emitir IDs validos.

Cambio aplicado:

- `_TLDR_TO_TILE["personality"]` cambia de:

```text
personality.P1
```

a:

```text
personality.PE1
```

- Test añadido: todas las tile signals emitidas desde `BrandInterpretation` deben tener prefijo `component.` y un tile id existente en `src.sv9.rubric.tile_ids(component)`.

Rerun de impacto:

```text
output: tmp/sv9_flow_p1_p2_rerun_after_personality_tile_id_fix_v4/
runs: 6
acceptable: 0
review: 6
blocker: 0
assessment kinds: legacy_delta_review:4, policy_review:2
provider_calls: 6
estimated cost:
  low:  $0.0450
  mid:  $0.1080
  high: $0.2160
```

Estado tras fix:

```text
withbaker.com                  57 vs 42  delta +15
www.cofisolutions.com          52 vs 46  delta +6
Staris                         59 vs 56  delta +3
www.becauce.com                52 vs 48  delta +4
hermes-agent.nousresearch.com  73 vs 58  delta +15
GetProsper                     62 vs 43  delta +19
```

Lectura:

- No introduce blockers.
- Cambia algunos scores 1 punto porque el advisory signal ahora usa un tile valido.
- Hermes sigue siendo review grande, ahora `personality +6`; requiere juicio humano o regla especifica de personality si se demuestra sobrecredito.
- GetProsper queda como el delta positivo mayor (`+19`), pero ya se sabe que `values +5` viene de manifesto owned y gates trazables.

Validacion:

```text
tests/test_sv9_flow_contracts.py
tests/test_sv9_flow_evidence_worker.py
tests/test_sv9_evaluator.py
tests/test_sv9_flow_interpretation_llm_worker.py
tests/test_sv9_flow_block_detection_worker.py
tests/test_sv9_flow_block_evidence_worker.py
Resultado: 117 passed
```

## Baker / GetProsper review audit 2026-07-01

Baker (`run_id=347`):

```text
current output: tmp/sv9_flow_p1_p2_rerun_after_personality_tile_id_fix_v4/withbaker_com_347_sv9_shadow_compare.json
full debug: tmp/sv9_flow_p1_p2_rerun_after_agent_core_policy_v3/withbaker_347_full_current_debug.json

Flow: 57
Legacy: 42
Delta: +15
Assessment: review
Kind: legacy_delta_review
```

Lectura:

- No se encontro bug claro de scoring.
- El delta se reparte entre:
  - `core_purpose +4`, ya limitado a PR basicas;
  - `magnetism +3`, con MG3-MG6/MG9/MG10 bloqueados como blind spots;
  - `attributes +2`;
  - `coherencia +2`;
  - `mission/value_proposition` menores.
- Visual Acquisition esta presente, pero no parece estar forzando magnetism:
  - existe un `supports` visual antiguo hacia `magnetism.MG5`;
  - el override determinista de `insufficient_evidence` mantiene MG5 como blind spot, no lit.
- Por tanto Baker queda como review humano por delta positivo grande, no como candidato a regla nueva.

GetProsper (`run_id=349`):

```text
current output: tmp/sv9_flow_p1_p2_rerun_after_personality_tile_id_fix_v4/getprosper_349_sv9_shadow_compare.json
full debug: tmp/sv9_flow_p1_p2_rerun_after_personality_tile_id_fix_v4/getprosper_349_full_current_debug.json

Flow: 62
Legacy: 43
Delta: +19
Assessment: review
Kind: legacy_delta_review
```

Componentes principales:

```text
values:            +5  legacy not_detected -> Flow scored
attributes:        +3
magnetism:         +3
value_proposition: +3
personality:       +2
core_purpose:      -2
```

Lectura:

- La recuperacion de `values` y `vision` viene del manifesto owned:
  - `At Prosper AI, we believe...`
  - `Our goal is to build an orchestration platform...`
  - `We believe that people who are really serious about the patient experience should go beyond the front door...`
  - `If we succeed...`
- Los gates estructurales estan confirmados:
  - `values:supports_detection(we believe)`
  - `vision:supports_detection(our goal is, if we succeed, transform the experience)`
- El uso de evidencia de producto en `VA4` no es necesariamente bug: la rubrica define VA4 como valores demostrados por copy, producto o decisiones publicas del snapshot.
- El delta +19 sigue siendo grande, pero parece un desacuerdo real con legacy por evidencia nueva de manifesto y proof, no una sobrepromocion obvia del Flow.

Decision:

- No introducir nuevas reglas por Baker ni GetProsper.
- Mantener ambos como review humano/golden subset:
  - Baker: revisar si legacy estaba infrapuntuando el reposicionamiento AI-agency.
  - GetProsper: validar humanamente si manifesto justifica `values=5/5` y `vision=5/5`; tecnicamente la trazabilidad es fuerte.

## Staris magnetism P1 audit 2026-07-01

Contexto:

- Tras el batch `personality_tile_id_fix_v4`, la review queue marcaba Staris como P1:

```text
Staris: Flow 59 vs legacy 56, delta +3
P1 reason: negative_core_component_delta_lte_minus_4
focus: core_purpose, magnetism
```

Full audit:

```text
full debug: tmp/sv9_flow_p1_p2_rerun_after_personality_tile_id_fix_v4/staris_297_full_current_debug.json
```

Resultado de `magnetism`:

```text
Flow magnetism:   4
Legacy magnetism: 8
Delta:           -4

Flow lit:   MG1, MG2, MG7, MG8
Flow blind: MG3, MG4, MG5, MG6, MG9, MG10

Legacy lit: MG1, MG2, MG3, MG5, MG6, MG7, MG8, MG10
Legacy off: MG4, MG9
```

Lectura:

- Legacy enciende MG3/MG5/MG6 desde una frase funcional:

```text
Every finding ships with a working exploit and a PR-ready patch — built for AppSec teams shipping fast.
```

- Flow conserva lo defendible:
  - MG1/MG2 por gancho y promesa clara.
  - MG7/MG8 por preferencia/diferenciacion real.
- Flow bloquea lo que no esta probado:
  - MG3-MG6: no hay suficiente evidencia de mecanismo owned/hook desplegado como sistema de magnetismo mas alla de la propuesta funcional.
  - MG9: no hay comunidad/status/pertenencia.
  - MG10: no hay gravedad externa suficiente en el snapshot actual.

Decision:

- No cambiar reglas por Staris.
- El `magnetism -4` parece una correccion de sobrepuntuacion legacy, no un falso negativo de Flow.
- La etiqueta P1 de la review queue es correcta como alerta, pero el caso queda resuelto por juicio: strictness aceptable.
- Staris puede pasar a golden subset/human review, no a calibracion tecnica inmediata.
