# Carrusel LinkedIn: Por que Exa queda como baseline del Lab

Fuente de datos: `out/search_enrichment_lab/20260604T084043Z/summary.json`  
Graficos: `docs/comms/assets/`

## Slide 1

Titulo:

> No elegimos Exa porque encontrara mas resultados.

Subtitulo:

> Lo elegimos porque trajo mas evidencia util para resolver identidad de marca.

Visual:

- Fondo limpio.
- Numero destacado: `70.01 vs 31.50`.
- Usar `assets/exa_vs_tavily_provider_score.svg` como base o referencia.

## Slide 2

Titulo:

> El problema no es buscar. Es saber que entidad estas mirando.

Texto:

> Empresa, producto, marca matriz, documentacion, marketplace, comunidad o coincidencia de nombre. Si esa frontera falla, el analisis posterior nace contaminado.

Visual:

- Diagrama simple de frontera de identidad.
- No usar logos de terceros salvo que tengamos permiso o sea imprescindible.

## Slide 3

Titulo:

> Montamos un Lab online, aislado de Brand3.

Texto:

> No toca la API principal. No escribe en la base canonica. No cambia produccion. Solo mide si un proveedor mejora evidencia de forma viable.

Visual:

- Tres checks: aislado, medible, reversible.

## Slide 4

Titulo:

> La muestra

Texto:

> 5 casos. 2 proveedores. 30 observaciones por proveedor. 60 observaciones totales.

Casos:

- LangChain
- ChatGPT
- Base
- Bokeroon
- Obscure Thing

Visual:

- Tabla compacta o chips de casos.

## Slide 5

Titulo:

> Exa trajo mas fuentes utilizables.

Texto:

> Exa: 24/30 fuentes elegibles. Tavily: 19/30.

Visual:

- Usar `assets/exa_vs_tavily_source_quality.svg`.

## Slide 6

Titulo:

> Tambien trajo menos ruido operativo.

Texto:

> Exa marco menos revision humana y no genero ruido clasificado como `noise` en esta pasada.

Datos:

- Revision humana: Exa 2, Tavily 5.
- Ruido: Exa 0, Tavily 4.
- No elegibles: Exa 6, Tavily 11.

Visual:

- Usar `assets/exa_vs_tavily_risk_signals.svg`.

## Slide 7

Titulo:

> La latencia tambien pesa.

Texto:

> Exa: 989.9 ms. Tavily: 4099.3 ms.

Nota:

> No decide sola, pero importa cuando el analisis requiere varias consultas por entidad.

Visual:

- Usar `assets/exa_vs_tavily_latency.svg`.

## Slide 8

Titulo:

> Conclusion provisional

Texto:

> Exa queda como baseline del Search Enrichment Lab. Tavily no queda descartado globalmente; puede tener valor como complemento de descubrimiento.

Visual:

- Baseline: Exa.
- Complemento potencial: Tavily.
- Estado: Lab, no produccion.

## Slide 9

Titulo:

> La regla para integrarlo en Brand3

Texto:

> Mas casos, mas sectores, casos negativos, coste medido y mejora real en el output final.

Visual:

- Checklist de criterios antes de integracion.

## Slide 10

Titulo:

> Buscar mejor no es encontrar mas.

Texto:

> Buscar mejor es encontrar evidencia que reduzca ambiguedad.

Visual:

- Cierre FLOC*.
- Incluir nota pequena: "Lab interno. Muestra: 5 casos, 30 observaciones por proveedor."

## Copy para el post que acompana el carrusel

Estamos probando proveedores de busqueda para enriquecer la fase de identidad de Brand3.

No buscamos mas resultados. Buscamos evidencia que ayude a responder una pregunta anterior al analisis:

Que entidad estamos mirando realmente?

En una pasada de Lab online, aislada de produccion, comparamos Exa y Tavily sobre 5 casos y 60 observaciones.

Exa obtuvo mejor relacion entre fuentes elegibles, ruido, revision humana y latencia. Por eso queda como baseline provisional del Search Enrichment Lab.

No es una integracion productiva todavia. El siguiente paso es ampliar muestra, medir coste y comprobar si la mejora se refleja en el output final de Brand3.

La tesis es simple: en analisis de marca, buscar mejor no significa encontrar mas. Significa encontrar pruebas que reduzcan ambiguedad.

