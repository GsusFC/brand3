# Brand3 — Plan de checks de refactor (23/06/2026)

## Check 1 — Regresión funcional de corte activo

- **Objetivo:** Validar que los módulos tocados no regresan contratos de reportes, evidencia, scanner y visual signature.
- **Comandos ejecutados:**
  - `PYTHONPATH=. ./.venv/bin/pytest tests/test_brand_audit_analyst.py tests/test_brand_context_brief.py tests/test_brand_research_pack.py tests/test_reports_renderer.py tests/test_reports_dossier.py tests/test_reports_snapshot.py tests/test_evidence_packet.py tests/test_strategic_evidence_packet.py tests/test_tldr_brand3_research_pack_evaluation.py -q`
  - `PYTHONPATH=. ./.venv/bin/pytest tests/test_web_visual_signature_data.py tests/test_web_visual_signature_routes.py tests/test_web_app.py tests/test_magnetism_scanner.py tests/test_research_evidence_graph.py tests/test_evidence_vnext.py tests/test_research_pack_quality.py tests/test_quality_trust.py tests/test_feature_extractors.py tests/test_evidence_source_backfill.py tests/test_research_pack_quality_batch.py -q`
- **Resultado:** `143 passed, 1 skipped` y `360 passed, 5 subtests passed`.
- **Estado:** ✅ Aprobado.

## Check 2 — Integridad de imports tras split de módulos

- **Objetivo:** Detectar ciclos de imports entre módulos refactorizados (`*_impl`, `*_support`, fachadas).
- **Herramienta:** script AST sobre `src/**/*.py` (imports de primer nivel).
- **Resultado inicial:** 11 ciclos detectados, concentrados en `brand_intelligence` y `evidence_vnext`, además de uno puntual `services/sv9`.
- **Intervención aplicada:** removimos el ciclo fuerte en `src/research/brand_intelligence*` evitando el import recíproco entre facade/core.
- **Resultado final:** `0` ciclos de import en el chequeo de nivel módulo (primer nivel).
- **Estado:** ✅ Aprobado con mejora aplicada.

## Check 3 — Estado de partición por patrón de contrato

- **Objetivo:** Verificar que no queden regresiones en los bloques ya partidos y medir concentraciones.
- **Evidencia automática:** conteo de módulos grandes en `src` (`>=1000` líneas).
- **Resultado:** `1177 src/visual_signature/platform/platform_builder_impl.py` (1 bloque grande restante fuera de las áreas objetivo).
- **Estado:** ✅ Aprobado para scope actual (objetivo de brand_intelligence + adquisición).

## Decisión de siguiente paso

- Mantener este bloque cerrado y pasar al siguiente chequeo de arquitectura con foco en `src/visual_signature/platform/platform_builder_impl.py` solo cuando no colisione con el flujo de Visual Signature en otro worktree.
