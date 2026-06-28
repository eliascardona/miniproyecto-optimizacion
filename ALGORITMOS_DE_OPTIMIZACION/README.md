# config.json — Esquema y reglas de validación de entrada (diseño de filtros)

Este documento describe, campo por campo, cómo debe construirse el config.json
que consumen los scripts de optimización de cada tipo de filtro
(FILTRO_PASABAJAS, FILTRO_PASAALTAS, FILTRO_PASABANDA,
FILTRO_RECHAZABANDA). Está pensado para el equipo de informática: define
**qué** debe validarse antes de invocar el script — no cómo implementar esa
validación, eso queda a criterio del equipo.

Esta estructura de config.json no depende de cuál algoritmo de
optimización se use para resolver el problema: la única parte del contrato
que cambia de un algoritmo a otro es el contenido de parametros_optimizador
(sección 6), donde cada algoritmo define su propio conjunto de claves; el
resto del esquema (entorno, barrido_ac, frecuencias) es el mismo sin
importar el algoritmo.

**Lo más importante primero:** el script de cada filtro solo captura dos
errores de forma controlada: archivo no encontrado y JSON mal formado.
**Todo lo demás —una clave faltante, un tipo de dato incorrecto, un valor
fuera de rango— provoca una excepción cruda de Python** sin ningún mensaje
útil para el usuario final de la API. Por diseño, toda la validación de este
documento debe vivir en la capa de la API, devolviendo un error claro, antes
de que el JSON llegue al script.

---

## 1. El config.json no dice qué tipo de filtro es

Ningún script lee un campo "tipo" o "filtro" dentro del JSON. El tipo de
filtro (pasabajas / pasaaltas / pasabanda / rechazabanda) está implícito en
**qué script se invoca**, no en el contenido del JSON.

**Recomendación para la API:** que el endpoint (o un campo a nivel de
*request*, fuera de este config.json) sea lo que decide qué script
invocar, y que ese dato se use únicamente para enrutar — no debería
reenviarse dentro del config.json que recibe el script, porque este lo
ignoraría silenciosamente (no lo lee, pero tampoco lo rechaza).

---

## 2. Esqueleto común a los 4 tipos de filtro

Los 4 config.json comparten exactamente la misma forma general; lo único
que cambia entre tipos de filtro (y según modo) es el contenido de
frecuencias (sección 7).

```json
{
  "modo": "BASICO | AVANZADO",
  "entorno": {
    "v_fuente": 5,
    "r_fuente": 470,
    "r_carga": 470
  },
  "barrido_ac": {
    "f_inicial": 100,
    "f_final": 100000
  },
  "parametros_optimizador": [
    { "clave": "tam_poblacion",     "valor": 30 },
    { "clave": "num_generaciones",  "valor": 30 },
    { "clave": "prob_cruce",        "valor": 0.7 },
    { "clave": "prob_mutacion",     "valor": 0.25 },
    { "clave": "elitismo",          "valor": 2 },
    { "clave": "torneo_k",          "valor": 4 }
  ],
  "frecuencias": [
    { "clave": "f_paso", "valor": 500 },
    { "clave": "f_aten", "valor": 10000 }
  ]
}
```

Las 5 claves raíz (modo, entorno, barrido_ac, parametros_optimizador,
frecuencias) son **todas obligatorias**. Si falta cualquiera, el script
termina en una excepción no controlada.

El ejemplo anterior muestra las claves de parametros_optimizador para el
Algoritmo Genético. Si el filtro se va a optimizar con PSO, ese mismo
arreglo cambia a las claves num_particulas, num_iteraciones, w, c1 y c2
(ver sección 6); el resto del esqueleto (entorno, barrido_ac, frecuencias)
no cambia.

Dentro de parametros_optimizador y frecuencias, el **orden de los
elementos del arreglo no importa** — cada valor se busca por su "clave",
no por posición. Lo que sí importa es que la clave exista exactamente con
ese nombre (sensible a mayúsculas/minúsculas) y que tenga un "valor"
numérico.

---

## 3. modo

| | |
|---|---|
| **Tipo** | string |
| **Dominio válido** | "BASICO" o "AVANZADO" (únicamente) |
| **Obligatorio** | Sí |

