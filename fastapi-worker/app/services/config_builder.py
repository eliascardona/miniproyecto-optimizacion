"""
Constructor del config.json que los scripts Python consumen.

Remueve tipo_filtro y algoritmo del request (se usan solo para
enrutar que script ejecutar) y pasa el resto tal cual.

Los scripts esperan parametros_optimizador y frecuencias como
arreglos de {clave, valor} (no como objetos planos).
"""

from typing import Dict, Any


def build_config_json(config: dict) -> Dict[str, Any]:
    """
    Genera el config.json que consumen los scripts Python.

    Solo remueve tipo_filtro y algoritmo (campos de enrutamiento).
    parametros_optimizador y frecuencias se pasan tal cual como
    arreglos [{clave, valor}] — que es lo que _buscar_etiqueta()
    espera en los scripts.
    """
    resultado = {
        "modo": config.get("modo", ""),
        "entorno": config.get("entorno", {}),
        "barrido_ac": config.get("barrido_ac", {}),
        "parametros_optimizador": config.get("parametros_optimizador", []),
        "frecuencias": config.get("frecuencias", []),
    }
    return resultado
