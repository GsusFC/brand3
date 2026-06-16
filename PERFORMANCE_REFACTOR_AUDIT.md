# Auditoría de Rendimiento y Refactorización — Brand3

**Fecha:** 2026-06-14 · **Modo:** solo lectura (sin cambios aplicados) · **Alcance:** worktree `capture-quick-fixes` @ `efad33f`

## Nota de alcance y método

- Audito el worktree `capture-quick-fixes` (HEAD `efad33f`), que está **1 commit por delante de `main`**. Ese único commit elimina la familia offline `narrative_harness` / `state_first_*` / `entity_narrative_state`. **El código vivo de producción es idéntico** entre este branch y `main` salvo esa poda de código muerto.
- **Importante:** varios archivos `state_first_findings_generator.py`, `state_first_prose_generator.py`, `entity_narrative_state.py` **ya no existen en este worktree** (sí en `main`/repo padre). Cualquier "hallazgo" sobre ellos queda **fuera de alcance** — ya resuelto por `efad33f`. Sí sobrevive `src/reports/narrative.py` (relevante por la nota de fork-safety, ver F4).
- **No hay profiling.** Es read-only y el pipeline depende de APIs externas de pago (Firecrawl/Exa/LLM). Por tanto **toda afirmación de "es lento" es una hipótesis estática basada en el patrón de código, no una medición.** La Fase 1 (observabilidad) y las Métricas existen precisamente para convertir estas hipótesis en números antes de optimizar a ciegas.
- Cada hallazgo cita `archivo:línea` verificado de primera mano sobre el filesystem del worktree.

---

## Resumen ejecutivo

El proyecto es un pipeline de *brand scoring* en Python (~73k LOC en `src/`, FastAPI + SQLite + Firecrawl/Exa/Playwright/LLM + Jinja2). La arquitectura es sana en lo fundamental: el trabajo pesado (scrape→features→score→LLM) corre **fuera del event loop** vía `asyncio.to_thread` en la cola de workers, y existe caché LLM persistente con clave SHA256. Los cuellos de botella **no** están en algoritmos exóticos sino en tres patrones repetidos y muy localizables:

1. **Abuso de `SQLiteStore()` efímero.** La clase re-ejecuta el DDL completo (301 líneas) + relee y re-`executescript` todos los `migrations/*.sql` **en cada instanciación**, y se instancia ~47 veces — incluido **una vez por cada lectura/escritura de caché LLM** (≈16-20 veces por run). Coste invisible pero multiplicado.
2. **SQLite síncrono ejecutado directamente sobre el event loop de FastAPI** en el middleware de rate-limit y en handlers de lectura/ensamblaje de `web/`. Bajo concurrencia, una lectura lenta congela *toda* la app, no solo una petición.
3. **Serialización total donde hay paralelismo trivial:** las 5 dimensiones de features (~8-10 llamadas LLM) corren en serie, y los colectores externos (Firecrawl/Exa) hacen fan-out secuencial — multiplicando latencia *y* coste de API.

Ninguno requiere reescritura. Los de mayor ratio impacto/riesgo son cambios quirúrgicos de pocas líneas. Las recomendaciones estructurales (paralelizar) ya tienen un patrón probado en el propio repo (`sv9/evaluator.py`). El mayor riesgo a vigilar es la **contradicción de fork-safety en macOS** documentada en `narrative.py` antes de paralelizar llamadas LLM.

---

## Hallazgos prioritarios

### H1 · `SQLiteStore` reconstruye todo el esquema + migraciones en cada llamada a caché LLM
- **Severidad:** Alta
- **Archivos:** `src/features/llm_analyzer.py:364-400` · `src/storage/sqlite_store.py:140-163`
- **Código/patrón observado:**
  ```python
  # llm_analyzer.py — en CADA _cache_get y _cache_save:
  from src.storage.sqlite_store import SQLiteStore   # import dinámico
  store = SQLiteStore(BRAND3_DB_PATH)                 # → dispara __init__ completo
  ...
  store.close()
  # sqlite_store.py:140-147 — __init__ SIEMPRE:
  self._init_schema()                # executescript de ~301 líneas DDL
  self._ensure_inline_table_columns()
  self._apply_file_migrations()      # :160-162 lee y executescript TODOS los .sql del disco
  ```
