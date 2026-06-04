# Brand3 Local vs Deploy Regression Harness

## Veredicto

Sí necesitamos una prueba local contra deploy para saber si un cambio degrada el resultado real. Los tests unitarios protegen contratos, pero no comparan el comportamiento completo de Brand Audit + Magnetism Scanner frente a producción.

El harness vive fuera del pipeline productivo:

```text
scripts/compare_local_deploy_pipeline.py
```

## Qué compara

El script puede trabajar en dos modos:

- `--mode api`: usa la API autenticada del Scanner. Es el modo más fuerte porque devuelve JSON de Scanner, Evidence, Methodology y Audit.
- `--mode web`: usa el formulario público y compara páginas visibles. No necesita token y sirve para detectar fallos operativos en deploy.
- `--mode auto`: usa API si encuentra `BRAND3_SCANNER_API_TOKEN`; si no, cae a modo web.

En modo API, el script usa la API del Scanner como entrada común:

1. `POST /api/v1/scanner` con la misma URL en local y deploy.
2. Espera a que ambos scans estén `ready` o `failed`.
3. Lee:
   - `/api/v1/scanner/{id}`
   - `/api/v1/scanner/{id}/result`
   - `/api/v1/scanner/{id}/evidence`
   - `/api/v1/scanner/{id}/methodology`
   - `/api/v1/scanner/{id}/audit`
4. Normaliza señales comparables de Scanner y Brand Audit.
5. Escribe JSON y Markdown con diferencias.

Esto cubre Brand Audit porque un scan por URL crea o adjunta un `source_run_id`, y el endpoint `/audit` devuelve el snapshot del audit asociado.

## Señales que vigila

- `scanner_readiness.status`
- `publication_decision.status`
- `publication_decision.publishable`
- `report_readiness.report_mode`
- `magnetism_score`
- `coherence_score`
- `composite_score`
- cuadrante
- versión de pipeline
- número de fuentes/evidencias normalizadas
- bloques TLDR detectados
- cambios de detección por bloque TLDR

## Cómo ejecutarlo

Arranca local:

```bash
scripts/run_web_dev_macos.sh
```

En otra terminal, sin token:

```bash
./.venv/bin/python scripts/compare_local_deploy_pipeline.py \
  --mode web \
  --url https://www.sklum.com \
  --local-base http://127.0.0.1:8000 \
  --deploy-base https://brand3.fly.dev
```

Con token de Scanner API:

```bash
./.venv/bin/python scripts/compare_local_deploy_pipeline.py \
  --mode api \
  --url https://www.sklum.com \
  --local-base http://127.0.0.1:8000 \
  --deploy-base https://brand3.fly.dev
```

Salida:

```text
scratch/local_vs_deploy_pipeline_compare/latest.md
scratch/local_vs_deploy_pipeline_compare/latest.json
```

## Interpretación

Un resultado sin diferencias materiales no demuestra que la lectura sea buena; demuestra que local no se ha desviado de deploy según los umbrales actuales.

Un `critical` significa que no deberíamos publicar o desplegar sin revisar:

- local/deploy falla;
- deploy falla aunque local complete;
- cambia readiness;
- cambia publicación;
- Audit deja de ser publicable;
- Scanner deja de ser publicable.

Un `warning` exige revisión humana, no bloqueo automático:

- delta de score mayor de 5 puntos;
- cambio de cuadrante;
- cambio de versión de pipeline;
- caída relevante en fuentes/evidencias;
- cambio de detección TLDR.

## Uso recomendado

Antes de desplegar cambios en adquisición, readiness, Research Pack, Analyst Pass o Scanner:

```bash
./.venv/bin/python scripts/compare_local_deploy_pipeline.py \
  --url https://www.sklum.com \
  --url https://www.langchain.com \
  --url https://www.netlify.com
```

Mantener un set pequeño:

- una marca conocida con buena evidencia;
- una marca con datos pobres o caso problemático, como SKLUM;
- una marca SaaS/tech usada como fixture mental;
- una marca con riesgo de colisión de entidad.

## Limitaciones

- Consume ejecución real de proveedores y LLM en local y deploy.
- Si deploy ya incluye el mismo commit, la comparación mide entorno/datos/proveedores, no diferencia de código.
- Si hay variabilidad LLM, conviene comparar dos ejecuciones deploy-deploy para establecer ruido base.
- No sustituye fixtures ni tests unitarios; es una prueba de regresión operativa.
