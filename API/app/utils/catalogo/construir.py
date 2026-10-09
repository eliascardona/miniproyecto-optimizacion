"""
Construye el catálogo (el dict que devuelve GET /api/catalogo) a partir de definiciones.py.

El catálogo le dice al cliente QUÉ puede pedir y CÓMO armar la petición, sin que el cliente tenga que
saberlo de antemano:
  · combinaciones  -> qué filtro × algoritmo corren de verdad (salen de SERVICE_MAP, que es lo que el
                      controlador ejecuta; no hay una lista aparte que se pueda desincronizar).
  · filtros        -> las frecuencias objetivo de cada modo (claves, orden, límites, valores iniciales).
  · algoritmos     -> los hiperparámetros (claves, tipos, límites, relaciones).
  · entorno/barrido/reglas -> lo común a todas las combinaciones.

Este módulo NO importa el controlador (utils no debe depender de controller): quien lo llama le pasa las
combinaciones disponibles.
"""
import copy
from itertools import product
from typing import Iterable

from . import definiciones as d


class CatalogoInvalido(ValueError):
    """Las definiciones del catálogo son inconsistentes entre sí (error de programación, no del cliente)."""


# --------------------------------------------------------------------------------------------------
# Comprobaciones de consistencia (se ejecutan al construir: un catálogo roto falla ruidosamente)
# --------------------------------------------------------------------------------------------------


def cumple_limites_duros(campo: dict, valor: float) -> bool:
    """True si `valor` respeta minimo/maximo (con sus variantes exclusivas) de `campo`."""
    if campo["minimo"] is not None:
        if valor < campo["minimo"] or (campo["minimo_exclusivo"] and valor == campo["minimo"]):
            return False
    if campo["maximo"] is not None:
        if valor > campo["maximo"] or (campo["maximo_exclusivo"] and valor == campo["maximo"]):
            return False
    return True


def relacion_se_cumple(relacion: dict, valores: dict) -> bool:
    izquierda, derecha = valores[relacion["izquierda"]], valores[relacion["derecha"]]
    return izquierda < derecha if relacion["operador"] == "<" else izquierda <= derecha


def _comprobar_campos_y_valores(donde: str, campos: list, relaciones: list, valores: dict) -> None:
    claves = [c["clave"] for c in campos]
    if len(set(claves)) != len(claves):
        raise CatalogoInvalido(f"{donde}: claves repetidas {claves}")
    if set(valores) != set(claves):
        raise CatalogoInvalido(f"{donde}: los valores iniciales {sorted(valores)} no coinciden con los campos "
                               f"{sorted(claves)}")
    por_clave = {c["clave"]: c for c in campos}
    for clave, valor in valores.items():
        if not cumple_limites_duros(por_clave[clave], valor):
            raise CatalogoInvalido(f"{donde}: el valor inicial de '{clave}' ({valor}) viola sus límites duros")
        if por_clave[clave]["tipo"] == "entero" and int(valor) != valor:
            raise CatalogoInvalido(f"{donde}: '{clave}' es entero y su valor inicial es {valor}")
    for relacion in relaciones:
        for extremo in (relacion["izquierda"], relacion["derecha"]):
            if extremo not in por_clave:
                raise CatalogoInvalido(f"{donde}: la relación nombra '{extremo}', que no es un campo")
        if relacion["severidad"] == "error" and not relacion_se_cumple(relacion, valores):
            raise CatalogoInvalido(f"{donde}: los valores iniciales incumplen {relacion['izquierda']} "
                                   f"{relacion['operador']} {relacion['derecha']}")


