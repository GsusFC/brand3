# Scoring Review

Fecha: 2026-04-13

## Objetivo

Dejar una revisión útil del motor de scoring actual:

- qué está bien
- qué está débil
- qué es un bug real
- qué es una decisión de modelo
- qué conviene priorizar

Este documento no intenta rediseñar todo el sistema. Intenta ordenar el trabajo.

## Lo que está bien

### 1. Arquitectura

La separación entre:

- collectors
- extractores
- scoring engine
- learning/calibration
- storage

es clara y razonable para un prototipo avanzado.

### 2. Filosofía del engine

El principio de:

- reglas que pueden capear
- pero no inflar artificialmente

es correcto para evitar scores fantasiosos.

Referencia:

- [engine.py](/Users/gsus/brand3-scoring/src/scoring/engine.py)

### 3. Perfiles de calibración

El sistema de perfiles permite no evaluar todas las marcas con el mismo criterio.

Esto es especialmente importante si Brand3 se va a usar por nichos o tipos de startup.

### 4. LLM como capa encima del heurístico

La dirección base es buena:

- heurístico como fallback
- LLM como override de algunas señales

El problema no es el enfoque. El problema es que hoy está parcial.

### 5. Sistema de calibración

El flujo:

- candidates
- review
- experiments
- gates
- rollback

ya tiene bastante madurez operativa.

## Hallazgos principales

## 1. `sentiment_trend` no mide tiempo real

Problema:

El extractor divide resultados por posición y asume que eso equivale a viejo/nuevo.

Pero el propio código reconoce que Exa devuelve por relevancia, no por fecha.

Referencias:

