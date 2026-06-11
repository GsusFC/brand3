# SV9 — Documento técnico de diseño v1

Para: Jesús, Javi
De: Sergio
Fecha: 2026-06-10

Este documento es la fuente de verdad del nuevo motor de scoring del Brand3 Scanner. Consolida el briefing v2.1 con las decisiones de diseño cerradas después de auditar el codebase y los scans en producción. Donde contradice al briefing v2.1, manda este documento.

Estado de cada sección: **[cerrado]** se construye tal cual · **[abierto]** falta decisión o redacción.

---

## 1. Qué es SV9

SV9 es el motor de scoring que sustituye al motor de 5 dimensiones (V5: coherencia, presencia, percepcion, diferenciacion, vitalidad). Puntúa una marca contra el framework Brand3: **9 componentes + Coherencia**, sobre 100.

Los 9 componentes son los que ya extrae la capa TLDR en producción (`TLDR_KEYS`):

```
core_purpose, magnetism, value_proposition, personality,
brand_idea, attributes, values, mission, vision
```

Coherencia es el décimo elemento: no tiene detección propia, lee el conjunto.

Principio rector heredado del codebase y que SV9 mantiene: **el LLM interpreta evidencia, el código calcula números.** Ningún score sale directamente de un modelo.

---

## 2. Naming [cerrado]

- Producto: **Brand3 Scanner** (B3S). "Magnetism Scanner" desaparece de rutas, títulos, copy y metadatos. Redirect 301 desde `/magnetism-scanner`.
- Nota global: **Brand3 Score** (0–100).
- Motor interno: **sv9**. Convenciones: módulo `src/sv9/`, tablas `sv9_*`, versión de rúbrica `sv9-rubric-vN`. En cualquier diff debe ser obvio qué es nuevo y qué es legado.
- Entregable posterior: **Brand System** (.md vivo).

---

## 3. Modelo de scoring [cerrado]

| Componente | Escala | Puntos sobre 100 |
|---|---|---|
| Misión | 0–5 | 5 |
| Visión | 0–5 | 5 |
| Valores | 0–5 | 5 |
| Atributos | 0–5 | 5 |
| Propuesta de valor | 0–10 | 10 |
| Personalidad / Arquetipo | 0–10 | 10 |
| Idea de marca | 0–10 | 10 |
| Propósito | 0–10 | 10 |
| Magnetism | 0–10, ×2 | 20 |
| Coherencia | 0–10, ×2 | 20 |
| **Brand3 Score** | | **100** |

Reglas:

- **Parejas.** Misión & Visión y Valores & Atributos se muestran como parejas (10 puntos cada pareja) pero se evalúan y puntúan por separado. Mitad no detectada = 0. No se promedia.
- **Tope de Magnetism.** Si la media normalizada de los 8 componentes base (los de escala 0–5 se normalizan ×2 a escala 0–10) es inferior a 4/10, Magnetism no puede superar 5/10 (10/20). Una frase brillante sobre una base rota es un eslogan, no magnetismo.
- **Estados y ceros.** Cada componente sale con uno de tres estados:
  - `detectado` → score por escalera.
  - `no_detectado` → score 0. Es diagnóstico, no error: el canvas con huecos es el producto.
  - `no_evaluado` → score 0. Es fallo técnico (LLM caído, timeout, evidencia corrupta).
  
  Públicamente ambos ceros se muestran igual: 0 en el componente, con su análisis visible. El score sigue siendo sobre 100 (el componente aporta 0; no se renormaliza el denominador). Internamente los estados se distinguen siempre: un `no_evaluado` es reintentable componente a componente desde el snapshot persistido, sin re-colectar nada.
- **Gate de identidad.** Si la confianza en la identidad de la entidad es baja (dominio ambiguo, marca homónima), el scan se detiene antes de evaluar y pide verificación manual. La maquinaria de entity discovery existente cubre esto.
- **Sin bandas.** Las bandas A/B/C/D/F del briefing v2.1 se eliminan. Las sustituyen las métricas de la sección 8.

---

## 4. Arquitectura del motor: cinco piezas [cerrado]

### 4.1 El rubric como datos, versionado

