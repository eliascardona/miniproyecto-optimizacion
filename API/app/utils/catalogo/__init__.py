"""Catálogo filtro × algoritmo: qué se puede pedir a /api/optimizar y cómo armar la petición."""
from .construir import CatalogoInvalido, construir_catalogo, cumple_limites_duros, relacion_se_cumple

__all__ = ["CatalogoInvalido", "construir_catalogo", "cumple_limites_duros", "relacion_se_cumple"]