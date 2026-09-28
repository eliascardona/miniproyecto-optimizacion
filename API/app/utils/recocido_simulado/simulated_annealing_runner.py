"""
Motor genérico de Recocido Simulado (Simulated Annealing).

Igual que los otros tres runners (genetic_algorithm_runner,
particle_swarm_runner, bayesian_runner), esto es "los detalles de
optimización" separados de la preparación: no sabe qué filtro se está
optimizando, ni cómo se simula un circuito. Trabaja sobre la misma
codificación que AG/PSO/BO (individuo = lista de índices en una serie de
valores comerciales), pero recorre el espacio con un único estado que se
mueve a un vecino en cada paso, aceptando siempre las mejoras y aceptando
empeoramientos con una probabilidad que decae con la temperatura (criterio
de Metrópolis, adaptado a MAXIMIZACIÓN: delta_fit > 0 siempre se acepta;
si no, se acepta con probabilidad exp(delta_fit / temperatura), que cae
mientras más negativo sea delta_fit o más baja esté la temperatura).

Reutiliza crear_individuo del AG (utils.genetico.genetic_operators) para
el estado inicial: es exactamente la misma "crear_solucion_inicial" del
código fuente original.

Diferencia deliberada frente al código fuente original: aquí se valida
que 0 < factor_enfriamiento < 1 y que temp_inicial > temp_final > 0 antes
de arrancar. El bucle `while temperatura > temp_final` del script
original no tiene ninguna garantía de terminar si factor_enfriamiento
fuera >= 1 (la temperatura nunca bajaría) -- en un script eso se
interrumpe a mano; corriendo dentro de un worker de API eso colgaría esa
request para siempre. Se prefiere fallar rápido con un ValueError claro.
"""
import math
import random
from typing import Callable, Optional

from app.utils.genetico.genetic_operators import crear_individuo
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12

EvaluarIndividuo = Callable[[list[int]], tuple]
LogEncabezado = Callable[[dict, list[dict]], None]
LogGeneracion = Callable[[int, float, tuple, str], None]


def ejecutar_recocido_simulado(
    componentes_ag: list[dict],
    ctx: dict,
    evaluar_individuo: EvaluarIndividuo,
    log_encabezado: Optional[LogEncabezado] = None,
    log_generacion: Optional[LogGeneracion] = None,
) -> tuple[list[int], float]:
    """
    Corre el recocido simulado completo y devuelve
    (mejor_individuo, mejor_fitness).

    `ctx` debe traer al menos: temp_inicial, temp_final,
    factor_enfriamiento, iteraciones_por_temp, modo (este último solo se
    reenvía tal cual a log_generacion, no se interpreta aquí).

    `evaluar_individuo(individuo) -> tuple` es la función de fitness ya
    resuelta por el llamador; esta función SIEMPRE espera que el primer
    elemento de esa tupla sea el fitness (float).

    log_generacion se llama UNA VEZ POR CICLO DE ENFRIAMIENTO (no una vez
    por cada una de las iteraciones_por_temp iteraciones internas),
    igual que el print original ("Ciclo N | Temp: ... | Mejor Fit: ...").
    """
    temp_inicial = ctx["temp_inicial"]
    temp_final = ctx["temp_final"]
    factor_enfriamiento = ctx["factor_enfriamiento"]
    iteraciones_por_temp = ctx["iteraciones_por_temp"]
    num_parametros = len(componentes_ag)

    if not (0.0 < factor_enfriamiento < 1.0):
        raise ValueError(
            "factor_enfriamiento debe estar estrictamente entre 0 y 1 para que la "
            f"temperatura baje y el recocido termine; recibido: {factor_enfriamiento}."
        )
    if temp_final <= 0:
        raise ValueError(f"temp_final debe ser mayor a 0; recibido: {temp_final}.")
    if temp_inicial <= temp_final:
        raise ValueError(
            f"temp_inicial ({temp_inicial}) debe ser mayor que temp_final ({temp_final})."
        )

    limites = [(len(SERIE_E12) if c["tipo"] == "R" else len(SERIE_E6)) - 1 for c in componentes_ag]

    def generar_vecino(estado_actual: list[int]) -> list[int]:
        """Muta entre 1 y num_parametros//3 genes (mínimo 1), cada uno con
        un salto discreto de -2/-1/+1/+2 posiciones dentro de su serie
        comercial, recortado a los límites -- misma regla que el AG usa
        para mutar, pero aplicada a un solo estado en vez de a toda una
        población."""
        vecino = estado_actual[:]
        num_mutaciones = random.randint(1, max(1, num_parametros // 3))
        indices_a_mutar = random.sample(range(num_parametros), num_mutaciones)
        for i in indices_a_mutar:
            salto = random.choice([-2, -1, 1, 2])
            vecino[i] = max(0, min(limites[i], vecino[i] + salto))
        return vecino

    # Caché de fitness: evita volver a correr SPICE para un individuo ya
    # evaluado antes (misma idea que en AG/PSO/BO; el script original de
    # RS no la traía, pero es una optimización pura sin ningún efecto en
    # el resultado -- solo evita recomputar algo ya conocido).
    cache_fitness: dict[tuple, tuple] = {}

    def evaluar_con_cache(individuo: list[int]) -> tuple:
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = evaluar_individuo(individuo)
        return cache_fitness[clave]

    if log_encabezado:
        log_encabezado(ctx, componentes_ag)

    estado_actual = crear_individuo(componentes_ag)
    res_actual = evaluar_con_cache(estado_actual)
    fit_actual = res_actual[0]

    mejor_estado = estado_actual[:]
    mejor_fit = fit_actual
    mejor_res = res_actual

    temperatura = temp_inicial
    ciclo = 0

    while temperatura > temp_final:
        for _ in range(iteraciones_por_temp):
            vecino = generar_vecino(estado_actual)
            res_vecino = evaluar_con_cache(vecino)
            fit_vecino = res_vecino[0]
            delta_fit = fit_vecino - fit_actual

            if delta_fit > 0:
                estado_actual, fit_actual, res_actual = vecino[:], fit_vecino, res_vecino
                if fit_actual > mejor_fit:
                    mejor_estado, mejor_fit, mejor_res = estado_actual[:], fit_actual, res_actual
            else:
                if random.random() < math.exp(delta_fit / temperatura):
                    estado_actual, fit_actual, res_actual = vecino[:], fit_vecino, res_vecino

        if log_generacion:
            log_generacion(ciclo, mejor_fit, mejor_res, ctx["modo"])

        temperatura *= factor_enfriamiento
        ciclo += 1

    return mejor_estado, mejor_fit