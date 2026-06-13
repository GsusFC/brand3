# Brand3 Scanner — Modelo de baldosas v3.1

Sustituye por completo a las escaleras acumulativas y al borrador v3. Documento único: reglas del modelo, reglas anti-sesgo del evaluador, las 80 baldosas y el prompt técnico para Claude Code. Listo para copiar a system prompts.

-----

## 1. Qué cambia y reglas del modelo

Las escaleras acumulativas bloqueaban marcas reales (caso SpaceX: valores perceptibles pero no declarados = 0/5). El modelo pasa a **baldosas**: cada punto es una característica clave independiente que se cumple o no. La nota de un componente es el número de baldosas encendidas.

1. **Binaria y con evidencia.** Cada baldosa se concede solo citando evidencia literal del snapshot. Sin evidencia citada, no se concede.
1. **Se evalúan todas, siempre.** Sin orden ni dependencia. El evaluador devuelve, por componente, la lista completa de baldosas con estado, evidencia o motivo.
1. **Tres estados, dos significados de cero.**
- `ok`: baldosa encendida. Suma 1 punto (×2 en Magnetism y Coherencia).
- `no`: baldosa apagada. Suma 0. Significa: el snapshot demuestra que la marca no lo comunica o no lo cumple. Es un fallo de marca.
- `sin_evidencia`: **punto ciego**. Suma 0 al cómputo, pero en el informe y la UI se diferencia visualmente de una apagada (celda atenuada, no roja) y lleva su motivo y una invitación: “aporta contexto para iluminar este punto”. No es un fallo de marca; es un límite del snapshot.
- Frontera entre ambos: si la prueba *podría* estar en la huella pública y no está, la baldosa se **apaga** (no comunicarlo es el fallo). `sin_evidencia` se reserva para baldosas cuya prueba el snapshot estructuralmente no puede contener: cohorte competitivo, experiencia real de producto, dinámica interna de comunidad.
1. **Confianza.** El componente baja a confianza `media` con 2 baldosas `sin_evidencia` y a `baja` con 3 o más. La confianza se muestra junto a la nota.
1. **Tope de Magnetism** (única dependencia que sobrevive): si la media normalizada de los 8 componentes base es inferior a 4/10, las baldosas `ok` de Magnetism se capan en 5 (10/20 tras el ×2).
1. Las baldosas apagadas son el plan de trabajo: cada una mapea a una entrega de construcción. El export .md las lista por componente. Los puntos ciegos son el gancho de conversación: el fundador que aporta contexto ya está hablando con FLOC*.

Total invariable: 60 puntos base + Magnetism 20 + Coherencia 20 = 100.

-----

## 2. Reglas anti-sesgo del evaluador

Se inyectan en el system prompt antes de las baldosas.

> ### Marco de categoría (antes de puntuar)
>
> Clasifica el juego de la marca a partir de la evidencia del snapshot, nunca de tu conocimiento previo: consumo, B2B SaaS, infraestructura/DeepTech, institucional, lujo/cultural. La clasificación no cambia las baldosas ni los puntos: cambia qué cuenta como evidencia válida.
>
> ### Reglas
>
> 1. **Las baldosas miden construcción, no temperatura.** Ninguna exige tono “humano”, “cercano” o “empático”. Un arquetipo implacable y técnico ejecutado con consistencia total puntúa igual que uno cálido. Evalúa nitidez y consistencia, no simpatía.
> 1. **El magnetismo tiene cinco mecanismos válidos: dolor, deseo, asombro, pertenencia y estatus.** Pertenencia es formar parte de algo; estatus es señalar posición ante los demás (clave en lujo, premium y Web3). No los confundas ni los cuentes doble. Identifica el mecanismo dominante antes de evaluar su ejecución; exigir “gancho de dolor” a una marca cuyo motor es el asombro o el estatus es un error de evaluación, no un fallo de la marca.
> 1. **El público puede ser inequívoco sin estar nombrado.** Si producto y contexto del snapshot hacen evidente quién compra, el criterio se cumple con esa evidencia.
> 1. **“Problema real” incluye problemas de industria, de infraestructura, de mundo y fronteras tecnológicas,** no solo dolores cotidianos de usuario final.
> 1. **Detección no es declaración.** Valores y atributos perceptibles de forma consistente en tono, decisiones y producto cuentan como detectados aunque no exista una página que los liste. Anota la vía: declarado o inferido.
> 1. **Evalúa ÚNICAMENTE el contenido presente en el snapshot.** Tu conocimiento pre-entrenado sobre la marca no existe a efectos de esta evaluación. Si sabes que la marca hace X pero X no aparece en el snapshot, la marca está fallando en comunicarlo: la baldosa se apaga. No completes, no asumas, no rellenes huecos con memoria. Toda evidencia citada debe ser literal del snapshot. La fama no sube puntos, no baja puntos y no es evidencia en ningún sentido.