- **Por qué afecta (hipótesis estática):** cada llamada LLM con caché abre un `SQLiteStore` nuevo (get + save) y cada apertura parsea el DDL completo y **relee del disco + `executescript`** todos los `migrations/*.sql`. Con ~8-10 llamadas LLM por run son ~16-20 ciclos de "reconstruir esquema" redundantes por run. Los `CREATE ... IF NOT EXISTS` son no-ops semánticos, pero el parseo SQL y la IO de migraciones se pagan íntegros. *Convergencia: detectado de forma independiente por 2 ejes de auditoría y por la observación de memoria 5805.*
- **Riesgo de cambiarlo:** Bajo-Medio. Reutilizar conexión entre hilos NO es opción (`check_same_thread=True`); el fix correcto es saltar la re-inicialización del esquema, no compartir conexión.
- **Refactor recomendado:** (a) guard de "esquema ya inicializado" por proceso/`db_path` (p.ej. `PRAGMA user_version` o flag de clase) que evite `_init_schema`/`_apply_file_migrations` tras la primera vez; (b) reutilizar un handle de `SQLiteStore` por instancia de `LLMAnalyzer` en vez de abrir/cerrar por lookup.
- **Cómo validar:** test que cuente invocaciones a `executescript` al crear N stores (debe ser 1, no N); diff byte-a-byte de un reporte antes/después; confirmar que el esquema sigue creándose en una DB virgen.
- **Tests:** suite completa (`pytest`), foco en `tests/` de storage y llm_analyzer; añadir test de "schema init once".

### H2 · SQLite síncrono ejecutado sobre el event loop de FastAPI (`web/`)
- **Severidad:** Alta
- **Archivos:** `web/middleware/rate_limit.py:61` · `web/storage.py:35-60` · `web/routes/status.py:38` · `web/routes/scanner_api.py:281-351` · `web/routes/magnetism_scanner.py:1054-1202`
- **Código/patrón observado:**
  ```python
  async def rate_limit_middleware(request, call_next):        # corre EN el loop
      ...
      count = count_recent_analyses_for_ip(ip, hours=...)     # :61 sqlite3 síncrono, sin to_thread
  ```
  Y los handlers de lectura/ensamblaje (`async def`) hacen `SQLiteStore(...).get_run_snapshot(...)` + construcción de dossier/TLDR **inline, sin un solo `await`**.
- **Por qué afecta (hipótesis estática):** en un `async def` (middleware o handler), cualquier IO bloqueante ocupa el event loop de forma cooperativa. El rate-limit corre en **cada `POST /analyze`**; `/r/{token}/status` es el endpoint de *polling* (se llama repetidamente por cada análisis en curso). Bajo N peticiones concurrentes + writes WAL de los workers, estas lecturas serializan y una lenta congela *toda* la app (polling, vistas de reporte, nuevos análisis). *Confirma observación de memoria 5801 ("CRITICAL: synchronous SQLite ... on FastAPI event loop").* Matiz que reduce el peor caso: el analizador de reportes en esos handlers es un stub no-op, así que **no** hay llamada LLM síncrona en el loop.
- **Riesgo de cambiarlo:** Bajo. `asyncio.to_thread(...)` no cambia la semántica; convertir handlers de solo-lectura a `def` los manda al threadpool de Starlette sin tocar su lógica.
- **Refactor recomendado:** familia de un solo fix — sacar las llamadas del loop: `await asyncio.to_thread(count_recent_analyses_for_ip, ...)` en el middleware, y convertir los handlers de lectura pura (`status.py`, listings) a `def`.
- **Cómo validar:** test de carga local con K clientes haciendo polling mientras corre 1 análisis (medir p95 de `/status`); verificar que rate-limit sigue contando igual.
- **Tests:** `tests/` de web/rate-limit y listings; smoke de endpoints con TestClient.

### H3 · `get_llm_cache` hace `UPDATE`+`commit` en cada acierto (write en path de lectura) y falta `busy_timeout`
- **Severidad:** Alta
- **Archivos:** `src/storage/sqlite_store.py:796-805` · PRAGMA en `~:222-225` (solo `journal_mode=WAL`)
- **Código/patrón observado:**
  ```python
  # dentro de get_llm_cache, tras encontrar la fila:
  self.conn.execute("UPDATE llm_cache SET hit_count = hit_count + 1, last_hit_at = ? WHERE cache_key = ?", (now, cache_key))
  self.conn.commit()      # :805 — fsync en CADA hit de caché
  ```
