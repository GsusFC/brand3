# Handoff

Fecha: 2026-04-13

## Estado actual

- Repo publicado en GitHub: `GsusFC/brand3-scoring`
- Rama principal: `main`
- El proyecto local ya es el repo real y trackea `origin/main`
- InsForge ya está enlazado al proyecto `Brnd3`
- El esquema v1 de InsForge ya está aplicado
- Los buckets de storage ya están creados
- Existe un workspace inicial `Brand3` con el usuario actual como `owner`

## InsForge

- Proyecto: `Brnd3`
- Project ID: `e5fd5be4-5b9f-4f6e-b6b1-8103621988ae`
- App key / region: `k5u5kgr3.eu-central`
- Dashboard: `https://insforge.dev/dashboard/project/e5fd5be4-5b9f-4f6e-b6b1-8103621988ae`

## Archivos clave

- Plan de arquitectura: [`docs/insforge_v1.md`](/Users/gsus/brand3-scoring/docs/insforge_v1.md)
- Esquema SQL: [`db/insforge_v1.sql`](/Users/gsus/brand3-scoring/db/insforge_v1.sql)
- Política de benchmark: [`docs/benchmark_policy.md`](/Users/gsus/brand3-scoring/docs/benchmark_policy.md)
- Benchmark exploratorio: [`examples/startup_benchmark.json`](/Users/gsus/brand3-scoring/examples/startup_benchmark.json)

## Esquema ya creado en InsForge

Tablas principales:

- `workspaces`
- `workspace_members`
- `brands`
- `brand_domains`
- `analysis_jobs`
- `analysis_job_events`
- `analysis_runs`
- `dimension_scores`
- `feature_values`
- `run_audits`
- `raw_artifacts`
- `startup_candidates`
- `startup_candidate_sources`
- `benchmark_sets`
- `benchmark_set_items`
- `benchmark_reviews`

Buckets:

- `run-results`
- `screenshots`
- `raw-artifacts`
- `benchmark-assets`

## Decisiones tomadas

- El motor Python actual se mantiene como worker externo
- InsForge será la capa de producto: auth, DB, storage, realtime
- No se pierde la calibración actual: `base` sigue existiendo
- Los perfiles de scoring se simplificaron a `base`, `frontier_ai`, `enterprise_ai` y `physical_ai`
- El benchmark actual es exploratorio, no canónico

## Pendientes prioritarios

1. Webapp v1
- frontend accesible para terceros
- auth + workspace + brands + jobs

2. Integración backend con InsForge
- escribir `analysis_jobs`, `analysis_runs`, `dimension_scores`, `run_audits`
- dejar de depender de SQLite local para la capa app

3. Worker Python
- leer jobs pendientes
- ejecutar análisis
- publicar progreso y resultados en InsForge

4. Curación de benchmark serio
- discovery con Exa
- guardar candidatas en DB
- definir benchmark canónico después de revisión manual

## Notas operativas

- `.insforge/` está ignorado y no debe subirse
- También se ignoran artefactos locales de agent skills para no ensuciar el repo
- Si se retoma desde otro ordenador, lo primero es clonar el repo, enlazar el proyecto de InsForge y revisar este documento

## Siguiente paso recomendado

Empezar la webapp sobre InsForge con este alcance mínimo:

- login
- brands
- jobs
- run detail
- report por marca