- [percepcion.py](/Users/gsus/brand3-scoring/src/features/percepcion.py#L112)
- [percepcion.py](/Users/gsus/brand3-scoring/src/features/percepcion.py#L117)

Impacto:

- feature con mucho ruido
- puede sugerir una mejora o empeoramiento inexistente

Decisión:

- bug de señal, no solo mejora opcional

Recomendación:

- ordenar por `published_date` cuando exista
- si faltan fechas suficientes, devolver score neutral con confianza baja

Prioridad:

- alta

## 2. `generic_language_score` no normaliza por longitud

Problema:

Hoy el score depende de hits absolutos y umbrales discretos.

Una web larga con algunas frases genéricas puede recibir el mismo castigo que una corta saturada de ellas.

Referencia:

- [diferenciacion.py](/Users/gsus/brand3-scoring/src/features/diferenciacion.py#L126)

Impacto:

- falsos positivos
- castigo desproporcionado en webs largas

Decisión:

- bug de modelado importante

Recomendación:

- medir ratio sobre oraciones o palabras
- mantener un pequeño castigo absoluto para casos extremos

Prioridad:

- alta

## 3. `confidence` existe pero no afecta al score

Problema:

Los `FeatureValue` llevan `confidence`, pero el engine la ignora al agregar.

Referencia:

- [engine.py](/Users/gsus/brand3-scoring/src/scoring/engine.py#L148)

Impacto:

- señales dudosas pesan igual que señales fuertes
- el sistema no distingue calidad de dato

Decisión:

- mejora estructural importante, no parche pequeño

Recomendación:

- introducir ponderación por `confidence`
- recalibrar después weights y defaults

Nota:

No conviene meter este cambio sin benchmark y recalibración, porque moverá muchos scores.

Prioridad:

- alta

## 4. Sentiment heurístico por keywords es frágil

Problema:

El sistema cuenta palabras positivas/negativas por substring.

Eso genera falsos positivos y falsos negativos contextuales.

Referencia:

- [percepcion.py](/Users/gsus/brand3-scoring/src/features/percepcion.py#L17)
- [percepcion.py](/Users/gsus/brand3-scoring/src/features/percepcion.py#L56)

Impacto:

- baja precisión en percepción

Decisión:

- debilidad real del modelo actual

Recomendación:

- mantener heurístico como fallback
- mejorar percepción LLM antes de plantearla como default

Matiz:

Hoy el extractor LLM de percepción no sustituye toda la dimensión; solo sobrescribe partes.

Referencia:

- [percepcion_llm.py](/Users/gsus/brand3-scoring/src/features/percepcion_llm.py#L22)

Prioridad:

- media-alta

## 5. `tech_modernity` mide copy, no stack real

Problema:

Busca señales como `react`, `next.js`, `tailwind` dentro del markdown visible.

Eso detecta más fácilmente marcas que hablan de tecnología que marcas que la usan.

Referencia:

- [vitalidad.py](/Users/gsus/brand3-scoring/src/features/vitalidad.py#L150)

Impacto:

- señal ruidosa
- sesgo hacia devtools o marcas técnicas

Decisión:

- feature débil

Recomendación:

- sustituir por inspección del HTML/source si se quiere conservar
- o eliminarla si no demuestra valor

Prioridad:

- media

## 6. Regla documentada de coherencia no implementada

Problema:

En dimensiones se documenta:

- `si solo tiene 1 canal activo -> cap a 50`

pero el engine no construye esa regla.

Referencias:

- [dimensions.py](/Users/gsus/brand3-scoring/src/dimensions.py#L37)
- [engine.py](/Users/gsus/brand3-scoring/src/scoring/engine.py#L55)

Impacto:

- inconsistencia entre documentación y comportamiento real

Decisión:

- bug de consistencia

Recomendación:

- implementar la regla
- o quitarla de la documentación

Prioridad:

- media

## 7. `ai_visibility` es demasiado simple

Problema:

La métrica actual hace:

- `score = min(num_results * 25, 100)`

sin peso por relevancia o calidad de la mención.

Referencia:

- [presencia.py](/Users/gsus/brand3-scoring/src/features/presencia.py#L276)

Impacto:

- inflación fácil
- señal poco robusta

Decisión:

- mejora clara necesaria

Recomendación:

- ponderar por relevancia del resultado
- distinguir mención central de mención tangencial

Prioridad:

- media

## 8. `web_presence` arranca alto por existencia mínima

Problema:

Si el markdown supera 100 chars, la web ya suma 40 puntos.

Referencia:

- [presencia.py](/Users/gsus/brand3-scoring/src/features/presencia.py#L47)

Matiz importante:

Esto no es necesariamente un error bruto.

El extractor intenta evitar penalizar webs mínimas pero legítimas.

La intención es buena.

Problema real:

- el floor puede ser alto en algunos casos
- pero la solución no debe volver a castigar minimalismo válido

Recomendación:

- reforzar detección de placeholder y señales estructurales
- revisar el floor con benchmark real antes de bajarlo agresivamente

Prioridad:

- media-baja

## 9. Composite lineal no penaliza desequilibrios

Problema:

El composite es media ponderada lineal.

Una dimensión muy baja puede quedar absorbida por otras altas.

Referencia:

- [engine.py](/Users/gsus/brand3-scoring/src/scoring/engine.py#L203)

Impacto:

- algunas marcas pueden parecer demasiado sanas pese a tener una debilidad crítica

Decisión:

- cuestión de modelo, no bug puro

Recomendación:

- no saltar directamente a media geométrica
- probar primero caps o reglas por dimensiones críticas

Especialmente relevante:

- cuidado con penalizar demasiado a startups pequeñas en `presencia` o `percepcion`

Prioridad:

- media

## 10. Duplicidad de `GENERIC_PHRASES`

Problema:

Hay listas muy parecidas en dos módulos distintos.

Referencias:

- [coherencia.py](/Users/gsus/brand3-scoring/src/features/coherencia.py#L18)
- [diferenciacion.py](/Users/gsus/brand3-scoring/src/features/diferenciacion.py#L19)

Impacto:

- deriva futura
- mantenimiento peor

Decisión:

- deuda de código, no urgencia de producto

Recomendación:

- extraer a un módulo común tipo `lexicons.py`

Prioridad:

- baja

## 11. Cliente LLM demasiado básico para producción

Problema:

`LLMAnalyzer` usa `urllib` crudo, sin retry ni backoff.

Referencia:

- [llm_analyzer.py](/Users/gsus/brand3-scoring/src/features/llm_analyzer.py#L49)

Impacto:

- fragilidad operacional

Decisión:

- importante para endurecer producción
- no bloquea validación inicial del producto

Recomendación:

- pasar a `httpx`
- añadir retry/backoff
- separar timeouts por tipo de llamada

Prioridad:

- baja-media

## Lo que no pondría tan arriba

## LLM como default en percepción

Dirección:

- sí, probablemente a medio plazo

Pero no hoy por tres razones:

1. depende de disponibilidad real del LLM
2. el extractor LLM actual no cubre toda la dimensión
3. primero conviene arreglar señales claramente rotas

## Validación con fuentes externas tipo SimilarWeb

Tiene sentido después.

Pero antes hay trabajo interno de mayor ROI:

- trend temporal
- generic language
- confidence
- ai visibility

## Prioridad recomendada

## Sprint A

1. arreglar `sentiment_trend`
2. normalizar `generic_language_score`
3. resolver inconsistencia docs/rule de coherencia
4. revisar `ai_visibility`

## Sprint B

1. definir diseño de `confidence-weighted scoring`
2. benchmark de impacto sobre scores existentes
3. decidir si `tech_modernity` se reemplaza o se elimina

## Sprint C

1. unificar lexicons
2. endurecer cliente LLM
3. revisar si percepción LLM puede pasar a ser ruta principal

## Conclusión

El motor actual tiene una base buena y una arquitectura defendible.

Los problemas más serios no están en la estructura del proyecto. Están en algunas señales heurísticas que hoy introducen demasiado ruido o están midiendo una cosa distinta de la que dicen medir.

La prioridad correcta no es rehacer todo el scoring. Es arreglar primero:

- features temporalmente incorrectas
- features no normalizadas
- diferencias entre documentación y comportamiento real

Después de eso ya tiene sentido replantear:

- uso de `confidence`
- composición del composite
- percepción LLM como camino principal
