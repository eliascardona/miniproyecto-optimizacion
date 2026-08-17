"""
Servicio de validacion Nivel 2 (FastAPI Worker).

Validaciones avanzadas que complementan las del Express BFF:
  1. Orden correcto de frecuencias segun tipo_filtro + modo.
  2. Margen minimo de una decade entre frecuencias de interes y barrido AC.
  3. Hiperparametros del algoritmo (presencia + rangos).

Todas las validaciones internas trabajan con dicts {clave: valor},
pero reciben arreglos [{clave, valor}] del request HTTP y los
convierten internamente.
"""

from typing import Tuple, List
from ..config import VALID_FILTER_TYPES, VALID_ALGORITHMS, VALID_MODES


def _arreglo_a_dict(items: list) -> dict:
    """Convierte [{clave, valor}, ...] a {clave: valor, ...}."""
    resultado = {}
    for item in items:
        if isinstance(item, dict) and "clave" in item and "valor" in item:
            resultado[item["clave"]] = item["valor"]
    return resultado


def _validate_frequencies_order(
    frecuencias: dict,
    tipo_filtro: str,
    modo: str,
    barrido: dict,
) -> List[str]:
    """
    Valida el orden numerico de las frecuencias segun tipo de filtro y modo.
    """
    errores = []

    claves_requeridas = {
        ("PASA_BAJA", "BASICO"): ["fc_objetivo"],
        ("PASA_BAJA", "AVANZADO"): ["f_paso", "f_aten"],
        ("PASA_ALTA", "BASICO"): ["fc_objetivo"],
        ("PASA_ALTA", "AVANZADO"): ["f_aten", "f_paso"],
        ("PASA_BANDA", "BASICO"): ["fc_inferior", "fc_superior"],
        ("PASA_BANDA", "AVANZADO"): ["f_aten_1", "f_paso_1", "f_paso_2", "f_aten_2"],
        ("RECHAZO_BANDA", "BASICO"): ["fc_inferior", "fc_superior"],
        ("RECHAZO_BANDA", "AVANZADO"): ["f_paso_1", "f_aten_1", "f_aten_2", "f_paso_2"],
    }

    expected = claves_requeridas.get((tipo_filtro, modo), [])
    for key in expected:
        if key not in frecuencias:
            errores.append(f"frecuencias: falta la clave requerida '{key}'")

    order_rules = {
        ("PASA_BAJA", "AVANZADO"): lambda c: c["f_paso"] < c["f_aten"],
        ("PASA_ALTA", "AVANZADO"): lambda c: c["f_aten"] < c["f_paso"],
        ("PASA_BANDA", "BASICO"): lambda c: c["fc_inferior"] < c["fc_superior"],
        ("PASA_BANDA", "AVANZADO"): lambda c: (
            c["f_aten_1"] < c["f_paso_1"]
            and c["f_paso_1"] <= c["f_paso_2"]
            and c["f_paso_2"] < c["f_aten_2"]
        ),
        ("RECHAZO_BANDA", "BASICO"): lambda c: c["fc_inferior"] < c["fc_superior"],
        ("RECHAZO_BANDA", "AVANZADO"): lambda c: (
            c["f_paso_1"] < c["f_aten_1"]
            and c["f_aten_1"] <= c["f_aten_2"]
            and c["f_aten_2"] < c["f_paso_2"]
        ),
    }

    rule = order_rules.get((tipo_filtro, modo))
    if rule and all(k in frecuencias for k in expected):
        try:
            if not rule(frecuencias):
                orden_msgs = {
                    ("PASA_BAJA", "AVANZADO"): "f_paso < f_aten",
                    ("PASA_ALTA", "AVANZADO"): "f_aten < f_paso",
                    ("PASA_BANDA", "BASICO"): "fc_inferior < fc_superior",
                    ("PASA_BANDA", "AVANZADO"): "f_aten_1 < f_paso_1 <= f_paso_2 < f_aten_2",
                    ("RECHAZO_BANDA", "BASICO"): "fc_inferior < fc_superior",
                    ("RECHAZO_BANDA", "AVANZADO"): "f_paso_1 < f_aten_1 <= f_aten_2 < f_paso_2",
                }
                errores.append(f"Orden de frecuencias invalido: se esperaba {orden_msgs.get((tipo_filtro, modo))}")
        except KeyError:
            pass

    return errores


def _validate_frequency_margin(frecuencias: dict, barrido: dict) -> List[str]:
    """
    Verifica que las frecuencias de interes esten al menos
    una decade por dentro de los limites del barrido AC.
    """
    errores = []
    f_inicial = barrido.get("f_inicial")
    f_final = barrido.get("f_final")

    if f_inicial is None or f_final is None:
        return errores

    all_freqs = [v for v in frecuencias.values() if isinstance(v, (int, float))]
    if not all_freqs:
        return errores

    mas_baja = min(all_freqs)
    mas_alta = max(all_freqs)

    if mas_baja < f_inicial * 10:
        errores.append(
            f"Frecuencia mas baja ({mas_baja} Hz) menor que una decade de f_inicial "
            f"({f_inicial} Hz = {f_inicial * 10} Hz)"
        )
    if mas_alta > f_final / 10:
        errores.append(
            f"Frecuencia mas alta ({mas_alta} Hz) mayor que una decade de f_final "
            f"({f_final} Hz = {f_final / 10} Hz)"
        )

    return errores


