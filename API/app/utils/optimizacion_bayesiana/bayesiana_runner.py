"""
Motor genérico de Optimización Bayesiana (proceso gaussiano + Expected
Improvement).

Igual que utils.genetico.genetic_algorithm_runner y utils.
enjambre_particulas.particle_swarm_runner, esto es "los detalles de
optimización" separados de la preparación: no sabe qué filtro se está
optimizando, ni cómo se simula un circuito. Trabaja sobre la misma
codificación que AG/PSO (individuo = lista de índices en una serie de
valores comerciales), moviéndose en el continuo (como PSO) pero
proponiendo el siguiente punto a evaluar maximizando Expected Improvement
sobre un proceso gaussiano ajustado a las observaciones previas, en vez
de por una regla de movimiento fija.

Concurrencia: el script original del equipo de algoritmos sembraba el
generador aleatorio GLOBAL del proceso (random.seed(SEMILLA)) porque se
ejecutaba como script de una sola corrida. Aquí eso mutaría el estado
aleatorio de TODO el proceso de la API mientras corre, interfiriendo con
cualquier otra optimización (AG/PSO/BO) que esté corriendo al mismo
tiempo en el mismo proceso. Por eso este runner usa un random.Random(semilla)
local, con el mismo efecto de reproducibilidad pero sin tocar estado
global. GaussianProcessRegressor ya recibe su propio random_state, así
que ese no tiene el mismo problema.
"""
import random
from typing import Callable, Optional

import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel

from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12

EvaluarIndividuo = Callable[[list[int]], tuple]
LogEncabezado = Callable[[dict, list[dict]], None]
LogGeneracion = Callable[[int, float, tuple, str], None]


