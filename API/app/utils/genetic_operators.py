"""
Utilería: operadores del algoritmo genético.

Funciones puras sin estado; reciben todo lo que necesitan como argumentos.
"""
import random

from app.utils.commercial_series import SERIE_E6, SERIE_E12


# ---------------------------------------------------------------------------
# Creación de individuos
# ---------------------------------------------------------------------------

def crear_individuo(componentes_ag: list[dict]) -> list[int]:
    """Genera un individuo aleatorio respetando los límites de cada serie."""
    return [
        random.randint(
            0,
            (len(SERIE_E12) if c["tipo"] == "R" else len(SERIE_E6)) - 1,
        )
        for c in componentes_ag
    ]


# ---------------------------------------------------------------------------
# Selección
# ---------------------------------------------------------------------------

def seleccion_torneo(
    poblacion: list[list[int]],
    fitnesses: list[float],
    k: int,
) -> list[int]:
    """Torneo de tamaño k: devuelve el individuo con mejor fitness entre k candidatos aleatorios."""
    candidatos = random.sample(range(len(poblacion)), min(k, len(poblacion)))
    idx_mejor = max(candidatos, key=lambda i: fitnesses[i])
    return poblacion[idx_mejor]


# ---------------------------------------------------------------------------
# Cruce
# ---------------------------------------------------------------------------

def cruzar(
    p1: list[int],
    p2: list[int],
    prob_cruce: float,
    num_parametros: int,
) -> tuple[list[int], list[int]]:
    """Cruce de un punto con probabilidad prob_cruce; si no hay cruce, devuelve copias."""
    if num_parametros > 1 and random.random() < prob_cruce:
        punto = random.randint(1, num_parametros - 1)
        h1 = p1[:punto] + p2[punto:]
        h2 = p2[:punto] + p1[punto:]
    else:
        h1, h2 = p1[:], p2[:]
    return h1, h2


# ---------------------------------------------------------------------------
# Mutación
# ---------------------------------------------------------------------------

def mutar(
    individuo: list[int],
    componentes_ag: list[dict],
    prob_mutacion: float,
) -> list[int]:
    """Mutación gen a gen: cada gen salta a un valor aleatorio de su serie con prob_mutacion."""
    for i, comp in enumerate(componentes_ag):
        if random.random() < prob_mutacion:
            lim = len(SERIE_E12) if comp["tipo"] == "R" else len(SERIE_E6)
            individuo[i] = random.randint(0, lim - 1)
    return individuo