"""
Validador de la serie E12 comercial.

La serie E12 es una norma internacional de valores preferidos para
componentes electronicos (resistencias, capacitores). Los valores
siguen la progresion: mantisa * 10^n, donde mantisa E12 = {1.0, 1.2,
1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2}.

Se aplica a: r_fuente y r_carga (resistencias).
No se aplica a capacitores (valores futuros se omiten por ahora).
"""

from typing import List

# Valores de mantisa de la serie E12 (10% de tolerancia)
E12_MANTISAS = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]


def es_e12(valor: float) -> bool:
    """
    Verifica si un valor pertenece a la serie E12 comercial.
    Descompone el valor en mantisa * 10^n y compara la mantisa
    contra la tabla de valores E12 con un margen de tolerancia de 0.01.
    """
    if valor <= 0:
        return False
    import math
    exp = math.floor(math.log10(valor))
    mantisa = round(valor / (10 ** exp), 3)
    return any(abs(m - mantisa) < 0.01 for m in E12_MANTISAS)


def validar_e12_circuit(circuito: dict) -> List[str]:
    """
    Valida todas las resistencias del circuito contra la serie E12.
    Retorna una lista de mensajes de error (vacia si todo esta OK).
    """
    errores = []
    r_fuente = circuito.get("r_fuente")
    r_carga = circuito.get("r_carga")

    if r_fuente is not None and not es_e12(r_fuente):
        errores.append(f"r_fuente ({r_fuente}) no pertenece a la serie E12")
    if r_carga is not None and not es_e12(r_carga):
        errores.append(f"r_carga ({r_carga}) no pertenece a la serie E12")

    return errores
