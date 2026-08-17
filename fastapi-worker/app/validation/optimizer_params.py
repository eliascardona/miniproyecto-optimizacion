"""
Validador de hiperparametros del algoritmo de optimizacion.

Cada algoritmo (AG o PSO) tiene un conjunto distinto de parametrizaciones
con tipos de dato y rangos validos:
  - AG: tam_poblacion, num_generaciones, prob_cruce, prob_mutacion, elitismo, torneo_k
  - PSO: num_particulas, num_iteraciones, w, c1, c2

Recibe arreglos [{clave, valor}] del request HTTP y los convierte
internamente a dicts {clave: valor} para validar.
"""

from typing import List


def _arreglo_a_dict(items: list) -> dict:
    """Convierte [{clave, valor}, ...] a {clave: valor, ...}."""
    resultado = {}
    for item in items:
        if isinstance(item, dict) and "clave" in item and "valor" in item:
            resultado[item["clave"]] = item["valor"]
    return resultado


def validar_parametros(params, algoritmo: str) -> List[str]:
    """
    Valida la presencia y rangos de los hiperparametros del algoritmo.
    Acepta tanto listas [{clave, valor}] como dicts {clave: valor}.
    """
    if isinstance(params, list):
        params = _arreglo_a_dict(params)

    if not isinstance(params, dict):
        return [f"parametros debe ser un arreglo [{'{clave, valor}'}] o un objeto"]

    if algoritmo == "AG":
        return _validar_ag(params)
    elif algoritmo == "PSO":
        return _validar_pso(params)
    return [f"Algoritmo no soportado: {algoritmo}"]


def _validar_ag(params: dict) -> List[str]:
    errores = []
    requeridas = ["tam_poblacion", "num_generaciones", "prob_cruce", "prob_mutacion", "elitismo", "torneo_k"]

    for key in requeridas:
        if key not in params:
            errores.append(f"falta '{key}' para AG")
            return errores

    tp = params["tam_poblacion"]
    ng = params["num_generaciones"]
    pc = params["prob_cruce"]
    pm = params["prob_mutacion"]
    el = params["elitismo"]
    tk = params["torneo_k"]

    if not isinstance(tp, int) or tp < 1:
        errores.append("tam_poblacion debe ser entero >= 1")
    if not isinstance(ng, int) or ng < 1:
        errores.append("num_generaciones debe ser entero >= 1")
    if not isinstance(pc, (int, float)) or pc < 0 or pc > 1:
        errores.append("prob_cruce debe ser un numero entre 0 y 1")
    if not isinstance(pm, (int, float)) or pm < 0 or pm > 1:
        errores.append("prob_mutacion debe ser un numero entre 0 y 1")
    if isinstance(el, int) and isinstance(tp, int):
        if el < 0 or el >= tp:
            errores.append("elitismo debe ser >= 0 y < tam_poblacion")
    if not isinstance(tk, int) or tk < 1:
        errores.append("torneo_k debe ser entero >= 1")

    return errores


def _validar_pso(params: dict) -> List[str]:
    errores = []
    requeridas = ["num_particulas", "num_iteraciones", "w", "c1", "c2"]

    for key in requeridas:
        if key not in params:
            errores.append(f"falta '{key}' para PSO")
            return errores

    np_ = params["num_particulas"]
    ni = params["num_iteraciones"]
    w = params["w"]
    c1 = params["c1"]
    c2 = params["c2"]

    if not isinstance(np_, int) or np_ < 1:
        errores.append("num_particulas debe ser entero >= 1")
    if not isinstance(ni, int) or ni < 0:
        errores.append("num_iteraciones debe ser entero >= 0")
    if not isinstance(w, (int, float)) or w < 0 or w > 1:
        errores.append("w debe ser un numero entre 0 y 1")
    if not isinstance(c1, (int, float)) or c1 <= 0:
        errores.append("c1 debe ser un numero mayor a 0")
    if not isinstance(c2, (int, float)) or c2 <= 0:
        errores.append("c2 debe ser un numero mayor a 0")

    return errores
