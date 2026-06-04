# Brand3 Lab: Exa deep search modes

## Veredicto

Tiene sentido evaluar `deep-lite`, `deep` y `deep-reasoning`, pero no tiene sentido activarlos por defecto ni integrarlos todavia en Brand3.

Las primeras pasadas indican que `deep-lite` aporta grounding y output sintetizado, pero no mejora la evidencia final frente a `fast` o `auto` en la muestra acotada ejecutada; aumenta coste y latencia.

## Implementacion actual

El Lab soporta variantes Exa separadas:

| Variante | Tipo Exa | Entrada por defecto | Uso |
| --- | --- | --- | --- |
| `exa` | `fast` via collector historico | Si hay key | Baseline compatible con el Lab existente. |
| `exa-fast` | `fast` via `/search` | No | Comparativa cost-aware contra otros modos Exa. |
| `exa-auto` | `auto` via `/search` | No | Router equilibrado de Exa. |
| `exa-deep-lite` | `deep-lite` via `/search` | No | Primera prueba deep de bajo presupuesto relativo. |
| `exa-deep` | `deep` via `/search` | No | Casos ambiguos, parent/product/sub-brand. |
| `exa-deep-reasoning` | `deep-reasoning` via `/search` | No | Solo casos dificiles y presupuestados. |

Los modos deep solo se ejecutan si se piden explicitamente con `--providers`. Esto evita gastar creditos accidentalmente cuando `EXA_API_KEY` existe.

## Pasada minima ejecutada

Output:

```text
out/search_enrichment_lab/20260604T101936Z
```

Comando:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 1 \
  --max-queries 1 \
  --timeout 45
```

Caso:

- LangChain
- 1 query
- 1 resultado por variante

Resultados:

| Variante | Fuente devuelta | Elegible | Clase | Latencia | Coste | Grounding |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `exa-auto` | `https://www.langchain.com` | Si | owned | 253 ms | 0.007 USD | 0 |
| `exa-fast` | `https://www.langchain.com/langchain` | Si | owned | 586 ms | 0.007 USD | 0 |
| `exa-deep-lite` | `https://www.langchain.com/about` | Si | owned | 3860 ms | 0.012 USD | 2 |

Score experimental:

| Variante | Score |
| --- | ---: |
| `exa-auto` | 3.997 |
| `exa-fast` | 3.664 |
| `exa-deep-lite` | 0.39 |

Interpretacion:

- Las tres variantes encontraron una fuente owned elegible.
- `exa-deep-lite` genero `output` y `grounding`, lo que puede ser util para research asistido.
- En este caso simple, ese grounding no mejoro la evidencia fuente: siguio siendo una URL owned.
- `exa-deep-lite` costo mas y tardo bastante mas.
- `exa-auto` fue la mejor variante de esta pasada minima.

## Decision provisional

No hay evidencia suficiente para usar `deep-lite` como baseline.

Siguiente criterio de prueba:

1. Usar `exa-fast`, `exa-auto` y `exa-deep-lite` sobre casos ambiguos, no solo sobre marcas faciles.
2. Medir si `deep-lite` descubre parent brand, producto/matriz, superficies owned ocultas o fuentes externas que `fast/auto` no detectan.
3. Comparar coste por fuente valida, no coste por llamada.
4. Revisar si `output.grounding` ayuda a explicar por que una entidad queda resuelta o provisional.
5. Mantener `deep` y `deep-reasoning` para casos dificiles, con presupuesto explicito.

## Uso recomendado para la siguiente pasada

Primero planificar:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 5 \
  --max-queries 1 \
  --timeout 45 \
  --plan-only
```

Si el coste estimado de llamadas es aceptable, ejecutar:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 5 \
  --max-queries 1 \
  --timeout 45
```

No probar `exa-deep` o `exa-deep-reasoning` en lote hasta tener una hipotesis concreta y un limite de coste.

## Pasada acotada de 5 casos

Output:

```text
out/search_enrichment_lab/20260604T102631Z
```

Comando:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-cases 5 \
  --max-queries 1 \
  --timeout 45
