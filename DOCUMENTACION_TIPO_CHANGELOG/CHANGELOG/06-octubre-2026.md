## Fase 0 y 1 -- aislamiento de las corridas del optimizador y esquema del circuito a partir del .cir

**Por qué.** Para dibujar en el frontend los 4 filtros activos (Sallen-Key y Twin-T) hacía falta que el backend entregara la
topología del circuito, y la fuente natural son los `.cir` de `constants_repository`. Al preparar eso se encontraron cuatro
problemas en cómo el backend usa esos mismos archivos y en la generación de la gráfica; se corrigieron primero (fase 0).

**Fase 0 -- correcciones del backend**

1. *`constants_repository` ya no se escribe.* Antes, `actualizar_circuito()` reescribía el `filtro.cir` de la carpeta del filtro
   en cada evaluación (dejándolo con los valores del último individuo y el entorno de la última petición) y dos peticiones
   simultáneas sobre el mismo filtro se pisaban. Ahora esa carpeta es una PLANTILLA de solo lectura: cada
   `ConstantsRepository(filtro)` crea un directorio temporal propio, copia ahí el `.cir` y la librería, y expone esas rutas.
   `IndividualOptimizationController.optimize()` lo borra siempre al terminar (`finally`); `weakref.finalize` es la red de seguridad.
2. *ngspice se ejecuta con el directorio de la corrida como `cwd`.* El `.cir` pide `wrdata datos_filtro.txt` y
   `write simulacion.raw` con rutas relativas, y ngspice las resuelve contra el cwd del PROCESO. Sin `cwd=`, esos archivos caían
   en la carpeta desde la que se arranca uvicorn (de ahí los `datos_filtro.txt`, `simulacion.raw` y `resultado.json` sueltos en
   `API/`) mientras el fitness leía el `datos_filtro.txt` de la carpeta del filtro, que nadie actualizaba. Si esto ocurría en tu
   entorno, el fitness veía la misma curva para todos los individuos. Con un ngspice simulado se reproduce exactamente ese
   síntoma con el código anterior y desaparece con el nuevo.
3. *Las gráficas ya no usan `pyplot` y se generan de a una.* Los 5 `result_exporter` usan `matplotlib.figure.Figure` (sin estado
   global ni figuras que se acumulan) y `@serializado` (`app/utils/matplotlib_seguro.py`) los ejecuta de uno en uno dentro del
   proceso: matplotlib no es seguro para hilos y, con el código anterior, 5 a 8 de 8 hilos que dibujaban a la vez fallaban con
   `ValueError: Unknown symbol: \mathdefault`, o sea un 500 al final de una optimización completa.
4. *Una sola raíz de importación.* `main.py` y el router importaban `API.app...` y el resto del backend `app...`; con el cwd de
   `run-fast-api.ps1` el arranque fallaba (`No module named 'API'`). Ahora todo usa `app...`.

**Fase 1 -- esquema del circuito (`app/utils/esquema/`)**

Convierte un `.cir` en un ESQUEMA: el circuito descrito con datos (elementos con su ruta en coordenadas de rejilla, op-amps,
cables, tierras, puntos de unión y límites), de modo que el cliente solo tenga que pintarlo.

- `netlist.py` lee R/C/L, fuentes y op-amps (LM741), el título y el nodo observado (`vm(...)`).
- `etapas.py` reconoce la estructura: cada op-amp cierra una etapa; dentro de ella hay elementos en serie (1 o 2 ramas
  paralelas), derivaciones a tierra y realimentación a la salida del op-amp. Lo que no encaja se rechaza con
  `TopologiaNoSoportada` y un mensaje claro (op-amp que no es seguidor, 3 ramas paralelas, elementos huérfanos, carga ambigua...).
- `layout.py` calcula la geometría; `validacion.py` comprueba cobertura exacta, ausencia de símbolos encimados y que cada ruta
  empiece y termine en sus nodos; `servicio.py` expone `obtener_esquema(filtro, valores=None)` con caché del layout.
- Los 4 filtros reales y la escalera LC del frontend legacy se dibujan con el mismo código.
- `tools/dibujar_esquema.py` dibuja un esquema usando SOLO su JSON (herramienta de desarrollo; la fase 3 hará lo mismo en Java).

**Todavía NO incluido (fase 2):** el esquema no se agrega aún a la respuesta de `/api/optimizar` ni hay endpoint para consultarlo.

**Cómo probar** (desde `API/`): `python -m unittest discover -s tests -t . -v`. Son 61 pruebas, sin dependencias nuevas. No
necesitan ngspice: `tests/_ngspice_falso.py` lo simula (respeta que las rutas relativas se resuelven contra el cwd).
Para ver los esquemas: `python -m tools.dibujar_esquema -o esquemas.png`.

**Limpieza recomendada tras aplicar el cambio**: borrar `API/datos_filtro.txt`, `API/simulacion.raw` y `API/resultado.json`, y los
`datos_filtro.txt` y `resultado_filtro.png` de cada carpeta de `constants_repository/` (ya no se usan). Los `filtro.cir` de la
plantilla conservan valores de pruebas anteriores (Vs, Rs, Rl, barrido, componentes): conviene dejarlos en los valores base que
se quieran mostrar por defecto.

```
    Fecha de cambio:    5 de octubre de 2026
    Tipo de cambio:     Correctivo / Mejora
    Asunto del cambio:  "AISLAMIENTO DE CORRIDAS (ngspice, .cir, GRAFICAS) Y ESQUEMA DE CIRCUITO DESDE EL .cir"
```