-----

## 3. Las baldosas (80 en total)

### Misión (5 baldosas × 1 punto)

|# |Baldosa  |Se enciende si                                                                                   |
|--|---------|-------------------------------------------------------------------------------------------------|
|M1|Detectada|Hay una misión identificable en superficie pública propia.                                       |
|M2|Propia   |No es intercambiable con cualquier marca de su categoría (“ser líderes” no enciende).            |
|M3|Anclada  |Conecta con un problema real: del usuario, de la categoría, del mundo o una frontera tecnológica.|
|M4|Coherente|No contradice propósito ni propuesta; encaja en el discurso.                                     |
|M5|Ambiciosa|Marca un camino que lidera o redefine su categoría.                                              |

### Visión (5 × 1)

|# |Baldosa     |Se enciende si                                               |
|--|------------|-------------------------------------------------------------|
|V1|Detectada   |Hay un destino identificable.                                |
|V2|Concreta    |El destino se nombra; “transformar la industria” no enciende.|
|V3|Propia      |Distinguible de la visión de su competencia.                 |
|V4|Conectada   |Se entiende el camino entre la misión de hoy y el destino.   |
|V5|De categoría|Define hacia dónde va el mercado, no solo la empresa.        |

### Valores (5 × 1)

|#  |Baldosa     |Se enciende si                                                 |
|---|------------|---------------------------------------------------------------|
|VA1|Detectados  |Declarados o inferibles en tono y decisiones del snapshot.     |
|VA2|Propios     |Con ángulo; “transparencia, innovación, calidad” no enciende.  |
|VA3|Perceptibles|El tono los transmite sin leer ninguna lista.                  |
|VA4|Demostrados |Copy, producto o decisiones públicas del snapshot los ejecutan.|
|VA5|Polarizantes|Repelen activamente a quien no es su cliente o talento ideal.  |

### Atributos (5 × 1)

|# |Baldosa      |Se enciende si                                                                                               |
|--|-------------|-------------------------------------------------------------------------------------------------------------|
|A1|Detectados   |Características tangibles identificables.                                                                    |
|A2|Específicos  |Sin adjetivos comodín.                                                                                       |
|A3|Verificables |Comprobables en producto o experiencia según el snapshot.                                                    |
|A4|Diferenciales|Distintos frente a alternativas. Requiere evidencia de cohorte en el snapshot; si no la hay, `sin_evidencia`.|
|A5|Integrados   |La marca los usa como argumento de venta, no solo los lista.                                                 |

### Propuesta de valor (10 × 1)

|#  |Baldosa              |Se enciende si                                                                    |
|---|---------------------|----------------------------------------------------------------------------------|
|P1 |Detectada            |La hero dice qué venden.                                                          |
|P2 |Clara                |Se entiende sin conocer la categoría.                                             |
|P3 |En beneficios        |Habla de resultado, no solo de features.                                          |
|P4 |Público inequívoco   |Nombrado, o evidente por producto y contexto.                                     |
|P5 |Tensión nombrada     |Se sabe qué dolor, deseo, necesidad o frontera tecnológica resuelve o rompe.      |
|P6 |Propia               |La frase no vale para su competencia.                                             |
|P7 |Diferencial explícito|Dice por qué ella y no las alternativas. Requiere cohorte; si no, `sin_evidencia`.|
|P8 |Mecanismo propio     |El cómo es identificable y difícil de copiar.                                     |
|P9 |Prueba a la vista    |Proof signals en la primera pantalla.                                             |
|P10|Promesa verificable  |Datos, casos o garantías irrefutables en el snapshot.                             |