**Punto crítico para la validación de la API:** el script normaliza el
valor recibido (quita espacios y lo pasa a mayúsculas) y luego compara
contra "BASICO"; cualquier otro valor cae en AVANZADO. Esto significa
que:
- Es insensible a mayúsculas/minúsculas y espacios (" basico " y
  "BASICO" son equivalentes).
- **Cualquier valor que no sea exactamente "BASICO" cae en AVANZADO sin
  avisar.** Un typo como "BASCO" o "AVANSADO" no truena: el script
  simplemente exige las claves de frecuencia del modo AVANZADO (sección 7),
  no las de BASICO. Esto puede confundir mucho a quien esté depurando.

La API debe validar el enum de forma estricta (rechazar cualquier valor
que, normalizado, no sea "BASICO" ni "AVANZADO") antes de confiar en el
comportamiento del script.

---

## 4. entorno

```json
"entorno": { "v_fuente": 5, "r_fuente": 470, "r_carga": 470 }
```

Las 3 claves (v_fuente, r_fuente, r_carga) son obligatorias; el script
las indexa directamente, así que cualquiera ausente provoca un error.

### 4.1 v_fuente

| | |
|---|---|
| **Tipo** | number (entero o decimal) |
| **Regla dura** | **Estrictamente > 0** |
| **Recomendado** | 0 < v_fuente ≤ 10 (ver nota) |

v_fuente es la amplitud (V) de la fuente AC. Si vale 0, el script
**truena por división entre cero**: el voltaje objetivo de la banda de paso
se deriva de v_fuente, y varias fórmulas internas dividen entre ese valor.

La alimentación del amplificador operacional se deriva automáticamente como
Vpp = v_fuente + 10 y Vnn = -(v_fuente + 10). Esto no está limitado en
el código, pero el modelo de amplificador usado en la simulación (LM741)
tiene un rango de alimentación recomendado de fábrica de ±5 V a ±15 V
(máximo absoluto ±22 V). Topar v_fuente en 10 V deja Vpp/Vnn en ±20 V:
todavía dentro del máximo absoluto del LM741, aunque ya por encima de su
rango recomendado de operación de fábrica. Esto **no lo exige el script**;
es el tope que se adopta para este contrato.

### 4.2 r_fuente y r_carga

| | |
|---|---|
| **Tipo** | number (entero o decimal) |
| **Regla dura** | > 0 |
| **Regla solicitada** | Debe pertenecer a la **serie E12** |

Son la resistencia de fuente (Rs) y de carga (Rl) del circuito. El
script no valida que pertenezcan a una serie comercial (acepta cualquier
número > 0 sin quejarse), pero la serie E12 ya es la que se usa
internamente para generar **todas las resistencias del circuito que sí se
optimizan**, así que pedir lo mismo para r_fuente/r_carga mantiene
consistencia con el resto del diseño.

**Definición de la serie E12:**

```
valor = mantisa × 10ⁿ
mantisa ∈ {1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2}
n ∈ ℤ   (década, p. ej. n=2 → ×100, n=3 → ×1000)
```

Rango de décadas recomendado: n ∈ {1, 2, 3, 4, 5} → de **10 Ω a 820 000 Ω**,
que es el mismo rango que se usa internamente para las resistencias que sí
se optimizan dentro del circuito. Mantener r_fuente/r_carga en ese mismo
orden de magnitud evita combinaciones de impedancia poco realistas para las
topologías usadas en estos filtros.

Ejemplos válidos: 10, 22, 100, 470, 1000, 2200, 4700, 10000, 33000, 820000.
Ejemplos **inválidos**: 500 (no es mantisa E12 × década), 300, 750.

---

## 5. barrido_ac

```json
"barrido_ac": { "f_inicial": 100, "f_final": 100000 }
```

Estas dos frecuencias (Hz) definen el rango del barrido de la simulación.

| Campo | Tipo | Regla |
|---|---|---|
| f_inicial | integer | > 0 |
| f_final | integer | ≤ 10 000 000 |
| (relación) | — | f_inicial < f_final (estricto) |

- El script internamente castea ambos valores a decimal, así que
  técnicamente toleraría valores no enteros; **se exige entero como regla de
  contrato de la API**, no porque el script lo necesite.