def _validate_optimizer_params(params: dict, algoritmo: str) -> List[str]:
    """
    Valida la presencia y rangos de los hiperparametros
    del algoritmo de optimizacion seleccionado.
    """
    errores = []

    if algoritmo == "AG":
        required = ["tam_poblacion", "num_generaciones", "prob_cruce", "prob_mutacion", "elitismo", "torneo_k"]
        for key in required:
            if key not in params:
                errores.append(f"parametros_optimizador: falta '{key}' para AG")

        tp = params.get("tam_poblacion")
        ng = params.get("num_generaciones")
        pc = params.get("prob_cruce")
        pm = params.get("prob_mutacion")
        el = params.get("elitismo")
        tk = params.get("torneo_k")

        if tp is not None and (not isinstance(tp, int) or tp < 1):
            errores.append("tam_poblacion debe ser un entero >= 1")
        if ng is not None and (not isinstance(ng, int) or ng < 1):
            errores.append("num_generaciones debe ser un entero >= 1")
        if pc is not None and (not isinstance(pc, (int, float)) or pc < 0 or pc > 1):
            errores.append("prob_cruce debe ser un numero entre 0 y 1")
        if pm is not None and (not isinstance(pm, (int, float)) or pm < 0 or pm > 1):
            errores.append("prob_mutacion debe ser un numero entre 0 y 1")
        if el is not None and tp is not None and (not isinstance(el, int) or el < 0 or el >= tp):
            errores.append("elitismo debe ser un entero >= 0 y menor que tam_poblacion")
        if tk is not None and (not isinstance(tk, int) or tk < 1):
            errores.append("torneo_k debe ser un entero >= 1")

    elif algoritmo == "PSO":
        required = ["num_particulas", "num_iteraciones", "w", "c1", "c2"]
        for key in required:
            if key not in params:
                errores.append(f"parametros_optimizador: falta '{key}' para PSO")

        np_ = params.get("num_particulas")
        ni = params.get("num_iteraciones")
        w = params.get("w")
        c1 = params.get("c1")
        c2 = params.get("c2")

        if np_ is not None and (not isinstance(np_, int) or np_ < 1):
            errores.append("num_particulas debe ser un entero >= 1")
        if ni is not None and (not isinstance(ni, int) or ni < 0):
            errores.append("num_iteraciones debe ser un entero >= 0")
        if w is not None and (not isinstance(w, (int, float)) or w < 0 or w > 1):
            errores.append("w debe ser un numero entre 0 y 1")
        if c1 is not None and (not isinstance(c1, (int, float)) or c1 <= 0):
            errores.append("c1 debe ser un numero mayor a 0")
        if c2 is not None and (not isinstance(c2, (int, float)) or c2 <= 0):
            errores.append("c2 debe ser un numero mayor a 0")

    return errores


def validar_config_nivel2(
    tipo_filtro: str,
    algoritmo: str,
    config: dict,
) -> Tuple[bool, List[str]]:
    """
    Orquestador de validacion Nivel 2.
    Ejecuta todas las sub-validaciones avanzadas y retorna (valido, errores).
    """
    errores = []

    if tipo_filtro not in VALID_FILTER_TYPES:
        errores.append(f"tipo_filtro debe ser uno de: {VALID_FILTER_TYPES}")
    if algoritmo not in VALID_ALGORITHMS:
        errores.append(f"algoritmo debe ser uno de: {VALID_ALGORITHMS}")

    modo = config.get("modo")
    if not modo or modo.strip().upper() not in VALID_MODES:
        errores.append(f"modo debe ser 'BASICO' o 'AVANZADO'")
    else:
        config["modo"] = modo.strip().upper()

    barrido = config.get("barrido_ac", {})
    if not barrido.get("f_inicial") or not barrido.get("f_final"):
        errores.append("barrido_ac.f_inicial y barrido_ac.f_final son requeridos")
    elif barrido.get("f_final", 0) > 10_000_000:
        errores.append("barrido_ac.f_final no debe exceder 10,000,000 Hz")

    # Convierte arreglos a dicts antes de validar
    frecuencias = config.get("frecuencias", [])
    if isinstance(frecuencias, list):
        frecuencias = _arreglo_a_dict(frecuencias)
    if isinstance(frecuencias, dict):
        errores.extend(_validate_frequencies_order(frecuencias, tipo_filtro, modo, barrido))
        errores.extend(_validate_frequency_margin(frecuencias, barrido))

    params = config.get("parametros_optimizador", [])
    if isinstance(params, list):
        params = _arreglo_a_dict(params)
    if isinstance(params, dict):
        errores.extend(_validate_optimizer_params(params, algoritmo))

    return (len(errores) == 0, errores)
