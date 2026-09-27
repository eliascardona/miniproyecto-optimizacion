"""
Motor genérico de optimización por Enjambre de Partículas (PSO).

Igual que utils.genetico.genetic_algorithm_runner, esto es "los detalles
de optimización" separados de la preparación: no sabe qué filtro se está
optimizando, ni cómo se simula un circuito. Solo orquesta el ciclo de PSO
(posiciones continuas + velocidad, pbest/gbest) sobre la misma
codificación que ya usa el AG (individuo = lista de índices en una serie
de valores comerciales), delegando la evaluación de cada partícula a
`evaluar_individuo`, una función inyectada por quien llama.

Reutiliza crear_individuo del AG (utils.genetico.genetic_operators) para
las posiciones iniciales: la codificación del "espacio de búsqueda" es la
misma para ambos algoritmos, solo cambia cómo se recorre ese espacio.
"""
import random
from typing import Callable, Optional

import numpy as np

from app.utils.genetico.genetic_operators import crear_individuo
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12

EvaluarIndividuo = Callable[[list[int]], tuple]
LogEncabezado = Callable[[dict, list[dict]], None]
LogGeneracion = Callable[[int, float, tuple, str], None]


def ejecutar_pso(
    componentes_ag: list[dict],
    ctx: dict,
    evaluar_individuo: EvaluarIndividuo,
    log_encabezado: Optional[LogEncabezado] = None,
    log_generacion: Optional[LogGeneracion] = None,
) -> tuple[list[int], float]:
    """
    Corre el PSO completo y devuelve (mejor_individuo, mejor_fitness).

    `ctx` debe traer al menos: num_particulas, num_iteraciones, w, c1, c2,
    modo (este último solo se reenvía tal cual a log_generacion, no se
    interpreta aquí).

    `evaluar_individuo(individuo) -> tuple` es la función de fitness ya
    resuelta por el llamador; esta función SIEMPRE espera que el primer
    elemento de esa tupla sea el fitness (float).
    """
    num_particulas = ctx["num_particulas"]
    num_iteraciones = ctx["num_iteraciones"]
    w, c1, c2 = ctx["w"], ctx["c1"], ctx["c2"]
    num_parametros = len(componentes_ag)

    # Límite superior (índice máximo válido) de cada dimensión, según si
    # el componente es R (serie E12) o C (serie E6).
    limites = [(len(SERIE_E12) if c["tipo"] == "R" else len(SERIE_E6)) - 1 for c in componentes_ag]

    # Velocidad máxima por dimensión: acota qué tanto puede moverse una
    # partícula en un solo paso (20% del rango de esa dimensión), evitando
    # que "vuele" fuera del espacio de búsqueda de un salto.
    vmax = [0.2 * lim for lim in limites]

    def crear_velocidad() -> list[float]:
        return [random.uniform(-vmax[i], vmax[i]) for i in range(num_parametros)]

    def redondear_individuo(posicion: list[float]) -> list[int]:
        """Convierte una posición continua de PSO al índice entero
        (discreto) de la serie comercial correspondiente, recortando a
        los límites."""
        return [int(round(min(max(p, 0.0), limites[i]))) for i, p in enumerate(posicion)]

    # Posiciones iniciales: mismos índices discretos que el AG (mismo
    # crear_individuo), pero representados como flotantes porque PSO
    # necesita moverse en un espacio continuo (se redondean solo al
    # evaluar el circuito).
    posiciones = [[float(g) for g in crear_individuo(componentes_ag)] for _ in range(num_particulas)]
    velocidades = [crear_velocidad() for _ in range(num_particulas)]

    # Caché de fitness: evita volver a correr SPICE para un individuo ya
    # evaluado antes (misma idea que en el AG; aquí la clave es el
    # individuo discreto resultante de redondear la posición).
    cache_fitness: dict[tuple, tuple] = {}

    def evaluar_con_cache(individuo: list[int]) -> tuple:
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = evaluar_individuo(individuo)
        return cache_fitness[clave]

    # Mejor posición histórica de cada partícula (pbest) y su fitness.
    pbest_pos = [pos[:] for pos in posiciones]
    pbest_individuo = [redondear_individuo(pos) for pos in posiciones]
    pbest_res = [evaluar_con_cache(ind) for ind in pbest_individuo]
    pbest_fit = [r[0] for r in pbest_res]

    # Mejor posición global del enjambre (gbest).
    idx_gbest = int(np.argmax(pbest_fit))
    gbest_pos = pbest_pos[idx_gbest][:]
    gbest_individuo = pbest_individuo[idx_gbest][:]
    gbest_fit = pbest_fit[idx_gbest]
    gbest_res = pbest_res[idx_gbest]

    if log_encabezado:
        log_encabezado(ctx, componentes_ag)

    for it in range(num_iteraciones):
        for p in range(num_particulas):
            for d in range(num_parametros):
                r1, r2 = random.random(), random.random()
                # Ecuación clásica de PSO: inercia + atracción al mejor
                # personal (cognitivo) + atracción al mejor global (social).
                velocidades[p][d] = (
                    w * velocidades[p][d]
                    + c1 * r1 * (pbest_pos[p][d] - posiciones[p][d])
                    + c2 * r2 * (gbest_pos[d] - posiciones[p][d])
                )
                velocidades[p][d] = max(-vmax[d], min(vmax[d], velocidades[p][d]))

                posiciones[p][d] += velocidades[p][d]
                posiciones[p][d] = max(0.0, min(float(limites[d]), posiciones[p][d]))

            individuo = redondear_individuo(posiciones[p])
            res = evaluar_con_cache(individuo)
            fit = res[0]

            if fit > pbest_fit[p]:
                pbest_fit[p] = fit
                pbest_pos[p] = posiciones[p][:]
                pbest_individuo[p] = individuo[:]
                pbest_res[p] = res

        idx_mejor_pbest = int(np.argmax(pbest_fit))
        if pbest_fit[idx_mejor_pbest] > gbest_fit:
            gbest_fit = pbest_fit[idx_mejor_pbest]
            gbest_pos = pbest_pos[idx_mejor_pbest][:]
            gbest_individuo = pbest_individuo[idx_mejor_pbest][:]
            gbest_res = pbest_res[idx_mejor_pbest]

        if log_generacion:
            log_generacion(it, gbest_fit, gbest_res, ctx["modo"])

    return gbest_individuo, gbest_fit