- f_final ≤ 10 000 000 es el tope solicitado para este contrato; el script
  no lo valida, así que debe aplicarse en la API.
- Si f_inicial >= f_final, el barrido queda invertido o de ancho cero, y
  la simulación puede comportarse de forma indefinida. Validar
  f_inicial < f_final siempre.

### 5.1 Regla recomendada: frecuencias "redondas" (por décadas)

Se puede (opcionalmente) restringir f_inicial/f_final a valores con **un
solo dígito significativo seguido de ceros**:

```
f = d × 10ⁿ ,   d ∈ {1, 2, ..., 9},   n ∈ {0, 1, 2, ...}
```

Bajo esta regla, un valor como 37 no sería válido: el sistema debería
ofrecer/aceptar el más cercano por abajo (30) o por arriba (40), no 37
directamente. Valores válidos: 1, 2, …, 9, 10, 20, …, 90, 100, 200, …,
10000000.

Esto **no lo exige el script**, pero conviene adoptarlo porque:
1. Es coherente con un barrido que avanza por décadas.
2. Los config.json de ejemplo del proyecto ya siguen esta convención sin
   excepción (1, 100, 100000, etc., todos son un dígito seguido de
   ceros) — es el patrón real que ya se usa.
3. Simplifica la UI de la futura API (p. ej. un selector de "dígito 1-9" +
   "década").

**Nota:** esta misma convención conviene aplicarla a *todas* las
frecuencias del JSON, no solo a f_inicial/f_final — ver sección 7.6,
donde se muestra que f_paso, f_aten, f_aten_1, etc. de los ejemplos
también la cumplen.

### 5.2 Margen mínimo de una década entre el barrido y las frecuencias de interés

No basta con que las frecuencias de interés (fc_objetivo, f_paso,
f_aten, etc., sección 7) caigan dentro de (f_inicial, f_final): la más
baja del conjunto debe quedar **al menos una década por encima de
f_inicial**, y la más alta **al menos una década por debajo de
f_final**:

```
frecuencia_más_baja  ≥ f_inicial × 10
frecuencia_más_alta  ≤ f_final / 10
```

(El detalle de cuál clave es la más baja/alta en cada tipo de filtro y modo
está en las subsecciones de la sección 7).

Esto es necesario para que el cálculo de la pendiente entre bandas sea
confiable: ese cálculo toma como referencia un punto ubicado una década más
allá de la frecuencia de interés (en modo BASICO esto es explícito: la
pendiente se mide en frecuencia_objetivo × 10 o ÷ 10, según el filtro).
Si la frecuencia de interés no tiene esa década de margen dentro del
barrido, ese punto de referencia queda fuera del rango simulado y el
cálculo deja de ser representativo.

---

## 6. parametros_optimizador

Arreglo de pares {clave, valor} con los hiperparámetros propios del
algoritmo de optimización que se esté usando. El contenido exacto de este
arreglo depende de cuál sea ese algoritmo: cada algoritmo se documenta en
esta sección con su propio subtítulo y su propio listado de claves, sin
afectar el resto del contrato (entorno, barrido_ac, frecuencias son
independientes del algoritmo elegido).

### Algoritmo Genético (AG)

Claves obligatorias (deben llamarse exactamente así):

| Clave | Tipo | Regla dura |
|---|---|---|
| tam_poblacion | integer | ≥ 1 — bloqueante: en 0, el AG no tiene de dónde elegir el mejor individuo y termina en error |
| num_generaciones | integer | ≥ 1 — bloqueante: en 0, no queda ningún individuo evaluado que guardar al final |
| prob_cruce | number | entre 0 y 1 — no bloqueante fuera de ese rango, pero deja de ser una probabilidad válida |
| prob_mutacion | number | entre 0 y 1 — no bloqueante, mismo caso |
| elitismo | integer | 0 ≤ elitismo < tam_poblacion — no bloqueante, pero si elitismo ≥ tam_poblacion la población deja de evolucionar (ver abajo) |
| torneo_k | integer | ≥ 1 — bloqueante: en 0 o negativo, la selección de padres termina en error |

