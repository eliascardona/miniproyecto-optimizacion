"""
Controlador de GET /api/circuitos/{filtro}: devuelve el ESQUEMA (el dibujo) de un filtro con los
valores base de su plantilla, p. ej. para mostrar el circuito ANTES de optimizar.
"""
from fastapi import HTTPException

from app.pydantic_schema.api_request_schema.circuit_optimization_request import FiltroEnum
from app.utils.esquema import EsquemaError, obtener_esquema


class CircuitSchemaController:

    def get_schema(self, filtro: str) -> dict:
        disponibles = [f.value for f in FiltroEnum]
        if filtro not in disponibles:
            raise HTTPException(
                status_code=404,
                detail=f"No existe el filtro '{filtro}'. Disponibles: {disponibles}",
            )
        try:
            return obtener_esquema(filtro)
        except EsquemaError as e:
            # El filtro existe pero su plantilla .cir no se puede dibujar: es un problema del
            # servidor (plantilla mal formada o con una topología no soportada), no del cliente.
            raise HTTPException(
                status_code=500,
                detail=f"La plantilla del filtro '{filtro}' no se puede dibujar: {e}",
            )