### Personalidad / Arquetipo (10 × 1)

|#   |Baldosa                        |Se enciende si                                                      |
|----|-------------------------------|--------------------------------------------------------------------|
|PE1 |Voz detectable                 |Hay un tono, no una plantilla.                                      |
|PE2 |Sin clichés                    |No cae en los tics de su categoría.                                 |
|PE3 |Arquetipo identificable        |Se puede nombrar: rebelde, sabio, creador, maverick…                |
|PE4 |Consistente entre páginas      |El tono no cambia de la home al pricing.                            |
|PE5 |Consistente en microcopy       |Botones, errores y detalles hablan igual.                           |
|PE6 |Consistente en redes y producto|La voz sobrevive fuera de la web.                                   |
|PE7 |Rasgos propios                 |Giros, ritmo, humor o dureza reconocibles.                          |
|PE8 |Coherente con valores e idea   |La personalidad ejecuta lo que la marca dice ser. Temperatura libre.|
|PE9 |Test del logo tapado           |Se reconoce quién habla sin ver la marca.                           |
|PE10|Citable                        |Genera contenido que otros recuerdan o imitan.                      |

### Idea de marca (10 × 1)

|#  |Baldosa                  |Se enciende si                                                                 |
|---|-------------------------|-------------------------------------------------------------------------------|
|I1 |Identidad existente      |No es una plantilla sin alterar.                                               |
|I2 |Sistema                  |Logo, color y tipografía funcionan como conjunto.                              |
|I3 |No genérica              |Se distingue de la estética estándar de su categoría.                          |
|I4 |Concepto detectable      |Hay una idea detrás, declarada o evidente.                                     |
|I5 |Concepto ejecutado       |La idea se ve en la web principal, no solo se declara.                         |
|I6 |Dirección de arte        |Decisiones visuales intencionadas, no decorativas.                             |
|I7 |Traduce la estrategia    |El visual expresa propósito y personalidad.                                    |
|I8 |Consistente              |El sistema se sostiene en todas las superficies del snapshot.                  |
|I9 |Universo propio          |Estética reconocible como suya.                                                |
|I10|Eleva el precio percibido|El envoltorio hace al producto parecer mejor de lo que sus features justifican.|

### Propósito (10 × 1)

|#   |Baldosa                 |Se enciende si                                                             |
|----|------------------------|---------------------------------------------------------------------------|
|PR1 |Detectado               |Hay un porqué en alguna superficie.                                        |
|PR2 |Explícito               |Escrito, no solo intuible.                                                 |
|PR3 |Más allá del qué        |Responde por qué existen, no qué hacen.                                    |
|PR4 |Propio                  |“Hacer el mundo mejor” no enciende.                                        |
|PR5 |Anclado                 |Conecta con su categoría y su producto.                                    |
|PR6 |Conectado a la propuesta|El porqué justifica el qué venden.                                         |
|PR7 |Cadena completa         |Propósito, misión y visión se sostienen juntos.                            |
|PR8 |Respirado               |Tono y diseño lo transmiten sin leer el “about”.                           |
|PR9 |Demostrado              |Al menos una decisión de negocio pública del snapshot lo ejecuta.          |
|PR10|Reputación              |Varias decisiones verificables por terceros; el porqué es su prueba social.|

### Magnetism (10 × 1, peso ×2)