**Valores ideales y por qué** (los circuitos de este proyecto tienen entre 6
y 8 componentes a optimizar, cada uno elegido de una lista de 24 a 60
valores comerciales posibles — esa escala es la referencia para los rangos
de abajo):

- **tam_poblacion** — ideal entre 20 y 50. Una población más grande
  explora más combinaciones por generación y reduce el riesgo de quedarse
  en un óptimo local, pero cada individuo nuevo implica correr una
  simulación completa del circuito, así que poblaciones muy grandes vuelven
  el proceso lento sin una mejora proporcional. Por debajo de ~10 individuos
  la convergencia es rápida pero con alto riesgo de estancarse en una
  solución mediocre por falta de diversidad.

- **num_generaciones** — ideal entre 30 y 50. Cada generación nueva solo
  mejora si el cruce y la mutación todavía encuentran combinaciones
  mejores; pasado cierto punto la población ya convergió y generaciones
  adicionales solo añaden tiempo de cómputo sin cambios apreciables en el
  resultado. Por debajo de ~15-20 generaciones, la búsqueda suele cortarse
  antes de que el algoritmo tenga oportunidad de refinar la solución.

- **prob_cruce** — ideal entre 0.7 y 0.9. El cruce combina las partes
  buenas que ya encontraron distintos individuos (por ejemplo, una etapa
  bien ajustada de un padre con otra etapa bien ajustada de otro padre); con
  una probabilidad alta, casi todas las parejas seleccionadas se cruzan en
  cada generación, lo que acelera esa combinación. Con una probabilidad
  baja, la mayoría de los hijos son copias directas de sus padres y la
  búsqueda pasa a depender casi solo de la mutación, lo que la hace más
  lenta.

- **prob_mutacion** — ideal entre 0.2 y 0.35 (más alto que la
  recomendación típica de los libros de texto sobre AG, por la razón
  siguiente). Aquí cada "gen" no es un bit ni un número continuo, sino el
  índice de un componente dentro de una lista corta de valores comerciales
  (24 a 60 opciones), y el cromosoma completo tiene pocos genes (6 a 8). Con
  tan pocos genes, una probabilidad de mutación baja deja a la población
  mutando casi nunca, y un cromosoma tan corto se homogeniza rápido solo con
  cruce (se pierde diversidad en pocas generaciones). Una probabilidad más
  alta por gen compensa eso sin volverse búsqueda puramente aleatoria,
  porque la probabilidad de que un individuo mute en más de uno o dos genes
  a la vez sigue siendo moderada. Por encima de ~0.5, el algoritmo deja de
  aprovechar lo que el cruce ya combinó y se comporta más como búsqueda
  aleatoria.

- **elitismo** — ideal entre 2 y 4 individuos, o aproximadamente 5-10 %
  de tam_poblacion. Garantiza que el mejor individuo encontrado hasta el
  momento no se pierda por una mala combinación de cruce/mutación en la
  siguiente generación; sin nada de elitismo, es posible retroceder en la
  calidad del mejor resultado de una generación a otra. Si se reserva una
  porción muy grande de la población como elite, queda menos espacio para
  generar individuos nuevos y la búsqueda explora menos.

- **torneo_k** — ideal entre 2 y 5, o aproximadamente 10 % de
  tam_poblacion. Define cuánta presión selectiva hay para elegir a los
  padres: con un torneo pequeño (k=2), incluso un individuo mediocre
  tiene una probabilidad razonable de ser elegido como padre, lo que
  mantiene diversidad pero hace la convergencia más lenta. Con un torneo
  grande (k cercano a tam_poblacion), casi siempre gana el mejor
  individuo de toda la población, lo que acelera la convergencia pero puede
  converger demasiado rápido a una sola solución y perder la oportunidad de
  explorar otras combinaciones.

### Enjambre de Partículas (PSO)

Claves obligatorias (deben llamarse exactamente así):

