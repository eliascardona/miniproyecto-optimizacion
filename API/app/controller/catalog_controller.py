"""
Controlador de GET /api/catalogo: el catálogo filtro × algoritmo × modo.

Las combinaciones disponibles salen de IndividualOptimizationController.SERVICE_MAP, o sea de lo que el
servidor ejecuta de verdad: agregar un servicio al mapa lo vuelve "disponible" aquí sin tocar nada más
(siempre que definiciones.py ya describa sus parámetros; si no, el catálogo falla al construirse y las
pruebas lo detectan).
"""
from functools import lru_cache

from fastapi import HTTPException

from app.controller.individual_optimization_controller import IndividualOptimizationController
from app.utils.catalogo import CatalogoInvalido, construir_catalogo


@lru_cache(maxsize=1)
def _catalogo() -> dict:
    """Se construye una sola vez por proceso (las definiciones no cambian mientras el servidor corre)."""
    return construir_catalogo(IndividualOptimizationController.SERVICE_MAP.keys())


class CatalogController:

    def get_catalog(self) -> dict:
        try:
            return _catalogo()
        except CatalogoInvalido as e:
            # Definiciones inconsistentes: es un error del servidor, no del cliente.
            raise HTTPException(status_code=500, detail=f"El catálogo del servidor es inconsistente: {e}")