Un archivo declarativo (heredero de `dimensions.py`) con los 10 elementos: escalas, escaleras de peldaños (criterio observable + etiqueta interna por peldaño), parejas, multiplicadores ×2 y la regla del tope de Magnetism.

Lleva `rubric_version` explícito (`sv9-rubric-v1`, `v2`…). Todo score y todo registro de calibración queda trazado contra la versión que lo produjo. Cualquier retoque de redacción de peldaños incrementa la versión; sin esto el dataset de calibración se corrompe en silencio.

### 4.2 El evaluador por componente

Input por componente, un paquete con:

- La detección del TLDR (texto, modo literal/inferido/performed/ausente, confianza, citas). El Pase 1 actual no se toca: funciona.
- Las señales auxiliares asignadas a ese componente desde la biblioteca de señales (sección 9).
- Contexto factual de otros componentes solo donde la escalera lo exige (p. ej. Visión peldaño "conecta con la misión" recibe el texto de la misión detectada).

Proceso: el LLM devuelve **un veredicto booleano por peldaño con cita de evidencia obligatoria**. Se evalúa **la escalera completa**, no se para en el primer fallo. Mismo coste (un prompt), tres beneficios: el mensaje de "qué falta para el siguiente peldaño" existe siempre; la calibración baja a nivel de peldaño; y los perfiles no monótonos (pasa el 7, falla el 4) delatan problemas de rúbrica o alucinación del evaluador.

El score lo calcula código: **peldaños consecutivos superados desde abajo**. El perfil completo de peldaños se persiste.

### 4.3 El agregador

Puro código, cero LLM, determinista y testeable sin mocks. Aplica: suma, parejas, ×2, estados a 0, tope de Magnetism, Brand3 Score, percentil de cohorte y margen inmediato.

### 4.4 Coherencia (ver sección 6)

Evaluador especial sin detección propia. Corre siempre, incluso con huecos.

### 4.5 La capa editorial

El generador del TLDRv2 actual gana un input (el veredicto de peldaños por componente) y pierde otro (el score del V5 que hoy alimenta la lectura ejecutiva). Ver sección 7.

---

## 5. Principios de evaluación [cerrado]

**Contexto encadenado, veredictos independientes.** El orden ascendente del briefing (Misión & Visión → … → Propósito → Magnetism → Coherencia) es narrativa de presentación, no de cálculo.

1. **Toda evaluación es total.** Cada componente siempre devuelve score + estado. Nada bloquea a nada: si un componente falla o no se detecta, los demás se evalúan igual.
2. **Las dependencias viven en los peldaños, nunca como precondición.** Si la misión no se detecta, Visión no se bloquea: su peldaño "conecta con la misión" simplemente falla y la escalera degrada sola. La degradación es semántica, no técnica.
3. **Hacia arriba se pasan evidencias, no juicios.** Propósito evalúa mejor sabiendo qué misión y qué propuesta de valor se detectaron (los textos), no qué nota sacaron. Pasar scores entre evaluadores propaga sesgo y ensucia la atribución de los deltas de calibración.
4. **Paralelismo.** 7 de los 9 componentes son evaluables en paralelo. Puntos de sincronización: Propósito (necesita contexto factual), el tope de Magnetism (necesita la base puntuada) y Coherencia (necesita todo).
5. **Los agregados exigen completitud interna.** Un scan con componentes `no_evaluado` puede mostrarse, pero no entra al ranking público hasta resolverse (reintento desde snapshot).

---

## 6. Coherencia: dos ejes y meta-evaluador [cerrado]

Coherencia evalúa la narrativa en su conjunto, con dos ejes que el evaluador recibe como paquetes de evidencia separados:

- **Sintonía interna.** ¿Los 9 componentes cuentan la misma historia? Input: los 9 veredictos con sus textos detectados. ¿La visión continúa la misión? ¿La personalidad encarna los valores? ¿El magnetismo nace de la propuesta o es un eslogan pegado?
- **Consistencia externa.** ¿Lo que dice la web coincide con lo que dice y lo que dicen de ella en el resto de espacios digitales? Input: las señales heredadas del desguace del V5 — `messaging_consistency` (cómo se describe vs. cómo la describen terceros), `tone_consistency`, `cross_channel_coherence`. Esta evidencia ya se colecta hoy; solo cambia de dueño.