| Clave | Tipo | Regla dura |
|---|---|---|
| num_particulas | integer | ≥ 1 — bloqueante: en 0 no hay enjambre que evaluar y el script termina en error al buscar el mejor índice sobre una lista vacía |
| num_iteraciones | integer | ≥ 0 — **no bloqueante en 0**: a diferencia del AG, PSO evalúa la posición inicial de cada partícula antes de entrar al ciclo principal, así que en 0 iteraciones el script sí termina y guarda un resultado, pero ese resultado es solo el mejor de un enjambre inicial aleatorio, sin ningún refinamiento |
| w | number | sin un mínimo/máximo que el script valide; fuera de [0, 1] el enjambre puede divergir (ver abajo) |
| c1 | number | sin mínimo que el script valide; valores negativos invierten la atracción hacia el mejor personal y no tienen sentido físico para el algoritmo |
| c2 | number | mismo caso que c1, pero para la atracción hacia el mejor global |

**Valores ideales y por qué** (misma referencia de escala que el AG: 6 a 8
componentes a optimizar, cada uno con 24 a 60 valores comerciales
posibles):

- **num_particulas** — ideal entre 20 y 40. Cada partícula es, en esencia,
  un individuo del AG que en vez de cruzarse y mutar se desplaza guiado por
  su propia mejor posición histórica y la del enjambre; un enjambre más
  grande cubre más del espacio de búsqueda en cada iteración, pero igual
  que en el AG, cada partícula nueva implica una simulación completa del
  circuito, así que el costo crece linealmente con este valor.

- **num_iteraciones** — ideal entre 30 y 50, por la misma razón que
  num_generaciones en el AG: pasado cierto punto el enjambre ya convergió
  alrededor de un óptimo y las iteraciones adicionales solo agregan tiempo
  de cómputo. Aquí sí importa más no quedarse corto, porque con muy pocas
  iteraciones (sección anterior) el resultado puede ser apenas mejor que
  una búsqueda aleatoria.

- **w (inercia)** — ideal entre 0.4 y 0.9. Controla qué tanto conserva
  cada partícula su velocidad anterior: un valor alto favorece la
  exploración (la partícula sigue "viajando" aunque el enjambre ya tenga
  un buen candidato), mientras que un valor bajo la frena rápido cerca de
  los mejores puntos encontrados, favoreciendo la explotación. Valores por
  encima de 1 pueden hacer que la velocidad crezca sin control de una
  iteración a otra (el enjambre "vibra" sin converger).

- **c1 (coeficiente cognitivo)** y **c2 (coeficiente social)** — ideal
  entre 1.0 y 2.0 cada uno, y típicamente con c1 ≈ c2 para no sesgar el
  enjambre hacia un solo tipo de atracción. c1 pondera cuánto se mueve una
  partícula hacia su propia mejor posición histórica (memoria individual);
  c2 pondera cuánto se mueve hacia la mejor posición encontrada por todo el
  enjambre (memoria colectiva). Si c1 domina sobre c2, las partículas
  exploran de forma casi independiente y el enjambre tarda más en
  coordinarse; si c2 domina sobre c1, todas las partículas convergen rápido
  hacia el mismo punto, con riesgo de quedarse en un óptimo local antes de
  tiempo.

**Nota de implementación (no forma parte del config.json, pero afecta el
comportamiento):** cada componente del circuito sigue codificándose como el
índice de una lista comercial (E12 para resistencias, E6 para
capacitores), igual que en el AG. PSO mueve esos índices en un espacio
continuo y los redondea al entero más cercano solo al momento de evaluar el
circuito; la velocidad máxima por componente está fijada internamente en
el script como 20 % del rango de su lista comercial, para evitar que una
partícula salte fuera del espacio de búsqueda en un solo paso. Este 20 %
no es configurable desde el config.json en la versión actual.

---

## 7. frecuencias — varía según tipo de filtro y modo

Esta es la única sección cuyo **esquema cambia** según (a) qué tipo de
filtro se está configurando y (b) el valor de modo. Las claves se buscan
por nombre, así que una clave de más no rompe nada, pero una clave faltante
sí provoca un error.

### 7.1 Tabla resumen