def comprobar_definiciones(disponibles: set) -> None:
    ids_filtro = [f["id"] for f in d.FILTROS]
    ids_algoritmo = [a["id"] for a in d.ALGORITMOS]
    ids_modo = [m["id"] for m in d.MODOS]
    todas = set(product(ids_filtro, ids_algoritmo))

    if set(d.FRECUENCIAS) != set(ids_filtro):
        raise CatalogoInvalido("FRECUENCIAS no cubre exactamente los filtros de FILTROS")
    if set(d.VALORES_INICIALES) != todas:
        faltan = sorted(todas - set(d.VALORES_INICIALES))
        sobran = sorted(set(d.VALORES_INICIALES) - todas)
        raise CatalogoInvalido(f"VALORES_INICIALES no cubre las {len(todas)} combinaciones (faltan {faltan}, "
                               f"sobran {sobran})")
    if not disponibles <= todas:
        raise CatalogoInvalido(f"Hay combinaciones disponibles que el catálogo no define: "
                               f"{sorted(disponibles - todas)}")

    for filtro in ids_filtro:
        if set(d.FRECUENCIAS[filtro]) != set(ids_modo):
            raise CatalogoInvalido(f"{filtro}: debe definir exactamente los modos {ids_modo}")
        for modo, datos in d.FRECUENCIAS[filtro].items():
            donde = f"frecuencias de {filtro}/{modo}"
            _comprobar_campos_y_valores(donde, datos["campos"], datos["relaciones"], datos["valores"])
            claves = [c["clave"] for c in datos["campos"]]
            if not set(datos["extremos"]) <= set(claves):
                raise CatalogoInvalido(f"{donde}: extremos {datos['extremos']} no son campos")
            menor, mayor = (datos["valores"][k] for k in datos["extremos"])
            if menor > mayor:
                raise CatalogoInvalido(f"{donde}: la frecuencia 'mínima' supera a la 'máxima'")

    for algoritmo in d.ALGORITMOS:
        for filtro in ids_filtro:
            _comprobar_campos_y_valores(
                f"parámetros de {filtro}/{algoritmo['id']}",
                algoritmo["parametros"], algoritmo["relaciones"], d.VALORES_INICIALES[(filtro, algoritmo["id"])])

    _comprobar_campos_y_valores(
        "barrido_ac", d.BARRIDO_AC, d.RELACIONES_BARRIDO, {"f_inicial": 1, "f_final": 100000})


# --------------------------------------------------------------------------------------------------
# Construcción
# --------------------------------------------------------------------------------------------------


def construir_catalogo(disponibles: Iterable[tuple]) -> dict:
    """
    `disponibles`: pares (filtro, algoritmo) que el servidor sabe ejecutar (las claves de SERVICE_MAP).
    Devuelve un dict nuevo (el llamador puede mutarlo sin afectar a definiciones.py).
    """
    disponibles = {tuple(par) for par in disponibles}
    comprobar_definiciones(disponibles)

    filtros = []
    for filtro in d.FILTROS:
        entrada = copy.deepcopy(filtro)
        entrada["frecuencias"] = []
        for modo in d.MODOS:
            datos = d.FRECUENCIAS[filtro["id"]][modo["id"]]
            minima, maxima = datos["extremos"]
            entrada["frecuencias"].append({
                "modo": modo["id"],
                "campos": copy.deepcopy(datos["campos"]),
                "relaciones": copy.deepcopy(datos["relaciones"]),
                "extremos": {"minima": minima, "maxima": maxima},
                "valores_iniciales": dict(datos["valores"]),
            })
        filtros.append(entrada)

    combinaciones = [
        {
            "filtro": filtro["id"],
            "algoritmo": algoritmo["id"],
            "disponible": (filtro["id"], algoritmo["id"]) in disponibles,
            "valores_iniciales": dict(d.VALORES_INICIALES[(filtro["id"], algoritmo["id"])]),
        }
        for filtro in d.FILTROS
        for algoritmo in d.ALGORITMOS
    ]

    return {
        "version_catalogo": d.VERSION_CATALOGO,
        "modos": copy.deepcopy(d.MODOS),
        "entorno": copy.deepcopy(d.ENTORNO),
        "barrido_ac": {"campos": copy.deepcopy(d.BARRIDO_AC), "relaciones": copy.deepcopy(d.RELACIONES_BARRIDO)},
        "reglas": copy.deepcopy(d.REGLAS),
        "filtros": filtros,
        "algoritmos": copy.deepcopy(d.ALGORITMOS),
        "combinaciones": combinaciones,
    }