La escalera de Coherencia debe repartir conscientemente ambos ejes entre sus peldaños (revisar en la sesión de redacción).

**Coherencia como termómetro del propio SV9.** Cuando Coherencia detecta discordancia entre los 9 veredictos hay dos explicaciones: la marca es incoherente, o el scan leyó mal. El desempate es el flag "evidencia errónea" de la calibración: si los scans con Coherencia baja acumulan flags, el problema es el motor. Regla operativa: **todo scan con Coherencia ≤ 3 entra en cola de revisión humana prioritaria.** Interno, no se renderiza.

---

## 7. Rúbricas y mensajes: el número primero, la prosa después [cerrado]

Las escaleras del briefing v2.1 §5 tienen doble función. Se separa:

- **Como instrumento de evaluación: irrenunciables e internas.** Son el checklist que recorre el evaluador (LLM o humano) y la rúbrica compartida sin la cual los deltas de calibración no significan nada.
- **Como copy público: se sustituyen.** Los mensajes de peldaño literales, iguales para todas las marcas, serían un paso atrás frente al TLDRv2 actual. El mensaje que ve el fundador es **prosa personalizada generada a partir del veredicto**: recibe como restricciones duras el peldaño alcanzado, el motivo del primer peldaño fallido y la evidencia de la marca. Cuenta con palabras propias de la marca por qué está donde está y qué le falta para el siguiente peldaño.

Orden inviolable: **primero el número, después la prosa.** La generación está condicionada por el veredicto; nunca corren en paralelo. Esto elimina el riesgo de que la prosa suene a 7 cuando el score dice 3.

Los mensajes de peldaño redactados no se tiran: son la rúbrica que ven los evaluadores humanos en el formulario de calibración, y se publican como metodología en Capa 3 (puntuar contra rúbrica publicada diferencia al scanner de cualquier caja negra).

**[abierto]** La redacción final de las escaleras: sesión conjunta pendiente (Sergio + Jesús). El formato (escaleras acumulativas, un criterio observable por peldaño) está cerrado; se ajusta redacción, no formato. Las escaleras del briefing v2.1 §5 son el borrador de partida.

TLDR (extracción) y TLDRv2 (interpretación) son complementarios y se mantienen. Lo que se inserta entre ambos es el motor de escaleras. El score global del V5 que hoy muestra el TLDRv2 se sustituye por los 9 scores + Coherencia + Brand3 Score, y la lectura ejecutiva pasa a hablar el idioma del modelo nuevo.

---

## 8. Métricas de presentación [cerrado]

Capa 1 muestra cuatro datos, cero decoración:

1. **Brand3 Score** (0–100).
2. **Percentil de cohorte**: posición dentro de su categoría primaria ("top 18% de las marcas SaaS escaneadas"). Solo se muestra cuando la cohorte tiene masa suficiente (≥20 scans); por debajo, se omite sin disculparse.
3. **Hueco más doloroso**: el componente con mayor distancia entre su peso y su score.
4. **Margen inmediato**: suma de puntos que la marca desbloquearía subiendo un solo peldaño en cada componente (en Magnetism y Coherencia un peldaño vale 2 puntos). Sale gratis del perfil completo de peldaños. Es a la vez diagnóstico honesto y el argumento comercial de FLOC* escrito por el motor.

---

## 9. Desguace del V5 [cerrado]

El V5 son dos cosas pegadas y se separan:

**Muere entero el rubric:** `src/dimensions.py`, `src/scoring/engine.py`, los perfiles de nicho (`src/niche/profiles.py` como pesos de scoring), las reglas de techo y el composite de 5 dimensiones.

**Sobreviven los extractores como biblioteca de señales**, reasignados a peldaños concretos:

| Señal del V5 | Destino en SV9 |
|---|---|
| Análisis visual + `visual_consistency` | Idea de marca (peldaños de sistema visual y consistencia) + puente al módulo visual manual |
| `brand_sentiment`, `mention_volume` (Exa) | Magnetism peldaños altos: "preferencia activa", "orgullo de pertenencia" son inobservables sin terceros |
| `tone_consistency`, `messaging_consistency` | Coherencia eje externo; Personalidad peldaños de consistencia |
| `cross_channel_coherence` | Coherencia eje externo ("todas las superficies") |
| Posicionamiento vs. competidores | Propuesta de valor peldaños de diferencial frente a alternativas |
| `content_recency`, `publication_cadence`, `momentum` | Evidencia de proof signals y de "decisiones de negocio públicas" en Propósito |