| Filtro | modo: BASICO (claves) | Orden exigido | modo: AVANZADO (claves) | Orden exigido |
|---|---|---|---|---|
| **PASABAJAS** | fc_objetivo | — (única frecuencia) | f_paso, f_aten | f_paso < f_aten |
| **PASAALTAS** | fc_objetivo | — (única frecuencia) | f_aten, f_paso | f_aten < f_paso (orden **invertido** vs. pasabajas) |
| **PASABANDA** | fc_inferior, fc_superior | fc_inferior < fc_superior | f_aten_1, f_paso_1, f_paso_2, f_aten_2 | f_aten_1 < f_paso_1 ≤ f_paso_2 < f_aten_2 |
| **RECHAZABANDA** | fc_inferior, fc_superior | fc_inferior < fc_superior | f_aten_1, f_paso_1, f_paso_2, f_aten_2 | f_paso_1 < f_aten_1 ≤ f_aten_2 < f_paso_2 |

**Importante:** PASABANDA y RECHAZABANDA en modo AVANZADO usan **las
mismas 4 claves** (f_aten_1, f_paso_1, f_paso_2, f_aten_2), pero con
**un orden numérico distinto e inverso entre sí**. Si la API comparte código
de validación entre ambos filtros, debe parametrizar el orden esperado por
tipo de filtro — copiar y pegar la validación de uno al otro produce
configuraciones aceptadas que no tienen sentido físico (p. ej. una "banda
de rechazo" mal ubicada).

Además del orden entre sí, cada combinación de filtro+modo tiene que
cumplir el margen mínimo de una década respecto al barrido (sección 5.2):
la clave más baja del conjunto debe ser ≥ f_inicial × 10, y la más alta
≤ f_final / 10. El detalle por filtro está en las subsecciones 7.2 a 7.5.

### 7.2 PASABAJAS

```json
// modo BASICO
"frecuencias": [ { "clave": "fc_objetivo", "valor": 5000 } ]

// modo AVANZADO
"frecuencias": [
  { "clave": "f_paso", "valor": 500 },
  { "clave": "f_aten", "valor": 10000 }
]
```
En modo BASICO, fc_objetivo es a la vez la frecuencia más baja y la más
alta del conjunto, así que debe cumplir ambos extremos del margen:
fc_objetivo ≥ f_inicial × 10 y fc_objetivo ≤ f_final / 10.

En modo AVANZADO, f_paso = frecuencia donde se espera amplitud máxima
(banda de paso, baja frecuencia) y f_aten = frecuencia donde se espera
amplitud ≈ 0 (banda de atenuación, alta frecuencia). Regla: **f_paso <
f_aten**, con f_paso ≥ f_inicial × 10 y f_aten ≤ f_final / 10.

### 7.3 PASAALTAS

```json
// modo BASICO
"frecuencias": [ { "clave": "fc_objetivo", "valor": 2000 } ]

// modo AVANZADO
"frecuencias": [
  { "clave": "f_aten", "valor": 1000 },
  { "clave": "f_paso", "valor": 10000 }
]
```
En modo BASICO, fc_objetivo debe cumplir igualmente
fc_objetivo ≥ f_inicial × 10 y fc_objetivo ≤ f_final / 10.

En modo AVANZADO es el espejo del pasabajas: aquí la banda de paso está
en **alta** frecuencia. Regla: **f_aten < f_paso** (orden invertido
respecto al pasabajas), con f_aten ≥ f_inicial × 10 y f_paso ≤ f_final / 10.

### 7.4 PASABANDA

```json
// modo BASICO
"frecuencias": [
  { "clave": "fc_inferior", "valor": 1000 },
  { "clave": "fc_superior", "valor": 8000 }
]

// modo AVANZADO
"frecuencias": [
  { "clave": "f_aten_1", "valor": 10 },
  { "clave": "f_paso_1", "valor": 100 },
  { "clave": "f_paso_2", "valor": 1000 },
  { "clave": "f_aten_2", "valor": 10000 }
]
```
En modo BASICO: fc_inferior ≥ f_inicial × 10, fc_superior ≤ f_final / 10,
además de fc_inferior < fc_superior.

En modo AVANZADO, de menor a mayor frecuencia: atenuación inferior →
inicio de paso → fin de paso → atenuación superior. Regla: **f_aten_1 <
f_paso_1 ≤ f_paso_2 < f_aten_2**, con f_aten_1 ≥ f_inicial × 10 y
f_aten_2 ≤ f_final / 10.

La comparación entre f_paso_1 y f_paso_2 **no es estricta**: puede
haber casos donde la banda de paso se reduzca a un solo punto (un único
pico de paso) en vez de un rango, por lo que f_paso_1 == f_paso_2 es
válido. Las fronteras con la banda de atenuación (f_aten_1 < f_paso_1 y
f_paso_2 < f_aten_2) sí son frecuencias de corte y deben seguir siendo
**estrictas**.

### 7.5 RECHAZABANDA

```json
// modo BASICO
"frecuencias": [
  { "clave": "fc_inferior", "valor": 200 },
  { "clave": "fc_superior", "valor": 800 }
]

// modo AVANZADO
"frecuencias": [
  { "clave": "f_paso_1", "valor": 10 },
  { "clave": "f_aten_1", "valor": 100 },
  { "clave": "f_aten_2", "valor": 500 },
  { "clave": "f_paso_2", "valor": 10000 }
]
```
En modo BASICO: igual que pasabanda, fc_inferior ≥ f_inicial × 10,
fc_superior ≤ f_final / 10, además de fc_inferior < fc_superior.

En modo AVANZADO, aquí la atenuación (la "muesca") queda en el **centro**
y el paso en los extremos — orden invertido respecto al pasabanda. Regla:
**f_paso_1 < f_aten_1 ≤ f_aten_2 < f_paso_2**, con f_paso_1 ≥ f_inicial × 10
y f_paso_2 ≤ f_final / 10.

La comparación entre f_aten_1 y f_aten_2 **no es estricta**: puede
haber casos donde la banda de rechazo se reduzca a un solo punto (una
muesca puntual) en vez de un rango, por lo que f_aten_1 == f_aten_2 es
válido. Las fronteras con la banda de paso (f_paso_1 < f_aten_1 y
f_aten_2 < f_paso_2) sí son frecuencias de corte y deben seguir siendo
**estrictas**.

### 7.6 La regla de "frecuencia redonda" también aplica aquí

Los config.json de ejemplo del proyecto muestran que **todas** las
frecuencias de esta sección —no solo f_inicial/f_final— ya siguen la
convención de un solo dígito significativo seguido de ceros (10, 100, 500,
1000, 10000, etc.). Se recomienda aplicar la misma regla de la sección 5.1
a fc_objetivo, fc_inferior, fc_superior, f_paso, f_aten,
f_paso_1, f_aten_1, f_paso_2 y f_aten_2.

---

## 8. Qué necesita validación simple y qué necesita lógica adicional

Conviene distinguir dos niveles de validación al implementar esto en la API:

**Validación de forma** (tipo de dato, presencia de la clave, enumeraciones,
mínimos/máximos fijos): todo lo descrito en las secciones 3 a 6 — modo,
entorno, barrido_ac, y las claves esperadas en parametros_optimizador
— se puede comprobar con las herramientas de validación de esquemas que ya
use el equipo. No depende de qué tipo de filtro sea ni de qué algoritmo de
optimización se vaya a usar.

**Validación relacional** (comparar dos o más valores entre sí): esto no se
reduce a un tipo o un rango por campo, así que necesita lógica propia en la
API:
- El orden entre las frecuencias de la sección 7 (varía por tipo de filtro
  y por modo; ver tabla 7.1). En PASABANDA y RECHAZABANDA modo
  AVANZADO, la comparación interna entre las dos frecuencias de la misma
  banda (f_paso_1/f_paso_2 en pasabanda, f_aten_1/f_aten_2 en
  rechazabanda) es de **menor o igual** (≤), no estricta, porque esa
  banda puede colapsar a un solo punto; las fronteras entre banda de paso y
  banda de atenuación, al ser frecuencias de corte, siguen siendo
  estrictas (<).
- El margen mínimo de una década entre las frecuencias de interés y
  f_inicial/f_final (sección 5.2).
- Que r_fuente/r_carga pertenezcan a la serie E12 (fórmula en la
  sección 4.2).
- Que f_inicial < f_final y, si el algoritmo es el AG, que
  elitismo < tam_poblacion (regla específica del AG; PSO no tiene un
  par de claves equivalente).

Esta segunda capa conviene parametrizarla por tipo de filtro y, en el caso
de parametros_optimizador, por el algoritmo de optimización seleccionado
— en vez de escribirla una vez y reutilizarla tal cual para los 4 filtros
(ver la advertencia de la sección 7.1).

---

## 9. Tabla resumen (cheat-sheet)

| Campo | Tipo | Obligatorio | Dominio / regla | Origen de la regla |
|---|---|---|---|---|
| modo | string | sí | "BASICO" \| "AVANZADO" (enum estricto) | contrato de API (el script no valida el enum) |
| entorno.v_fuente | number | sí | > 0; recomendado ≤ 10 | >0 obligatorio; ≤10 recomendación adoptada |
| entorno.r_fuente | number | sí | > 0; serie E12 | >0 sentido físico; E12 solicitado |
| entorno.r_carga | number | sí | > 0; serie E12 | igual que r_fuente |
| barrido_ac.f_inicial | integer | sí | > 0; < f_final; recomendado 1 dígito sig. × 10ⁿ | contrato API; redondeo recomendado |
| barrido_ac.f_final | integer | sí | ≤ 10 000 000; > f_inicial; recomendado 1 dígito sig. × 10ⁿ | contrato API; redondeo recomendado |
| parametros_optimizador.tam_poblacion *(Algoritmo Genético)* | integer | sí | ≥ 1 (obligatorio); ideal 20-50 | algoritmo + recomendación |
| parametros_optimizador.num_generaciones *(Algoritmo Genético)* | integer | sí | ≥ 1 (obligatorio); ideal 30-50 | algoritmo + recomendación |
| parametros_optimizador.prob_cruce *(Algoritmo Genético)* | number | sí | [0, 1]; ideal 0.7-0.9 | dominio matemático de una probabilidad |
| parametros_optimizador.prob_mutacion *(Algoritmo Genético)* | number | sí | [0, 1]; ideal 0.2-0.35 | dominio matemático + recomendación |
| parametros_optimizador.elitismo *(Algoritmo Genético)* | integer | sí | 0 ≤ elitismo < tam_poblacion; ideal 2-4 | algoritmo (si no, deja de evolucionar) |
| parametros_optimizador.torneo_k *(Algoritmo Genético)* | integer | sí | ≥ 1 (obligatorio); ideal 2-5 | algoritmo |
| parametros_optimizador.num_particulas *(PSO)* | integer | sí | ≥ 1 (obligatorio); ideal 20-40 | algoritmo + recomendación |
| parametros_optimizador.num_iteraciones *(PSO)* | integer | sí | ≥ 0 (no bloqueante en 0, a diferencia del AG); ideal 30-50 | algoritmo + recomendación |
| parametros_optimizador.w *(PSO)* | number | sí | sin tope validado por el script; ideal 0.4-0.9 | recomendación (>1 puede diverger) |
| parametros_optimizador.c1 *(PSO)* | number | sí | sin tope validado por el script; ideal 1.0-2.0 | recomendación |
| parametros_optimizador.c2 *(PSO)* | number | sí | sin tope validado por el script; ideal 1.0-2.0, c1≈c2 | recomendación |
| frecuencias.* | number | depende de tipo+modo (sección 7) | margen mínimo de una década respecto a f_inicial/f_final; orden según tabla 7.1; recomendado 1 dígito sig. × 10ⁿ | claves obligatorias + recomendación (rango/orden/redondeo) |

---

## 10. Recomendaciones adicionales para el diseño de la API

1. **No reenviar claves desconocidas** al config.json final (p. ej. el
   campo de enrutamiento de tipo de filtro o de algoritmo): el script las
   ignora sin avisar, pero ensucia el contrato.
2. **Validar todo en la capa de API antes de invocar el script** y traducir
   cada regla violada a un error con mensaje específico (campo + regla +
   valor recibido). Dejar que el script truene equivale a un error opaco
   para el usuario final.
3. Las rutas y nombres de archivo que usa cada script (ejecutable de
   simulación, archivos intermedios, etc.) hoy están fijos en el código con
   una ruta local de desarrollo; tendrán que parametrizarse para correr en
   el servidor de la API.
4. El resultado que produce cada script incluye la gráfica final
   codificada en base64 — útil para que la API lo devuelva directo al
   cliente sin tocar el sistema de archivos, pero no es el objeto de este
   documento (que cubre solo la entrada).
