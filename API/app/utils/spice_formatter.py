"""
Utilería: funciones de formateo de valores para archivos SPICE.
No depende de ninguna otra capa.
"""
import re


def valor_spice(v: float) -> str:
    """Convierte un número a notación científica limpia aceptada por ngspice.
    Ejemplo: 1e-08 → '1.0e-8'
    """
    return re.sub(r"e([+-])0", r"e\1", f"{v:.1e}")


def valor_frecuencia(v: float) -> str:
    """Formatea una frecuencia del barrido .AC: entero limpio si no tiene
    parte decimal (1 → '1', 1e7 → '10000000').
    """
    return str(int(v)) if float(v).is_integer() else str(v)