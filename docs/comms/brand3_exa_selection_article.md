# Como elegimos Exa para enriquecer la busqueda de identidad en Brand3

Fuente de datos interna: `out/search_enrichment_lab/20260604T084043Z/summary.json`  
Estado: borrador de comunicacion FLOC*  
Uso recomendado: articulo largo para LinkedIn, blog o post editorial.  

## Veredicto

Elegimos Exa como proveedor base del Lab de enriquecimiento porque, en la muestra comparada, no fue simplemente el proveedor que "encontro cosas": fue el que devolvio mas evidencia util, menos ruido y menos carga de revision humana.

Esto importa porque Brand3 no necesita volumen de resultados. Necesita resolver una pregunta previa: que entidad estamos mirando realmente.

Antes de evaluar una marca, tenemos que distinguir si estamos ante una empresa, un producto, una documentacion tecnica, una comunidad, un marketplace, una filial, una landing de afiliacion o una coincidencia de nombre. Si esa frontera se define mal, todo lo que venga despues parece analisis, pero en realidad es contaminacion.

## El problema

Buscar informacion de una empresa en internet parece una tarea resuelta. Escribir el nombre, mirar la web, leer algunos resultados y pedirle a un modelo que lo resuma.

En la practica, eso falla pronto.

Una marca puede compartir nombre con otros proyectos. Un producto puede depender de una empresa matriz. Una web puede ser solo una pagina comercial, no la fuente principal. Una fuente puede parecer oficial y no serlo. Un resultado puede estar bien posicionado y ser irrelevante. Y una captura superficial de la web propia suele dejar fuera las senales externas que explican como existe esa marca fuera de su control.

Por eso en Brand3 separamos dos fases:

1. Identidad: determinar cual es la entidad real que estamos investigando.
2. Evidencia: buscar fuentes que ayuden a entender esa entidad desde varios angulos.

La web propia sigue siendo importante, pero no es suficiente. Necesitamos fuentes externas, documentacion, menciones, perfiles, comparativas, noticias, listados y senales de ecosistema. Tambien necesitamos detectar cuando una fuente debe quedarse fuera.

## Que probamos

Montamos un Lab online aislado de Brand3. No toca la API principal, no escribe en la base de datos canonica y no cambia el pipeline de produccion.

El objetivo era comparar proveedores de busqueda y enriquecimiento con una regla simple: solo nos interesan si mejoran la calidad de evidencia de forma economicamente viable.

En la pasada de referencia usamos 5 casos:

- LangChain, como empresa/producto tecnico con mucha superficie publica.
- ChatGPT, como producto con marca matriz clara.
- Base, como ecosistema tecnico con documentacion propia.
- Bokeroon, como caso pequeno y provisional.
- Obscure Thing, como caso negativo para comprobar si el sistema sabe no inventar identidad.

Comparamos Exa y Tavily en una muestra controlada:

- 5 casos.
- 30 observaciones por proveedor.
- 60 observaciones totales.
- Misma logica de clasificacion interna.
- Misma formula experimental de scoring.

La formula no pretende ser una verdad universal. Es una herramienta de decision para el Lab. Penaliza ruido, fuentes no elegibles, revision humana, marketplaces, entidades no resueltas, errores y latencia. Premia fuentes elegibles, consenso entre proveedores y resultados owned cuando ayudan a confirmar identidad.

## Que encontramos

Exa obtuvo un score experimental de 70.01 frente a 31.50 de Tavily.

La diferencia relevante no esta solo en el numero final. Esta en la composicion.

Exa devolvio 24 fuentes elegibles de 30. Tavily devolvio 19 de 30.

Exa produjo 6 fuentes no elegibles. Tavily produjo 11.

Exa marco 2 fuentes para revision humana. Tavily marco 5.

Exa no produjo ruido clasificado como `noise` en esta pasada. Tavily produjo 4 resultados de ruido.

Exa encontro 8 resultados clasificados como `owned`. Tavily encontro 4.

La latencia media tambien fue distinta: Exa quedo cerca de 990 ms y Tavily cerca de 4.099 ms.

