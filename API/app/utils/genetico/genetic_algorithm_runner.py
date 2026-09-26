"""
Motor genérico del algoritmo genético.

Esto es "los detalles de optimización" separados de la preparación
(GeneticPreparationService): no sabe qué filtro se está optimizando, ni
cómo se simula un circuito, ni qué significa cada gen. Solo orquesta
población / generaciones / elitismo / selección / cruce / mutación sobre
listas de índices enteros, delegando la evaluación de cada individuo a
`evaluar_individuo`, una función inyectada por quien llama.

Puede reutilizarse tal cual para cualquier filtro (pasa_altas, pasa_bajas,
pasa_banda, rechaza_banda) e incluso, en el futuro, para otro tipo de
optimización que use esta misma codificación (individuo = lista de índices
en una serie de valores comerciales).
"""
from typing import Callable, Optional

import numpy as np

from app.utils.genetico.genetic_operators import (
    crear_individuo,
    seleccion_torneo,
    cruzar,
    mutar,
)

EvaluarIndividuo = Callable[[list[int]], tuple]
LogEncabezado = Callable[[dict, list[dict]], None]
LogGeneracion = Callable[[int, float, tuple, str], None]


def ejecutar_algoritmo_genetico(
    componentes_ag: list[dict],
    ctx: dict,
    evaluar_individuo: EvaluarIndividuo,
    log_encabezado: Optional[LogEncabezado] = None,
    log_generacion: Optional[LogGeneracion] = None,
) -> tuple[list[int], float]:
    """
    Corre el AG completo y devuelve (mejor_individuo, mejor_fitness).

    `ctx` debe traer al menos: tam_poblacion, num_generaciones, elitismo,
    torneo_k, prob_cruce, prob_mutacion, modo (este último solo se reenvía
    tal cual a log_generacion, no se interpreta aquí).

    `evaluar_individuo(individuo) -> tuple` es la función de fitness ya
    resuelta por el llamador (con el circuito, modo y objetivos que
    correspondan); esta función SIEMPRE espera que el primer elemento de
    esa tupla sea el fitness (float).
    """
    tam_poblacion = ctx["tam_poblacion"]
    num_generaciones = ctx["num_generaciones"]
    num_parametros = len(componentes_ag)

    poblacion = [crear_individuo(componentes_ag) for _ in range(tam_poblacion)]
    mejor_global: list[int] | None = None
    mejor_fit = -1.0
    cache_fitness: dict[tuple, tuple] = {}

    def evaluar_con_cache(individuo: list[int]) -> tuple:
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = evaluar_individuo(individuo)
        return cache_fitness[clave]

    if log_encabezado:
        log_encabezado(ctx, componentes_ag)

    for gen in range(num_generaciones):
        resultados = [evaluar_con_cache(ind) for ind in poblacion]
        fitnesses = [r[0] for r in resultados]

        idx_best = int(np.argmax(fitnesses))
        if fitnesses[idx_best] > mejor_fit:
            mejor_fit = fitnesses[idx_best]
            mejor_global = poblacion[idx_best][:]

        if log_generacion:
            log_generacion(gen, fitnesses[idx_best], resultados[idx_best], ctx["modo"])

        # Elitismo + nueva generación
        indices_ordenados = np.argsort(fitnesses)[::-1]
        nueva_pob = [poblacion[i][:] for i in indices_ordenados[: ctx["elitismo"]]]

        while len(nueva_pob) < tam_poblacion:
            p1 = seleccion_torneo(poblacion, fitnesses, ctx["torneo_k"])
            p2 = seleccion_torneo(poblacion, fitnesses, ctx["torneo_k"])
            h1, h2 = cruzar(p1, p2, ctx["prob_cruce"], num_parametros)
            mutar(h1, componentes_ag, ctx["prob_mutacion"])
            nueva_pob.append(h1)
            if len(nueva_pob) < tam_poblacion:
                mutar(h2, componentes_ag, ctx["prob_mutacion"])
                nueva_pob.append(h2)

        poblacion = nueva_pob

    return mejor_global, mejor_fit