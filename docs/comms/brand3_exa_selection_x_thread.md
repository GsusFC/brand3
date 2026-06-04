# Hilo para X: por que elegimos Exa como baseline del Lab

Fuente de datos interna: `out/search_enrichment_lab/20260604T084043Z/summary.json`

## Hilo

1/ Estamos probando proveedores de busqueda para enriquecer Brand3.

La pregunta no es: que proveedor encuentra mas links?

La pregunta es: que proveedor ayuda mejor a saber que entidad estamos analizando realmente?

2/ Antes de analizar una marca hay que resolver identidad.

Empresa, producto, matriz, documentacion, marketplace, filial, comunidad, afiliado o simple coincidencia de nombre.

Si esa frontera falla, el analisis posterior nace contaminado.

3/ Montamos un Lab online aislado.

No toca la API de Brand3.
No escribe en la base de datos canonica.
No cambia produccion.

Solo mide si un proveedor mejora evidencia de forma viable.

4/ Pasada de referencia:

- 5 casos.
- 2 proveedores: Exa y Tavily.
- 30 observaciones por proveedor.
- 60 observaciones totales.

Casos: LangChain, ChatGPT, Base, Bokeroon y un caso negativo.

5/ Resultado experimental:

- Exa: 70.01
- Tavily: 31.50

No es un benchmark universal. Es una metrica interna de Lab para decidir si una fuente reduce ruido y ambiguedad.

6/ La diferencia importante:

- Exa: 24/30 fuentes elegibles.
- Tavily: 19/30.

Exa trajo mas material que el pipeline puede usar sin forzar interpretaciones.

7/ Senales de riesgo:

- Exa: 6 fuentes no elegibles.
- Tavily: 11.
- Exa: 2 fuentes para revision humana.
- Tavily: 5.
- Exa: 0 resultados de ruido.
- Tavily: 4.

Menos ruido importa mas que mas volumen.

8/ Latencia media:

- Exa: 990 ms.
- Tavily: 4.099 ms.

La velocidad no decide sola, pero afecta al coste operativo de un pipeline con multiples consultas.

9/ Conclusion provisional:

Exa queda como baseline del Search Enrichment Lab.

Tavily no queda descartado como complemento, pero en esta muestra no gana como proveedor principal para identidad y evidencia.

10/ La regla para integrarlo en Brand3:

Mas casos.
Mas sectores.
Mas casos negativos.
Coste medido.
Mejora real en el output final.

Hasta entonces, sigue siendo Lab.

11/ La tesis:

Buscar mejor no es encontrar mas.

Buscar mejor es encontrar evidencia que reduzca ambiguedad.

Eso es lo que necesitamos antes de pedirle a un sistema que opine sobre una marca.