- **Por qué afecta (hipótesis estática):** una operación conceptualmente de *lectura* (consultar caché) dispara una transacción de escritura con `commit`/fsync en cada acierto. Con varios `brand3-worker-{i}` concurrentes en WAL y **sin `PRAGMA busy_timeout`**, una colisión por el único write-lock de SQLite devuelve `SQLITE_BUSY` inmediatamente en vez de reintentar. El contador `hit_count` es telemetría: no necesita consistencia inmediata. Es perf **y** fiabilidad.
- **Riesgo de cambiarlo:** Bajo. `hit_count` best-effort no afecta a la lógica de scoring.
- **Refactor recomendado:** diferir/batchear el `UPDATE hit_count` (o hacerlo sin `commit` por hit); añadir `PRAGMA busy_timeout=5000` en `__init__`.
- **Cómo validar:** test de aciertos concurrentes simulando 2+ conexiones; confirmar que el valor de caché devuelto no cambia y que no salta `database is locked`.
- **Tests:** storage + un test nuevo de concurrencia de caché.

### H4 · Pipeline de features 100% secuencial (~8-10 llamadas LLM en serie)
- **Severidad:** Alta
- **Archivos:** `src/services/feature_pipeline.py:100-152` (orquestación) · `src/features/{coherencia,diferenciacion,percepcion,vitalidad}.py`
- **Código/patrón observado:** los 5 extractores se invocan uno tras otro (`presencia` → `vitalidad` → `coherencia` → `diferenciacion` → `percepcion`), y los 4 con LLM hacen 1-3 llamadas HTTP cada uno (timeout 35s), todas en serie.
- **Por qué afecta (hipótesis estática):** las 4 dimensiones LLM son juicios **independientes** entre sí. En serie, el wall-clock es la suma (~20-60s) y, como corre vía `to_thread` en la cola, **un único request retiene un worker thread durante todo el ciclo**, tapando el throughput de la cola. *Confirma observación de memoria 5803.*
- **Riesgo de cambiarlo:** **Medio-Alto** — ver F4 (fork-safety macOS). El patrón seguro ya existe en el repo: `sv9/evaluator.py:140` y `sv9/editorial.py:94` usan `ThreadPoolExecutor`+`pool.map` gateado por env-var (`SV9_*_MAX_WORKERS`).
- **Refactor recomendado:** paralelizar las dimensiones LLM con `ThreadPoolExecutor` gateado por env-var (default conservador), replicando el patrón SV9. **Requisito previo:** resolver la contradicción de fork-safety (F4) — `narrative.py:187-195` defaultea a `max_workers=1` por un crash Objective-C en macOS, pero SV9 ya paraleliza sin mitigación visible.
- **Cómo validar:** golden test que compare el dict de features serial vs paralelo (deben ser idénticos); ejecutar en macOS dev y en Linux para confirmar ausencia de crash.
- **Tests:** `tests/` de feature_pipeline + extractores; test de equivalencia serial/paralelo.

### H5 · Índices ausentes en las FK `run_id` / `brand_id` (path de lectura central)
- **Severidad:** Alta (escala con el histórico)
- **Archivos:** `src/storage/sqlite_store.py` — tablas `features`, `scores`, `raw_inputs`, `annotations` (sin índice en `run_id`); `runs.brand_id`. `get_run_snapshot` (~`:1364-1488`).
- **Código/patrón observado:** SQLite **no crea índice automático para FOREIGN KEY**. `get_run_snapshot` lanza varios `SELECT ... WHERE run_id = ?` sobre tablas sin índice en esa columna, y `list_brands` hace `JOIN`/subqueries por `runs.brand_id` sin índice.
- **Por qué afecta (hipótesis estática):** cada `WHERE run_id = ?` es un **full table scan** cuyo coste crece con el **total histórico** de filas, no con las del run. `get_run_snapshot` es el path central (lo usan replay, provenance, brand_service, api, magnetism). Hoy puede ser imperceptible; degrada de forma monótona al crecer la DB.
- **Riesgo de cambiarlo:** Bajo. Añadir índices es aditivo y reversible; coste de escritura marginal en estas tablas.
- **Refactor recomendado:** `CREATE INDEX` en `features(run_id)`, `scores(run_id)`, `raw_inputs(run_id)`, `annotations(run_id)`, `runs(brand_id, started_at)` (vía migración idempotente).
- **Cómo validar:** `EXPLAIN QUERY PLAN` antes/después (debe pasar de `SCAN` a `SEARCH USING INDEX`); diff de resultados de `get_run_snapshot`.
- **Tests:** storage; verificar que las migraciones siguen siendo re-ejecutables.

