"""
Validador de frecuencias por tipo de filtro y modo.

Cada tipo de filtro tiene reglas especificas sobre:
  1. Claves requeridas (ej: PASA_BAJA BASICO solo necesita fc_objetivo).
  2. Orden numerico obligatorio entre frecuencias.
  3. Margen minimo de una decade entre frecuencias y limites del barrido AC.

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


def validar_frecuencias(
    frecuencias,
    tipo_filtro: str,
    modo: str,
    barrido_ac: dict,
) -> List[str]:
    """
    Valida las frecuencias segun tipo_filtro y modo.
    Acepta tanto listas [{clave, valor}] como dicts {clave: valor}.
    """
    errores = []

    if isinstance(frecuencias, list):
        frecuencias = _arreglo_a_dict(frecuencias)

    if not isinstance(frecuencias, dict):
        errores.append("frecuencias debe ser un arreglo [{clave, valor}] o un objeto {clave: valor}")
        return errores

    claves_requeridas = _obtener_claves_requeridas(tipo_filtro, modo)
    for key in claves_requeridas:
        if key not in frecuencias:
            errores.append(f"frecuencias: falta la clave '{key}' para {tipo_filtro} modo {modo}")

    errores.extend(_verificar_margen_decade(frecuencias, barrido_ac))

    return errores


def _obtener_claves_requeridas(tipo_filtro: str, modo: str) -> List[str]:
    mapa = {
        ("PASA_BAJA", "BASICO"): ["fc_objetivo"],
        ("PASA_BAJA", "AVANZADO"): ["f_paso", "f_aten"],
        ("PASA_ALTA", "BASICO"): ["fc_objetivo"],
        ("PASA_ALTA", "AVANZADO"): ["f_aten", "f_paso"],
        ("PASA_BANDA", "BASICO"): ["fc_inferior", "fc_superior"],
        ("PASA_BANDA", "AVANZADO"): ["f_aten_1", "f_paso_1", "f_paso_2", "f_aten_2"],
        ("RECHAZO_BANDA", "BASICO"): ["fc_inferior", "fc_superior"],
        ("RECHAZO_BANDA", "AVANZADO"): ["f_paso_1", "f_aten_1", "f_aten_2", "f_paso_2"],
    }
    return mapa.get((tipo_filtro, modo), [])


def _verificar_margen_decade(frecuencias: dict, barrido_ac: dict) -> List[str]:
    errores = []
    f_inicial = barrido_ac.get("f_inicial", 0)
    f_final = barrido_ac.get("f_final", 0)

    if f_inicial <= 0 or f_final <= 0:
        return errores

    all_freqs = [v for v in frecuencias.values() if isinstance(v, (int, float))]
    if not all_freqs:
        return errores

    mas_baja = min(all_freqs)
    mas_alta = max(all_freqs)

    if mas_baja < f_inicial * 10:
        errores.append(
            f"La frecuencia mas baja ({mas_baja} Hz) debe ser al menos "
            f"una decade por encima de f_inicial ({f_inicial} Hz)"
        )
    if mas_alta > f_final / 10:
        errores.append(
            f"La frecuencia mas alta ({mas_alta} Hz) debe ser al menos "
            f"una decade por debajo de f_final ({f_final} Hz)"
        )

    return errores