|#   |Baldosa                |Se enciende si                                                              |
|----|-----------------------|----------------------------------------------------------------------------|
|MG1 |Retiene                |Algo detiene el scroll, verbal o visual.                                    |
|MG2 |Mecanismo identificable|Se sabe cuál opera: dolor, deseo, asombro, pertenencia o estatus.           |
|MG3 |Hook                   |Gancho claro anclado a una tensión real de su audiencia.                    |
|MG4 |Tensión narrativa      |Hay historia, no solo descripción.                                          |
|MG5 |Memorable              |Una frase o imagen que se queda.                                            |
|MG6 |Invita a explorar      |La huella pide seguir navegando.                                            |
|MG7 |Genera deseo           |El packaging hace al producto parecer superior.                             |
|MG8 |Genera preferencia     |Da razones para elegirla frente a alternativas con más features.            |
|MG9 |Pertenencia o estatus  |Señales de orgullo: comunidad que presume o posición que se exhibe.         |
|MG10|Gravedad propia        |Atrae talento, prensa o comunidad sin empujar, según evidencia del snapshot.|

Tope: regla 5 de la sección 1.

### Coherencia (10 × 1, peso ×2)

|#  |Baldosa                      |Se enciende si                                                                                                                                                                                                                                                                |
|---|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|C1 |Sin contradicciones graves   |No prometen simplicidad con un producto laberíntico.                                                                                                                                                                                                                          |
|C2 |Sin contradicciones parciales|Los mensajes clave no se pisan entre sí.                                                                                                                                                                                                                                      |
|C3 |Propósito-misión             |El porqué y el camino encajan.                                                                                                                                                                                                                                                |
|C4 |Misión-propuesta             |Lo que persiguen y lo que venden encajan.                                                                                                                                                                                                                                     |
|C5 |Valores en el tono           |La personalidad ejecuta los valores declarados o inferidos.                                                                                                                                                                                                                   |
|C6 |Diseño-copy                  |El visual cuenta la misma historia que el texto.                                                                                                                                                                                                                              |
|C7 |Web-redes                    |El discurso sobrevive al cambio de canal.                                                                                                                                                                                                                                     |
|C8 |Marca-producto               |La experiencia real cumple lo que la marca proyecta. **Nota para el evaluador: el scanner no puede probar el producto. Por defecto `sin_evidencia`, salvo que el snapshot contenga pruebas sociales contundentes: reviews, casos de estudio detallados o demos comprobables.**|
|C9 |Refuerzo mutuo               |Las piezas se apoyan entre sí, no solo conviven.                                                                                                                                                                                                                              |
|C10|Inseparable                  |Imposible distinguir dónde acaba el producto y empieza la marca.                                                                                                                                                                                                              |

-----

## 4. Protocolo de output del evaluador

Por cada componente, JSON estricto:

```json
{
  "componente": "magnetism",
  "baldosas": [
    {"id": "MG1", "estado": "ok", "evidencia": "cita literal del snapshot"},
    {"id": "MG2", "estado": "ok", "evidencia": "mecanismo dominante: asombro"},
    {"id": "MG8", "estado": "no", "motivo": "ninguna razón de preferencia frente a alternativas en la huella"},
    {"id": "MG9", "estado": "sin_evidencia", "motivo": "el snapshot no contiene señales de comunidad", "contexto_requerido": "enlaces a comunidad, testimonios o menciones de usuarios"}
  ],
  "puntos": 7,
  "confianza": "media"
}
```

- `puntos` = recuento de baldosas `ok` (el ×2 de Magnetism y Coherencia lo aplica el backend, nunca el LLM).
- `evidencia` obligatoria en cada `ok`, citada literal del snapshot.
- `motivo` obligatorio en cada `no` y `sin_evidencia`; `contexto_requerido` opcional en `sin_evidencia` para pedir al usuario lo que iluminaría el punto ciego.
- `confianza`: `alta` por defecto, `media` con 2 `sin_evidencia`, `baja` con 3 o más.
- UI: tres estados visuales por celda. Encendida, apagada (rojo: fallo de marca), punto ciego (atenuada, con motivo y CTA de aportar contexto). Nunca pintar un punto ciego como fallo.

-----

## 5. Gobierno del modelo

Las baldosas se cambian por calibración, no por intuición. Una baldosa que nunca se enciende, que siempre se enciende o en la que los evaluadores humanos no coinciden está mal escrita: se reescribe, se divide o se elimina en la siguiente versión, con registro.