Los peldaños altos de casi todas las escaleras hablan de cosas que no están en la web de la marca (quién la imita, quién presume de usarla, consistencia entre superficies). Esa evidencia externa es exactamente lo que estos extractores ya saben traer.

### Retirada en tres movimientos

1. **Convivencia muda.** SV9 se construye al lado y corre en sombra sobre los snapshots históricos (replay desde `raw_inputs` persistidos, sin re-colectar). V5 sigue siendo lo público. De aquí sale la primera tabla comparativa V5-vs-SV9 sobre marcas reales; los casos de mayor divergencia son la primera tanda de calibración humana.
2. **El relevo.** SV9 sale a producto (pantalla nueva, canvas, export). V5 deja de renderizarse en cualquier superficie pública pero su cálculo sigue vivo internamente como red de seguridad.
3. **El desguace.** Se apaga el cálculo del composite V5, se retiran rubric/engine/perfiles, los extractores supervivientes se mudan oficialmente a la biblioteca de señales y se podan los tests que asumen 5 dimensiones (~33 archivos). La tabla `scores` histórica no se toca: archivo muerto pero legible.

### Puerta de calidad para el movimiento 3 [cerrado en estructura, números ajustables]

El V5 se apaga cuando se cumpla, contra la misma `rubric_version`:

- ≥ 50 scans calibrados por al menos 2 evaluadores.
- Delta humano-IA ≤ 1 punto en ≥ 80% de los componentes.
- Flags de "evidencia errónea" < 5%.

Los números se ajustan cuando existan los primeros deltas reales. Lo innegociable: la puerta se define antes de empezar a calibrar y no se mueve según convenga.

---

## 10. Persistencia [cerrado]

Todo aditivo. Nada del esquema V5 se migra ni se muta.

- **Resultado por componente** (no blob monolítico): `(scan_id, componente, score, escala, estado, perfil_peldaños JSON, evidencia, mensaje, rubric_version, fecha)`. Un registro por componente permite reintentar y re-evaluar componentes sueltos.
- **Scan**: agregados (Brand3 Score, percentil, margen inmediato, hueco), estado global, referencia al snapshot del audit.
- **Calibración**: `(scan_id, url, componente, score_ia, score_humano, delta, motivo, flag_evidencia, evaluador, fecha, rubric_version)` — el esquema del briefing §7 más `rubric_version`.
- Tablas `sv9_*` vía migración. `scores` y demás tablas V5 quedan intactas para los runs históricos.

---

## 11. Calibración humana [cerrado]

Como el briefing v2.1 §7, con dos adiciones:

- Todo registro lleva `rubric_version`.
- Como se persiste el perfil completo de peldaños, el desacuerdo se analiza a nivel de peldaño, no solo de componente: se ve exactamente en qué criterio el humano y la IA divergen.

Uso del dataset, en orden: few-shots de anclaje en los prompts de evaluación (los casos con mayor delta son los mejores ejemplos), fine-tuning cuando haya volumen.

Obligatorio: mínimo dos evaluadores (Sergio más Jesús o Javi) puntuando un subconjunto común cada mes. Una sola persona calibrando no entrena el scanner, entrena su sesgo.

---

## 12. UX del resultado [cerrado en estructura]

Revelación progresiva con la estética terminal actual, ascendiendo el canvas. El orden de presentación es el del briefing §4 (Misión & Visión → Valores & Atributos → Propuesta de valor → Personalidad → Idea de marca → Propósito → Magnetism → Coherencia), aunque el cálculo por debajo sea paralelo.