### H6 · Fan-out de colectores externos secuencial (latencia × coste de API)
- **Severidad:** Media-Alta (impacto en coste monetario)
- **Archivos:** `src/collectors/competitor_collector.py:283-290` · `src/collectors/web_collector.py:673,734-762` · `src/collectors/exa_collector.py:446-482`
- **Código/patrón observado:**
  ```python
  for comp in result.competitors:          # hasta 5 competidores
      web_data = self.web.scrape(comp.url)  # crawl_subpages=True por defecto → +4 subpáginas c/u
  # exa_collector: 4 búsquedas (2 de type="deep") estrictamente en serie
  ```
  Ningún colector usa concurrencia (`grep ThreadPoolExecutor src/collectors` = 0).
- **Por qué afecta (hipótesis estática):** 5 competidores × (1+4 subpáginas) = hasta **25 scrapes Firecrawl secuenciales** (cada uno timeout 60s), y luego truncados a 30k chars (gran parte del crawl se computa y se tira). Exa hace 4 llamadas independientes en serie, 2 de ellas `deep` (las más caras/lentas). Multiplica latencia *y* gasto de API.
- **Riesgo de cambiarlo:** Medio. Los clientes son síncronos → usar `ThreadPoolExecutor`, no asyncio. Hay que respetar rate-limits de los proveedores.
- **Refactor recomendado:** (a) `crawl_subpages=False` en el scrape de competidores (su contenido se trunca de todos modos); (b) paralelizar el bucle de competidores y las 4 búsquedas Exa con `ThreadPoolExecutor`.
- **Cómo validar:** mockear los clientes y verificar mismo conjunto de resultados con orden estable; medir nº de llamadas API (debe bajar con `crawl_subpages=False`).
- **Tests:** `tests/` de collectors con dobles de Firecrawl/Exa.

### H7 · `save_reviewed_score` construye el snapshot completo del run dos veces
- **Severidad:** Media
- **Archivos:** `src/storage/sqlite_store.py:~1585,~1598` · `src/scoring/replay.py:~231`
- **Código/patrón observado:** `save_reviewed_score` llama `get_run_snapshot(run_id)` y luego `build_score_replay_audit(self, run_id)`, que **vuelve a llamar** `get_run_snapshot(run_id)` internamente.
- **Por qué afecta (hipótesis estática):** `get_run_snapshot` lanza ~5 SELECT y hace `json.loads` de cada blob de `raw_inputs` (hay evidencia en memoria de blobs ~38KB, obs. 5362). Llamarlo dos veces duplica queries y re-parseo de blobs grandes en la misma operación.
- **Riesgo de cambiarlo:** Muy bajo. Trabajo duplicado determinista.
- **Refactor recomendado:** pasar el `snapshot` ya cargado: `build_score_replay_audit(self, run_id, snapshot=snapshot)`.
- **Cómo validar:** diff del `reviewed_score` persistido antes/después; contar llamadas a `get_run_snapshot` (de 2 a 1).
- **Tests:** scoring/replay.

### H8 · Llamadas LLM duplicadas con el mismo input (positioning+uniqueness, messaging+tone)
- **Severidad:** Media (coste de tokens)
- **Archivos:** `src/features/diferenciacion.py:277-284,363-371` · `src/features/coherencia.py:339-347,498-506`
- **Código/patrón observado:** dentro de un extractor, dos métodos LLM reciben **el mismo `prompt_input`** (mismo Research Pack hasta 6000 chars + mismos snippets de competidores) en dos round-trips separados.
- **Por qué afecta (hipótesis estática):** se pagan los input tokens dos veces y se incurre en dos latencias de inferencia donde una sola llamada con schema combinado (ambos veredictos) bastaría. *Relacionado con obs. 5424: prompts de entrada ya identificados como el driver real de coste, no `max_tokens`.*
- **Riesgo de cambiarlo:** Medio. Cambia la forma del prompt/schema → hay que revalidar la calidad del juicio LLM.
- **Refactor recomendado:** fusionar cada par en un único `_call_json` con schema de dos sub-veredictos. (Bonus: evita threads, sortea la fork-safety de F4.)
- **Cómo validar:** A/B de calidad sobre un set de marcas conocidas; comparar veredictos y scores con el baseline.
- **Tests:** extractores coherencia/diferenciacion; A/B manual de calidad LLM.