```

Configuracion:

- 5 casos.
- 1 query por caso.
- 1 resultado por variante.
- 15 llamadas estimadas y ejecutadas.

Resumen por proveedor:

| Variante | Elegibles | No elegibles | Revision | Latencia media | Coste total | Coste medio | Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `exa-fast` | 4 | 1 | 1 | 565.4 ms | 0.035 USD | 0.007 USD | 15.4346 |
| `exa-auto` | 4 | 1 | 1 | 1024.6 ms | 0.035 USD | 0.007 USD | 14.2254 |
| `exa-deep-lite` | 4 | 1 | 1 | 4410.4 ms | 0.060 USD | 0.012 USD | 10.0 |

Observaciones por caso:

| Caso | `exa-fast` | `exa-auto` | `exa-deep-lite` |
| --- | --- | --- | --- |
| LangChain | owned elegible | owned elegible | owned elegible + grounding |
| ChatGPT | external elegible | external elegible | external elegible + grounding |
| Base | external elegible | owned elegible | external elegible + grounding |
| Bokeroon | owned elegible | owned elegible | owned elegible + grounding |
| Obscure Thing | related unresolved, ineligible | related unresolved, ineligible | related unresolved, ineligible + grounding |

Interpretacion:

- `deep-lite` genero grounding en todos los casos, pero no cambio el resultado de elegibilidad.
- `deep-lite` no redujo revision humana ni mejoro el control negativo.
- `deep-lite` costo un 71.4% mas que `fast/auto` en esta pasada: 0.060 USD frente a 0.035 USD.
- `deep-lite` fue unas 7.8 veces mas lento que `exa-fast`: 4410.4 ms frente a 565.4 ms.
- `exa-auto` encontro mas fuentes owned que `exa-fast` y `deep-lite`, pero fue mas lento que `fast`.
- `exa-fast` obtuvo mejor score global por consenso y menor latencia.

Decision tras la pasada de 5 casos:

`exa-deep-lite` no debe ampliarse como modo general del Lab. Queda reservado para pruebas con hipotesis especifica:

- resolver parent/product/sub-brand cuando `fast` y `auto` discrepen;
- explicar una entidad provisional con grounding;
- investigar casos ambiguos donde el coste extra pueda justificarse;
- auditar si el output sintetizado ayuda a humanos, no al pipeline automatico.

El baseline operativo para siguientes comparativas Exa debe ser `exa-fast` + `exa-auto`. `exa-deep-lite` solo entra como escalado condicional.

## Prueba query compacta vs query rica en marcas menos conocidas

Pregunta:

> Si usamos marcas menos conocidas o ambiguas, una query pobre tipo `ChatGPT official brand` no prueba realmente el valor de Exa deep. Hay que probar queries ricas de research de identidad.

Veredicto:

La duda era correcta. Una query compacta no es una prueba justa para `deep-lite`.

Pero al probar una query rica sobre casos menos conocidos, `deep-lite` tampoco demostro ventaja suficiente como modo general. Aporto grounding, pero no mejoro la decision final frente a `fast`/`auto` cuando se aplican guardrails de entidad.

### Implementacion

El Lab ahora acepta:

```bash
--query-profile compact
--query-profile rich
```

`compact` conserva el comportamiento anterior:

```text
Bokeroon official brand
```

`rich` expande la query de identidad:

```text
Research the real brand/entity identity for "Bokeroon" at "https://bokeroon.com".
The current resolver status is "provisional" and resolved name is "Bokeroon".
Find sources that help decide whether this is a real company, product, parent brand,
sub-brand, ecosystem, affiliate page, marketplace listing, or ambiguous same-name entity.
Prioritize official owned surfaces, parent-company evidence, documentation, LinkedIn or
company profiles, external mentions, reviews, community/ecosystem sources, and same-name
collisions. Prefer primary and attributable sources. Return URLs that reduce identity ambiguity.
```

Tambien se anadio el fixture:

```text
examples/benchmarks/search_enrichment_lab/lesser_known_cases.json
```

Casos:

- Bokeroon: marca pequena/provisional.
- Obscure Thing: control negativo ambiguo/no resuelto.

### Runs

Compact:

```text
out/search_enrichment_lab/20260604T103822Z
```

Rich, tras guardrail:

```text
out/search_enrichment_lab/20260604T104037Z
```

Comando base:

```bash
./.venv/bin/python scripts/search_enrichment_lab.py \
  --cases-file examples/benchmarks/search_enrichment_lab/lesser_known_cases.json \
  --providers exa-fast,exa-auto,exa-deep-lite \
  --results 1 \
  --max-queries 1 \
  --timeout 45 \
  --query-profile rich
```

### Comparativa

| Perfil | Variante | Elegibles | No elegibles | Revision | Latencia media | Coste total | Score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| compact | `exa-auto` | 1 | 1 | 1 | 246.0 ms | 0.014 USD | 3.504 |
| compact | `exa-fast` | 1 | 1 | 1 | 301.0 ms | 0.014 USD | 3.449 |
| compact | `exa-deep-lite` | 1 | 1 | 1 | 4882.0 ms | 0.024 USD | -0.25 |
| rich | `exa-auto` | 1 | 1 | 1 | 232.0 ms | 0.014 USD | 3.518 |
| rich | `exa-fast` | 1 | 1 | 1 | 409.0 ms | 0.014 USD | 3.341 |
| rich | `exa-deep-lite` | 1 | 1 | 1 | 6365.0 ms | 0.024 USD | -0.25 |

### Lectura

- En Bokeroon, `rich` cambio la URL devuelta de la home a `/hello-world`, pero los tres modos encontraron una fuente owned elegible.
- En Obscure Thing, `rich` cambio el falso candidato de `obscureclo.com` a `obscureinternational.com`, pero siguio siendo una colision de nombre, no una resolucion de entidad.
- `deep-lite` anadio grounding, pero no resolvio mejor el control negativo.
- `deep-lite` mantuvo el mismo coste superior: 0.012 USD por llamada frente a 0.007 USD en `fast/auto`.
- `deep-lite` mantuvo una latencia muy superior.

### Guardrail nuevo

Durante la prueba aparecio un riesgo: con una query rica, una fuente externa con texto suficiente puede parecer elegible aunque la entidad no este resuelta.

El Lab ahora aplica esta regla:

- Si la entidad no esta `resolved`;
- y la fuente devuelta es externa;
- y no hay relacion owned/same-root clara;
- entonces la observacion no debe contar como confirmacion limpia.

Se marca para revision humana o se limita su elegibilidad segun el caso.

### Decision

La hipotesis correcta era:

> Para probar `deep-lite`, necesitamos queries ricas y marcas menos conocidas.

La evidencia actual dice:

> Incluso con queries ricas y casos menos conocidos, `deep-lite` no justifica uso general todavia.

Decision actual:

- Usar queries ricas para pruebas de research, no para el baseline normal.
- Mantener `exa-fast` y `exa-auto` como variantes principales.
- Usar `exa-deep-lite` solo como escalado condicional cuando `fast/auto` devuelvan señales contradictorias o insuficientes.
- No evaluar `deep` ni `deep-reasoning` en lote hasta tener un caso donde `deep-lite` ya haya demostrado mejora neta.
