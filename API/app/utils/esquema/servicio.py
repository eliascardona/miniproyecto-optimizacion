"""
Punto de entrada para el resto de la API: esquema de un filtro, a partir de la
PLANTILLA de solo lectura de constants_repository.

El layout depende solo de la topología, así que se calcula UNA vez por filtro
(y por versión del archivo) y se cachea; los valores de los componentes se
aplican después, sobre una copia nueva del esquema en cada llamada.
"""
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from app.constants_repository import ConstantsRepository

from .errores import EsquemaError
from .layout import construir_esquema
from .netlist import parse_netlist
from .validacion import exigir_esquema_valido


@lru_cache(maxsize=32)
def _esquema_base_json(ruta: str, mtime_ns: int) -> str:
    net = parse_netlist(Path(ruta).read_text(encoding="utf-8", errors="replace"))
    esquema = construir_esquema(net)
    exigir_esquema_valido(esquema, net)
    return json.dumps(esquema, ensure_ascii=False)


def limpiar_cache() -> None:
    _esquema_base_json.cache_clear()


def _aplicar_valores(esquema: dict, valores: Mapping[str, float], filtro: str) -> None:
    por_nombre = {}
    for entrada in (*esquema["elementos"], *esquema["alimentacion"]):
        por_nombre[entrada["nombre"].lower()] = entrada
    for nombre, valor in valores.items():
        entrada = por_nombre.get(str(nombre).lower())
        if entrada is None:
            raise EsquemaError(f"El esquema de '{filtro}' no tiene un componente llamado '{nombre}'.")
        if not isinstance(valor, (int, float)) or not math.isfinite(valor):
            raise EsquemaError(f"Valor inválido para '{nombre}': {valor!r}")
        entrada["valor"] = float(valor)


def obtener_esquema(filtro: str, valores: Mapping[str, float] | None = None) -> dict:
    """
    Esquema del filtro, listo para serializar a JSON.

    `valores` (opcional) reemplaza el valor de componentes por nombre
    (p. ej. los R/C optimizados y Vs/Rs/Rl/Vpp/Vnn de la petición); un nombre
    que no exista en el esquema es un error (así se detecta cualquier
    desfase entre el optimizador y el dibujo).
    """
    ruta = ConstantsRepository.plantilla_cir(filtro)
    esquema = json.loads(_esquema_base_json(ruta, Path(ruta).stat().st_mtime_ns))
    esquema["filtro"] = filtro
    if valores:
        _aplicar_valores(esquema, valores, filtro)
    return esquema