---

## Quick wins (bajo riesgo, alto ratio, pocas líneas)

1. **H7 — doble snapshot:** pasar `snapshot` a `build_score_replay_audit`. ~5 queries + N parseos de blob menos por reviewed-score. Cambio trivial.
2. **Import lazy de `firecrawl`** (`web_collector.py:19`, `social_collector.py:20`, `visual_analyzer.py:27`): mover `from firecrawl import Firecrawl` dentro del método (como ya se hace con Playwright). El agente midió **~330ms de arranque** que paga *todo* flujo de colectores aunque no use Firecrawl. *(Medido por el auditor, no solo hipótesis.)*
3. **H3 — `PRAGMA busy_timeout=5000`** en `SQLiteStore.__init__`: una línea, mejora fiabilidad bajo concurrencia.
4. **H3 — `hit_count` best-effort:** quitar el `commit` por hit de caché LLM.
5. **`_load_dimension_labels()`** (`src/reports/derivation.py`): es un dict constante reconstruido 4-5 veces por reporte (una dentro del bucle de dimensiones). Promover a constante de módulo.
6. **`crawl_subpages=False`** en el scrape de competidores (parte de H6): recorte directo de llamadas Firecrawl sin pérdida (el contenido se trunca a 30k igualmente).

## Refactors de impacto medio (más cuidado / validación)

- **H1 — guard de schema-init + reuso de store en `LLMAnalyzer`.** Requiere asegurar que una DB virgen sigue creándose y que no se rompe el aislamiento por hilo.
- **H2 — sacar SQLite del event loop** (`to_thread` en middleware + handlers de lectura a `def`). Toca varios archivos de `web/`; validar con test de carga.
- **H5 — índices FK** vía migración idempotente. Verificar `EXPLAIN QUERY PLAN`.
- **H6 — paralelizar colectores** con `ThreadPoolExecutor` (respetar rate-limits de proveedores).
- **H8 — fusionar pares de llamadas LLM** con schema combinado. Requiere A/B de calidad.
- **Deduplicación de helpers:** `_reconcile_*_score` es byte-idéntico en 4 extractores (`coherencia.py:128`, `percepcion.py:131`, `vitalidad.py:348`, `diferenciacion.py:168`); `_extract_domain`/`_clean_string_list` duplicados en 2+. Extraer a `src/features/_shared.py`. Mantenibilidad: un fix corrige los 4 sitios y evita divergencia silenciosa.
- **Escaneos múltiples sobre la misma colección:** `dimension_confidence.py:79-142` recorre `records` 4× por dimensión; `evidence_packet.py:775-781` rescanea `classified_candidates` por dimensión y evalúa `_counts_for_readiness` 2× por item. Particionar en una pasada. *(Impacto real depende del tamaño de las colecciones — medir antes.)*

## Refactors que NO recomiendo ahora

- **Compartir una conexión SQLite global / pool de conexiones.** `check_same_thread=True` lo prohíbe entre los hilos de workers; un pool no aporta a SQLite. El fix correcto es H1+H2 (no abrir stores de más, sacarlos del loop), no centralizar la conexión.
- **Paralelizar el feature pipeline (H4) sin resolver antes la fork-safety de macOS.** `narrative.py:187-195` documenta un crash Objective-C al paralelizar llamadas LLM en macOS; SV9 paraleliza sin mitigación visible. Hasta reconciliar esto (gate por env-var + validación en Linux), paralelizar a ciegas arriesga crashes en dev.
- **Reescribir `brand_service.run()` (401 líneas) entero.** Es el orquestador monolítico más grande del repo, pero su tamaño es deuda de *mantenibilidad*, no un cuello de rendimiento medido. Extraer fases es deseable pero es un refactor estructural de alto riesgo que no debe colarse en un pase de performance.
- **Memoización masiva (`@lru_cache`).** Solo hay 1 en 73k LOC, pero no localicé un call-site puro+caro+repetido-con-mismos-args que lo justifique. Sin evidencia de repetición (Fase 1), añadir caché es complejidad especulativa.
- **Tocar la familia `state_first`/`narrative_harness`.** Ya eliminada en este branch (`efad33f`). No aplica.
- **Reusar un único browser Playwright global.** El fallback de browser (`web_collector.py:257-322`) lanza Chromium por llamada, pero **solo se activa cuando Firecrawl Y el fetch estático fallan** — no es el path normal. Optimizarlo sin datos de frecuencia de fallback es prematuro.