- **Capa 1 (siempre visible):** los cuatro datos de la sección 8.
- **Capa 2 (desplegable): el canvas TLDR puntuado.** Mismo grid que los TLDR de FLOC*. Cada caja: texto detectado o "(no detectado)", score en la esquina, mensaje personalizado. Coherencia como el marco o las líneas que conectan las cajas, con su nota. El canvas con huecos es la decisión de producto central: diagnóstico y entregable de FLOC* son el mismo artefacto en dos estados.
- **Capa 3 (desplegable):** evidencia completa + metodología, incluidas las escaleras genéricas contra las que se puntúa.

Eliminar de pantalla todo string de motor interno: "Canonical Brand Audit Snapshot", "evidence_basis", "derived_from", spaces, señales Magenta, sub-métricas sueltas.

---

## 13. Ranking público [cerrado, taxonomía abierta]

- Ordenado por Brand3 Score, con fecha, categoría primaria y percentil dentro de su cohorte.
- Solo dominio en texto plano. Sin logos, sin nombres enriquecidos, sin enlaces. Takedown visible.
- Solo entran scans completos (sin componentes `no_evaluado`).

### Categorías [abierto — borrador por pulir, actualizable]

Estructura cerrada: **una categoría primaria** (define cohorte de percentil y posición en ranking) **+ hasta dos secundarias** (filtro y contexto). El clasificador de nicho heredado del V5 sugiere; un humano confirma al publicar. Una categoría nueva solo nace cuando ≥10 scans la pedirían.

Lista semilla provisional, pendiente de trabajo — se irá puliendo con los escaneos reales:

IA · Web3/Crypto · DevTools/Infra · SaaS B2B · Fintech · E-commerce/DTC · Marketplace/Plataforma · Servicios/Agencia · Media/Comunidad · EdTech · Salud/Wellness · Consumo físico

La taxonomía vive como datos editables (no hardcodeada) para poder actualizarla sin tocar el motor.

---

## 14. Módulo visual (manual en v1) [cerrado]

Formulario interno por scan: logo (sí/no/débil), paleta definida (sí/no), tipografía propia (sí/no), consistencia entre superficies (1–5), nota libre. Lo rellena un humano en cinco minutos mirando web y redes. Alimenta los peldaños de sistema visual de Idea de marca y aparece como evidencia en Capa 2. El Visual Signature Lab queda como herramienta de investigación enlazada, fuera del flujo del scan. Con 50+ scans rellenados, se evalúa automatizar con visión.

---

## 15. Export .md [cerrado]

Botón visible en cada scan. Mismo schema que el Brand System final: mismo archivo, dos estados (`scan | system`). Estructura por componente: score, texto detectado o "(no detectado)", evidencia, mensaje. Coherencia con su lectura de conexiones. Actualizado a los 9 componentes + Coherencia (el schema del briefing §8 agrupaba por parejas; se mantiene la agrupación visual pero con los scores individuales).

---

## 16. Orden de implementación

0. **Motor en sombra.** `src/sv9/` completo (rubric v1 con las escaleras borrador, evaluador, agregador, persistencia) corriendo por replay sobre snapshots históricos. Sin tocar ninguna pantalla. Entregable: tabla comparativa V5-vs-SV9.
1. Naming y rutas con redirects 301.
2. Sesión de redacción de escaleras → `sv9-rubric-v1` definitivo.
3. Capa editorial: mensajes personalizados condicionados por veredicto; el TLDRv2 deja de leer el score V5.
4. Limpieza de la pantalla de resultado (ningún término de motor interno).
5. Canvas TLDR puntuado como Capa 2 + revelación progresiva.
6. Export .md.
7. Formulario de calibración + cola de revisión por Coherencia baja.
8. Ranking con categorías y percentil.
9. Módulo visual manual.
10. Desguace V5 al cruzar la puerta de calidad (sección 9).

---

## 17. Registro de decisiones abiertas

| Tema | Estado |
|---|---|
| Redacción final de escaleras | Sesión conjunta pendiente; formato cerrado |
| Reparto de los dos ejes de Coherencia en su escalera | Se cierra en la misma sesión |
| Números exactos de la puerta de calidad | Se ajustan con los primeros deltas reales |
| Taxonomía de categorías | Borrador abierto, se pule con scans reales |
| Umbral de cohorte para mostrar percentil (≥20) | Provisional |
| Automatización del módulo visual | Se evalúa con 50+ scans manuales |

---

Think Beautiful. Build Brand3.