Ambos proveedores coincidieron en 2 fuentes relevantes. Ese consenso es valioso porque ayuda a confirmar que una URL no es solo una ocurrencia aislada de un proveedor. Por ejemplo, ambos encontraron documentacion owned para Base y una URL owned para Bokeroon.

## Que significa esto

La conclusion no es que Tavily no sirva.

La conclusion es mas precisa: en esta pasada, Exa funciono mejor como proveedor base para evidencia de identidad y superficie de marca. Tavily puede seguir siendo util como complemento de descubrimiento, especialmente si en futuras pruebas aporta diversidad de fuentes que Exa no encuentre.

Pero para Brand3 el proveedor base tiene que cumplir otro criterio: reducir ambiguedad.

Un buen proveedor para este proceso no es el que trae mas enlaces. Es el que trae enlaces que podemos clasificar, comparar, descartar o convertir en evidencia sin obligar al sistema a adivinar.

Por eso la metrica clave no es "coverage". Es evidencia util por unidad de ruido, coste y latencia.

## Por que no lo integramos directamente

No integramos este Lab en Brand3 todavia por una razon deliberada: una mejora prometedora no es una mejora probada.

Antes de tocar produccion necesitamos mas evidencia:

- Mas casos.
- Sectores distintos.
- Empresas pequenas y grandes.
- Productos con marca matriz.
- Marcas con nombres ambiguos.
- Casos negativos.
- Medicion de coste por analisis.
- Medicion de mejora real sobre el output final de Brand3.

La decision correcta no es "meter mas proveedores". La decision correcta es integrar solo los proveedores que mejoren el resultado final y que tengan un coste defendible.

## Que aprendimos

Aprendimos que la busqueda para analisis de marca no debe ser tratada como scraping ampliado.

Scraping responde a: que dice la web.

Este proceso responde a: que entidad es esta, donde existe, quien habla de ella, que fuentes son propias, que fuentes son externas, que resultados son ruido y que pruebas merecen entrar en el analisis.

Ese cambio parece pequeno, pero cambia todo el pipeline.

Brand3 no esta intentando leer internet. Esta intentando construir una frontera de identidad suficientemente fiable para que el analisis posterior no parta de una premisa falsa.

## Cierre

Por ahora, Exa queda como baseline del Search Enrichment Lab.

No porque sea una solucion magica. No porque encuentre mas resultados en abstracto. Sino porque, con los datos actuales, nos da una mejor relacion entre evidencia util, ruido, latencia y carga de revision.

La siguiente fase no es celebrar la eleccion. Es intentar romperla con mas casos.

Si Exa sigue ganando cuando ampliemos la muestra, tendra sentido valorar su integracion en Brand3. Si otro proveedor demuestra mejor evidencia a menor coste, cambiaremos la decision.

Ese es el criterio: menos intuicion, mas evidencia.

## Version corta para LinkedIn

Estamos probando proveedores de busqueda para enriquecer la fase de identidad de Brand3.

No buscamos "mas resultados". Buscamos evidencia util para responder una pregunta anterior al analisis:

Que entidad estamos mirando realmente?

En un Lab online aislado comparamos Exa y Tavily sobre 5 casos y 60 observaciones.

Resultado de la pasada:

- Exa: 70.01 de score experimental.
- Tavily: 31.50.
- Exa: 24/30 fuentes elegibles.
- Tavily: 19/30.
- Exa: 6 fuentes no elegibles.
- Tavily: 11.
- Exa: 2 fuentes para revision humana.
- Tavily: 5.
- Exa: 0 resultados de ruido.
- Tavily: 4.
- Exa: 990 ms de latencia media.
- Tavily: 4.099 ms.

La conclusion no es que Tavily no sirva. Puede ser un buen complemento.

La conclusion es que, en esta muestra, Exa funciona mejor como baseline para construir evidencia de identidad: menos ruido, mas fuentes utilizables y menos trabajo manual.

Todavia no lo integramos en Brand3. Lo dejamos como Lab hasta tener mas evidencia, mas casos y un coste defendible.

La tesis de FLOC* aqui es simple: en analisis de marca, buscar mejor no significa encontrar mas. Significa encontrar pruebas que reduzcan ambiguedad.