---

## Plan de implementación por fases

**Fase 1 — Observabilidad / medición (prerrequisito, sin esto lo demás es a ciegas)**
- Instrumentar tiempo por fase del run: collect / features / score / persist / render.
- Contar por run: nº llamadas LLM, tokens input/output, nº queries SQL, nº scrapes Firecrawl/Exa.
- Loggear cache hit-rate (ya existen `cache_hits`/`cache_writes` en `LLMAnalyzer`).
- Cronometrar `executescript` en `SQLiteStore.__init__` (valida H1).
- `EXPLAIN QUERY PLAN` de `get_run_snapshot`/`list_brands` (valida H5).
- Medir tamaño real de prompts por dimensión (obs. 5424 ya vio uno de 47k chars).

**Fase 2 — Quick wins** (los 6 de arriba: H7, import lazy, busy_timeout, hit_count, dimension_labels, crawl_subpages). Bajo riesgo, no requieren datos de Fase 1 para ser seguros.

**Fase 3 — Refactors estructurales** (guiados por los números de Fase 1, en orden de ratio):
1. H1 (guard schema + reuso store) — probablemente el mayor ahorro por su multiplicador ×N.
2. H2 (SQLite fuera del event loop) — habilita concurrencia real bajo carga.
3. H5 (índices FK).
4. H6 (paralelizar colectores) y H8 (fusionar llamadas LLM).
5. H4 (paralelizar features) — **solo tras** resolver fork-safety.

**Fase 4 — Validación y pruebas**
- Suite completa `pytest` (baseline actual conocido: ~1587 passed, 4 fallos pre-existentes ajenos a esto — confirmar que no aumentan).
- Golden tests: comparar reportes/snapshots/scores antes y después byte-a-byte (comportamiento observable invariante).
- Re-medir las métricas de Fase 1 y comparar contra baseline.
- A/B de calidad LLM para H8 (cambio de forma de prompt).

---

## Métricas sugeridas (antes / después)

| Métrica | Cómo medir | Hallazgo que valida |
|---|---|---|
| Wall-clock total por run + desglose por fase | instrumentación Fase 1 | global |
| Nº instanciaciones `SQLiteStore` + tiempo en `executescript` por run | contador + timer | H1 |
| Latencia p95 de `/r/{token}/status` con K clientes concurrentes | test de carga local | H2 |
| `database is locked` / `SQLITE_BUSY` por run bajo carga | logs | H2, H3 |
| Nº llamadas LLM por run + tokens input/output + coste | instrumentación | H4, H8 |
| Cache hit-rate LLM | `cache_hits/(hits+writes)` | H1, H4 |
| Plan de query (`SCAN` vs `SEARCH USING INDEX`) | `EXPLAIN QUERY PLAN` | H5 |
| Nº scrapes Firecrawl/Exa + coste API por run | contador en colectores | H6 |
| Tiempo de arranque CLI / import de `brand_service` | `python -X importtime` | quick win #2 |
| Memoria pico por run | `tracemalloc` / RSS | riesgo: payloads grandes |

---

### Apéndice — Riesgos abiertos a investigar (no son hallazgos cerrados)
- **Contradicción fork-safety macOS vs SV9:** `narrative.py` evita paralelizar LLM por crash en macOS, pero `sv9/{editorial,evaluator}.py` ya lo hacen sin mitigación. Resolver antes de H4.
- **`synchronous` PRAGMA no fijado explícitamente:** confirmar valor efectivo en producción.
- **Fallback `json_schema`→`json_object`** (`llm_analyzer.py:537-548`): duplica la llamada completa si el provider no soporta schema mode. Depende del provider configurado (memoria 5424: gemini-3.1-flash-lite). Medir tasa de fallback.
- **`brand_service.py:901,916`** invocan `SocialCollector().collect` fuera del wrapper de caché del pipeline canónico — confirmar si es ruta viva (re-scraping social sin caché).
- **Caché LLM sin TTL ni invalidación por versión de contenido:** correctness, no perf, pero relevante si el contenido de marca cambia entre runs.

---

## Reconciliación con segunda auditoría independiente

Una segunda auditoría (modelo independiente) revisó el mismo proyecto. He cruzado ambos informes y **verificado de primera mano cada punto divergente o nuevo**. Resultado: las dos auditorías son fuertemente consistentes, sin contradicciones de fondo. Notación: `Hn` = este informe, `Bn` = segunda auditoría.

