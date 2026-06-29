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
