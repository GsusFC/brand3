# Brand3 — Mapa de Prompts por Prisma (en español)

Este documento resume **qué prompts se usan hoy** para cada dimensión del prisma Brand3:

- Coherencia
- Presencia
- Percepción
- Diferenciación
- Vitalidad

También separa dos capas distintas del sistema:

1. **Extracción/medición** (features, scoring input)  
2. **Narrativa** (texto final del reporte)

---

## 1) Capa de extracción (features)

Archivo principal: `src/features/llm_analyzer.py`

### Coherencia

- `analyze_messaging_consistency(web_content, third_party_mentions, brand_name)`
  - Prompt system: *brand coherence analyst*.
  - Objetivo: comparar auto-descripción vs terceros.
  - Salida esperada: `consistency_score`, `verdict`, `self_category`, `third_party_category`, `gaps`, `reasoning`.

- `analyze_tone_consistency(web_content, third_party_snippets, brand_name)`
  - Prompt system: *brand tone analyst*.
  - Objetivo: consistencia de tono entre owned y terceros.
  - Salida esperada: `tone_consistency_score`, `self_tone`, `third_party_tone`, `gap_signal`, `examples`, `reasoning`.

---

### Presencia

- **No tiene prompt LLM principal dedicado** para el cálculo base de presencia.
- Se construye mayoritariamente con señales heurísticas/estructuradas en `src/features/presencia.py` (web/exa/social/context).

---

### Percepción

- `analyze_brand_sentiment(mentions, brand_name)`
  - Prompt system: *brand perception analyst*.
  - Objetivo: sentimiento y controversia con evidencia literal.
  - Salida esperada: `sentiment_score`, `verdict`, `overall_tone`, `positive_themes`, `negative_themes`, `evidence`, `controversy_detected`, `controversy_details`, `reasoning`.

- (Legacy disponible) `analyze_sentiment(mentions, brand_name)`
  - Menos estricto que `analyze_brand_sentiment`.

---

### Diferenciación

- `analyze_positioning_clarity(web_content, brand_name, competitor_snippets)`
  - Prompt system: *brand positioning analyst*.
  - Objetivo: claridad de posicionamiento.
  - Salida esperada: `clarity_score`, `verdict`, `stated_position`, `target_audience`, `differentiator_claimed`, `evidence`, `reasoning`.

- `analyze_uniqueness(web_content, brand_name, competitor_snippets)`
  - Prompt system: *brand differentiation analyst*.
  - Objetivo: lenguaje único vs genérico.
  - Salida esperada: `uniqueness_score`, `verdict`, `unique_phrases`, `generic_phrases`, `brand_vocabulary`, `competitor_overlap_signals`, `reasoning`.

- (Legacy disponible) `analyze_differentiation(...)` y `analyze_positioning(...)`.

---

### Vitalidad

- `analyze_momentum(mentions, brand_name)`
  - Prompt system: *brand momentum analyst*.
  - Objetivo: detectar `building | maintaining | declining | unclear`.
  - Salida esperada: `momentum_score`, `verdict`, `evidence`, `reasoning`.

---

## 2) Capa narrativa (texto final del reporte)

Archivo principal: `src/reports/narrative.py`

### Prompt de hallazgos por dimensión (aplica a las 5 dimensiones)

- System prompt: `_FINDINGS_SYSTEM`
- User prompt builder: `_build_findings_user_prompt(dim, brand, analysis_date, perceptual_hints)`
- Ejecución: `generate_dimension_findings(...)` → `_try_findings(...)`

Este prompt genera los hallazgos de cada dimensión con la estructura:

- `title`
- `observation`
- `implication`
- `typical_decision`
- `evidence_urls`

Reglas editoriales fuertes incluidas en el prompt:

- no echo-chamber de claims propios,
- separación observación vs implicación,
- prohibición de adjetivos cerrados,
- evidencias con ancla explícita.

---

### Prompt de síntesis global (no es “lado” del prisma)

- System prompt: `_SYNTHESIS_SYSTEM`
- User prompt builder: `_build_synthesis_user_prompt(ctx)`
- Función: `generate_synthesis(...)`

---

### Prompt de tensiones cruzadas (no es “lado” del prisma)

- System prompt: `_TENSIONS_SYSTEM`
- User prompt builder: `_build_tensions_user_prompt(dimensions, brand, analysis_date)`
- Función: `generate_tensions(...)`

---

## 3) Resumen rápido por dimensión

- **Coherencia**: `analyze_messaging_consistency`, `analyze_tone_consistency` + prompt narrativo de findings.
- **Presencia**: heurístico/estructurado (sin prompt LLM principal dedicado) + prompt narrativo de findings.
- **Percepción**: `analyze_brand_sentiment` + prompt narrativo de findings.
- **Diferenciación**: `analyze_positioning_clarity`, `analyze_uniqueness` + prompt narrativo de findings.
- **Vitalidad**: `analyze_momentum` + prompt narrativo de findings.

---

## 4) Nota práctica

Si quieres, el siguiente paso es generar una versión **“prompt inventory”** con:

- el texto literal completo de cada system/user prompt,
- versión,
- campos JSON esperados,
- y dónde se usa en runtime (call stack).