def ejecutar_bo(
    componentes_ag: list[dict],
    ctx: dict,
    evaluar_individuo: EvaluarIndividuo,
    log_encabezado: Optional[LogEncabezado] = None,
    log_generacion: Optional[LogGeneracion] = None,
) -> tuple[list[int], float]:
    """
    Corre la BO completa y devuelve (mejor_individuo, mejor_fitness).

    `ctx` debe traer al menos: n_iniciales, n_iteraciones, xi,
    n_candidatos, n_restarts, semilla, modo (este último solo se reenvía
    tal cual a log_generacion, no se interpreta aquí).

    `evaluar_individuo(individuo) -> tuple` es la función de fitness ya
    resuelta por el llamador; esta función SIEMPRE espera que el primer
    elemento de esa tupla sea el fitness (float).
    """
    n_iniciales = ctx["n_iniciales"]
    n_iteraciones = ctx["n_iteraciones"]
    xi = ctx["xi"]
    n_candidatos = ctx["n_candidatos"]
    n_restarts = ctx["n_restarts"]
    semilla = ctx["semilla"]
    num_parametros = len(componentes_ag)

    limites = [(len(SERIE_E12) if c["tipo"] == "R" else len(SERIE_E6)) - 1 for c in componentes_ag]
    bounds = np.array([[0.0, float(lim)] for lim in limites])

    # Generador local, no global (ver docstring del módulo).
    rnd = random.Random(semilla)

    def redondear_individuo(posicion: np.ndarray) -> list[int]:
        """Convierte un punto continuo de la BO al índice entero
        (discreto) de la serie comercial correspondiente, recortando a
        los límites -- misma idea que en PSO."""
        return [int(round(min(max(p, 0.0), limites[i]))) for i, p in enumerate(posicion)]

    def punto_aleatorio() -> np.ndarray:
        return np.array([rnd.uniform(0, limites[i]) for i in range(num_parametros)])

    def construir_gp() -> GaussianProcessRegressor:
        """Kernel Matern (nu=2.5) anisotrópico + ruido blanco, uno por
        cada dimensión (un R o C a optimizar). El Matern generaliza al
        RBF y se comporta mejor con superficies de fitness no
        perfectamente suaves."""
        kernel = (
            ConstantKernel(1.0, (1e-3, 1e3))
            * Matern(length_scale=[1.0] * num_parametros, length_scale_bounds=(1e-2, 1e3), nu=2.5)
            + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-8, 1e2))
        )
        return GaussianProcessRegressor(
            kernel=kernel, normalize_y=True, n_restarts_optimizer=5, random_state=semilla
        )

    def expected_improvement(X: np.ndarray, gp: GaussianProcessRegressor, y_mejor: float) -> np.ndarray:
        """EI para MAXIMIZACIÓN (el fitness de este proyecto es 0..1, más
        alto = mejor, al revés que un error a minimizar)."""
        mu, sigma = gp.predict(X, return_std=True)
        sigma = np.maximum(sigma, 1e-9)
        mejora = mu - y_mejor - xi
        z = mejora / sigma
        return mejora * norm.cdf(z) + sigma * norm.pdf(z)

    def proponer_siguiente_punto(gp: GaussianProcessRegressor, y_mejor: float) -> np.ndarray:
        """Maximiza EI: muestreo aleatorio grueso sobre bounds +
        refinamiento local con L-BFGS-B desde los mejores candidatos."""
        candidatos = np.array([punto_aleatorio() for _ in range(n_candidatos)])
        ei_candidatos = expected_improvement(candidatos, gp, y_mejor)
        mejores_idx = np.argsort(ei_candidatos)[::-1][:n_restarts]

        mejor_x, mejor_ei = None, -np.inf
        for idx in mejores_idx:
            x0 = candidatos[idx]

            def neg_ei(x):
                return -expected_improvement(x.reshape(1, -1), gp, y_mejor)[0]

            res = minimize(neg_ei, x0, method="L-BFGS-B", bounds=bounds)
            if res.success and (-res.fun) > mejor_ei:
                mejor_ei = -res.fun
                mejor_x = res.x

        if mejor_x is None:
            mejor_x = candidatos[mejores_idx[0]]
        return np.clip(mejor_x, bounds[:, 0], bounds[:, 1])

    # Caché de fitness: evita volver a correr SPICE para un individuo ya
    # evaluado antes (misma idea que en AG/PSO).
    cache_fitness: dict[tuple, tuple] = {}

    def evaluar_con_cache(individuo: list[int]) -> tuple:
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = evaluar_individuo(individuo)
        return cache_fitness[clave]

    if log_encabezado:
        log_encabezado(ctx, componentes_ag)

    # --- Fase 1: muestreo inicial aleatorio uniforme ---
    X_obs, y_obs, res_obs = [], [], []
    for _ in range(n_iniciales):
        x = punto_aleatorio()
        individuo = redondear_individuo(x)
        res = evaluar_con_cache(individuo)
        X_obs.append(x)
        y_obs.append(res[0])
        res_obs.append(res)

    X_obs = np.array(X_obs)
    y_obs = np.array(y_obs)

    idx_best = int(np.argmax(y_obs))
    mejor_global = redondear_individuo(X_obs[idx_best])
    mejor_fit = float(y_obs[idx_best])
    mejor_res = res_obs[idx_best]

    if log_generacion:
        log_generacion(-1, mejor_fit, mejor_res, ctx["modo"])

    # --- Fase 2: iteraciones bayesianas (GP + Expected Improvement) ---
    for it in range(n_iteraciones):
        gp = construir_gp()
        gp.fit(X_obs, y_obs)

        x_next = proponer_siguiente_punto(gp, mejor_fit)
        individuo = redondear_individuo(x_next)
        res = evaluar_con_cache(individuo)
        fit = res[0]

        X_obs = np.vstack([X_obs, x_next])
        y_obs = np.append(y_obs, fit)

        if fit > mejor_fit:
            mejor_fit = fit
            mejor_global = individuo[:]
            mejor_res = res

        if log_generacion:
            log_generacion(it, mejor_fit, mejor_res, ctx["modo"])

    return mejor_global, mejor_fit