### Convergencia (ambas auditorías de forma independiente → máxima confianza)

| Patrón | Este informe | 2ª auditoría | Líneas verificadas |
|---|---|---|---|
| Init SQLite repetida (DDL + migraciones por instancia) | H1 | B1 | `sqlite_store.py:140-163` |
| `get_llm_cache` hace `UPDATE`+`commit` en cada hit | H3 | B8 | `sqlite_store.py:796-805` |
| Snapshot/provenance/replay recargados en la misma petición | H7 | B3 | `provenance.py:20` + `replay.py:231` |
| `list_brands` subqueries correlacionadas + `list_experiments` N+1 | medio | B5 | `sqlite_store.py:~1688,~1954` |
| Llamadas externas independientes en serie | H6 | B7 | `exa_collector.py:446`, `competitor_collector.py:283` |

### Aportes de la 2ª auditoría — verificados, a incorporar

- **B1 (amplía H1):** el patrón de store efímero no está solo en el caché LLM — hay **~46 instanciaciones de `SQLiteStore(BRAND3_DB_PATH)` solo en `brand_service.py`** (líneas 2441, 2727, 2737…3148, +16 más), muchas en callbacks de progreso/cancelación dentro de jobs largos. Cada una re-ejecuta el DDL/migraciones (H1). **Sube la prioridad de H1**: el ahorro es mayor de lo estimado.
- **B2 (NUEVO, Alta) — snapshots completos donde basta metadata:** rutas que cargan `get_run_snapshot()` íntegro (run+scores+features+annotations+raw_inputs+evidence, con JSON decode completo) cuando solo necesitan existencia/brand/url. Verificado: `web/routes/magnetism_scanner.py:619,1079,1169` y `web/routes/scanner_api.py:147,256,314`. **No estaba en mi informe.** Refactor: método proyectado `get_run_summary(run_id)` / `get_run_metadata(run_id)`.
- **B4 (NUEVO, Media) — listados decodifican `raw_payload` grande:** `_normalize_magnetism_listing_row` hace `json.loads(raw_payload)` por cada fila del índice, aunque la lista solo muestra un resumen. Verificado: `web/storage.py:132-138`. Refactor: columnas normalizadas para listado, `raw_payload` solo en detalle.
- **B6 (eleva un riesgo a hallazgo, Media) — `feature.raw_value` como string:** se persiste con `str(feature.raw_value)` (verificado `sqlite_store.py:867`) y se re-parsea con `ast.literal_eval`/json en varias funciones de `derivation.py`. Yo lo tenía como "riesgo a investigar"; la 2ª auditoría acierta al señalar el **origen en la escritura**. Refactor con compatibilidad legacy.

### Aportes de este informe que la 2ª auditoría omitió — mantener

- **H2 (Alta) — SQLite síncrono sobre el event loop de FastAPI:** la 2ª auditoría **no menciona el event loop**. Es un problema distinto al coste por query: en `async def` middleware/handlers (`rate_limit.py:61`, handlers de lectura en `web/`), `sqlite3` bloqueante **congela toda la app bajo concurrencia**, no solo ralentiza una petición. Es mi hallazgo de mayor impacto bajo carga. **Se mantiene.**
- **Fork-safety en macOS antes de paralelizar (F4):** la 2ª auditoría recomienda concurrencia acotada (B7) pero no advierte del crash Objective-C documentado en `narrative.py:187-195`. Paralelizar el pipeline (H4) o los colectores (H6/B7) **exige resolver esto primero** y validar en Linux. Requisito previo, no opcional.

### Veredicto del cruce

Convergencia alta y complementariedad limpia. La lista prioritaria fusionada queda:
1. **H1+B1** — dejar de re-inicializar el esquema por instancia (impacto ×46 en `brand_service`, no ×16).
2. **H2** — SQLite fuera del event loop (concurrencia bajo carga).
3. **H3/B8** — `hit_count` best-effort + `busy_timeout`.
4. **H7/B3 + B2** — no recargar snapshot; proyecciones `get_run_summary` para rutas que solo leen metadata.
5. **H5** — índices FK.
6. **H6/B7** — paralelizar colectores con límite (tras resolver fork-safety).
7. **B4, B6, H8** — payloads de listado y normalización de `raw_value`/llamadas LLM duplicadas.
